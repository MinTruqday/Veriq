"use client";
import Link from "next/link";
import { useState } from "react";
import InlineState from "@/shared/components/common/InlineState";
import { Button } from "@/shared/components/ui/Button";
import AuthField from "../components/AuthField";
import AuthFrame from "../components/AuthFrame";
import PasswordField from "../components/PasswordField";
import { useLogin } from "../hooks/useLogin";
export default function LoginPage() {
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const { submitting, error, passwordLogin, passkeyLogin, googleLogin } = useLogin();
  const submit = (event) => {
    event.preventDefault();
    passwordLogin(email, password);
  };
  return (
    <AuthFrame
      title="Đăng nhập"
      footer={<p>Chưa có tài khoản? Liên hệ quản trị viên để được cấp tài khoản.</p>}
    >
      {error && (
        <div className="mb-5">
          <InlineState title="Không thể đăng nhập" detail={error} tone="danger" />
        </div>
      )}
      <form className="space-y-5" onSubmit={submit}>
        <AuthField
          id="login-email"
          name="email"
          label="Email"
          type="email"
          autoComplete="email"
          required
          value={email}
          onChange={(event) => setEmail(event.target.value)}
        />
        <PasswordField
          id="login-password"
          name="password"
          label="Mật khẩu"
          autoComplete="current-password"
          required
          value={password}
          onChange={(event) => setPassword(event.target.value)}
        />
        <div className="flex justify-end">
          <Link
            href="/quen-mat-khau"
            className="text-[13px] font-semibold text-brand hover:text-brand-hover"
          >
            Quên mật khẩu
          </Link>
        </div>
        <Button type="submit" className="w-full" disabled={submitting}>
          {submitting ? "Đang xử lý" : "Đăng nhập"}
        </Button>
      </form>
      <div className="my-6 flex items-center gap-3" aria-hidden="true">
        <span className="h-px flex-1 bg-border" />
        <span className="text-[12px] text-ink-faint">Hoặc</span>
        <span className="h-px flex-1 bg-border" />
      </div>
      <div className="grid gap-3 sm:grid-cols-2">
        <Button
          type="button"
          variant="secondary"
          disabled={submitting}
          onClick={() => passkeyLogin(email)}
        >
          Passkey
        </Button>
        <Button type="button" variant="secondary" disabled={submitting} onClick={googleLogin}>
          Google
        </Button>
      </div>
    </AuthFrame>
  );
}
