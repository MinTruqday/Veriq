import DataTable from "./DataTable";
import { StatusPill } from "./WorkspacePrimitives";
import { valueLabel } from "../lib/testing";

export default function TestabilityFindingsPanel({ condition, canResolve, onResolve }) {
  return (
    <DataTable
      items={condition.analysis_findings || []}
      empty="Không có phát hiện về khả năng kiểm thử"
      columns={[
        { key: "finding_type", label: "Loại", render: (item) => valueLabel(item.finding_type) },
        {
          key: "severity",
          label: "Mức độ",
          render: (item) => <StatusPill value={item.severity} />,
        },
        { key: "description", label: "Mô tả" },
        { key: "suggestion", label: "Đề xuất" },
        {
          key: "status",
          label: "Trạng thái",
          render: (item) => <StatusPill value={item.status} />,
        },
        ...(canResolve
          ? [
              {
                key: "actions",
                label: "Thao tác",
                render: (item) =>
                  item.status === "OPEN" ? (
                    <button
                      className="secondary-button"
                      type="button"
                      onClick={() => onResolve(item)}
                    >
                      Giải quyết
                    </button>
                  ) : null,
              },
            ]
          : []),
      ]}
    />
  );
}
