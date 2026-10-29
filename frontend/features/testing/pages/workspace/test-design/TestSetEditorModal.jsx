import { useEffect, useRef, useState } from "react";
import { Modal, ModalFooter, ModalHeader, ModalTitle } from "@/shared/components/ui/Modal";
import { messageOf, valueLabel } from "../../../lib/testing";
import { testingApi } from "../../../services/testing.service";

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
  const [suiteType, setSuiteType] = useState(suite?.suite_type || SUITE_TYPES[0]);
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
      className="max-w-3xl max-h-[90dvh] overflow-y-auto"
    >
      <ModalHeader>
        <ModalTitle>{editing ? "Cập nhật bộ kiểm thử" : "Tạo bộ kiểm thử"}</ModalTitle>
        <p className="mt-2 text-sm text-ink-muted">
          Chọn các phiên bản ca kiểm thử bằng tìm kiếm và phân trang. Các phiên bản đã chọn được giữ
          nguyên khi chuyển trang.
        </p>
      </ModalHeader>
      <form className="space-y-4 p-5" onSubmit={submit}>
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
            {SUITE_TYPES.map((value) => (
              <option key={value} value={value}>
                {valueLabel(value)}
              </option>
            ))}
          </select>
        </label>
        <section
          className="space-y-3 rounded-control border border-border p-4"
          aria-label="Chọn ca kiểm thử"
        >
          <div className="flex flex-wrap items-center justify-between gap-2">
            <h3 className="font-semibold">Ca kiểm thử</h3>
            <span className="text-sm text-ink-muted" aria-live="polite">
              Đã chọn {selectedIds.length}
            </span>
          </div>
          <div className="flex flex-wrap gap-2">
            <input
              className="apple-input min-w-0 flex-1"
              type="search"
              value={query}
              placeholder="Tìm ca kiểm thử theo mã hoặc tên"
              aria-label="Tìm ca kiểm thử"
              onChange={(event) => setQuery(event.target.value)}
              onKeyDown={(event) => {
                if (event.key === "Enter") {
                  event.preventDefault();
                  applySearch();
                }
              }}
            />
            <button className="secondary-button" type="button" onClick={applySearch}>
              Tìm
            </button>
          </div>
          {selected.length > 0 && (
            <div className="space-y-2 rounded-control bg-surface-quiet p-3">
              <p className="text-sm font-medium">Phiên bản đã chọn</p>
              <ul className="space-y-1">
                {selected.map((option) => (
                  <li
                    key={option.value}
                    className="flex min-w-0 items-start justify-between gap-2 text-sm"
                  >
                    <span className="min-w-0 break-words">{option.label}</span>
                    <button
                      className="shrink-0 text-brand hover:underline"
                      type="button"
                      aria-label={`Bỏ chọn ${option.label}`}
                      onClick={() => toggleVersion(option)}
                    >
                      Bỏ
                    </button>
                  </li>
                ))}
              </ul>
            </div>
          )}
          {loading ? (
            <p role="status" className="text-sm text-ink-muted">
              Đang tải ca kiểm thử…
            </p>
          ) : error ? (
            <div className="space-y-2" role="alert">
              <p className="text-sm text-danger">{error}</p>
              <button
                className="secondary-button"
                type="button"
                onClick={() => setReloadToken((current) => current + 1)}
              >
                Thử tải lại
              </button>
            </div>
          ) : (
            <>
              <div className="max-h-64 space-y-1 overflow-y-auto rounded-control border border-border p-2">
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
                      ? "Không tìm thấy ca kiểm thử phù hợp với từ khóa."
                      : "Chưa có ca kiểm thử để thêm vào bộ này."}
                  </p>
                )}
              </div>
              <div className="flex flex-wrap items-center justify-between gap-2 text-sm">
                <span className="text-ink-muted">
                  {pageInfo?.total || 0} ca · trang {page} / {totalPages}
                </span>
                <div className="flex gap-2">
                  <button
                    className="secondary-button"
                    type="button"
                    disabled={loading || page <= 1}
                    onClick={() => setPage((current) => current - 1)}
                  >
                    Trang trước
                  </button>
                  <button
                    className="secondary-button"
                    type="button"
                    disabled={loading || page >= totalPages}
                    onClick={() => setPage((current) => current + 1)}
                  >
                    Trang sau
                  </button>
                </div>
              </div>
            </>
          )}
        </section>
        <ModalFooter className="-mx-5 -mb-5">
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
