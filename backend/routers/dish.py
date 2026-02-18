from fastapi import APIRouter, Depends, HTTPException
from sqlmodel import Session, select
from backend.models.dish import Dish
from backend.models.user import User
from backend.database import get_session
from backend.auth_utils import get_current_user, get_current_admin
from backend.services.dish_service import get_category_cost_ratio
from typing import Optional
from pydantic import BaseModel

router = APIRouter(prefix="/api/dishes", tags=["dishes"])
require_admin = get_current_admin


class DishCreate(BaseModel):
    name: str
    category: str
    price: float
    price_text: str
    serving_unit: str = "例"
    serving_split: int = 0
    is_signature: bool = False
    is_must_order: bool = False


class DishUpdate(BaseModel):
    name: Optional[str] = None
    price_text: Optional[str] = None
    price: Optional[float] = None
    cost: Optional[float] = None  # Admin only
    min_price: Optional[float] = None  # Admin only
    category: Optional[str] = None
    is_active: Optional[bool] = None
    is_signature: Optional[bool] = None
    is_must_order: Optional[bool] = None
    serving_unit: Optional[str] = None
    serving_split: Optional[int] = None


@router.get("")
def list_dishes(
    category: Optional[str] = None,
    active_only: bool = False,
    session: Session = Depends(get_session),
    current_user: User = Depends(get_current_user),
):
    query = select(Dish)
    if category:
        query = query.where(Dish.category == category)
    if active_only:
        query = query.where(Dish.is_active == True)

    return session.exec(query).all()


@router.post("", response_model=Dish, status_code=201)
def create_dish(
    dish: DishCreate,
    session: Session = Depends(get_session),
    current_user: User = Depends(require_admin),
):
    name = dish.name.strip()
    category = dish.category.strip()
    price_text = dish.price_text.strip()
    serving_unit = (dish.serving_unit or "例").strip() or "例"

    if not name:
        raise HTTPException(status_code=400, detail="菜名不能为空")
    if not category:
        raise HTTPException(status_code=400, detail="分类不能为空")
    if dish.price <= 0:
        raise HTTPException(status_code=400, detail="价格必须大于0")

    ratio = get_category_cost_ratio(category)
    price = round(float(dish.price), 2)
    cost = round(price * ratio, 2)
    min_price = round(cost * 1.3, 2)

    if not price_text:
        price_text = f"{price:.2f}元/{serving_unit}"

    db_dish = Dish(
        name=name,
        category=category,
        price=price,
        price_text=price_text,
        serving_unit=serving_unit,
        serving_split=max(0, int(dish.serving_split)),
        is_signature=bool(dish.is_signature),
        is_must_order=bool(dish.is_must_order),
        cost=cost,
        min_price=min_price,
        is_market_price="时价" in price_text,
        is_active=True,
    )
    session.add(db_dish)
    session.commit()
    session.refresh(db_dish)
    return db_dish


@router.put("/{dish_id}")
def update_dish(
    dish_id: int,
    updates: DishUpdate,
    session: Session = Depends(get_session),
    current_user: User = Depends(get_current_user),
):
    dish = session.get(Dish, dish_id)
    if not dish:
        raise HTTPException(status_code=404, detail="菜品不存在")

    # Permission checks
    restricted_fields = ["cost", "price", "price_text", "min_price"]
    update_data = updates.model_dump(exclude_unset=True)

    for field in restricted_fields:
        if field in update_data:
            if current_user.role != "admin":
                raise HTTPException(status_code=403, detail="需要管理员权限才能修改价格或成本")

    # Apply updates
    for key, value in update_data.items():
        setattr(dish, key, value)

    session.add(dish)
    session.commit()
    session.refresh(dish)
    return dish
