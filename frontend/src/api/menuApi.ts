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

export interface Dish {
  id: number;
  name: string;
  price_text: string;
  price: number;
  cost: number;
  category: string;
  is_active: boolean;
  tags?: string;
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

export interface MenuRequest {
  customer_name: string;
  party_size: number;
  budget: number;
  target_margin: number;
  occasion: string;
  preferences: string;
  date: string;
}

export interface MenuItemData {
  dish_id: number;
  dish_name: string;
  price_text: string;
  price: number;
  cost: number;
  quantity: number;
  subtotal: number;
  cost_total: number;
  category: string;
  reason: string;
}

export interface MenuData {
  id: string;
  customer_name: string;
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

export function getExcelUrl(menuId: string): string {
  // Direct link download might fail with Bearer auth unless we implement query param auth again or use blob download
  // For now rely on checkToken or just let downloadExcel handle it
  return `${BASE}/api/menu/${menuId}/excel`;
}

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

export async function downloadExcel(menuId: string): Promise<void> {
  const res = await fetch(`${BASE}/api/menu/${menuId}/excel`, {
    headers: { Authorization: `Bearer ${getToken()}` },
  });
  if (!res.ok) throw new Error('下载失败');
  const blob = await res.blob();
  const url = URL.createObjectURL(blob);
  const a = document.createElement('a');
  a.href = url;
  a.download = `旺阁渔村_菜单.xlsx`;
  a.click();
  URL.revokeObjectURL(url);
}
