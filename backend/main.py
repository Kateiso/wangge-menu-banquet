import logging
import os
import threading
import time
from contextlib import asynccontextmanager
from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse, JSONResponse
from fastapi.staticfiles import StaticFiles
from sqlmodel import SQLModel, Session
from backend.database import engine
from backend.config import ALLOWED_ORIGINS, RATE_LIMIT_PER_MINUTE
from backend.models.dish import Dish  # noqa: F401
from backend.models.dish_spec import DishSpec  # noqa: F401
from backend.models.menu import Menu, MenuItem  # noqa: F401
from backend.models.package import PackageGroup, Package, PackageItem  # noqa: F401
from backend.models.conversation import MenuConversation  # noqa: F401
from backend.models.user import User, create_default_users  # noqa: F401
from backend.services.dish_service import import_dishes_from_csv, ensure_all_dishes_have_default_specs
from backend.db_migrations import run_sqlite_compat_migrations
from backend.routers.menu import router as menu_router
from backend.routers.auth import router as auth_router
from backend.routers.dish import router as dish_router
from backend.routers.package import router as package_router

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    # 启动时创建表并导入 CSV + 初始化用户
    SQLModel.metadata.create_all(engine)
    run_sqlite_compat_migrations(engine)

    with Session(engine) as session:
        count = import_dishes_from_csv(session)
        if count > 0:
            logger.info(f"已导入 {count} 道菜品")
        else:
            logger.info("菜品数据已存在或无需导入")

        spec_summary = ensure_all_dishes_have_default_specs(session)
        session.commit()
        logger.info(
            "规格一致性检查完成: 新建标准规格 %s 条, 修正默认规格 %s 条",
            spec_summary["created_specs"],
            spec_summary["normalized_defaults"],
        )

        create_default_users(session)

    yield


app = FastAPI(title="旺阁渔村 AI 点菜系统", lifespan=lifespan)

app.add_middleware(
    CORSMiddleware,
    allow_origins=ALLOWED_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

_rate_lock = threading.Lock()
_request_buckets: dict[str, list[float]] = {}


def _client_ip(request: Request) -> str:
    xff = request.headers.get("x-forwarded-for", "")
    if xff:
        return xff.split(",")[0].strip()
    return request.client.host if request.client else "unknown"


@app.middleware("http")
async def rate_limit_middleware(request: Request, call_next):
    if os.getenv("PYTEST_CURRENT_TEST") or RATE_LIMIT_PER_MINUTE <= 0:
        return await call_next(request)

    path = request.url.path
    if path.startswith("/api") and path != "/api/health":
        now = time.time()
        ip = _client_ip(request)
        with _rate_lock:
            bucket = _request_buckets.setdefault(ip, [])
            window_start = now - 60
            bucket[:] = [ts for ts in bucket if ts >= window_start]
            if len(bucket) >= RATE_LIMIT_PER_MINUTE:
                return JSONResponse(status_code=429, content={"detail": "请求过于频繁，请稍后再试"})
            bucket.append(now)
    return await call_next(request)


@app.get("/api/health")
async def health():
    return {"status": "ok"}


app.include_router(auth_router)
app.include_router(dish_router)
app.include_router(menu_router)
app.include_router(package_router)

frontend_dist = os.path.join(os.path.dirname(__file__), "..", "frontend", "dist")
if os.path.exists(frontend_dist):
    assets_dir = os.path.join(frontend_dist, "assets")
    if os.path.exists(assets_dir):
        app.mount("/assets", StaticFiles(directory=assets_dir), name="assets")

    from starlette.middleware.base import BaseHTTPMiddleware

    class SPAMiddleware(BaseHTTPMiddleware):
        async def dispatch(self, request: Request, call_next):
            response = await call_next(request)
            if (
                response.status_code == 404
                and not request.url.path.startswith("/api")
                and "." not in request.url.path.split("/")[-1]
            ):
                return FileResponse(os.path.join(frontend_dist, "index.html"))
            return response

    app.add_middleware(SPAMiddleware)
