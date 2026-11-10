import DataTable from "./DataTable";
import { LoadingState, Panel } from "./WorkspacePrimitives";
import { valueLabel } from "../lib/testing";

function countRows(values, prefix) {
  return Object.entries(values || {}).map(([name, count]) => ({
    _id: `${prefix}-${name}`,
    name: valueLabel(name),
    count,
  }));
}

function rate(value) {
  if (typeof value !== "number") return "Chưa đủ dữ liệu";
  return `${(value * 100).toFixed(1)}%`;
}

function duration(value) {
  if (typeof value !== "number") return "Chưa đủ dữ liệu";
  return value < 1000 ? `${Math.round(value)} ms` : `${(value / 1000).toFixed(1)} giây`;
}

function Metric({ label, value, detail }) {
  return (
    <div className="rounded-xl border border-border-strong bg-surface-raised p-4 shadow-sm">
      <p className="text-xs font-medium leading-5 text-ink-muted">{label}</p>
      <p className="mt-2 text-2xl font-semibold tracking-tight text-ink">{value}</p>
      {detail && <p className="mt-1 text-xs leading-5 text-ink-faint">{detail}</p>}
    </div>
  );
}

export default function ProjectAIEvaluationPanel({ analytics, loading }) {
  if (loading && !analytics) return <LoadingState />;

  const requests = analytics?.ai_request_metrics || {};
  const results = analytics?.ai_result_metrics || {};
  const feedback = analytics?.ai_test_case_feedback || {};
  const adequacy = analytics?.ai_test_adequacy_feedback || {};
  const proposalDecisions = analytics?.decision_feedback?.decision_counts || {};
  const generatedCount = Number(feedback.generated_draft_count || 0);
  const evidenceRate = results.record_count
    ? Number(results.grounded_record_count || 0) / Number(results.record_count)
    : null;

  return (
    <div className="space-y-5">
      <Panel title="Đánh giá AI từ dữ liệu sử dụng thật">
        <div className="space-y-3 p-4 text-sm leading-6 text-ink-muted">
          <p>
            Số liệu được tổng hợp từ yêu cầu AI, kết quả đã lưu và quyết định rà soát trong dự án
            này. Không dùng bộ câu hỏi mẫu cố định và không tự tạo đáp án chuẩn.
          </p>
          <p>
            Đây là đánh giá vận hành: mức độ sử dụng, tỷ lệ đề xuất được nhận hoặc chỉnh sửa, bằng
            chứng nguồn, lỗi và độ trễ. Các số liệu này không thay thế phép đánh giá độ chính xác có
            nhãn độc lập.
          </p>
          {requests.sample_truncated ||
          results.sample_truncated ||
          feedback.generated_draft_sample_truncated ? (
            <p className="text-warning">
              Một số thống kê bị giới hạn ở 10.000 bản ghi gần nhất; các thẻ bên dưới dùng đúng mẫu
              dữ liệu mà hệ thống báo cáo.
            </p>
          ) : null}
        </div>
      </Panel>

      <Panel title="Khả năng phát hiện lỗi trong dữ liệu dự án">
        <div className="space-y-3 p-4 text-sm leading-6 text-ink-muted">
          <p>
            Chỉ tính phản hồi thuộc hồ sơ độ đầy đủ đã được duyệt, gắn với phiên bản ca AI, kết quả
            chạy và lỗi đã ghi nhận. Đây là số liệu quan sát trong dự án, chưa phải phép thử có lỗi
            cài sẵn và không dùng để kết luận phương pháp AI nào tốt hơn.
          </p>
          {adequacy.approved_assessment_sample_truncated && (
            <p className="text-warning">Số liệu chỉ bao gồm 10.000 hồ sơ đã duyệt gần nhất.</p>
          )}
        </div>
        <dl className="grid gap-3 p-4 pt-0 sm:grid-cols-2 xl:grid-cols-5">
          <Metric
            label="Ca AI có kết quả và lỗi liên kết"
            value={adequacy.linked_ai_case_count ?? 0}
          />
          <Metric label="Lượt phát hiện lỗi" value={adequacy.outcome_counts?.CAUGHT_DEFECT ?? 0} />
          <Metric
            label="Lượt không phát hiện lỗi"
            value={adequacy.outcome_counts?.DID_NOT_DIFFERENTIATE ?? 0}
          />
          <Metric
            label="Tỷ lệ phát hiện quan sát được"
            value={rate(adequacy.observed_detection_rate)}
            detail={`${adequacy.outcome_count_with_run_and_defect_evidence ?? 0} lượt có đủ bằng chứng`}
          />
          <Metric
            label="Ghi nhận thiếu bằng chứng"
            value={adequacy.incomplete_evidence_count ?? 0}
          />
        </dl>
      </Panel>

      <Panel title="Hoạt động và độ tin cậy">
        <dl className="grid gap-3 p-4 sm:grid-cols-2 xl:grid-cols-4">
          <Metric label="Lượt gọi AI" value={requests.request_count ?? 0} />
          <Metric
            label="Lượt cần xem lại hoặc bị suy giảm"
            value={requests.degraded_count ?? 0}
            detail={rate(
              requests.request_count ? requests.degraded_count / requests.request_count : null,
            )}
          />
          <Metric label="Kết quả AI đã lưu" value={results.record_count ?? 0} />
          <Metric
            label="Kết quả có dẫn chứng nguồn"
            value={results.grounded_record_count ?? 0}
            detail={rate(evidenceRate)}
          />
          <Metric label="Độ trễ p50" value={duration(requests.p50_latency_ms)} />
          <Metric label="Độ trễ p95" value={duration(requests.p95_latency_ms)} />
          <Metric label="Bản nháp ca kiểm thử do AI tạo" value={generatedCount} />
          <Metric
            label="Phiên bản ca kiểm thử AI có phản hồi duyệt"
            value={Object.values(feedback.approved_decision_counts || {}).reduce(
              (total, count) => total + Number(count || 0),
              0,
            )}
          />
        </dl>
      </Panel>

      <div className="grid gap-5 xl:grid-cols-2">
        <Panel title="Lượt gọi theo chức năng">
          <DataTable
            items={countRows(requests.by_capability, "request")}
            empty="Dự án chưa có lượt gọi AI được ghi nhận"
            columns={[
              { key: "name", label: "Chức năng" },
              { key: "count", label: "Số lượt" },
            ]}
          />
        </Panel>
        <Panel title="Trạng thái xử lý">
          <DataTable
            items={countRows(requests.by_status, "status")}
            empty="Chưa có trạng thái xử lý được ghi nhận"
            columns={[
              { key: "name", label: "Trạng thái" },
              { key: "count", label: "Số lượt" },
            ]}
          />
        </Panel>
        <Panel title="Rà soát ca kiểm thử do AI tạo">
          <DataTable
            items={countRows(feedback.approved_decision_counts, "test-case-review")}
            empty="Chưa có ca kiểm thử AI được rà soát"
            columns={[
              { key: "name", label: "Quyết định" },
              { key: "count", label: "Số ca" },
            ]}
          />
          {feedback.changes_requested_count > 0 && (
            <p className="px-4 pb-4 text-xs text-ink-muted">
              Số ca bị yêu cầu chỉnh sửa: {feedback.changes_requested_count}
            </p>
          )}
        </Panel>
        <Panel title="Quyết định với đề xuất bảo trì">
          <DataTable
            items={countRows(proposalDecisions, "proposal-review")}
            empty="Chưa có đề xuất bảo trì được rà soát"
            columns={[
              { key: "name", label: "Quyết định" },
              { key: "count", label: "Số đề xuất" },
            ]}
          />
          <p className="px-4 pb-4 text-xs text-ink-muted">
            Tỷ lệ được nhận hoặc chỉnh sửa: {rate(analytics?.proposal_acceptance_rate)}
          </p>
        </Panel>
      </div>
    </div>
  );
}
