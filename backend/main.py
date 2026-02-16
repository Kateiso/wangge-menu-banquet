import logging
import os
import threading
import time
from contextlib import asynccontextmanager
from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse, JSONResponse
from sqlmodel import SQLModel, Session
from backend.database import engine
from backend.config import ALLOWED_ORIGINS, RATE_LIMIT_PER_MINUTE
from backend.models.dish import Dish  # noqa: F401
from backend.models.menu import Menu, MenuItem  # noqa: F401
from backend.models.conversation import MenuConversation  # noqa: F401
from backend.models.user import User, create_default_users  # noqa: F401
from backend.services.dish_service import import_dishes_from_csv
from backend.routers.menu import router as menu_router
from backend.routers.auth import router as auth_router
from backend.routers.dish import router as dish_router

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    # 启动时创建表并导入 CSV + 初始化用户
    SQLModel.metadata.create_all(engine)
    with Session(engine) as session:
        # 导入菜品
        count = import_dishes_from_csv(session)
        if count > 0:
            logger.info(f"已导入 {count} 道菜品")
        else:
            logger.info("菜品数据已存在或无需导入")
        
        # 初始化默认用户
        create_default_users(session)
        
    yield


app = FastAPI(title="旺阁渔村 AI 点菜系统", lifespan=lifespan)

# CORS
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


# API 路由
app.include_router(auth_router)
app.include_router(dish_router)
app.include_router(menu_router)

# 前端静态文件（生产环境）
frontend_dist = os.path.join(os.path.dirname(__file__), "..", "frontend", "dist")
if os.path.exists(frontend_dist):
    # 静态资源
    assets_dir = os.path.join(frontend_dist, "assets")
    if os.path.exists(assets_dir):
        app.mount("/assets", StaticFiles(directory=assets_dir), name="assets")

    # SPA fallback - 放在最后，通过中间件实现而非 catch-all 路由
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
