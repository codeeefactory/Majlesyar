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
