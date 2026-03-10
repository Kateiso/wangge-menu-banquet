from urllib.parse import quote
from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import StreamingResponse
from sqlmodel import Session, select
from backend.models.dish import Dish
from backend.models.dish_spec import DishSpec
from backend.models.menu import Menu, MenuItem
from backend.models.user import User
from backend.models.schemas import (
    MenuGenerateRequest, MenuResponse, MenuItemResponse,
    MenuFromPackageRequest, MenuItemUpdateRequest, MenuItemAddRequest,
    MenuPricingUpdateRequest,
    AdjustRequest, AdjustResponse,
)
from backend.services.menu_engine import generate_menu
from backend.services.excel_generator import generate_excel, generate_margin_excel
from backend.services.adjustment_engine import analyze_adjustment_intent, execute_adjustment
from backend.services.spec_matcher import build_menu_from_package, match_spec
from backend.database import get_session
from backend.auth_utils import get_current_user

router = APIRouter(
    prefix="/api/menu",
    tags=["menu"],
)


def _build_menu_response(menu: Menu, items: list[MenuItem], role: str = "admin") -> MenuResponse:
    is_staff = role == "staff"
    return MenuResponse(
        id=menu.id,
        customer_name=menu.customer_name,
        mode=getattr(menu, 'mode', 'retail'),
        party_size=menu.party_size,
        budget=menu.budget,
        target_margin=menu.target_margin,
        occasion=menu.occasion,
        total_price=menu.total_price,
        total_cost=0.0 if is_staff else menu.total_cost,
        margin_rate=menu.margin_rate,
        reasoning=menu.reasoning,
        date=getattr(menu, 'date', ''),
        pricing_mode=getattr(menu, 'pricing_mode', 'additive'),
        fixed_price=getattr(menu, 'fixed_price', 0.0),
        table_count=getattr(menu, 'table_count', 1),
        items=[
            MenuItemResponse(
                id=item.id,
                dish_id=item.dish_id,
                dish_name=item.dish_name,
                price_text=item.price_text,
                price=item.price,
                min_price=0.0 if is_staff else getattr(item, 'min_price', 0.0),
                cost=0.0 if is_staff else item.cost,
                quantity=item.quantity,
                subtotal=item.subtotal,
                cost_total=0.0 if is_staff else item.cost_total,
                category=item.category,
                reason=item.reason,
                spec_id=getattr(item, 'spec_id', None),
                spec_name=getattr(item, 'spec_name', ''),
                adjusted_price=getattr(item, 'adjusted_price', 0.0),
            )
            for item in items
        ],
    )


@router.post("/generate", response_model=MenuResponse)
def api_generate_menu(
    request: MenuGenerateRequest,
    session: Session = Depends(get_session),
    current_user: User = Depends(get_current_user),
):
    """生成 AI 推荐菜单"""
    try:
        menu, items = generate_menu(session, request)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"菜单生成失败: {str(e)}")
    return _build_menu_response(menu, items, role=current_user.role)


@router.post("/from-package", response_model=MenuResponse)
def api_create_from_package(
    request: MenuFromPackageRequest,
    session: Session = Depends(get_session),
    current_user: User = Depends(get_current_user),
):
    """从套餐模板创建菜单实例"""
    try:
        menu, items = build_menu_from_package(
            session,
            package_id=request.package_id,
            party_size=request.party_size,
            table_count=request.table_count,
            customer_name=request.customer_name,
            date=request.date,
            pricing_mode=request.pricing_mode,
        )
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"创建菜单失败: {str(e)}")
    return _build_menu_response(menu, items, role=current_user.role)


@router.get("/{menu_id}", response_model=MenuResponse)
def api_get_menu(
    menu_id: str,
    session: Session = Depends(get_session),
    current_user: User = Depends(get_current_user),
):
    """获取菜单详情"""
    menu = session.get(Menu, menu_id)
    if not menu:
        raise HTTPException(status_code=404, detail="菜单不存在")
    items = list(session.exec(
        select(MenuItem).where(MenuItem.menu_id == menu_id)
    ).all())
    return _build_menu_response(menu, items, role=current_user.role)


