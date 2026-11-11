"use client";
import { useDateTimeOptions } from "../../hooks/useDateTimeOptions";
import { useCallback, useEffect, useMemo, useRef, useState } from "react";
import Link from "next/link";
import { Check, ChevronLeft, ChevronRight, RotateCcw, X } from "lucide-react";
import {
  ErrorState,
  InitialLoadState,
  Metric,
  Panel,
  ProjectCrumb,
  WorkspacePage,
  StatusPill,
  useActionDialog,
} from "../../components/WorkspacePrimitives";
import { testingApi } from "../../services/testing.service";
import { formatDate as formatDateValue, messageOf, valueLabel } from "../../lib/testing";
import { Modal, ModalHeader, ModalTitle } from "@/shared/components/ui/Modal";
import SearchField from "@/shared/components/ui/SearchField";
import { formatNumber } from "@/shared/lib/locale.mjs";

const PAGE_SIZE = 25;

function displayMetric(value, suffix = "") {
  return value === null || value === undefined ? "—" : `${value}${suffix}`;
}

function displayRate(value, denominator) {
  return value === null || value === undefined || !denominator ? "—" : `${value}%`;
}

function linkStateLabel(status, obsolete) {
  if (obsolete) return "Cần kiểm tra lại";
  return (
    {
      CONFIRMED: "Đã xác nhận",
      SUGGESTED: "Chờ rà soát",
      REJECTED: "Đã từ chối",
      REVOKED: "Đã thu hồi",
    }[status] || valueLabel(status)
  );
}

function relationshipLabel(type) {
  return (
    {
      verifies: "Xác minh",
      covers: "Bao phủ",
      derived_from: "Phát sinh từ",
      relates_to: "Có liên quan",
    }[type] || valueLabel(type)
  );
}

function linkOriginLabel(origin) {
  return (
    {
      manual: "Thủ công",
      ai_suggested: "AI đề xuất",
      import: "Nhập dữ liệu",
      trace_recovery: "Khôi phục liên kết",
    }[origin] || valueLabel(origin)
  );
}

