export default function MetricTrendChart({ snapshots = [] }) {
  const values = snapshots.slice(0, 12).reverse();
  const maximum = Math.max(1, ...values.map((item) => Number(item.value) || 0));
  return (
    <div className="min-w-0 rounded-xl border border-border p-3">
      <p className="mb-2 text-sm font-semibold text-ink">Xu hướng qua các lần đo</p>
      <div className="flex h-32 min-w-0 items-end gap-2" role="img" aria-label="Xu hướng chỉ số">
        {values.length ? (
          values.map((item, index) => (
            <div
              className="min-w-2 flex-1 rounded-t bg-accent"
              key={item._id}
              style={{ height: `${Math.max(4, ((Number(item.value) || 0) * 100) / maximum)}%` }}
              title={`Lần đo ${index + 1}${item.measured_at ? ` · ${new Date(item.measured_at).toLocaleString("vi-VN")}` : ""} · ${item.value ?? "Chưa có số liệu"}${item.unit ? ` ${item.unit}` : ""}`}
            />
          ))
        ) : (
          <p className="self-center text-sm text-ink-muted">Chưa có dữ liệu xu hướng</p>
        )}
      </div>
    </div>
  );
}
