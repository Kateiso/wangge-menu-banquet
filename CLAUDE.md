# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

旺阁渔村 AI 点菜系统 — A full-stack restaurant menu recommendation system powered by DeepSeek LLM. Users input party size, budget, and margin targets; the AI generates an optimized menu from the restaurant's dish catalog (150+ dishes loaded from CSV).

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
│   ├── conversation.py  # MenuConversation table (dialog history for adjustments)
│   └── schemas.py       # Pydantic request/response schemas
├── routers/menu.py      # POST /generate, POST /{id}/adjust, GET /{id}/excel
└── services/
    ├── dish_service.py       # CSV parsing, price text→float, category inference
    ├── menu_engine.py        # LLM prompt building, DeepSeek call, validation, streaming
    ├── adjustment_engine.py  # Conversation-based menu adjustment (analyze intent, execute replacement)
    └── excel_generator.py    # openpyxl formatted export
```

### Menu Generation Pipeline
1. `build_dish_catalog()` → formats all dishes by category for LLM context
2. `build_prompt()` → detailed prompt with rules (dish count, structure, budget, margin, diversity)
3. `call_deepseek()` → LLM returns `{menu: [{dish_id, quantity, reason}], reasoning}`
4. `validate_and_build_menu()` → validates dish_ids, deduplicates, computes totals, saves to DB

### Conversation Adjustment Flow (feat/conversation-adjust branch)
1. User sends message → `analyze_adjustment_intent()` → LLM returns `{type: "ask"|"suggest"}`
2. User confirms → `execute_adjustment()` → replaces dishes, recalculates totals
3. Response streamed via `generate_menu_stream()` → NDJSON lines `{"item": {...}}` + `{"summary": {...}}`

### Frontend Structure
```
frontend/src/
├── App.tsx                    # Login → OrderForm → MenuPreview flow
├── components/
│   ├── OrderForm.tsx          # Form: party_size, budget, target_margin, occasion, preferences
│   ├── MenuPreview.tsx        # Left: menu table + stats, Right: chat sidebar
│   └── MenuAdjustChat.tsx     # Conversation UI with streaming confirm
└── api/menuApi.ts             # API client (login, generateMenu, streamMenuAdjustConfirm, downloadExcel)
```

### Auth
Simple password auth: token = password stored in `localStorage('wg_token')`. Middleware checks `Authorization: Bearer <token>` header or `?token=` query param (for Excel download).

## Key Conventions

- **DeepSeek proxy**: System SOCKS proxy is bypassed; uses `http_proxy` env var if set (`menu_engine.py:get_client()`)
- **Price parsing**: Handles formats like `99元/例`, `时价(参考180元)/例`, `53元/只` (`dish_service.py:parse_price()`)
- **Category order**: 凉菜 → 热菜 → 汤羹 → 主食 → 甜品 → 点心
- **Cost assumption**: Dish cost auto-calculated as ~40% of price in CSV import
- **Streaming format**: NDJSON (one JSON object per line, `\n` separated)
- **DB migrations**: None — delete `menu.db` to reset schema

## Environment Variables (.env)
```
DEEPSEEK_API_KEY=sk-...    # Required for LLM calls
APP_PASSWORD=wangge2026    # Login password
DEFAULT_MARGIN=55          # Default target margin %
```

## Git Workflow

- **master**: stable production
- Feature branches developed in `.worktrees/` (git worktrees for isolation)
- Worktree convention: `.worktrees/<short-name>/` with `HANDOFF.md` for cross-session continuity
- Auto git commit on changes (per user preference)
