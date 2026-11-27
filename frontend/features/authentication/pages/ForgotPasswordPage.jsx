"use client";
import { useState } from "react";
import InlineState from "@/shared/components/common/InlineState";
import AuthField from "../components/AuthField";
import AuthFlowLinks from "../components/AuthFlowLinks";
import AuthFrame from "../components/AuthFrame";
import AuthSubmitButton from "../components/AuthSubmitButton";
import { useForgotPassword } from "../hooks/usePasswordRecovery";
export default function ForgotPasswordPage() {
  const [email, setEmail] = useState("");
  const { submitting, error, submit } = useForgotPassword();
  const handleSubmit = (event) => {
    event.preventDefault();
    submit(email);
  };
  return (
    <AuthFrame
      title="Khôi phục mật khẩu"
      description="Nhập Email của tài khoản để nhận mã xác thực."
      footer={
        <AuthFlowLinks
          links={[
            { href: "/xac-thuc", label: "Nhập mã" },
            { href: "/dang-nhap", label: "Quay lại đăng nhập", tone: "ink" },
          ]}
        />
      }
    >
      {error && (
        <div className="mb-5">
          <InlineState title="Không thể gửi mã" detail={error} tone="danger" />
        </div>
      )}
      <form className="space-y-5" onSubmit={handleSubmit}>
        <AuthField
          id="recovery-email"
          name="email"
          label="Email"
          type="email"
          autoComplete="email"
          required
          value={email}
          onChange={(event) => setEmail(event.target.value)}
        />
        <AuthSubmitButton type="submit" loading={submitting} loadingLabel="Đang gửi mã">
          Gửi mã
        </AuthSubmitButton>
      </form>
    </AuthFrame>
  );
}
