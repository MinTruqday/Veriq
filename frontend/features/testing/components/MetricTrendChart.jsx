export default function MetricTrendChart({ snapshots = [], aggregation }) {
  const values = snapshots.slice(0, 12).reverse();
  const maximum = Math.max(1, ...values.map((item) => Number(item.value) || 0));
  return (
    <div className="min-w-0 rounded-xl border border-border p-3">
      <p className="mb-2 text-sm font-semibold text-ink">Xu hướng qua các lần đo</p>
      <ol
        aria-label="Các lần đo theo thời gian"
        className="grid min-h-40 grid-cols-[repeat(auto-fit,minmax(5rem,1fr))] items-end gap-x-3"
      >
        {values.length >= 2 ? (
          values.map((item, index) => (
            <li className="flex min-w-0 flex-col items-center gap-1.5" key={item._id}>
              <span className="text-xs font-medium text-ink">
                {aggregation === "RATIO"
                  ? `${((Number(item.value) || 0) * 100).toLocaleString(undefined, { maximumFractionDigits: 2 })}%`
                  : `${item.value ?? "—"}${item.unit ? ` ${item.unit}` : ""}`}
              </span>
              <span aria-hidden="true" className="flex h-24 w-full items-end justify-center">
                <span
                  className="w-8 rounded-t bg-accent"
                  style={{ height: `${Math.max(4, ((Number(item.value) || 0) * 100) / maximum)}%` }}
                />
              </span>
              <span className="text-center text-xs text-ink-muted">
                {item.measured_at
                  ? new Date(item.measured_at).toLocaleDateString(undefined, {
                      day: "numeric",
                      month: "short",
                    })
                  : `Lần ${index + 1}`}
              </span>
            </li>
          ))
        ) : (
          <li className="col-span-full self-center text-sm text-ink-muted">
            {values.length === 1
              ? "Cần ít nhất hai lần đo để hiển thị xu hướng."
              : "Chưa có dữ liệu đo lường."}
          </li>
        )}
      </ol>
    </div>
  );
}
