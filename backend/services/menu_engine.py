import json
import logging
import math
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
        http_proxy = os.environ.get('http_proxy', '')
        proxy = http_proxy if http_proxy.startswith('http://') else None
        _client = OpenAI(
            api_key=DEEPSEEK_API_KEY,
            base_url='https://api.deepseek.com',
            http_client=httpx.Client(proxy=proxy),
        )
    return _client

CATEGORY_ORDER = ['凉菜', '热菜', '汤羹', '主食', '甜品', '点心']


def _get_dish_unit(dish: Dish) -> str:
    unit = (dish.serving_unit or '').strip()
    if unit:
        return unit
    if '元/' in dish.price_text:
        return dish.price_text.split('元/', 1)[1].strip()
    return ''


def build_dish_catalog(session: Session) -> str:
    grouped = get_dishes_by_category(session)
    lines = []
    for cat in CATEGORY_ORDER:
        dishes = grouped.get(cat, [])
        if not dishes:
            continue
        lines.append(f'\n【{cat}】')
        for d in dishes:
            tag_display = d.tags.replace('|', '·') if d.tags else ''
            price_display = d.price_text
            if d.is_market_price:
                price_display = f'时价(参考{int(d.price)}元)/例'
            rule_tags = []
            if d.is_signature:
                rule_tags.append('招牌')
            if d.is_must_order:
                rule_tags.append('必点')
            rule_tag_text = f" | {'/'.join(rule_tags)}" if rule_tags else ''
            unit = _get_dish_unit(d)
            split_text = f' | 一开{d.serving_split}' if d.serving_split > 0 else ''
            unit_text = f' | 单位{unit}' if unit and d.serving_split <= 0 else ''
            lines.append(
                f'#{d.id} | {d.name} | {price_display} | 成本{int(d.cost)} | {tag_display}{rule_tag_text}{split_text}{unit_text}'
            )
    return '\n'.join(lines)


def _build_signature_constraint(
    request: MenuGenerateRequest, priority_dishes: list[Dish]
) -> str:
    if not priority_dishes:
        return ''

    pref_text = request.preferences or ''
    if '要招牌菜' in pref_text:
        required_count = min(len(priority_dishes), max(3, math.ceil(request.party_size / 4)))
    else:
        required_count = min(3, len(priority_dishes))

    lines = []
    for dish in priority_dishes:
        labels = []
        if dish.is_signature:
            labels.append('招牌')
        if dish.is_must_order:
            labels.append('必点')
        label_text = '/'.join(labels) if labels else '优先'
        lines.append(f'- #{dish.id} {dish.name}（{label_text}）')

    return (
        '\n## 招牌菜/必点菜约束\n'
        f'以下菜品为本店招牌或必点，请至少选择 {required_count} 道：\n'
        + '\n'.join(lines)
    )


def _build_serving_rules(
    request: MenuGenerateRequest,
    split_rule_dishes: list[Dish],
    per_unit_dishes_without_split: list[Dish],
) -> str:
    lines = ['\n## 按位菜品数量规则', '- 按只/件计价的菜品，不要按人数 1:1 配置数量。']

    if split_rule_dishes:
        lines.append('- 已设定规则的菜品：')
        for dish in split_rule_dishes:
            split = max(1, dish.serving_split)
            recommend_qty = math.ceil(request.party_size / split)
            unit = _get_dish_unit(dish) or '只'
            lines.append(
                f'  - #{dish.id} {dish.name}: 一开{split}，{request.party_size}人建议 {recommend_qty}{unit}'
            )

    if per_unit_dishes_without_split:
        preview = '、'.join(
            [f'#{dish.id}{dish.name}' for dish in per_unit_dishes_without_split[:8]]
        )
        lines.append(
            f'- 未设定规则的按位菜品（如：{preview}），按人数的 40-60% 配置数量。'
        )

    return '\n'.join(lines)


