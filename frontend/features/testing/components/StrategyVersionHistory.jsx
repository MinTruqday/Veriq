import DataTable from "./DataTable";
import { StatusPill } from "./WorkspacePrimitives";

export default function StrategyVersionHistory({ items, lineageId, onSelect }) {
  const versions = items.filter((item) => item.lineage_id === lineageId);
  return (
    <DataTable
      items={versions}
      empty="Chưa có lịch sử phiên bản"
      columns={[
        { key: "version", label: "Phiên bản" },
        {
          key: "status",
          label: "Trạng thái",
          render: (item) => <StatusPill value={item.status} />,
        },
        {
          key: "updated_at",
          label: "Cập nhật",
          render: (item) => new Date(item.updated_at).toLocaleString("vi-VN"),
        },
        {
          key: "actions",
          label: "Thao tác",
          render: (item) => (
            <button className="secondary-button" type="button" onClick={() => onSelect(item)}>
              Mở
            </button>
          ),
        },
      ]}
    />
  );
}
