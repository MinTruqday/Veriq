import Link from "next/link";

export default function PublicSiteFooter() {
  return (
    <footer className="border-t border-border bg-surface">
      <div className="mx-auto flex w-full max-w-[1200px] flex-col gap-3 px-5 py-6 text-[13px] text-ink-muted sm:flex-row sm:items-center sm:justify-between md:px-8">
        <span className="font-semibold text-ink">Veriq</span>
        <nav aria-label="Liên kết cuối trang" className="flex gap-5">
          <Link href="/dieu-khoan" className="hover:text-ink">
            Điều khoản
          </Link>
          <Link href="/dang-nhap" className="hover:text-ink">
            Đăng nhập
          </Link>
        </nav>
      </div>
    </footer>
  );
}
