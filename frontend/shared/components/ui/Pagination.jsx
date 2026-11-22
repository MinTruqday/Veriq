export function Pagination({
  value,
  page,
  pageSize,
  total,
  onChange,
  pageSizeOptions,
  onPageSizeChange,
}) {
  const pagination =
    value ||
    (Number.isFinite(page) && Number.isFinite(pageSize) && Number.isFinite(total)
      ? {
          page,
          total,
          total_pages: Math.ceil(total / pageSize),
        }
      : null);
  const totalPages =
    pagination && Number.isFinite(pageSize) && pageSize > 0
      ? Math.max(1, Math.ceil(pagination.total / pageSize))
      : pagination?.total_pages;
  const effectivePageSize = Number(pageSize || pagination?.page_size);
  if (
    !pagination ||
    !Number.isFinite(pagination.page) ||
    !Number.isFinite(pagination.total) ||
    !Number.isFinite(totalPages) ||
    (totalPages <= 1 && !onPageSizeChange)
  )
    return null;
  const start =
    pagination.total && Number.isFinite(effectivePageSize)
      ? (pagination.page - 1) * effectivePageSize + 1
      : 0;
  const end = Number.isFinite(effectivePageSize)
    ? Math.min(pagination.total, pagination.page * effectivePageSize)
    : pagination.total;
  return (
    <nav
      aria-label="Phân trang"
      className="flex flex-wrap items-center justify-between gap-3 border-t border-border px-5 py-4"
    >
      <p className="text-[12px] text-ink-muted">
        {onPageSizeChange
          ? `Hiển thị ${start}–${end} trong ${pagination.total} kết quả · Trang ${pagination.page} trên ${totalPages}`
          : `Trang ${pagination.page} trên ${totalPages} với ${pagination.total} kết quả`}
      </p>
      <div className="flex flex-wrap items-center gap-2">
        {onPageSizeChange && (
          <label className="flex items-center gap-2 text-[12px] text-ink-muted">
            Số mục mỗi trang
            <select
              aria-label="Số mục mỗi trang"
              className="apple-input h-9 w-24"
              value={pageSize}
              onChange={(event) => onPageSizeChange(Number(event.target.value))}
            >
              {(pageSizeOptions || [10, 20, 40]).map((size) => (
                <option key={size} value={size}>
                  {size}
                </option>
              ))}
            </select>
          </label>
        )}
        <button
          aria-label="Trang trước"
          className="secondary-button"
          disabled={pagination.page <= 1}
          type="button"
          onClick={() => onChange(pagination.page - 1)}
        >
          Trang trước
        </button>
        <button
          aria-label="Trang sau"
          className="secondary-button"
          disabled={pagination.page >= totalPages}
          type="button"
          onClick={() => onChange(pagination.page + 1)}
        >
          Trang sau
        </button>
      </div>
    </nav>
  );
}
