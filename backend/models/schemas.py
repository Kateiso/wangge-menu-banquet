from pydantic import BaseModel
from typing import Optional


class MenuGenerateRequest(BaseModel):
    customer_name: str = ""
    party_size: int
    budget: float
    target_margin: float = 55.0
    occasion: str = ""
    preferences: str = ""  # 偏好备注
    date: str = ""  # 日期


class MenuItemResponse(BaseModel):
    dish_id: int
    dish_name: str
    price_text: str
    price: float
    cost: float
    quantity: int
    subtotal: float
    cost_total: float
    category: str
    reason: str = ""


class MenuResponse(BaseModel):
    id: str
    customer_name: str
    party_size: int
    budget: float
    target_margin: float
    occasion: str
    total_price: float
    total_cost: float
    margin_rate: float
    reasoning: str
    items: list[MenuItemResponse]
    date: str = ""


class AuthRequest(BaseModel):
    password: str
