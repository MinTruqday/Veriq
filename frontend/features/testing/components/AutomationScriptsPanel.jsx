"use client";
import { useDateTimeOptions } from "../hooks/useDateTimeOptions";
import { useCallback, useEffect, useMemo, useRef, useState } from "react";
import Link from "next/link";
import { RefreshCw } from "lucide-react";
import {
  ErrorState,
  LoadingState,
  Panel,
  StatusPill,
  useActionDialog,
} from "./WorkspacePrimitives";
import SearchField from "@/shared/components/ui/SearchField";
import ContentOriginBadge from "../../../shared/components/common/ContentOriginBadge";
import { PROJECT_SECTION_SLUGS, projectRoute } from "../routes";
import { testingApi } from "../services/testing.service";
import { formatDate as formatDateValue, messageOf, valueLabel } from "../lib/testing";

function scriptFormatLabel(value, labels) {
  if (!value) return "";
  const normalized = String(value).toLowerCase();
  return labels[normalized] || valueLabel(value);
}

export default function AutomationScriptsPanel({ project }) {
  const dateTimeOptions = useDateTimeOptions(project);
  const formatDate = (value) => formatDateValue(value, dateTimeOptions);
  const { ask, dialog } = useActionDialog();
  const [items, setItems] = useState([]);
  const [selected, setSelected] = useState(null);
  const [filename, setFilename] = useState("");
  const [source, setSource] = useState("");
  const [query, setQuery] = useState("");
  const [error, setError] = useState("");
  const [draftDirty, setDraftDirtyState] = useState(false);
  const draftDirtyRef = useRef(false);
  const setDraftDirty = (value) => {
    draftDirtyRef.current = value;
    setDraftDirtyState(value);
  };
  const [loading, setLoading] = useState(true);
  const [busy, setBusy] = useState(false);
  const canUpdate = project.current_permissions?.includes("automation.script.update");
  const canApprove = project.current_permissions?.includes("automation.script.approve");
  const canExport = project.current_permissions?.includes("automation.script.export");
  const frameworkLabels = {
    cypress: "Cypress",
    playwright: "Playwright",
    selenium: "Selenium",
  };
  const languageLabels = {
    javascript: "JavaScript",
    python: "Python",
    typescript: "TypeScript",
  };
  const visibleItems = useMemo(() => {
    const normalizedQuery = query.trim().toLocaleLowerCase();
    if (!normalizedQuery) return items;
    return items.filter((item) =>
      [item.filename, item.test_case_key, item.framework, item.language]
        .filter(Boolean)
        .join(" ")
        .toLocaleLowerCase()
        .includes(normalizedQuery),
    );
  }, [items, query]);

  const load = useCallback(async () => {
    if (!canExport) return;
    setLoading(true);
    setError("");
    try {
      const values = await testingApi.listAutomationScriptDrafts(project._id);
      setItems(values);
      setError("");
      setSelected((current) => {
        const next = values.find((item) => item._id === current?._id) || null;
        if (next && !draftDirtyRef.current) {
          setFilename(next.filename);
          setSource(next.source);
        }
        return next;
      });
    } catch (reason) {
      setError(messageOf(reason));
    } finally {
      setLoading(false);
    }
  }, [canExport, project._id]);

  useEffect(() => {
    void load();
  }, [load]);

  const openDraft = async (item) => {
    if (draftDirty) {
      const answer = await ask({
        title: "Bỏ thay đổi chưa lưu?",
        description: "Nội dung đang sửa sẽ được thay bằng mã kiểm thử khác.",
        confirmLabel: "Bỏ thay đổi",
      });
      if (!answer) return;
    }
    setBusy(true);
    setError("");
    try {
      const value = await testingApi.getAutomationScriptDraft(item._id);
      setSelected(value);
      setFilename(value.filename);
      setSource(value.source);
      setDraftDirty(false);
      setError("");
    } catch (reason) {
      setError(messageOf(reason));
    } finally {
      setBusy(false);
    }
  };

  const save = async () => {
    if (!selected || !draftDirty || busy) return;
    setBusy(true);
    setError("");
    try {
      const value = await testingApi.updateAutomationScriptDraft(selected._id, {
        expected_revision: selected.revision,
        filename,
        source,
      });
      setSelected(value);
      setItems((current) => current.map((item) => (item._id === value._id ? value : item)));
      setFilename(value.filename);
      setSource(value.source);
      setDraftDirty(false);
      setError("");
    } catch (reason) {
      setError(messageOf(reason));
    } finally {
      setBusy(false);
    }
  };

  const approve = async () => {
    if (!selected || busy) return;
    const answer = await ask({
      title: "Phê duyệt kịch bản tự động hóa",
      description: "Kịch bản chỉ được xuất thành tệp sau bước xác nhận này",
      confirmLabel: "Phê duyệt",
      fields: [
        {
          name: "reviewNote",
          label: "Ghi chú rà soát",
          required: true,
          multiline: true,
          autoFocus: true,
        },
      ],
    });
    if (!answer) return;
    setBusy(true);
    setError("");
    try {
      const value = await testingApi.approveAutomationScriptDraft(selected._id, {
        expected_revision: selected.revision,
        review_note: answer.reviewNote.trim(),
      });
      setSelected(value);
      setItems((current) => current.map((item) => (item._id === value._id ? value : item)));
      setFilename(value.filename);
      setSource(value.source);
      setDraftDirty(false);
      setError("");
    } catch (reason) {
      setError(messageOf(reason));
    } finally {
      setBusy(false);
    }
  };

  const exportDraft = async () => {
    if (!selected || busy) return;
    setBusy(true);
    setError("");
    try {
      await testingApi.exportAutomationScriptDraft(selected._id, filename);
    } catch (reason) {
      setError(messageOf(reason));
    } finally {
      setBusy(false);
    }
  };

  if (!canExport) return null;

  return (
    <Panel
      className="automation-scripts-list-panel"
      title="Danh sách mã kiểm thử"
      actions={
        <div className="flex items-center gap-3">
          {!loading && <span className="text-sm text-ink-muted">{items.length} mã</span>}
          <button
            aria-label="Tải lại danh sách mã"
            className="icon-button h-9 w-9 shrink-0"
            disabled={loading}
            onClick={() => void load()}
            title="Tải lại danh sách mã"
            type="button"
          >
            <RefreshCw aria-hidden="true" size={17} />
          </button>
        </div>
      }
    >
      <div className="space-y-4 p-4 sm:p-5">
        {error && (
          <div className="grid gap-3">
            <ErrorState message={error} />
            <button
              className="secondary-button justify-self-start"
              disabled={loading}
              onClick={() => void load()}
              type="button"
            >
              Thử tải lại
            </button>
          </div>
        )}
        {loading ? (
          <LoadingState />
        ) : (
          <div className="grid min-w-0 gap-y-5 gap-x-5 lg:grid-cols-[minmax(0,0.85fr)_minmax(0,1.35fr)] lg:gap-x-0">
            <section aria-label="Danh sách mã kiểm thử tự động" className="min-w-0">
              <SearchField
                ariaLabel="Tìm mã kiểm thử tự động"
                className="mb-5 lg:mr-5"
                label="Tìm mã kiểm thử"
                onChange={(event) => setQuery(event.target.value)}
                placeholder="Tên tệp, mã ca hoặc công cụ"
                value={query}
              />
              {visibleItems.length ? (
                <ul className="-ml-4 divide-y divide-border border-y border-border sm:-ml-5">
                  {visibleItems.map((item) => (
                    <li key={item._id}>
                      <button
                        aria-current={selected?._id === item._id ? "true" : undefined}
                        className={`grid w-full min-w-0 grid-cols-[minmax(0,1fr)_auto] items-center gap-4 py-3 pl-4 pr-3 text-left transition sm:pl-5 sm:pr-4 ${selected?._id === item._id ? "bg-brand-soft/50 text-ink" : "text-ink hover:bg-surface-quiet"}`}
                        disabled={busy}
                        onClick={() => void openDraft(item)}
                        type="button"
                      >
                        <span className="min-w-0">
                          <span className="block min-w-0 break-all font-medium">
                            {item.filename}
                          </span>
                          {(item.test_case_key ||
                            item.framework ||
                            item.language ||
                            item.source_event_key) && (
                            <span className="mt-1 flex min-w-0 flex-wrap items-center gap-x-2 gap-y-1 text-xs text-ink-muted">
                              {item.source_event_key && (
                                <ContentOriginBadge origin="ai_generated" />
                              )}
                              {[item.test_case_key, item.framework, item.language]
                                .map((value, index) =>
                                  index === 1
                                    ? scriptFormatLabel(value, frameworkLabels)
                                    : index === 2
                                      ? scriptFormatLabel(value, languageLabels)
                                      : value,
                                )
                                .filter(Boolean)
                                .join(" · ")}
                            </span>
                          )}
                        </span>
                        <StatusPill value={item.status} />
                      </button>
                    </li>
                  ))}
                </ul>
              ) : (
                !error && (
                  <p className="py-3 text-sm text-ink-muted">
                    {query.trim()
                      ? "Không tìm thấy mã kiểm thử phù hợp."
                      : "Chưa có mã kiểm thử được tạo."}
                  </p>
                )
              )}
            </section>
            <section
              aria-label="Chi tiết kịch bản"
              className="min-w-0 space-y-4 border-t border-border pt-4 lg:border-l lg:border-t-0 lg:pl-5 lg:pt-0"
            >
              {busy && !selected && <LoadingState />}
              {selected ? (
                <>
                  <div className="flex flex-wrap items-center justify-between gap-2 border-b border-border pb-3">
                    <div className="flex flex-wrap items-center gap-2">
                      {selected.source_event_key && <ContentOriginBadge origin="ai_generated" />}
                      <StatusPill value={selected.status} />
                      {selected.generation_status && (
                        <StatusPill value={selected.generation_status} />
                      )}
                    </div>
                  </div>
                  {selected.degraded_mode && (
                    <p className="text-sm text-ink-muted">
                      Mô hình đã dùng để tạo bản nháp này không còn khả dụng
                    </p>
                  )}
                  <dl className="grid gap-3 rounded-control border border-border bg-surface p-4 text-sm sm:grid-cols-2">
                    <div className="min-w-0">
                      <dt className="text-xs font-semibold text-ink-muted">Ca kiểm thử</dt>
                      <dd className="mt-1 break-words text-ink">
                        {selected.test_case_id ? (
                          <Link
                            className="text-brand underline decoration-brand/30 underline-offset-2 hover:decoration-brand"
                            href={`${projectRoute(project._id, PROJECT_SECTION_SLUGS.testCases)}?case=${encodeURIComponent(selected.test_case_id)}`}
                          >
                            {selected.test_case_key || "Mở ca kiểm thử"}
                          </Link>
                        ) : (
                          selected.test_case_key || "Chưa liên kết ca kiểm thử"
                        )}
                      </dd>
                    </div>
                    <div className="min-w-0">
                      <dt className="text-xs font-semibold text-ink-muted">Công cụ và ngôn ngữ</dt>
                      <dd className="mt-1 break-words text-ink">
                        {[
                          scriptFormatLabel(selected.framework, frameworkLabels),
                          scriptFormatLabel(selected.language, languageLabels),
                        ]
                          .filter(Boolean)
                          .join(" · ") || "Chưa xác định"}
                      </dd>
                    </div>
                    <div className="min-w-0">
                      <dt className="text-xs font-semibold text-ink-muted">Lần sửa ca kiểm thử</dt>
                      <dd className="mt-1 break-words text-ink">
                        {selected.source_event_revision ?? "Chưa có"}
                      </dd>
                    </div>
                    <div className="min-w-0">
                      <dt className="text-xs font-semibold text-ink-muted">Ngày tạo</dt>
                      <dd className="mt-1 break-words text-ink">
                        {formatDate(selected.created_at)}
                      </dd>
                    </div>
                    <div className="min-w-0">
                      <dt className="text-xs font-semibold text-ink-muted">Phiên bản mã</dt>
                      <dd className="mt-1 break-words text-ink">
                        {selected.revision ?? "Chưa có"}
                      </dd>
                    </div>
                  </dl>
                  {selected.status === "DRAFT" && canUpdate ? (
                    <>
                      <label className="field-label block">
                        Tên tệp xuất
                        <input
                          className="apple-input mt-2"
                          value={filename}
                          onChange={(event) => {
                            setFilename(event.target.value);
                            setDraftDirty(true);
                          }}
                        />
                      </label>
                      <label className="field-label block">
                        Mã nguồn kịch bản
                        <textarea
                          aria-label="Mã nguồn kịch bản"
                          className="apple-input mt-2 min-h-80 font-mono text-xs"
                          value={source}
                          onChange={(event) => {
                            setSource(event.target.value);
                            setDraftDirty(true);
                          }}
                        />
                      </label>
                    </>
                  ) : (
                    <div className="space-y-3">
                      <div>
                        <p className="text-xs font-semibold text-ink-muted">Tên tệp xuất</p>
                        <p className="break-all text-sm text-ink">{filename}</p>
                      </div>
                      <div>
                        <p className="mb-2 text-xs font-semibold text-ink-muted">
                          Mã nguồn kịch bản
                        </p>
                        <pre className="max-h-96 overflow-auto whitespace-pre-wrap break-words rounded-control bg-surface-quiet p-3 font-mono text-xs text-ink">
                          {source}
                        </pre>
                      </div>
                    </div>
                  )}
                  <div className="flex flex-wrap gap-2">
                    {selected.status === "DRAFT" && canUpdate && (
                      <button
                        className="apple-button"
                        disabled={!draftDirty || busy}
                        type="button"
                        onClick={save}
                      >
                        Lưu bản nháp
                      </button>
                    )}
                    {selected.status === "DRAFT" && canApprove && (
                      <button
                        className="secondary-button"
                        disabled={busy}
                        type="button"
                        onClick={approve}
                      >
                        Phê duyệt kịch bản
                      </button>
                    )}
                    {selected.status === "APPROVED" && canExport && (
                      <button
                        className="apple-button"
                        disabled={busy}
                        type="button"
                        onClick={() => void exportDraft()}
                      >
                        Xuất tệp đã duyệt
                      </button>
                    )}
                  </div>
                </>
              ) : (
                <p className="py-2 text-sm text-ink-muted">
                  Chọn một kịch bản để xem nội dung và thao tác được cấp quyền.
                </p>
              )}
            </section>
          </div>
        )}
      </div>
      {dialog}
    </Panel>
  );
}
