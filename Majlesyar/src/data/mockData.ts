// Types
export interface Category {
  id: string;
  name: string;
  slug: string;
  icon: string;
}

export interface Product {
  id: string;
  name: string;
  description: string;
  price: number | null; // null means "call for price"
  categoryIds: string[];
  eventTypes: string[];
  contents: string[];
  image: string;
  featured: boolean;
  available: boolean;
}

export interface BuilderItem {
  id: string;
  name: string;
  group: 'packaging' | 'fruit' | 'drink' | 'snack' | 'addon';
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
  status: 'pending' | 'confirmed' | 'preparing' | 'shipped' | 'delivered';
  total: number;
  createdAt: string;
  notes?: string[];
}

// Initial Categories
export const categories: Category[] = [
  { id: 'cat-1', name: 'اقتصادی', slug: 'economic', icon: '💰' },
  { id: 'cat-2', name: 'لوکس', slug: 'luxury', icon: '✨' },
  { id: 'cat-3', name: 'همایش', slug: 'conference', icon: '🎤' },
  { id: 'cat-4', name: 'ترحیم', slug: 'memorial', icon: '🕯️' },
  { id: 'cat-5', name: 'پک خالی', slug: 'empty', icon: '📦' },
];

// Event Types
export const eventTypes = [
  { id: 'conference', name: 'همایش', slug: 'conference', description: 'پک‌های مناسب برای کنفرانس‌ها و سمینارها', icon: '🎤', color: 'bg-secondary' },
  { id: 'memorial', name: 'ترحیم', slug: 'memorial', description: 'پک‌های متناسب با مراسم ترحیم', icon: '🕯️', color: 'bg-muted' },
  { id: 'defense', name: 'دفاع', slug: 'defense', description: 'پک‌های ویژه جلسات دفاع پایان‌نامه', icon: '🎓', color: 'bg-accent' },
  { id: 'party', name: 'تولد/مهمانی', slug: 'party', description: 'پک‌های شاد برای جشن‌ها و مهمانی‌ها', icon: '🎂', color: 'bg-primary/20' },
];

// Initial Products
export const products: Product[] = [
  {
    id: 'prod-1',
    name: 'پک اقتصادی همایش',
    description: 'پک ساده و اقتصادی مناسب برای همایش‌های بزرگ',
    price: 85000,
    categoryIds: ['cat-1', 'cat-3'],
    eventTypes: ['conference'],
    contents: ['آبمیوه کوچک', 'کیک یزدی', 'دستمال'],
    image: '/placeholder.svg',
    featured: true,
    available: true,
  },
  {
    id: 'prod-2',
    name: 'پک لوکس همایش',
    description: 'پک کامل و لوکس با بهترین محتویات',
    price: 165000,
    categoryIds: ['cat-2', 'cat-3'],
    eventTypes: ['conference'],
    contents: ['آبمیوه طبیعی', 'شیرینی تر', 'میوه خشک', 'چای کیسه‌ای', 'دستمال مرطوب'],
    image: '/placeholder.svg',
    featured: true,
    available: true,
  },
  {
    id: 'prod-3',
    name: 'پک ترحیم ساده',
    description: 'پک متناسب با فضای احترام‌آمیز مراسم',
    price: 95000,
    categoryIds: ['cat-1', 'cat-4'],
    eventTypes: ['memorial'],
    contents: ['خرما', 'حلوا', 'آب معدنی', 'دستمال'],
    image: '/placeholder.svg',
    featured: false,
    available: true,
  },
  {
    id: 'prod-4',
    name: 'پک ترحیم کامل',
    description: 'پک کامل شامل تمام ملزومات مراسم ترحیم',
    price: 145000,
    categoryIds: ['cat-2', 'cat-4'],
    eventTypes: ['memorial'],
    contents: ['خرما مضافتی', 'حلوا', 'زولبیا بامیه', 'آب معدنی', 'چای کیسه‌ای', 'دستمال'],
    image: '/placeholder.svg',
    featured: true,
    available: true,
  },
  {
    id: 'prod-5',
    name: 'پک دفاع پایان‌نامه',
    description: 'پک ویژه برای جلسات دفاع دانشگاهی',
    price: 125000,
    categoryIds: ['cat-2'],
    eventTypes: ['defense'],
    contents: ['شیرینی تر', 'میوه فصل', 'آبمیوه', 'قهوه فوری', 'دستمال'],
    image: '/placeholder.svg',
    featured: true,
    available: true,
  },
  {
    id: 'prod-6',
    name: 'پک تولد شاد',
    description: 'پک رنگارنگ برای جشن‌های تولد',
    price: 135000,
    categoryIds: ['cat-2'],
    eventTypes: ['party'],
    contents: ['کیک تولد کوچک', 'آبنبات', 'آبمیوه', 'بادکنک', 'کلاه'],
    image: '/placeholder.svg',
    featured: false,
    available: true,
  },
  {
    id: 'prod-7',
    name: 'پک VIP',
    description: 'لوکس‌ترین پک برای مهمانان ویژه',
    price: null,
    categoryIds: ['cat-2'],
    eventTypes: ['conference', 'defense'],
    contents: ['سوپرایز ویژه', 'تماس بگیرید'],
    image: '/placeholder.svg',
    featured: true,
    available: true,
  },
  {
    id: 'prod-8',
    name: 'پک خالی زیپ‌لاک',
    description: 'بسته‌بندی خالی زیپ‌لاک برای پک سفارشی',
    price: 15000,
    categoryIds: ['cat-5'],
    eventTypes: ['conference', 'memorial', 'defense', 'party'],
    contents: ['کیسه زیپ‌لاک با لوگو'],
    image: '/placeholder.svg',
    featured: false,
    available: true,
  },
  {
    id: 'prod-9',
    name: 'پک خالی جعبه‌ای',
    description: 'جعبه خالی مقوایی برای پک سفارشی',
    price: 25000,
    categoryIds: ['cat-5'],
    eventTypes: ['conference', 'memorial', 'defense', 'party'],
    contents: ['جعبه مقوایی با لوگو'],
    image: '/placeholder.svg',
    featured: false,
    available: true,
  },
];

