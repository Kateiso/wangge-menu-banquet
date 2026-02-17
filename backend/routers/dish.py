from fastapi import APIRouter, Depends, HTTPException
from sqlmodel import Session, select
from backend.models.dish import Dish
from backend.models.user import User
from backend.database import get_session
from backend.auth_utils import get_current_user
from typing import Optional
from pydantic import BaseModel

router = APIRouter(prefix="/api/dishes", tags=["dishes"])

class DishUpdate(BaseModel):
    name: Optional[str] = None
    price_text: Optional[str] = None
    price: Optional[float] = None
    cost: Optional[float] = None  # Admin only
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
    current_user: User = Depends(get_current_user)
):
    query = select(Dish)
    if category:
        query = query.where(Dish.category == category)
    if active_only:
        query = query.where(Dish.is_active == True)
    
    return session.exec(query).all()

@router.put("/{dish_id}")
def update_dish(
    dish_id: int,
    updates: DishUpdate,
    session: Session = Depends(get_session),
    current_user: User = Depends(get_current_user)
):
    dish = session.get(Dish, dish_id)
    if not dish:
        raise HTTPException(status_code=404, detail="菜品不存在")
        
    # Permission checks
    restricted_fields = ["cost", "price", "price_text"]
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
