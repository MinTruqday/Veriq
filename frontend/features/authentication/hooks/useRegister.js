"use client";
import { useState } from "react";
import { useRouter } from "next/navigation";
import { register } from "@/features/authentication/services/session.service";
export function useRegister() {
  const router = useRouter();
  const [submitting, setSubmitting] = useState(false);
  const [error, setError] = useState("");
  const submit = async (values) => {
    if (submitting) return;
    if (values.fullName.trim().length < 2) {
      setError("Tên hiển thị cần ít nhất 2 ký tự");
      return;
    }
    if (!/^[a-zA-Z0-9_-]{3,50}$/.test(values.slug)) {
      setError("Tên tài khoản cần 3 đến 50 ký tự, chỉ gồm chữ, số, gạch dưới hoặc gạch nối");
      return;
    }
    if (values.password.length < 12) {
      setError("Mật khẩu cần ít nhất 12 ký tự");
      return;
    }
    if (!values.agreed) {
      setError("Cần chấp thuận điều khoản để tạo tài khoản");
      return;
    }
    setSubmitting(true);
    setError("");
    try {
      await register(
        values.email.trim(),
        values.password,
        values.fullName.trim(),
        values.slug,
        true,
      );
      router.push(`/xac-minh-thu-dien-tu?email=${encodeURIComponent(values.email.trim())}`);
    } catch (reason) {
      setError(reason instanceof Error ? reason.message : "Không thể tạo tài khoản");
      setSubmitting(false);
    }
  };
  return { submitting, error, submit };
}
