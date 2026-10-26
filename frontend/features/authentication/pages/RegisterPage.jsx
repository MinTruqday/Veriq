"use client";
import Link from "next/link";
import { useState } from "react";
import InlineState from "@/shared/components/common/InlineState";
import { Button } from "@/shared/components/ui/Button";
import AuthField from "../components/AuthField";
import AuthFrame from "../components/AuthFrame";
import PasswordField from "../components/PasswordField";
import { useRegister } from "../hooks/useRegister";
export default function RegisterPage() {
  const [fullName, setFullName] = useState("");
  const [slug, setSlug] = useState("");
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [agreed, setAgreed] = useState(false);
  const { submitting, error, submit } = useRegister();
  const handleSubmit = (event) => {
    event.preventDefault();
    submit({ fullName, slug, email, password, agreed });
  };
  return (
    <AuthFrame
      title="Tạo tài khoản"
      width="md"
      footer={
        <p>
          Đã có tài khoản?{" "}
          <Link href="/dang-nhap" className="font-semibold text-brand hover:text-brand-hover">
            Đăng nhập
          </Link>
        </p>
      }
    >
      {error && (
        <div className="mb-5">
          <InlineState title="Không thể tạo tài khoản" detail={error} tone="danger" />
        </div>
      )}
      <form className="space-y-5" onSubmit={handleSubmit}>
        <div className="grid gap-5 sm:grid-cols-2">
          <AuthField
            id="register-name"
            name="full_name"
            label="Tên hiển thị"
            autoComplete="name"
            required
            minLength={2}
            maxLength={100}
            value={fullName}
            onChange={(event) => setFullName(event.target.value)}
          />
          <AuthField
            id="register-slug"
            name="slug"
            label="Tên tài khoản"
            autoComplete="username"
            required
            minLength={3}
            maxLength={50}
            pattern={"[a-zA-Z0-9_\\-]+"}
            value={slug}
            onChange={(event) => setSlug(event.target.value)}
            helper="Chữ, số, gạch dưới hoặc gạch nối"
          />
        </div>
        <AuthField
          id="register-email"
          name="email"
          label="Email"
          type="email"
          autoComplete="email"
          required
          value={email}
          onChange={(event) => setEmail(event.target.value)}
        />
        <PasswordField
          id="register-password"
          name="password"
          label="Mật khẩu"
          autoComplete="new-password"
          required
          minLength={12}
          maxLength={128}
          value={password}
          onChange={(event) => setPassword(event.target.value)}
          helper="Tối thiểu 12 ký tự"
        />
        <label className="flex items-start gap-3 text-[13px] leading-relaxed text-ink">
          <input
            type="checkbox"
            required
            checked={agreed}
            onChange={(event) => setAgreed(event.target.checked)}
            className="mt-0.5 h-4 w-4 shrink-0 accent-[hsl(var(--brand))]"
          />
          <span>
            Tôi đồng ý với{" "}
            <Link href="/dieu-khoan" className="font-semibold text-brand hover:text-brand-hover">
              điều khoản sử dụng
            </Link>
          </span>
        </label>
        <Button type="submit" className="w-full" disabled={submitting}>
          {submitting ? "Đang xử lý" : "Tạo tài khoản"}
        </Button>
      </form>
    </AuthFrame>
  );
}
