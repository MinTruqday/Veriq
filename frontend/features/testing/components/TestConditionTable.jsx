import DataTable from "./DataTable";
import { StatusPill } from "./WorkspacePrimitives";
import ContentOriginBadge from "../../../shared/components/common/ContentOriginBadge";
import { valueLabel } from "../lib/testing";

export default function TestConditionTable({ items, onSelect }) {
  return (
    <DataTable
      items={items}
      empty="Chưa có điều kiện kiểm thử"
      columns={[
        { key: "condition_key", label: "Mã" },
        { key: "title", label: "Điều kiện" },
        {
          key: "origin",
          label: "Nguồn",
          render: (item) => <ContentOriginBadge origin={item.origin || "manual"} />,
        },
        {
          key: "category",
          label: "Nhóm",
          render: (item) => (item.category ? valueLabel(item.category) : "Chưa phân loại"),
        },
        { key: "coverage_item", label: "Hạng mục độ phủ" },
        { key: "risk", label: "Rủi ro", render: (item) => <StatusPill value={item.risk} /> },
        {
          key: "priority",
          label: "Ưu tiên",
          render: (item) => <StatusPill value={item.priority} />,
        },
        {
          key: "testability_status",
          label: "Khả năng kiểm thử",
          render: (item) => <StatusPill value={item.testability_status} />,
        },
        {
          key: "status",
          label: "Trạng thái",
          render: (item) => <StatusPill value={item.status} />,
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
