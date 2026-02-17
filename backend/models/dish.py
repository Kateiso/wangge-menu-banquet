from sqlmodel import SQLModel, Field


class Dish(SQLModel, table=True):
    id: int | None = Field(default=None, primary_key=True)
    name: str = Field(index=True)
    price_text: str = ''
    price: float = 0.0
    is_market_price: bool = False
    cost: float = 0.0
    min_price: float = 0.0
    category: str = ''
    tags: str = ''
    is_active: bool = True
    is_signature: bool = False
    is_must_order: bool = False
    serving_unit: str = ''
    serving_split: int = 0
