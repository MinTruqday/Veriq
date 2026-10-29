"use client";
import InlineState from "@/shared/components/common/InlineState";
import { Button } from "@/shared/components/ui/Button";
import { usePasskeySetup } from "../hooks/usePasskeySetup";
export default function PasskeySetup({ email, onClose, onSuccess }) {
  const passkey = usePasskeySetup(email, onSuccess);
  return (
    <div>
      <p className="break-words text-[14px] leading-relaxed text-ink-muted">
        Đăng nhập bằng thiết bị này mà không cần nhập mật khẩu. Bạn có thể bỏ qua và thiết lập sau.
      </p>
      {passkey.error && (
        <div className="mt-5">
          <InlineState title="Không thể thiết lập" detail={passkey.error} tone="danger" />
        </div>
      )}
      <div className="mt-6 flex flex-wrap justify-end gap-3">
        <Button variant="secondary" onClick={onClose} disabled={passkey.loading}>
          Để sau
        </Button>
        <Button onClick={passkey.register} disabled={passkey.loading}>
          {passkey.loading ? "Đang thiết lập" : "Thiết lập"}
        </Button>
      </div>
    </div>
  );
}
