export default function MetricTrendChart({ snapshots = [] }) {
  const values = snapshots.slice(0, 12).reverse();
  const maximum = Math.max(1, ...values.map((item) => Number(item.value) || 0));
  return (
    <div
      className="flex h-32 items-end gap-2 rounded-xl border border-border p-3"
      role="img"
      aria-label="Xu hướng chỉ số"
    >
      {values.length ? (
        values.map((item) => (
          <div
            className="min-w-2 flex-1 rounded-t bg-accent"
            key={item._id}
            style={{ height: `${Math.max(4, ((Number(item.value) || 0) * 100) / maximum)}%` }}
            title={`${item.value} ${item.unit}`}
          />
        ))
      ) : (
        <p className="self-center text-sm text-ink-muted">Chưa có dữ liệu xu hướng</p>
      )}
    </div>
  );
}
