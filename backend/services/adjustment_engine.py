import json
import logging
from sqlmodel import Session, select
from backend.models.dish import Dish
from backend.models.menu import Menu, MenuItem
from backend.models.conversation import MenuConversation
from backend.models.schemas import AdjustResponse, AdjustmentAction
from backend.services.menu_engine import get_client, build_dish_catalog, CATEGORY_ORDER

logger = logging.getLogger(__name__)


def _build_current_menu_text(items: list[MenuItem]) -> str:
    """当前菜单的文本描述"""
    lines = []
    for item in sorted(items, key=lambda x: CATEGORY_ORDER.index(x.category) if x.category in CATEGORY_ORDER else 99):
        lines.append(f"#{item.dish_id} {item.dish_name} | {item.category} | ¥{item.price}×{item.quantity}=¥{item.subtotal}")
    return "\n".join(lines)


def _build_conversation_text(history: list[MenuConversation]) -> str:
    """格式化对话历史"""
    lines = []
    for msg in history[-10:]:  # 最多最近 10 条
        role = "用户" if msg.role == "user" else "助手"
        lines.append(f"{role}: {msg.content}")
    return "\n".join(lines) if lines else "（首次对话）"


def analyze_adjustment_intent(session: Session, menu_id: str, user_message: str) -> AdjustResponse:
    """分析用户调整意图，返回追问或建议"""
    menu = session.get(Menu, menu_id)
    items = list(session.exec(select(MenuItem).where(MenuItem.menu_id == menu_id)).all())
    history = list(session.exec(
        select(MenuConversation)
        .where(MenuConversation.menu_id == menu_id)
        .order_by(MenuConversation.created_at)
    ).all())

    # 保存用户消息
    user_msg = MenuConversation(menu_id=menu_id, role="user", content=user_message)
    session.add(user_msg)
    session.flush()

    # 构建 Prompt
    catalog = build_dish_catalog(session)
    current_menu_text = _build_current_menu_text(items)
    conversation_text = _build_conversation_text(history)

    prompt = f"""## 角色
你是旺阁渔村的AI点菜调整助手。用户已有一份菜单，现在想调整。

## 当前菜单（总价¥{menu.total_price:.0f}，预算¥{menu.budget:.0f}，毛利率{menu.margin_rate}%）
{current_menu_text}

## 可选菜品（只能从以下菜品中选择替换）
{catalog}

## 对话历史
{conversation_text}

## 用户最新要求
{user_message}

## 判断规则
- 如果用户要求模糊（如"太贵了"、"换点别的"、"不够"），用 type="ask" 追问细节
- 如果用户要求明确（如"换掉#5"、"去掉XX加YY"、"加个海鲜"），用 type="suggest" 给出具体替换方案
- suggest 时 remove 填要移除的当前菜单中的 dish_id，add 填要新增的菜品
- 替换后总价应尽量保持在原预算 ¥{menu.budget:.0f} 范围内（±10%）
- message 用中文自然语言描述你的建议或追问

## 严格输出以下 JSON
{{"type": "ask或suggest", "message": "你的回复", "action": {{"remove": [dish_id], "add": [{{"dish_id": 1, "quantity": 1, "reason": "推荐理由"}}]}}}}
type="ask" 时 action 设为 null"""

    # 调用 LLM
    client = get_client()
    response = client.chat.completions.create(
        model="deepseek-chat",
        messages=[
            {"role": "system", "content": "你是专业的中餐点菜调整顾问，只输出JSON。"},
            {"role": "user", "content": prompt},
        ],
        temperature=0.7,
        max_tokens=1500,
        response_format={"type": "json_object"},
    )
    content = response.choices[0].message.content.strip()
    result = json.loads(content)

    msg_type = result.get("type", "ask")
    message = result.get("message", "")
    action_raw = result.get("action")

    # 构建 action
    action = None
    action_data = ""
    if msg_type == "suggest" and action_raw:
        action = AdjustmentAction(
            remove=action_raw.get("remove", []),
            add=action_raw.get("add", []),
        )
        action_data = json.dumps(action_raw, ensure_ascii=False)

    # 保存助手回复
    assistant_msg = MenuConversation(
        menu_id=menu_id,
        role="assistant",
        content=message,
        msg_type=msg_type,
        action_data=action_data,
    )
    session.add(assistant_msg)
    session.commit()
    session.refresh(assistant_msg)

    return AdjustResponse(
        type=msg_type,
        message=message,
        action=action,
        conversation_id=assistant_msg.id,
    )


def execute_adjustment(session: Session, menu_id: str, conversation_id: int) -> tuple[Menu, list[MenuItem]]:
    """执行已确认的调整：替换菜品，重算汇总"""
    # 加载建议消息
    conv = session.get(MenuConversation, conversation_id)
    if not conv or conv.menu_id != menu_id or conv.msg_type != "suggest":
        raise ValueError("无效的调整确认")

    action = json.loads(conv.action_data)
    remove_ids = set(action.get("remove", []))
    add_items = action.get("add", [])

    menu = session.get(Menu, menu_id)
    all_dishes = {d.id: d for d in session.exec(select(Dish)).all()}

    # 删除要移除的菜品
    existing = list(session.exec(select(MenuItem).where(MenuItem.menu_id == menu_id)).all())
    for item in existing:
        if item.dish_id in remove_ids:
            session.delete(item)

    # 添加新菜品
    for add in add_items:
        dish_id = add.get("dish_id")
        quantity = add.get("quantity", 1)
        try:
            quantity = max(1, int(quantity))
        except (TypeError, ValueError):
            quantity = 1
        reason = add.get("reason", "")

        if dish_id not in all_dishes:
            logger.warning(f"调整中 dish_id {dish_id} 不存在，跳过")
            continue

        dish = all_dishes[dish_id]
        new_item = MenuItem(
            menu_id=menu_id,
            dish_id=dish.id,
            dish_name=dish.name,
            price_text=dish.price_text,
            price=dish.price,
            cost=dish.cost,
            quantity=quantity,
            subtotal=round(dish.price * quantity, 2),
            cost_total=round(dish.cost * quantity, 2),
            category=dish.category,
            reason=reason,
        )
        session.add(new_item)

    session.flush()

    # 重算汇总
    final_items = list(session.exec(select(MenuItem).where(MenuItem.menu_id == menu_id)).all())
    total_price = sum(item.subtotal for item in final_items)
    total_cost = sum(item.cost_total for item in final_items)

    menu.total_price = round(total_price, 2)
    menu.total_cost = round(total_cost, 2)
    menu.margin_rate = round((total_price - total_cost) / total_price * 100, 1) if total_price > 0 else 0

    # 记录确认
    confirm_msg = MenuConversation(
        menu_id=menu_id,
        role="assistant",
        content="菜单已更新",
        msg_type="confirm",
    )
    session.add(confirm_msg)
    session.commit()
    session.refresh(menu)

    return menu, final_items
