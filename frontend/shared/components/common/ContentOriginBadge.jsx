import { Sparkles, UserRound } from "lucide-react";

const AI_ORIGINS = new Set([
  "ai",
  "ai_generated",
  "ai_suggested",
  "ai_candidate_confirmed",
  "maintenance",
]);
const HUMAN_ORIGINS = new Set(["manual", "human", "user"]);

export default function ContentOriginBadge({ origin, aiLabel, humanLabel = "Người dùng tạo" }) {
  const value = String(origin || "")
    .trim()
    .toLowerCase();
  if (AI_ORIGINS.has(value)) {
    const label =
      aiLabel ||
      (value === "ai_candidate_confirmed"
        ? "AI đề xuất · người dùng đã chọn"
        : value === "maintenance"
          ? "AI bảo trì"
          : value === "ai_generated"
            ? "AI tạo"
            : "AI đề xuất");
    return (
      <span
        aria-label="Nội dung do AI tạo hoặc đề xuất"
        className="inline-flex items-center gap-1 rounded-full border border-violet-300 bg-violet-50 px-2.5 py-1 text-xs font-medium text-violet-900"
        data-content-origin="ai"
      >
        <Sparkles aria-hidden="true" className="h-3.5 w-3.5" />
        {label}
      </span>
    );
  }
  if (HUMAN_ORIGINS.has(value)) {
    return (
      <span
        aria-label="Nội dung do người dùng tạo"
        className="inline-flex items-center gap-1 rounded-full border border-border bg-surface-quiet px-2.5 py-1 text-xs font-medium text-ink-muted"
        data-content-origin="human"
      >
        <UserRound aria-hidden="true" className="h-3.5 w-3.5" />
        {humanLabel}
      </span>
    );
  }
  if (value === "import") {
    return (
      <span
        aria-label="Nội dung được nhập từ tài liệu"
        className="inline-flex items-center gap-1 rounded-full border border-border bg-surface-quiet px-2.5 py-1 text-xs font-medium text-ink-muted"
        data-content-origin="import"
      >
        Tài liệu nhập
      </span>
    );
  }
  if (value === "clone") {
    return (
      <span
        aria-label="Nội dung được sao chép từ một ca kiểm thử khác"
        className="inline-flex items-center gap-1 rounded-full border border-border bg-surface-quiet px-2.5 py-1 text-xs font-medium text-ink-muted"
        data-content-origin="clone"
      >
        Bản sao
      </span>
    );
  }
  if (value === "rule") {
    return (
      <span
        aria-label="Kết quả từ kiểm tra theo quy tắc"
        className="inline-flex items-center rounded-full border border-border bg-surface-quiet px-2.5 py-1 text-xs font-medium text-ink-muted"
        data-content-origin="rule"
      >
        Quy tắc tự động
      </span>
    );
  }
  return null;
}
