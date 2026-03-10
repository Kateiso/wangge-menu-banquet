# 旺阁渔村点菜系统 Walkthrough

## 目标
- 升级认证为账号+JWT（替代单密码）。
- 增加菜品管理能力（上/下架、招牌/必点、单位/一开几）。
- 增强 AI 配菜规则（预算、毛利、按位菜、招牌约束）。

## 关键步骤
1. 后端新增用户模型与认证路由，菜单与菜品接口接入鉴权。
2. 前端登录改为用户名+密码，并新增菜品管理页面。
3. 菜品模型扩展字段：`is_signature`、`is_must_order`、`serving_unit`、`serving_split`。
4. 配菜引擎增加规则提示、重试反馈与失败兜底。
5. 补充认证与 RBAC 回归测试，验证核心路径。

## 本轮验证
- 后端启动：`python -m uvicorn backend.main:app --reload --port 8000`
- 前端启动：`cd frontend && npm run dev -- --port 5173`
- 登录接口：`POST /api/auth/login`（`admin`、`chef` 均可登录）
- 菜品权限：`chef` 修改成本返回 403，`admin` 可修改招牌标签
- AI 点菜：`POST /api/menu/generate` 已可返回菜单数据

## 结果
- 三项目标功能都已落地并可运行。
- 额外补齐：`/api/health` 健康检查、JWT 密钥改为环境变量、AI 最终重试失败时不再返回不达标菜单。

## 2026-02-18 宴会版 5 项优化（feature/banquet-mode）
- Opt-1（调整助手）：将模糊语义默认从 `ask` 改为 `suggest`，仅在完全无法映射操作时追问；删除预算约束提示语。
- Opt-2（Excel）：C 列改数值单价并加格式，E 列改 `=C*D` 公式，时价标记移动到备注 `(时价)`。
- Opt-3（生成速度）：LLM 尝试次数从 3 降到 2；retail 重试阈值放宽到预算 85%-110%、毛利偏差 8%。
- Opt-4（菜品管理）：新增 `POST /api/dishes`（admin），前端菜品管理新增名称搜索、分类筛选和“新增菜品”弹窗。
- Opt-5（毛利区间）：前端滑条收窄到 50%-72%，后端入口增加同范围前置校验并快速失败。

## 本轮验证（2026-02-18）
- 前端类型检查：`cd frontend && npx tsc --noEmit` 通过。
- 后端导入检查：`source ../旺阁渔村_点菜系统开发/.venv/bin/activate && python -c "from backend.main import app"` 通过。
- 后端回归测试：`python -m pytest backend/tests/test_auth_and_dishes.py -q`，`27 passed in 11.97s`。

## 2026-03-10 文档真源收敛
- 决策：保留 `AGENTS.md` 作为仓库唯一指令文档，删除重复的 `CLAUDE.md`。
- 真源内容：以原 `CLAUDE.md` 的最新版内容为准，旧 `AGENTS.md` 不再保留。
- 目的：避免两份说明文档继续分叉，减少 Agent 读取到过期项目上下文的风险。
