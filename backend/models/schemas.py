from pydantic import BaseModel
from typing import List, Optional


# ── Dish Spec ──

class DishSpecCreate(BaseModel):
    spec_name: str
    price: float
    price_text: str = ""
    cost: float = 0.0
    min_people: int = 0
    max_people: int = 0
    is_default: bool = False
    sort_order: int = 0


class DishSpecUpdate(BaseModel):
    spec_name: Optional[str] = None
    price: Optional[float] = None
    price_text: Optional[str] = None
    cost: Optional[float] = None
    min_people: Optional[int] = None
    max_people: Optional[int] = None
    is_default: Optional[bool] = None
    sort_order: Optional[int] = None
    is_active: Optional[bool] = None


class DishSpecResponse(BaseModel):
    id: int
    dish_id: int
    spec_name: str
    price: float
    price_text: str
    cost: float
    min_people: int
    max_people: int
    is_default: bool
    sort_order: int
    is_active: bool


# ── Package ──

class PackageGroupCreate(BaseModel):
    name: str
    sort_order: int = 0


class PackageGroupUpdate(BaseModel):
    name: Optional[str] = None
    sort_order: Optional[int] = None
    is_active: Optional[bool] = None


class PackageGroupResponse(BaseModel):
    id: int
    name: str
    sort_order: int
    is_active: bool
    packages: List['PackageSummary'] = []


class PackageSummary(BaseModel):
    id: int
    name: str
    description: str
    base_price: float
    default_pricing_mode: str
    dish_count: int
    sort_order: int
    is_active: bool
    created_by: str


class PackageItemCreate(BaseModel):
    dish_id: int
    default_spec_id: Optional[int] = None
    default_quantity: int = 1
    override_price: Optional[float] = None
    sort_order: int = 0


class PackageItemDetail(BaseModel):
    id: int
    dish_id: int
    dish_name: str
    category: str
    price: float
    price_text: str
    cost: float
    default_spec_id: Optional[int] = None
    default_spec_name: str = ""
    default_quantity: int
    override_price: Optional[float] = None
    sort_order: int
    specs: List[DishSpecResponse] = []


class PackageItemUpdate(BaseModel):
    default_spec_id: Optional[int] = None
    default_quantity: Optional[int] = None
    override_price: Optional[float] = None
    sort_order: Optional[int] = None


class PackageCreate(BaseModel):
    group_id: int
    name: str
    description: str = ""
    base_price: float = 0.0
    default_pricing_mode: str = "additive"
    items: List[PackageItemCreate] = []


class PackageUpdate(BaseModel):
    name: Optional[str] = None
    group_id: Optional[int] = None
    description: Optional[str] = None
    base_price: Optional[float] = None
    default_pricing_mode: Optional[str] = None
    sort_order: Optional[int] = None
    is_active: Optional[bool] = None


class PackageDetail(BaseModel):
    id: int
    group_id: int
    name: str
    description: str
    base_price: float
    default_pricing_mode: str
    dish_count: int
    sort_order: int
    is_active: bool
    created_by: str
    items: List[PackageItemDetail] = []


class PackageItemReorder(BaseModel):
    item_ids: List[int]


# ── Menu (updated) ──

class MenuFromPackageRequest(BaseModel):
    customer_name: str = ''
    date: str = ''
    party_size: int = 10
    table_count: int = 1
    package_id: int
    pricing_mode: str = 'additive'


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
    id: Optional[int] = None
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
    spec_id: Optional[int] = None
    spec_name: str = ''
    additive_price: float = 0.0
    adjusted_price: float = 0.0


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
    pricing_mode: str = 'additive'
    fixed_price: float = 0.0
    table_count: int = 1
    items: List[MenuItemResponse]


class MenuItemUpdateRequest(BaseModel):
    adjusted_price: Optional[float] = None
    spec_id: Optional[int] = None
    quantity: Optional[int] = None


class MenuItemAddRequest(BaseModel):
    dish_id: int
    spec_id: Optional[int] = None
    quantity: int = 1


class MenuPricingUpdateRequest(BaseModel):
    pricing_mode: Optional[str] = None
    fixed_price: Optional[float] = None


# ── Adjust (unchanged) ──

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


# ── AI Package Creation ──

class AIPackageCreateRequest(BaseModel):
    description: str
    group_id: int
