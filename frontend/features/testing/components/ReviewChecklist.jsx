import { valueLabel } from "../lib/testing";

export default function ReviewChecklist({ items = [] }) {
  return (
    <div className="space-y-2">
      {items.length ? (
        items.map((item, index) => (
          <div
            className="grid min-w-0 grid-cols-[auto_minmax(0,1fr)] items-start gap-3 rounded-xl border border-border px-3 py-2 text-sm"
            key={item.id || index}
          >
            <span className="whitespace-nowrap rounded-full bg-surface-quiet px-2 py-1 text-xs font-semibold">
              {valueLabel(item.status || "PENDING")}
            </span>
            <span className="min-w-0 break-words">{item.label || item.text || String(item)}</span>
          </div>
        ))
      ) : (
        <p className="text-sm text-ink-muted">Chưa có mục kiểm tra</p>
      )}
    </div>
  );
}
