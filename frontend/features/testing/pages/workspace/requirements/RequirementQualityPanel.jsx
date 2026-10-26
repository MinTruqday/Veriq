import DataTable from "../../../components/DataTable";
import { Panel } from "../../../components/WorkspacePrimitives";
import { requirementFieldLabel, requirementSuggestionPreview } from "./requirements.model";

export default function RequirementQualityPanel({ lint }) {
  if (!lint) return null;
  return (
    <Panel
      title={
        lint.degraded_mode
          ? "Chưa thể hoàn tất đánh giá tự động"
          : lint.valid
            ? "Đánh giá tự động không phát hiện lỗi chặn"
            : "Đánh giá tự động phát hiện vấn đề"
      }
    >
      {lint.is_stale && (
        <p className="px-5 pt-4 text-sm text-warning" role="status">
          Kết quả này thuộc phiên bản hoặc lần sửa trước; đang chờ phân tích tự động cho revision
          hiện tại.
        </p>
      )}
      {lint.artifact_revision && (
        <p className="px-5 pt-3 text-sm text-ink-muted">
          Kết quả tự động cho revision {lint.artifact_revision}
        </p>
      )}
      <DataTable
        items={lint.findings}
        empty="Không có vấn đề"
        columns={[
          {
            key: "origin",
            label: "Nguồn",
            render: (item) => (item.origin === "AI" ? "AI" : "Quy tắc"),
          },
          { key: "severity", label: "Mức độ" },
          { key: "rule_id", label: "Mã" },
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
