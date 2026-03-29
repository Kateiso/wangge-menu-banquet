"""
Comprehensive tests for Auth (RBAC) and Dish Management features.

Run with:
    cd /Users/kateiso_cao/Desktop/旺阁渔村_点菜系统开发
    source .venv/bin/activate
    python -m pytest backend/tests/test_auth_and_dishes.py -v

These tests use FastAPI's TestClient (no real server needed).
A fresh in-memory SQLite database is used per test session.
"""

import pytest
from fastapi.testclient import TestClient
from sqlmodel import SQLModel, Session, create_engine


# ── Fixtures ──────────────────────────────────────────────────────────────────


@pytest.fixture(scope="session", autouse=True)
def setup_test_db():
    """Override database to use in-memory SQLite for all tests."""
    import backend.config as cfg
    cfg.DATABASE_URL = "sqlite://"          # in-memory
    cfg.APP_PASSWORD = "test_not_used"      # legacy field; no longer drives auth

    # Must import app AFTER config override so engine uses in-memory DB
    from backend.main import app, engine     # noqa: F811
    SQLModel.metadata.create_all(engine)

    # Seed default users (mirrors lifespan logic)
    from backend.models.user import User, hash_password
    with Session(engine) as session:
        if not session.get(User, "admin"):
            session.add(User(username="admin", password_hash=hash_password("wangge2026"), role="admin"))
            session.add(User(username="chef", password_hash=hash_password("chef123"), role="staff"))
            session.commit()

    # Seed a few dishes for testing
    from backend.models.dish import Dish
    with Session(engine) as session:
        if not session.get(Dish, 1):
            session.add(Dish(id=1, name="白灼虾", price_text="128元/例", price=128.0, cost=48.64, category="热菜", is_active=True))
        if not session.get(Dish, 2):
            session.add(Dish(id=2, name="蒜蓉蒸扇贝", price_text="68元/例", price=68.0, cost=25.84, category="热菜", is_active=True))
        if not session.get(Dish, 3):
            session.add(Dish(id=3, name="皮蛋豆腐", price_text="38元/例", price=38.0, cost=10.64, category="凉菜", is_active=True))
        if not session.get(Dish, 4):
            session.add(Dish(id=4, name="杨枝甘露", price_text="28元/例", price=28.0, cost=8.96, category="甜品", is_active=False))
        session.commit()

    yield engine


@pytest.fixture()
def client(setup_test_db):
    from backend.main import app
    with TestClient(app) as test_client:
        yield test_client


def _login(client: TestClient, username: str, password: str) -> str | None:
    """Helper: login and return JWT token, or None on failure."""
    res = client.post("/api/auth/login", json={"username": username, "password": password})
    if res.status_code == 200:
        return res.json()["token"]
    return None


def _auth_header(token: str) -> dict:
    return {"Authorization": f"Bearer {token}"}


# ══════════════════════════════════════════════════════════════════════════════
# 1. AUTH TESTS
# ══════════════════════════════════════════════════════════════════════════════


class TestAuth:
    """Test login, token validation, and user info retrieval."""

    def test_login_admin_success(self, client):
        """Admin can login with correct credentials."""
        res = client.post("/api/auth/login", json={"username": "admin", "password": "wangge2026"})
        assert res.status_code == 200
        data = res.json()
        assert "token" in data
        assert data["role"] == "admin"
        assert data["username"] == "admin"

    def test_login_staff_success(self, client):
        """Staff (chef) can login with correct credentials."""
        res = client.post("/api/auth/login", json={"username": "chef", "password": "chef123"})
        assert res.status_code == 200
        data = res.json()
        assert data["role"] == "staff"

    def test_login_wrong_password(self, client):
        """Wrong password returns 401."""
        res = client.post("/api/auth/login", json={"username": "admin", "password": "wrong"})
        assert res.status_code == 401

    def test_login_nonexistent_user(self, client):
        """Non-existent user returns 401."""
        res = client.post("/api/auth/login", json={"username": "ghost", "password": "any"})
        assert res.status_code == 401

    def test_me_with_valid_token(self, client):
        """GET /api/auth/me returns user info for valid token."""
        token = _login(client, "admin", "wangge2026")
        res = client.get("/api/auth/me", headers=_auth_header(token))
        assert res.status_code == 200
        data = res.json()
        assert data["username"] == "admin"
        assert data["role"] == "admin"

    def test_me_without_token(self, client):
        """GET /api/auth/me returns 401 without token."""
        res = client.get("/api/auth/me")
        assert res.status_code == 401

    def test_me_with_invalid_token(self, client):
        """GET /api/auth/me returns 401 with garbage token."""
        res = client.get("/api/auth/me", headers={"Authorization": "Bearer invalid.token.here"})
        assert res.status_code == 401


