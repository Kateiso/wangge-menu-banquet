# AGENTS.md (Project Handover - Minimal)

## 1) 项目定位
- 项目：旺阁渔村 AI 点菜系统（FastAPI + React）。
- 当前工作目录：`/Users/kateiso_cao/Desktop/project-onweb`（git worktree）。
- 主仓库目录：`/Users/kateiso_cao/Desktop/旺阁渔村_点菜系统开发`。
- 当前分支：`onweb`。

## 2) 线上状态（已上线）
- 平台：GCP Cloud Run（区域 `asia-east2`，香港）。
- 服务名：`wangge-menu`。
- 线上 URL：`https://wangge-menu-sbvdirxv5q-df.a.run.app`。
- 当前版本包含：
  - 用户名+密码登录（`/api/auth/login`）
  - 菜品管理（`/api/dishes`，前端 `DishManager`）
  - AI 点菜与菜单调整

## 3) 已做安全基线
- `DEEPSEEK_API_KEY` 通过 Secret Manager 注入（secret: `deepseek-api-key`）。
- `JWT_SECRET_KEY` 通过 Secret Manager 注入（secret: `jwt-secret-key`）。
- API 限流：每 IP 每分钟 `RATE_LIMIT_PER_MINUTE`（默认 30）。
- 健康检查：`/api/health`。
- Uptime Check：`wangge-menu-health`。
- Alert Policy：`wangge-menu-health-alert`。

## 4) 本地关键文件（本次同步）
- 后端：
  - `backend/main.py`
  - `backend/config.py`
  - `backend/auth_utils.py`
  - `backend/database.py`
  - `backend/models/user.py`
  - `backend/routers/auth.py`
  - `backend/routers/dish.py`
  - `backend/routers/menu.py`
- 前端：
  - `frontend/src/App.tsx`
  - `frontend/src/api/menuApi.ts`
  - `frontend/src/components/DishManager.tsx`
- 部署：`Dockerfile`（multi-stage，云端构建 frontend）

## 5) 常用操作
- 本地构建：
  - `cd frontend && npm run build`
  - `python3 -m compileall backend`
- 线上发布：
  - `gcloud run deploy wangge-menu --source . --region asia-east2 --project kateiso-core --allow-unauthenticated`
- 线上日志：
  - `gcloud run services logs read wangge-menu --region=asia-east2 --project=kateiso-core --limit=100`

## 6) 绝对注意
- 不要把密钥写入代码或前端。
- 认证流是 JWT（不是旧版单密码 `/api/auth`）。
- 修改登录/权限时需同时检查前端 `menuApi.ts` 与后端 `auth.py/auth_utils.py`。
