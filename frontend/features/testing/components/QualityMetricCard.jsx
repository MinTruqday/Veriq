import ThresholdStatus from "./ThresholdStatus";

export default function QualityMetricCard({ definition, snapshot }) {
  const displayedValue =
    snapshot && definition.aggregation === "RATIO"
      ? `${(Number(snapshot.value) * 100).toLocaleString("vi-VN", { maximumFractionDigits: 2 })}%`
      : snapshot
        ? `${snapshot.value} ${snapshot.unit || definition.unit || ""}`.trim()
        : "Chưa đo";
  return (
    <article className="rounded-2xl border border-border bg-surface p-4">
      <div className="min-w-0">
        <p className="break-words text-sm font-semibold">{definition.name}</p>
        <p className="mt-1 break-words text-xs text-ink-muted">{definition.objective}</p>
      </div>
      {snapshot && (
        <div className="mt-2">
          <ThresholdStatus
            metricKey={definition.key}
            value={snapshot.value}
            target={definition.target}
            warning={definition.warning_threshold}
            critical={definition.critical_threshold}
          />
        </div>
      )}
      <p className="mt-4 text-2xl font-semibold">{displayedValue}</p>
      {definition.description && (
        <p className="mt-2 break-words text-xs text-ink-muted">{definition.description}</p>
      )}
    </article>
  );
}