# ══════════════════════════════════════════════════════════════════════════════
# 2. DISH LISTING TESTS
# ══════════════════════════════════════════════════════════════════════════════


class TestDishList:
    """Test GET /api/dishes — listing and filtering."""

    def test_list_dishes_requires_auth(self, client):
        """Unauthenticated request returns 401."""
        res = client.get("/api/dishes")
        assert res.status_code == 401

    def test_list_all_dishes_as_admin(self, client):
        """Admin can list all dishes (including inactive)."""
        token = _login(client, "admin", "wangge2026")
        res = client.get("/api/dishes", headers=_auth_header(token))
        assert res.status_code == 200
        dishes = res.json()
        assert isinstance(dishes, list)
        assert len(dishes) >= 4  # we seeded 4

    def test_list_all_dishes_as_staff(self, client):
        """Staff can also list all dishes."""
        token = _login(client, "chef", "chef123")
        res = client.get("/api/dishes", headers=_auth_header(token))
        assert res.status_code == 200

    def test_filter_by_category(self, client):
        """Filter dishes by category query param."""
        token = _login(client, "admin", "wangge2026")
        res = client.get("/api/dishes?category=凉菜", headers=_auth_header(token))
        assert res.status_code == 200
        dishes = res.json()
        assert all(d["category"] == "凉菜" for d in dishes)

    def test_filter_by_active_status(self, client):
        """Filter active-only dishes."""
        token = _login(client, "admin", "wangge2026")
        res = client.get("/api/dishes?active_only=true", headers=_auth_header(token))
        assert res.status_code == 200
        dishes = res.json()
        assert all(d["is_active"] for d in dishes)


# ══════════════════════════════════════════════════════════════════════════════
# 2.5 DISH CREATE TESTS
# ══════════════════════════════════════════════════════════════════════════════


class TestDishCreate:
    """Test POST /api/dishes create endpoint with RBAC and derived fields."""

    def test_admin_can_create_dish(self, client):
        token = _login(client, "admin", "wangge2026")
        payload = {
            "name": "椒盐九肚鱼",
            "category": "热菜",
            "default_spec_name": "标准",
            "default_spec_price": 128.0,
            "default_spec_cost": 52.0,
            "serving_unit": "例",
            "serving_split": 0,
            "is_signature": True,
            "is_must_order": False,
        }
        res = client.post("/api/dishes", json=payload, headers=_auth_header(token))
        assert res.status_code == 201
        data = res.json()
        assert data["name"] == payload["name"]
        assert data["category"] == payload["category"]
        assert data["cost"] == 52.0
        assert data["price"] == 128.0
        assert data["min_price"] == 67.6
        assert data["is_active"] is True

        specs = client.get(f"/api/dishes/{data['id']}/specs", headers=_auth_header(token))
        assert specs.status_code == 200
        specs_data = specs.json()
        assert len(specs_data) == 1
        assert specs_data[0]["spec_name"] == "标准"
        assert specs_data[0]["is_default"] is True

    def test_staff_cannot_create_dish(self, client):
        token = _login(client, "chef", "chef123")
        res = client.post(
            "/api/dishes",
            json={"name": "新菜", "category": "凉菜", "default_spec_price": 68.0},
            headers=_auth_header(token),
        )
        assert res.status_code == 403

    def test_create_requires_auth(self, client):
        res = client.post(
            "/api/dishes",
            json={"name": "无权限菜", "category": "凉菜", "default_spec_price": 68.0},
        )
        assert res.status_code == 401


# ══════════════════════════════════════════════════════════════════════════════
# 3. DISH UPDATE — PERMISSION TESTS
# ══════════════════════════════════════════════════════════════════════════════


