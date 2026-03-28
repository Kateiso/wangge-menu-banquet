import pytest
from fastapi.testclient import TestClient
from sqlmodel import SQLModel, Session


@pytest.fixture(scope="session", autouse=True)
def setup_test_db():
    import backend.config as cfg

    cfg.DATABASE_URL = "sqlite://"
    cfg.APP_PASSWORD = "test_not_used"

    from backend.main import app, engine  # noqa: F401

    yield engine


def _seed_base_data(engine) -> None:
    from backend.models.user import User, hash_password
    from backend.models.dish import Dish

    SQLModel.metadata.drop_all(engine)
    SQLModel.metadata.create_all(engine)

    with Session(engine) as session:
        session.add(User(username="admin", password_hash=hash_password("wangge2026"), role="admin"))
        session.add(Dish(id=1, name="白灼虾", price_text="128元/例", price=128.0, cost=48.64, category="热菜", is_active=True))
        session.add(Dish(id=2, name="皮蛋豆腐", price_text="38元/例", price=38.0, cost=10.64, category="凉菜", is_active=True))
        session.commit()


@pytest.fixture()
def client(setup_test_db):
    from backend.main import app, engine

    _seed_base_data(engine)

    with TestClient(app) as test_client:
        yield test_client


def _login(client: TestClient) -> str:
    res = client.post("/api/auth/login", json={"username": "admin", "password": "wangge2026"})
    assert res.status_code == 200
    return res.json()["token"]


def _auth_header(token: str) -> dict[str, str]:
    return {"Authorization": f"Bearer {token}"}


def _create_group_with_package():
    from backend.main import engine
    from backend.models.package import PackageGroup, Package, PackageItem

    with Session(engine) as session:
        group = PackageGroup(name="宴席", sort_order=1, is_active=True)
        empty_group = PackageGroup(name="空分组", sort_order=2, is_active=True)
        session.add(group)
        session.add(empty_group)
        session.flush()

        package = Package(
            group_id=group.id,
            name="金牌套餐",
            description="测试定价继承",
            base_price=888.0,
            default_pricing_mode="fixed",
            dish_count=2,
            is_active=True,
            created_by="admin",
        )
        session.add(package)
        session.flush()

        session.add(PackageItem(package_id=package.id, dish_id=1, default_quantity=1, sort_order=1))
        session.add(PackageItem(package_id=package.id, dish_id=2, default_quantity=2, sort_order=2))
        session.commit()

        return {
            "group_id": group.id,
            "empty_group_id": empty_group.id,
            "package_id": package.id,
        }


def test_create_menu_from_package_preserves_base_price_for_additive_mode(client: TestClient):
    token = _login(client)
    ids = _create_group_with_package()

    res = client.post(
        "/api/menu/from-package",
        json={
            "customer_name": "陈先生",
            "date": "2026-03-20",
            "party_size": 10,
            "table_count": 2,
            "package_id": ids["package_id"],
            "pricing_mode": "additive",
        },
        headers=_auth_header(token),
    )

    assert res.status_code == 200
    data = res.json()
    assert data["pricing_mode"] == "additive"
    assert data["fixed_price"] == 888.0
    assert data["total_price"] == 204.0
    assert data["budget"] == 204.0


def test_switch_pricing_mode_uses_inherited_fixed_price(client: TestClient):
    token = _login(client)
    ids = _create_group_with_package()

    created = client.post(
        "/api/menu/from-package",
        json={
            "customer_name": "陈先生",
            "date": "2026-03-20",
            "party_size": 10,
            "table_count": 2,
            "package_id": ids["package_id"],
            "pricing_mode": "additive",
        },
        headers=_auth_header(token),
    )
    assert created.status_code == 200
    menu_id = created.json()["id"]

    fixed_res = client.put(
        f"/api/menu/{menu_id}/pricing",
        json={"pricing_mode": "fixed"},
        headers=_auth_header(token),
    )

    assert fixed_res.status_code == 200
    fixed_data = fixed_res.json()
    assert fixed_data["pricing_mode"] == "fixed"
    assert fixed_data["fixed_price"] == 888.0
    assert fixed_data["total_price"] == 1776.0
    assert fixed_data["budget"] == 1776.0

    additive_res = client.put(
        f"/api/menu/{menu_id}/pricing",
        json={"pricing_mode": "additive"},
        headers=_auth_header(token),
    )

    assert additive_res.status_code == 200
    additive_data = additive_res.json()
    assert additive_data["pricing_mode"] == "additive"
    assert additive_data["fixed_price"] == 888.0
    assert additive_data["total_price"] == 204.0
    assert [item["subtotal"] for item in additive_data["items"]] == [128.0, 76.0]


def test_fixed_mode_distribution_persists_item_prices(client: TestClient):
    token = _login(client)
    ids = _create_group_with_package()

    created = client.post(
        "/api/menu/from-package",
        json={
            "customer_name": "李先生",
            "date": "2026-03-20",
            "party_size": 10,
            "table_count": 2,
            "package_id": ids["package_id"],
            "pricing_mode": "fixed",
        },
        headers=_auth_header(token),
    )
    assert created.status_code == 200
    data = created.json()
    assert data["total_price"] == 1776.0
    assert sum(item["subtotal"] for item in data["items"]) == 888.0
    assert data["items"][0]["adjusted_price"] == 557.18
    assert data["items"][0]["subtotal"] == 557.18
    assert data["items"][1]["adjusted_price"] == 165.41
    assert data["items"][1]["subtotal"] == 330.82


def test_package_override_price_takes_priority_when_building_menu(client: TestClient):
    token = _login(client)
    ids = _create_group_with_package()

    update_item = client.put(
        "/api/packages/items/1",
        json={"override_price": 200.0},
        headers=_auth_header(token),
    )
    assert update_item.status_code == 200

    detail = client.get(f"/api/packages/{ids['package_id']}", headers=_auth_header(token))
    assert detail.status_code == 200
    detail_data = detail.json()
    assert detail_data["items"][0]["override_price"] == 200.0
    assert detail_data["items"][0]["price"] == 200.0

    created = client.post(
        "/api/menu/from-package",
        json={
            "customer_name": "周先生",
            "date": "2026-03-20",
            "party_size": 10,
            "table_count": 1,
            "package_id": ids["package_id"],
            "pricing_mode": "additive",
        },
        headers=_auth_header(token),
    )
    assert created.status_code == 200
    menu = created.json()
    assert menu["total_price"] == 276.0
    assert menu["items"][0]["additive_price"] == 200.0
    assert menu["items"][0]["adjusted_price"] == 200.0
    assert menu["items"][0]["price"] == 128.0


def test_delete_group_only_allows_empty_group(client: TestClient):
    token = _login(client)
    ids = _create_group_with_package()

    non_empty_res = client.delete(
        f"/api/packages/groups/{ids['group_id']}",
        headers=_auth_header(token),
    )
    assert non_empty_res.status_code == 400
    assert non_empty_res.json()["detail"] == "分组下仍有套餐，请先清空后再删除"

    empty_res = client.delete(
        f"/api/packages/groups/{ids['empty_group_id']}",
        headers=_auth_header(token),
    )
    assert empty_res.status_code == 204
