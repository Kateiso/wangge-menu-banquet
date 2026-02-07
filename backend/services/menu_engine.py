import json
import logging
import os
import httpx
from openai import OpenAI
from sqlmodel import Session, select
from backend.config import DEEPSEEK_API_KEY
from backend.models.dish import Dish
from backend.models.menu import Menu, MenuItem
from backend.models.schemas import MenuGenerateRequest
from backend.services.dish_service import get_dishes_by_category

logger = logging.getLogger(__name__)

_client = None


def get_client() -> OpenAI:
    global _client
    if _client is None:
        # 绕过系统 SOCKS 代理，使用 HTTP 代理或直连
        http_proxy = os.environ.get("http_proxy", "")
        proxy = http_proxy if http_proxy.startswith("http://") else None
        _client = OpenAI(
            api_key=DEEPSEEK_API_KEY,
            base_url="https://api.deepseek.com",
            http_client=httpx.Client(proxy=proxy),
        )
    return _client

CATEGORY_ORDER = ["凉菜", "热菜", "汤羹", "主食", "甜品", "点心"]


def build_dish_catalog(session: Session) -> str:
    """构建按类别分组的菜品目录，供 LLM 使用"""
    grouped = get_dishes_by_category(session)
    lines = []
    for cat in CATEGORY_ORDER:
        dishes = grouped.get(cat, [])
        if not dishes:
            continue
        lines.append(f"\n【{cat}】")
        for d in dishes:
            tag_display = d.tags.replace("|", "·") if d.tags else ""
            price_display = d.price_text
            if d.is_market_price:
                price_display = f"时价(参考{int(d.price)}元)/例"
            lines.append(
                f"#{d.id} | {d.name} | {price_display} | 成本{int(d.cost)} | {tag_display}"
            )
    return "\n".join(lines)


def build_prompt(request: MenuGenerateRequest, catalog: str) -> str:
    dish_count = request.party_size + 3
    avg_price = int(request.budget / dish_count)
    budget_low = int(request.budget * 0.90)
    budget_high = int(request.budget * 1.05)
    return f"""## 角色
你是旺阁渔村的AI点菜助手，擅长根据客户需求搭配菜品。

## 配菜规则
1. 菜品总数: 约 {dish_count} 道菜（人数{request.party_size}人）
2. 结构: 凉菜2-4道 / 热菜≥3道 / 汤羹1道 / 主食1-2道 / 甜品或点心1-2道
3. 预算控制【最重要】:
   - 目标总价: {request.budget} 元，允许范围 {budget_low}~{budget_high} 元
   - 每道菜平均约 {avg_price} 元（含数量），请选菜时边选边算，确保总价落在目标范围
   - 如果选的菜偏便宜，就多选几道或增加按只/件计价菜品的数量来凑满预算
   - 按只/件计价的菜（乳鸽、T骨等），数量按人数配（{request.party_size}人点{request.party_size}只/件）
4. 毛利控制: 目标整单毛利率 {request.target_margin}%，优先选高毛利菜品但不牺牲菜品档次
5. 多样性: 烹饪方式≥4种、口味≥3种、食材≥3种
6. 不要重复选同一道菜

## 客户需求
- 人数: {request.party_size}人
- 预算: {request.budget}元（必须花到 {budget_low}~{budget_high} 元）
- 毛利目标: {request.target_margin}%
- 场合: {request.occasion or "普通聚餐"}
- 偏好: {request.preferences or "无特殊要求"}

## 可选菜品（只能从以下菜品中选择，用 dish_id 引用）
{catalog}

## 输出要求
严格输出以下 JSON 格式，不要输出其他内容：
```json
{{
  "menu": [
    {{"dish_id": 24, "quantity": 6, "reason": "招牌必点，人均1只"}}
  ],
  "total_estimate": {request.budget},
  "reasoning": "本套餐以粤菜为主，兼顾..."
}}
```

注意：
- dish_id 必须是上面菜品列表中存在的 # 号后数字
- quantity 是点菜数量（按份/例/只计）
- reason 是推荐该菜的简短理由
- total_estimate 是你估算的菜品总价（必须在 {budget_low}~{budget_high} 范围内）
- reasoning 是整体配菜思路说明
- 选完菜后请自行加总验算，如果总价低于 {budget_low} 元，请增加菜品或数量"""


def call_deepseek(prompt: str) -> dict:
    """调用 DeepSeek API 获取配菜建议"""
    client = get_client()
    response = client.chat.completions.create(
        model="deepseek-chat",
        messages=[
            {"role": "system", "content": "你是一个专业的中餐点菜顾问，只输出JSON格式结果。"},
            {"role": "user", "content": prompt},
        ],
        temperature=0.7,
        max_tokens=2000,
        response_format={"type": "json_object"},
    )
    content = response.choices[0].message.content.strip()
    return json.loads(content)


