const BASE = '';

function getToken(): string {
  return localStorage.getItem('wg_token') || '';
}

function headers(): Record<string, string> {
  return {
    'Content-Type': 'application/json',
    Authorization: `Bearer ${getToken()}`,
  };
}

async function readErrorMessage(res: Response, fallback: string): Promise<string> {
  const err = await res.json().catch(() => ({ detail: fallback }));
  return err.detail || fallback;
}

export interface User {
  username: string;
  role: string;
  full_name?: string;
}

export async function login(username: string, pass: string): Promise<User> {
  const res = await fetch(`${BASE}/api/auth/login`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ username, password: pass }),
  });
  if (!res.ok) throw new Error("用户名或密码错误");

  const data = await res.json();
  localStorage.setItem('wg_token', data.access_token);
  return { username: data.username, role: data.role, full_name: data.full_name };
}

export async function getMe(): Promise<User> {
  const token = getToken();
  if (!token) throw new Error("not logged in");
  const res = await fetch(`${BASE}/api/auth/me`, { headers: headers() });
  if (!res.ok) throw new Error("未授权");
  return res.json();
}

// ── Dish ──

export interface Dish {
  id: number;
  name: string;
  price_text: string;
  price: number;
  min_price: number;
  cost: number;
  category: string;
  is_active: boolean;
  tags?: string;
  is_signature?: boolean;
  is_must_order?: boolean;
  serving_unit?: string;
  serving_split?: number;
}

export async function getDishes(params?: { category?: string; active_only?: boolean }): Promise<Dish[]> {
  const url = new URL(`${window.location.origin}${BASE}/api/dishes`);
  if (params?.category) url.searchParams.set("category", params.category);
  if (params?.active_only) url.searchParams.set("active_only", "true");
  const res = await fetch(url.toString(), { headers: headers() });
  if (!res.ok) throw new Error("获取菜品失败");
  return res.json();
}

export async function updateDish(id: number, updates: Partial<Dish>): Promise<Dish> {
  const res = await fetch(`${BASE}/api/dishes/${id}`, {
    method: 'PUT',
    headers: headers(),
    body: JSON.stringify(updates),
  });
  if (!res.ok) throw new Error("更新菜品失败");
  return res.json();
}

export interface DishCreateData {
  name: string;
  category: string;
  price: number;
  price_text: string;
}

export async function createDish(data: DishCreateData): Promise<Dish> {
  const res = await fetch(`${BASE}/api/dishes`, {
    method: 'POST',
    headers: headers(),
    body: JSON.stringify(data),
  });
  if (!res.ok) {
    const err = await res.json().catch(() => ({ detail: '新增菜品失败' }));
    throw new Error(err.detail || '新增菜品失败');
  }
  return res.json();
}

// ── DishSpec ──

export interface DishSpec {
  id: number;
  dish_id: number;
  spec_name: string;
  price: number;
  price_text: string;
  cost: number;
  min_people: number;
  max_people: number;
  is_default: boolean;
  sort_order: number;
  is_active: boolean;
}

export async function getDishSpecs(dishId: number): Promise<DishSpec[]> {
  const res = await fetch(`${BASE}/api/dishes/${dishId}/specs`, { headers: headers() });
  if (!res.ok) throw new Error("获取规格失败");
  return res.json();
}

export async function getBatchDishSpecs(dishIds: number[]): Promise<Record<number, DishSpec[]>> {
  const res = await fetch(`${BASE}/api/dishes/specs/batch?dish_ids=${dishIds.join(",")}`, { headers: headers() });
  if (!res.ok) throw new Error("获取规格失败");
  return res.json();
}

export async function createDishSpec(dishId: number, data: Omit<DishSpec, 'id' | 'dish_id' | 'is_active'>): Promise<DishSpec> {
  const res = await fetch(`${BASE}/api/dishes/${dishId}/specs`, {
    method: 'POST',
    headers: headers(),
    body: JSON.stringify(data),
  });
  if (!res.ok) throw new Error("创建规格失败");
  return res.json();
}

