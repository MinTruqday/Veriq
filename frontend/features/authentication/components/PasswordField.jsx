"use client";
import { useState } from "react";
import AuthField from "./AuthField";
export default function PasswordField(props) {
  const [visible, setVisible] = useState(false);
  return (
    <div className="relative">
      <AuthField {...props} type={visible ? "text" : "password"} className="pr-20" />
      <button
        type="button"
        onClick={() => setVisible((value) => !value)}
        className="absolute right-2 top-[30px] min-h-10 rounded-control px-2 text-[12px] font-semibold text-ink-muted hover:bg-surface-quiet hover:text-ink"
        aria-label={visible ? "Ẩn mật khẩu" : "Hiện mật khẩu"}
        aria-pressed={visible}
      >
        {visible ? "Ẩn" : "Hiện"}
      </button>
    </div>
  );
}
