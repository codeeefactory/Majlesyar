import type {
  BuilderItem,
  Category,
  Order,
  OrderItem,
  Product,
  Settings,
} from "@/types/domain";
import {
  clearAuthTokens,
  getAuthTokens,
  hasValidAccessToken,
  isTokenExpired,
  requestJson,
  setAuthTokens,
} from "@/lib/http";

interface ApiCategory {
  id: string;
  name: string;
  slug: string;
  icon: string;
}

interface ApiProduct {
  id: string;
  name: string;
  description: string;
  price: number | null;
  category_ids: string[];
  event_types: string[];
  contents: string[];
  image: string | null;
  featured: boolean;
  available: boolean;
}

interface ApiBuilderItem {
  id: string;
  name: string;
  group: BuilderItem["group"];
  price: number;
  required: boolean;
  image: string | null;
}

interface ApiSettings {
  min_order_qty: number;
  lead_time_hours: number;
  allowed_provinces: string[];
  delivery_windows: string[];
  payment_methods: { id: string; label: string; enabled: boolean }[];
}

interface ApiOrderItem {
  id: string;
  product_id: string | null;
  name: string;
  quantity: number;
  price: number;
  is_custom_pack: boolean;
  custom_config: Record<string, unknown> | null;
}

interface ApiOrderNote {
  id: string;
  note: string;
  created_at: string;
}

interface ApiOrder {
  public_id: string;
  status: Order["status"];
  customer: {
    name: string;
    phone: string;
    province: string;
    address: string;
    notes?: string | null;
  };
  delivery: {
    date: string;
    window: string;
  };
  payment_method: string;
  total: number;
  created_at: string;
  items: ApiOrderItem[];
  notes: ApiOrderNote[];
}

const UUID_REGEX =
  /^[0-9a-f]{8}-[0-9a-f]{4}-[1-5][0-9a-f]{3}-[89ab][0-9a-f]{3}-[0-9a-f]{12}$/i;

function isUuid(value: string): boolean {
  return UUID_REGEX.test(value);
}

function mapCategory(apiCategory: ApiCategory): Category {
  return {
    id: apiCategory.id,
    name: apiCategory.name,
    slug: apiCategory.slug,
    icon: apiCategory.icon,
  };
}

function mapProduct(apiProduct: ApiProduct): Product {
  return {
    id: apiProduct.id,
    name: apiProduct.name,
    description: apiProduct.description,
    price: apiProduct.price,
    categoryIds: apiProduct.category_ids || [],
    eventTypes: apiProduct.event_types || [],
    contents: apiProduct.contents || [],
    image: apiProduct.image || "/placeholder.svg",
    featured: apiProduct.featured,
    available: apiProduct.available,
  };
}

function mapBuilderItem(apiBuilderItem: ApiBuilderItem): BuilderItem {
  return {
    id: apiBuilderItem.id,
    name: apiBuilderItem.name,
    group: apiBuilderItem.group,
    price: apiBuilderItem.price,
    required: apiBuilderItem.required,
    image: apiBuilderItem.image || undefined,
  };
}

function mapSettings(apiSettings: ApiSettings): Settings {
  return {
    minOrderQty: apiSettings.min_order_qty,
    leadTimeHours: apiSettings.lead_time_hours,
    allowedProvinces: apiSettings.allowed_provinces || [],
    deliveryWindows: apiSettings.delivery_windows || [],
    paymentMethods: apiSettings.payment_methods || [],
  };
}

function normalizeCustomConfig(raw: unknown): OrderItem["customConfig"] | undefined {
  if (!raw || typeof raw !== "object") return undefined;
  const config = raw as Record<string, unknown>;
  return {
    packaging: String(config.packaging || ""),
    fruit: String(config.fruit || ""),
    drink: String(config.drink || ""),
    snack: String(config.snack || ""),
    addons: Array.isArray(config.addons) ? config.addons.map((item) => String(item)) : [],
  };
}

function mapOrderItem(apiItem: ApiOrderItem): OrderItem {
  return {
    productId: apiItem.product_id || `custom-${apiItem.id}`,
    name: apiItem.name,
    quantity: apiItem.quantity,
    price: apiItem.price,
    isCustomPack: apiItem.is_custom_pack,
    customConfig: normalizeCustomConfig(apiItem.custom_config),
  };
}

function mapOrder(apiOrder: ApiOrder): Order {
  return {
    id: apiOrder.public_id,
    status: apiOrder.status,
    customer: {
      name: apiOrder.customer.name,
      phone: apiOrder.customer.phone,
      province: apiOrder.customer.province,
      address: apiOrder.customer.address,
      notes: apiOrder.customer.notes || undefined,
    },
    delivery: {
      date: apiOrder.delivery.date,
      window: apiOrder.delivery.window,
    },
    paymentMethod: apiOrder.payment_method,
    total: apiOrder.total,
    createdAt: apiOrder.created_at,
    items: apiOrder.items.map(mapOrderItem),
    notes: (apiOrder.notes || []).map(
      (note) => `${new Date(note.created_at).toLocaleString("fa-IR")}: ${note.note}`,
    ),
  };
}

