import HorizontalScrollCue from "./HorizontalScrollCue";

export default function SegmentedTabs({ tabs, value, onChange, label }) {
  return (
    <HorizontalScrollCue
      className="max-w-full border-b border-border"
      viewportClassName="hide-scrollbar flex min-w-0 max-w-full flex-nowrap gap-1 overflow-x-auto overscroll-x-contain"
    >
      <div
        role="group"
        aria-label={label || "Chế độ xem"}
        className="flex h-10 w-max min-w-full flex-nowrap items-stretch gap-1"
      >
        {tabs.map((tab) => (
          <button
            key={tab.id}
            id={tab.elementId}
            type="button"
            aria-pressed={value === tab.id}
            onClick={() => onChange(tab.id)}
            className={`-mb-px flex shrink-0 items-center whitespace-nowrap border-b-2 px-3 text-[13px] font-medium transition duration-150 ${value === tab.id ? "border-brand text-brand" : "border-transparent text-ink-muted hover:border-border-strong hover:text-ink"}`}
          >
            {tab.label}
            {typeof tab.count === "number" ? ` ${tab.count}` : ""}
          </button>
        ))}
      </div>
    </HorizontalScrollCue>
  );
}
