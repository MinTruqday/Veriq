import DataTable from "./DataTable";
import { StatusPill } from "./WorkspacePrimitives";
import { valueLabel } from "../lib/testing";

export default function ReviewFindingsTable({
  findings = [],
  canAssign,
  canResolve,
  canVerify,
  onAssign,
  onResolve,
  onVerify,
}) {
  return (
    <DataTable
      items={findings}
      empty="Chưa có phát hiện"
      columns={[
        {
          key: "severity",
          label: "Mức độ",
          render: (item) => <StatusPill value={item.severity} />,
        },
        { key: "category", label: "Nhóm", render: (item) => valueLabel(item.category) },
        { key: "description", label: "Nội dung" },
        {
          key: "status",
          label: "Trạng thái",
          render: (item) => <StatusPill value={item.status} />,
        },
        {
          key: "action",
          label: "Thao tác",
          hideWhenEmpty: true,
          render: (item) => (
            <div className="flex flex-wrap gap-2">
              {["OPEN", "IN_PROGRESS"].includes(item.status) && canAssign(item) && onAssign && (
                <button className="secondary-button" type="button" onClick={() => onAssign(item)}>
                  Gán
                </button>
              )}
              {["OPEN", "IN_PROGRESS"].includes(item.status) && canResolve(item) && onResolve && (
                <button className="secondary-button" type="button" onClick={() => onResolve(item)}>
                  Giải quyết
                </button>
              )}
              {item.status === "RESOLVED" && canVerify(item) && onVerify && (
                <button className="secondary-button" type="button" onClick={() => onVerify(item)}>
                  Xác minh
                </button>
              )}
            </div>
          ),
        },
      ]}
    />
  );
}
