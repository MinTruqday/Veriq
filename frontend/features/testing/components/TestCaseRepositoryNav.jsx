"use client";
import { Search } from "lucide-react";
import { Pagination } from "@/shared/components/ui/Pagination";
import { StatusPill } from "./WorkspacePrimitives";
import { valueLabel } from "../lib/testing";

export default function TestCaseRepositoryNav({
  cases,
  selected,
  suites,
  filters,
  pageInfo,
  page,
  pageSize,
  onPageChange,
  onPageSizeChange,
  onFilterChange,
  onSelect,
}) {
  const visibleCases =
    selected && !cases.some((item) => item._id === selected._id) ? [selected, ...cases] : cases;

  return (
    <aside className="min-w-0 overflow-hidden rounded-panel border border-border bg-surface xl:sticky xl:top-4 xl:self-start">
      <div className="border-b border-border p-4">
        <div className="flex items-center justify-between gap-3">
          <h2 className="font-semibold text-ink">Kho ca kiểm thử</h2>
          <span className="text-xs text-ink-muted">{pageInfo?.total ?? cases.length} ca</span>
        </div>
        <label className="relative mt-3 block">
          <span className="sr-only">Tìm ca kiểm thử</span>
          <Search
            aria-hidden="true"
            className="pointer-events-none absolute left-3 top-1/2 -translate-y-1/2 text-ink-muted"
            size={16}
          />
          <input
            aria-label="Tìm ca kiểm thử"
            className="apple-input w-full pl-9"
            placeholder="Tìm mã hoặc tiêu đề"
            value={filters.q || ""}
            onChange={(event) => onFilterChange("q", event.target.value)}
          />
        </label>
        <label className="mt-3 block text-xs font-medium text-ink-muted">
          Bộ kiểm thử
          <select
            aria-label="Lọc theo bộ kiểm thử"
            className="apple-input mt-1 w-full text-sm"
            value={filters.suite_id || ""}
            onChange={(event) => onFilterChange("suite_id", event.target.value)}
          >
            <option value="">Tất cả ca</option>
            {suites
              .filter((suite) => suite.status !== "ARCHIVED")
              .map((suite) => (
                <option key={suite._id} value={suite._id}>
                  {suite.name}
                </option>
              ))}
          </select>
        </label>
      </div>
      <nav
        aria-label="Danh sách ca kiểm thử"
        className="max-h-[55dvh] divide-y divide-border overflow-y-auto xl:max-h-[calc(100dvh-19rem)]"
      >
        {visibleCases.length ? (
          visibleCases.map((item) => {
            const active = item._id === selected?._id;
            return (
              <button
                aria-current={active ? "true" : undefined}
                className={`block w-full border-l-4 px-4 py-3 text-left transition ${active ? "border-brand bg-brand/5" : "border-transparent hover:bg-surface-quiet"}`}
                key={item._id}
                onClick={() => onSelect(item._id)}
                type="button"
              >
                <span className="flex min-w-0 items-start justify-between gap-2">
                  <span className="min-w-0">
                    <span className="block truncate font-mono text-[11px] text-ink-muted">
                      {item.test_case_key || "-"}
                    </span>
                    <span className="mt-1 block line-clamp-2 break-words text-sm font-medium text-ink">
                      {item.current_version?.title || item.title || "Chưa có tiêu đề"}
                    </span>
                  </span>
                  <span className="shrink-0 text-[11px] text-ink-muted">
                    {valueLabel(item.current_version?.priority || item.priority || "UNASSESSED")}
                  </span>
                </span>
                <span className="mt-2 flex flex-wrap items-center gap-2">
                  <StatusPill value={item.status} />
                  {item.latest_result && <StatusPill value={item.latest_result} />}
                </span>
              </button>
            );
          })
        ) : (
          <p className="p-5 text-sm text-ink-muted">
            {filters.suite_id
              ? "Bộ kiểm thử này chưa có ca phù hợp"
              : "Không tìm thấy ca kiểm thử phù hợp"}
          </p>
        )}
      </nav>
      <div className="border-t border-border px-2 py-2">
        <Pagination
          value={pageInfo}
          page={page}
          pageSize={pageSize}
          onChange={onPageChange}
          pageSizeOptions={[10, 20, 40]}
          onPageSizeChange={onPageSizeChange}
        />
      </div>
    </aside>
  );
}
