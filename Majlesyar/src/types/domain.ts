export interface Category {
  id: string;
  name: string;
  slug: string;
  icon: string;
}

export interface Product {
  id: string;
  name: string;
  urlSlug: string;
  description: string;
  price: number | null;
  categoryIds: string[];
  eventTypes: string[];
  contents: string[];
  image: string;
  imageAlt?: string;
  imageName?: string;
  featured: boolean;
  available: boolean;
}

export interface BuilderItem {
  id: string;
  name: string;
  group: "packaging" | "fruit" | "drink" | "snack" | "addon";
  price: number;
  required: boolean;
  image?: string;
}

export interface SiteBranding {
  siteName: string;
  siteAlternateName: string;
  siteTagline: string;
  logoAlt: string;
  metaAuthor: string;
  defaultMetaTitle: string;
  defaultMetaDescription: string;
  defaultMetaKeywords: string[];
  adminSiteTitle: string;
  adminSiteHeader: string;
  adminSiteSubheader: string;
  adminSiteSymbol: string;
}

export interface ThemePalette {
  primary: string;
  accent: string;
  background: string;
  surface: string;
  foreground: string;
  mutedForeground: string;
  success: string;
  warning: string;
}

export interface PageSeoEntry {
  title: string;
  description: string;
  keywords: string[];
}

export interface EventPage {
  id: string;
  name: string;
  slug: string;
  description: string;
  seoTitle?: string;
  seoDescription?: string;
  seoKeywords?: string[];
  faqs?: { question: string; answer: string }[];
  icon: string;
  color: string;
  available?: boolean;
}

export interface SiteTopNotice {
  title: string;
  message: string;
  badge: string;
}

export interface HomepageBenefitItem {
  title: string;
  description: string;
  note?: string;
}

export interface HomepageBenefitsSection {
  eyebrow: string;
  title: string;
  items: HomepageBenefitItem[];
}

export interface Settings {
  minOrderQty: number;
  leadTimeHours: number;
  allowedProvinces: string[];
  deliveryWindows: string[];
  paymentMethods: { id: string; label: string; enabled: boolean }[];
  contactPhone: string;
  contactAddress: string;
  workingHours: string;
  instagramUrl: string;
  telegramUrl: string;
  whatsappUrl: string;
  baleUrl: string;
  mapsUrl: string;
  mapsEmbedUrl: string;
  siteLogoUrl?: string;
  siteFaviconUrl?: string;
  siteOgImageUrl?: string;
  siteBranding: SiteBranding;
  themePalette: ThemePalette;
  pageSeo: Record<string, PageSeoEntry>;
  eventPages: EventPage[];
  siteTopNotice: SiteTopNotice;
  homepageBenefitsSection: HomepageBenefitsSection;
}

export interface OrderItem {
  productId: string;
  name: string;
  quantity: number;
  price: number;
  isCustomPack?: boolean;
  customConfig?: {
    packaging: string;
    fruit: string;
    drink: string;
    snack: string;
    addons: string[];
  };
}

export interface Order {
  id: string;
  items: OrderItem[];
  customer: {
    name: string;
    phone: string;
    province: string;
    address: string;
    notes?: string;
  };
  delivery: {
    date: string;
    window: string;
  };
  paymentMethod: string;
  status: "pending" | "confirmed" | "preparing" | "shipped" | "delivered";
  total: number;
  createdAt: string;
  notes?: string[];
}
