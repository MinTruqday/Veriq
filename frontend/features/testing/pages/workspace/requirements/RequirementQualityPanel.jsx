import DataTable from "../../../components/DataTable";
import { Panel } from "../../../components/WorkspacePrimitives";
import { valueLabel } from "../../../lib/testing";
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
      <p className="mx-5 mt-4 rounded-control border border-border bg-surface-quiet px-3 py-2 text-sm text-ink-muted">
        Kết quả này là gợi ý để BA chỉnh bản nháp trong biểu mẫu yêu cầu; AI không tự sửa hoặc gửi
        duyệt. Nếu cần người khác xác nhận nghiệp vụ còn thiếu, mở tab “Phiếu làm rõ” để tạo câu
        hỏi. Sau khi nội dung đã cập nhật, lưu bản nháp rồi gửi QA rà soát.
      </p>
      {lint.artifact_revision && (
        <p className="px-5 pt-3 text-sm text-ink-muted">
          Kết quả kiểm tra cho lần cập nhật {lint.artifact_revision}
        </p>
      )}
      {lint.findings?.length > 0 ? (
        <DataTable
          items={lint.findings}
          columns={[
            {
              key: "origin",
              label: "Nguồn",
              render: (item) => (
                <ContentOriginBadge origin={item.origin === "AI" ? "ai" : "rule"} />
              ),
            },
            { key: "severity", label: "Mức độ", render: (item) => valueLabel(item.severity) },
            { key: "message", label: "Nội dung" },
            { key: "suggestion", label: "Đề xuất" },
            {
              key: "evidence_quotes",
              label: "Dẫn chứng",
              render: (item) =>
                item.evidence_quotes?.length ? (
                  <ul className="space-y-2">
                    {item.evidence_quotes.map((quote, index) => (
                      <li key={`${quote.evidence_ref}-${index}`}>
                        <blockquote className="whitespace-pre-wrap border-l-2 border-line pl-2 text-sm text-ink">
                          {quote.quote}
                        </blockquote>
                        <span className="mt-1 block text-xs text-ink-muted">
                          Phiên bản nguồn: {quote.evidence_ref}
                        </span>
                      </li>
                    ))}
                  </ul>
                ) : (
                  (item.evidence_refs || []).join(", ") || "Không có dẫn chứng nguồn"
                ),
            },
          ]}
        />
      ) : (
        <p className="px-5 py-3 text-sm text-ink-muted" role="status">
          Không có vấn đề cần xử lý.
        </p>
      )}
      {lint.degraded_mode && (
        <p className="mt-3 text-sm text-warning">
          Mô hình AI chưa sẵn sàng nên kết quả hiện chỉ gồm kiểm tra bằng quy tắc
        </p>
      )}
      {lint.suggestions?.length > 0 && (
        <div className="mt-4">
          <DataTable
            items={lint.suggestions}
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
      )}
    </Panel>
  );
}
