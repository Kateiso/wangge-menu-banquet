from sqlmodel import SQLModel, Session, create_engine, select

from backend.models.dish import Dish
from backend.models.dish_spec import DishSpec
from backend.scripts.sync_real_dishes import (
    apply_sync_plan,
    build_sync_plan,
    compute_compat_min_price,
    extract_spec_name,
)


def _make_engine():
    return create_engine("sqlite://")


def _seed_base_data(session: Session):
    session.add(
        Dish(
            id=1,
            name="白切清远鸡",
            price_text="109元/半只",
            price=109.0,
            cost=43.82,
            min_price=56.97,
            category="热菜",
            is_active=True,
        )
    )
    session.add(
        Dish(
            id=2,
            name="小青龙炒鲜奶",
            price_text="时价(参考0元)/例",
            price=78.0,
            cost=27.3,
            min_price=35.49,
            category="热菜",
            is_market_price=True,
            is_active=True,
        )
    )
    session.add(
        Dish(
            id=3,
            name="顺德家乡炒双脆",
            price_text="68元/例",
            price=68.0,
            cost=20.0,
            min_price=26.0,
            category="热菜",
            is_active=True,
        )
    )
    session.add(
        DishSpec(
            id=101,
            dish_id=1,
            spec_name="例牌",
            price_text="109元/半只",
            price=109.0,
            cost=43.82,
            min_people=1,
            max_people=999,
            is_default=True,
            sort_order=0,
            is_active=True,
        )
    )
    session.add(
        DishSpec(
            id=201,
            dish_id=2,
            spec_name="例牌",
            price_text="时价(参考0元)/例",
            price=78.0,
            cost=27.3,
            min_people=1,
            max_people=999,
            is_default=True,
            sort_order=0,
            is_active=True,
        )
    )
    session.add(
        DishSpec(
            id=301,
            dish_id=3,
            spec_name="例牌",
            price_text="68元/例",
            price=68.0,
            cost=20.0,
            min_people=1,
            max_people=999,
            is_default=True,
            sort_order=0,
            is_active=True,
        )
    )
    session.commit()


def test_extract_spec_name_from_price_text():
    assert extract_spec_name("216元/只") == "只"
    assert extract_spec_name("46元/打") == "打"
    assert extract_spec_name("时价(参考0元)/例") == "例"
    assert extract_spec_name("") == "标准"


def test_build_sync_plan_rebuilds_multi_specs_and_flags_market_zero():
    engine = _make_engine()
    SQLModel.metadata.create_all(engine)
    snapshot = {
        "dishes": [
            {
                "id": 1,
                "name": "白切清远鸡",
                "price_text": "109元/半只",
                "price": 109.0,
                "cost": 40.0,
                "is_market_price": False,
                "is_active": True,
                "specs": [
                    {"price_text": "109元/半只", "price": 109.0, "cost": 40.0, "is_active": True},
                    {"price_text": "216元/只", "price": 216.0, "cost": 80.0, "is_active": True},
                ],
            },
            {
                "id": 2,
                "name": "小青龙炒鲜奶",
                "price_text": "时价(参考0元)/例",
                "price": 0.0,
                "cost": 0.0,
                "is_market_price": True,
                "is_active": True,
                "specs": [
                    {"price_text": "时价(参考0元)/例", "price": 0.0, "cost": 0.0, "is_active": True},
                ],
            },
        ]
    }

    with Session(engine) as session:
        _seed_base_data(session)
        plans, report = build_sync_plan(session, snapshot)

    assert report["matched_dishes"] == 2
    assert report["market_zero_names"] == ["小青龙炒鲜奶"]
    assert report["rebuild_spec_dish_names"] == ["白切清远鸡"]
    chicken_plan = next(plan for plan in plans if plan.name == "白切清远鸡")
    assert chicken_plan.spec_mode == "rebuild"
    assert [spec.fields["spec_name"] for spec in chicken_plan.spec_plans] == ["半只", "只"]


def test_apply_sync_plan_updates_single_spec_and_rebuilds_multi_specs():
    engine = _make_engine()
    SQLModel.metadata.create_all(engine)
    snapshot = {
        "dishes": [
            {
                "id": 1,
                "name": "白切清远鸡",
                "price_text": "109元/半只",
                "price": 109.0,
                "cost": 40.0,
                "is_market_price": False,
                "is_active": True,
                "specs": [
                    {"price_text": "109元/半只", "price": 109.0, "cost": 40.0, "is_active": True},
                    {"price_text": "216元/只", "price": 216.0, "cost": 80.0, "is_active": True},
                ],
            },
            {
                "id": 2,
                "name": "小青龙炒鲜奶",
                "price_text": "时价(参考0元)/例",
                "price": 0.0,
                "cost": 0.0,
                "is_market_price": True,
                "is_active": True,
                "specs": [
                    {"price_text": "时价(参考0元)/例", "price": 0.0, "cost": 0.0, "is_active": True},
                ],
            },
            {
                "id": 3,
                "name": "顺德家乡炒双脆",
                "price_text": "68元/例",
                "price": 68.0,
                "cost": 27.0,
                "is_market_price": False,
                "is_active": True,
                "specs": [
                    {"price_text": "68元/例", "price": 68.0, "cost": 27.0, "is_active": True},
                ],
            },
        ]
    }

    with Session(engine) as session:
        _seed_base_data(session)
        plans, _ = build_sync_plan(session, snapshot)
        stats = apply_sync_plan(session, plans)

        chicken_specs = list(session.exec(select(DishSpec).where(DishSpec.dish_id == 1).order_by(DishSpec.sort_order)).all())
        market_dish = session.get(Dish, 2)
        normal_spec = session.get(DishSpec, 301)

    assert stats["updated_dishes"] == 3
    assert stats["created_specs"] == 2
    assert stats["deleted_specs"] == 1
    assert [spec.spec_name for spec in chicken_specs] == ["半只", "只"]
    assert market_dish.price == 0.0
    assert market_dish.cost == 0.0
    assert market_dish.min_price == 0.0
    assert normal_spec.cost == 27.0
    assert compute_compat_min_price(27.0) == 35.1
