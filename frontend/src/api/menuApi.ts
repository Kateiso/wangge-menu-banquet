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

export async function login(password: string): Promise<boolean> {
  const res = await fetch(`${BASE}/api/auth`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ password }),
  });
  if (!res.ok) return false;
  const data = await res.json();
  localStorage.setItem('wg_token', data.token);
  return true;
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
  return `${BASE}/api/menu/${menuId}/excel?token=${getToken()}`;
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
