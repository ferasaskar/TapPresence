import { createContext, useContext, useEffect, useState } from "react";
import { api } from "@/lib/api";

const AuthContext = createContext(null);

export const AuthProvider = ({ children }) => {
  const [user, setUser] = useState(null);
  const [entitlements, setEntitlements] = useState(null);
  const [workspace, setWorkspace] = useState(null);
  const [memberships, setMemberships] = useState([]);
  const [ready, setReady] = useState(false);

  useEffect(() => {
    const token = localStorage.getItem("ariadni_token");
    if (!token) { setUser(false); setReady(true); return; }
    api.get("/auth/session")
      .then((res) => {
        setUser(res.data.user);
        setEntitlements(res.data.entitlements);
        setWorkspace(res.data.workspace);
        setMemberships(res.data.memberships || []);
      })
      .catch(() => { localStorage.removeItem("ariadni_token"); setUser(false); })
      .finally(() => setReady(true));
  }, []);

  const _apply = (data) => {
    localStorage.setItem("ariadni_token", data.token);
    if (data.refresh_token) localStorage.setItem("ariadni_refresh", data.refresh_token);
    setUser(data.user);
    setEntitlements(data.entitlements || null);
    setWorkspace(data.workspace || null);
    setMemberships(data.memberships || []);
    return data.user;
  };

  const login = async (email, password) => {
    const { data } = await api.post("/auth/login", { email, password });
    return _apply(data);
  };

  const register = async (payload) => {
    const { data } = await api.post("/auth/register", payload);
    return _apply(data);
  };

  const refreshSession = async () => {
    try {
      const res = await api.get("/auth/session");
      setUser(res.data.user);
      setEntitlements(res.data.entitlements);
      setWorkspace(res.data.workspace);
      setMemberships(res.data.memberships || []);
      return res.data;
    } catch { return null; }
  };

  const logout = () => {
    const refresh = localStorage.getItem("ariadni_refresh");
    if (refresh) api.post("/auth/logout", { refresh_token: refresh }).catch(() => {});
    localStorage.removeItem("ariadni_token");
    localStorage.removeItem("ariadni_refresh");
    setUser(false); setEntitlements(null); setWorkspace(null); setMemberships([]);
  };

  return (
    <AuthContext.Provider value={{ user, entitlements, workspace, memberships, ready, login, register, logout, refreshSession }}>
      {children}
    </AuthContext.Provider>
  );
};

export const useAuth = () => useContext(AuthContext);
