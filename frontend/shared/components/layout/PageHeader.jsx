export default function PageHeader({ title, showTitle = true, description, actions, meta }) {
  if (!showTitle && !actions && !meta) {
    return <h1 className="sr-only">{title}</h1>;
  }
  return (
    <header className="mb-6 min-w-0">
      <div
        className={`workspace-page-header min-w-0 gap-4 ${actions ? "workspace-page-header-with-actions" : ""}`}
      >
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
          <div className="workspace-page-actions flex min-w-0 max-w-full flex-wrap items-center gap-2">
            {actions}
          </div>
        )}
      </div>
    </header>
  );
}
