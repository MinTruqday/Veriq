import { valueLabel } from "../lib/testing";

export default function ReviewChecklist({ items = [] }) {
  return (
    <div className="space-y-2">
      {items.length ? (
        items.map((item, index) => (
          <div
            className="flex items-start gap-3 rounded-xl border border-border px-3 py-2 text-sm"
            key={item.id || index}
          >
            <span className="font-semibold">{valueLabel(item.status || "PENDING")}</span>
            <span>{item.label || item.text || String(item)}</span>
          </div>
        ))
      ) : (
        <p className="text-sm text-ink-muted">Chưa có mục kiểm tra</p>
      )}
    </div>
  );
}