class TestDishUpdatePermissions:
    """Test PUT /api/dishes/{id} with role-based restrictions."""

    # ── Admin: can modify everything ────────────────────────────────────────

    def test_admin_cannot_update_cost_from_dish(self, client):
        """Cost must be maintained on spec rows, not on dish."""
        token = _login(client, "admin", "wangge2026")
        res = client.put("/api/dishes/1", json={"cost": 55.0}, headers=_auth_header(token))
        assert res.status_code == 400
        assert res.json()["detail"] == "菜品价格和成本请在规格中维护"

    def test_admin_can_toggle_active(self, client):
        """Admin can toggle dish active status."""
        token = _login(client, "admin", "wangge2026")
        res = client.put("/api/dishes/1", json={"is_active": False}, headers=_auth_header(token))
        assert res.status_code == 200
        assert res.json()["is_active"] is False
        # restore
        client.put("/api/dishes/1", json={"is_active": True}, headers=_auth_header(token))

    def test_admin_cannot_update_price_from_dish(self, client):
        """Price must be maintained on spec rows, not on dish."""
        token = _login(client, "admin", "wangge2026")
        res = client.put("/api/dishes/1", json={"price": 138.0, "price_text": "138元/例"}, headers=_auth_header(token))
        assert res.status_code == 400
        assert res.json()["detail"] == "菜品价格和成本请在规格中维护"

    def test_admin_cannot_update_price_or_cost_from_dish_when_active_specs_exist(self, client):
        """Dish-level price/cost updates are rejected consistently."""
        token = _login(client, "admin", "wangge2026")

        res = client.put(
            "/api/dishes/1",
            json={"cost": 55.0, "price": 138.0, "price_text": "138元/例"},
            headers=_auth_header(token),
        )
        assert res.status_code == 400
        assert res.json()["detail"] == "菜品价格和成本请在规格中维护"

    def test_admin_can_update_dish_metadata(self, client):
        """Dish master data remains editable."""
        token = _login(client, "admin", "wangge2026")
        res = client.put(
            "/api/dishes/1",
            json={"name": "白灼虾（招牌）", "category": "热菜", "serving_unit": "份"},
            headers=_auth_header(token),
        )
        assert res.status_code == 200
        data = res.json()
        assert data["name"] == "白灼虾（招牌）"
        assert data["serving_unit"] == "份"

    # ── Staff: can only toggle is_active ────────────────────────────────────

    def test_staff_can_toggle_active(self, client):
        """Staff can toggle dish active status (on/off shelf)."""
        token = _login(client, "chef", "chef123")
        res = client.put("/api/dishes/3", json={"is_active": False}, headers=_auth_header(token))
        assert res.status_code == 200
        assert res.json()["is_active"] is False
        # restore
        admin_token = _login(client, "admin", "wangge2026")
        client.put("/api/dishes/3", json={"is_active": True}, headers=_auth_header(admin_token))

    def test_staff_cannot_update_cost(self, client):
        """Staff trying to change cost gets 403."""
        token = _login(client, "chef", "chef123")
        res = client.put("/api/dishes/1", json={"cost": 99.0}, headers=_auth_header(token))
        assert res.status_code == 403

    def test_staff_cannot_update_price(self, client):
        """Staff trying to change price gets 403."""
        token = _login(client, "chef", "chef123")
        res = client.put("/api/dishes/1", json={"price": 200.0}, headers=_auth_header(token))
        assert res.status_code == 403

    # ── Edge cases ──────────────────────────────────────────────────────────

    def test_update_nonexistent_dish(self, client):
        """Updating non-existent dish returns 404."""
        token = _login(client, "admin", "wangge2026")
        res = client.put("/api/dishes/9999", json={"cost": 10.0}, headers=_auth_header(token))
        assert res.status_code == 404

    def test_update_requires_auth(self, client):
        """Unauthenticated update returns 401."""
        res = client.put("/api/dishes/1", json={"cost": 10.0})
        assert res.status_code == 401


# ══════════════════════════════════════════════════════════════════════════════
# 4. DATA PERSISTENCE TESTS
# ══════════════════════════════════════════════════════════════════════════════