def build_prompt(
    request: MenuGenerateRequest,
    catalog: str,
    priority_dishes: list[Dish],
    split_rule_dishes: list[Dish],
    per_unit_dishes_without_split: list[Dish],
    feedback_note: str = '',
) -> str:
    dish_count = request.party_size + 3
    avg_price = int(request.budget / dish_count)
    budget_low = int(request.budget * 0.90)
    budget_high = int(request.budget * 1.05)
    signature_constraint = _build_signature_constraint(request, priority_dishes)
    serving_rules = _build_serving_rules(
        request, split_rule_dishes, per_unit_dishes_without_split
    )
    return f"""## 角色
你是旺阁渔村的AI点菜助手，擅长根据客户需求搭配菜品。

## 配菜规则
1. 菜品总数: 约 {dish_count} 道菜（人数{request.party_size}人）
2. 结构: 凉菜2-4道 / 热菜≥3道 / 汤羹1道 / 主食1-2道 / 甜品或点心1-2道
3. 预算控制【最重要，必须遵守】:
   - 目标总价: {request.budget} 元，绝对不能超过 {budget_high} 元
   - 最低消费: {budget_low} 元，不能低于此金额
   - 每道菜平均约 {avg_price} 元（含数量）
   - 选完所有菜后，请逐一计算 price*quantity 求和，确认总价在范围内
   - 如果超预算，删掉最贵的一道菜或减少数量
4. 毛利控制【重要】:
   - 目标整单毛利率 {request.target_margin}%，允许偏差 ±3%
   - 每道菜都有标注成本，请计算: 毛利率 = (总售价-总成本)/总售价*100%
   - 如果毛利偏低，优先替换低毛利菜品为同类高毛利菜品
5. 多样性: 烹饪方式≥4种、口味≥3种、食材≥3种
6. 不要重复选同一道菜

## 客户需求
- 人数: {request.party_size}人
- 预算: {request.budget}元（必须花到 {budget_low}~{budget_high} 元）
- 毛利目标: {request.target_margin}%
- 场合: {request.occasion or '普通聚餐'}
- 偏好: {request.preferences or '无特殊要求'}
{signature_constraint}
{serving_rules}

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
- 选完菜后请自行加总验算，如果总价低于 {budget_low} 元，请增加菜品或数量
{feedback_note}"""


def build_banquet_prompt(
    request: MenuGenerateRequest,
    catalog: str,
    priority_dishes: list[Dish],
    split_rule_dishes: list[Dish],
    per_unit_dishes_without_split: list[Dish],
    feedback_note: str = '',
) -> str:
    dish_count = request.party_size + 3
    target_cost = request.budget * (1 - request.target_margin / 100)
    cost_low = int(target_cost * 0.90)
    cost_high = int(target_cost * 1.10)
    signature_constraint = _build_signature_constraint(request, priority_dishes)
    serving_rules = _build_serving_rules(
        request, split_rule_dishes, per_unit_dishes_without_split
    )
    return f"""## 角色
你是旺阁渔村的资深大厨和宴会顾问，擅长根据客户的场合和氛围搭配完美的菜单。

## 配菜规则 (宴会模式 - 内容优先)
1. 菜品总数: 约 {dish_count} 道菜（人数{request.party_size}人）
2. 结构: 凉菜2-4道 / 热菜≥4道 / 汤羹1-2道 / 主食1-2道 / 甜品或点心1-2道
3. 重点: 优先考虑菜品的搭配、档次、口味多样性和视觉效果。
4. 质量: 确保菜单包含招牌菜，且食材涵盖海鲜、肉类、时蔬等。
5. 场合匹配: 根据客户提供的场合（如：婚宴、商务、生日等）选择最合适的菜品。
6. 成本参考【重要】:
   - 每道菜都标注了成本，请选菜后计算总成本 = sum(成本×数量)
   - 目标总成本范围: {cost_low}~{cost_high} 元
   - 若总成本过高，替换部分高成本菜为同类中等成本菜
   - 若总成本过低，升级部分菜品为更高档食材

## 客户需求
- 人数: {request.party_size}人
- 宴会总价: {request.budget}元（系统将自动按此总价分配单价）
- 目标毛利: {request.target_margin}%（对应目标成本 {int(target_cost)} 元）
- 场合: {request.occasion or '宴会聚餐'}
- 偏好: {request.preferences or '无特殊要求'}
{signature_constraint}
{serving_rules}

## 可选菜品（只能从以下菜品中选择，用 dish_id 引用）
{catalog}

## 输出要求
严格输出以下 JSON 格式，不要输出其他内容：
```json
{{
  "menu": [
    {{"dish_id": 24, "quantity": 6, "reason": "宴会必备，高档大气"}}
  ],
  "cost_estimate": {int(target_cost)},
  "reasoning": "本菜单专为{request.occasion or '宴会'}设计，突出了..."
}}
```

注意：
- dish_id 必须是上面菜品列表中存在的 # 号后数字
- quantity 是点菜数量
- cost_estimate 是你估算的菜品总成本（应在 {cost_low}~{cost_high} 范围内）
- reasoning 是整体配菜思路说明
- 选完菜后请自行加总验算成本，如果不在范围内请调整菜品
{feedback_note}"""


