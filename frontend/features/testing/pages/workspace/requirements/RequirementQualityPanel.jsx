import DataTable from "../../../components/DataTable";
import { Panel } from "../../../components/WorkspacePrimitives";
import { requirementFieldLabel, requirementSuggestionPreview } from "./requirements.model";
import ContentOriginBadge from "@/shared/components/common/ContentOriginBadge";

export default function RequirementQualityPanel({ lint, loading = false }) {
  if (!lint) {
    return (
      <Panel title="Kết quả kiểm tra AI">
        <p className="px-5 py-4 text-sm text-ink-muted" role="status" aria-live="polite">
          {loading
            ? "Đang tải kết quả đã lưu…"
            : "Chưa kiểm tra phiên bản này. Chọn “Kiểm tra AI” để phân tích nội dung hiện tại."}
        </p>
      </Panel>
    );
  }
  return (
    <Panel
      title={
        lint.degraded_mode
          ? "Kiểm tra AI chưa hoàn tất"
          : lint.valid
            ? "AI không phát hiện lỗi chặn"
            : "AI phát hiện vấn đề"
      }
    >
      {lint.is_stale && (
        <p className="px-5 pt-4 text-sm text-warning" role="status">
          Kết quả này thuộc phiên bản hoặc lần sửa trước. Hãy chạy kiểm tra AI lại nếu nội dung đã
          thay đổi.
        </p>
      )}
      {lint.artifact_revision && (
        <p className="px-5 pt-3 text-sm text-ink-muted">
          Kết quả kiểm tra cho lần cập nhật {lint.artifact_revision}
        </p>
      )}
      <DataTable
        items={lint.findings}
        empty="Không có vấn đề"
        columns={[
          {
            key: "origin",
            label: "Nguồn",
            render: (item) => <ContentOriginBadge origin={item.origin === "AI" ? "ai" : "rule"} />,
          },
          { key: "severity", label: "Mức độ", render: (item) => valueLabel(item.severity) },
          { key: "message", label: "Nội dung" },
          { key: "suggestion", label: "Đề xuất" },
        ]}
      />
      {lint.degraded_mode && (
        <p className="mt-3 text-sm text-warning">
          Mô hình AI chưa sẵn sàng nên kết quả hiện chỉ gồm kiểm tra bằng quy tắc
        </p>
      )}
      <div className="mt-4">
        <DataTable
          items={lint.suggestions || []}
          empty="Chưa có đề xuất chỉnh sửa có đủ căn cứ"
          columns={[
            {
              key: "suggestion",
              label: "Bản vá đề xuất",
              render: (item) => (
                <dl className="space-y-2">
                  {requirementSuggestionPreview(item).map(([label, value]) => (
                    <div key={label}>
                      <dt className="field-label">{label}</dt>
                      <dd className="mt-1 whitespace-pre-wrap text-sm">{value}</dd>
                    </div>
                  ))}
                </dl>
              ),
            },
            {
              key: "target_fields",
              label: "Trường được cập nhật",
              render: (item) =>
                item.target_fields?.map(requirementFieldLabel).filter(Boolean).join(" · ") ||
                "Nội dung",
            },
            { key: "rationale", label: "Cơ sở" },
          ]}
        />
      </div>
    </Panel>
  );
}
