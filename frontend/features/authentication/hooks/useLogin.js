"use client";
import { useState } from "react";
import { useRouter, useSearchParams } from "next/navigation";
import { useAuth } from "@/features/authentication/contexts/AuthContext";
import {
  getGoogleLoginUrlAPI,
  login,
  passkeyLoginBeginAPI,
  passkeyLoginFinishAPI,
} from "@/features/authentication/services/session.service";
import { b64urlToBuffer, bufferToB64url } from "../lib/webauthn";
import { authReturnPath, isSafeAuthReturnPath } from "../lib/authReturnPath.mjs";
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
  const passkeyLogin = async (email) => {
    if (submitting) return;
    if (!email.trim()) {
      setError("Nhập email trước khi dùng Passkey");
      return;
    }
    setSubmitting(true);
    setError("");
    try {
      const begin = await passkeyLoginBeginAPI(email.trim());
      const assertion = await navigator.credentials.get({
        publicKey: {
          challenge: b64urlToBuffer(begin.challenge),
          rpId: begin.rpId,
          timeout: begin.timeout,
          userVerification: begin.userVerification,
          allowCredentials: (begin.allowCredentials || []).map((credential) => ({
            type: credential.type,
            id: b64urlToBuffer(credential.id),
          })),
        },
      });
      if (!assertion) throw new Error("Không nhận được thông tin passkey");
      const credential = assertion;
      const response = credential.response;
      const result = await passkeyLoginFinishAPI(email.trim(), {
        id: credential.id,
        rawId: bufferToB64url(credential.rawId),
        type: credential.type,
        response: {
          clientDataJSON: bufferToB64url(response.clientDataJSON),
          authenticatorData: bufferToB64url(response.authenticatorData),
          signature: bufferToB64url(response.signature),
          userHandle: response.userHandle ? bufferToB64url(response.userHandle) : null,
        },
      });
      await finish(result.access_token || result);
    } catch (reason) {
      setError(reason instanceof Error ? reason.message : "Không thể đăng nhập bằng Passkey");
      setSubmitting(false);
    }
  };
  const googleLogin = async () => {
    if (submitting) return;
    setSubmitting(true);
    setError("");
    try {
      const requested = searchParams.get("next") || "";
      sessionStorage.removeItem("veriq_return_path");
      if (isSafeAuthReturnPath(requested)) {
        sessionStorage.setItem("veriq_return_path", requested);
      }
      window.location.assign(await getGoogleLoginUrlAPI());
    } catch (reason) {
      setError(reason instanceof Error ? reason.message : "Không thể kết nối với Google");
      setSubmitting(false);
    }
  };
  return { submitting, error, passwordLogin, passkeyLogin, googleLogin };
}
