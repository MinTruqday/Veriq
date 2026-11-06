export default function TestProgressBoard({ metrics = {} }) {
  const percentValue = (value, denominator) =>
    value !== null && value !== undefined && Number(denominator) > 0
      ? `${value}%`
      : "Chưa có dữ liệu";
  const countValue = (value) => value ?? "Chưa có dữ liệu";
  const items = [
    {
      label: "Tiến độ thực thi",
      value: percentValue(metrics.execution_percent, metrics.execution_denominator),
      detail: `${metrics.executed_test_count ?? "—"} / ${metrics.planned_test_count ?? "—"} kết quả`,
    },
    {
      label: "Tỷ lệ đạt",
      value: percentValue(metrics.pass_rate, metrics.pass_rate_denominator),
      detail: `${metrics.pass ?? "—"} đạt · ${metrics.fail ?? "—"} không đạt`,
    },
    {
      label: "Độ phủ yêu cầu",
      value: percentValue(metrics.requirement_coverage, metrics.requirement_coverage_denominator),
      detail: "Yêu cầu có liên kết kiểm thử",
    },
    {
      label: "Độ phủ điều kiện kiểm thử",
      value: percentValue(
        metrics.test_condition_coverage,
        metrics.test_condition_coverage_denominator,
      ),
      detail: "Điều kiện có liên kết kiểm thử",
    },
    {
      label: "Lỗi chặn phát hành đang mở",
      value: countValue(metrics.open_blocker),
      detail:
        metrics.open_critical === null || metrics.open_critical === undefined
          ? "Chưa có dữ liệu về lỗi nghiêm trọng"
          : `${metrics.open_critical} lỗi nghiêm trọng`,
    },
  ];
  return (
    <section
      aria-label="Chỉ số giám sát"
      className="grid overflow-hidden rounded-panel border border-border bg-surface sm:grid-cols-2 xl:grid-cols-5"
    >
      {items.map((item, index) => (
        <div
          className={`min-w-0 px-4 py-4 ${index ? "border-t border-border sm:border-l sm:border-t-0" : ""} ${index >= 2 ? "xl:border-l" : ""}`}
          key={item.label}
        >
          <p className="break-words text-xs font-medium leading-5 text-ink-muted">{item.label}</p>
          <p className="mt-2 break-words text-xl font-semibold tracking-tight text-ink">
            {item.value}
          </p>
          <p className="mt-1 break-words text-xs leading-5 text-ink-faint">{item.detail}</p>
        </div>
      ))}
    </section>
  );
}
