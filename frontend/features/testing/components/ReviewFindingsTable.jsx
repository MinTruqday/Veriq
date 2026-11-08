import { Check, ShieldCheck, UserRound } from "lucide-react";
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
          minWidth: 128,
          render: (item) => <StatusPill value={item.severity} />,
        },
        {
          key: "blocks_acceptance",
          label: "Ảnh hưởng quyết định",
          minWidth: 150,
          render: (item) => (item.blocks_acceptance ? "Chặn chấp thuận" : "Không chặn chấp thuận"),
        },
        { key: "category", label: "Nhóm", render: (item) => valueLabel(item.category) },
        { key: "description", label: "Nội dung", minWidth: 280 },
        {
          key: "status",
          label: "Trạng thái",
          minWidth: 136,
          render: (item) => <StatusPill value={item.status} />,
        },
        {
          key: "action",
          label: "Thao tác",
          hideWhenEmpty: true,
          render: (item) => (
            <div className="flex flex-wrap gap-2">
              {["OPEN", "IN_PROGRESS"].includes(item.status) && canAssign(item) && onAssign && (
                <button
                  className="icon-button h-9 w-9"
                  type="button"
                  aria-label="Gán người phụ trách"
                  title="Gán người phụ trách"
                  onClick={() => onAssign(item)}
                >
                  <UserRound aria-hidden="true" size={16} />
                </button>
              )}
              {["OPEN", "IN_PROGRESS"].includes(item.status) && canResolve(item) && onResolve && (
                <button
                  className="icon-button h-9 w-9"
                  type="button"
                  aria-label="Đánh dấu đã giải quyết"
                  title="Đánh dấu đã giải quyết"
                  onClick={() => onResolve(item)}
                >
                  <Check aria-hidden="true" size={16} />
                </button>
              )}
              {item.status === "RESOLVED" && canVerify(item) && onVerify && (
                <button
                  className="icon-button h-9 w-9"
                  type="button"
                  aria-label="Xác minh kết quả"
                  title="Xác minh kết quả"
                  onClick={() => onVerify(item)}
                >
                  <ShieldCheck aria-hidden="true" size={16} />
                </button>
              )}
            </div>
          ),
        },
      ]}
    />
  );
}