export async function updateDishSpec(specId: number, data: Partial<DishSpec>): Promise<DishSpec> {
  const res = await fetch(`${BASE}/api/dishes/specs/${specId}`, {
    method: 'PUT',
    headers: headers(),
    body: JSON.stringify(data),
  });
  if (!res.ok) throw new Error("更新规格失败");
  return res.json();
}

export async function deleteDishSpec(specId: number): Promise<void> {
  const res = await fetch(`${BASE}/api/dishes/specs/${specId}`, {
    method: 'DELETE',
    headers: headers(),
  });
  if (!res.ok) throw new Error("删除规格失败");
}

// ── Package ──

export interface PackageSummary {
  id: number;
  name: string;
  description: string;
  base_price: number;
  default_pricing_mode: string;
  dish_count: number;
  sort_order: number;
  is_active: boolean;
  created_by: string;
}

export interface PackageGroup {
  id: number;
  name: string;
  sort_order: number;
  is_active: boolean;
  packages: PackageSummary[];
}

export interface PackageItemDetail {
  id: number;
  dish_id: number;
  dish_name: string;
  category: string;
  price: number;
  price_text: string;
  cost: number;
  default_spec_id: number | null;
  default_spec_name: string;
  default_quantity: number;
  override_price: number | null;
  sort_order: number;
  specs: DishSpec[];
}

export interface PackageDetail {
  id: number;
  group_id: number;
  name: string;
  description: string;
  base_price: number;
  default_pricing_mode: string;
  dish_count: number;
  sort_order: number;
  is_active: boolean;
  created_by: string;
  items: PackageItemDetail[];
}

export async function getPackageGroups(): Promise<PackageGroup[]> {
  const res = await fetch(`${BASE}/api/packages/groups`, { headers: headers() });
  if (!res.ok) throw new Error("获取套餐分组失败");
  return res.json();
}

export async function createPackageGroup(name: string, sort_order: number = 0): Promise<PackageGroup> {
  const res = await fetch(`${BASE}/api/packages/groups`, {
    method: 'POST',
    headers: headers(),
    body: JSON.stringify({ name, sort_order }),
  });
  if (!res.ok) throw new Error(await readErrorMessage(res, '创建分组失败'));
  return res.json();
}

export async function updatePackageGroup(id: number, data: { name?: string; sort_order?: number }): Promise<PackageGroup> {
  const res = await fetch(`${BASE}/api/packages/groups/${id}`, {
    method: 'PUT',
    headers: headers(),
    body: JSON.stringify(data),
  });
  if (!res.ok) throw new Error(await readErrorMessage(res, '更新分组失败'));
  return res.json();
}

export async function deletePackageGroup(id: number): Promise<void> {
  const res = await fetch(`${BASE}/api/packages/groups/${id}`, {
    method: 'DELETE',
    headers: headers(),
  });
  if (!res.ok) throw new Error(await readErrorMessage(res, '删除分组失败'));
}

export async function getPackageDetail(id: number): Promise<PackageDetail> {
  const res = await fetch(`${BASE}/api/packages/${id}`, { headers: headers() });
  if (!res.ok) throw new Error("获取套餐详情失败");
  return res.json();
}

export async function createPackage(data: {
  group_id: number;
  name: string;
  description?: string;
  base_price?: number;
  default_pricing_mode?: string;
  items?: { dish_id: number; default_spec_id?: number; default_quantity?: number; override_price?: number | null; sort_order?: number }[];
}): Promise<{ id: number; name: string }> {
  const res = await fetch(`${BASE}/api/packages`, {
    method: 'POST',
    headers: headers(),
    body: JSON.stringify(data),
  });
  if (!res.ok) throw new Error(await readErrorMessage(res, '创建套餐失败'));
  return res.json();
}

export async function updatePackage(id: number, data: Partial<PackageSummary & { group_id?: number }>): Promise<{ id: number; name: string }> {
  const res = await fetch(`${BASE}/api/packages/${id}`, {
    method: 'PUT',
    headers: headers(),
    body: JSON.stringify(data),
  });
  if (!res.ok) throw new Error(await readErrorMessage(res, '更新套餐失败'));
  return res.json();
}

