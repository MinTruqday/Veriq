import { Eye } from "lucide-react";
import { StatusPill } from "./WorkspacePrimitives";
import ContentOriginBadge from "../../../shared/components/common/ContentOriginBadge";
import { valueLabel } from "../lib/testing";

export default function TestConditionTable({ items, selectedId, onSelect }) {
  return items.length ? (
    <div className="divide-y divide-border">
      {items.map((item) => (
        <article
          className={`min-w-0 ${selectedId === item._id ? "bg-brand-soft/50" : ""}`}
          key={item._id}
        >
          <button
            aria-label={`Mở điều kiện ${item.condition_key || item.title}`}
            aria-pressed={selectedId === item._id}
            className="flex min-h-20 w-full min-w-0 items-start justify-between gap-3 px-4 py-3 text-left transition-colors hover:bg-surface-quiet focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-brand/50"
            onClick={() => onSelect(item)}
            type="button"
          >
            <span className="min-w-0 flex-1">
              <span className="flex min-w-0 flex-wrap items-center gap-x-2 gap-y-1">
                <span className="text-[11px] font-semibold tracking-wide text-ink-muted">
                  {item.condition_key}
                </span>
                <StatusPill value={item.status} />
              </span>
              <span className="mt-1 block break-words text-[13px] font-medium leading-5 text-ink">
                {item.title}
              </span>
              <span className="mt-1 block break-words text-[12px] leading-5 text-ink-muted">
                {item.coverage_item || "Chưa gắn hạng mục độ phủ"}
              </span>
            </span>
            <span className="flex shrink-0 flex-col items-end gap-2">
              <StatusPill value={item.risk} />
              <Eye aria-hidden="true" className="text-ink-muted" size={15} />
            </span>
          </button>
          <div className="grid min-w-0 grid-cols-2 items-center gap-x-3 gap-y-2 px-4 pb-3 text-[11px] text-ink-muted">
            <span className="min-w-0 justify-self-start">
              <ContentOriginBadge origin={item.origin || "manual"} />
            </span>
            <span className="min-w-0 break-words">
              {item.category ? valueLabel(item.category) : "Chưa phân loại"}
            </span>
            <span className="min-w-0 break-words">Ưu tiên: {valueLabel(item.priority)}</span>
            <span className="min-w-0 break-words">
              Khả năng kiểm thử: {valueLabel(item.testability_status)}
            </span>
          </div>
        </article>
      ))}
    </div>
  ) : (
    <p className="px-5 py-8 text-center text-sm text-ink-muted" role="status">
      Chưa có điều kiện kiểm thử
    </p>
  );
}
