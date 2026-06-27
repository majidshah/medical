import {
  createContext,
  useCallback,
  useContext,
  useEffect,
  useState,
  type ReactNode,
} from "react";
import { useNavigate } from "react-router-dom";
import { useQueryClient } from "@tanstack/react-query";

import { login as apiLogin, register as apiRegister } from "@/api/auth";
import {
  clearTokens,
  getAccessToken,
  setOnAuthFailure,
  setTokens,
} from "@/api/client";
import { useTheme } from "@/lib/theme-context";

interface AuthState {
  isAuthenticated: boolean;
  isLoading: boolean;
  login: (email: string, password: string) => Promise<void>;
  register: (email: string, password: string) => Promise<void>;
  logout: () => void;
}

const AuthContext = createContext<AuthState | null>(null);

export function AuthProvider({ children }: { children: ReactNode }) {
  const [isAuthenticated, setIsAuthenticated] = useState(
    () => !!getAccessToken(),
  );
  const [isLoading, setIsLoading] = useState(false);
  const queryClient = useQueryClient();
  const navigate = useNavigate();
  const theme = useTheme();

  useEffect(() => {
    setIsAuthenticated(!!getAccessToken());
  }, []);

  useEffect(() => {
    setOnAuthFailure(() => {
      setIsAuthenticated(false);
      queryClient.clear();
      theme.resetToDefaults();
      navigate("/login");
    });
  }, [queryClient, navigate, theme]);

  const login = useCallback(async (email: string, password: string) => {
    setIsLoading(true);
    try {
      const tokens = await apiLogin(email, password);
      setTokens(tokens.access_token, tokens.refresh_token);
      setIsAuthenticated(true);
      await theme.loadFromAccount();
    } finally {
      setIsLoading(false);
    }
  }, [theme]);

  const register = useCallback(async (email: string, password: string) => {
    setIsLoading(true);
    try {
      await apiRegister(email, password);
      const tokens = await apiLogin(email, password);
      setTokens(tokens.access_token, tokens.refresh_token);
      setIsAuthenticated(true);
      await theme.loadFromAccount();
    } finally {
      setIsLoading(false);
    }
  }, [theme]);

  const logout = useCallback(() => {
    clearTokens();
    setIsAuthenticated(false);
    queryClient.clear();
    theme.resetToDefaults();
  }, [queryClient, theme]);

  return (
    <AuthContext.Provider
      value={{ isAuthenticated, isLoading, login, register, logout }}
    >
      {children}
    </AuthContext.Provider>
  );
}

export function useAuth() {
  const ctx = useContext(AuthContext);
  if (!ctx) throw new Error("useAuth must be inside AuthProvider");
  return ctx;
}