@router.put("/{menu_id}/items/{item_id}", response_model=MenuItemResponse)
def api_update_menu_item(
    menu_id: str,
    item_id: int,
    data: MenuItemUpdateRequest,
    session: Session = Depends(get_session),
    current_user: User = Depends(get_current_user),
):
    """更新菜单项（价格/规格/数量）"""
    item = session.get(MenuItem, item_id)
    if not item or item.menu_id != menu_id:
        raise HTTPException(status_code=404, detail="菜单项不存在")

    if data.spec_id is not None:
        spec = session.get(DishSpec, data.spec_id)
        if spec and spec.dish_id == item.dish_id:
            item.spec_id = spec.id
            item.spec_name = spec.spec_name
            item.price = spec.price
            item.cost = spec.cost
            item.adjusted_price = spec.price

    if data.adjusted_price is not None:
        item.adjusted_price = data.adjusted_price

    if data.quantity is not None:
        item.quantity = max(1, data.quantity)

    # 重算小计
    effective_price = item.adjusted_price if item.adjusted_price > 0 else item.price
    item.subtotal = round(effective_price * item.quantity, 2)
    item.cost_total = round(item.cost * item.quantity, 2)

    session.add(item)
    session.flush()

    # 重算菜单汇总
    _recalculate_menu(session, menu_id)
    session.commit()
    session.refresh(item)

    is_staff = current_user.role == "staff"
    return MenuItemResponse(
        id=item.id,
        dish_id=item.dish_id,
        dish_name=item.dish_name,
        price_text=item.price_text,
        price=item.price,
        min_price=0.0 if is_staff else item.min_price,
        cost=0.0 if is_staff else item.cost,
        quantity=item.quantity,
        subtotal=item.subtotal,
        cost_total=0.0 if is_staff else item.cost_total,
        category=item.category,
        reason=item.reason,
        spec_id=item.spec_id,
        spec_name=item.spec_name,
        adjusted_price=item.adjusted_price,
    )


@router.post("/{menu_id}/items", response_model=MenuItemResponse, status_code=201)
def api_add_menu_item(
    menu_id: str,
    data: MenuItemAddRequest,
    session: Session = Depends(get_session),
    current_user: User = Depends(get_current_user),
):
    """添加菜品到菜单"""
    menu = session.get(Menu, menu_id)
    if not menu:
        raise HTTPException(status_code=404, detail="菜单不存在")

    dish = session.get(Dish, data.dish_id)
    if not dish:
        raise HTTPException(status_code=404, detail="菜品不存在")

    # 规格处理
    spec_id = data.spec_id
    spec_name = ""
    item_price = dish.price
    item_cost = dish.cost

    if spec_id:
        spec = session.get(DishSpec, spec_id)
        if spec and spec.dish_id == dish.id:
            item_price = spec.price
            item_cost = spec.cost
            spec_name = spec.spec_name
    else:
        # 自动匹配规格
        spec = match_spec(dish.id, menu.party_size, session)  # type: ignore
        if spec:
            spec_id = spec.id
            spec_name = spec.spec_name
            item_price = spec.price
            item_cost = spec.cost

    quantity = max(1, data.quantity)
    item = MenuItem(
        menu_id=menu_id,
        dish_id=dish.id,  # type: ignore
        dish_name=dish.name,
        price_text=dish.price_text,
        price=item_price,
        min_price=dish.min_price,
        cost=item_cost,
        quantity=quantity,
        subtotal=round(item_price * quantity, 2),
        cost_total=round(item_cost * quantity, 2),
        category=dish.category,
        spec_id=spec_id,
        spec_name=spec_name,
        adjusted_price=item_price,
    )
    session.add(item)
    session.flush()

    _recalculate_menu(session, menu_id)
    session.commit()
    session.refresh(item)

    is_staff = current_user.role == "staff"
    return MenuItemResponse(
        id=item.id,
        dish_id=item.dish_id,
        dish_name=item.dish_name,
        price_text=item.price_text,
        price=item.price,
        min_price=0.0 if is_staff else item.min_price,
        cost=0.0 if is_staff else item.cost,
        quantity=item.quantity,
        subtotal=item.subtotal,
        cost_total=0.0 if is_staff else item.cost_total,
        category=item.category,
        spec_id=item.spec_id,
        spec_name=item.spec_name,
        adjusted_price=item.adjusted_price,
    )


@router.delete("/{menu_id}/items/{item_id}", status_code=204)
def api_delete_menu_item(
    menu_id: str,
    item_id: int,
    session: Session = Depends(get_session),
    current_user: User = Depends(get_current_user),
):
    """删除菜单项"""
    item = session.get(MenuItem, item_id)
    if not item or item.menu_id != menu_id:
        raise HTTPException(status_code=404, detail="菜单项不存在")
    session.delete(item)
    session.flush()
    _recalculate_menu(session, menu_id)
    session.commit()


