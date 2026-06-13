import React, { createContext, useCallback, useContext, useEffect, useMemo, useState } from 'react';
import { storage } from '@/lib/storage';

export interface CustomerProfile {
  id: string;
  username: string;
  email: string;
  fullName: string;
  phone: string;
  province: string;
  address: string;
  createdAt: string;
}

interface CustomerAccount extends CustomerProfile {
  passwordHash: string;
}

interface CustomerAuthContextType {
  customer: CustomerProfile | null;
  isAuthenticated: boolean;
  signup: (input: SignupInput) => Promise<{ ok: boolean; message?: string }>;
  login: (identifier: string, password: string) => Promise<{ ok: boolean; message?: string }>;
  logout: () => void;
  updateProfile: (updates: Partial<Omit<CustomerProfile, 'id' | 'createdAt'>>) => void;
}

interface SignupInput {
  username: string;
  email: string;
  password: string;
  fullName: string;
}

interface CustomerSession {
  customerId: string;
  signedInAt: string;
}

const CustomerAuthContext = createContext<CustomerAuthContextType | undefined>(undefined);

function normalizeIdentifier(value: string) {
  return value.trim().toLowerCase();
}

async function hashPassword(password: string) {
  const payload = new TextEncoder().encode(`majlesyar:${password}`);
  const digest = await crypto.subtle.digest('SHA-256', payload);
  return Array.from(new Uint8Array(digest))
    .map((byte) => byte.toString(16).padStart(2, '0'))
    .join('');
}

function getAccounts(): CustomerAccount[] {
  const accounts = storage.getCustomerAccounts();
  return Array.isArray(accounts) ? (accounts as CustomerAccount[]) : [];
}

function profileFromAccount(account: CustomerAccount): CustomerProfile {
  const { passwordHash: _passwordHash, ...profile } = account;
  return profile;
}

export function CustomerAuthProvider({ children }: { children: React.ReactNode }) {
  const [accounts, setAccounts] = useState<CustomerAccount[]>([]);
  const [session, setSession] = useState<CustomerSession | null>(null);

  useEffect(() => {
    setAccounts(getAccounts());
    const savedSession = storage.getCustomerSession();
    if (savedSession && typeof savedSession === 'object') {
      setSession(savedSession as CustomerSession);
    }
  }, []);

  const persistAccounts = useCallback((nextAccounts: CustomerAccount[]) => {
    setAccounts(nextAccounts);
    storage.setCustomerAccounts(nextAccounts);
  }, []);

  const customer = useMemo(() => {
    if (!session?.customerId) return null;
    const account = accounts.find((item) => item.id === session.customerId);
    return account ? profileFromAccount(account) : null;
  }, [accounts, session]);

  const signup = useCallback(
    async (input: SignupInput) => {
      const username = normalizeIdentifier(input.username);
      const email = normalizeIdentifier(input.email);
      const fullName = input.fullName.trim();

      if (username.length < 3) return { ok: false, message: 'نام کاربری باید حداقل ۳ کاراکتر باشد' };
      if (!/^[^\s@]+@[^\s@]+\.[^\s@]+$/.test(email)) return { ok: false, message: 'ایمیل معتبر وارد کنید' };
      if (input.password.length < 6) return { ok: false, message: 'رمز عبور باید حداقل ۶ کاراکتر باشد' };
      if (!fullName) return { ok: false, message: 'نام کامل را وارد کنید' };
      if (accounts.some((account) => account.username === username || account.email === email)) {
        return { ok: false, message: 'حسابی با این نام کاربری یا ایمیل وجود دارد' };
      }

      const account: CustomerAccount = {
        id: crypto.randomUUID(),
        username,
        email,
        fullName,
        phone: '',
        province: '',
        address: '',
        createdAt: new Date().toISOString(),
        passwordHash: await hashPassword(input.password),
      };
      const nextAccounts = [...accounts, account];
      const nextSession = { customerId: account.id, signedInAt: new Date().toISOString() };
      persistAccounts(nextAccounts);
      setSession(nextSession);
      storage.setCustomerSession(nextSession);
      return { ok: true };
    },
    [accounts, persistAccounts],
  );

  const login = useCallback(
    async (identifier: string, password: string) => {
      const normalized = normalizeIdentifier(identifier);
      const account = accounts.find((item) => item.username === normalized || item.email === normalized);
      if (!account) return { ok: false, message: 'حساب کاربری پیدا نشد' };
      const passwordHash = await hashPassword(password);
      if (passwordHash !== account.passwordHash) return { ok: false, message: 'رمز عبور نادرست است' };

      const nextSession = { customerId: account.id, signedInAt: new Date().toISOString() };
      setSession(nextSession);
      storage.setCustomerSession(nextSession);
      return { ok: true };
    },
    [accounts],
  );

  const logout = useCallback(() => {
    setSession(null);
    storage.clearCustomerSession();
  }, []);

  const updateProfile = useCallback(
    (updates: Partial<Omit<CustomerProfile, 'id' | 'createdAt'>>) => {
      if (!customer) return;
      const nextAccounts = accounts.map((account) =>
        account.id === customer.id
          ? {
              ...account,
              ...updates,
              username: updates.username ? normalizeIdentifier(updates.username) : account.username,
              email: updates.email ? normalizeIdentifier(updates.email) : account.email,
            }
          : account,
      );
      persistAccounts(nextAccounts);
    },
    [accounts, customer, persistAccounts],
  );

  return (
    <CustomerAuthContext.Provider
      value={{
        customer,
        isAuthenticated: Boolean(customer),
        signup,
        login,
        logout,
        updateProfile,
      }}
    >
      {children}
    </CustomerAuthContext.Provider>
  );
}

export function useCustomerAuth() {
  const context = useContext(CustomerAuthContext);
  if (context === undefined) {
    throw new Error('useCustomerAuth must be used within a CustomerAuthProvider');
  }
  return context;
}
