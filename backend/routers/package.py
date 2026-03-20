from fastapi import APIRouter, Depends, HTTPException
from sqlmodel import Session
from backend.database import get_session
from backend.auth_utils import get_current_user
from backend.models.user import User
from backend.models.schemas import (
    PackageGroupCreate, PackageGroupUpdate, PackageGroupResponse,
    PackageCreate, PackageUpdate, PackageDetail,
    PackageItemCreate, PackageItemReorder,
    AIPackageCreateRequest,
)
from backend.services.package_service import (
    list_groups_with_packages, create_group, update_group, delete_group,
    get_package_detail, create_package, update_package, delete_package,
    add_package_item, remove_package_item, reorder_package_items,
)

router = APIRouter(
    prefix="/api/packages",
    tags=["packages"],
    dependencies=[Depends(get_current_user)],
)


# ── PackageGroup ──

@router.get("/groups", response_model=list[PackageGroupResponse])
def api_list_groups(session: Session = Depends(get_session)):
    return list_groups_with_packages(session)


@router.post("/groups", response_model=PackageGroupResponse, status_code=201)
def api_create_group(
    data: PackageGroupCreate,
    session: Session = Depends(get_session),
):
    group = create_group(session, name=data.name, sort_order=data.sort_order)
    return PackageGroupResponse(
        id=group.id, name=group.name,  # type: ignore
        sort_order=group.sort_order, is_active=group.is_active, packages=[],
    )


@router.put("/groups/{group_id}", response_model=PackageGroupResponse)
def api_update_group(
    group_id: int,
    data: PackageGroupUpdate,
    session: Session = Depends(get_session),
):
    try:
        group = update_group(session, group_id, **data.model_dump(exclude_unset=True))
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))
    return PackageGroupResponse(
        id=group.id, name=group.name,  # type: ignore
        sort_order=group.sort_order, is_active=group.is_active, packages=[],
    )


@router.delete("/groups/{group_id}", status_code=204)
def api_delete_group(
    group_id: int,
    session: Session = Depends(get_session),
):
    try:
        delete_group(session, group_id)
    except ValueError as e:
        detail = str(e)
        if detail == "分组下仍有套餐，请先清空后再删除":
            raise HTTPException(status_code=400, detail=detail)
        raise HTTPException(status_code=404, detail=detail)


# ── Package ──

@router.get("/{package_id}", response_model=PackageDetail)
def api_get_package(
    package_id: int,
    session: Session = Depends(get_session),
):
    try:
        return get_package_detail(session, package_id)
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))


@router.post("", status_code=201)
def api_create_package(
    data: PackageCreate,
    session: Session = Depends(get_session),
    current_user: User = Depends(get_current_user),
):
    package = create_package(
        session,
        group_id=data.group_id,
        name=data.name,
        description=data.description,
        base_price=data.base_price,
        default_pricing_mode=data.default_pricing_mode,
        items=data.items if data.items else None,
        created_by=current_user.username,
    )
    return {"id": package.id, "name": package.name}


@router.put("/{package_id}")
def api_update_package(
    package_id: int,
    data: PackageUpdate,
    session: Session = Depends(get_session),
):
    try:
        package = update_package(session, package_id, **data.model_dump(exclude_unset=True))
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))
    return {"id": package.id, "name": package.name}


@router.delete("/{package_id}", status_code=204)
def api_delete_package(
    package_id: int,
    session: Session = Depends(get_session),
):
    try:
        delete_package(session, package_id)
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))


# ── PackageItem ──

@router.post("/{package_id}/items", status_code=201)
def api_add_item(
    package_id: int,
    data: PackageItemCreate,
    session: Session = Depends(get_session),
):
    try:
        pi = add_package_item(
            session, package_id,
            dish_id=data.dish_id,
            default_spec_id=data.default_spec_id,
            default_quantity=data.default_quantity,
            sort_order=data.sort_order,
        )
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))
    return {"id": pi.id}


@router.delete("/items/{item_id}", status_code=204)
def api_remove_item(
    item_id: int,
    session: Session = Depends(get_session),
):
    try:
        remove_package_item(session, item_id)
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))


@router.put("/{package_id}/items/reorder", status_code=204)
def api_reorder_items(
    package_id: int,
    data: PackageItemReorder,
    session: Session = Depends(get_session),
):
    reorder_package_items(session, package_id, data.item_ids)


# ── AI Create ──

@router.post("/ai-create", status_code=201)
def api_ai_create_package(
    data: AIPackageCreateRequest,
    session: Session = Depends(get_session),
    current_user: User = Depends(get_current_user),
):
    from backend.services.ai_package_creator import create_package_from_description
    try:
        package = create_package_from_description(
            session, data.description, data.group_id, current_user.username,
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"AI 创建套餐失败: {str(e)}")
    return {"id": package.id, "name": package.name}
