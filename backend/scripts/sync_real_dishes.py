from __future__ import annotations

import argparse
import json
import shutil
import ssl
import sys
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Any
from urllib import request

import certifi
from sqlmodel import Session, select

from backend.config import DATABASE_URL
from backend.database import engine
from backend.models.dish import Dish
from backend.models.dish_spec import DishSpec

DEFAULT_BASE_URL = "https://wangge-menu-316255291165.asia-east2.run.app"
DEFAULT_USERNAME = "admin"
DEFAULT_PASSWORD = "wangge2026"


def now_stamp() -> str:
    return datetime.now().strftime("%Y%m%d-%H%M%S")


def round_money(value: float) -> float:
    return round(float(value), 2)


def compute_compat_min_price(cost: float) -> float:
    if cost <= 0:
        return 0.0
    return round_money(cost * 1.3)


def extract_spec_name(price_text: str) -> str:
    if "/" in price_text:
        return price_text.rsplit("/", 1)[1].strip() or "标准"
    return "标准"


def is_meaningful_diff(current: Any, target: Any) -> bool:
    return current != target


def fetch_old_dishes(base_url: str, username: str, password: str) -> list[dict[str, Any]]:
    ssl_context = ssl.create_default_context(cafile=certifi.where())
    login_req = request.Request(
        f"{base_url.rstrip('/')}/api/auth/login",
        data=json.dumps({"username": username, "password": password}).encode("utf-8"),
        headers={"Content-Type": "application/json"},
    )
    with request.urlopen(login_req, context=ssl_context) as resp:
        token = json.load(resp)["access_token"]

    dishes_req = request.Request(
        f"{base_url.rstrip('/')}/api/dishes?active_only=false",
        headers={"Authorization": f"Bearer {token}"},
    )
    with request.urlopen(dishes_req, context=ssl_context) as resp:
        return json.load(resp)


def snapshot_dir() -> Path:
    return Path("tmp/backups")


def build_snapshot_payload(base_url: str, dishes: list[dict[str, Any]]) -> dict[str, Any]:
    return {
        "exported_at": datetime.now().isoformat(timespec="seconds"),
        "source": {
            "base_url": base_url,
            "endpoint": "/api/dishes?active_only=false",
        },
        "dish_count": len(dishes),
        "dishes": dishes,
    }


def save_snapshot(payload: dict[str, Any], output_path: Path) -> None:
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def load_snapshot(snapshot_path: Path) -> dict[str, Any]:
    return json.loads(snapshot_path.read_text(encoding="utf-8"))


def resolve_sqlite_path(database_url: str) -> Path | None:
    prefix = "sqlite:///"
    if not database_url.startswith(prefix):
        return None
    raw = database_url[len(prefix):]
    if not raw:
        return None
    return Path(raw).resolve()


def backup_sqlite_db() -> Path | None:
    db_path = resolve_sqlite_path(DATABASE_URL)
    if not db_path or not db_path.exists():
        return None
    backup_path = snapshot_dir() / f"{db_path.stem}.before-real-sync-{now_stamp()}{db_path.suffix}"
    backup_path.parent.mkdir(parents=True, exist_ok=True)
    shutil.copy2(db_path, backup_path)
    return backup_path


@dataclass
class SpecPlan:
    action: str
    spec_id: int | None
    fields: dict[str, Any]


@dataclass
class DishPlan:
    dish_id: int
    name: str
    dish_fields: dict[str, Any]
    spec_mode: str
    spec_plans: list[SpecPlan]
    delete_spec_ids: list[int]
    old_spec_count: int
    new_spec_count: int


def _dish_fields_from_source(source_dish: dict[str, Any]) -> dict[str, Any]:
    cost = round_money(source_dish.get("cost") or 0.0)
    return {
        "price_text": source_dish.get("price_text") or "",
        "price": round_money(source_dish.get("price") or 0.0),
        "cost": cost,
        "min_price": compute_compat_min_price(cost),
        "is_market_price": bool(source_dish.get("is_market_price")),
        "is_active": bool(source_dish.get("is_active", True)),
    }