class TestDataPersistence:
    """Verify that changes via API persist correctly."""

    def test_spec_change_persists_in_dish_listing_cache(self, client):
        """Updating the default spec should sync dish cache fields."""
        token = _login(client, "admin", "wangge2026")
        specs = client.get("/api/dishes/2/specs", headers=_auth_header(token))
        assert specs.status_code == 200
        spec_id = specs.json()[0]["id"]

        updated = client.put(
            f"/api/dishes/specs/{spec_id}",
            json={"price": 58.0, "cost": 18.5, "is_default": True},
            headers=_auth_header(token),
        )
        assert updated.status_code == 200

        res = client.get("/api/dishes", headers=_auth_header(token))
        dish2 = next(d for d in res.json() if d["id"] == 2)
        assert dish2["price"] == 58.0
        assert dish2["cost"] == 18.5

    def test_deactivated_dish_excluded_from_active_filter(self, client):
        """Deactivated dish is excluded when active_only filter is used."""
        token = _login(client, "admin", "wangge2026")
        # Deactivate dish 2
        client.put("/api/dishes/2", json={"is_active": False}, headers=_auth_header(token))
        # Active-only list should not contain dish 2
        res = client.get("/api/dishes?active_only=true", headers=_auth_header(token))
        ids = [d["id"] for d in res.json()]
        assert 2 not in ids
        # Restore
        client.put("/api/dishes/2", json={"is_active": True}, headers=_auth_header(token))


# ══════════════════════════════════════════════════════════════════════════════
# 5. BACKWARD COMPATIBILITY — EXISTING MENU API
# ══════════════════════════════════════════════════════════════════════════════


class TestBackwardCompatibility:
    """Ensure existing menu endpoints still work with the new auth system."""

    def test_menu_generate_still_requires_auth(self, client):
        """POST /api/menu/generate still returns 401 without token."""
        res = client.post("/api/menu/generate", json={
            "party_size": 10, "budget": 3000, "target_margin": 55,
        })
        assert res.status_code == 401

    def test_menu_generate_works_with_new_token(self, client):
        """POST /api/menu/generate accepts JWT token from new auth.
        Note: this will fail with 500 if DeepSeek key is invalid,
        but should NOT return 401 — that proves auth works.
        """
        token = _login(client, "admin", "wangge2026")
        res = client.post("/api/menu/generate", json={
            "party_size": 10, "budget": 3000, "target_margin": 55,
        }, headers=_auth_header(token))
        # Should not be 401 (auth passed); 500 is OK (LLM key may not work in test)
        assert res.status_code != 401


# ══════════════════════════════════════════════════════════════════════════════
# 6. BATCH SPECS TESTS
# ══════════════════════════════════════════════════════════════════════════════


@pytest.fixture()
def auth_headers(client):
    token = _login(client, "admin", "wangge2026")
    return _auth_header(token)


def test_batch_specs_returns_dict_keyed_by_dish_id(client, auth_headers):
    """GET /api/dishes/specs/batch?dish_ids=1,2 returns {dish_id: [specs]} mapping"""
    res = client.get("/api/dishes/specs/batch?dish_ids=1,2", headers=auth_headers)
    assert res.status_code == 200
    data = res.json()
    assert isinstance(data, dict)
    for key in data:
        assert isinstance(data[key], list)


def test_startup_backfills_standard_spec_for_seeded_dishes(client, auth_headers):
    """Startup should backfill a single default spec for legacy dish rows."""
    res = client.get("/api/dishes/1/specs", headers=auth_headers)
    assert res.status_code == 200
    specs = res.json()
    assert len(specs) == 1
    assert specs[0]["spec_name"] == "标准"
    assert specs[0]["is_default"] is True


def test_cannot_delete_last_spec(client, auth_headers):
    """A dish must always keep at least one active spec."""
    specs = client.get("/api/dishes/1/specs", headers=auth_headers)
    assert specs.status_code == 200
    spec_id = specs.json()[0]["id"]

    res = client.delete(f"/api/dishes/specs/{spec_id}", headers=auth_headers)
    assert res.status_code == 400
    assert res.json()["detail"] == "至少需要保留一个规格"
