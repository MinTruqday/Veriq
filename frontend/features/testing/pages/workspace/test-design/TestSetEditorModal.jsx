import { useEffect, useRef, useState } from "react";
import { ChevronLeft, ChevronRight } from "lucide-react";
import { Modal, ModalFooter, ModalHeader, ModalTitle } from "@/shared/components/ui/Modal";
import { messageOf, valueLabel } from "../../../lib/testing";
import { testingApi } from "../../../services/testing.service";
import SearchField from "@/shared/components/ui/SearchField";

const PAGE_SIZE = 50;
const SUITE_TYPES = [
  "smoke",
  "regression",
  "sanity",
  "feature",
  "api",
  "ui",
  "integration",
  "custom",
];

function optionFor(item) {
  const versionId = item.current_version_id;
  if (!versionId) return null;
  return {
    value: versionId,
    label: `${item.test_case_key || "Ca kiểm thử"} · ${item.current_version?.title || "Không có tiêu đề"}`,
    fallback: false,
  };
}

function optionForVersion(version) {
  if (!version?._id || !version.title) return null;
  return {
    value: version._id,
    label: `${version.test_case_key || "Ca kiểm thử"} · ${version.title}`,
    fallback: false,
  };
}

export default function TestSetEditorModal({ projectId, mode, suite, onClose, onSubmit }) {
  const editing = mode === "edit";
  const initialVersionIds = suite?.test_case_version_ids || [];
  const [name, setName] = useState(suite?.name || "");
  const [suiteType, setSuiteType] = useState(suite?.suite_type || "");
  const [query, setQuery] = useState("");
  const [appliedQuery, setAppliedQuery] = useState("");
  const [page, setPage] = useState(1);
  const [pageInfo, setPageInfo] = useState(null);
  const [cases, setCases] = useState([]);
  const [selection, setSelection] = useState(() =>
    Object.fromEntries(
      initialVersionIds.map((versionId, index) => [
        versionId,
        {
          value: versionId,
          label: `Ca đã lưu, mục ${index + 1} · chưa tải được thông tin`,
          fallback: true,
        },
      ]),
    ),
  );
  const [loading, setLoading] = useState(true);
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState("");
  const [reloadToken, setReloadToken] = useState(0);
  const requestSequence = useRef(0);
  const attemptedVersionIds = useRef(new Set());
  const mounted = useRef(true);
  const selectedIds = Object.keys(selection);

  useEffect(() => {
    mounted.current = true;
    return () => {
      mounted.current = false;
    };
  }, []);

  useEffect(() => {
    let active = true;
    const requestId = ++requestSequence.current;
    setLoading(true);
    setError("");
    testingApi
      .listTestCasePage(projectId, { q: appliedQuery, page, page_size: PAGE_SIZE })
      .then((result) => {
        if (!active || requestSequence.current !== requestId) return;
        const items = result.items || [];
        setCases(items);
        setPageInfo(result);
        setSelection((current) => {
          const next = { ...current };
          for (const item of items) {
            const option = optionFor(item);
            if (option && Object.hasOwn(next, option.value)) next[option.value] = option;
          }
          return next;
        });
      })
      .catch((reason) => {
        if (!active || requestSequence.current !== requestId) return;
        setError(messageOf(reason));
      })
      .finally(() => {
        if (active && requestSequence.current === requestId) setLoading(false);
      });
    return () => {
      active = false;
      requestSequence.current += 1;
    };
  }, [appliedQuery, page, projectId, reloadToken]);

  useEffect(() => {
    const unresolvedIds = Object.values(selection)
      .filter((option) => option.fallback && !attemptedVersionIds.current.has(option.value))
      .map((option) => option.value);
    if (!unresolvedIds.length) return;

    for (const versionId of unresolvedIds) attemptedVersionIds.current.add(versionId);
    const resolveHistoricalLabels = async () => {
      for (let offset = 0; offset < unresolvedIds.length; offset += 8) {
        const results = await Promise.all(
          unresolvedIds.slice(offset, offset + 8).map(async (versionId) => {
            try {
              const version = await testingApi.getTestCaseVersion(versionId);
              if (version?.project_id !== projectId) return null;
              const option = optionForVersion(version);
              return option ? [versionId, option] : null;
            } catch {
              return null;
            }
          }),
        );
        if (!mounted.current) return;
        const resolved = results.filter(Boolean);
        if (!resolved.length) continue;
        setSelection((current) => {
          const next = { ...current };
          for (const [versionId, option] of resolved) {
            if (next[versionId]?.fallback) next[versionId] = option;
          }
          return next;
        });
      }
    };
    void resolveHistoricalLabels();
  }, [projectId, selection]);

  const applySearch = () => {
    setPage(1);
    setAppliedQuery(query.trim());
  };

  const toggleVersion = (option) => {
    setSelection((current) => {
      const next = { ...current };
      if (Object.hasOwn(next, option.value)) delete next[option.value];
      else next[option.value] = option;
      return next;
    });
  };

  const submit = async (event) => {
    event.preventDefault();
    if (saving) return;
    setSaving(true);
    setError("");
    try {
      await onSubmit({ name, suiteType, versionIds: selectedIds });
    } catch (reason) {
      setError(messageOf(reason));
    } finally {
      setSaving(false);
    }
  };

  const totalPages = Math.max(1, pageInfo?.total_pages || 1);
  const selected = Object.values(selection);

  return (
    <Modal
      isOpen
      onClose={() => {
        if (!saving) onClose();
      }}
      ariaLabel={editing ? "Cập nhật bộ kiểm thử" : "Tạo bộ kiểm thử"}
      placement="right"
      className="flex flex-col"
    >
      <ModalHeader>
        <ModalTitle>{editing ? "Cập nhật bộ kiểm thử" : "Tạo bộ kiểm thử"}</ModalTitle>
        <p className="mt-2 text-sm text-ink-muted">
          Chọn các phiên bản ca kiểm thử bằng tìm kiếm và phân trang. Các phiên bản đã chọn được giữ
          nguyên khi chuyển trang
        </p>
      </ModalHeader>
      <form className="flex min-h-0 flex-1 flex-col" onSubmit={submit}>
        <div className="min-h-0 flex-1 space-y-5 overflow-y-auto overscroll-contain p-5 sm:p-6">
          {error && (
            <div
              className="rounded-control border border-danger/30 bg-danger/5 p-3 text-sm text-danger"
              role="alert"
            >
              {error}
            </div>
          )}
          <section aria-label="Thông tin bộ kiểm thử" className="grid gap-4 md:grid-cols-2">
            <label className="field-label">
              Tên bộ kiểm thử
              <input
                className="apple-input mt-2 w-full"
                autoFocus
                required
                minLength={2}
                maxLength={300}
                value={name}
                onChange={(event) => setName(event.target.value)}
              />
            </label>
            <label className="field-label">
              Loại bộ kiểm thử
              <select
                className="apple-input mt-2 w-full"
                value={suiteType}
                onChange={(event) => setSuiteType(event.target.value)}
              >
                <option value="">Chưa phân loại</option>
                {SUITE_TYPES.map((value) => (
                  <option key={value} value={value}>
                    {valueLabel(value)}
                  </option>
                ))}
              </select>
            </label>
          </section>

          <div className="grid min-w-0 gap-4 xl:grid-cols-[minmax(0,1fr)_19rem]">
            <section
              className="min-w-0 space-y-3 rounded-control border border-border p-4"
              aria-label="Chọn ca kiểm thử"
            >
              <div>
                <h3 className="font-semibold">Ca kiểm thử</h3>
                <p className="mt-1 text-sm text-ink-muted">
                  Chọn phiên bản ca cần đưa vào bộ kiểm thử
                </p>
              </div>
              <div className="flex flex-wrap gap-2">
                <SearchField
                  ariaLabel="Tìm ca kiểm thử"
                  className="min-w-0 flex-1"
                  onChange={(event) => setQuery(event.target.value)}
                  onKeyDown={(event) => {
                    if (event.key === "Enter") {
                      event.preventDefault();
                      applySearch();
                    }
                  }}
                  placeholder="Tìm theo mã hoặc tên"
                  type="search"
                  value={query}
                />
                <button className="secondary-button" type="button" onClick={applySearch}>
                  Tìm
                </button>
              </div>
              {loading ? (
                <div className="grid gap-2" role="status" aria-label="Đang tải ca kiểm thử">
                  {[0, 1, 2, 3].map((item) => (
                    <div aria-hidden="true" className="skeleton h-12 w-full" key={item} />
                  ))}
                </div>
              ) : error ? (
                <button
                  className="secondary-button"
                  type="button"
                  onClick={() => setReloadToken((current) => current + 1)}
                >
                  Thử tải danh sách lại
                </button>
              ) : (
                <>
                  <div className="max-h-[52vh] space-y-1 overflow-y-auto rounded-control border border-border p-2">
                    {cases.map((item) => {
                      const option = optionFor(item);
                      if (!option) return null;
                      return (
                        <label
                          key={option.value}
                          className="flex min-h-10 cursor-pointer items-start gap-3 rounded-control px-2 py-2 text-sm hover:bg-surface-quiet"
                        >
                          <input
                            className="mt-1 shrink-0"
                            type="checkbox"
                            checked={selectedIds.includes(option.value)}
                            onChange={() => toggleVersion(option)}
                          />
                          <span className="min-w-0 break-words">{option.label}</span>
                        </label>
                      );
                    })}
                    {!cases.length && (
                      <p className="px-2 py-3 text-sm text-ink-muted">
                        {appliedQuery
                          ? "Không tìm thấy ca kiểm thử phù hợp với từ khóa"
                          : "Chưa có ca kiểm thử để thêm vào bộ này"}
                      </p>
                    )}
                  </div>
                  <div className="flex flex-wrap items-center justify-between gap-2 text-sm">
                    <span className="text-ink-muted">
                      {pageInfo?.total || 0} ca · trang {page} / {totalPages}
                    </span>
                    <div className="flex gap-2">
                      <button
                        aria-label="Trang trước"
                        title="Trang trước"
                        className="icon-button h-9 w-9"
                        type="button"
                        disabled={loading || page <= 1}
                        onClick={() => setPage((current) => current - 1)}
                      >
                        <ChevronLeft aria-hidden="true" size={16} />
                      </button>
                      <button
                        aria-label="Trang sau"
                        title="Trang sau"
                        className="icon-button h-9 w-9"
                        type="button"
                        disabled={loading || page >= totalPages}
                        onClick={() => setPage((current) => current + 1)}
                      >
                        <ChevronRight aria-hidden="true" size={16} />
                      </button>
                    </div>
                  </div>
                </>
              )}
            </section>

            <aside className="min-w-0 rounded-control border border-border bg-surface-quiet/40 p-4 xl:sticky xl:top-2 xl:self-start">
              <div className="flex flex-wrap items-center justify-between gap-2">
                <h3 className="font-semibold">Phiên bản đã chọn</h3>
                <span
                  className="rounded-full bg-surface px-2.5 py-1 text-xs font-semibold tabular-nums text-ink-muted"
                  aria-live="polite"
                >
                  {selectedIds.length}
                </span>
              </div>
              {selected.length ? (
                <ul className="mt-3 grid max-h-[48vh] gap-2 overflow-y-auto">
                  {selected.map((option) => (
                    <li
                      key={option.value}
                      className="flex min-w-0 items-start gap-2 rounded-control border border-border bg-surface p-3 text-sm"
                    >
                      <span className="min-w-0 flex-1 break-words">{option.label}</span>
                      <button
                        className="shrink-0 rounded-control px-2 py-1 text-xs font-medium text-brand hover:bg-brand/5 hover:underline"
                        type="button"
                        aria-label={`Bỏ chọn ${option.label}`}
                        onClick={() => toggleVersion(option)}
                      >
                        Bỏ
                      </button>
                    </li>
                  ))}
                </ul>
              ) : (
                <p className="mt-3 rounded-control border border-dashed border-border bg-surface p-3 text-sm text-ink-muted">
                  Chưa chọn phiên bản ca nào
                </p>
              )}
            </aside>
          </div>
        </div>
        <ModalFooter>
          <button className="secondary-button" type="button" disabled={saving} onClick={onClose}>
            Hủy
          </button>
          <button className="primary-button" type="submit" disabled={saving || loading}>
            {saving ? "Đang lưu" : editing ? "Lưu thay đổi" : "Tạo bộ kiểm thử"}
          </button>
        </ModalFooter>
      </form>
    </Modal>
  );
}
