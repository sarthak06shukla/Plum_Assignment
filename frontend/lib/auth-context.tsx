"use client";

import {
  createContext,
  useContext,
  useState,
  useEffect,
  useCallback,
  ReactNode,
} from "react";
import { api, setToken } from "./api";

type AuthState = {
  token: string | null;
  role: string | null;
  email: string | null;
  isAuthenticated: boolean;
};

type AuthContextType = AuthState & {
  login: (email: string, password: string) => Promise<void>;
  register: (name: string, email: string, password: string) => Promise<void>;
  logout: () => void;
  loading: boolean;
};

const AuthContext = createContext<AuthContextType>(null!);

export const useAuth = () => useContext(AuthContext);

export function AuthProvider({ children }: { children: ReactNode }) {
  const [state, setState] = useState<AuthState>({
    token: null,
    role: null,
    email: null,
    isAuthenticated: false,
  });
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    const t = localStorage.getItem("plum_token");
    const r = localStorage.getItem("plum_role");
    const e = localStorage.getItem("plum_email");
    if (t) {
      setToken(t);
      setState({ token: t, role: r, email: e, isAuthenticated: true });
    }
    setLoading(false);
  }, []);

  const login = useCallback(async (email: string, password: string) => {
    const data = await api.login(email, password);
    setToken(data.access_token);
    localStorage.setItem("plum_token", data.access_token);
    localStorage.setItem("plum_role", data.role);
    localStorage.setItem("plum_email", email);
    setState({
      token: data.access_token,
      role: data.role,
      email,
      isAuthenticated: true,
    });
  }, []);

  const register = useCallback(
    async (name: string, email: string, password: string) => {
      const data = await api.register(email, name, password, "USER");
      setToken(data.access_token);
      localStorage.setItem("plum_token", data.access_token);
      localStorage.setItem("plum_role", data.role);
      localStorage.setItem("plum_email", email);
      setState({
        token: data.access_token,
        role: data.role,
        email,
        isAuthenticated: true,
      });
    },
    [],
  );

  const logout = useCallback(() => {
    setToken(null);
    localStorage.removeItem("plum_token");
    localStorage.removeItem("plum_role");
    localStorage.removeItem("plum_email");
    setState({ token: null, role: null, email: null, isAuthenticated: false });
  }, []);

  return (
    <AuthContext.Provider value={{ ...state, login, register, logout, loading }}>
      {children}
    </AuthContext.Provider>
  );
}
