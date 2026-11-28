"use client";
import { Suspense, useState } from "react";
import { useSearchParams } from "next/navigation";
import InlineState from "@/shared/components/common/InlineState";
import AuthField from "../components/AuthField";
import AuthFlowLinks from "../components/AuthFlowLinks";
import AuthFrame from "../components/AuthFrame";
import AuthLoading from "../components/AuthLoading";
import AuthSubmitButton from "../components/AuthSubmitButton";
import { useVerifyCode } from "../hooks/usePasswordRecovery";
function VerifyCodeContent() {
  const email = useSearchParams().get("email") || "";
  const [token, setToken] = useState("");
  const { submitting, resending, countdown, error, verify, resend } = useVerifyCode(email);
  const handleSubmit = (event) => {
    event.preventDefault();
    verify(token);
  };
  return (
    <AuthFrame
      title="Xác minh mã khôi phục mật khẩu"
      description={email ? `Nhập mã đã gửi đến ${email}` : "Nhập mã khôi phục đã nhận qua Email"}
      footer={
        <AuthFlowLinks
          links={[
            { href: "/quen-mat-khau", label: "Gửi mã mới" },
            { href: "/dang-nhap", label: "Quay lại đăng nhập", tone: "ink" },
          ]}
        />
      }
    >
      {error && (
        <div className="mb-5">
          <InlineState title="Không thể xác thực" detail={error} tone="danger" />
        </div>
      )}
      <form className="space-y-5" onSubmit={handleSubmit}>
        <AuthField
          id="verification-code"
          name="token"
          label="Mã xác thực"
          inputMode="numeric"
          autoComplete="one-time-code"
          required
          minLength={6}
          maxLength={128}
          value={token}
          onChange={(event) => setToken(event.target.value)}
          className="text-center text-[20px] tracking-[0.18em]"
        />
        <AuthSubmitButton type="submit" loading={submitting} loadingLabel="Đang kiểm tra mã">
          Xác nhận
        </AuthSubmitButton>
      </form>
      {email && (
        <div className="mt-5 text-[13px] text-ink-muted">
          {countdown > 0 ? (
            <p>Có thể gửi lại sau {countdown} giây</p>
          ) : (
            <button
              type="button"
              onClick={resend}
              disabled={resending}
              className="font-semibold text-brand hover:text-brand-hover"
            >
              {resending ? "Đang gửi" : "Gửi lại mã"}
            </button>
          )}
        </div>
      )}
    </AuthFrame>
  );
}
export default function VerifyCodePage() {
  return (
    <Suspense fallback={<AuthLoading />}>
      <VerifyCodeContent />
    </Suspense>
  );
}
