"use client";
import { useState } from "react";
import { useRouter, useSearchParams } from "next/navigation";
import { useAuth } from "@/features/authentication/contexts/AuthContext";
import { login } from "@/features/authentication/services/session.service";
import { authReturnPath } from "../lib/authReturnPath.mjs";
export function useLogin() {
  const router = useRouter();
  const searchParams = useSearchParams();
  const { loginState } = useAuth();
  const [submitting, setSubmitting] = useState(false);
  const [error, setError] = useState("");
  const finish = async (token) => {
    await loginState(token);
    const requested = searchParams.get("next") || "";
    const destination = authReturnPath(requested);
    sessionStorage.removeItem("veriq_return_path");
    router.replace(destination);
  };
  const passwordLogin = async (email, password) => {
    if (submitting) return;
    setSubmitting(true);
    setError("");
    try {
      const response = await login(email.trim(), password);
      await finish(response.access_token || response);
    } catch (reason) {
      setError(reason instanceof Error ? reason.message : "Email hoặc mật khẩu không đúng");
      setSubmitting(false);
    }
  };
  return { submitting, error, passwordLogin };
}
