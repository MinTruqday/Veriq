import DataTable from "./DataTable";
import QualityGateBadge from "./QualityGateBadge";
import { StructuredValueView } from "./StructuredValueEditor";

export default function ExitCriteriaPanel({ snapshot, canOverride, onOverride }) {
  const items =
    snapshot?.effective_exit_criteria_evaluation || snapshot?.exit_criteria_evaluation || [];
  return (
    <div className="space-y-4">
      <div className="flex items-center justify-between px-5 pt-5">
        <span className="field-label">Cổng chất lượng</span>
        <QualityGateBadge
          status={snapshot?.effective_quality_gate_status || snapshot?.quality_gate_status}
        />
      </div>
      <DataTable
        items={items}
        empty="Kế hoạch chưa cấu hình mục tiêu chất lượng"
        columns={[
          { key: "criterion", label: "Tiêu chí" },
          {
            key: "threshold",
            label: "Ngưỡng",
            render: (item) =>
              Array.isArray(item.threshold) ? item.threshold.join(" · ") : String(item.threshold),
          },
          {
            key: "actual",
            label: "Thực tế",
            render: (item) => <StructuredValueView value={item.actual ?? "Cần đánh giá"} />,
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
