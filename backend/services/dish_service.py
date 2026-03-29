import csv
import re
import hashlib
from sqlmodel import Session, select
from backend.models.dish import Dish
from backend.models.dish_spec import DishSpec
from backend.config import CSV_PATH

CATEGORY_COST_RATIO = {
    "凉菜": 0.28,   # 毛利高，~72%
    "热菜": 0.38,   # 中等，~62%
    "汤羹": 0.30,   # 汤水成本低，~70%
    "主食": 0.25,   # 毛利最高，~75%
    "甜品": 0.32,   # ~68%
    "点心": 0.30,   # ~70%
}


def get_category_cost_ratio(category: str) -> float:
    return CATEGORY_COST_RATIO.get(category, 0.35)


def calculate_min_price(cost: float) -> float:
    return round(cost * 1.3, 2)


def build_price_text(price: float, serving_unit: str) -> str:
    unit = (serving_unit or "例").strip() or "例"
    return f"{round(price, 2):.2f}元/{unit}"


def _extract_serving_unit(price_text: str) -> str:
    match = re.search(r"元/([^\s/]+)", price_text)
    return match.group(1).strip() if match else ""


def parse_price(price_str: str) -> tuple[str, float, bool, str]:
    """解析价格字符串 → (price_text, price, is_market_price, serving_unit)"""
    if not price_str or price_str.strip() == "":
        return "", 0.0, False, ""

    price_str = price_str.strip()

    if price_str == "时价" or price_str.startswith("时价"):
        # 时价(参考180元)/例 or 时价
        ref_match = re.search(r"参考(\d+\.?\d*)", price_str)
        ref_price = float(ref_match.group(1)) if ref_match else 0.0
        price_text = price_str if "参考" in price_str else f"时价(参考0元)/例"
        return price_text, ref_price, True, _extract_serving_unit(price_text)

    # 标准价格: 99元/例、53元/只、13.9元/件
    match = re.match(r"^(\d+\.?\d*)元/(.+)$", price_str)
    if match:
        serving_unit = match.group(2).strip()
        return price_str, float(match.group(1)), False, serving_unit

    # 尝试直接提取数字
    num_match = re.search(r"(\d+\.?\d*)", price_str)
    if num_match:
        return price_str, float(num_match.group(1)), False, _extract_serving_unit(price_str)

    return price_str, 0.0, False, _extract_serving_unit(price_str)


def infer_category(name: str, cooking_method: str, scene: str) -> str:
    """根据菜名、烹饪方式、场景推断分类"""
    cooking_method = cooking_method or ""
    scene = scene or ""
    name = name or ""

    # 凉菜
    if cooking_method in ("凉拌", "腌制", "冷盘") or "前菜" in scene:
        return "凉菜"

    # 汤羹
    if "羹" in name or cooking_method in ("煮/羹",):
        return "汤羹"

    # 主食
    staple_keywords = ["炒饭", "米粉", "河", "伊面", "粉丝", "飞饼", "炒面"]
    if any(kw in name for kw in staple_keywords):
        return "主食"

    # 甜品
    dessert_keywords = ["双皮奶", "糕", "酸奶", "官燕", "杨枝甘露"]
    if any(kw in name for kw in dessert_keywords):
        return "甜品"

    # 点心
    dim_sum_keywords = ["包", "酥", "饼", "饺"]
    if any(kw in name for kw in dim_sum_keywords):
        return "点心"

    # 默认热菜
    return "热菜"


def build_tags(row: dict) -> str:
    """合并标签: 食材分类|口味|烹饪方式|场景"""
    parts = []
    for field in ["食材分类", "口味标签", "烹饪方式", "场景推荐"]:
        val = row.get(field, "").strip()
        if val:
            parts.append(val)
    return "|".join(parts)


