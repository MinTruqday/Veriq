import PageHeader from "@/shared/components/layout/PageHeader";
const sections = [
  {
    id: "su-dung",
    title: "Sử dụng dịch vụ",
    paragraphs: [
      "Khi tạo tài khoản hoặc sử dụng Veriq, bạn đồng ý cung cấp thông tin chính xác và chịu trách nhiệm với hoạt động phát sinh từ tài khoản của mình.",
      "Bạn không được dùng dịch vụ để phát tán nội dung trái pháp luật, xâm phạm quyền của người khác hoặc can thiệp vào hoạt động của hệ thống.",
    ],
  },
  {
    id: "noi-dung",
    title: "Nội dung và bản quyền",
    paragraphs: [
      "Tác giả giữ quyền đối với nội dung do mình đăng tải và chịu trách nhiệm về quyền sử dụng các tài liệu nguồn.",
      "Người đọc cần tôn trọng quyền tác giả và không phân phối lại nội dung khi chưa có chấp thuận.",
    ],
  },
  {
    id: "du-lieu",
    title: "Dữ liệu cá nhân",
    paragraphs: [
      "Veriq xử lý thông tin tài khoản để xác thực, quản lý phiên đăng nhập và vận hành các chức năng của dịch vụ. Dữ liệu dự án được truy cập theo quyền được cấp cho tài khoản.",
    ],
  },
  {
    id: "thay-doi",
    title: "Thay đổi điều khoản",
    paragraphs: [
      "Phiên bản mới có hiệu lực từ ngày được ghi ở đầu trang và thay thế phiên bản trước đó.",
      "Nếu thay đổi ảnh hưởng đáng kể đến quyền của người dùng Veriq, chúng tôi sẽ thông báo qua tài khoản trước khi áp dụng.",
    ],
  },
];
export default function TermsPage() {
  return (
    <div className="mx-auto w-full max-w-[1480px] min-w-0">
      <PageHeader title="Điều khoản" meta="Hiệu lực từ ngày 28 tháng 4 năm 2026" />

      <div className="grid gap-8 lg:grid-cols-[220px_minmax(0,720px)] lg:items-start">
        <nav
          className="border-y border-border py-2 lg:sticky lg:top-[84px]"
          aria-label="Nội dung điều khoản"
        >
          {sections.map((section, index) => (
            <a
              key={section.id}
              href={`#${section.id}`}
              className="grid grid-cols-[24px_1fr] gap-2 border-b border-border py-3 text-[13px] text-ink-muted last:border-b-0 hover:text-ink"
            >
              <span className="text-ink-faint">{index + 1}</span>
              <span className="font-semibold">{section.title}</span>
            </a>
          ))}
        </nav>

        <article className="divide-y divide-border border-t border-border">
          {sections.map((section, index) => (
            <section key={section.id} id={section.id} className="scroll-mt-24 py-7 first:pt-6">
              <div className="grid gap-5 sm:grid-cols-[32px_1fr]">
                <span className="text-[13px] font-semibold text-ink-faint">
                  {String(index + 1).padStart(2, "0")}
                </span>
                <div>
                  <h2 className="text-[17px] font-semibold text-ink">{section.title}</h2>
                  <div className="mt-4 space-y-4">
                    {section.paragraphs.map((paragraph) => (
                      <p key={paragraph} className="text-[15px] leading-7 text-ink-muted">
                        {paragraph}
                      </p>
                    ))}
                  </div>
                </div>
              </div>
            </section>
          ))}
        </article>
      </div>
    </div>
  );
}
