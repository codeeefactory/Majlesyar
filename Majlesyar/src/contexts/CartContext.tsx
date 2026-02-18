import React, { createContext, useContext, useState, useEffect, useCallback } from 'react';
import { storage } from '@/lib/storage';
import type { OrderItem } from '@/types/domain';
import { useSettings } from '@/contexts/SettingsContext';

interface CartContextType {
  items: OrderItem[];
  addItem: (item: OrderItem) => void;
  removeItem: (productId: string) => void;
  updateQuantity: (productId: string, quantity: number) => void;
  clearCart: () => void;
  totalItems: number;
  totalQuantity: number;
  totalPrice: number;
  isMinQuantityMet: boolean;
  minQuantityRequired: number;
}

const CartContext = createContext<CartContextType | undefined>(undefined);

export function CartProvider({ children }: { children: React.ReactNode }) {
  const { settings } = useSettings();
  const [items, setItems] = useState<OrderItem[]>([]);
  const minQuantityRequired = settings.minOrderQty;

  useEffect(() => {
    const savedCart = storage.getCart() as OrderItem[];
    if (savedCart && Array.isArray(savedCart)) {
      setItems(savedCart);
    }
  }, []);

  useEffect(() => {
    storage.setCart(items);
  }, [items]);

  const addItem = useCallback((newItem: OrderItem) => {
    setItems((prev) => {
      // For custom packs, always add as new item
      if (newItem.isCustomPack) {
        return [...prev, { ...newItem, productId: `custom-${Date.now()}` }];
      }
      
      // For regular products, check if exists
      const existingIndex = prev.findIndex((item) => item.productId === newItem.productId);
      if (existingIndex > -1) {
        const updated = [...prev];
        updated[existingIndex].quantity += newItem.quantity;
        return updated;
      }
      return [...prev, newItem];
    });
  }, []);

  const removeItem = useCallback((productId: string) => {
    setItems((prev) => prev.filter((item) => item.productId !== productId));
  }, []);

  const updateQuantity = useCallback((productId: string, quantity: number) => {
    if (quantity < 1) {
      removeItem(productId);
      return;
    }
    setItems((prev) =>
      prev.map((item) =>
        item.productId === productId ? { ...item, quantity } : item
      )
    );
  }, [removeItem]);

  const clearCart = useCallback(() => {
    setItems([]);
  }, []);

  const totalItems = items.length;
  const totalQuantity = items.reduce((sum, item) => sum + item.quantity, 0);
  const totalPrice = items.reduce((sum, item) => sum + item.price * item.quantity, 0);
  const isMinQuantityMet = totalQuantity >= minQuantityRequired;

  return (
    <CartContext.Provider
      value={{
        items,
        addItem,
        removeItem,
        updateQuantity,
        clearCart,
        totalItems,
        totalQuantity,
        totalPrice,
        isMinQuantityMet,
        minQuantityRequired,
      }}
    >
      {children}
    </CartContext.Provider>
  );
}

export function useCart() {
  const context = useContext(CartContext);
  if (context === undefined) {
    throw new Error('useCart must be used within a CartProvider');
  }
  return context;
}