export async function listProducts(): Promise<Product[]> {
  const products = await requestJson<ApiProduct[]>("/api/v1/products/");
  return products.map(mapProduct);
}

export async function getProduct(id: string): Promise<Product | null> {
  try {
    const product = await requestJson<ApiProduct>(`/api/v1/products/${id}/`);
    return mapProduct(product);
  } catch {
    return null;
  }
}

export async function createProduct(_product: Omit<Product, "id">): Promise<Product> {
  throw new Error("Product creation is not exposed in public API.");
}

export async function updateProduct(_id: string, _updates: Partial<Product>): Promise<Product | null> {
  throw new Error("Product update is not exposed in public API.");
}

export async function deleteProduct(_id: string): Promise<boolean> {
  throw new Error("Product deletion is not exposed in public API.");
}

export async function listCategories(): Promise<Category[]> {
  const categories = await requestJson<ApiCategory[]>("/api/v1/categories/");
  return categories.map(mapCategory);
}

export async function getBuilderConfig(): Promise<BuilderItem[]> {
  const items = await requestJson<ApiBuilderItem[]>("/api/v1/builder-items/");
  return items.map(mapBuilderItem);
}

export async function updateBuilderConfig(_items: BuilderItem[]): Promise<BuilderItem[]> {
  throw new Error("Builder config update is not exposed in public API.");
}

export async function getSettings(): Promise<Settings> {
  const settings = await requestJson<ApiSettings>("/api/v1/settings/");
  return mapSettings(settings);
}

export async function updateSettings(_updates: Partial<Settings>): Promise<Settings> {
  throw new Error("Settings update is not exposed in public API.");
}

export async function listOrders(): Promise<Order[]> {
  const orders = await requestJson<ApiOrder[]>("/api/v1/admin/orders/", { auth: true });
  return orders.map(mapOrder);
}

export async function getOrder(id: string): Promise<Order | null> {
  try {
    const order = await requestJson<ApiOrder>(`/api/v1/orders/${id}/`);
    return mapOrder(order);
  } catch {
    return null;
  }
}

export async function createOrder(
  items: OrderItem[],
  customer: Order["customer"],
  delivery: Order["delivery"],
  paymentMethod: string,
): Promise<Order> {
  const payload = {
    items: items.map((item) => ({
      product_id: !item.isCustomPack && isUuid(item.productId) ? item.productId : null,
      name: item.name,
      quantity: item.quantity,
      price: item.price,
      is_custom_pack: Boolean(item.isCustomPack),
      custom_config: item.customConfig || null,
    })),
    customer: {
      name: customer.name,
      phone: customer.phone,
      province: customer.province,
      address: customer.address,
      notes: customer.notes || "",
    },
    delivery: {
      date: delivery.date,
      window: delivery.window,
    },
    payment_method: paymentMethod,
  };

  const order = await requestJson<ApiOrder>("/api/v1/orders/", {
    method: "POST",
    body: payload,
  });
  return mapOrder(order);
}

export async function updateOrderStatus(id: string, status: Order["status"]): Promise<Order | null> {
  try {
    const order = await requestJson<ApiOrder>(`/api/v1/admin/orders/${id}/`, {
      method: "PATCH",
      auth: true,
      body: { status },
    });
    return mapOrder(order);
  } catch {
    return null;
  }
}

export async function addOrderNote(id: string, note: string): Promise<Order | null> {
  try {
    await requestJson(`/api/v1/admin/orders/${id}/notes/`, {
      method: "POST",
      auth: true,
      body: { note },
    });
    return getOrder(id);
  } catch {
    return null;
  }
}

export async function adminLogin(username: string, password: string): Promise<boolean> {
  try {
    const tokens = await requestJson<{ access: string; refresh: string }>("/api/v1/auth/token/", {
      method: "POST",
      body: { username, password },
    });
    if (!tokens.access || !tokens.refresh) return false;
    setAuthTokens(tokens);
    return true;
  } catch {
    return false;
  }
}

export async function adminLogout(): Promise<void> {
  clearAuthTokens();
}

export async function isAdminLoggedIn(): Promise<boolean> {
  const tokens = getAuthTokens();
  if (!tokens) return false;
  if (hasValidAccessToken()) return true;
  if (isTokenExpired(tokens.refresh)) {
    clearAuthTokens();
    return false;
  }
  try {
    await requestJson<{ access: string }>("/api/v1/auth/token/refresh/", {
      method: "POST",
      body: { refresh: tokens.refresh },
    }).then((data) => {
      if (data.access) {
        setAuthTokens({ ...tokens, access: data.access });
      }
    });
    return hasValidAccessToken();
  } catch {
    clearAuthTokens();
    return false;
  }
}
