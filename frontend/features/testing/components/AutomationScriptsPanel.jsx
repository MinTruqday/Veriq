"use client";
import { useCallback, useEffect, useState } from "react";
import DataTable from "./DataTable";
import { ErrorState, Panel, StatusPill, useActionDialog } from "./WorkspacePrimitives";
import { testingApi } from "../services/testing.service";
import { messageOf } from "../lib/testing";

const frameworkLanguages = {
  playwright: ["typescript", "javascript"],
  cypress: ["typescript", "javascript"],
  selenium: ["python"],
};

export default function AutomationScriptsPanel({ project, tests }) {
  const { ask, dialog } = useActionDialog();
  const [items, setItems] = useState([]);
  const [selected, setSelected] = useState(null);
  const [testCaseVersionId, setTestCaseVersionId] = useState("");
  const [framework, setFramework] = useState("playwright");
  const [language, setLanguage] = useState("typescript");
  const [filename, setFilename] = useState("");
  const [source, setSource] = useState("");
  const [error, setError] = useState("");
  const [generating, setGenerating] = useState(false);
  const canGenerate = project.current_permissions?.includes("ai.generate_automation_script");
  const canUpdate = project.current_permissions?.includes("automation.script.update");
  const canApprove = project.current_permissions?.includes("automation.script.approve");
  const canExport = project.current_permissions?.includes("automation.script.export");

  const load = useCallback(async () => {
    if (!canExport) return;
    try {
      const values = await testingApi.listAutomationScriptDrafts(project._id);
      setItems(values);
      setSelected((current) => {
        const next = values.find((item) => item._id === current?._id) || null;
        if (next) {
          setFilename(next.filename);
          setSource(next.source);
        }
        return next;
      });
    } catch (reason) {
      setError(messageOf(reason));
    }
  }, [canExport, project._id]);

  useEffect(() => {
    void load();
  }, [load]);

  useEffect(() => {
    const allowed = frameworkLanguages[framework];
    if (!allowed.includes(language)) setLanguage(allowed[0]);
  }, [framework, language]);

  useEffect(() => {
    if (!testCaseVersionId && tests[0]?.current_version_id) {
      setTestCaseVersionId(tests[0].current_version_id);
    }
  }, [testCaseVersionId, tests]);

  const openDraft = async (item) => {
    try {
      const value = await testingApi.getAutomationScriptDraft(item._id);
      setSelected(value);
      setFilename(value.filename);
      setSource(value.source);
      setError("");
    } catch (reason) {
      setError(messageOf(reason));
    }
  };

  const generate = async () => {
    if (!testCaseVersionId) {
      setError("Phải chọn một phiên bản ca kiểm thử đã phê duyệt");
      return;
    }
    setGenerating(true);
    try {
      const value = await testingApi.generateAutomationScriptDraft(project._id, {
        framework,
        language,
        test_case_version_id: testCaseVersionId,
        context: "",
        idempotency_key: crypto.randomUUID(),
      });
      await load();
      setSelected(value);
      setFilename(value.filename);
      setSource(value.source);
      setError("");
    } catch (reason) {
      setError(messageOf(reason));
    } finally {
      setGenerating(false);
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
      setError("");
    } catch (reason) {
      setError(messageOf(reason));
    }
  };

  if (!canGenerate && !canExport) return null;

  return (
    <Panel title="Kịch bản kiểm thử tự động hóa">
      <div className="space-y-5 p-5">
        {error && <ErrorState message={error} />}
        {canGenerate && (
          <div className="grid gap-3 xl:grid-cols-[minmax(260px,1fr)_180px_180px_auto]">
            <select
              aria-label="Phiên bản ca kiểm thử cho kịch bản tự động hóa"
              className="apple-input"
              value={testCaseVersionId}
              onChange={(event) => setTestCaseVersionId(event.target.value)}
            >
              <option value="">Chọn ca kiểm thử đã phê duyệt</option>
              {tests
                .filter((item) => item.current_version_id)
                .map((item) => (
                  <option key={item.current_version_id} value={item.current_version_id}>
                    {item.test_case_key} {item.current_version?.title}
                  </option>
                ))}
            </select>
            <select
              aria-label="Công cụ tự động hóa"
              className="apple-input"
              value={framework}
              onChange={(event) => setFramework(event.target.value)}
            >
              <option value="playwright">Playwright</option>
              <option value="cypress">Cypress</option>
              <option value="selenium">Selenium</option>
            </select>
            <select
              aria-label="Ngôn ngữ kịch bản tự động hóa"
              className="apple-input"
              value={language}
              onChange={(event) => setLanguage(event.target.value)}
            >
              {frameworkLanguages[framework].map((value) => (
                <option key={value} value={value}>
                  {value === "typescript"
                    ? "TypeScript"
                    : value === "javascript"
                      ? "JavaScript"
                      : "Python"}
                </option>
              ))}
            </select>
            <button
              aria-busy={generating}
              className="apple-button"
              disabled={generating}
              type="button"
              onClick={generate}
            >
              {generating ? "AI đang tạo kịch bản" : "Tạo bản nháp"}
            </button>
          </div>
        )}
        {canExport && (
          <div className="grid gap-5 xl:grid-cols-[minmax(0,0.8fr)_minmax(0,1.2fr)]">
            <div className="overflow-hidden rounded-xl border border-border">
              <DataTable
                items={items}
                empty="Chưa có bản nháp kịch bản tự động hóa"
                onSelect={openDraft}
                columns={[
                  { key: "filename", label: "Tệp" },
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
                          onChange={(event) => setFilename(event.target.value)}
                        />
                      </label>
                      <label className="field-label block">
                        Mã nguồn kịch bản
                        <textarea
                          aria-label="Mã nguồn kịch bản tự động hóa"
                          className="apple-input mt-2 min-h-80 font-mono text-xs"
                          value={source}
                          onChange={(event) => setSource(event.target.value)}
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
