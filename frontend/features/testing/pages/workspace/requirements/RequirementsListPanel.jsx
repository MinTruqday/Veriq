import DataTable from "../../../components/DataTable";
import { LoadingState, Panel, StatusPill } from "../../../components/WorkspacePrimitives";
import { Pagination } from "@/shared/components/ui/Pagination";
import { valueLabel } from "../../../lib/testing";
import {
  REQUIREMENT_COVERAGE_FILTERS,
  REQUIREMENT_SORT_OPTIONS,
  REQUIREMENT_STATUS_FILTERS,
} from "./requirements.model";

export default function RequirementsListPanel({
  projectId,
  loading,
  items,
  query,
  setQuery,
  filters,
  setFilters,
  setPage,
  members,
  selectedIds,
  setSelectedIds,
  pageInfo,
  can,
  onBulkTags,
  onScanDuplicates,
  onMerge,
  onBulkArchive,
  onSelect,
  title = "Danh sách yêu cầu",
}) {
  const activeFilterCount = [filters.status, filters.coverage, filters.tag, filters.owner].filter(
    Boolean,
  ).length;
  const canSelectRows = [
    "requirement.update",
    "requirement.duplicate_check",
    "requirement.merge",
    "requirement.archive",
  ].some(can);
  const updateFilter = (key, value) => {
    setFilters((current) => ({ ...current, [key]: value }));
    setPage(1);
  };

  return (
    <Panel
      title={title}
      className="requirements-list-panel"
      actions={
        <div className="flex min-w-0 flex-wrap items-center gap-2">
          <input
            aria-label="Tìm yêu cầu"
            className="apple-input w-full min-w-0 sm:w-64"
            value={query}
            onChange={(event) => {
              setQuery(event.target.value);
              setPage(1);
            }}
            placeholder="Tìm yêu cầu"
          />
          {selectedIds.length > 0 && can("requirement.update") && (
            <button
              className="secondary-button w-full whitespace-nowrap sm:w-auto"
              type="button"
              onClick={onBulkTags}
            >
              Cập nhật nhãn
            </button>
          )}
          {can("requirement.duplicate_check") && (
            <button
              className="secondary-button w-full whitespace-nowrap sm:w-auto"
              type="button"
              onClick={onScanDuplicates}
            >
              {selectedIds.length ? "Tìm yêu cầu trùng đã chọn" : "Kiểm tra trùng lặp"}
            </button>
          )}
          {selectedIds.length > 0 && can("requirement.merge") && (
            <button
              className="secondary-button w-full whitespace-nowrap sm:w-auto"
              disabled={selectedIds.length < 2}
              type="button"
              onClick={onMerge}
            >
              Gộp yêu cầu
            </button>
          )}
          {selectedIds.length > 0 && can("requirement.archive") && (
            <button
              className="danger-button w-full whitespace-nowrap sm:w-auto"
              type="button"
              onClick={onBulkArchive}
            >
              Lưu trữ
            </button>
          )}
        </div>
      }
    >
      {loading ? (
        <div className="p-5">
          <LoadingState />
        </div>
      ) : (
        <>
          <details className="border-b border-border p-4">
            <summary className="cursor-pointer text-sm font-medium">
              Bộ lọc và sắp xếp
              {activeFilterCount > 0 && (
                <span className="ml-2 text-ink-muted">{activeFilterCount} bộ lọc đang dùng</span>
              )}
            </summary>
            <div className="mt-3 grid gap-3 sm:grid-cols-2 xl:grid-cols-5">
              <select
                aria-label="Lọc trạng thái yêu cầu"
                className="apple-input"
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
                className="apple-input"
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
                className="apple-input"
                placeholder="Nhãn"
                value={filters.tag}
                onChange={(event) => updateFilter("tag", event.target.value)}
              />
              <select
                aria-label="Lọc người phụ trách yêu cầu"
                className="apple-input"
                value={filters.owner}
                onChange={(event) => updateFilter("owner", event.target.value)}
              >
                <option value="">Mọi người phụ trách</option>
                {members.map((item) => (
                  <option key={item.user_id} value={item.user_id}>
                    {item.user_label || item.user?.email || "Thành viên dự án"}
                  </option>
                ))}
              </select>
              <select
                aria-label="Sắp xếp yêu cầu"
                className="apple-input"
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
          <DataTable
            onSelect={
              onSelect ||
              ((item) => window.location.assign(`/du-an/${projectId}/yeu-cau/${item._id}`))
            }
            items={items}
            selectedIds={canSelectRows ? selectedIds : undefined}
            onSelectionChange={canSelectRows ? setSelectedIds : undefined}
            selectionLabel="Chọn yêu cầu"
            empty="Chưa có yêu cầu"
            columns={[
              { key: "requirement_key", label: "Mã" },
              { key: "title", label: "Tên", render: (item) => item.current_version?.title },
              {
                key: "type",
                label: "Loại",
                render: (item) => valueLabel(item.current_version?.type),
              },
              {
                key: "risk",
                label: "Rủi ro",
                render: (item) => valueLabel(item.current_version?.risk),
              },
              {
                key: "status",
                label: "Trạng thái",
                render: (item) => <StatusPill value={item.status} />,
              },
              {
                key: "assurance_status",
                label: "Hồ sơ đảm bảo",
                render: (item) => <StatusPill value={item.assurance_status} />,
              },
            ]}
          />
          <Pagination value={pageInfo} onChange={setPage} />
        </>
      )}
    </Panel>
  );
}