def validate_and_build_menu(
    session: Session, request: MenuGenerateRequest, llm_result: dict
) -> tuple[Menu, list[MenuItem]]:
    """后验证 + 构建 Menu 和 MenuItem"""
    menu_items_raw = llm_result.get("menu", [])
    reasoning = llm_result.get("reasoning", "")

    # 加载所有菜品 id→Dish 映射
    all_dishes = {d.id: d for d in session.exec(select(Dish)).all()}

    items: list[MenuItem] = []
    seen_ids = set()
    total_price = 0.0
    total_cost = 0.0

    menu = Menu(
        customer_name=request.customer_name,
        party_size=request.party_size,
        budget=request.budget,
        target_margin=request.target_margin,
        occasion=request.occasion,
        preferences=request.preferences,
        reasoning=reasoning,
    )
    session.add(menu)
    session.flush()  # 获取 menu.id

    for item_raw in menu_items_raw:
        dish_id = item_raw.get("dish_id")
        quantity = item_raw.get("quantity", 1)
        reason = item_raw.get("reason", "")

        # dish_id 校验
        if dish_id not in all_dishes:
            logger.warning(f"LLM 返回了不存在的 dish_id: {dish_id}，跳过")
            continue

        # 去重
        if dish_id in seen_ids:
            logger.warning(f"LLM 重复推荐 dish_id: {dish_id}，跳过")
            continue
        seen_ids.add(dish_id)

        dish = all_dishes[dish_id]
        subtotal = round(dish.price * quantity, 2)
        cost_total = round(dish.cost * quantity, 2)

        item = MenuItem(
            menu_id=menu.id,
            dish_id=dish.id,
            dish_name=dish.name,
            price_text=dish.price_text,
            price=dish.price,
            cost=dish.cost,
            quantity=quantity,
            subtotal=subtotal,
            cost_total=cost_total,
            category=dish.category,
            reason=reason,
        )
        items.append(item)
        total_price += subtotal
        total_cost += cost_total

    # 更新 Menu 汇总
    menu.total_price = round(total_price, 2)
    menu.total_cost = round(total_cost, 2)
    menu.margin_rate = (
        round((total_price - total_cost) / total_price * 100, 1)
        if total_price > 0
        else 0
    )

    # 后验证日志
    budget_ratio = total_price / request.budget if request.budget > 0 else 0
    if budget_ratio > 1.05:
        logger.warning(
            f"总价 {total_price} 超预算 {request.budget} ({budget_ratio:.0%})"
        )
    if abs(menu.margin_rate - request.target_margin) > 3:
        logger.warning(
            f"毛利率 {menu.margin_rate}% 偏离目标 {request.target_margin}%"
        )

    # 检查类别覆盖
    categories_present = {item.category for item in items}
    required = {"凉菜", "热菜"}
    missing = required - categories_present
    if missing:
        logger.warning(f"缺少必要类别: {missing}")

    for item in items:
        session.add(item)
    session.commit()
    session.refresh(menu)

    return menu, items


def generate_menu(session: Session, request: MenuGenerateRequest) -> tuple[Menu, list[MenuItem]]:
    """完整流程: 构建 Prompt → 调用 LLM → 后验证 → 存 DB（预算不足自动重试）"""
    catalog = build_dish_catalog(session)
    prompt = build_prompt(request, catalog)

    logger.info(f"调用 DeepSeek 为 {request.party_size} 人配菜，预算 {request.budget} 元")

    for attempt in range(2):
        try:
            llm_result = call_deepseek(prompt)
            menu, items = validate_and_build_menu(session, request, llm_result)
            if not items:
                logger.warning(f"第 {attempt + 1} 次尝试未生成有效菜单，重试")
                continue

            # 检查预算利用率，低于 75% 则重试（仅第一次）
            budget_ratio = menu.total_price / request.budget if request.budget > 0 else 1
            if budget_ratio < 0.75 and attempt < 1:
                logger.warning(
                    f"第 {attempt + 1} 次预算利用率仅 {budget_ratio:.0%}"
                    f"（{menu.total_price:.0f}/{request.budget}），重试"
                )
                # 回滚本次结果
                session.delete(menu)
                for item in items:
                    session.delete(item)
                session.commit()
                # 补充强调提示重新生成
                prompt = build_prompt(request, catalog) + f"""

## 特别注意
上一次配菜总价仅 {menu.total_price:.0f} 元，远低于预算 {request.budget} 元（利用率 {budget_ratio:.0%}）。
请增加菜品数量或选择更高档的菜品，确保总价接近 {request.budget} 元。"""
                continue

            return menu, items
        except Exception as e:
            logger.error(f"第 {attempt + 1} 次尝试失败: {e}")
            if attempt == 1:
                raise

    raise ValueError("无法生成有效菜单，请重试")