def _spec_fields_from_source(source_spec: dict[str, Any], *, keep_shape: DishSpec | None = None, is_default: bool | None = None) -> dict[str, Any]:
    fields = {
        "price_text": source_spec.get("price_text") or "",
        "price": round_money(source_spec.get("price") or 0.0),
        "cost": round_money(source_spec.get("cost") or 0.0),
        "is_active": bool(source_spec.get("is_active", True)),
    }
    if keep_shape is not None:
        fields.update(
            {
                "spec_name": keep_shape.spec_name,
                "min_people": keep_shape.min_people,
                "max_people": keep_shape.max_people,
                "is_default": keep_shape.is_default,
                "sort_order": keep_shape.sort_order,
            }
        )
    else:
        fields.update(
            {
                "spec_name": extract_spec_name(source_spec.get("price_text") or ""),
                "min_people": 0,
                "max_people": 0,
                "is_default": bool(is_default),
                "sort_order": int(source_spec.get("sort_order") or 0),
            }
        )
    return fields


def build_sync_plan(session: Session, snapshot: dict[str, Any]) -> tuple[list[DishPlan], dict[str, Any]]:
    source_dishes = snapshot.get("dishes") or []
    current_dishes = list(session.exec(select(Dish)).all())
    current_by_name = {dish.name: dish for dish in current_dishes}

    plans: list[DishPlan] = []
    id_mismatches: list[dict[str, Any]] = []
    missing_names: list[str] = []
    market_zero_names: list[str] = []
    rebuild_names: list[str] = []
    changed_dish_names: list[str] = []

    for source_dish in source_dishes:
        source_name = source_dish["name"]
        current_dish = current_by_name.get(source_name)
        if not current_dish:
            missing_names.append(source_name)
            continue
        if current_dish.id != source_dish.get("id"):
            id_mismatches.append(
                {
                    "name": source_name,
                    "old_id": source_dish.get("id"),
                    "new_id": current_dish.id,
                }
            )
            continue

        current_specs = list(session.exec(
            select(DishSpec)
            .where(DishSpec.dish_id == current_dish.id)
            .order_by(DishSpec.sort_order, DishSpec.id)
        ).all())
        source_specs = list(source_dish.get("specs") or [])
        dish_fields = _dish_fields_from_source(source_dish)

        if source_dish.get("is_market_price") and dish_fields["price"] == 0 and dish_fields["cost"] == 0:
            market_zero_names.append(source_name)

        spec_plans: list[SpecPlan] = []
        delete_spec_ids: list[int] = []
        spec_mode = "single_update"

        if len(source_specs) == 1 and len(current_specs) == 1:
            spec_plans.append(
                SpecPlan(
                    action="update",
                    spec_id=current_specs[0].id,
                    fields=_spec_fields_from_source(source_specs[0], keep_shape=current_specs[0]),
                )
            )
        else:
            spec_mode = "rebuild"
            rebuild_names.append(source_name)
            delete_spec_ids = [spec.id for spec in current_specs if spec.id is not None]
            default_price_text = dish_fields["price_text"]
            for index, source_spec in enumerate(source_specs):
                spec_fields = _spec_fields_from_source(
                    source_spec,
                    keep_shape=None,
                    is_default=(source_spec.get("price_text") == default_price_text) or (index == 0 and default_price_text == ""),
                )
                spec_fields["sort_order"] = index
                if index == 0 and not any(plan.fields["is_default"] for plan in spec_plans):
                    spec_fields["is_default"] = source_spec.get("price_text") == default_price_text or index == 0
                spec_plans.append(SpecPlan(action="create", spec_id=None, fields=spec_fields))

        dish_changed = any(
            is_meaningful_diff(getattr(current_dish, field_name), target)
            for field_name, target in dish_fields.items()
        )
        spec_changed = spec_mode == "rebuild" or any(
            any(is_meaningful_diff(getattr(current_specs[0], field_name), target) for field_name, target in plan.fields.items())
            for plan in spec_plans
            if current_specs and plan.action == "update"
        )
        if dish_changed or spec_changed:
            changed_dish_names.append(source_name)

        plans.append(
            DishPlan(
                dish_id=current_dish.id or 0,
                name=source_name,
                dish_fields=dish_fields,
                spec_mode=spec_mode,
                spec_plans=spec_plans,
                delete_spec_ids=delete_spec_ids,
                old_spec_count=len(source_specs),
                new_spec_count=len(current_specs),
            )
        )

    report = {
        "source_dish_count": len(source_dishes),
        "matched_dishes": len(plans),
        "changed_dishes": len(changed_dish_names),
        "missing_names": missing_names,
        "id_mismatches": id_mismatches,
        "market_zero_count": len(market_zero_names),
        "market_zero_names": market_zero_names,
        "rebuild_spec_dish_count": len(rebuild_names),
        "rebuild_spec_dish_names": rebuild_names,
        "single_spec_update_count": sum(1 for plan in plans if plan.spec_mode == "single_update"),
        "compat_min_price_rule": "recompute_from_cost",
    }
    return plans, report


