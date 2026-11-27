"use client";
import { useEffect, useState } from "react";
import { useRouter } from "next/navigation";
import {
  forgotPasswordAPI,
  resetPasswordAPI,
  verifyCodeAPI,
} from "@/features/authentication/services/session.service";
export function useForgotPassword() {
  const router = useRouter();
  const [submitting, setSubmitting] = useState(false);
  const [error, setError] = useState("");
  const submit = async (email) => {
    if (submitting) return;
    setSubmitting(true);
    setError("");
    try {
      await forgotPasswordAPI(email.trim());
      router.push(`/xac-thuc?email=${encodeURIComponent(email.trim())}`);
    } catch (reason) {
      setError(reason instanceof Error ? reason.message : "Không thể gửi mã xác thực");
      setSubmitting(false);
    }
  };
  return { submitting, error, submit };
}
export function useVerifyCode(email) {
  const router = useRouter();
  const [submitting, setSubmitting] = useState(false);
  const [resending, setResending] = useState(false);
  const [countdown, setCountdown] = useState(60);
  const [error, setError] = useState("");
  useEffect(() => {
    if (countdown <= 0) return;
    const timer = window.setTimeout(() => setCountdown((value) => value - 1), 1000);
    return () => window.clearTimeout(timer);
  }, [countdown]);
  const verify = async (token) => {
    if (submitting) return;
    if (token.trim().length < 6) {
      setError("Mã xác thực cần ít nhất 6 ký tự");
      return;
    }
    setSubmitting(true);
    setError("");
    try {
      await verifyCodeAPI(token.trim());
      router.push(`/dat-lai-mat-khau?token=${encodeURIComponent(token.trim())}`);
    } catch (reason) {
      setError(reason instanceof Error ? reason.message : "Mã xác thực không hợp lệ");
      setSubmitting(false);
    }
  };
  const resend = async () => {
    if (!email || resending) return;
    setResending(true);
    setError("");
    try {
      await forgotPasswordAPI(email);
      setCountdown(60);
    } catch (reason) {
      setError(reason instanceof Error ? reason.message : "Không thể gửi lại mã xác thực");
    } finally {
      setResending(false);
    }
  };
  return { submitting, resending, countdown, error, verify, resend };
}
export function useResetPassword(token) {
  const router = useRouter();
  const [submitting, setSubmitting] = useState(false);
  const [error, setError] = useState("");
  const submit = async (password) => {
    if (submitting || !token) return;
    if (password.length < 12) {
      setError("Mật khẩu cần ít nhất 12 ký tự");
      return;
    }
    setSubmitting(true);
    setError("");
    try {
      await resetPasswordAPI(token, password);
      router.push("/dang-nhap");
    } catch (reason) {
      setError(reason instanceof Error ? reason.message : "Không thể cập nhật mật khẩu");
      setSubmitting(false);
    }
  };
  return { submitting, error, submit };
}
