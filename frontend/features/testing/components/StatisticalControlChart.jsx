export default function StatisticalControlChart({ analysis }) {
  const points = analysis?.points || [];
  const values = points.map((item) => Number(item.value));
  const limits = [
    Number(analysis?.lower_control_limit),
    Number(analysis?.center_line),
    Number(analysis?.upper_control_limit),
  ];
  const chartValues = [...values, ...limits].filter(Number.isFinite);
  if (!points.length || !chartValues.length) {
    return (
      <div className="rounded-xl border border-border px-4 py-8 text-center text-sm text-ink-muted">
        Chưa có đủ số liệu để hiển thị biểu đồ kiểm soát.
      </div>
    );
  }
  const minimum = Math.min(...chartValues);
  const maximum = Math.max(...chartValues);
  const span = Math.max(maximum - minimum, 1);
  const x = (index) => (points.length === 1 ? 50 : 6 + (index * 88) / (points.length - 1));
  const y = (value) => 92 - ((Number(value) - minimum) * 84) / span;
  const path = points.map((item, index) => `${x(index)},${y(item.value)}`).join(" ");
  return (
    <div className="rounded-xl border border-border p-4">
      <svg
        aria-label={`Biểu đồ kiểm soát với ${points.length} lần đo, ${points.filter((item) => item.outlier).length} điểm vượt giới hạn`}
        className="h-56 w-full"
        preserveAspectRatio="none"
        role="img"
        viewBox="0 0 100 100"
      >
        <line
          className="stroke-rose-500"
          strokeDasharray="2 2"
          x1="4"
          x2="96"
          y1={y(limits[2])}
          y2={y(limits[2])}
        />
        <line
          className="stroke-slate-500"
          strokeDasharray="2 2"
          x1="4"
          x2="96"
          y1={y(limits[1])}
          y2={y(limits[1])}
        />
        <line
          className="stroke-rose-500"
          strokeDasharray="2 2"
          x1="4"
          x2="96"
          y1={y(limits[0])}
          y2={y(limits[0])}
        />
        <polyline className="fill-none stroke-accent" points={path} strokeWidth="1.2" />
        {points.map((item, index) => (
          <circle
            className={item.outlier ? "fill-rose-600" : "fill-accent"}
            cx={x(index)}
            cy={y(item.value)}
            key={item.snapshot_id}
            r={item.outlier ? 2 : 1.4}
          >
            <title>{`Lần đo ${index + 1}${item.measured_at ? ` · ${new Date(item.measured_at).toLocaleString("vi-VN")}` : ""} · ${item.value}${analysis?.unit ? ` ${analysis.unit}` : ""}${item.outlier ? " · Vượt giới hạn kiểm soát" : ""}`}</title>
          </circle>
        ))}
      </svg>
      <div className="mt-2 flex flex-wrap gap-x-4 gap-y-2 text-xs text-ink-muted">
        <span className="inline-flex items-center gap-2">
          <span className="h-0.5 w-4 border-t border-dashed border-rose-500" aria-hidden="true" />
          Giới hạn trên: {analysis?.upper_control_limit}
          {analysis?.unit ? ` ${analysis.unit}` : ""}
        </span>
        <span className="inline-flex items-center gap-2">
          <span className="h-0.5 w-4 border-t border-dashed border-slate-500" aria-hidden="true" />
          Đường trung tâm: {analysis?.center_line}
          {analysis?.unit ? ` ${analysis.unit}` : ""}
        </span>
        <span className="inline-flex items-center gap-2">
          <span className="h-0.5 w-4 border-t border-dashed border-rose-500" aria-hidden="true" />
          Giới hạn dưới: {analysis?.lower_control_limit}
          {analysis?.unit ? ` ${analysis.unit}` : ""}
        </span>
        <span className="inline-flex items-center gap-2">
          <span className="h-2 w-2 rounded-full bg-rose-600" aria-hidden="true" />
          Điểm vượt giới hạn
        </span>
      </div>
    </div>
  );
}