export async function deletePackage(id: number): Promise<void> {
  const res = await fetch(`${BASE}/api/packages/${id}`, {
    method: 'DELETE',
    headers: headers(),
  });
  if (!res.ok) throw new Error(await readErrorMessage(res, '删除套餐失败'));
}

export async function addPackageItem(packageId: number, data: { dish_id: number; default_spec_id?: number | null; default_quantity?: number; override_price?: number | null; sort_order?: number }): Promise<{ id: number }> {
  const res = await fetch(`${BASE}/api/packages/${packageId}/items`, {
    method: 'POST',
    headers: headers(),
    body: JSON.stringify(data),
  });
  if (!res.ok) throw new Error(await readErrorMessage(res, '添加菜品失败'));
  return res.json();
}

export async function updatePackageItem(itemId: number, data: {
  default_spec_id?: number | null;
  default_quantity?: number;
  override_price?: number | null;
  sort_order?: number;
}): Promise<{ id: number }> {
  const res = await fetch(`${BASE}/api/packages/items/${itemId}`, {
    method: 'PUT',
    headers: headers(),
    body: JSON.stringify(data),
  });
  if (!res.ok) throw new Error(await readErrorMessage(res, '更新套餐菜品失败'));
  return res.json();
}

export async function removePackageItem(itemId: number): Promise<void> {
  const res = await fetch(`${BASE}/api/packages/items/${itemId}`, {
    method: 'DELETE',
    headers: headers(),
  });
  if (!res.ok) throw new Error("移除菜品失败");
}

export async function aiCreatePackage(description: string, groupId: number): Promise<{ id: number; name: string }> {
  const res = await fetch(`${BASE}/api/packages/ai-create`, {
    method: 'POST',
    headers: headers(),
    body: JSON.stringify({ description, group_id: groupId }),
  });
  if (!res.ok) {
    const err = await res.json().catch(() => ({ detail: 'AI创建失败' }));
    throw new Error(err.detail || 'AI创建套餐失败');
  }
  return res.json();
}

// ── Menu ──

export interface MenuItemData {
  id?: number;
  dish_id: number;
  dish_name: string;
  price_text: string;
  price: number;
  min_price: number;
  cost: number;
  quantity: number;
  subtotal: number;
  cost_total: number;
  category: string;
  reason: string;
  spec_id?: number | null;
  spec_name?: string;
  additive_price?: number;
  adjusted_price?: number;
}

export interface MenuData {
  id: string;
  customer_name: string;
  mode: string;
  party_size: number;
  budget: number;
  target_margin: number;
  occasion: string;
  total_price: number;
  total_cost: number;
  margin_rate: number;
  reasoning: string;
  items: MenuItemData[];
  date: string;
  pricing_mode: string;
  fixed_price: number;
  table_count: number;
}

export interface MenuRequest {
  customer_name: string;
  party_size: number;
  budget: number;
  target_margin: number;
  occasion: string;
  preferences: string;
  date: string;
  mode: 'retail' | 'banquet';
}

export async function generateMenu(req: MenuRequest): Promise<MenuData> {
  const res = await fetch(`${BASE}/api/menu/generate`, {
    method: 'POST',
    headers: headers(),
    body: JSON.stringify(req),
  });
  if (res.status === 401) {
    localStorage.removeItem('wg_token');
    window.location.reload();
    throw new Error('未授权');
  }
  if (!res.ok) {
    const err = await res.json().catch(() => ({ detail: '请求失败' }));
    throw new Error(err.detail || '请求失败');
  }
  return res.json();
}

export async function createMenuFromPackage(data: {
  customer_name: string;
  date: string;
  party_size: number;
  table_count: number;
  package_id: number;
  pricing_mode?: string;
}): Promise<MenuData> {
  const res = await fetch(`${BASE}/api/menu/from-package`, {
    method: 'POST',
    headers: headers(),
    body: JSON.stringify(data),
  });
  if (res.status === 401) {
    localStorage.removeItem('wg_token');
    window.location.reload();
    throw new Error('未授权');
  }
  if (!res.ok) {
    const err = await res.json().catch(() => ({ detail: '创建失败' }));
    throw new Error(err.detail || '从套餐创建菜单失败');
  }
  return res.json();
}

