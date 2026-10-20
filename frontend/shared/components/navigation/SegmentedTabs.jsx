import HorizontalScrollCue from "./HorizontalScrollCue";

export default function SegmentedTabs({ tabs, value, onChange, label }) {
  return (
    <HorizontalScrollCue
      className="max-w-full rounded-control bg-surface-quiet p-1"
      viewportClassName="hide-scrollbar flex min-w-0 max-w-full flex-nowrap gap-1 overflow-x-auto overscroll-x-contain"
    >
      <div role="tablist" aria-label={label} className="flex w-max min-w-full flex-nowrap gap-1">
        {tabs.map((tab) => (
          <button
            key={tab.id}
            type="button"
            role="tab"
            aria-selected={value === tab.id}
            onClick={() => onChange(tab.id)}
            className={`min-h-11 shrink-0 whitespace-nowrap rounded-control px-3 text-[13px] font-semibold transition duration-150 md:min-h-9 ${value === tab.id ? "bg-surface text-ink shadow-[0_1px_3px_rgba(48,47,42,0.08)]" : "text-ink-muted hover:text-ink"}`}
          >
            {tab.label}
            {typeof tab.count === "number" ? ` ${tab.count}` : ""}
          </button>
        ))}
      </div>
    </HorizontalScrollCue>
  );
}
