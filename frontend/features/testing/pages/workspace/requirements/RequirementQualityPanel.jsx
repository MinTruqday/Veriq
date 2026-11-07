import DataTable from "../../../components/DataTable";
import { Panel } from "../../../components/WorkspacePrimitives";
import { valueLabel } from "../../../lib/testing";
import { requirementFieldLabel, requirementSuggestionPreview } from "./requirements.model";

function severityLabel(severity) {
  return (
    {
      error: "Lỗi",
      info: "Thông tin",
      warning: "Cảnh báo",
    }[String(severity || "").toLowerCase()] || valueLabel(severity)
  );
}

export default function RequirementQualityPanel({ lint, loading = false, onOpenClarifications }) {
  if (!lint) {
    return (
      <Panel title="Gợi ý hoàn thiện Requirement">
        <p className="px-5 py-4 text-sm text-ink-muted" role="status" aria-live="polite">
          {loading
            ? "Đang tải kết quả đã lưu…"
            : "Chưa kiểm tra phiên bản này. Chọn “Kiểm tra AI” để phân tích nội dung hiện tại."}
        </p>
      </Panel>
    );
  }
  const systemFindings = (lint.findings || []).filter((item) => item.origin !== "AI");
  const recommendations = [
    ...(lint.recommendations || []),
    ...(lint.findings || [])
      .filter((item) => item.origin === "AI")
      .map((item, index) => ({
        ...item,
        recommendation_id: item.recommendation_id || `legacy-${index}`,
      })),
  ];
  return (
    <Panel title="Gợi ý hoàn thiện Requirement">
      {lint.is_stale && (
        <p className="px-5 pt-4 text-sm text-warning" role="status">
          Kết quả này thuộc phiên bản hoặc lần sửa trước. Hãy chạy kiểm tra AI lại nếu nội dung đã
          thay đổi.
        </p>
      )}
      <div className="mx-5 mt-4 flex flex-wrap items-center justify-between gap-3 rounded-control border border-border bg-surface-quiet px-3 py-2">
        <p className="text-sm text-ink-muted">
          AI chỉ đưa ra nhận xét và đề xuất bổ sung; không tự sửa, không đánh dấu Requirement là lỗi
          và không gửi rà soát. Việc chấp nhận do người có quyền thực hiện.
        </p>
      </div>
      {lint.artifact_revision && (
        <p className="px-5 pt-3 text-sm text-ink-muted">
          Kết quả kiểm tra cho lần cập nhật {lint.artifact_revision}
        </p>
      )}
      {systemFindings.length > 0 && (
        <div className="mt-4">
          <div className="flex flex-wrap items-center justify-between gap-3 px-5 pb-3">
            <div>
              <h3 className="text-sm font-semibold text-ink">Kiểm tra điều kiện dữ liệu</h3>
              <p className="mt-1 text-sm text-ink-muted">
                Các điều kiện bắt buộc được hệ thống kiểm tra riêng khi gửi rà soát hoặc chấp nhận.
              </p>
            </div>
            {onOpenClarifications && (
              <button
                className="secondary-button shrink-0"
                type="button"
                onClick={onOpenClarifications}
              >
                Mở Phiếu làm rõ
              </button>
            )}
          </div>
          <DataTable
            items={systemFindings}
            columns={[
              { key: "severity", label: "Mức độ", render: (item) => severityLabel(item.severity) },
              { key: "message", label: "Điều kiện" },
              { key: "suggestion", label: "Cách hoàn thiện" },
            ]}
          />
        </div>
      )}
      {recommendations.length > 0 && (
        <div className="mt-4">
          <h3 className="px-5 pb-2 text-sm font-semibold text-ink">Nhận xét tham khảo từ AI</h3>
          <DataTable
            items={recommendations}
            columns={[
              { key: "message", label: "Nhận xét" },
              { key: "suggestion", label: "Đề xuất bổ sung" },
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
                        </li>
                      ))}
                    </ul>
                  ) : (
                    (item.evidence_refs || []).join(", ") || "Không có dẫn chứng nguồn"
                  ),
              },
            ]}
          />
        </div>
      )}
      {!systemFindings.length && !recommendations.length && !lint.suggestions?.length && (
        <p className="px-5 py-3 text-sm text-ink-muted" role="status">
          Chưa có đề xuất bổ sung cho phiên bản này.
        </p>
      )}
      {lint.degraded_mode && (
        <p className="mt-3 text-sm text-warning">
          Mô hình AI chưa sẵn sàng; hiện chỉ có các điều kiện dữ liệu được hệ thống kiểm tra.
        </p>
      )}
      {lint.suggestions?.length > 0 && (
        <div className="mt-4">
          <DataTable
            items={lint.suggestions}
            columns={[
              {
                key: "suggestion",
                label: "Đề xuất bổ sung",
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