def call_deepseek(prompt: str) -> dict:
    client = get_client()
    response = client.chat.completions.create(
        model='deepseek-chat',
        messages=[
            {'role': 'system', 'content': '你是一个专业的中餐点菜顾问，只输出JSON格式结果。'},
            {'role': 'user', 'content': prompt},
        ],
        temperature=0.7,
        max_tokens=2000,
        response_format={'type': 'json_object'},
    )
    content = response.choices[0].message.content.strip()
    return json.loads(content)


def validate_and_build_menu(
    session: Session, request: MenuGenerateRequest, llm_result: dict
) -> tuple[Menu, list[MenuItem]]:
    menu_items_raw = llm_result.get('menu', [])
    reasoning = llm_result.get('reasoning', '')

    all_dishes = {d.id: d for d in session.exec(select(Dish)).all()}

    items: list[MenuItem] = []
    seen_ids = set()
    total_price = 0.0
    total_cost = 0.0

    menu = Menu(
        customer_name=request.customer_name,
        mode='retail',
        party_size=request.party_size,
        budget=request.budget,
        target_margin=request.target_margin,
        occasion=request.occasion or '',
        preferences=request.preferences or '',
        reasoning=reasoning or '',
    )
    session.add(menu)
    session.flush()

    for item_raw in menu_items_raw:
        dish_id = item_raw.get('dish_id')
        quantity = item_raw.get('quantity', 1)
        reason = item_raw.get('reason', '')
        try:
            quantity = max(1, int(quantity))
        except (TypeError, ValueError):
            quantity = 1

        if dish_id not in all_dishes or dish_id in seen_ids:
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
            min_price=dish.min_price,
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

    menu.total_price = round(total_price, 2)
    menu.total_cost = round(total_cost, 2)
    menu.margin_rate = (
        round((total_price - total_cost) / total_price * 100, 1)
        if total_price > 0
        else 0
    )
    summary = (
        f"系统核算：总价 {menu.total_price:.0f} 元，"
        f"总成本 {menu.total_cost:.0f} 元，毛利率 {menu.margin_rate:.1f}% 。"
    )
    menu.reasoning = f"{reasoning}\n\n{summary}" if reasoning else summary

    for item in items:
        session.add(item)
    session.commit()
    session.refresh(menu)

    return menu, items


