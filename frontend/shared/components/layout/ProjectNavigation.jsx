import LinkTabs from "@/shared/components/navigation/LinkTabs";

export default function ProjectNavigation({ groups, selectedGroup, sidebarCollapsed }) {
  if (!groups.length || !selectedGroup) return null;
  const hasSubnavigation = selectedGroup.items.length > 1;

  return (
    <div
      className={`fixed left-0 right-0 top-[68px] z-30 hidden border-b border-border bg-surface transition-[left] duration-200 lg:block ${sidebarCollapsed ? "lg:left-[76px]" : "lg:left-[260px]"}`}
    >
      <LinkTabs
        items={groups.map((group) => ({
          id: group.label,
          href: group.href || group.items[0]?.href,
          active: group.label === selectedGroup.label,
          label: group.items.some((item) => item.id === "dashboard") ? "Tổng quan" : group.label,
        }))}
        label="Khu vực dự án"
        scrollLabel="các khu vực dự án"
        className="h-11 items-center"
        viewportClassName="px-4 md:px-6"
      />
      {hasSubnavigation && (
        <LinkTabs
          items={selectedGroup.items.map((item) => ({
            ...item,
            active: item.id === selectedGroup.activeItemId,
          }))}
          label={`Trang trong ${selectedGroup.label}`}
          scrollLabel={`trang trong ${selectedGroup.label}`}
          compact
          baseline
          className="border-t border-border/70"
          viewportClassName="px-4 md:px-6"
        />
      )}
    </div>
  );
}
