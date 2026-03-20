from sqlmodel import Session, select
from backend.models.dish import Dish
from backend.models.dish_spec import DishSpec
from backend.models.package import PackageGroup, Package, PackageItem
from backend.models.schemas import (
    PackageGroupResponse, PackageSummary, PackageDetail, PackageItemDetail,
    DishSpecResponse,
)


# ── PackageGroup CRUD ──

def list_groups_with_packages(session: Session) -> list[PackageGroupResponse]:
    groups = list(session.exec(
        select(PackageGroup)
        .where(PackageGroup.is_active == True)
        .order_by(PackageGroup.sort_order)
    ).all())

    result = []
    for g in groups:
        packages = list(session.exec(
            select(Package)
            .where(Package.group_id == g.id, Package.is_active == True)
            .order_by(Package.sort_order)
        ).all())
        result.append(PackageGroupResponse(
            id=g.id,  # type: ignore
            name=g.name,
            sort_order=g.sort_order,
            is_active=g.is_active,
            packages=[
                PackageSummary(
                    id=p.id,  # type: ignore
                    name=p.name,
                    description=p.description,
                    base_price=p.base_price,
                    default_pricing_mode=p.default_pricing_mode,
                    dish_count=p.dish_count,
                    sort_order=p.sort_order,
                    is_active=p.is_active,
                    created_by=p.created_by,
                )
                for p in packages
            ],
        ))
    return result


def create_group(session: Session, name: str, sort_order: int = 0) -> PackageGroup:
    group = PackageGroup(name=name, sort_order=sort_order)
    session.add(group)
    session.commit()
    session.refresh(group)
    return group


def update_group(session: Session, group_id: int, **kwargs) -> PackageGroup:
    group = session.get(PackageGroup, group_id)
    if not group:
        raise ValueError("分组不存在")
    for k, v in kwargs.items():
        if v is not None:
            setattr(group, k, v)
    session.add(group)
    session.commit()
    session.refresh(group)
    return group


def delete_group(session: Session, group_id: int) -> None:
    group = session.get(PackageGroup, group_id)
    if not group:
        raise ValueError("分组不存在")

    active_packages = list(session.exec(
        select(Package).where(Package.group_id == group_id, Package.is_active == True)
    ).all())
    if active_packages:
        raise ValueError("分组下仍有套餐，请先清空后再删除")

    group.is_active = False
    session.add(group)
    session.commit()


# ── Package CRUD ──

def get_package_detail(session: Session, package_id: int) -> PackageDetail:
    package = session.get(Package, package_id)
    if not package:
        raise ValueError("套餐不存在")

    pkg_items = list(session.exec(
        select(PackageItem)
        .where(PackageItem.package_id == package_id)
        .order_by(PackageItem.sort_order)
    ).all())

    items_detail = []
    for pi in pkg_items:
        dish = session.get(Dish, pi.dish_id)
        if not dish:
            continue

        # 获取该菜品的所有规格
        specs = list(session.exec(
            select(DishSpec)
            .where(DishSpec.dish_id == pi.dish_id, DishSpec.is_active == True)
            .order_by(DishSpec.sort_order)
        ).all())

        default_spec_name = ""
        if pi.default_spec_id:
            for s in specs:
                if s.id == pi.default_spec_id:
                    default_spec_name = s.spec_name
                    break

        items_detail.append(PackageItemDetail(
            id=pi.id,  # type: ignore
            dish_id=pi.dish_id,
            dish_name=dish.name,
            category=dish.category,
            price=dish.price,
            price_text=dish.price_text,
            cost=dish.cost,
            default_spec_id=pi.default_spec_id,
            default_spec_name=default_spec_name,
            default_quantity=pi.default_quantity,
            sort_order=pi.sort_order,
            specs=[
                DishSpecResponse(
                    id=s.id,  # type: ignore
                    dish_id=s.dish_id,
                    spec_name=s.spec_name,
                    price=s.price,
                    price_text=s.price_text,
                    cost=s.cost,
                    min_people=s.min_people,
                    max_people=s.max_people,
                    is_default=s.is_default,
                    sort_order=s.sort_order,
                    is_active=s.is_active,
                )
                for s in specs
            ],
        ))

    return PackageDetail(
        id=package.id,  # type: ignore
        group_id=package.group_id,
        name=package.name,
        description=package.description,
        base_price=package.base_price,
        default_pricing_mode=package.default_pricing_mode,
        dish_count=package.dish_count,
        sort_order=package.sort_order,
        is_active=package.is_active,
        created_by=package.created_by,
        items=items_detail,
    )


def create_package(session: Session, group_id: int, name: str, description: str = "",
                   base_price: float = 0.0, default_pricing_mode: str = "additive",
                   items: list | None = None, created_by: str = "") -> Package:
    package = Package(
        group_id=group_id,
        name=name,
        description=description,
        base_price=base_price,
        default_pricing_mode=default_pricing_mode,
        created_by=created_by,
    )
    session.add(package)
    session.flush()

    if items:
        for i, item_data in enumerate(items):
            pi = PackageItem(
                package_id=package.id,  # type: ignore
                dish_id=item_data.dish_id,
                default_spec_id=item_data.default_spec_id,
                default_quantity=item_data.default_quantity,
                sort_order=item_data.sort_order or i,
            )
            session.add(pi)
        package.dish_count = len(items)
    else:
        package.dish_count = 0

    session.commit()
    session.refresh(package)
    return package


def update_package(session: Session, package_id: int, **kwargs) -> Package:
    package = session.get(Package, package_id)
    if not package:
        raise ValueError("套餐不存在")
    for k, v in kwargs.items():
        if v is not None:
            setattr(package, k, v)
    session.add(package)
    session.commit()
    session.refresh(package)
    return package


def delete_package(session: Session, package_id: int) -> None:
    package = session.get(Package, package_id)
    if not package:
        raise ValueError("套餐不存在")
    package.is_active = False
    session.add(package)
    session.commit()


# ── PackageItem operations ──

def add_package_item(session: Session, package_id: int, dish_id: int,
                     default_spec_id: int | None = None,
                     default_quantity: int = 1, sort_order: int = 0) -> PackageItem:
    package = session.get(Package, package_id)
    if not package:
        raise ValueError("套餐不存在")

    pi = PackageItem(
        package_id=package_id,
        dish_id=dish_id,
        default_spec_id=default_spec_id,
        default_quantity=default_quantity,
        sort_order=sort_order,
    )
    session.add(pi)
    package.dish_count = _count_items(session, package_id) + 1
    session.add(package)
    session.commit()
    session.refresh(pi)
    return pi


def remove_package_item(session: Session, item_id: int) -> None:
    pi = session.get(PackageItem, item_id)
    if not pi:
        raise ValueError("套餐菜品不存在")
    package_id = pi.package_id
    session.delete(pi)
    session.flush()

    package = session.get(Package, package_id)
    if package:
        package.dish_count = _count_items(session, package_id)
        session.add(package)
    session.commit()


def reorder_package_items(session: Session, package_id: int, item_ids: list[int]) -> None:
    for i, item_id in enumerate(item_ids):
        pi = session.get(PackageItem, item_id)
        if pi and pi.package_id == package_id:
            pi.sort_order = i
            session.add(pi)
    session.commit()


def _count_items(session: Session, package_id: int) -> int:
    items = list(session.exec(
        select(PackageItem).where(PackageItem.package_id == package_id)
    ).all())
    return len(items)