def _apply_banquet_pricing(items: list[MenuItem], budget: float) -> float:
    """反向定价：按比例分配加价，强制 min_price 下限，修正舍入余额。

    返回实际 total_price（应极接近或等于 budget）。
    """
    total_cost = sum(item.cost_total for item in items)
    if total_cost == 0:
        return 0.0

    total_markup = budget - total_cost

    # 阶段 1：按比例分配加价
    for item in items:
        item_markup = total_markup * (item.cost_total / total_cost)
        raw_subtotal = item.cost_total + item_markup
        # 阶段 2：强制 min_price 下限
        min_subtotal = round(item.min_price * item.quantity, 2)
        item.subtotal = round(max(raw_subtotal, min_subtotal), 2)
        item.price = round(item.subtotal / item.quantity, 2)
        # 重新精确计算 subtotal 避免 price*qty 的舍入偏差
        item.subtotal = round(item.price * item.quantity, 2)

    # 阶段 3：修正舍入余额 — 差额吸收到最大可调项
    current_sum = sum(item.subtotal for item in items)
    remainder = round(budget - current_sum, 2)
    if remainder != 0 and items:
        # 找最大 subtotal 且有调整空间的项
        adjustable = [
            it for it in items
            if it.subtotal + remainder >= round(it.min_price * it.quantity, 2)
        ]
        target = max(adjustable or items, key=lambda it: it.subtotal)
        target.subtotal = round(target.subtotal + remainder, 2)
        target.price = round(target.subtotal / target.quantity, 2)

    return sum(item.subtotal for item in items)


def validate_and_build_banquet_menu(
    session: Session, request: MenuGenerateRequest, llm_result: dict
) -> tuple[Menu, list[MenuItem]]:
    menu_items_raw = llm_result.get('menu', [])
    reasoning = llm_result.get('reasoning', '')
    all_dishes = {d.id: d for d in session.exec(select(Dish)).all()}

    items: list[MenuItem] = []
    seen_ids = set()
    total_cost = 0.0

    menu = Menu(
        customer_name=request.customer_name,
        mode='banquet',
        party_size=request.party_size,
        budget=request.budget,
        target_margin=request.target_margin,
        occasion=request.occasion or '',
        preferences=request.preferences or '',
        reasoning=reasoning or '',
    )
    session.add(menu)
    session.flush()

    for item_raw in menu_items_raw:
        dish_id = item_raw.get('dish_id')
        quantity = item_raw.get('quantity', 1)
        try:
            quantity = max(1, int(quantity))
        except (TypeError, ValueError):
            quantity = 1
        if dish_id not in all_dishes or dish_id in seen_ids:
            continue
        seen_ids.add(dish_id)
        dish = all_dishes[dish_id]
        cost_total = round(dish.cost * quantity, 2)
        total_cost += cost_total

        item = MenuItem(
            menu_id=menu.id,
            dish_id=dish.id,
            dish_name=dish.name,
            price_text=dish.price_text,
            min_price=dish.min_price,
            cost=dish.cost,
            quantity=quantity,
            cost_total=cost_total,
            category=dish.category,
            reason=item_raw.get('reason', ''),
        )
        items.append(item)

    if not items or total_cost == 0:
        return menu, []

    current_margin = (request.budget - total_cost) / request.budget * 100
    if current_margin < request.target_margin - 5:
        logger.warning(f'Banquet margin too low: {current_margin:.1f}% < {request.target_margin}%')
        return menu, []

    # 反向定价（含 min_price 保护 + 舍入修正）
    actual_total = _apply_banquet_pricing(items, request.budget)

    for item in items:
        session.add(item)

    menu.total_price = round(actual_total, 2)
    menu.total_cost = round(total_cost, 2)
    menu.margin_rate = round((actual_total - total_cost) / actual_total * 100, 1) if actual_total > 0 else 0
    summary = (
        f"系统核算：按预算定价 {menu.total_price:.0f} 元，"
        f"总成本 {menu.total_cost:.0f} 元，毛利率 {menu.margin_rate:.1f}% 。"
    )
    menu.reasoning = f"{reasoning}\n\n{summary}" if reasoning else summary

    session.commit()
    session.refresh(menu)
    return menu, items


