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
