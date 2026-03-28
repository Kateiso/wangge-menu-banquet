from backend.models.menu import Menu, MenuItem


def current_additive_price(item: MenuItem) -> float:
    return item.additive_price if getattr(item, "additive_price", 0) > 0 else item.price


def current_actual_price(item: MenuItem) -> float:
    if getattr(item, "adjusted_price", 0) > 0:
        return item.adjusted_price
    return current_additive_price(item)


def apply_actual_price(item: MenuItem, unit_price: float) -> None:
    item.adjusted_price = round(unit_price, 2)
    item.subtotal = round(item.adjusted_price * item.quantity, 2)
    item.cost_total = round(item.cost * item.quantity, 2)


def apply_additive_baseline(item: MenuItem, unit_price: float) -> None:
    item.additive_price = round(unit_price, 2)
    apply_actual_price(item, item.additive_price)


def restore_additive_prices(items: list[MenuItem]) -> None:
    for item in items:
        apply_actual_price(item, current_additive_price(item))


def distribute_fixed_price(items: list[MenuItem], fixed_price: float) -> None:
    if not items:
        return

    base_subtotals = [round(current_additive_price(item) * item.quantity, 2) for item in items]
    total_base = sum(base_subtotals)

    if total_base <= 0:
        per_item_total = round(fixed_price / len(items), 2)
        running_total = 0.0
        for index, item in enumerate(items):
            item_total = round(fixed_price - running_total, 2) if index == len(items) - 1 else per_item_total
            running_total = round(running_total + item_total, 2)
            unit_price = item_total / item.quantity if item.quantity > 0 else 0.0
            apply_actual_price(item, unit_price)
        return

    allocated_totals: list[float] = []
    running_total = 0.0
    for index, base_subtotal in enumerate(base_subtotals):
        if index == len(items) - 1:
            item_total = round(fixed_price - running_total, 2)
        else:
            item_total = round(fixed_price * (base_subtotal / total_base), 2)
            running_total = round(running_total + item_total, 2)
        allocated_totals.append(item_total)

    for item, item_total in zip(items, allocated_totals):
        unit_price = item_total / item.quantity if item.quantity > 0 else 0.0
        apply_actual_price(item, unit_price)


def recalculate_menu_values(menu: Menu, items: list[MenuItem]) -> None:
    total_cost = sum(item.cost_total for item in items)
    table_count = max(1, getattr(menu, "table_count", 1))

    if getattr(menu, "pricing_mode", "additive") == "fixed" and getattr(menu, "fixed_price", 0) > 0:
        distribute_fixed_price(items, menu.fixed_price)
        menu.total_price = round(menu.fixed_price * table_count, 2)
    else:
        restore_additive_prices(items)
        menu.total_price = round(sum(item.subtotal for item in items), 2)

    menu.total_cost = round(total_cost, 2)
    per_table_price = menu.total_price / table_count if table_count > 0 else menu.total_price
    per_table_cost = menu.total_cost / table_count if table_count > 0 else menu.total_cost
    menu.margin_rate = round(
        (per_table_price - per_table_cost) / per_table_price * 100, 1
    ) if per_table_price > 0 else 0.0
    menu.budget = menu.total_price
