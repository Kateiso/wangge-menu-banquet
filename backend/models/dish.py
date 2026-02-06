from sqlmodel import SQLModel, Field


class Dish(SQLModel, table=True):
    id: int | None = Field(default=None, primary_key=True)
    name: str = Field(index=True)
    price_text: str = ""
    price: float = 0.0
    is_market_price: bool = False
    cost: float = 0.0
    category: str = ""
    tags: str = ""
    is_active: bool = True
