import {
  createContext,
  useCallback,
  useContext,
  useEffect,
  useState,
  type ReactNode,
} from "react";

import {
  getPreferences,
  updatePreferences,
  type ThemePreferences,
} from "@/api/preferences";
import { getAccessToken } from "@/api/client";

export type ThemeMode = "light" | "dark";
export type ThemeAccent = "teal" | "blue" | "rose";
export type ThemeDensity = "comfortable" | "compact";

export type { ThemePreferences };

const DEFAULTS: ThemePreferences = {
  mode: "light",
  accent: "teal",
  density: "comfortable",
};

interface ThemeState extends ThemePreferences {
  setMode: (m: ThemeMode) => void;
  setAccent: (a: ThemeAccent) => void;
  setDensity: (d: ThemeDensity) => void;
  setAll: (prefs: ThemePreferences) => void;
  loadFromAccount: () => Promise<void>;
  resetToDefaults: () => void;
}

const ThemeContext = createContext<ThemeState | null>(null);

function applyToDOM(prefs: ThemePreferences) {
  const el = document.documentElement;
  el.setAttribute("data-mode", prefs.mode);
  el.setAttribute("data-accent", prefs.accent);
  el.setAttribute("data-density", prefs.density);
}

export function ThemeProvider({ children }: { children: ReactNode }) {
  const [prefs, setPrefsState] = useState<ThemePreferences>(() => {
    applyToDOM(DEFAULTS);
    return DEFAULTS;
  });

  useEffect(() => {
    applyToDOM(prefs);
  }, [prefs]);

  const persist = useCallback((next: ThemePreferences) => {
    setPrefsState(next);
    applyToDOM(next);
    if (getAccessToken()) {
      updatePreferences(next).catch(() => {});
    }
  }, []);

  const loadFromAccount = useCallback(async () => {
    if (!getAccessToken()) return;
    try {
      const p = await getPreferences();
      setPrefsState(p);
      applyToDOM(p);
    } catch {
      // Keep defaults on failure
    }
  }, []);

  const resetToDefaults = useCallback(() => {
    setPrefsState(DEFAULTS);
    applyToDOM(DEFAULTS);
  }, []);

  const setMode = useCallback(
    (mode: ThemeMode) => persist({ ...prefs, mode }),
    [prefs, persist],
  );
  const setAccent = useCallback(
    (accent: ThemeAccent) => persist({ ...prefs, accent }),
    [prefs, persist],
  );
  const setDensity = useCallback(
    (density: ThemeDensity) => persist({ ...prefs, density }),
    [prefs, persist],
  );
  const setAll = useCallback(
    (p: ThemePreferences) => persist(p),
    [persist],
  );

  return (
    <ThemeContext.Provider
      value={{
        ...prefs,
        setMode,
        setAccent,
        setDensity,
        setAll,
        loadFromAccount,
        resetToDefaults,
      }}
    >
      {children}
    </ThemeContext.Provider>
  );
}

export function useTheme() {
  const ctx = useContext(ThemeContext);
  if (!ctx) throw new Error("useTheme must be inside ThemeProvider");
  return ctx;
}
