"use client";
import { useState } from "react";
import { verifyEmailAPI } from "../services/session.service";

export function useEmailVerification() {
  const [submitting, setSubmitting] = useState(false);
  const [verifiedEmail, setVerifiedEmail] = useState("");
  const [error, setError] = useState("");

  const submit = async (token) => {
    if (submitting) return;
    const normalizedToken = token.trim();
    if (normalizedToken.length < 16) {
      setError("Mã xác minh cần ít nhất 16 ký tự");
      return;
    }
    setSubmitting(true);
    setError("");
    try {
      const result = await verifyEmailAPI(normalizedToken);
      setVerifiedEmail(result?.email || "");
    } catch (reason) {
      setError(reason instanceof Error ? reason.message : "Không thể xác minh địa chỉ thư điện tử");
    } finally {
      setSubmitting(false);
    }
  };

  return { submitting, verifiedEmail, error, submit };
}
