import DataTable from "./DataTable";
import { StatusPill } from "./WorkspacePrimitives";
import { formatDate, valueLabel } from "../lib/testing";

export default function TestControlActionPanel({
  items,
  members = [],
  typeLabel = (item) => valueLabel(item.type),
  canCreate,
  canUpdate,
  onCreate,
  onUpdate,
}) {
  return (
    <div className="space-y-4">
      {canCreate && (
        <div className="flex justify-end px-5 pt-5">
          <button className="apple-button" type="button" onClick={onCreate}>
            Tạo hành động kiểm soát
          </button>
        </div>
      )}
      <DataTable
        items={items}
        empty="Chưa có hành động kiểm soát"
        columns={[
          { key: "type", label: "Loại", render: typeLabel },
          { key: "title", label: "Nội dung" },
          {
            key: "owner_id",
            label: "Người phụ trách",
            render: (item) =>
              members.find((member) => member.user_id === item.owner_id)?.user_label ||
              "Chưa phân công",
          },
          {
            key: "due_at",
            label: "Hạn",
            render: (item) => formatDate(item.due_at),
          },
          {
            key: "priority",
            label: "Ưu tiên",
            render: (item) => <StatusPill value={item.priority} />,
          },
          {
            key: "status",
            label: "Trạng thái",
            render: (item) => <StatusPill value={item.status} />,
          },
          ...(canUpdate
            ? [
                {
                  key: "actions",
                  label: "Thao tác",
                  hideWhenEmpty: true,
                  render: (item) =>
                    item.status === "OPEN" ? (
                      <button
                        className="secondary-button"
                        type="button"
                        onClick={() => onUpdate(item, "IN_PROGRESS")}
                      >
                        Bắt đầu
                      </button>
                    ) : item.status === "IN_PROGRESS" ? (
                      <button
                        className="secondary-button"
                        type="button"
                        onClick={() => onUpdate(item, "DONE")}
                      >
                        Hoàn tất
                      </button>
                    ) : null,
                },
              ]
            : []),
        ]}
      />
    </div>
  );
}
