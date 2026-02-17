from pydantic import BaseModel
from typing import List, Optional


class MenuGenerateRequest(BaseModel):
    customer_name: str = ''
    party_size: int = 10
    budget: float = 2000.0
    target_margin: float = 60.0
    occasion: Optional[str] = None
    preferences: Optional[str] = None
    date: str = ''
    mode: str = 'retail'

class MenuItemResponse(BaseModel):
    dish_id: int
    dish_name: str
    price_text: str = ''
    price: float = 0.0
    min_price: float = 0.0
    cost: float = 0.0
    quantity: int = 1
    subtotal: float = 0.0
    cost_total: float = 0.0
    category: str = ''
    reason: Optional[str] = None

class MenuResponse(BaseModel):
    id: Optional[str]
    customer_name: str
    mode: str = 'retail'
    party_size: int
    budget: float
    target_margin: float
    occasion: Optional[str]
    total_price: float
    total_cost: float
    margin_rate: float
    reasoning: Optional[str]
    date: str = ''
    items: List[MenuItemResponse]

class AdjustRequest(BaseModel):
    action: str = 'chat'
    message: str = ''
    conversation_id: Optional[int] = None


class AdjustmentAction(BaseModel):
    remove: List[int] = []
    add: List[dict] = []


class AdjustResponse(BaseModel):
    type: str
    message: str
    action: Optional[AdjustmentAction] = None
    menu: Optional[MenuResponse] = None
    options: Optional[List[str]] = None
    conversation_id: Optional[int] = None
