"use client";
import Link from "next/link";
import { Suspense, useState } from "react";
import { useSearchParams } from "next/navigation";
import InlineState from "@/shared/components/common/InlineState";
import AuthFlowLinks from "../components/AuthFlowLinks";
import AuthField from "../components/AuthField";
import AuthFrame from "../components/AuthFrame";
import AuthLoading from "../components/AuthLoading";
import AuthSubmitButton from "../components/AuthSubmitButton";
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
            verifiedEmail ? `Email ${verifiedEmail} đã được xác minh` : "Email đã được xác minh"
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
      title="Xác minh Email"
      description={email ? `Nhập mã đã gửi đến ${email}` : "Nhập mã xác minh đã nhận qua Email"}
      footer={<AuthFlowLinks links={[{ href: "/dang-nhap", label: "Quay lại đăng nhập" }]} />}
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
          helper="Mã xác minh có ít nhất 16 ký tự"
          value={token}
          onChange={(event) => setToken(event.target.value)}
        />
        <AuthSubmitButton type="submit" loading={submitting} loadingLabel="Đang xác minh Email">
          Xác minh Email
        </AuthSubmitButton>
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