export async function getMenuDetail(menuId: string): Promise<MenuData> {
  const res = await fetch(`${BASE}/api/menu/${menuId}`, { headers: headers() });
  if (!res.ok) throw new Error("获取菜单失败");
  return res.json();
}

export async function updateMenuItem(menuId: string, itemId: number, data: {
  adjusted_price?: number;
  spec_id?: number;
  quantity?: number;
}): Promise<MenuItemData> {
  const res = await fetch(`${BASE}/api/menu/${menuId}/items/${itemId}`, {
    method: 'PUT',
    headers: headers(),
    body: JSON.stringify(data),
  });
  if (!res.ok) throw new Error(await readErrorMessage(res, '更新菜单项失败'));
  return res.json();
}

export async function addMenuItem(menuId: string, data: {
  dish_id: number;
  spec_id?: number;
  quantity?: number;
}): Promise<MenuItemData> {
  const res = await fetch(`${BASE}/api/menu/${menuId}/items`, {
    method: 'POST',
    headers: headers(),
    body: JSON.stringify(data),
  });
  if (!res.ok) throw new Error(await readErrorMessage(res, '添加菜品失败'));
  return res.json();
}

export async function removeMenuItem(menuId: string, itemId: number): Promise<void> {
  const res = await fetch(`${BASE}/api/menu/${menuId}/items/${itemId}`, {
    method: 'DELETE',
    headers: headers(),
  });
  if (!res.ok) throw new Error(await readErrorMessage(res, '删除菜品失败'));
}

export async function updateMenuPricing(menuId: string, data: {
  pricing_mode?: string;
  fixed_price?: number;
}): Promise<MenuData> {
  const res = await fetch(`${BASE}/api/menu/${menuId}/pricing`, {
    method: 'PUT',
    headers: headers(),
    body: JSON.stringify(data),
  });
  if (!res.ok) throw new Error(await readErrorMessage(res, '更新定价模式失败'));
  return res.json();
}

export async function downloadExcel(menuId: string, format: 'simple' | 'margin' = 'simple'): Promise<void> {
  const res = await fetch(`${BASE}/api/menu/${menuId}/excel?format=${format}`, {
    headers: { Authorization: `Bearer ${getToken()}` },
  });
  if (!res.ok) throw new Error('下载失败');
  const blob = await res.blob();
  const url = URL.createObjectURL(blob);
  const a = document.createElement('a');
  a.href = url;
  a.download = format === 'margin' ? '旺阁渔村_毛利核算.xlsx' : '旺阁渔村_菜单.xlsx';
  a.click();
  URL.revokeObjectURL(url);
}

// ── Adjust ──

export interface AdjustAction {
  remove: number[];
  add: { dish_id: number; quantity: number; reason: string }[];
}

export interface AdjustResponse {
  type: 'ask' | 'suggest' | 'updated';
  message: string;
  action: AdjustAction | null;
  conversation_id: number | null;
  menu: MenuData | null;
}

export async function adjustMenu(
  menuId: string,
  message: string,
  action: 'chat' | 'confirm' = 'chat',
  conversationId?: number,
): Promise<AdjustResponse> {
  const res = await fetch(`${BASE}/api/menu/${menuId}/adjust`, {
    method: 'POST',
    headers: headers(),
    body: JSON.stringify({
      message,
      action,
      conversation_id: conversationId ?? null,
    }),
  });
  if (res.status === 401) {
    localStorage.removeItem('wg_token');
    window.location.reload();
    throw new Error('未授权');
  }
  if (!res.ok) {
    const err = await res.json().catch(() => ({ detail: '请求失败' }));
    throw new Error(err.detail || '调整失败');
  }
  return res.json();
}
