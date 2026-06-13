export interface Category {
  id: string;
  name: string;
  slug: string;
  icon: string;
}

export interface ProductContentItem {
  name: string;
  price: number | null;
}

export type ProductContent = string | ProductContentItem;

export interface Product {
  id: string;
  name: string;
  urlSlug: string;
  description: string;
  price: number | null;
  categoryIds: string[];
  eventTypes: string[];
  contents: ProductContent[];
  image: string;
  imageResponsive?: ProductImageResponsive;
  imageAlt?: string;
  imageName?: string;
  customerReviews?: CustomerReview[];
  featured: boolean;
  available: boolean;
}

export interface CustomerReview {
  id: string;
  productId?: string;
  productName?: string;
  customerName: string;
  customerCity?: string;
  title?: string;
  comment: string;
  rating: number;
  isFeatured: boolean;
  displayOrder: number;
  createdAt: string;
}

export interface ProductImageVariant {
  url: string;
  width: number;
  height: number;
  bytes?: number;
  mimeType?: string;
}

export interface ProductImageResponsive {
  width: number;
  height: number;
  backupUrl?: string;
  formats: {
    avif: ProductImageVariant[];
    webp: ProductImageVariant[];
    jpeg: ProductImageVariant[];
  };
  fallback: {
    src?: string;
    width?: number;
    height?: number;
    format?: string;
    sizes?: {
      card?: string;
      detail?: string;
    };
  };
}

export interface PageProductPreview {
  pageType: "home" | "event";
  pageSlug: string;
  pageKey: string;
  pageTitle: string;
  pageDescription: string;
  routePath: string;
  usesCustomOrder: boolean;
  products: Product[];
}

export interface PagePreviewTarget {
  pageType: "home" | "event";
  pageSlug: string;
  pageKey: string;
  pageTitle: string;
  pageDescription: string;
  routePath: string;
}

export interface PageProductPlacement {
  id: string;
  pageType: "home" | "event";
  pageSlug: string;
  pageKey: string;
  position: number;
  productId: string;
  product: Product;
}

export interface PageProductPlacementState {
  pageType: "home" | "event";
  pageSlug: string;
  pageKey: string;
  pageTitle: string;
  pageDescription: string;
  routePath: string;
  usesCustomOrder: boolean;
  placements: PageProductPlacement[];
  previewProducts: Product[];
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

export interface InternalLink {
  label: string;
  url: string;
}

export interface EventContentBlock {
  tag?: "h2" | "h3" | "p";
  text: string;
}

export interface EventPage {
  id: string;
  name: string;
  slug: string;
  routePath?: string;
  description: string;
  seoTitle?: string;
  seoDescription?: string;
  seoKeywords?: string[];
  benefits?: { title: string; description: string }[];
  internalLinks?: InternalLink[];
  introTitle?: string;
  introDescription?: string;
  contentBlocks?: EventContentBlock[];
  faqs?: { question: string; answer: string }[];
  icon: string;
  color: string;
  available?: boolean;
  hidden?: boolean;
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
  eitaaUrl: string;
  soroushUrl: string;
  rubikaUrl: string;
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
