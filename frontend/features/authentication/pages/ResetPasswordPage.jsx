"use client";
import Link from "next/link";
import { Suspense, useState } from "react";
import { useSearchParams } from "next/navigation";
import InlineState from "@/shared/components/common/InlineState";
import AuthFrame from "../components/AuthFrame";
import AuthFlowLinks from "../components/AuthFlowLinks";
import AuthLoading from "../components/AuthLoading";
import AuthSubmitButton from "../components/AuthSubmitButton";
import PasswordField from "../components/PasswordField";
import { useResetPassword } from "../hooks/usePasswordRecovery";
function ResetPasswordContent() {
  const token = useSearchParams().get("token") || "";
  const [password, setPassword] = useState("");
  const { submitting, error, submit } = useResetPassword(token);
  const handleSubmit = (event) => {
    event.preventDefault();
    submit(password);
  };
  return (
    <AuthFrame
      title="Đặt mật khẩu mới"
      description="Mật khẩu mới cần có ít nhất 12 ký tự. Sau khi cập nhật, bạn sẽ được chuyển về trang đăng nhập"
      footer={
        token ? (
          <AuthFlowLinks links={[{ href: "/dang-nhap", label: "Quay lại đăng nhập" }]} />
        ) : null
      }
    >
      {!token ? (
        <div className="grid gap-4">
          <InlineState
            title="Liên kết đặt lại không hợp lệ"
            detail="Liên kết không có mã đặt lại. Hãy yêu cầu một mã mới để tiếp tục"
            tone="warning"
          />
          <Link className="primary-button justify-center" href="/quen-mat-khau">
            Yêu cầu mã mới
          </Link>
        </div>
      ) : (
        <>
          {error && (
            <div className="mb-5">
              <InlineState title="Không thể cập nhật" detail={error} tone="danger" />
            </div>
          )}
          <form className="space-y-5" onSubmit={handleSubmit}>
            <PasswordField
              id="new-password"
              name="new_password"
              label="Mật khẩu mới"
              autoComplete="new-password"
              required
              minLength={12}
              maxLength={128}
              value={password}
              onChange={(event) => setPassword(event.target.value)}
            />
            <AuthSubmitButton
              type="submit"
              loading={submitting}
              loadingLabel="Đang cập nhật mật khẩu"
              disabled={!token}
            >
              Cập nhật
            </AuthSubmitButton>
          </form>
        </>
      )}
    </AuthFrame>
  );
}
export default function ResetPasswordPage() {
  return (
    <Suspense fallback={<AuthLoading />}>
      <ResetPasswordContent />
    </Suspense>
  );
}
