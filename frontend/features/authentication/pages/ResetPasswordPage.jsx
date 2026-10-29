"use client";
import { Suspense, useState } from "react";
import { useSearchParams } from "next/navigation";
import InlineState from "@/shared/components/common/InlineState";
import { Button } from "@/shared/components/ui/Button";
import AuthFrame from "../components/AuthFrame";
import AuthLoading from "../components/AuthLoading";
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
      description="Mật khẩu mới cần có ít nhất 12 ký tự. Sau khi cập nhật, bạn sẽ được chuyển về trang đăng nhập."
    >
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
        <Button type="submit" className="w-full" disabled={submitting || !token}>
          {submitting ? "Đang cập nhật" : "Cập nhật"}
        </Button>
      </form>
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
