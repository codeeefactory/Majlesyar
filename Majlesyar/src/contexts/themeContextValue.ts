import { createContext } from 'react';

export type ThemePreference = 'auto' | 'light' | 'night';

export interface ThemeContextValue {
  isNight: boolean;
  preference: ThemePreference;
  toggleTheme: () => void;
}

export const ThemeContext = createContext<ThemeContextValue | undefined>(undefined);
