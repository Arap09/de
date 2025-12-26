import {
  createContext,
  useContext,
  useEffect,
  useState,
  ReactNode,
} from "react";
import { fetchMe, login as loginApi, register as registerApi } from "../api/auth";
import { User } from "../types/auth";

interface AuthContextType {
  user: User | null;
  loading: boolean;
  login: (email: string, password: string) => Promise<void>;
  register: (email: string, password: string) => Promise<void>;
  logout: () => void;
}

const AuthContext = createContext<AuthContextType | undefined>(undefined);

export const AuthProvider = ({ children }: { children: ReactNode }) => {
  const [user, setUser] = useState<User | null>(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    const init = async () => {
      try {
        const me = await fetchMe();
        setUser(me);
      } catch {
        localStorage.removeItem("access_token");
      } finally {
        setLoading(false);
      }
    };
    init();
  }, []);

  const login = async (email: string, password: string) => {
    const data = await loginApi({ email, password });
    localStorage.setItem("access_token", data.access_token);
    const me = await fetchMe();
    setUser(me);
  };

  const register = async (email: string, password: string) => {
    await registerApi({ email, password });
    await login(email, password);
  };

  const logout = () => {
    localStorage.removeItem("access_token");
    setUser(null);
  };

  return (
    <AuthContext.Provider value={{ user, loading, login, register, logout }}>
      {children}
    </AuthContext.Provider>
  );
};

export const useAuthContext = () => {
  const ctx = useContext(AuthContext);
  if (!ctx) throw new Error("useAuthContext must be used within AuthProvider");
  return ctx;
};
