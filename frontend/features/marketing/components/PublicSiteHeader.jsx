import Image from "next/image";
import Link from "next/link";

export default function PublicSiteHeader() {
  return (
    <header className="border-b border-border bg-surface">
      <nav aria-label="Điều hướng trang công khai">
        <div className="mx-auto flex h-[64px] w-full max-w-[1200px] items-center justify-between px-5 md:px-8">
          <Link href="/" className="flex items-center gap-3 text-[18px] font-semibold">
            <Image
              src="/brand/veriq-logo.png"
              alt="Veriq"
              width={32}
              height={32}
              className="size-8 rounded-control object-cover"
              priority
              unoptimized
            />
            <span>Veriq</span>
          </Link>
          <Link href="/dang-nhap" className="apple-button">
            Đăng nhập
          </Link>
        </div>
      </nav>
    </header>
  );
}
