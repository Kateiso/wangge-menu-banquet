from datetime import datetime
import uuid
from sqlmodel import SQLModel, Field


def generate_uuid() -> str:
    return str(uuid.uuid4())


class Menu(SQLModel, table=True):
    id: str = Field(default_factory=generate_uuid, primary_key=True)
    customer_name: str = ''
    mode: str = 'retail'
    party_size: int = 0
    budget: float = 0.0
    target_margin: float = 0.0
    occasion: str = ''
    preferences: str = ''
    reasoning: str = ''
    total_price: float = 0.0
    total_cost: float = 0.0
    margin_rate: float = 0.0
    pricing_mode: str = 'additive'
    fixed_price: float = 0.0
    table_count: int = 1
    date: str = ''
    created_at: datetime = Field(default_factory=datetime.now)


class MenuItem(SQLModel, table=True):
    id: int | None = Field(default=None, primary_key=True)
    menu_id: str = Field(default="", foreign_key='menu.id', index=True)
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
    reason: str = ''
    spec_id: int | None = None
    spec_name: str = ''
    additive_price: float = 0.0
    adjusted_price: float = 0.0
