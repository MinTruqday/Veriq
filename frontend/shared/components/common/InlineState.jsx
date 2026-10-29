export default function InlineState({ title, detail, action, tone = "neutral" }) {
  return (
    <div
      className={`rounded-panel border px-5 py-4 ${tone === "danger" ? "border-danger/30 bg-danger-soft" : "border-border bg-surface"}`}
      role={tone === "danger" ? "alert" : "status"}
    >
      <div className="flex flex-col gap-4 sm:flex-row sm:items-center sm:justify-between">
        <div className="min-w-0">
          <p
            className={`break-words text-[14px] font-semibold ${tone === "danger" ? "text-danger" : "text-ink"}`}
          >
            {title}
          </p>
          {detail && (
            <p className="mt-1 break-words text-[13px] leading-relaxed text-ink-muted">{detail}</p>
          )}
        </div>
        {action && <div className="shrink-0">{action}</div>}
      </div>
    </div>
  );
}
