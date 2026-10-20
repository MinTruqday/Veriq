export default function PageHeader({ title, showTitle = true, description, actions, meta }) {
  if (!showTitle && !actions && !meta) {
    return <h1 className="sr-only">{title}</h1>;
  }
  return (
    <header className="mb-6 min-w-0">
      <div className="flex min-w-0 flex-col gap-4 xl:flex-row xl:items-end xl:justify-between">
        <div className="min-w-0">
          <h1 className={showTitle ? "product-heading" : "sr-only"}>{title}</h1>
          {showTitle && description && (
            <p className="mt-2 max-w-[65ch] text-[14px] leading-relaxed text-ink-muted">
              {description}
            </p>
          )}
          {meta && <div className="mt-2 text-[13px] text-ink-muted">{meta}</div>}
        </div>
        {actions && (
          <div className="flex min-w-0 max-w-full flex-wrap items-center gap-2 xl:shrink-0 xl:justify-end">
            {actions}
          </div>
        )}
      </div>
    </header>
  );
}
