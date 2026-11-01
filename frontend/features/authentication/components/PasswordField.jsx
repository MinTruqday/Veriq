"use client";
import { useState } from "react";
import { Eye, EyeOff } from "lucide-react";
import AuthField from "./AuthField";
export default function PasswordField(props) {
  const [visible, setVisible] = useState(false);
  return (
    <div className="relative">
      <AuthField {...props} type={visible ? "text" : "password"} className="pr-12" />
      <button
        type="button"
        onClick={() => setVisible((value) => !value)}
        className="absolute right-2 top-[30px] inline-flex size-10 items-center justify-center rounded-control text-ink-muted hover:bg-surface-quiet hover:text-ink focus-visible:outline focus-visible:outline-2 focus-visible:outline-brand"
        aria-label={visible ? "Ẩn mật khẩu" : "Hiện mật khẩu"}
        aria-pressed={visible}
      >
        {visible ? <EyeOff size={18} aria-hidden="true" /> : <Eye size={18} aria-hidden="true" />}
      </button>
    </div>
  );
}
