# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

旺阁渔村 AI 点菜系统 — A full-stack restaurant menu recommendation system powered by DeepSeek LLM. Users input party size, budget, and margin targets; the AI generates an optimized menu from the restaurant's dish catalog (150+ dishes loaded from CSV).

## Commands

### Development (two terminals)
```bash
# Backend (from project root, or worktree root)
source .venv/bin/activate   # venv 在主仓库根目录
python -m uvicorn backend.main:app --reload --port 8000

# Frontend (separate terminal)
cd frontend && npm run dev    # Vite dev server at :5173, proxies /api → :8000
```

### Build & Deploy
```bash
cd frontend && npm run build           # Output → frontend/dist/
docker-compose up -d                    # Production: serves both backend + built frontend
```

### Type Checking
```bash
cd frontend && npx tsc --noEmit        # Frontend TypeScript check
python -c "from backend.main import app"  # Backend import check (no test framework yet)
```

### Database Reset
```bash
rm menu.db   # Auto-recreated on next startup with CSV import
```

## Architecture

**Backend**: FastAPI + SQLModel (SQLAlchemy+Pydantic) + SQLite (`menu.db`)
**Frontend**: React 19 + TypeScript + Ant Design 6 + Vite
**LLM**: DeepSeek API via OpenAI SDK (`deepseek-chat` model, JSON mode)

### Backend Flow
```
backend/
├── main.py              # App setup, CORS, auth middleware, SPA fallback
├── config.py            # Reads .env (DEEPSEEK_API_KEY, APP_PASSWORD, DEFAULT_MARGIN)
├── models/
│   ├── dish.py          # Dish table (imported from CSV on first run)
│   ├── menu.py          # Menu + MenuItem tables (UUID primary key)
│   └── schemas.py       # Pydantic request/response schemas
├── routers/menu.py      # POST /generate, GET /{id}/excel
└── services/
    ├── dish_service.py       # CSV parsing, price text→float, category inference
    ├── menu_engine.py        # LLM prompt building, DeepSeek call, validation
    └── excel_generator.py    # openpyxl formatted export
```

### Menu Generation Pipeline
1. `build_dish_catalog()` → formats all dishes by category for LLM context
2. `build_prompt()` → detailed prompt with rules (dish count, structure, budget, margin, diversity)
3. `call_deepseek()` → LLM returns `{menu: [{dish_id, quantity, reason}], reasoning}`
4. `validate_and_build_menu()` → validates dish_ids, deduplicates, computes totals, saves to DB

### Frontend Structure
```
frontend/src/
├── App.tsx                    # Login → OrderForm → MenuPreview flow
├── components/
│   ├── OrderForm.tsx          # Form: party_size, budget, target_margin, occasion, preferences
│   └── MenuPreview.tsx        # Menu table + stats + download
└── api/menuApi.ts             # API client (login, generateMenu, downloadExcel)
```

### Auth
Simple password auth: token = password stored in `localStorage('wg_token')`. Middleware checks `Authorization: Bearer <token>` header or `?token=` query param (for Excel download).

## Key Conventions

- **DeepSeek proxy**: `_find_http_proxy()` 遍历所有代理变量，优先选 HTTP 代理，跳过 SOCKS（缺 socksio 包会报 Connection error）
- **Price parsing**: Handles formats like `99元/例`, `时价(参考180元)/例`, `53元/只` (`dish_service.py:parse_price()`)
- **Category order**: 凉菜 → 热菜 → 汤羹 → 主食 → 甜品 → 点心
- **Cost model**: Dish cost by category (凉菜28%, 热菜38%, 主食25%...) + per-dish jitter, margin range 54-82%
- **DB migrations**: None — delete `menu.db` to reset schema

## Environment Variables (.env)
```
DEEPSEEK_API_KEY=sk-...    # Required for LLM calls
APP_PASSWORD=wangge2026    # Login password
DEFAULT_MARGIN=55          # Default target margin %
```

## Git Workflow

- **master**: stable production
- Auto git commit on changes (per user preference)

## Release Trigger

- 只有当用户在当前对话中明确回复“OK”（或“可以发布”）时，才允许执行生产发布动作。
- 在收到“OK”前，默认只完成开发、构建、测试与预览，不执行发布到生产环境。

## Handoff (Concise)

- 项目目录固定：`/Users/kateiso_cao/Desktop/旺阁渔村_点菜系统开发`（不迁移）。
- 并行开发使用 `wt` / `git worktree`：
  - `wt switch --create <branch>`
  - `wt switch <branch>`
  - `git worktree list`
- 当前目标方向：可上线、国内访问速度可接受（不是必须备案级别）。
- 生产动作前必须再次拿到用户明确“OK / 可以发布”。

## Latest Online Snapshot (2026-02-16)

- 已上线地址：`https://wangge-menu-sbvdirxv5q-df.a.run.app`（Cloud Run, `asia-east2`）。
- 线上服务：`wangge-menu`（项目 `kateiso-core`）。
- 当前线上功能：用户名+密码登录、菜品管理、AI 点菜、菜单调整、Excel 下载。
- 认证已升级为 JWT：
  - 登录：`POST /api/auth/login`
  - 当前用户：`GET /api/auth/me`
  - 菜品管理：`/api/dishes`（需登录）
- 密钥策略：
  - `DEEPSEEK_API_KEY` -> Secret Manager: `deepseek-api-key`
  - `JWT_SECRET_KEY` -> Secret Manager: `jwt-secret-key`
- 安全基线：IP 限流（默认 30/min）、`/api/health`、Uptime Check（`wangge-menu-health`）、Alert Policy（`wangge-menu-health-alert`）。
- 发布命令（当前可用）：
  - `gcloud run deploy wangge-menu --source . --region asia-east2 --project kateiso-core --allow-unauthenticated`
- 代码基线提交（worktree `onweb`）：
  - `56b4f1e`：恢复账号登录+菜品管理到线上版本
  - `a76060b`：部署修复与基础安全能力
