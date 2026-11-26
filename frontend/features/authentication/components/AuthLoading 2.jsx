export default function AuthLoading({ label = "Đang tải trang xác thực" }) {
  return (
    <main
      className="flex min-h-[100dvh] items-center justify-center bg-[#eef3ef] px-4"
      role="status"
      aria-label={label}
      aria-live="polite"
    >
      <div className="w-full max-w-[500px] rounded-3xl bg-surface p-8 shadow-[0_24px_70px_rgba(48,47,42,0.12)]">
        <p className="text-[14px] font-semibold text-ink">{label}</p>
        <div className="skeleton mt-4 h-8 w-48" aria-hidden="true" />
        <div className="skeleton mt-3 h-4 w-72 max-w-full" aria-hidden="true" />
        <div className="skeleton mt-8 h-11 w-full" aria-hidden="true" />
        <div className="skeleton mt-5 h-11 w-full" aria-hidden="true" />
      </div>
    </main>
  );
}
