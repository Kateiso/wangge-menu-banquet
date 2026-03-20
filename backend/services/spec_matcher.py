from sqlmodel import Session, select
from backend.models.dish import Dish
from backend.models.dish_spec import DishSpec
from backend.models.menu import Menu, MenuItem
from backend.models.package import Package, PackageItem


def match_spec(dish_id: int, party_size: int, session: Session) -> DishSpec | None:
    """根据人数匹配菜品规格"""
    # 1. 查找人数范围匹配的规格
    specs = list(session.exec(
        select(DishSpec)
        .where(DishSpec.dish_id == dish_id, DishSpec.is_active == True)
        .where(DishSpec.min_people <= party_size, DishSpec.max_people >= party_size)
        .order_by(DishSpec.sort_order)
    ).all())
    if specs:
        return specs[0]

    # 2. 无匹配 → 返回默认规格
    default = session.exec(
        select(DishSpec)
        .where(DishSpec.dish_id == dish_id, DishSpec.is_active == True, DishSpec.is_default == True)
    ).first()
    if default:
        return default

    # 3. 无默认 → 返回 None（调用方用 Dish 本身价格）
    return None


def build_menu_from_package(
    session: Session,
    package_id: int,
    party_size: int,
    table_count: int,
    customer_name: str,
    date: str,
    pricing_mode: str,
) -> tuple[Menu, list[MenuItem]]:
    """从套餐模板创建菜单实例"""
    package = session.get(Package, package_id)
    if not package:
        raise ValueError("套餐不存在")

    effective_pricing_mode = pricing_mode or package.default_pricing_mode or "additive"

    # 加载套餐菜品
    pkg_items = list(session.exec(
        select(PackageItem)
        .where(PackageItem.package_id == package_id)
        .order_by(PackageItem.sort_order)
    ).all())

    menu = Menu(
        customer_name=customer_name,
        mode='package',
        party_size=party_size,
        date=date,
        pricing_mode=effective_pricing_mode,
        table_count=table_count,
        fixed_price=package.base_price,
    )

    menu_items: list[MenuItem] = []
    total_price = 0.0
    total_cost = 0.0

    for pkg_item in pkg_items:
        dish = session.get(Dish, pkg_item.dish_id)
        if not dish or not dish.is_active:
            continue

        # 匹配规格
        spec = match_spec(dish.id, party_size, session)  # type: ignore

        if spec:
            item_price = spec.price
            item_cost = spec.cost
            spec_name = spec.spec_name
            spec_id = spec.id
        else:
            item_price = dish.price
            item_cost = dish.cost
            spec_name = ""
            spec_id = None

        quantity = pkg_item.default_quantity
        subtotal = round(item_price * quantity, 2)
        cost_total = round(item_cost * quantity, 2)

        mi = MenuItem(
            dish_id=dish.id,  # type: ignore
            dish_name=dish.name,
            price_text=dish.price_text,
            price=item_price,
            min_price=dish.min_price,
            cost=item_cost,
            quantity=quantity,
            subtotal=subtotal,
            cost_total=cost_total,
            category=dish.category,
            spec_id=spec_id,
            spec_name=spec_name,
            adjusted_price=item_price,
        )
        menu_items.append(mi)
        total_price += subtotal
        total_cost += cost_total

    # 定价模式
    if effective_pricing_mode == 'fixed':
        menu.total_price = package.base_price * table_count
    else:
        menu.total_price = round(total_price, 2)

    menu.total_cost = round(total_cost, 2)
    menu.budget = menu.total_price

    if menu.total_price > 0:
        menu.margin_rate = round(
            (menu.total_price / table_count - menu.total_cost / table_count)
            / (menu.total_price / table_count) * 100, 1
        )
    else:
        menu.margin_rate = 0.0

    # 保存
    session.add(menu)
    session.flush()

    for mi in menu_items:
        mi.menu_id = menu.id
        session.add(mi)

    session.commit()
    session.refresh(menu)

    saved_items = list(session.exec(
        select(MenuItem).where(MenuItem.menu_id == menu.id)
    ).all())

    return menu, saved_items
