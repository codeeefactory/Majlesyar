import type {
  BuilderItem,
  Category,
  Order,
  OrderItem,
  Product,
  Settings,
} from "@/types/domain";
import { defaultSettings } from "@/data/siteConstants";
import {
  buildUrl,
  clearAuthTokens,
  extractErrorMessage,
  getAuthTokens,
  hasValidAccessToken,
  HttpError,
  isTokenExpired,
  parseResponseBody,
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
  url_slug: string;
  uri?: string;
  description: string;
  price: number | null;
  category_ids: string[];
  event_types: string[];
  contents: string[];
  image: string | null;
  image_alt?: string;
  image_name?: string;
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
  contact_phone: string;
  contact_address: string;
  working_hours: string;
  instagram_url: string;
  telegram_url: string;
  whatsapp_url: string;
  bale_url: string;
  maps_url: string;
  maps_embed_url: string;
  site_logo?: string | null;
  site_favicon?: string | null;
  site_og_image?: string | null;
  site_branding?: {
    site_name?: string;
    site_alternate_name?: string;
    site_tagline?: string;
    logo_alt?: string;
    meta_author?: string;
    default_meta_title?: string;
    default_meta_description?: string;
    default_meta_keywords?: string[];
    admin_site_title?: string;
    admin_site_header?: string;
    admin_site_subheader?: string;
    admin_site_symbol?: string;
  };
  theme_palette?: {
    primary?: string;
    accent?: string;
    background?: string;
    surface?: string;
    foreground?: string;
    muted_foreground?: string;
    success?: string;
    warning?: string;
  };
  page_seo?: Record<
    string,
    {
      title?: string;
      description?: string;
      keywords?: string[];
    }
  >;
  event_pages?: {
    id?: string;
    name?: string;
    slug?: string;
    description?: string;
    seo_title?: string;
    seo_description?: string;
    seo_keywords?: string[];
    faqs?: { question?: string; answer?: string }[];
    icon?: string;
    color?: string;
    available?: boolean;
  }[];
  site_top_notice?: {
    title?: string;
    message?: string;
    badge?: string;
  };
  homepage_benefits_section?: {
    eyebrow?: string;
    title?: string;
    items?: {
      title?: string;
      description?: string;
      note?: string;
    }[];
  };
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

export interface OfflineSessionImportResult {
  applied_actions: number;
  clients_created: number;
  clients_updated: number;
  invoices_created: number;
  invoices_updated: number;
}

const RAW_API_BASE_URL = import.meta.env.VITE_API_BASE_URL?.trim();

function resolveApiOrigin(): string {
  if (!RAW_API_BASE_URL) return "";
  try {
    return new URL(RAW_API_BASE_URL).origin;
  } catch {
    return "";
  }
}

const API_ORIGIN = resolveApiOrigin();

function normalizeImageUrl(image: string | null): string {
  if (!image) return "/placeholder.svg";
  if (/^https?:\/\//i.test(image)) return image;

  if (image.startsWith("/")) {
    return API_ORIGIN ? `${API_ORIGIN}${image}` : image;
  }

  const normalized = `/${image.replace(/^\/+/, "")}`;
  return API_ORIGIN ? `${API_ORIGIN}${normalized}` : normalized;
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
    urlSlug: apiProduct.url_slug || apiProduct.id,
    description: apiProduct.description,
    price: apiProduct.price,
    categoryIds: apiProduct.category_ids || [],
    eventTypes: apiProduct.event_types || [],
    contents: apiProduct.contents || [],
    image: normalizeImageUrl(apiProduct.image),
    imageAlt: apiProduct.image_alt || undefined,
    imageName: apiProduct.image_name || undefined,
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
  const defaultTopNotice = defaultSettings.siteTopNotice;
  const defaultHomepageBenefits = defaultSettings.homepageBenefitsSection;
  const defaultBranding = defaultSettings.siteBranding;
  const defaultThemePalette = defaultSettings.themePalette;
  const defaultPageSeo = defaultSettings.pageSeo;
  const defaultEventPages = defaultSettings.eventPages;
  const rawTopNotice = apiSettings.site_top_notice || {};
  const rawHomepageBenefits = apiSettings.homepage_benefits_section || {};
  const rawBranding = apiSettings.site_branding || {};
  const rawThemePalette = apiSettings.theme_palette || {};
  const rawPageSeo = apiSettings.page_seo || {};
  const rawEventPages = Array.isArray(apiSettings.event_pages) ? apiSettings.event_pages : [];
  const rawHomepageItems = Array.isArray(rawHomepageBenefits.items) ? rawHomepageBenefits.items : [];
  const resolvedPageSeoEntries = {
    ...defaultPageSeo,
    ...Object.fromEntries(
      Object.entries(rawPageSeo).map(([pageKey, value]) => [
        pageKey,
        {
          title: value?.title || defaultPageSeo[pageKey]?.title || "",
          description: value?.description || defaultPageSeo[pageKey]?.description || "",
          keywords:
            Array.isArray(value?.keywords) && value?.keywords.length
              ? value.keywords.filter(Boolean)
              : defaultPageSeo[pageKey]?.keywords || [],
        },
      ]),
    ),
  };
  const resolvedEventPages = rawEventPages.length
    ? rawEventPages
        .map((page, index) => {
          const fallback = defaultEventPages[index] || defaultEventPages.find((item) => item.slug === page.slug);
          if (!page.slug && !fallback?.slug) {
            return null;
          }
          return {
            id: page.id || fallback?.id || page.slug || "",
            name: page.name || fallback?.name || "",
            slug: page.slug || fallback?.slug || "",
            description: page.description || fallback?.description || "",
            seoTitle: page.seo_title || fallback?.seoTitle || page.name || fallback?.name || "",
            seoDescription:
              page.seo_description || fallback?.seoDescription || page.description || fallback?.description || "",
            seoKeywords:
              Array.isArray(page.seo_keywords) && page.seo_keywords.length
                ? page.seo_keywords.filter(Boolean)
                : fallback?.seoKeywords || [],
            faqs:
              Array.isArray(page.faqs) && page.faqs.length
                ? page.faqs
                    .map((faq) => ({
                      question: faq.question || "",
                      answer: faq.answer || "",
                    }))
                    .filter((faq) => faq.question || faq.answer)
                : fallback?.faqs || [],
            icon: page.icon || fallback?.icon || "📦",
            color: page.color || fallback?.color || "bg-muted",
            available: page.available ?? fallback?.available ?? true,
          };
        })
        .filter((page): page is NonNullable<typeof page> => Boolean(page && page.slug && page.name))
    : defaultEventPages;

  return {
    minOrderQty: apiSettings.min_order_qty,
    leadTimeHours: apiSettings.lead_time_hours,
    allowedProvinces: apiSettings.allowed_provinces || [],
    deliveryWindows: apiSettings.delivery_windows || [],
    paymentMethods: apiSettings.payment_methods || [],
    contactPhone: apiSettings.contact_phone || "",
    contactAddress: apiSettings.contact_address || "",
    workingHours: apiSettings.working_hours || "",
    instagramUrl: apiSettings.instagram_url || "",
    telegramUrl: apiSettings.telegram_url || "",
    whatsappUrl: apiSettings.whatsapp_url || "",
    baleUrl: apiSettings.bale_url || "",
    mapsUrl: apiSettings.maps_url || "",
    mapsEmbedUrl: apiSettings.maps_embed_url || "",
    siteLogoUrl: apiSettings.site_logo ? normalizeImageUrl(apiSettings.site_logo) : undefined,
    siteFaviconUrl: apiSettings.site_favicon ? normalizeImageUrl(apiSettings.site_favicon) : undefined,
    siteOgImageUrl: apiSettings.site_og_image ? normalizeImageUrl(apiSettings.site_og_image) : undefined,
    siteBranding: {
      siteName: rawBranding.site_name || defaultBranding.siteName,
      siteAlternateName: rawBranding.site_alternate_name || defaultBranding.siteAlternateName,
      siteTagline: rawBranding.site_tagline || defaultBranding.siteTagline,
      logoAlt: rawBranding.logo_alt || defaultBranding.logoAlt,
      metaAuthor: rawBranding.meta_author || defaultBranding.metaAuthor,
      defaultMetaTitle: rawBranding.default_meta_title || defaultBranding.defaultMetaTitle,
      defaultMetaDescription:
        rawBranding.default_meta_description || defaultBranding.defaultMetaDescription,
      defaultMetaKeywords:
        Array.isArray(rawBranding.default_meta_keywords) && rawBranding.default_meta_keywords.length
          ? rawBranding.default_meta_keywords.filter(Boolean)
          : defaultBranding.defaultMetaKeywords,
      adminSiteTitle: rawBranding.admin_site_title || defaultBranding.adminSiteTitle,
      adminSiteHeader: rawBranding.admin_site_header || defaultBranding.adminSiteHeader,
      adminSiteSubheader: rawBranding.admin_site_subheader || defaultBranding.adminSiteSubheader,
      adminSiteSymbol: rawBranding.admin_site_symbol || defaultBranding.adminSiteSymbol,
    },
    themePalette: {
      primary: rawThemePalette.primary || defaultThemePalette.primary,
      accent: rawThemePalette.accent || defaultThemePalette.accent,
      background: rawThemePalette.background || defaultThemePalette.background,
      surface: rawThemePalette.surface || defaultThemePalette.surface,
      foreground: rawThemePalette.foreground || defaultThemePalette.foreground,
      mutedForeground: rawThemePalette.muted_foreground || defaultThemePalette.mutedForeground,
      success: rawThemePalette.success || defaultThemePalette.success,
      warning: rawThemePalette.warning || defaultThemePalette.warning,
    },
    pageSeo: resolvedPageSeoEntries,
    eventPages: resolvedEventPages,
    siteTopNotice: {
      title: rawTopNotice.title || defaultTopNotice.title,
      message: rawTopNotice.message || defaultTopNotice.message,
      badge: rawTopNotice.badge || defaultTopNotice.badge,
    },
    homepageBenefitsSection: {
      eyebrow: rawHomepageBenefits.eyebrow || defaultHomepageBenefits.eyebrow,
      title: rawHomepageBenefits.title || defaultHomepageBenefits.title,
      items: rawHomepageItems.length
        ? rawHomepageItems
            .map((item) => ({
              title: item.title || "",
              description: item.description || "",
              note: item.note || "",
            }))
            .filter((item) => item.title || item.description || item.note)
        : defaultHomepageBenefits.items,
    },
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

export async function getProduct(identifier: string): Promise<Product | null> {
  try {
    const product = await requestJson<ApiProduct>(`/api/v1/products/${encodeURIComponent(identifier)}/`);
    return mapProduct(product);
  } catch {
    return null;
  }
}

export async function createProduct(product: Omit<Product, "id"> & { imageFile?: File }): Promise<Product> {
  const formData = new FormData();
  formData.append("name", product.name);
  formData.append("url_slug", product.urlSlug || "");
  formData.append("description", product.description);
  formData.append("price", product.price?.toString() || "");
  product.categoryIds.forEach(id => formData.append("category_ids", id));
  product.eventTypes.forEach(type => formData.append("event_types", type));
  product.contents.forEach(content => formData.append("contents", content));
  formData.append("image_alt", product.imageAlt || "");
  formData.append("image_name", product.imageName || "");
  formData.append("featured", product.featured.toString());
  formData.append("available", product.available.toString());

  if (product.imageFile) {
    formData.append("image_file", product.imageFile);
  } else if (product.image) {
    formData.append("image", product.image);
  }

  const response = await fetch(buildUrl("/api/v1/admin/products/"), {
    method: "POST",
    headers: {
      Authorization: `Bearer ${getAuthTokens()?.access}`,
    },
    body: formData,
  });

  if (!response.ok) {
    const error = await parseResponseBody(response);
    throw new HttpError(
      extractErrorMessage(error, `Request failed with status ${response.status}`),
      response.status,
      error,
    );
  }

  const created = await response.json();
  return mapProduct(created);
}

export async function updateProduct(id: string, updates: Partial<Product> & { imageFile?: File }): Promise<Product | null> {
  const formData = new FormData();
  if (updates.name !== undefined) formData.append("name", updates.name);
  if (updates.urlSlug !== undefined) formData.append("url_slug", updates.urlSlug);
  if (updates.description !== undefined) formData.append("description", updates.description);
  if (updates.price !== undefined) formData.append("price", updates.price?.toString() || "");
  if (updates.categoryIds !== undefined) updates.categoryIds.forEach(id => formData.append("category_ids", id));
  if (updates.eventTypes !== undefined) updates.eventTypes.forEach(type => formData.append("event_types", type));
  if (updates.contents !== undefined) updates.contents.forEach(content => formData.append("contents", content));
  if (updates.image !== undefined) formData.append("image", updates.image || "");
  if (updates.imageAlt !== undefined) formData.append("image_alt", updates.imageAlt || "");
  if (updates.imageName !== undefined) formData.append("image_name", updates.imageName || "");
  if (updates.featured !== undefined) formData.append("featured", updates.featured.toString());
  if (updates.available !== undefined) formData.append("available", updates.available.toString());

  if (updates.imageFile) {
    formData.append("image_file", updates.imageFile);
  }

  const response = await fetch(buildUrl(`/api/v1/admin/products/${id}/`), {
    method: "PATCH",
    headers: {
      Authorization: `Bearer ${getAuthTokens()?.access}`,
    },
    body: formData,
  });

  if (!response.ok) {
    if (response.status === 404) return null;
    const error = await parseResponseBody(response);
    throw new HttpError(
      extractErrorMessage(error, `Request failed with status ${response.status}`),
      response.status,
      error,
    );
  }

  const updated = await response.json();
  return mapProduct(updated);
}

export async function deleteProduct(_id: string): Promise<boolean> {
  try {
    await requestJson(`/api/v1/admin/products/${_id}/`, {
      method: "DELETE",
      auth: true,
    });
    return true;
  } catch {
    return false;
  }
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

export async function uploadOfflineSessionBundle(file: File): Promise<OfflineSessionImportResult> {
  const loggedIn = await isAdminLoggedIn();
  if (!loggedIn) {
    throw new HttpError("نشست مدیریتی معتبر نیست. دوباره وارد شوید.", 401, null);
  }

  const tokens = getAuthTokens();
  if (!tokens?.access) {
    throw new HttpError("توکن دسترسی در دسترس نیست.", 401, null);
  }

  const formData = new FormData();
  formData.append("session_file", file);

  const response = await fetch(buildUrl("/api/v1/admin/offline-session/import/"), {
    method: "POST",
    headers: {
      Authorization: `Bearer ${tokens.access}`,
    },
    body: formData,
  });

  const payload = await parseResponseBody(response);
  if (!response.ok) {
    throw new HttpError(
      extractErrorMessage(payload, `Request failed with status ${response.status}`),
      response.status,
      payload,
    );
  }

  return payload as OfflineSessionImportResult;
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