export default function TraceabilityPage({ project }) {
  const dateTimeOptions = useDateTimeOptions(project);
  const formatDate = (value) => formatDateValue(value, dateTimeOptions);
  const { ask, dialog } = useActionDialog();
  const [matrix, setMatrix] = useState({ trace_links: [], requirements: [], test_cases: [] });
  const [coverage, setCoverage] = useState(null);
  const [snapshots, setSnapshots] = useState([]);
  const [linkForm, setLinkForm] = useState({ source_id: "", target_id: "" });
  const [query, setQuery] = useState("");
  const [statusFilter, setStatusFilter] = useState("ALL");
  const [activeLinkId, setActiveLinkId] = useState("");
  const [page, setPage] = useState(0);
  const [error, setError] = useState("");
  const [linkError, setLinkError] = useState("");
  const [creating, setCreating] = useState(false);
  const [busyLinkId, setBusyLinkId] = useState("");
  const [initialLoading, setInitialLoading] = useState(true);
  const [initialLoadFailed, setInitialLoadFailed] = useState(false);
  const initialDataLoaded = useRef(false);
  const loadedProjectId = useRef(project._id);
  const permissions = useMemo(
    () => project.current_permissions || [],
    [project.current_permissions],
  );
  const can = useCallback((permission) => permissions.includes(permission), [permissions]);
  const load = useCallback(async () => {
    if (!can("trace.read")) {
      setInitialLoading(false);
      return;
    }
    if (loadedProjectId.current !== project._id) {
      loadedProjectId.current = project._id;
      initialDataLoaded.current = false;
      setInitialLoading(true);
    }
    setError("");
    try {
      const [traceValue, coverageValue, snapshotValues] = await Promise.all([
        testingApi.traceability(project._id),
        can("coverage.read") ? testingApi.coverage(project._id) : Promise.resolve(null),
        can("coverage.read") ? testingApi.listCoverageSnapshots(project._id) : Promise.resolve([]),
      ]);
      setMatrix(traceValue);
      setCoverage(coverageValue);
      setSnapshots(snapshotValues);
      setActiveLinkId((current) =>
        traceValue.trace_links?.some((item) => item._id === current)
          ? current
          : (traceValue.trace_links?.[0]?._id ?? ""),
      );
      initialDataLoaded.current = true;
      setInitialLoadFailed(false);
    } catch (reason) {
      setError(messageOf(reason));
      if (!initialDataLoaded.current) setInitialLoadFailed(true);
    } finally {
      setInitialLoading(false);
    }
  }, [can, project._id]);
  useEffect(() => {
    void load();
  }, [load]);

  const requirementsByVersion = useMemo(
    () => new Map((matrix.requirement_versions || []).map((item) => [item._id, item])),
    [matrix.requirement_versions],
  );
  const requirementRecordsById = useMemo(
    () => new Map((matrix.requirements || []).map((item) => [item._id, item])),
    [matrix.requirements],
  );
  const casesByVersion = useMemo(() => {
    const records = new Map((matrix.test_cases || []).map((item) => [item._id, item]));
    return new Map(
      (matrix.test_case_versions || []).map((item) => [
        item._id,
        records.get(item.test_case_id) || null,
      ]),
    );
  }, [matrix.test_cases, matrix.test_case_versions]);
  const baselineRequirementVersionIds = useMemo(
    () =>
      new Set(
        (matrix.requirements || [])
          .filter((item) => item.status === "BASELINED" && item.current_version_id)
          .map((item) => item.current_version_id),
      ),
    [matrix.requirements],
  );
  const baselineCriteriaCount = (matrix.acceptance_criteria || []).filter(
    (item) =>
      baselineRequirementVersionIds.has(item.requirement_version_id) &&
      String(item.status || "").toLowerCase() !== "obsolete",
  ).length;
  const executionScopeCount = coverage?.scope?.test_case_version_ids?.length;
  const filteredLinks = useMemo(() => {
    const normalized = query.trim().toLocaleLowerCase();
    return (matrix.trace_links || []).filter((item) => {
      const state = item.obsolete ? "OBSOLETE" : item.status;
      const statusMatches = statusFilter === "ALL" || state === statusFilter;
      if (!statusMatches) return false;
      if (!normalized) return true;
      const source = `${item.source_label || ""} ${item.evidence?.map((entry) => entry.text || "").join(" ") || ""}`;
      const target = item.target_label || "";
      return `${source} ${target} ${item.link_type || ""}`.toLocaleLowerCase().includes(normalized);
    });
  }, [matrix.trace_links, query, statusFilter]);
  const pageCount = Math.max(1, Math.ceil(filteredLinks.length / PAGE_SIZE));
  const visibleLinks = filteredLinks.slice(page * PAGE_SIZE, (page + 1) * PAGE_SIZE);
  const activeLink =
    filteredLinks.find((item) => item._id === activeLinkId) || visibleLinks[0] || null;
  const activeSource = activeLink ? requirementsByVersion.get(activeLink.source_id) : null;
  const activeTarget = activeLink
    ? (matrix.test_case_versions || []).find((item) => item._id === activeLink.target_id)
    : null;
  const activeRequirement = activeSource
    ? requirementRecordsById.get(activeSource.requirement_id)
    : null;
  const activeCase = activeLink ? casesByVersion.get(activeLink.target_id) : null;
  const activeExecution = activeLink ? coverage?.latest_execution?.[activeLink.target_id] : null;
  const activeDefects = activeLink
    ? (matrix.defects || []).filter(
        (item) => item.linked_test_case_version_id === activeLink.target_id,
      )
    : [];
  const unlinkedRequirements = (coverage?.uncovered_requirements || []).map((item) => ({
    ...item,
    version: requirementsByVersion.get(item.current_version_id),
  }));

  if (!can("trace.read")) return null;
  if (initialLoading || initialLoadFailed)
    return (
      <InitialLoadState
        title="Truy vết"
        projectId={project._id}
        loading={initialLoading}
        error={error}
        onRetry={() => void load()}
      />
    );

  const performDecision = async (item, action) => {
    setBusyLinkId(item._id);
    setError("");
    try {
      if (action === "confirm") await testingApi.confirmTrace(item._id);
      if (action === "reject") await testingApi.rejectTrace(item._id);
      if (action === "revoke") await testingApi.revokeTrace(item._id);
      await load();
    } catch (reason) {
      setError(messageOf(reason));
    } finally {
      setBusyLinkId("");
    }
  };

  const linkActions = (item) => {
    if (item.status === "SUGGESTED" && (can("trace.confirm") || can("trace.review")))
      return (
        <div className="flex items-center gap-2">
          {can("trace.confirm") && (
            <button
              aria-label="Xác nhận liên kết"
              className="icon-button h-9 w-9"
              disabled={busyLinkId === item._id}
              title="Xác nhận liên kết"
              type="button"
              onClick={(event) => {
                event.stopPropagation();
                void performDecision(item, "confirm");
              }}
            >
              <Check aria-hidden="true" size={16} />
            </button>
          )}
          {can("trace.review") && (
            <button
              aria-label="Từ chối liên kết"
              className="icon-button h-9 w-9"
              disabled={busyLinkId === item._id}
              title="Từ chối liên kết"
              type="button"
              onClick={(event) => {
                event.stopPropagation();
                void performDecision(item, "reject");
              }}
            >
              <X aria-hidden="true" size={16} />
            </button>
          )}
        </div>
      );
    if (item.status === "CONFIRMED" && can("trace.revoke"))
      return (
        <button
          aria-label="Thu hồi liên kết"
          className="icon-button h-9 w-9"
          disabled={busyLinkId === item._id}
          title="Thu hồi liên kết"
          type="button"
          onClick={(event) => {
            event.stopPropagation();
            void performDecision(item, "revoke");
          }}
        >
          <RotateCcw aria-hidden="true" size={16} />
        </button>
      );
    return null;
  };

  return (
    <WorkspacePage
      title="Truy vết"
      actions={
        <div className="flex flex-wrap items-center gap-2">
          {can("report.export") && (
            <button
              className="secondary-button"
              type="button"
              onClick={() =>
                testingApi
                  .exportTraceability(project._id)
                  .catch((reason) => setError(messageOf(reason)))
              }
            >
              Xuất CSV
            </button>
          )}
          {can("trace.recover") && (
            <button
              className="secondary-button"
              type="button"
              onClick={async () => {
                setError("");
                try {
                  await testingApi.recoverTrace(project._id);
                  await load();
                } catch (reason) {
                  setError(messageOf(reason));
                }
              }}
            >
              Tìm liên kết bị thiếu
            </button>
          )}
          {can("coverage.snapshot.create") && (
            <button
              className="secondary-button"
              type="button"
              onClick={() =>
                void ask({
                  title: "Lưu mốc độ phủ",
                  description: "Lưu các chỉ số hiện tại để đối chiếu về sau.",
                  confirmLabel: "Lưu mốc độ phủ",
                  fields: [
                    {
                      name: "label",
                      label: "Tên mốc độ phủ",
                      initialValue: "Độ phủ hiện tại",
                      required: true,
                      autoFocus: true,
                    },
                  ],
                  onConfirm: async (answer) => {
                    try {
                      await testingApi.createCoverageSnapshot(project._id, {
                        label: answer.label,
                        idempotency_key: crypto.randomUUID(),
                      });
                      await load();
                    } catch (reason) {
                      throw new Error(messageOf(reason));
                    }
                  },
                })
              }
            >
              Lưu mốc độ phủ
            </button>
          )}
          {can("trace.create") && (
            <button
              className="apple-button"
              type="button"
              onClick={() => {
                setLinkError("");
                setCreating(true);
              }}
            >
              Tạo liên kết
            </button>
          )}
          <ProjectCrumb projectId={project._id} />
        </div>
      }
    >
      {error && (
        <div className="flex flex-wrap items-center justify-between gap-3">
          <div className="min-w-0 flex-1">
            <ErrorState message={error} />
          </div>
          <button className="secondary-button shrink-0" type="button" onClick={() => void load()}>
            Tải lại
          </button>
        </div>
      )}

      {can("coverage.read") && coverage && (
        <div className="grid grid-cols-2 gap-3 xl:grid-cols-4">
          <Metric
            label="Yêu cầu đã liên kết"
            value={displayRate(coverage.requirement_coverage, baselineRequirementVersionIds.size)}
          />
          <Metric
            label="Tiêu chí đã liên kết"
            value={displayRate(coverage.acceptance_criterion_coverage, baselineCriteriaCount)}
          />
          <Metric
            label="Liên kết còn hiệu lực"
            value={displayRate(coverage.fresh_coverage, baselineRequirementVersionIds.size)}
          />
          <Metric
            label="Ca kiểm thử đã thực thi"
            value={displayRate(coverage.execution_coverage, executionScopeCount)}
          />
        </div>
      )}

      {can("trace.create") && (
        <Modal
          isOpen={creating}
          onClose={() => setCreating(false)}
          ariaLabel="Tạo liên kết yêu cầu và ca kiểm thử"
          className="max-w-2xl"
        >
          <ModalHeader>
            <ModalTitle>Tạo liên kết yêu cầu và ca kiểm thử</ModalTitle>
          </ModalHeader>
          {linkError && (
            <div className="px-5 pt-4 text-sm text-danger" role="alert">
              {linkError}
            </div>
          )}
          <form
            className="grid min-w-0 gap-4 p-5 md:grid-cols-2"
            onSubmit={async (event) => {
              event.preventDefault();
              try {
                await testingApi.createTrace({
                  project_id: project._id,
                  source_type: "requirement_version",
                  source_id: linkForm.source_id,
                  target_type: "test_case_version",
                  target_id: linkForm.target_id,
                  link_type: "verifies",
                  confidence: 1,
                  origin: "manual",
                  evidence: [],
                });
                setLinkForm({ source_id: "", target_id: "" });
                setCreating(false);
                setLinkError("");
                await load();
              } catch (reason) {
                setLinkError(messageOf(reason));
              }
            }}
          >
            <label className="grid gap-2 text-sm font-medium">
              Yêu cầu
              <select
                className="apple-input min-w-0 w-full"
                required
                value={linkForm.source_id}
                onChange={(event) => setLinkForm({ ...linkForm, source_id: event.target.value })}
              >
                <option value="">Chọn phiên bản yêu cầu</option>
                {(matrix.requirement_versions || []).map((item) => (
                  <option key={item._id} value={item._id}>
                    {item.requirement_key} v{item.version} {item.title}
                  </option>
                ))}
              </select>
            </label>
            <label className="grid gap-2 text-sm font-medium">
              Ca kiểm thử
              <select
                className="apple-input min-w-0 w-full"
                required
                value={linkForm.target_id}
                onChange={(event) => setLinkForm({ ...linkForm, target_id: event.target.value })}
              >
                <option value="">Chọn phiên bản ca kiểm thử</option>
                {(matrix.test_case_versions || []).map((item) => (
                  <option key={item._id} value={item._id}>
                    {item.test_case_key} v{item.version} {item.title}
                  </option>
                ))}
              </select>
            </label>
            <div className="flex justify-end gap-3 md:col-span-2">
              <button className="secondary-button" type="button" onClick={() => setCreating(false)}>
                Hủy
              </button>
              <button className="apple-button" type="submit">
                Tạo liên kết
              </button>
            </div>
          </form>
        </Modal>
      )}

      <Panel
        title="Liên kết yêu cầu với ca kiểm thử"
        description={`${formatNumber(filteredLinks.length, dateTimeOptions.locale, { maximumFractionDigits: 0 })} liên kết phù hợp`}
        actions={
          <div className="grid w-full min-w-0 gap-2 sm:grid-cols-[minmax(220px,1fr)_210px]">
            <SearchField
              ariaLabel="Tìm liên kết"
              onChange={(event) => {
                setQuery(event.target.value);
                setPage(0);
              }}
              placeholder="Tìm mã hoặc nội dung"
              type="search"
              value={query}
            />
            <label className="sr-only" htmlFor="trace-status-filter">
              Lọc trạng thái liên kết
            </label>
            <select
              id="trace-status-filter"
              className="apple-input w-full"
              value={statusFilter}
              onChange={(event) => {
                setStatusFilter(event.target.value);
                setPage(0);
              }}
            >
              <option value="ALL">Mọi trạng thái</option>
              <option value="CONFIRMED">Đã xác nhận</option>
              <option value="SUGGESTED">Chờ rà soát</option>
              <option value="OBSOLETE">Cần kiểm tra lại</option>
              <option value="REJECTED">Đã từ chối</option>
              <option value="REVOKED">Đã thu hồi</option>
            </select>
          </div>
        }
      >
        {(matrix.trace_links || []).length === 0 ? (
          <div className="px-5 py-10 text-center">
            <p className="font-semibold">Chưa có liên kết truy vết</p>
            <p className="mt-2 text-sm text-ink-muted">
              Tạo liên kết giữa yêu cầu và ca kiểm thử để theo dõi độ phủ.
            </p>
            {can("trace.create") && (
              <button className="apple-button mt-4" type="button" onClick={() => setCreating(true)}>
                Tạo liên kết
              </button>
            )}
          </div>
        ) : filteredLinks.length === 0 ? (
          <div className="px-5 py-10 text-center">
            <p className="font-semibold">Không tìm thấy liên kết phù hợp</p>
            <button
              className="secondary-button mt-4"
              type="button"
              onClick={() => {
                setQuery("");
                setStatusFilter("ALL");
              }}
            >
              Xóa bộ lọc
            </button>
          </div>
        ) : (
          <div className="grid min-w-0 xl:grid-cols-[minmax(0,1.35fr)_minmax(300px,0.85fr)]">
            <div className="min-w-0 border-b border-border xl:border-b-0 xl:border-r">
              <div className="divide-y divide-border">
                {visibleLinks.map((item) => {
                  const selected = activeLink?._id === item._id;
                  return (
                    <button
                      key={item._id}
                      aria-pressed={selected}
                      className={`grid w-full min-w-0 gap-3 px-4 py-4 text-left transition hover:bg-surface-quiet sm:px-5 md:grid-cols-[minmax(0,1fr)_auto] md:items-center ${selected ? "bg-brand-soft/40" : ""}`}
                      type="button"
                      onClick={() => setActiveLinkId(item._id)}
                    >
                      <span className="grid min-w-0 gap-2 sm:grid-cols-[minmax(0,1fr)_24px_minmax(0,1fr)] sm:items-center sm:gap-3">
                        <span className="min-w-0">
                          <span className="block text-[11px] font-semibold uppercase tracking-wide text-ink-muted">
                            Yêu cầu
                          </span>
                          <span className="mt-1 block break-words text-sm font-semibold leading-5">
                            {item.source_label || "Yêu cầu không còn khả dụng"}
                          </span>
                        </span>
                        <span
                          aria-hidden="true"
                          className="hidden text-center text-ink-faint sm:block"
                        >
                          →
                        </span>
                        <span className="min-w-0">
                          <span className="block text-[11px] font-semibold uppercase tracking-wide text-ink-muted">
                            Ca kiểm thử
                          </span>
                          <span className="mt-1 block break-words text-sm font-semibold leading-5">
                            {item.target_label || "Ca kiểm thử không còn khả dụng"}
                          </span>
                        </span>
                      </span>
                      <span className="flex min-w-0 items-center justify-between gap-3 md:justify-end">
                        <StatusPill value={linkStateLabel(item.status, item.obsolete)} />
                        <span className="whitespace-nowrap text-xs text-ink-muted">
                          {typeof item.confidence === "number"
                            ? `${Math.round(item.confidence * 100)}% phù hợp`
                            : "Chưa đánh giá"}
                        </span>
                      </span>
                    </button>
                  );
                })}
              </div>
              {pageCount > 1 && (
                <div className="flex items-center justify-between gap-3 border-t border-border px-4 py-3 sm:px-5">
                  <span className="text-xs text-ink-muted">
                    {page * PAGE_SIZE + 1}–{Math.min((page + 1) * PAGE_SIZE, filteredLinks.length)}{" "}
                    / {filteredLinks.length}
                  </span>
                  <div className="flex gap-2">
                    <button
                      aria-label="Trang trước"
                      className="icon-button h-9 w-9"
                      disabled={page === 0}
                      type="button"
                      onClick={() => setPage((value) => Math.max(0, value - 1))}
                    >
                      <ChevronLeft aria-hidden="true" size={17} />
                    </button>
                    <button
                      aria-label="Trang sau"
                      className="icon-button h-9 w-9"
                      disabled={page + 1 >= pageCount}
                      type="button"
                      onClick={() => setPage((value) => Math.min(pageCount - 1, value + 1))}
                    >
                      <ChevronRight aria-hidden="true" size={17} />
                    </button>
                  </div>
                </div>
              )}
            </div>

            <aside className="min-w-0 p-4 sm:p-5" aria-label="Chi tiết liên kết">
              {activeLink ? (
                <div className="space-y-5">
                  <div className="flex flex-wrap items-start justify-between gap-3">
                    <div className="min-w-0">
                      <p className="text-[11px] font-semibold uppercase tracking-wide text-ink-muted">
                        Chi tiết liên kết
                      </p>
                      <h3 className="mt-1 break-words text-lg font-semibold">
                        {relationshipLabel(activeLink.link_type)}
                      </h3>
                    </div>
                    <StatusPill value={linkStateLabel(activeLink.status, activeLink.obsolete)} />
                  </div>

                  <div className="divide-y divide-border">
                    <div className="py-3 first:pt-0">
                      <p className="text-[11px] font-semibold uppercase tracking-wide text-ink-muted">
                        Yêu cầu
                      </p>
                      <p className="mt-1 break-words text-sm font-medium">
                        {activeLink.source_label || "Yêu cầu không còn khả dụng"}
                      </p>
                      {activeSource?.version && (
                        <p className="mt-1 text-xs text-ink-muted">
                          Phiên bản {activeSource.version}
                        </p>
                      )}
                      {activeRequirement?._id && (
                        <Link
                          className="mt-2 inline-flex text-sm font-semibold text-brand hover:underline"
                          href={`/du-an/${project._id}/yeu-cau/${activeRequirement._id}`}
                        >
                          Mở yêu cầu
                        </Link>
                      )}
                    </div>
                    <div className="py-3">
                      <p className="text-[11px] font-semibold uppercase tracking-wide text-ink-muted">
                        Ca kiểm thử
                      </p>
                      <p className="mt-1 break-words text-sm font-medium">
                        {activeLink.target_label || "Ca kiểm thử không còn khả dụng"}
                      </p>
                      {activeTarget?.version && (
                        <p className="mt-1 text-xs text-ink-muted">
                          Phiên bản {activeTarget.version}
                        </p>
                      )}
                      {activeCase?._id && (
                        <Link
                          className="mt-2 inline-flex text-sm font-semibold text-brand hover:underline"
                          href={`/du-an/${project._id}/ca-kiem-thu?case=${encodeURIComponent(activeCase._id)}`}
                        >
                          Mở ca kiểm thử
                        </Link>
                      )}
                    </div>
                  </div>

                  <dl className="grid grid-cols-2 gap-x-4 gap-y-3 border-y border-border py-4 text-sm">
                    <dt className="text-ink-muted">Độ phù hợp</dt>
                    <dd className="text-right font-medium">
                      {typeof activeLink.confidence === "number"
                        ? `${Math.round(activeLink.confidence * 100)}%`
                        : "Chưa đánh giá"}
                    </dd>
                    <dt className="text-ink-muted">Nguồn liên kết</dt>
                    <dd className="text-right font-medium">{linkOriginLabel(activeLink.origin)}</dd>
                    <dt className="text-ink-muted">Kết quả gần nhất</dt>
                    <dd className="text-right">
                      {activeExecution ? (
                        <StatusPill value={activeExecution.status} />
                      ) : (
                        "Chưa chạy"
                      )}
                    </dd>
                    <dt className="text-ink-muted">Lỗi đang mở</dt>
                    <dd className="text-right font-medium">{activeDefects.length}</dd>
                  </dl>

                  {activeLink.obsolete && (
                    <p
                      className="rounded-lg bg-warning-soft p-3 text-sm text-warning"
                      role="status"
                    >
                      Phiên bản nguồn hoặc ca kiểm thử đã cũ. Hãy rà soát liên kết trước khi dùng
                      làm căn cứ.
                    </p>
                  )}
                  {activeLink.evidence?.some((item) => item.text) && (
                    <details>
                      <summary className="cursor-pointer text-sm font-semibold">
                        Căn cứ liên kết
                        <span className="ml-2 font-normal text-ink-muted">
                          {activeLink.evidence.filter((item) => item.text).length}
                        </span>
                      </summary>
                      <ul className="mt-2 space-y-2">
                        {activeLink.evidence
                          .filter((item) => item.text)
                          .map((item, index) => (
                            <li
                              key={`${item.artifact_version_id || "evidence"}-${index}`}
                              className="border-l-2 border-border pl-3 text-sm leading-6 text-ink-muted"
                            >
                              {item.text}
                            </li>
                          ))}
                      </ul>
                    </details>
                  )}
                  {linkActions(activeLink) && (
                    <div className="flex items-center gap-2 border-t border-border pt-4">
                      <span className="mr-auto text-sm font-semibold">Xử lý liên kết</span>
                      {linkActions(activeLink)}
                    </div>
                  )}
                </div>
              ) : (
                <p className="py-8 text-center text-sm text-ink-muted">
                  Chọn một liên kết để xem chi tiết.
                </p>
              )}
            </aside>
          </div>
        )}
      </Panel>

      {can("coverage.read") && coverage && (
        <Panel title="Cần bổ sung liên kết">
          <div className="grid min-w-0 lg:grid-cols-2">
            <section className="min-w-0 border-b border-border p-4 sm:p-5 lg:border-b-0 lg:border-r">
              <div className="flex items-baseline justify-between gap-3">
                <h3 className="font-semibold">Yêu cầu chưa có ca kiểm thử</h3>
                <span className="text-sm text-ink-muted">
                  {Array.isArray(coverage.uncovered_requirements)
                    ? unlinkedRequirements.length
                    : "—"}
                </span>
              </div>
              {!Array.isArray(coverage.uncovered_requirements) ? (
                <p className="mt-3 text-sm text-ink-muted">
                  Chưa có dữ liệu yêu cầu chưa liên kết.
                </p>
              ) : unlinkedRequirements.length ? (
                <ul className="mt-3 divide-y divide-border">
                  {unlinkedRequirements.slice(0, 8).map((item) => (
                    <li
                      key={item._id}
                      className="flex min-w-0 items-center justify-between gap-3 py-3"
                    >
                      <div className="min-w-0">
                        <p className="break-words text-sm font-medium">
                          {item.requirement_key || item.version?.requirement_key || "Yêu cầu"}
                          {item.version?.title ? ` · ${item.version.title}` : ""}
                        </p>
                        <p className="mt-1 text-xs text-ink-muted">{valueLabel(item.status)}</p>
                      </div>
                      {item._id && (
                        <Link
                          aria-label={`Mở yêu cầu ${item.requirement_key || ""}`}
                          className="secondary-button shrink-0"
                          href={`/du-an/${project._id}/yeu-cau/${item._id}`}
                        >
                          Mở
                        </Link>
                      )}
                    </li>
                  ))}
                </ul>
              ) : (
                <p className="mt-3 text-sm text-ink-muted">
                  Tất cả yêu cầu hiện hành đã có liên kết.
                </p>
              )}
              {unlinkedRequirements.length > 8 && (
                <p className="mt-2 text-xs text-ink-muted">
                  Còn {unlinkedRequirements.length - 8} yêu cầu khác trong báo cáo độ phủ.
                </p>
              )}
            </section>
            <section className="min-w-0 p-4 sm:p-5">
              <div className="flex items-baseline justify-between gap-3">
                <h3 className="font-semibold">Ca kiểm thử chưa liên kết</h3>
                <span className="text-sm text-ink-muted">
                  {Array.isArray(coverage.unlinked_tests) ? coverage.unlinked_tests.length : "—"}
                </span>
              </div>
              {!Array.isArray(coverage.unlinked_tests) ? (
                <p className="mt-3 text-sm text-ink-muted">
                  Chưa có dữ liệu ca kiểm thử chưa liên kết.
                </p>
              ) : coverage.unlinked_tests.length ? (
                <ul className="mt-3 divide-y divide-border">
                  {coverage.unlinked_tests.slice(0, 8).map((item) => (
                    <li
                      key={item._id}
                      className="flex min-w-0 items-center justify-between gap-3 py-3"
                    >
                      <div className="min-w-0">
                        <p className="break-words text-sm font-medium">
                          {item.test_case_key || item.title || "Ca kiểm thử"}
                        </p>
                        {item.title && item.test_case_key && (
                          <p className="mt-1 truncate text-xs text-ink-muted">{item.title}</p>
                        )}
                        <p className="mt-1 text-xs text-ink-muted">{valueLabel(item.status)}</p>
                      </div>
                      <Link
                        aria-label={`Mở ca kiểm thử ${item.test_case_key || ""}`}
                        className="secondary-button shrink-0"
                        href={`/du-an/${project._id}/ca-kiem-thu?case=${encodeURIComponent(item._id)}`}
                      >
                        Mở
                      </Link>
                    </li>
                  ))}
                </ul>
              ) : (
                <p className="mt-3 text-sm text-ink-muted">
                  Tất cả ca kiểm thử hiện hành đã được liên kết.
                </p>
              )}
              {(coverage.unlinked_tests?.length || 0) > 8 && (
                <p className="mt-2 text-xs text-ink-muted">
                  Còn {coverage.unlinked_tests.length - 8} ca kiểm thử khác trong báo cáo độ phủ.
                </p>
              )}
            </section>
          </div>
        </Panel>
      )}

      {can("coverage.read") && coverage && (
        <details className="workspace-panel min-w-0">
          <summary className="cursor-pointer list-inside px-5 py-4 font-semibold">
            Lịch sử mốc độ phủ
            <span className="ml-2 text-sm font-normal text-ink-muted">{snapshots.length}</span>
          </summary>
          <div className="border-t border-border">
            {snapshots.length ? (
              <div className="divide-y divide-border">
                {snapshots.map((item) => (
                  <div
                    key={item._id}
                    className="grid min-w-0 gap-3 px-5 py-4 sm:grid-cols-[minmax(0,1.3fr)_repeat(3,minmax(100px,0.7fr))] sm:items-center"
                  >
                    <div className="min-w-0">
                      <p className="break-words font-medium">{item.label || "Mốc độ phủ"}</p>
                      <p className="mt-1 text-xs text-ink-muted">{formatDate(item.created_at)}</p>
                    </div>
                    <p className="text-sm">
                      <span className="text-ink-muted">Yêu cầu </span>
                      {displayMetric(item.metrics?.requirement_coverage, "%")}
                    </p>
                    <p className="text-sm">
                      <span className="text-ink-muted">Còn hiệu lực </span>
                      {displayMetric(item.metrics?.fresh_coverage, "%")}
                    </p>
                    <p className="text-sm">
                      <span className="text-ink-muted">Thực thi </span>
                      {displayMetric(item.metrics?.execution_coverage, "%")}
                    </p>
                  </div>
                ))}
              </div>
            ) : (
              <p className="px-5 py-6 text-sm text-ink-muted">Chưa lưu mốc độ phủ nào.</p>
            )}
          </div>
        </details>
      )}
      {dialog}
    </WorkspacePage>
  );
}
