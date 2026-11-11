"use client";

import { useDateTimeOptions } from "../hooks/useDateTimeOptions";
import DataTable from "./DataTable";
import { UserRound } from "lucide-react";
import { StatusPill } from "./WorkspacePrimitives";
import { formatDate as formatDateValue, valueLabel } from "../lib/testing";

const actionTypeLabels = {
  CORRECTIVE: "Khắc phục",
  PREVENTIVE: "Phòng ngừa",
};

const nextStatusLabels = {
  IN_PROGRESS: "Bắt đầu thực hiện",
  IMPLEMENTED: "Ghi nhận đã thực hiện",
  EFFECTIVENESS_REVIEW: "Đánh giá hiệu quả",
  CLOSED: "Đóng hành động",
};

export default function PreventiveActionTable({ items = [], canManage, onAssign, onAdvance }) {
  const dateTimeOptions = useDateTimeOptions();
  const formatDate = (value) => formatDateValue(value, dateTimeOptions);
  const next = {
    OPEN: "IN_PROGRESS",
    IN_PROGRESS: "IMPLEMENTED",
    IMPLEMENTED: "EFFECTIVENESS_REVIEW",
    EFFECTIVENESS_REVIEW: "CLOSED",
  };
  return (
    <DataTable
      items={items}
      empty="Chưa có hành động khắc phục và phòng ngừa"
      columns={[
        {
          key: "action_type",
          label: "Loại",
          minWidth: 128,
          render: (item) => actionTypeLabels[item.action_type] || "Hành động",
        },
        { key: "title", label: "Hành động", minWidth: 240 },
        {
          key: "owner_id",
          label: "Phụ trách",
          render: (item) => (item.owner_id ? "Đã phân công" : "Chưa phân công"),
        },
        {
          key: "due_at",
          label: "Hạn hoàn tất",
          minWidth: 152,
          render: (item) => formatDate(item.due_at),
        },
        {
          key: "status",
          label: "Trạng thái",
          render: (item) => <StatusPill value={item.status} />,
        },
        {
          key: "action",
          label: "Thao tác",
          hideWhenEmpty: true,
          render: (item) =>
            canManage ? (
              <div className="flex flex-wrap gap-2">
                <button
                  aria-label={`Phân công: ${item.title}`}
                  className="icon-button h-9 w-9"
                  title="Phân công"
                  type="button"
                  onClick={() => onAssign(item)}
                >
                  <UserRound aria-hidden="true" size={16} />
                </button>
                {next[item.status] && (
                  <button
                    className="secondary-button"
                    type="button"
                    onClick={() => onAdvance(item, next[item.status])}
                  >
                    {nextStatusLabels[next[item.status]] ||
                      `Chuyển ${valueLabel(next[item.status])}`}
                  </button>
                )}
              </div>
            ) : null,
        },
      ]}
    />
  );
}
