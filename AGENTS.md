# AGENTS.md

This file provides guidance to coding agents working in this repository.

Single source of truth: this is the only project instruction file in this repository. Do not recreate `CLAUDE.md`.

## Project Overview

旺阁渔村点菜系统 — 餐厅套餐模板 + 算法规格匹配 + 手动编辑的全栈点菜系统。AI 作为辅助角色（创建新套餐、对话微调菜单）。

**核心流程**：登录 → 填参数(客户名/日期/人数/桌数) → 选套餐模板 → 系统匹配规格 → 菜单编辑器(增删改价) → 导出 Excel

## Commands

### Development (two terminals)
```bash
# Backend (from project root)
source .venv/bin/activate
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
python -c "from backend.main import app"  # Backend import check
```

### Database Reset
```bash
rm menu.db   # Auto-recreated on next startup with CSV import
```

## Architecture

**Backend**: FastAPI + SQLModel (SQLAlchemy+Pydantic) + SQLite (`menu.db`)
**Frontend**: React 19 + TypeScript + Ant Design 6 + Vite + dayjs
**LLM**: DeepSeek API via OpenAI SDK (`deepseek-chat` model, JSON mode)

### Backend Structure
```
backend/
├── main.py              # App setup, CORS, auth middleware, SPA fallback
├── config.py            # Reads .env
├── database.py          # SQLAlchemy session
├── auth_utils.py        # JWT token generation/validation
├── models/
│   ├── dish.py          # Dish table (imported from CSV on first run)
│   ├── dish_spec.py     # DishSpec — 菜品多规格(例牌/半只/一只/中牌)
│   ├── menu.py          # Menu + MenuItem tables (UUID primary key)
│   ├── package.py       # PackageGroup + Package + PackageItem — 套餐模板
│   ├── user.py          # User model (admin/staff roles)
│   ├── conversation.py  # Chat conversation history
│   └── schemas.py       # Pydantic request/response schemas
├── routers/
│   ├── auth.py          # POST /api/auth/login, GET /api/auth/me
│   ├── dish.py          # CRUD /api/dishes + /api/dishes/{id}/specs + /api/dishes/specs/batch
│   ├── menu.py          # 菜单CRUD、从套餐创建、编辑、定价切换、Excel导出
│   └── package.py       # 套餐分组+套餐CRUD、AI创建套餐
└── services/
    ├── dish_service.py       # CSV parsing, price→float, DishSpec CRUD
    ├── spec_matcher.py       # 按人数匹配菜品规格
    ├── package_service.py    # 套餐分组+模板CRUD
    ├── menu_engine.py        # LLM prompt + DeepSeek call (保留旧AI生成)
    ├── ai_package_creator.py # AI 从描述创建套餐
    ├── adjustment_engine.py  # 对话式菜单微调
    └── excel_generator.py    # 普通菜单 + 毛利核算表两种导出
```

### Key API Endpoints
```
# 套餐
GET/POST   /api/packages/groups          # 套餐分组
GET/PUT/DEL /api/packages/{id}           # 套餐详情/修改/删除
POST       /api/packages/{id}/items      # 添加菜品到套餐
POST       /api/packages/ai-create       # AI 创建套餐

# 菜单
POST       /api/menu/from-package        # 从套餐创建菜单实例（主流程）
GET        /api/menu/{id}                # 获取菜单详情
PUT        /api/menu/{id}/items/{itemId} # 改单项（价格/规格/数量）
POST       /api/menu/{id}/items          # 添加菜品
DELETE     /api/menu/{id}/items/{itemId} # 删除菜品
PUT        /api/menu/{id}/pricing        # 切换定价模式(fixed/additive)
GET        /api/menu/{id}/excel?format=simple|margin  # Excel导出
POST       /api/menu/{id}/adjust         # AI对话调整
POST       /api/menu/generate            # 旧AI生成(保留)

# 菜品
GET/POST   /api/dishes                   # 菜品列表/新增
GET/POST   /api/dishes/{id}/specs        # 菜品规格
GET        /api/dishes/specs/batch?dish_ids=1,2,3  # 批量获取多菜品规格（菜单编辑器用，避免并发429）
```

### Frontend Structure
```
frontend/src/
├── App.tsx                        # Login → PackageSelector → MenuEditor flow
├── components/
│   ├── PackageSelector.tsx        # 顶栏参数 + 套餐分组Tab + 卡片选择
│   ├── MenuEditor.tsx             # 可编辑菜品表格 + AI对话 + 导出
│   ├── PackageTemplateEditor.tsx  # 套餐模板编辑(Drawer)
│   ├── DishManager.tsx            # 菜品管理 + DishSpec展开行
│   └── MenuAdjustChat.tsx         # AI对话助手
└── api/menuApi.ts                 # 全部API客户端函数
```

### Key Concepts

- **定价模式**: `additive`(加法价：总价=各菜小计之和) | `fixed`(固定价：总价=固定价×桌数)
- **规格匹配**: DishSpec 按 min_people/max_people 匹配，无匹配用 is_default，再无则用 Dish 本价
- **角色权限**: admin 看全部数据; staff 隐藏成本/单菜毛利，只看总毛利率; 员工可编辑套餐模板; 菜品管理仅 admin
- **Excel 两种导出**: `simple`=推荐菜单(给客户), `margin`=毛利核算表(内部用，G列可编辑自动刷新公式)

## Key Conventions

- **DeepSeek proxy**: `_find_http_proxy()` 遍历代理变量，优先 HTTP，跳过 SOCKS
- **Price parsing**: `dish_service.py:parse_price()` handles `99元/例`, `时价(参考180元)/例`
- **Category order**: 凉菜 → 热菜 → 汤羹 → 主食 → 甜品 → 点心
- **Cost model**: Category-based ratio + per-dish jitter
- **DB migrations**: None — delete `menu.db` to reset schema

## Environment Variables (.env)
```
DEEPSEEK_API_KEY=sk-...    # Required for LLM calls
JWT_SECRET_KEY=...         # JWT signing
APP_PASSWORD=wangge2026    # Legacy
DEFAULT_MARGIN=55          # Default target margin %
```

## Git Workflow

- **onweb**: production branch
- Conventional Commits: `type(scope): summary`

## Release Trigger

- 只有当用户明确回复"OK"（或"可以发布"）时，才执行生产发布动作。
- 发布命令：`gcloud run deploy wangge-menu --source . --region asia-east2 --project kateiso-core --allow-unauthenticated`

## Online Deployment

- 地址：`https://wangge-menu-sbvdirxv5q-df.a.run.app`（Cloud Run, `asia-east2`, `kateiso-core`）
- 密钥：Secret Manager (`deepseek-api-key`, `jwt-secret-key`)
- 安全：IP 限流 30/min, health check, Uptime monitoring
