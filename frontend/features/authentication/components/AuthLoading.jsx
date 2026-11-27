import AuthFrame from "./AuthFrame";

export default function AuthLoading({ label = "Đang tải trang xác thực" }) {
  return (
    <AuthFrame title={label}>
      <div role="status" aria-label={label} aria-live="polite" aria-busy="true">
        <div className="skeleton h-11 w-full" aria-hidden="true" />
        <div className="skeleton mt-5 h-11 w-full" aria-hidden="true" />
        <div className="skeleton mt-6 h-11 w-full" aria-hidden="true" />
      </div>
    </AuthFrame>
  );
}
