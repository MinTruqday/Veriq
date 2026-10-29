import DataTable from "./DataTable";
import QualityGateBadge from "./QualityGateBadge";
import { StructuredValueView } from "./StructuredValueEditor";

const criterionLabels = {
  EXECUTION_PERCENT_MIN: "Tỷ lệ kiểm thử đã chạy tối thiểu",
  PASS_RATE_MIN: "Tỷ lệ kiểm thử đạt tối thiểu",
  OPEN_BLOCKER_MAX: "Số lỗi chặn phát hành tối đa",
  OPEN_CRITICAL_MAX: "Số lỗi nghiêm trọng đang mở tối đa",
  REQUIREMENT_COVERAGE_MIN: "Độ phủ yêu cầu tối thiểu",
  AC_COVERAGE_MIN: "Độ phủ tiêu chí chấp nhận tối thiểu",
  CONDITION_COVERAGE_MIN: "Độ phủ điều kiện kiểm thử tối thiểu",
  STALE_TESTCASE_MAX: "Số ca kiểm thử lỗi thời tối đa",
  ENVIRONMENT_INCIDENT_MAX: "Số sự cố môi trường đang mở tối đa",
  REQUIRED_RUNS_COMPLETED: "Số lượt chạy bắt buộc hoàn tất",
  CUSTOM_MANUAL_GATE: "Tiêu chí cần đánh giá thủ công",
};

const percentageCriteria = new Set([
  "EXECUTION_PERCENT_MIN",
  "PASS_RATE_MIN",
  "REQUIREMENT_COVERAGE_MIN",
  "AC_COVERAGE_MIN",
  "CONDITION_COVERAGE_MIN",
]);

function criterionName(item) {
  if (item.criterion && item.criterion !== item.type) return item.criterion;
  return criterionLabels[item.type] || item.criterion || "Tiêu chí tùy chỉnh";
}

function thresholdValue(item) {
  if (item.type === "REQUIRED_RUNS_COMPLETED" && Array.isArray(item.threshold)) {
    return `${item.threshold.length} lượt chạy`;
  }
  if (
    percentageCriteria.has(item.type) &&
    item.threshold !== null &&
    item.threshold !== undefined &&
    item.threshold !== "" &&
    Number.isFinite(Number(item.threshold))
  ) {
    const threshold = Number(item.threshold);
    return `${threshold >= 0 && threshold <= 1 ? threshold * 100 : threshold}%`;
  }
  return Array.isArray(item.threshold) ? item.threshold.join(" · ") : String(item.threshold);
}

function actualValue(item) {
  if (item.type === "REQUIRED_RUNS_COMPLETED" && item.actual && typeof item.actual === "object") {
    const completed = item.actual.completed?.length || 0;
    const missing = item.actual.missing?.length || 0;
    return `${completed} lượt hoàn tất${missing ? ` · ${missing} lượt còn thiếu` : ""}`;
  }
  return <StructuredValueView value={item.actual ?? "Cần đánh giá"} />;
}

export default function ExitCriteriaPanel({ snapshot, canOverride, onOverride }) {
  const items =
    snapshot?.effective_exit_criteria_evaluation || snapshot?.exit_criteria_evaluation || [];
  return (
    <div className="space-y-4">
      <div className="flex flex-wrap items-center justify-between gap-3 px-5 pt-5">
        <span className="field-label">Trạng thái điều kiện phát hành</span>
        <QualityGateBadge
          status={snapshot?.effective_quality_gate_status || snapshot?.quality_gate_status}
        />
      </div>
      <DataTable
        items={items}
        empty="Kế hoạch chưa cấu hình mục tiêu chất lượng"
        columns={[
          { key: "criterion", label: "Tiêu chí", minWidth: 260, render: criterionName },
          {
            key: "threshold",
            label: "Ngưỡng",
            render: thresholdValue,
          },
          {
            key: "actual",
            label: "Thực tế",
            render: actualValue,
          },
          {
            key: "status",
            label: "Kết quả",
            render: (item) => <QualityGateBadge status={item.status} />,
          },
          ...(canOverride
            ? [
                {
                  key: "actions",
                  label: "Thao tác",
                  render: (item) => (
                    <button
                      className="secondary-button"
                      type="button"
                      onClick={() => onOverride(item)}
                    >
                      Ghi đè có lý do
                    </button>
                  ),
                },
              ]
            : []),
        ]}
      />
    </div>
  );
}
