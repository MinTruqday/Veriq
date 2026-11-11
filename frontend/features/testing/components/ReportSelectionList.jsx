"use client";

import { useDateTimeOptions } from "../hooks/useDateTimeOptions";
import { formatDate as formatDateValue } from "../lib/testing";
import { StatusPill } from "./WorkspacePrimitives";

export default function ReportSelectionList({ items, selectedId, onSelect, label, emptyMessage }) {
  const dateTimeOptions = useDateTimeOptions();
  const formatDate = (value) => formatDateValue(value, dateTimeOptions);
  if (!items.length) {
    return (
      <p className="px-4 py-5 text-sm text-ink-muted" role="status">
        {emptyMessage}
      </p>
    );
  }

  return (
    <ul aria-label={label} className="divide-y divide-border">
      {items.map((item) => {
        const start = item.reporting_period?.start_at || item.reporting_period_start;
        const end = item.reporting_period?.end_at || item.reporting_period_end;
        const selected = selectedId === item._id;
        return (
          <li className="min-w-0" key={item._id}>
            <button
              aria-pressed={selected}
              className={`w-full min-w-0 px-4 py-3 text-left transition-colors ${selected ? "bg-surface-raised" : "hover:bg-surface-raised/60"}`}
              type="button"
              onClick={() => onSelect(item)}
            >
              <span className="flex min-w-0 flex-wrap items-center justify-between gap-2">
                <span className="font-medium">Báo cáo lần {item.sequence}</span>
                <StatusPill value={item.status} />
              </span>
              <span className="mt-1 block text-xs text-ink-muted">
                {formatDate(item.created_at)}
              </span>
              {start && end && (
                <span className="mt-1 block text-xs text-ink-faint">
                  Kỳ {formatDate(start)} đến {formatDate(end)}
                </span>
              )}
            </button>
          </li>
        );
      })}
    </ul>
  );
}
