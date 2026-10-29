"use client";
import React, { createContext, useCallback, useContext, useEffect, useState } from "react";
import {
  getUserMe,
  getToken,
  removeToken,
  logoutAPI,
} from "@/features/authentication/services/session.service";
import { useRouter } from "next/navigation";
import { authReturnPath } from "../lib/authReturnPath.mjs";
const AuthContext = createContext(undefined);
export function AuthProvider({ children }) {
  const [user, setUser] = useState(null);
  const [isLoading, setIsLoading] = useState(true);
  const [authError, setAuthError] = useState("");
  const router = useRouter();
  const clearAuth = useCallback((expectedToken) => {
    if (expectedToken && getToken() !== expectedToken) return false;
    removeToken(expectedToken);
    const cookieToken = document.cookie
      .split(";")
      .map((part) => part.trim())
      .find((part) => part.startsWith("token="))
      ?.slice("token=".length);
    if (!expectedToken || cookieToken === expectedToken) {
      document.cookie = "token=; path=/; max-age=0; SameSite=Lax";
    }
    setUser(null);
    setAuthError("");
    return true;
  }, []);
  const fetchUser = useCallback(
    async ({ showLoading = true } = {}) => {
      const token = getToken();
      if (!token) {
        setUser(null);
        setAuthError("");
        setIsLoading(false);
        return null;
      }
      if (showLoading) setIsLoading(true);
      try {
        const data = await getUserMe();
        if (getToken() !== token) {
          if (!getToken()) {
            setUser(null);
            setAuthError("");
          }
          return null;
        }
        if (data) {
          setUser(data);
          setAuthError("");
          document.cookie = `token=${token}; path=/; max-age=604800; SameSite=Lax`;
          return data;
        } else {
          clearAuth(token);
          return null;
        }
      } catch {
        if (getToken() !== token) {
          if (!getToken()) {
            setUser(null);
            setAuthError("");
          }
          return null;
        }
        setUser(null);
        setAuthError("Không thể xác minh phiên đăng nhập. Hãy thử lại khi máy chủ hoạt động.");
        return null;
      } finally {
        if (showLoading) setIsLoading(false);
      }
    },
    [clearAuth],
  );
  useEffect(() => {
    void fetchUser();
  }, [fetchUser]);
  useEffect(() => {
    const handleSessionExpired = () => {
      const token = getToken();
      if (!token || !clearAuth(token) || window.location.pathname === "/dang-nhap") return;
      const requestedPath = `${window.location.pathname}${window.location.search}`;
      const next = authReturnPath(requestedPath);
      router.replace(`/dang-nhap?next=${encodeURIComponent(next)}`);
    };
    window.addEventListener("veriq-session-expired", handleSessionExpired);
    return () => window.removeEventListener("veriq-session-expired", handleSessionExpired);
  }, [clearAuth, router]);
  const loginState = useCallback(
    async (token) => {
      localStorage.setItem("veriq_token", token);
      document.cookie = `token=${token}; path=/; max-age=604800; SameSite=Lax`;
      try {
        const verifiedUser = await fetchUser();
        if (!verifiedUser) {
          throw new Error("Không thể xác minh phiên đăng nhập. Vui lòng thử lại.");
        }
      } catch (error) {
        clearAuth(token);
        throw error;
      }
    },
    [clearAuth, fetchUser],
  );
  const logoutState = useCallback(async () => {
    const token = getToken();
    try {
      await logoutAPI();
    } finally {
      if (clearAuth(token)) router.push("/dang-nhap");
    }
  }, [clearAuth, router]);
  const refreshUser = useCallback(() => fetchUser({ showLoading: false }), [fetchUser]);
  return (
    <AuthContext.Provider
      value={{
        user,
        isAuthenticated: !!user,
        isLoading,
        authError,
        loginState,
        logoutState,
        refreshUser,
      }}
    >
      {children}
    </AuthContext.Provider>
  );
}
export const useAuth = () => {
  const context = useContext(AuthContext);
  if (!context) {
    throw new Error("useAuth passed outside of AuthProvider");
  }
  return context;
};
