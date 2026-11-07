import Link from "next/link";
import HorizontalScrollCue from "./HorizontalScrollCue";

export default function LinkTabs({
  items,
  label,
  scrollLabel,
  compact = false,
  baseline = false,
  className = "",
  viewportClassName = "",
}) {
  const visibleItems = items.filter((item) => item?.id && item.href && item.label);
  if (!visibleItems.length) return null;

  return (
    <HorizontalScrollCue
      ariaLabel={label}
      scrollLabel={scrollLabel || label || "các trang"}
      className={`min-w-0 ${className}`}
      viewportClassName={`hide-scrollbar min-w-0 overflow-x-auto ${viewportClassName}`}
    >
      <nav
        aria-label={label}
        className={`flex ${compact ? "h-10" : "h-11"} w-max min-w-full items-stretch gap-1 ${baseline ? "border-b border-border" : ""}`}
      >
        {visibleItems.map((item) => (
          <Link
            aria-current={item.active ? "page" : undefined}
            className={`${baseline ? "-mb-px " : ""}flex shrink-0 items-center whitespace-nowrap border-b-2 px-3 ${compact ? "text-[12px]" : "text-[13px]"} font-medium transition ${item.active ? "border-brand text-brand" : "border-transparent text-ink-muted hover:border-border-strong hover:text-ink"}`}
            href={item.href}
            key={item.id}
            title={item.label}
          >
            {item.label}
          </Link>
        ))}
      </nav>
    </HorizontalScrollCue>
  );
}
