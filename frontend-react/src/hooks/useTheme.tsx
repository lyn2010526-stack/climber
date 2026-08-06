import React, { createContext, useContext, useEffect, useState, useCallback, useMemo } from 'react';

type Theme = 'dark' | 'light';

interface ThemeContextType {
  theme: Theme;
  toggleTheme: () => void;
  setTheme: (theme: Theme) => void;
  isLoading: boolean;
}

const ThemeContext = createContext<ThemeContextType | undefined>(undefined);

// Safe localStorage operations with error handling
const storage = {
  get: (key: string): string | null => {
    try {
      return window.localStorage.getItem(key);
    } catch (e) {
      console.warn('localStorage read failed:', e);
      return null;
    }
  },
  set: (key: string, value: string): void => {
    try {
      window.localStorage.setItem(key, value);
    } catch (e) {
      console.warn('localStorage write failed:', e);
    }
  },
};

export const ThemeProvider: React.FC<{ children: React.ReactNode; defaultTheme?: Theme }> = ({
  children,
  defaultTheme = 'dark',
}) => {
  const [theme, setThemeState] = useState<Theme>('dark');
  const [isLoading, setIsLoading] = useState(true);

  // Initialize theme from localStorage or system preference
  useEffect(() => {
    if (typeof window === 'undefined') {
      setIsLoading(false);
      return;
    }

    try {
      // Step 1: Check stored preference first
      const stored = storage.get('climber-theme') as Theme;
      
      if (stored && (stored === 'dark' || stored === 'light')) {
        setThemeState(stored);
        setIsLoading(false);
        return;
      }

      // Step 2: Fall back to system preference
      const prefersLight = window.matchMedia('(prefers-color-scheme: light)').matches;
      const initialTheme = prefersLight ? 'light' : defaultTheme;
      
      setThemeState(initialTheme);
      setIsLoading(false);
    } catch (error) {
      console.error('Theme initialization error:', error);
      setThemeState(defaultTheme);
      setIsLoading(false);
    }
  }, [defaultTheme]);

  // Apply theme and persist to localStorage
  useEffect(() => {
    if (isLoading) return;

    const root = document.documentElement;
    root.setAttribute('data-theme', theme);
    
    // Persist theme preference
    storage.set('climber-theme', theme);
  }, [theme, isLoading]);

  // Listen for system theme changes (only if user hasn't set manual preference)
  useEffect(() => {
    if (typeof window === 'undefined') return;

    const mediaQuery = window.matchMedia('(prefers-color-scheme: light)');
    
    const handler = (e: MediaQueryListEvent) => {
      // Only auto-switch if no manual preference exists
      if (!storage.get('climber-theme')) {
        setThemeState(e.matches ? 'light' : defaultTheme);
      }
    };

    // Support both old and new API
    const listener = mediaQuery.addEventListener 
      ? () => mediaQuery.addEventListener('change', handler)
      : () => mediaQuery.addListener(handler);
    
    listener();

    return () => {
      mediaQuery.removeEventListener('change', handler);
    };
  }, [defaultTheme]);

  const toggleTheme = useCallback(() => {
    setThemeState((prev) => (prev === 'dark' ? 'light' : 'dark'));
  }, []);

  const setTheme = useCallback((newTheme: Theme) => {
    setThemeState(newTheme);
  }, []);

  const value = useMemo(() => ({
    theme,
    toggleTheme,
    setTheme,
    isLoading,
  }), [theme, toggleTheme, setTheme, isLoading]);

  return <ThemeContext.Provider value={value}>{children}</ThemeContext.Provider>;
};

export const useTheme = (): ThemeContextType => {
  const context = useContext(ThemeContext);
  if (!context) {
    throw new Error('useTheme must be used within a ThemeProvider');
  }
  return context;
};