@router.put("/{menu_id}/pricing", response_model=MenuResponse)
def api_update_pricing(
    menu_id: str,
    data: MenuPricingUpdateRequest,
    session: Session = Depends(get_session),
    current_user: User = Depends(get_current_user),
):
    """切换定价模式/改固定价"""
    menu = session.get(Menu, menu_id)
    if not menu:
        raise HTTPException(status_code=404, detail="菜单不存在")

    if data.pricing_mode is not None:
        menu.pricing_mode = data.pricing_mode
    if data.fixed_price is not None:
        menu.fixed_price = data.fixed_price

    session.add(menu)
    session.flush()
    _recalculate_menu(session, menu_id)
    session.commit()
    session.refresh(menu)

    items = list(session.exec(
        select(MenuItem).where(MenuItem.menu_id == menu_id)
    ).all())
    return _build_menu_response(menu, items, role=current_user.role)


@router.post("/{menu_id}/adjust", response_model=AdjustResponse)
def api_adjust_menu(
    menu_id: str,
    request: AdjustRequest,
    session: Session = Depends(get_session),
    current_user: User = Depends(get_current_user),
):
    """调整菜单 — 对话或确认"""
    menu = session.get(Menu, menu_id)
    if not menu:
        raise HTTPException(status_code=404, detail="菜单不存在")

    if request.action == "confirm":
        if not request.conversation_id:
            raise HTTPException(status_code=400, detail="缺少 conversation_id")
        try:
            updated_menu, items = execute_adjustment(session, menu_id, request.conversation_id)
        except Exception as e:
            raise HTTPException(status_code=500, detail=f"执行调整失败: {str(e)}")
        return AdjustResponse(
            type="updated",
            message="菜单已更新",
            menu=_build_menu_response(updated_menu, items, role=current_user.role),
        )
    else:
        try:
            return analyze_adjustment_intent(session, menu_id, request.message)
        except Exception as e:
            raise HTTPException(status_code=500, detail=f"分析意图失败: {str(e)}")


@router.get("/{menu_id}/excel")
def api_download_excel(
    menu_id: str,
    format: str = "simple",
    session: Session = Depends(get_session),
    current_user: User = Depends(get_current_user),
):
    """下载 Excel 菜单（simple=普通菜单, margin=毛利核算表）"""
    menu = session.get(Menu, menu_id)
    if not menu:
        raise HTTPException(status_code=404, detail="菜单不存在")

    items = list(session.exec(
        select(MenuItem).where(MenuItem.menu_id == menu_id)
    ).all())
    if not items:
        raise HTTPException(status_code=404, detail="菜单无菜品数据")

    is_admin = current_user.role == "admin"

    if format == "margin":
        excel_file = generate_margin_excel(menu, items, is_admin=is_admin)
        filename = f"旺阁渔村_毛利核算_{menu.customer_name or '贵宾'}_{menu.party_size}人.xlsx"
    else:
        excel_file = generate_excel(menu, items)
        filename = f"旺阁渔村_菜单_{menu.customer_name or '贵宾'}_{menu.party_size}人.xlsx"

    encoded = quote(filename)
    return StreamingResponse(
        excel_file,
        media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        headers={"Content-Disposition": f"attachment; filename*=UTF-8''{encoded}"},
    )


def _recalculate_menu(session: Session, menu_id: str) -> None:
    """重算菜单汇总"""
    menu = session.get(Menu, menu_id)
    if not menu:
        return

    items = list(session.exec(
        select(MenuItem).where(MenuItem.menu_id == menu_id)
    ).all())

    total_cost = sum(item.cost_total for item in items)
    table_count = max(1, getattr(menu, 'table_count', 1))

    if getattr(menu, 'pricing_mode', 'additive') == 'fixed' and getattr(menu, 'fixed_price', 0) > 0:
        per_table = menu.fixed_price
        menu.total_price = round(per_table * table_count, 2)
    else:
        total_price = sum(item.subtotal for item in items)
        menu.total_price = round(total_price, 2)

    menu.total_cost = round(total_cost, 2)
    per_table_price = menu.total_price / table_count if table_count > 0 else menu.total_price
    per_table_cost = menu.total_cost / table_count if table_count > 0 else menu.total_cost
    menu.margin_rate = round(
        (per_table_price - per_table_cost) / per_table_price * 100, 1
    ) if per_table_price > 0 else 0.0
    menu.budget = menu.total_price

    session.add(menu)
