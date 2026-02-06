from datetime import datetime
import uuid
from sqlmodel import SQLModel, Field


def generate_uuid() -> str:
    return str(uuid.uuid4())


class Menu(SQLModel, table=True):
    id: str = Field(default_factory=generate_uuid, primary_key=True)
    customer_name: str = ""
    party_size: int = 0
    budget: float = 0.0
    target_margin: float = 55.0
    occasion: str = ""
    preferences: str = ""
    total_price: float = 0.0
    total_cost: float = 0.0
    margin_rate: float = 0.0
    reasoning: str = ""
    created_at: datetime = Field(default_factory=datetime.now)


class MenuItem(SQLModel, table=True):
    id: int | None = Field(default=None, primary_key=True)
    menu_id: str = Field(default="", foreign_key="menu.id", index=True)
    dish_id: int = Field(default=0, foreign_key="dish.id")
    dish_name: str = ""
    price_text: str = ""
    price: float = 0.0
    cost: float = 0.0
    quantity: int = 0
    subtotal: float = 0.0
    cost_total: float = 0.0
    category: str = ""
    reason: str = ""
