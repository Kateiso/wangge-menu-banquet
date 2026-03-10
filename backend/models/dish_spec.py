from sqlmodel import SQLModel, Field


class DishSpec(SQLModel, table=True):
    id: int | None = Field(default=None, primary_key=True)
    dish_id: int = Field(foreign_key="dish.id", index=True)
    spec_name: str = ""
    price: float = 0.0
    price_text: str = ""
    cost: float = 0.0
    min_people: int = 0
    max_people: int = 0
    is_default: bool = False
    sort_order: int = 0
    is_active: bool = True