def apply_sync_plan(session: Session, plans: list[DishPlan]) -> dict[str, int]:
    updated_dishes = 0
    updated_specs = 0
    created_specs = 0
    deleted_specs = 0

    for plan in plans:
        dish = session.get(Dish, plan.dish_id)
        if not dish:
            raise ValueError(f"菜品不存在: {plan.name} ({plan.dish_id})")
        for field_name, value in plan.dish_fields.items():
            setattr(dish, field_name, value)
        session.add(dish)
        updated_dishes += 1

        if plan.spec_mode == "rebuild":
            for spec_id in plan.delete_spec_ids:
                spec = session.get(DishSpec, spec_id)
                if spec:
                    session.delete(spec)
                    deleted_specs += 1
            session.flush()

        for spec_plan in plan.spec_plans:
            if spec_plan.action == "update":
                spec = session.get(DishSpec, spec_plan.spec_id)
                if not spec:
                    raise ValueError(f"规格不存在: {plan.name} spec={spec_plan.spec_id}")
                for field_name, value in spec_plan.fields.items():
                    setattr(spec, field_name, value)
                session.add(spec)
                updated_specs += 1
            else:
                spec = DishSpec(dish_id=plan.dish_id, **spec_plan.fields)
                session.add(spec)
                created_specs += 1

    session.commit()
    return {
        "updated_dishes": updated_dishes,
        "updated_specs": updated_specs,
        "created_specs": created_specs,
        "deleted_specs": deleted_specs,
    }


def command_export(args: argparse.Namespace) -> int:
    dishes = fetch_old_dishes(args.base_url, args.username, args.password)
    payload = build_snapshot_payload(args.base_url, dishes)
    output_path = Path(args.output) if args.output else snapshot_dir() / f"real-dishes-{now_stamp()}.json"
    save_snapshot(payload, output_path)
    print(json.dumps({"snapshot": str(output_path), "dish_count": len(dishes)}, ensure_ascii=False, indent=2))
    return 0


def command_sync(args: argparse.Namespace) -> int:
    snapshot = load_snapshot(Path(args.snapshot))
    with Session(engine) as session:
        plans, report = build_sync_plan(session, snapshot)
        print(json.dumps(report, ensure_ascii=False, indent=2))

        if report["missing_names"] or report["id_mismatches"]:
            print("同步已中止：发现缺失菜名或 ID 不匹配。", file=sys.stderr)
            return 1

        if not args.apply:
            return 0

        backup_path = backup_sqlite_db()
        stats = apply_sync_plan(session, plans)
        if backup_path:
            stats["backup_path"] = str(backup_path)
        print(json.dumps(stats, ensure_ascii=False, indent=2))
    return 0


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="同步旧生产真实菜品数据到新版本地数据库")
    subparsers = parser.add_subparsers(dest="command", required=True)

    export_parser = subparsers.add_parser("export", help="从旧生产抓取菜品快照")
    export_parser.add_argument("--base-url", default=DEFAULT_BASE_URL)
    export_parser.add_argument("--username", default=DEFAULT_USERNAME)
    export_parser.add_argument("--password", default=DEFAULT_PASSWORD)
    export_parser.add_argument("--output", help="快照输出路径")
    export_parser.set_defaults(func=command_export)

    sync_parser = subparsers.add_parser("sync", help="根据快照 dry-run 或写入本地数据库")
    sync_parser.add_argument("--snapshot", required=True, help="export 生成的 JSON 快照")
    sync_parser.add_argument("--apply", action="store_true", help="确认写入数据库；默认仅 dry-run")
    sync_parser.set_defaults(func=command_sync)

    return parser


def main() -> int:
    parser = build_parser()
    args = parser.parse_args()
    return args.func(args)


if __name__ == "__main__":
    raise SystemExit(main())