def import_dishes_from_csv(session: Session) -> int:
    """从 CSV 导入菜品数据，返回导入数量"""
    # 如果已有数据则跳过
    existing = session.exec(select(Dish)).first()
    if existing:
        return 0

    count = 0
    with open(CSV_PATH, "r", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        for row in reader:
            name = row.get("菜品名称", "").strip()
            price_raw = row.get("价格", "").strip()
            tag_col = row.get("标签", "").strip()

            # 跳过空行
            if not name:
                continue

            # 跳过宴席菜（无价格且标签为宴席）
            if tag_col == "宴席" or (not price_raw and "宴席" in row.get("待确认", "")):
                continue

            # 跳过没有价格的菜品
            if not price_raw:
                continue

            price_text, price, is_market_price, serving_unit = parse_price(price_raw)

            cooking_method = row.get("烹饪方式", "").strip()
            scene = row.get("场景推荐", "").strip()
            category = infer_category(name, cooking_method, scene)

            tags = build_tags(row)

            # 成本按品类基准 + 菜品名哈希微调，模拟真实差异
            ratio = get_category_cost_ratio(category)
            # 用菜名哈希生成 ±0.08 的浮动，让每道菜不一样
            name_hash = int(hashlib.md5(name.encode()).hexdigest()[:8], 16)
            jitter = ((name_hash % 160) - 80) / 1000  # -0.08 ~ +0.08
            cost = round(price * max(0.15, min(0.55, ratio + jitter)), 2)
            min_price = calculate_min_price(cost)

            dish = Dish(
                name=name,
                price_text=price_text,
                price=price,
                is_market_price=is_market_price,
                cost=cost,
                min_price=min_price,
                category=category,
                tags=tags,
                is_active=True,
                serving_unit=serving_unit,
                serving_split=0,
            )
            session.add(dish)
            count += 1

    session.commit()
    return count


def get_all_active_dishes(session: Session) -> list[Dish]:
    """获取所有启用的菜品"""
    return list(session.exec(select(Dish).where(Dish.is_active == True)).all())


def get_dishes_by_category(session: Session) -> dict[str, list[Dish]]:
    """按类别分组获取菜品"""
    dishes = get_all_active_dishes(session)
    grouped: dict[str, list[Dish]] = {}
    for dish in dishes:
        grouped.setdefault(dish.category, []).append(dish)
    return grouped


def _list_active_specs(session: Session, dish_id: int) -> list[DishSpec]:
    return list(session.exec(
        select(DishSpec)
        .where(DishSpec.dish_id == dish_id, DishSpec.is_active == True)
        .order_by(DishSpec.sort_order, DishSpec.id)
    ).all())


def get_default_spec(session: Session, dish_id: int) -> DishSpec | None:
    specs = _list_active_specs(session, dish_id)
    for spec in specs:
        if spec.is_default:
            return spec
    return specs[0] if specs else None


def _sync_dish_cache_from_spec(dish: Dish, spec: DishSpec) -> None:
    dish.price = round(spec.price, 2)
    dish.price_text = (spec.price_text or build_price_text(spec.price, dish.serving_unit or "例")).strip()
    dish.cost = round(spec.cost, 2)
    dish.min_price = calculate_min_price(dish.cost)
    dish.is_market_price = "时价" in dish.price_text


def _apply_default_spec(session: Session, dish: Dish, specs: list[DishSpec], chosen_id: int) -> DishSpec:
    chosen: DishSpec | None = None
    for spec in specs:
        if not (spec.price_text or "").strip():
            spec.price_text = build_price_text(spec.price, dish.serving_unit or "例")
        should_be_default = spec.id == chosen_id
        if spec.is_default != should_be_default:
            spec.is_default = should_be_default
        session.add(spec)
        if should_be_default:
            chosen = spec

    if chosen is None:
        raise ValueError("默认规格不存在")

    _sync_dish_cache_from_spec(dish, chosen)
    session.add(dish)
    return chosen


def ensure_dish_spec_consistency(
    session: Session,
    dish_id: int,
    *,
    create_default_if_missing: bool = False,
) -> DishSpec:
    dish = session.get(Dish, dish_id)
    if not dish:
        raise ValueError("菜品不存在")

    specs = _list_active_specs(session, dish_id)
    if not specs:
        if not create_default_if_missing:
            raise ValueError("至少需要保留一个规格")

        spec = DishSpec(
            dish_id=dish_id,
            spec_name="标准",
            price=round(dish.price, 2),
            price_text=(dish.price_text or build_price_text(dish.price, dish.serving_unit or "例")).strip(),
            cost=round(dish.cost, 2),
            min_people=0,
            max_people=0,
            is_default=True,
            sort_order=0,
            is_active=True,
        )
        session.add(spec)
        session.flush()
        specs = [spec]

    chosen = next((spec for spec in specs if spec.is_default), None) or specs[0]
    return _apply_default_spec(session, dish, specs, chosen.id)  # type: ignore[arg-type]


def ensure_all_dishes_have_default_specs(session: Session) -> dict[str, int]:
    summary = {
        "created_specs": 0,
        "normalized_defaults": 0,
        "synced_dishes": 0,
    }

    dishes = list(session.exec(select(Dish)).all())
    for dish in dishes:
        active_specs = _list_active_specs(session, dish.id)  # type: ignore[arg-type]
        default_ids_before = [spec.id for spec in active_specs if spec.is_default]
        if not active_specs:
            summary["created_specs"] += 1

        chosen = ensure_dish_spec_consistency(
            session,
            dish.id,  # type: ignore[arg-type]
            create_default_if_missing=True,
        )

        default_ids_after = [spec.id for spec in _list_active_specs(session, dish.id) if spec.is_default]  # type: ignore[arg-type]
        if len(default_ids_before) != 1 or default_ids_before != default_ids_after:
            summary["normalized_defaults"] += 1
        if chosen:
            summary["synced_dishes"] += 1

    return summary


# ── DishSpec CRUD ──

def list_specs(session: Session, dish_id: int) -> list[DishSpec]:
    return list(session.exec(
        select(DishSpec)
        .where(DishSpec.dish_id == dish_id)
        .order_by(DishSpec.sort_order)
    ).all())


def create_spec(session: Session, dish_id: int, **kwargs) -> DishSpec:
    dish = session.get(Dish, dish_id)
    if not dish:
        raise ValueError("菜品不存在")

    existing_specs = _list_active_specs(session, dish_id)
    price = round(float(kwargs.get("price", 0.0) or 0.0), 2)
    if price <= 0:
        raise ValueError("规格价格必须大于0")

    spec_name = (kwargs.get("spec_name") or "").strip()
    if not spec_name:
        raise ValueError("规格名称不能为空")

    cost = kwargs.get("cost")
    if cost is None:
        cost = round(price * get_category_cost_ratio(dish.category), 2)

    spec = DishSpec(
        dish_id=dish_id,
        spec_name=spec_name,
        price=price,
        price_text=(kwargs.get("price_text") or build_price_text(price, dish.serving_unit or "例")).strip(),
        cost=round(float(cost), 2),
        min_people=max(0, int(kwargs.get("min_people", 0) or 0)),
        max_people=max(0, int(kwargs.get("max_people", 0) or 0)),
        is_default=bool(kwargs.get("is_default", False)),
        sort_order=int(kwargs.get("sort_order", 0) or 0),
        is_active=True,
    )
    session.add(spec)
    session.flush()

    if not existing_specs or spec.is_default:
        _apply_default_spec(session, dish, _list_active_specs(session, dish_id), spec.id)  # type: ignore[arg-type]
    else:
        ensure_dish_spec_consistency(session, dish_id, create_default_if_missing=True)

    session.commit()
    session.refresh(spec)
    return spec


def update_spec(session: Session, spec_id: int, **kwargs) -> DishSpec:
    spec = session.get(DishSpec, spec_id)
    if not spec:
        raise ValueError("规格不存在")

    dish = session.get(Dish, spec.dish_id)
    if not dish:
        raise ValueError("菜品不存在")

    if "spec_name" in kwargs and kwargs["spec_name"] is not None:
        spec_name = str(kwargs["spec_name"]).strip()
        if not spec_name:
            raise ValueError("规格名称不能为空")
        spec.spec_name = spec_name

    if "price" in kwargs and kwargs["price"] is not None:
        price = round(float(kwargs["price"]), 2)
        if price <= 0:
            raise ValueError("规格价格必须大于0")
        spec.price = price
        if "price_text" not in kwargs:
            spec.price_text = build_price_text(price, dish.serving_unit or "例")

    if "price_text" in kwargs and kwargs["price_text"] is not None:
        spec.price_text = str(kwargs["price_text"]).strip() or build_price_text(spec.price, dish.serving_unit or "例")

    if "cost" in kwargs and kwargs["cost"] is not None:
        spec.cost = round(float(kwargs["cost"]), 2)

    if "min_people" in kwargs and kwargs["min_people"] is not None:
        spec.min_people = max(0, int(kwargs["min_people"]))
    if "max_people" in kwargs and kwargs["max_people"] is not None:
        spec.max_people = max(0, int(kwargs["max_people"]))
    if "sort_order" in kwargs and kwargs["sort_order"] is not None:
        spec.sort_order = int(kwargs["sort_order"])
    if "is_active" in kwargs and kwargs["is_active"] is not None:
        if not kwargs["is_active"] and len(_list_active_specs(session, spec.dish_id)) <= 1 and spec.is_active:
            raise ValueError("至少需要保留一个规格")
        spec.is_active = bool(kwargs["is_active"])
    if "is_default" in kwargs and kwargs["is_default"] is not None:
        spec.is_default = bool(kwargs["is_default"])

    session.add(spec)
    session.flush()

    active_specs = _list_active_specs(session, spec.dish_id)
    if not active_specs:
        raise ValueError("至少需要保留一个规格")

    if spec.is_active and kwargs.get("is_default") is True:
        _apply_default_spec(session, dish, active_specs, spec.id)  # type: ignore[arg-type]
    else:
        ensure_dish_spec_consistency(session, spec.dish_id, create_default_if_missing=False)

    session.commit()
    session.refresh(spec)
    return spec


def delete_spec(session: Session, spec_id: int) -> None:
    spec = session.get(DishSpec, spec_id)
    if not spec:
        raise ValueError("规格不存在")
    active_specs = _list_active_specs(session, spec.dish_id)
    if len(active_specs) <= 1:
        raise ValueError("至少需要保留一个规格")
    session.delete(spec)
    session.flush()
    ensure_dish_spec_consistency(session, spec.dish_id, create_default_if_missing=False)
    session.commit()
