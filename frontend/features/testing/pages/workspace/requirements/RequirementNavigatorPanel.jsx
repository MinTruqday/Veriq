import { Search } from "lucide-react";
import { Pagination } from "@/shared/components/ui/Pagination";
import { Panel, StatusPill } from "../../../components/WorkspacePrimitives";
import {
  REQUIREMENT_COVERAGE_FILTERS,
  REQUIREMENT_SORT_OPTIONS,
  REQUIREMENT_STATUS_FILTERS,
} from "./requirements.model";

export default function RequirementNavigatorPanel({
  items,
  loading,
  query,
  setQuery,
  filters,
  setFilters,
  members,
  pageInfo,
  pageSize,
  onPageChange,
  setPage,
  selectedId,
  onSelect,
}) {
  const updateFilter = (key, value) => {
    setFilters((current) => ({ ...current, [key]: value }));
    setPage(1);
  };
  return (
    <Panel title="Yêu cầu" className="min-w-0 md:sticky md:top-20 md:self-start">
      <label className="relative block border-b border-border p-3">
        <span className="sr-only">Tìm trong yêu cầu</span>
        <Search
          aria-hidden="true"
          className="pointer-events-none absolute left-6 top-1/2 -translate-y-1/2 text-ink-faint"
          size={15}
        />
        <input
          className="apple-input w-full pl-9"
          onChange={(event) => setQuery(event.target.value)}
          placeholder="Tìm yêu cầu"
          type="search"
          value={query}
        />
      </label>
      <details className="border-b border-border p-3">
        <summary className="cursor-pointer text-xs font-medium">
          Bộ lọc
          {[filters.status, filters.coverage, filters.tag, filters.owner].filter(Boolean).length >
            0 && <span className="ml-1 text-ink-muted">Đang áp dụng</span>}
        </summary>
        <div className="mt-3 grid gap-2">
          <select
            aria-label="Lọc trạng thái yêu cầu"
            className="apple-input w-full"
            value={filters.status}
            onChange={(event) => updateFilter("status", event.target.value)}
          >
            {REQUIREMENT_STATUS_FILTERS.map((option) => (
              <option key={option.value} value={option.value}>
                {option.label}
              </option>
            ))}
          </select>
          <select
            aria-label="Lọc độ phủ yêu cầu"
            className="apple-input w-full"
            value={filters.coverage}
            onChange={(event) => updateFilter("coverage", event.target.value)}
          >
            {REQUIREMENT_COVERAGE_FILTERS.map((option) => (
              <option key={option.value} value={option.value}>
                {option.label}
              </option>
            ))}
          </select>
          <input
            aria-label="Lọc nhãn yêu cầu"
            className="apple-input w-full"
            onChange={(event) => updateFilter("tag", event.target.value)}
            placeholder="Nhãn"
            value={filters.tag}
          />
          <select
            aria-label="Lọc người phụ trách yêu cầu"
            className="apple-input w-full"
            value={filters.owner}
            onChange={(event) => updateFilter("owner", event.target.value)}
          >
            <option value="">Mọi người phụ trách</option>
            {members.map((member) => (
              <option key={member.user_id} value={member.user_id}>
                {member.user_label || member.user?.email || "Thành viên dự án"}
              </option>
            ))}
          </select>
          <select
            aria-label="Sắp xếp yêu cầu"
            className="apple-input w-full"
            value={filters.sort}
            onChange={(event) => updateFilter("sort", event.target.value)}
          >
            {REQUIREMENT_SORT_OPTIONS.map((option) => (
              <option key={option.value} value={option.value}>
                {option.label}
              </option>
            ))}
          </select>
        </div>
      </details>
      {loading ? (
        <p className="p-4 text-sm text-ink-muted" role="status">
          Đang tải danh sách…
        </p>
      ) : items.length ? (
        <ul className="max-h-[min(62vh,44rem)] divide-y divide-border overflow-y-auto">
          {items.map((item) => {
            const active = item._id === selectedId;
            const title = item.current_version?.title || item.requirement_key;
            return (
              <li key={item._id}>
                <button
                  aria-current={active ? "page" : undefined}
                  className={`block w-full min-w-0 px-3 py-3 text-left transition ${active ? "bg-brand-soft/60" : "hover:bg-surface-quiet"}`}
                  onClick={() => onSelect(item)}
                  type="button"
                >
                  <span className="flex min-w-0 flex-wrap items-center gap-x-2 gap-y-1">
                    <span className="min-w-0 max-w-full truncate font-mono text-[11px] font-semibold text-brand">
                      {item.requirement_key}
                      {item.current_version?.version ? ` · v${item.current_version.version}` : ""}
                    </span>
                    <span className="max-w-full shrink-0">
                      <StatusPill value={item.status} />
                    </span>
                  </span>
                  <span className="mt-1 line-clamp-2 break-words text-[13px] font-medium leading-5 [overflow-wrap:anywhere]">
                    {title}
                  </span>
                </button>
              </li>
            );
          })}
        </ul>
      ) : (
        <p className="p-4 text-sm text-ink-muted">Không có yêu cầu phù hợp.</p>
      )}
      <Pagination value={pageInfo} pageSize={pageSize} onChange={onPageChange} />
    </Panel>
  );
}
