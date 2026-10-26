"use client";
import { Suspense } from "react";
import { Button } from "@/shared/components/ui/Button";
import AuthFrame from "@/features/authentication/components/AuthFrame";
import AuthLoading from "@/features/authentication/components/AuthLoading";
import InlineState from "@/shared/components/common/InlineState";
import { useGoogleCallback } from "../hooks/useGoogleCallback";
import PasskeySetup from "../components/PasskeySetup";
function GoogleCallbackContent() {
  const { emailForPasskey, error, finish, back } = useGoogleCallback();
  if (emailForPasskey)
    return (
      <AuthFrame title="Thiết lập passkey">
        <PasskeySetup email={emailForPasskey} onClose={finish} onSuccess={finish} />
      </AuthFrame>
    );
  if (error) {
    return (
      <AuthFrame title="Xác thực Google">
        <InlineState title="Không thể đăng nhập" detail={error} tone="danger" />
        <Button className="mt-5 w-full" onClick={back}>
          Quay lại đăng nhập
        </Button>
      </AuthFrame>
    );
  }
  return <AuthLoading label="Đang xác thực tài khoản Google" />;
}
export default function GoogleCallbackPage() {
  return (
    <Suspense fallback={<AuthLoading />}>
      <GoogleCallbackContent />
    </Suspense>
  );
}
