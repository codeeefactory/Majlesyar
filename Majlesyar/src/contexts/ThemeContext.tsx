import { useEffect, useMemo, useState, type ReactNode } from 'react';
import { ThemeContext, type ThemeContextValue, type ThemePreference } from '@/contexts/themeContextValue';

const STORAGE_KEY = 'majlesyar-theme';
function isNightByDeviceTime(date = new Date()) {
  const hour = date.getHours();
  return hour >= 19 || hour < 7;
}

function getStoredPreference(): ThemePreference {
  if (typeof window === 'undefined') return 'auto';
  const stored = window.localStorage.getItem(STORAGE_KEY);
  return stored === 'light' || stored === 'night' ? stored : 'auto';
}

export function ThemeProvider({ children }: { children: ReactNode }) {
  const [preference, setPreference] = useState<ThemePreference>(getStoredPreference);
  const [isDeviceNight, setIsDeviceNight] = useState(() => isNightByDeviceTime());

  useEffect(() => {
    const refreshDeviceTime = () => setIsDeviceNight(isNightByDeviceTime());
    const intervalId = window.setInterval(refreshDeviceTime, 60_000);
    return () => window.clearInterval(intervalId);
  }, []);

  const isNight = preference === 'auto' ? isDeviceNight : preference === 'night';

  const value = useMemo<ThemeContextValue>(() => ({
    isNight,
    preference,
    toggleTheme: () => {
      setPreference((currentPreference) => {
        const currentlyNight = currentPreference === 'auto'
          ? isNightByDeviceTime()
          : currentPreference === 'night';
        const nextPreference: ThemePreference = currentlyNight ? 'light' : 'night';
        window.localStorage.setItem(STORAGE_KEY, nextPreference);
        return nextPreference;
      });
    },
  }), [isNight, preference]);

  return <ThemeContext.Provider value={value}>{children}</ThemeContext.Provider>;
}