def generate_menu(session: Session, request: MenuGenerateRequest) -> tuple[Menu, list[MenuItem]]:
    if request.target_margin < 50 or request.target_margin > 72:
        raise ValueError(
            f"目标毛利 {request.target_margin:.0f}% 超出可达范围（50%-72%），建议调整至 55%-65% 以获得最佳结果"
        )

    active_dishes = list(session.exec(select(Dish).where(Dish.is_active == True)).all())
    priority_dishes = [
        dish for dish in active_dishes if dish.is_signature or dish.is_must_order
    ]
    priority_dishes.sort(key=lambda dish: (0 if dish.is_must_order else 1, dish.id or 0))
    split_rule_dishes = [dish for dish in active_dishes if dish.serving_split > 0]
    split_rule_dishes.sort(key=lambda dish: dish.id or 0)
    per_unit_dishes_without_split = [
        dish
        for dish in active_dishes
        if _get_dish_unit(dish) in {'只', '件'} and dish.serving_split <= 0
    ]

    catalog = build_dish_catalog(session)
    
    is_banquet = request.mode == 'banquet'
    prompt_builder = build_banquet_prompt if is_banquet else build_prompt
    validator = validate_and_build_banquet_menu if is_banquet else validate_and_build_menu

    prompt = prompt_builder(
        request,
        catalog,
        priority_dishes,
        split_rule_dishes,
        per_unit_dishes_without_split,
    )

    logger.info(f'调用 DeepSeek ({request.mode}) 为 {request.party_size} 人配菜，预算 {request.budget} 元')

    for attempt in range(2):
        try:
            llm_result = call_deepseek(prompt)
            menu, items = validator(session, request, llm_result)
            if not items:
                if attempt == 1:
                    raise ValueError('未生成有效菜品或毛利不足，请尝试调整预算或目标毛利')
                
                feedback = '上一次结果需修正：毛利不足或未生成菜品，请尝试替换一些成本较低的菜品。' if is_banquet else '上一次返回为空菜单，请按规则重新生成。'
                prompt = prompt_builder(
                    request,
                    catalog,
                    priority_dishes,
                    split_rule_dishes,
                    per_unit_dishes_without_split,
                    feedback_note=f'\n## 上一次结果需修正\n{feedback}',
                )
                continue

            if not is_banquet:
                retry_reasons = []
                budget_ratio = menu.total_price / request.budget if request.budget > 0 else 1
                margin_gap = abs(menu.margin_rate - request.target_margin)
                if budget_ratio < 0.85:
                    retry_reasons.append(f'总价仅 {menu.total_price:.0f} 元，低于最低预算要求。')
                if budget_ratio > 1.10:
                    retry_reasons.append(f'总价 {menu.total_price:.0f} 元，超过预算上限。')
                if margin_gap > 8:
                    retry_reasons.append(f'毛利率 {menu.margin_rate:.1f}% 与目标 {request.target_margin:.1f}% 偏差过大。')

                if retry_reasons and attempt < 1:
                    for item in items: session.delete(item)
                    session.delete(menu)
                    session.commit()
                    prompt = build_prompt(
                        request, catalog, priority_dishes, split_rule_dishes, per_unit_dishes_without_split,
                        feedback_note='\n## 上一次结果需修正\n' + '\n'.join([f'- {r}' for r in retry_reasons])
                    )
                    continue
                if retry_reasons and attempt == 1:
                    for item in items:
                        session.delete(item)
                    session.delete(menu)
                    session.commit()
                    raise ValueError('；'.join(retry_reasons))
            else:
                # 宴会模式：检查成本是否偏离过大
                target_cost = request.budget * (1 - request.target_margin / 100)
                cost_ratio = menu.total_cost / target_cost if target_cost > 0 else 1
                if (cost_ratio < 0.85 or cost_ratio > 1.15) and attempt < 1:
                    note = f'总成本 {menu.total_cost:.0f} 元，目标 {target_cost:.0f} 元，偏差过大。'
                    for item in items: session.delete(item)
                    session.delete(menu)
                    session.commit()
                    prompt = build_banquet_prompt(
                        request, catalog, priority_dishes, split_rule_dishes, per_unit_dishes_without_split,
                        feedback_note=f'\n## 上一次结果需修正\n- {note}\n- 请调整菜品使总成本更接近目标。',
                    )
                    continue

            return menu, items
        except Exception as e:
            logger.error(f'第 {attempt + 1} 次尝试失败: {e}')
            if attempt == 1: raise

    raise ValueError('无法生成有效菜单，请重试')
