"use client";
import { useCallback, useEffect, useState } from "react";
import DataTable from "./DataTable";
import { ErrorState, Panel, StatusPill, useActionDialog } from "./WorkspacePrimitives";
import ContentOriginBadge from "../../../shared/components/common/ContentOriginBadge";
import { testingApi } from "../services/testing.service";
import { messageOf } from "../lib/testing";

export default function AutomationScriptsPanel({ project }) {
  const { ask, dialog } = useActionDialog();
  const [items, setItems] = useState([]);
  const [selected, setSelected] = useState(null);
  const [filename, setFilename] = useState("");
  const [source, setSource] = useState("");
  const [error, setError] = useState("");
  const [draftDirty, setDraftDirty] = useState(false);
  const canUpdate = project.current_permissions?.includes("automation.script.update");
  const canApprove = project.current_permissions?.includes("automation.script.approve");
  const canExport = project.current_permissions?.includes("automation.script.export");

  const load = useCallback(async () => {
    if (!canExport) return;
    try {
      const values = await testingApi.listAutomationScriptDrafts(project._id);
      setItems(values);
      setError("");
      setSelected((current) => {
        const next = values.find((item) => item._id === current?._id) || null;
        if (next && !draftDirty) {
          setFilename(next.filename);
          setSource(next.source);
        }
        return next;
      });
    } catch (reason) {
      setError(messageOf(reason));
    }
  }, [canExport, draftDirty, project._id]);

  useEffect(() => {
    void load();
  }, [load]);

  useEffect(() => {
    if (!canExport) return undefined;
    let active = true;
    let pending = false;
    const timer = window.setInterval(async () => {
      if (!active || document.visibilityState !== "visible" || pending) return;
      pending = true;
      try {
        await load();
      } finally {
        pending = false;
      }
    }, 5000);
    return () => {
      active = false;
      window.clearInterval(timer);
    };
  }, [canExport, load]);

  const openDraft = async (item) => {
    try {
      const value = await testingApi.getAutomationScriptDraft(item._id);
      setSelected(value);
      setFilename(value.filename);
      setSource(value.source);
      setDraftDirty(false);
      setError("");
    } catch (reason) {
      setError(messageOf(reason));
    }
  };

  const save = async () => {
    if (!selected) return;
    try {
      const value = await testingApi.updateAutomationScriptDraft(selected._id, {
        expected_revision: selected.revision,
        filename,
        source,
      });
      await load();
      setSelected(value);
      setFilename(value.filename);
      setSource(value.source);
      setDraftDirty(false);
      setError("");
    } catch (reason) {
      setError(messageOf(reason));
    }
  };

  const approve = async () => {
    if (!selected) return;
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
    try {
      const value = await testingApi.approveAutomationScriptDraft(selected._id, {
        expected_revision: selected.revision,
        review_note: answer.reviewNote.trim(),
      });
      await load();
      setSelected(value);
      setFilename(value.filename);
      setSource(value.source);
      setDraftDirty(false);
      setError("");
    } catch (reason) {
      setError(messageOf(reason));
    }
  };

  if (!canExport) return null;

  return (
    <Panel title="Kịch bản tự động hóa">
      <p className="px-5 pt-4 text-sm text-ink-muted">
        Khi phiên bản ca kiểm thử được phê duyệt, đánh dấu tự động hóa và dự án đã cấu hình công cụ,
        AI sẽ tạo kịch bản theo sự kiện. Ca thủ công hoặc dự án chưa cấu hình sẽ không bị tự chọn
        công cụ.
      </p>
      <div className="space-y-5 p-5">
        {error && <ErrorState message={error} />}
        {canExport && (
          <div className="grid gap-5 xl:grid-cols-[minmax(0,0.8fr)_minmax(0,1.2fr)]">
            <div className="overflow-hidden rounded-xl border border-border">
              <DataTable
                items={items}
                empty="Chưa có bản nháp kịch bản tự động hóa"
                onSelect={openDraft}
                columns={[
                  {
                    key: "filename",
                    label: "Tệp",
                    render: (item) => (
                      <div className="flex flex-wrap items-center gap-2">
                        <span>{item.filename}</span>
                        {item.source_event_key && <ContentOriginBadge origin="ai_generated" />}
                      </div>
                    ),
                  },
                  { key: "framework", label: "Công cụ" },
                  {
                    key: "status",
                    label: "Trạng thái",
                    render: (item) => <StatusPill value={item.status} />,
                  },
                ]}
              />
            </div>
            <div className="space-y-3 rounded-xl border border-border p-4">
              {selected ? (
                <>
                  <div className="flex flex-wrap items-center justify-between gap-2">
                    <div className="flex flex-wrap items-center gap-2">
                      {selected.source_event_key && <ContentOriginBadge origin="ai_generated" />}
                      <StatusPill value={selected.status} />
                      <StatusPill value={selected.generation_status} />
                    </div>
                    <span className="text-xs text-ink-muted">Không ghi kho mã nguồn</span>
                  </div>
                  {selected.degraded_mode && (
                    <p className="text-sm text-ink-muted">
                      Mô hình đã dùng để tạo bản nháp này không còn khả dụng
                    </p>
                  )}
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
                          aria-label="Mã nguồn kịch bản tự động hóa"
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
                      <button className="secondary-button" type="button" onClick={save}>
                        Lưu bản nháp
                      </button>
                    )}
                    {selected.status === "DRAFT" && canApprove && (
                      <button className="apple-button" type="button" onClick={approve}>
                        Phê duyệt kịch bản
                      </button>
                    )}
                    {selected.status === "APPROVED" && canExport && (
                      <button
                        className="apple-button"
                        type="button"
                        onClick={() =>
                          testingApi.exportAutomationScriptDraft(selected._id, filename)
                        }
                      >
                        Xuất tệp đã duyệt
                      </button>
                    )}
                  </div>
                </>
              ) : (
                <p className="text-sm text-ink-muted">Chọn một bản nháp để rà soát</p>
              )}
            </div>
          </div>
        )}
      </div>
      {dialog}
    </Panel>
  );
}
