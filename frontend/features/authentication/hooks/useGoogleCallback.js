"use client";
import { useEffect, useRef, useState } from "react";
import { useRouter, useSearchParams } from "next/navigation";
import { useAuth } from "@/features/authentication/contexts/AuthContext";
import { completeGoogleLoginAPI } from "@/features/authentication/services/session.service";
import { authReturnPath } from "../lib/authReturnPath.mjs";
import { getOAuthCallbackAttempt } from "../lib/oauthCallbackAttempt.mjs";
export function useGoogleCallback() {
  const router = useRouter();
  const params = useSearchParams();
  const { loginState } = useAuth();
  const [emailForPasskey, setEmailForPasskey] = useState("");
  const [error, setError] = useState("");
  const callbackAttempt = useRef(null);
  useEffect(() => {
    const code = params.get("code");
    const state = params.get("state");
    if (!code || !state) {
      setError("Thiếu mã xác thực từ Google");
      return;
    }
    let active = true;
    const complete = async () => {
      try {
        const attemptKey = `${code}\u0000${state}`;
        const data = await getOAuthCallbackAttempt(callbackAttempt, attemptKey, async () => {
          const result = await completeGoogleLoginAPI(code, state);
          if (!result.access_token) throw new Error("Không nhận được quyền truy cập");
          await loginState(result.access_token);
          return result;
        });
        if (!active) return;
        if (!data.user?.has_passkey && data.user?.email) setEmailForPasskey(data.user.email);
        else {
          const requested = sessionStorage.getItem("veriq_return_path") || "";
          sessionStorage.removeItem("veriq_return_path");
          router.replace(authReturnPath(requested));
        }
      } catch (reason) {
        if (active)
          setError(reason instanceof Error ? reason.message : "Không thể xác thực bằng Google");
      }
    };
    complete();
    return () => {
      active = false;
    };
  }, [loginState, params, router]);
  return {
    emailForPasskey,
    error,
    finish: () => {
      const requested = sessionStorage.getItem("veriq_return_path") || "";
      sessionStorage.removeItem("veriq_return_path");
      router.replace(authReturnPath(requested));
    },
    back: () => router.replace("/dang-nhap"),
  };
}
