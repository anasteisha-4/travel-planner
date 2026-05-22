import { createContext, useContext, useEffect, useState, useSyncExternalStore } from 'react';

type Theme = 'dark' | 'light' | 'system';

type ThemeProviderProps = {
  children: React.ReactNode;
  defaultTheme?: Theme;
  storageKey?: string;
};

type ThemeProviderState = {
  theme: Theme;
  resolvedTheme: Exclude<Theme, 'system'>;
  setTheme: (theme: Theme) => void;
};

const initialState: ThemeProviderState = {
  theme: 'system',
  resolvedTheme: 'light',
  setTheme: () => null,
};

const ThemeProviderContext = createContext<ThemeProviderState>(initialState);

const getSystemTheme = (): Exclude<Theme, 'system'> => {
  if (typeof window === 'undefined') return 'light';
  return window.matchMedia('(prefers-color-scheme: dark)').matches ? 'dark' : 'light';
};

const subscribeToSystemTheme = (onChange: () => void) => {
  const mediaQuery = window.matchMedia('(prefers-color-scheme: dark)');
  mediaQuery.addEventListener('change', onChange);
  return () => mediaQuery.removeEventListener('change', onChange);
};

const getServerTheme = (): Exclude<Theme, 'system'> => 'light';

export const ThemeProvider = ({
  children,
  defaultTheme = 'system',
  storageKey = 'vite-ui-theme',
  ...props
}: ThemeProviderProps) => {
  const [theme, setTheme] = useState<Theme>(() => {
    if (typeof window === 'undefined') return defaultTheme;
    return (localStorage.getItem(storageKey) as Theme | null) ?? defaultTheme;
  });
  const systemTheme = useSyncExternalStore(
    subscribeToSystemTheme,
    getSystemTheme,
    getServerTheme
  );
  const resolvedTheme = theme === 'system' ? systemTheme : theme;

  const applyTheme = (nextTheme: Exclude<Theme, 'system'>) => {
    const root = window.document.documentElement;
    root.classList.remove('light', 'dark');
    root.classList.add(nextTheme);
  };

  useEffect(() => {
    applyTheme(resolvedTheme);
  }, [resolvedTheme]);

  const value = {
    theme,
    resolvedTheme,
    setTheme: (theme: Theme) => {
      localStorage.setItem(storageKey, theme);
      setTheme(theme);
    },
  };

  return (
    <ThemeProviderContext.Provider {...props} value={value}>
      {children}
    </ThemeProviderContext.Provider>
  );
};

// eslint-disable-next-line react-refresh/only-export-components
export const useTheme = () => {
  const context = useContext(ThemeProviderContext);

  if (context === undefined) throw new Error('useTheme must be used within a ThemeProvider');

  return context;
};
