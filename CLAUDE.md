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

### Conversation Adjustment Flow
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

- **DeepSeek proxy**: `_find_http_proxy()` 遍历所有代理变量，优先选 HTTP 代理，跳过 SOCKS（缺 socksio 包会报 Connection error）
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
- Auto git commit on changes (per user preference)

### Worktree 注意事项
- `.env` 文件只在主仓库根目录，worktree 需要创建符号链接：`ln -s /主仓库/.env /worktree/.env`
- `.venv` 也在主仓库，worktree 中用 `source /主仓库/.venv/bin/activate`
- 新增 DB 表后需 `rm menu.db` 重建

## Current Progress — feat/conversation-adjust 分支

**分支位置**: `.worktrees/feat-conversation/`
**状态**: Step 1-6 代码全部完成，待端到端测试验证

### 已实现
| Step | 内容 | 状态 |
|------|------|------|
| 1 | 后端调整 API — `MenuConversation` 表、`analyze_adjustment_intent()`、`build_adjustment_prompt()` | done |
| 2 | 前端对话框 UI — `MenuAdjustChat.tsx`、`MenuPreview.tsx` 左右分栏 | done |
| 3 | 流式输出 — `generate_menu_stream()` 逐菜品 yield NDJSON | done |
| 4 | 前端流式接收 — `streamMenuAdjustConfirm()` 异步生成器 + `handleConfirm()` 更新菜单 | done |
| 5 | 完整调整流程 — `execute_adjustment()` 菜品替换 + confirm action 路由 | done |
| 6 | Excel 下载修复 — 认证中间件支持 URL token + 前端 URL 跳转下载 | done |

### 待完成
- [ ] 端到端测试：生成菜单 → 对话调整(ask/suggest) → 确认 → 菜单实时更新 → 下载 Excel
- [ ] 测试通过后合并回 master

### 合并条件
- 后端 `/api/menu/{id}/adjust` confirm action 返回流式菜单 ✅
- 前端接收并实时渲染流式菜单更新 ✅
- 完整对话流程测试通过（提问 → 确认 → 菜单更新）❓ 待验证
- Excel 下载正常 ❓ 待验证

### 测试场景
- 8人、3000元预算、55% 毛利
- 对话测试 1: 输入"太贵了" → LLM 追问(type=ask) → 用户回复
- 对话测试 2: 输入"换掉#5，要海鲜" → LLM 直接建议(type=suggest) → 确认 → 菜单刷新
- Excel 下载验证

### 已知问题 & 排查
| 问题 | 原因 & 解决 |
|------|-----------|
| Connection error | DeepSeek 连接失败。检查: 1) `.env` 是否存在(worktree 需符号链接) 2) 代理是否可用(`_find_http_proxy()` 会打日志) |
| LLM JSON 格式错误 | 检查 `build_adjustment_prompt()` 的 response_format，确保 `{"type": "json_object"}` |
| 菜单更新不显示 | 检查 `MenuPreview.tsx` 的 `onAdjustmentApplied()` 回调是否触发 |
| 预算/毛利率计算错误 | 检查 `execute_adjustment()` 中的 subtotal/cost_total 重算逻辑 |
