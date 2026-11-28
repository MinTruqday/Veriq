import Link from "next/link";
import { ArrowRight, SearchCheck, Sparkles } from "lucide-react";
import PublicSiteFooter from "../components/PublicSiteFooter";
import PublicSiteHeader from "../components/PublicSiteHeader";

const capabilities = [
  {
    icon: SearchCheck,
    title: "Liên kết yêu cầu và kiểm thử",
    description: "Theo dõi yêu cầu, tiêu chí chấp nhận, ca kiểm thử và kết quả theo từng phiên bản",
  },
  {
    icon: Sparkles,
    title: "Hỗ trợ xử lý bằng AI",
    description:
      "Người dùng chọn tác vụ cần chạy; kết quả được lưu cùng nguồn dẫn và lịch sử để tiếp tục rà soát",
  },
];

const workflow = [
  "Chuẩn hóa yêu cầu và chọn phiên bản làm căn cứ kiểm thử",
  "Thiết kế kịch bản và ca kiểm thử gắn với yêu cầu nguồn",
  "Theo dõi ca kiểm thử, kết quả chạy, lỗi và nội dung cần rà soát khi yêu cầu thay đổi",
];

export default function HomePage() {
  return (
    <main className="min-h-[100dvh] overflow-x-hidden bg-canvas text-ink">
      <PublicSiteHeader />

      <section className="mx-auto w-full max-w-[1200px] px-5 py-14 md:px-8 md:py-20">
        <div className="max-w-4xl">
          <h1 className="text-balance text-[32px] font-semibold leading-tight tracking-tight sm:text-[42px] lg:text-[48px]">
            Quản lý yêu cầu và kiểm thử
          </h1>
          <p className="mt-4 max-w-3xl text-[15px] leading-7 text-ink-muted">
            Theo dõi Requirement, Test Case, lần chạy, lỗi và bản phát hành trong cùng dự án
          </p>
          <div className="mt-9 flex flex-wrap gap-3">
            <Link href="/dang-nhap" className="apple-button px-6">
              Đăng nhập
              <ArrowRight size={17} />
            </Link>
          </div>
        </div>
      </section>

      <section className="border-y border-border bg-surface">
        <div className="mx-auto w-full max-w-[1200px] px-5 py-16 md:px-8 md:py-20">
          <div className="grid gap-4 md:grid-cols-2">
            {capabilities.map((item) => (
              <article key={item.title} className="rounded-panel border border-border p-5">
                <span className="flex h-10 w-10 items-center justify-center rounded-control bg-brand-soft text-brand">
                  <item.icon size={21} />
                </span>
                <h3 className="mt-5 text-[18px] font-semibold">{item.title}</h3>
                <p className="mt-3 text-[14px] leading-6 text-ink-muted">{item.description}</p>
              </article>
            ))}
          </div>
        </div>
      </section>

      <section className="mx-auto grid w-full max-w-[1200px] gap-8 px-5 py-14 md:px-8 md:py-16 lg:grid-cols-[0.8fr_1.2fr] lg:items-start">
        <div>
          <h2 className="text-[32px] font-semibold leading-tight tracking-[-0.04em]">
            Các bước trong quy trình kiểm thử
          </h2>
        </div>
        <ol className="space-y-3">
          {workflow.map((item, index) => (
            <li
              key={item}
              className="grid grid-cols-[40px_1fr] items-center gap-4 rounded-panel border border-border bg-surface p-4"
            >
              <span className="flex h-10 w-10 items-center justify-center rounded-control bg-brand text-[13px] font-bold text-white">
                {String(index + 1).padStart(2, "0")}
              </span>
              <p className="text-[14px] font-semibold leading-6 md:text-[15px]">{item}</p>
            </li>
          ))}
        </ol>
      </section>

      <PublicSiteFooter />
    </main>
  );
}
