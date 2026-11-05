import Link from "next/link";
import HorizontalScrollCue from "@/shared/components/navigation/HorizontalScrollCue";

export default function ProjectNavigation({ groups, selectedGroup, sidebarCollapsed }) {
  if (!groups.length || !selectedGroup) return null;
  const hasSubnavigation = selectedGroup.items.length > 1;

  return (
    <div
      className={`fixed left-0 right-0 top-[68px] z-30 hidden border-b border-border bg-surface transition-[left] duration-200 lg:block ${sidebarCollapsed ? "lg:left-[76px]" : "lg:left-[260px]"}`}
    >
      <HorizontalScrollCue
        ariaLabel="Khu vực dự án"
        scrollLabel="các khu vực dự án"
        className="h-11 items-center"
        viewportClassName="hide-scrollbar min-w-0 overflow-x-auto px-4 md:px-6"
      >
        <nav aria-label="Khu vực dự án" className="flex h-11 w-max min-w-full items-stretch gap-1">
          {groups.map((group) => {
            const destination = group.href || group.items[0]?.href;
            const active = group.label === selectedGroup.label;
            const label = group.items.some((item) => item.id === "dashboard")
              ? "Tổng quan"
              : group.label;
            if (!destination) return null;
            return (
              <Link
                aria-current={active ? "page" : undefined}
                className={`flex shrink-0 items-center border-b-2 px-3 text-[13px] font-medium transition ${active ? "border-brand text-brand" : "border-transparent text-ink-muted hover:border-border-strong hover:text-ink"}`}
                href={destination}
                key={group.label}
                title={label}
              >
                {label}
              </Link>
            );
          })}
        </nav>
      </HorizontalScrollCue>
      {hasSubnavigation && (
        <HorizontalScrollCue
          ariaLabel={`Trang trong ${selectedGroup.label}`}
          scrollLabel={`trang trong ${selectedGroup.label}`}
          className="border-t border-border/70 py-1.5"
          viewportClassName="hide-scrollbar min-w-0 overflow-x-auto px-4 md:px-6"
        >
          <nav
            aria-label={`Trang trong ${selectedGroup.label}`}
            className="flex w-max min-w-full gap-1"
          >
            {selectedGroup.items.map((item) => (
              <Link
                aria-current={item.id === selectedGroup.activeItemId ? "page" : undefined}
                className={`flex min-h-8 shrink-0 items-center rounded-control px-3 text-[12px] font-medium transition ${item.id === selectedGroup.activeItemId ? "bg-brand-soft text-brand" : "text-ink-muted hover:bg-surface-quiet hover:text-ink"}`}
                href={item.href}
                key={item.id}
                title={item.label}
              >
                {item.label}
              </Link>
            ))}
          </nav>
        </HorizontalScrollCue>
      )}
    </div>
  );
}