// Builder Items
export const builderItems: BuilderItem[] = [
  // Packaging
  { id: 'pkg-1', name: 'زیپ‌لاک', group: 'packaging', price: 15000, required: true },
  { id: 'pkg-2', name: 'جعبه مقوایی', group: 'packaging', price: 25000, required: true },
  
  // Fruits
  { id: 'fruit-1', name: 'سیب', group: 'fruit', price: 20000, required: true },
  { id: 'fruit-2', name: 'پرتقال', group: 'fruit', price: 22000, required: true },
  { id: 'fruit-3', name: 'موز', group: 'fruit', price: 25000, required: true },
  { id: 'fruit-4', name: 'میوه خشک مخلوط', group: 'fruit', price: 35000, required: true },
  
  // Drinks
  { id: 'drink-1', name: 'آب معدنی', group: 'drink', price: 8000, required: true },
  { id: 'drink-2', name: 'آبمیوه کوچک', group: 'drink', price: 15000, required: true },
  { id: 'drink-3', name: 'آبمیوه طبیعی', group: 'drink', price: 25000, required: true },
  { id: 'drink-4', name: 'نوشابه قوطی', group: 'drink', price: 18000, required: true },
  
  // Snacks
  { id: 'snack-1', name: 'کیک یزدی', group: 'snack', price: 12000, required: true },
  { id: 'snack-2', name: 'شیرینی خشک', group: 'snack', price: 20000, required: true },
  { id: 'snack-3', name: 'شیرینی تر', group: 'snack', price: 30000, required: true },
  { id: 'snack-4', name: 'کلوچه', group: 'snack', price: 15000, required: true },
  
  // Addons
  { id: 'addon-1', name: 'چاقو پلاستیکی', group: 'addon', price: 2000, required: false },
  { id: 'addon-2', name: 'دستمال کاغذی', group: 'addon', price: 3000, required: false },
  { id: 'addon-3', name: 'دستمال مرطوب', group: 'addon', price: 5000, required: false },
  { id: 'addon-4', name: 'پد الکلی', group: 'addon', price: 4000, required: false },
];

// Default Settings
export const defaultSettings: Settings = {
  minOrderQty: 40,
  leadTimeHours: 48,
  allowedProvinces: ['تهران', 'البرز'],
  deliveryWindows: ['۱۰-۱۲', '۱۲-۱۴', '۱۴-۱۶', '۱۶-۱۸'],
  paymentMethods: [
    { id: 'pay-later', label: 'پرداخت بعد از تایید', enabled: true },
    { id: 'online', label: 'درگاه آنلاین (به‌زودی)', enabled: false },
  ],
};

// All provinces for dropdown
export const allProvinces = [
  'تهران',
  'البرز',
  'اصفهان',
  'فارس',
  'خراسان رضوی',
  'آذربایجان شرقی',
  'مازندران',
  'گیلان',
  'کرمان',
  'خوزستان',
];
