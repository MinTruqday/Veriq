import Link from "next/link";

export default function NotFound() {
  return (
    <main className="flex min-h-[100dvh] items-center justify-center bg-canvas px-6 py-12 text-ink">
      <section className="w-full max-w-lg rounded-panel border border-border bg-surface p-8 shadow-[0_18px_50px_rgba(48,47,42,0.08)]">
        <p className="text-sm font-semibold text-brand">Không tìm thấy trang</p>
        <h1 className="mt-3 text-3xl font-semibold tracking-[-0.03em]">
          Đường dẫn này không còn khả dụng
        </h1>
        <p className="mt-3 text-sm leading-6 text-ink-muted">
          Kiểm tra lại địa chỉ hoặc quay về danh sách dự án để tiếp tục.
        </p>
        <Link className="apple-button mt-6 inline-flex items-center justify-center" href="/du-an">
          Mở danh sách dự án
        </Link>
      </section>
    </main>
  );
}
