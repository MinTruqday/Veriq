"use client";
import Link from "next/link";
import { Suspense, useState } from "react";
import { useSearchParams } from "next/navigation";
import InlineState from "@/shared/components/common/InlineState";
import { Button } from "@/shared/components/ui/Button";
import AuthField from "../components/AuthField";
import AuthFrame from "../components/AuthFrame";
import AuthLoading from "../components/AuthLoading";
import { useEmailVerification } from "../hooks/useEmailVerification";

function EmailVerificationContent() {
  const email = useSearchParams().get("email") || "";
  const [token, setToken] = useState("");
  const { submitting, verifiedEmail, error, submit } = useEmailVerification();

  if (verifiedEmail) {
    return (
      <AuthFrame title="Email đã được xác minh">
        <InlineState
          title="Xác minh thành công"
          detail={
            verifiedEmail
              ? `Địa chỉ ${verifiedEmail} đã được xác minh.`
              : "Địa chỉ thư điện tử đã được xác minh."
          }
        />
        <Link className="apple-button mt-5 w-full justify-center" href="/dang-nhap">
          Đến đăng nhập
        </Link>
      </AuthFrame>
    );
  }

  return (
    <AuthFrame
      title="Xác minh địa chỉ thư điện tử"
      description={email ? `Nhập mã đã gửi đến ${email}` : "Nhập mã xác minh đã nhận qua email"}
      footer={
        <Link href="/dang-nhap" className="font-semibold text-brand hover:text-brand-hover">
          Quay lại đăng nhập
        </Link>
      }
    >
      {error && (
        <div className="mb-5">
          <InlineState title="Không thể xác minh" detail={error} tone="danger" />
        </div>
      )}
      <form
        className="space-y-5"
        onSubmit={(event) => {
          event.preventDefault();
          void submit(token);
        }}
      >
        <AuthField
          id="email-verification-token"
          name="token"
          label="Mã xác minh"
          autoComplete="one-time-code"
          required
          minLength={16}
          maxLength={256}
          helper="Mã xác minh có ít nhất 16 ký tự."
          value={token}
          onChange={(event) => setToken(event.target.value)}
        />
        <Button type="submit" className="w-full" disabled={submitting}>
          {submitting ? "Đang xác minh" : "Xác minh email"}
        </Button>
      </form>
    </AuthFrame>
  );
}

export default function EmailVerificationPage() {
  return (
    <Suspense fallback={<AuthLoading />}>
      <EmailVerificationContent />
    </Suspense>
  );
}
