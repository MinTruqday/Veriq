"use client";

import { Eye } from "lucide-react";
import DataTable from "./DataTable";
import { StatusPill } from "./WorkspacePrimitives";
import { useDateTimeOptions } from "../hooks/useDateTimeOptions";
import { formatDateTime } from "@/shared/lib/dateTime.mjs";

export default function StrategyVersionHistory({ items, lineageId, onSelect }) {
  const dateTimeOptions = useDateTimeOptions();
  const versions = items.filter((item) => item.lineage_id === lineageId);
  return (
    <DataTable
      items={versions}
      empty="Chưa có lịch sử phiên bản"
      columns={[
        { key: "version", label: "Phiên bản", align: "center" },
        {
          key: "status",
          label: "Trạng thái",
          render: (item) => <StatusPill value={item.status} />,
        },
        {
          key: "updated_at",
          label: "Cập nhật",
          render: (item) => formatDateTime(item.updated_at, dateTimeOptions),
        },
        {
          key: "actions",
          label: "Thao tác",
          minWidth: 64,
          render: (item) => (
            <button
              aria-label={`Mở phiên bản ${item.version}`}
              className="icon-button h-10 w-10"
              title="Mở phiên bản"
              type="button"
              onClick={() => onSelect(item)}
            >
              <Eye aria-hidden="true" size={17} />
            </button>
          ),
        },
      ]}
    />
  );
}
