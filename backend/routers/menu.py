from urllib.parse import quote
from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import StreamingResponse
from sqlmodel import Session, select
from backend.models.menu import Menu, MenuItem
from backend.models.schemas import (
    MenuGenerateRequest, MenuResponse, MenuItemResponse,
    AdjustRequest, AdjustResponse,
)
from backend.services.menu_engine import generate_menu
from backend.services.excel_generator import generate_excel
from backend.services.adjustment_engine import analyze_adjustment_intent, execute_adjustment
from backend.database import get_session
from backend.auth_utils import get_current_user

router = APIRouter(
    prefix="/api/menu", 
    tags=["menu"],
    dependencies=[Depends(get_current_user)]
)


def _build_menu_response(menu: Menu, items: list[MenuItem], date: str = "") -> MenuResponse:
    return MenuResponse(
        id=menu.id,
        customer_name=menu.customer_name,
        party_size=menu.party_size,
        budget=menu.budget,
        target_margin=menu.target_margin,
        occasion=menu.occasion,
        total_price=menu.total_price,
        total_cost=menu.total_cost,
        margin_rate=menu.margin_rate,
        reasoning=menu.reasoning,
        date=date,
        items=[
            MenuItemResponse(
                dish_id=item.dish_id,
                dish_name=item.dish_name,
                price_text=item.price_text,
                price=item.price,
                cost=item.cost,
                quantity=item.quantity,
                subtotal=item.subtotal,
                cost_total=item.cost_total,
                category=item.category,
                reason=item.reason,
            )
            for item in items
        ],
    )

@router.post("/generate", response_model=MenuResponse)
def api_generate_menu(
    request: MenuGenerateRequest,
    session: Session = Depends(get_session),
):
    """生成 AI 推荐菜单"""
    try:
        menu, items = generate_menu(session, request)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=f"菜单生成失败: {str(e)}")
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"菜单生成失败: {str(e)}")

    return _build_menu_response(menu, items, date=request.date)


@router.post("/{menu_id}/adjust", response_model=AdjustResponse)
def api_adjust_menu(
    menu_id: str,
    request: AdjustRequest,
    session: Session = Depends(get_session),
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
            menu=_build_menu_response(updated_menu, items),
        )
    else:
        try:
            return analyze_adjustment_intent(session, menu_id, request.message)
        except Exception as e:
            raise HTTPException(status_code=500, detail=f"分析意图失败: {str(e)}")


@router.get("/{menu_id}/excel")
def api_download_excel(
    menu_id: str,
    session: Session = Depends(get_session),
):
    """下载 Excel 菜单"""
    menu = session.get(Menu, menu_id)
    if not menu:
        raise HTTPException(status_code=404, detail="菜单不存在")

    items = list(session.exec(
        select(MenuItem).where(MenuItem.menu_id == menu_id)
    ).all())

    if not items:
        raise HTTPException(status_code=404, detail="菜单无菜品数据")

    excel_file = generate_excel(menu, items)

    filename = f"旺阁渔村_菜单_{menu.customer_name or '贵宾'}_{menu.party_size}人.xlsx"
    encoded = quote(filename)

    return StreamingResponse(
        excel_file,
        media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        headers={"Content-Disposition": f"attachment; filename*=UTF-8''{encoded}"},
    )
