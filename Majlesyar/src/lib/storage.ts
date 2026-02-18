const STORAGE_PREFIX = 'majlesyar_';
const SCHEMA_VERSION = 1;

interface StorageWrapper<T> {
  version: number;
  data: T;
  updatedAt: string;
}

export function getStorageKey(key: string): string {
  return `${STORAGE_PREFIX}${key}`;
}

export function getItem<T>(key: string, defaultValue: T): T {
  try {
    const raw = localStorage.getItem(getStorageKey(key));
    if (!raw) return defaultValue;
    
    const wrapper: StorageWrapper<T> = JSON.parse(raw);
    
    // Version check - if schema changed, return default
    if (wrapper.version !== SCHEMA_VERSION) {
      return defaultValue;
    }
    
    return wrapper.data;
  } catch {
    return defaultValue;
  }
}

export function setItem<T>(key: string, data: T): void {
  const wrapper: StorageWrapper<T> = {
    version: SCHEMA_VERSION,
    data,
    updatedAt: new Date().toISOString(),
  };
  localStorage.setItem(getStorageKey(key), JSON.stringify(wrapper));
}

export function removeItem(key: string): void {
  localStorage.removeItem(getStorageKey(key));
}

export function clearAll(): void {
  const keys = Object.keys(localStorage);
  keys.forEach((key) => {
    if (key.startsWith(STORAGE_PREFIX)) {
      localStorage.removeItem(key);
    }
  });
}

// Specific storage helpers
export const storage = {
  // Products
  getProducts: () => getItem('products', null),
  setProducts: (products: unknown) => setItem('products', products),
  
  // Categories
  getCategories: () => getItem('categories', null),
  setCategories: (categories: unknown) => setItem('categories', categories),
  
  // Builder Items
  getBuilderItems: () => getItem('builderItems', null),
  setBuilderItems: (items: unknown) => setItem('builderItems', items),
  
  // Settings
  getSettings: () => getItem('settings', null),
  setSettings: (settings: unknown) => setItem('settings', settings),
  
  // Orders
  getOrders: () => getItem('orders', []),
  setOrders: (orders: unknown) => setItem('orders', orders),
  
  // Cart
  getCart: () => getItem('cart', []),
  setCart: (cart: unknown) => setItem('cart', cart),
  
  // Admin Auth
  getAdminAuth: () => getItem('adminAuth', null),
  setAdminAuth: (auth: unknown) => setItem('adminAuth', auth),
  clearAdminAuth: () => removeItem('adminAuth'),
};
