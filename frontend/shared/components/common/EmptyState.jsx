import Link from "next/link";
export default function EmptyState({
  text = "Chưa có dữ liệu",
  children,
  description,
  compact = false,
  bordered = false,
  actionLabel,
  actionHref,
  onAction,
}) {
  const actionClass =
    "mt-5 inline-flex min-h-11 max-w-full items-center justify-center break-words rounded-control bg-brand px-4 py-2.5 text-center text-[14px] font-semibold text-white transition duration-150 hover:bg-brand-hover active:translate-y-px";
  const message = children ?? text;

  return (
    <div
      role="status"
      aria-live="polite"
      className={`${compact ? "py-8" : "py-12"} flex w-full min-w-0 flex-col items-center justify-center px-5 text-center md:px-8 ${bordered ? "rounded-panel border border-border bg-surface" : ""}`}
    >
      <p className="max-w-full break-words text-[15px] font-semibold text-ink">{message}</p>
      {description && (
        <p className="mt-2 max-w-[58ch] break-words text-[14px] leading-relaxed text-ink-muted">
          {description}
        </p>
      )}
      {actionLabel && actionHref && (
        <Link href={actionHref} className={actionClass}>
          {actionLabel}
        </Link>
      )}
      {actionLabel && onAction && !actionHref && (
        <button type="button" onClick={onAction} className={actionClass}>
          {actionLabel}
        </button>
      )}
    </div>
  );
}
