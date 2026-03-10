from sqlmodel import SQLModel, Field


class PackageGroup(SQLModel, table=True):
    id: int | None = Field(default=None, primary_key=True)
    name: str = ""
    sort_order: int = 0
    is_active: bool = True


class Package(SQLModel, table=True):
    id: int | None = Field(default=None, primary_key=True)
    group_id: int = Field(default=0, foreign_key="packagegroup.id", index=True)
    name: str = ""
    description: str = ""
    base_price: float = 0.0
    default_pricing_mode: str = "additive"
    dish_count: int = 0
    sort_order: int = 0
    is_active: bool = True
    created_by: str = ""


class PackageItem(SQLModel, table=True):
    id: int | None = Field(default=None, primary_key=True)
    package_id: int = Field(foreign_key="package.id", index=True)
    dish_id: int = Field(foreign_key="dish.id")
    default_spec_id: int | None = None
    default_quantity: int = 1
    sort_order: int = 0
