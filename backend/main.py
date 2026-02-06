import logging
from contextlib import asynccontextmanager
from fastapi import FastAPI, Request, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse, JSONResponse
from sqlmodel import SQLModel, Session, create_engine
from backend.config import DATABASE_URL, APP_PASSWORD
from backend.models.dish import Dish  # noqa: F401 - needed for table creation
from backend.models.menu import Menu, MenuItem  # noqa: F401
from backend.services.dish_service import import_dishes_from_csv
from backend.routers.menu import router as menu_router

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

engine = create_engine(DATABASE_URL, echo=False)


@asynccontextmanager
async def lifespan(app: FastAPI):
    # 启动时创建表并导入 CSV
    SQLModel.metadata.create_all(engine)
    with Session(engine) as session:
        count = import_dishes_from_csv(session)
        if count > 0:
            logger.info(f"已导入 {count} 道菜品")
        else:
            logger.info("菜品数据已存在，跳过导入")
    yield


app = FastAPI(title="旺阁渔村 AI 点菜系统", lifespan=lifespan)

# CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# 密码认证中间件
@app.middleware("http")
async def auth_middleware(request: Request, call_next):
    # 放行静态文件和认证接口
    path = request.url.path
    if (
        path == "/api/auth"
        or path == "/"
        or path.startswith("/assets")
        or path.endswith(".js")
        or path.endswith(".css")
        or path.endswith(".ico")
        or path.endswith(".svg")
        or path.endswith(".png")
        or not path.startswith("/api")
    ):
        return await call_next(request)

    # 检查 Authorization header
    auth = request.headers.get("Authorization", "")
    if auth != f"Bearer {APP_PASSWORD}":
        return JSONResponse(status_code=401, content={"detail": "未授权"})

    return await call_next(request)


# 认证接口
@app.post("/api/auth")
async def auth(request: Request):
    body = await request.json()
    password = body.get("password", "")
    if password == APP_PASSWORD:
        return {"success": True, "token": APP_PASSWORD}
    raise HTTPException(status_code=401, detail="密码错误")


# API 路由
app.include_router(menu_router)

# 前端静态文件（生产环境）
import os
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
