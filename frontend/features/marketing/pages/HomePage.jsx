import Link from "next/link";
import Image from "next/image";
import { ArrowRight, GitBranch, SearchCheck, Sparkles } from "lucide-react";

const capabilities = [
  {
    icon: SearchCheck,
    title: "Liên kết truy vết",
    description: "Liên kết yêu cầu, tiêu chí chấp nhận, ca kiểm thử và kết quả chạy theo phiên bản",
  },
  {
    icon: GitBranch,
    title: "Phân tích thay đổi",
    description:
      "Xác định các ca kiểm thử và hồ sơ liên quan cần được rà soát khi yêu cầu thay đổi",
  },
  {
    icon: Sparkles,
    title: "Tự động hóa AI",
    description: "Thiết lập quy tắc, sự kiện kích hoạt và mục tiêu AI",
  },
];

const workflow = [
  "Chuẩn hóa và đặt phiên bản yêu cầu làm nguồn chính thức",
  "Thiết kế kịch bản và ca kiểm thử có liên kết truy vết",
  "Theo dõi độ phủ, lần chạy, lỗi và ảnh hưởng thay đổi",
];

export default function HomePage() {
  return (
    <main className="min-h-[100dvh] overflow-x-hidden bg-[#eef3ef] text-ink">
      <nav
        className="border-b border-brand/10 bg-white/80 backdrop-blur-md"
        aria-label="Điều hướng trang chủ"
      >
        <div className="mx-auto flex h-[72px] w-full max-w-[1200px] items-center justify-between px-5 md:px-8">
          <Link
            href="/"
            className="flex items-center gap-3 text-[19px] font-semibold tracking-[-0.035em]"
          >
            <Image
              src="/brand/veriq-logo.png"
              alt="Veriq"
              width={36}
              height={36}
              className="h-9 w-9 rounded-xl object-cover"
              priority
            />
            <span>Veriq</span>
          </Link>
          <div className="flex items-center gap-2">
            <Link
              href="/dang-nhap"
              className="hidden rounded-control px-4 py-2 text-[14px] font-semibold text-ink-muted transition hover:bg-surface hover:text-ink sm:inline-flex"
            >
              Đăng nhập
            </Link>
            <Link href="/dang-ky" className="apple-button">
              Tạo tài khoản
              <ArrowRight size={16} />
            </Link>
          </div>
        </div>
      </nav>

      <section className="mx-auto w-full max-w-[1200px] px-5 py-16 md:px-8 md:py-24">
        <div>
          <h1 className="max-w-none text-balance text-[44px] font-semibold leading-[1.02] tracking-[-0.055em] sm:text-[58px] lg:text-[66px]">
            Quản lý yêu cầu và kiểm thử
          </h1>
          <div className="mt-9 flex flex-wrap gap-3">
            <Link href="/dang-ky" className="apple-button px-6">
              Tạo tài khoản
              <ArrowRight size={17} />
            </Link>
            <Link href="/dang-nhap" className="secondary-button px-6">
              Đăng nhập
            </Link>
          </div>
        </div>
      </section>

      <section className="border-y border-brand/10 bg-white/70">
        <div className="mx-auto w-full max-w-[1200px] px-5 py-16 md:px-8 md:py-20">
          <div className="max-w-2xl">
            <h2 className="text-[32px] font-semibold leading-tight tracking-[-0.04em] md:text-[42px]">
              Chức năng
            </h2>
          </div>
          <div className="mt-10 grid gap-4 md:grid-cols-3">
            {capabilities.map((item) => (
              <article
                key={item.title}
                className="rounded-2xl border border-border bg-surface p-6 shadow-[0_10px_30px_rgba(48,47,42,0.04)]"
              >
                <span className="flex h-11 w-11 items-center justify-center rounded-xl bg-brand-soft text-brand">
                  <item.icon size={21} />
                </span>
                <h3 className="mt-5 text-[18px] font-semibold">{item.title}</h3>
                <p className="mt-3 text-[14px] leading-6 text-ink-muted">{item.description}</p>
              </article>
            ))}
          </div>
        </div>
      </section>

      <section className="mx-auto grid w-full max-w-[1200px] gap-10 px-5 py-16 md:px-8 md:py-20 lg:grid-cols-[0.8fr_1.2fr] lg:items-start">
        <div>
          <h2 className="text-[32px] font-semibold leading-tight tracking-[-0.04em]">Quy trình</h2>
        </div>
        <ol className="space-y-3">
          {workflow.map((item, index) => (
            <li
              key={item}
              className="grid grid-cols-[44px_1fr] items-center gap-4 rounded-2xl border border-border bg-white/70 p-4 md:p-5"
            >
              <span className="flex h-11 w-11 items-center justify-center rounded-xl bg-brand text-[13px] font-bold text-white">
                {String(index + 1).padStart(2, "0")}
              </span>
              <p className="text-[14px] font-semibold leading-6 md:text-[15px]">{item}</p>
            </li>
          ))}
        </ol>
      </section>

      <footer className="border-t border-brand/10 bg-white/60">
        <div className="mx-auto flex w-full max-w-[1200px] flex-col gap-3 px-5 py-8 text-[13px] text-ink-muted sm:flex-row sm:items-center sm:justify-between md:px-8">
          <span className="font-semibold text-ink">Veriq</span>
          <div className="flex gap-5">
            <Link href="/dieu-khoan" className="hover:text-ink">
              Điều khoản
            </Link>
            <Link href="/dang-nhap" className="hover:text-ink">
              Đăng nhập
            </Link>
          </div>
        </div>
      </footer>
    </main>
  );
}
