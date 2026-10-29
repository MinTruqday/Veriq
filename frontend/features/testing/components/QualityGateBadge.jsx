import { StatusPill } from "./WorkspacePrimitives";

const QUALITY_GATE_LABELS = {
  INSUFFICIENT_DATA: "Chưa đủ dữ liệu",
  MANUAL_REQUIRED: "Cần đánh giá thủ công",
  NOT_CONFIGURED: "Chưa cấu hình",
  WARN: "Cảnh báo",
};

export default function QualityGateBadge({ status }) {
  if (QUALITY_GATE_LABELS[status]) {
    return (
      <span className="inline-flex max-w-full rounded-full bg-brand-soft px-2.5 py-1 text-[11px] font-semibold text-brand">
        {QUALITY_GATE_LABELS[status]}
      </span>
    );
  }
  return <StatusPill value={status || "NOT_CONFIGURED"} />;
}
