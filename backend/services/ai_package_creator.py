import json
import logging
from sqlmodel import Session, select
from backend.models.dish import Dish
from backend.models.package import Package, PackageItem
from backend.services.menu_engine import get_client, build_dish_catalog

logger = logging.getLogger(__name__)


def create_package_from_description(
    session: Session, description: str, group_id: int, created_by: str
) -> Package:
    """用 AI 从自然语言描述创建套餐"""
    catalog = build_dish_catalog(session)

    prompt = f"""## 角色
你是旺阁渔村的AI点菜专家。根据用户描述，从菜品库中选菜组建一个套餐。

## 可用菜品
{catalog}

## 用户描述
{description}

## 规则
1. 只能从上面的菜品库中选择
2. 菜品搭配要合理：有凉菜有热菜有主食，荤素搭配
3. 数量合理，一般每道菜1份
4. 给套餐起一个合适的名字

## 输出 JSON 格式
{{"name": "套餐名称", "description": "简要描述", "base_price": 0, "items": [{{"dish_id": 1, "quantity": 1}}]}}
"""

    client = get_client()
    response = client.chat.completions.create(
        model="deepseek-chat",
        messages=[
            {"role": "system", "content": "你是专业的中餐套餐设计师，只输出JSON。"},
            {"role": "user", "content": prompt},
        ],
        temperature=0.7,
        max_tokens=2000,
        response_format={"type": "json_object"},
    )

    content = response.choices[0].message.content.strip()
    result = json.loads(content)

    # 验证菜品存在
    all_dishes = {d.id: d for d in session.exec(select(Dish).where(Dish.is_active == True)).all()}
    valid_items = []
    for item in result.get("items", []):
        dish_id = item.get("dish_id")
        if dish_id in all_dishes:
            valid_items.append(item)
        else:
            logger.warning(f"AI 套餐创建跳过不存在的 dish_id={dish_id}")

    if not valid_items:
        raise ValueError("AI 未能选出有效菜品")

    # 计算基础价格
    base_price = result.get("base_price", 0)
    if base_price <= 0:
        base_price = sum(
            all_dishes[i["dish_id"]].price * i.get("quantity", 1)
            for i in valid_items
        )

    package = Package(
        group_id=group_id,
        name=result.get("name", "AI 推荐套餐"),
        description=result.get("description", description),
        base_price=round(base_price, 2),
        default_pricing_mode="additive",
        dish_count=len(valid_items),
        created_by=created_by,
    )
    session.add(package)
    session.flush()

    for i, item in enumerate(valid_items):
        pi = PackageItem(
            package_id=package.id,  # type: ignore
            dish_id=item["dish_id"],
            default_quantity=item.get("quantity", 1),
            sort_order=i,
        )
        session.add(pi)

    session.commit()
    session.refresh(package)
    return package
