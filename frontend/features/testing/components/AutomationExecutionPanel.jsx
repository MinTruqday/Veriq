"use client";
import { useCallback, useEffect, useMemo, useRef, useState } from "react";
import DataTable from "./DataTable";
import { ErrorState, Panel, StatusPill, useActionDialog } from "./WorkspacePrimitives";
import { testingApi } from "../services/testing.service";
import { messageOf } from "../lib/testing";
import {
  operationForRetry,
  shouldReloadAfterAmbiguousMutation,
} from "../lib/executionRecovery.logic.mjs";

export default function AutomationExecutionPanel({ project }) {
  const { ask, dialog } = useActionDialog();
  const [items, setItems] = useState([]);
  const [artifacts, setArtifacts] = useState([]);
  const [scripts, setScripts] = useState([]);
  const [environments, setEnvironments] = useState([]);
  const [runner, setRunner] = useState("newman");
  const [selected, setSelected] = useState(null);
  const [evidence, setEvidence] = useState(null);
  const [loadingExecutionId, setLoadingExecutionId] = useState("");
  const [error, setError] = useState("");
  const createOperation = useRef(null);
  const loadGeneration = useRef(0);
  const selectionGeneration = useRef(0);
  const permissions = useMemo(
    () => project.current_permissions || [],
    [project.current_permissions],
  );
  const can = (permission) => permissions.includes(permission);
  const load = useCallback(async () => {
    const requestGeneration = ++loadGeneration.current;
    if (!permissions.includes("automation.read")) {
      setItems([]);
      setArtifacts([]);
      setScripts([]);
      setEnvironments([]);
      setSelected(null);
      setEvidence(null);
      return;
    }
    try {
      const [executionValues, artifactValues, scriptValues, environmentValues] = await Promise.all([
        testingApi.listAutomationExecutions(project._id),
        permissions.includes("apiartifact.read")
          ? testingApi.listApiArtifacts(project._id)
          : Promise.resolve([]),
        permissions.includes("automation.script.export")
          ? testingApi.listAutomationScriptDrafts(project._id)
          : Promise.resolve([]),
        permissions.includes("environment.read")
          ? testingApi.listEnvironments(project._id)
          : Promise.resolve([]),
      ]);
      if (requestGeneration !== loadGeneration.current) return;
      setItems(executionValues);
      setArtifacts(
        artifactValues.filter((item) => item.format === "postman" && item.status === "CONFIRMED"),
      );
      setScripts(
        scriptValues.filter(
          (item) => item.framework === "playwright" && item.status === "APPROVED",
        ),
      );
      setEnvironments(environmentValues);
      setSelected(
        (current) => executionValues.find((item) => item._id === current?._id) || current,
      );
      setError("");
    } catch (reason) {
      if (requestGeneration !== loadGeneration.current) return;
      setError(messageOf(reason));
    }
  }, [permissions, project._id, loadGeneration]);
  useEffect(() => {
    selectionGeneration.current += 1;
    setItems([]);
    setArtifacts([]);
    setScripts([]);
    setEnvironments([]);
    setSelected(null);
    setEvidence(null);
    void load();
    return () => {
      loadGeneration.current += 1;
      selectionGeneration.current += 1;
    };
  }, [load, loadGeneration, selectionGeneration]);
  const create = async () => {
    const choices = runner === "newman" ? artifacts : scripts;
    await ask({
      title: runner === "newman" ? "Tạo lần chạy Postman" : "Tạo lần chạy Playwright",
      description:
        runner === "newman"
          ? "Collection phải được nhập rà soát và xác nhận trước khi thực thi"
          : "Kịch bản Playwright phải được rà soát và phê duyệt trước khi thực thi",
      confirmLabel: "Tạo lần chạy",
      fields: [
        { name: "name", label: "Tên lần chạy", required: true, autoFocus: true },
        {
          name: "artifactId",
          label:
            runner === "newman"
              ? "Collection Postman đã xác nhận"
              : "Kịch bản Playwright đã phê duyệt",
          required: true,
          options: choices.map((item) => ({ value: item._id, label: item.filename })),
          initialValue: choices[0]?._id || "",
        },
        {
          name: "environmentId",
          label: "Môi trường chạy",
          options: [
            { value: "", label: "Không dùng môi trường" },
            ...environments.map((item) => ({ value: item._id, label: item.name })),
          ],
          initialValue: "",
        },
      ],
      onConfirm: async (answer) => {
        const payload = {
          name: answer.name.trim(),
          runner,
          ...(runner === "newman"
            ? { postman_artifact_id: answer.artifactId }
            : { automation_script_id: answer.artifactId }),
          environment_id: answer.environmentId || null,
        };
        const signature = JSON.stringify(payload);
        createOperation.current = operationForRetry(
          createOperation.current,
          signature,
          crypto.randomUUID(),
        );
        try {
          const value = await testingApi.createAutomationExecution(project._id, {
            ...payload,
            idempotency_key: createOperation.current.idempotencyKey,
          });
          createOperation.current = null;
          setSelected(value);
          await load();
        } catch (reason) {
          throw new Error(messageOf(reason));
        }
      },
    });
  };
  const open = async (item) => {
    const requestGeneration = ++selectionGeneration.current;
    setLoadingExecutionId(item._id);
    setError("");
    try {
      const value = await testingApi.getAutomationExecution(item._id);
      if (requestGeneration !== selectionGeneration.current || value.project_id !== project._id)
        return;
      setSelected(value);
      const evidenceValue = await testingApi.getAutomationEvidence(item._id);
      if (requestGeneration === selectionGeneration.current) setEvidence(evidenceValue);
    } catch (reason) {
      if (requestGeneration === selectionGeneration.current) setError(messageOf(reason));
    } finally {
      if (requestGeneration === selectionGeneration.current) setLoadingExecutionId("");
    }
  };
  const reconcileAfterFailure = async (executionId, reason) => {
    if (!shouldReloadAfterAmbiguousMutation(reason)) return;
    try {
      setSelected(await testingApi.getAutomationExecution(executionId));
      await load();
    } catch {}
  };
  const start = async () => {
    try {
      const value = await testingApi.startAutomationExecution(selected._id, {
        expected_revision: selected.revision,
        idempotency_key: crypto.randomUUID(),
      });
      setSelected(value);
      await load();
    } catch (reason) {
      await reconcileAfterFailure(selected._id, reason);
      setError(messageOf(reason));
    }
  };
  const cancel = async () => {
    try {
      const value = await testingApi.cancelAutomationExecution(selected._id, {
        expected_revision: selected.revision,
        idempotency_key: crypto.randomUUID(),
      });
      setSelected(value);
      await load();
    } catch (reason) {
      await reconcileAfterFailure(selected._id, reason);
      setError(messageOf(reason));
    }
  };
  if (!can("automation.read")) return null;
  return (
    <Panel
      title="Lần chạy kiểm thử tự động"
      actions={
        can("automation.create") ? (
          <div className="flex flex-wrap items-end gap-2">
            <label className="field-label">
              Công cụ chạy
              <select
                aria-label="Công cụ thực thi tự động hóa"
                className="apple-input mt-1"
                value={runner}
                onChange={(event) => setRunner(event.target.value)}
              >
                <option value="newman">Postman bằng Newman</option>
                <option value="playwright">Playwright</option>
              </select>
            </label>
            <button
              className="apple-button"
              disabled={runner === "newman" ? !artifacts.length : !scripts.length}
              type="button"
              onClick={create}
            >
              Tạo lần chạy
            </button>
          </div>
        ) : null
      }
    >
      <div className="space-y-5 p-5">
        {error && (
          <div className="grid gap-2">
            <ErrorState message={error} />
            <button
              className="secondary-button justify-self-start"
              type="button"
              disabled={Boolean(loadingExecutionId)}
              onClick={() => void (selected ? open(selected) : load())}
            >
              {loadingExecutionId
                ? "Đang tải…"
                : selected
                  ? "Tải lại trạng thái"
                  : "Tải lại danh sách"}
            </button>
          </div>
        )}
        {runner === "newman" && !artifacts.length && can("automation.create") && (
          <p className="text-sm text-ink-muted">Cần xác nhận ít nhất một collection Postman</p>
        )}
        {runner === "playwright" && !scripts.length && can("automation.create") && (
          <p className="text-sm text-ink-muted">Cần phê duyệt ít nhất một kịch bản Playwright</p>
        )}
        <DataTable
          items={items}
          empty="Chưa có lần thực thi tự động"
          onSelect={open}
          activeRowId={selected?._id}
          columns={[
            { key: "name", label: "Tên" },
            { key: "runner", label: "Công cụ chạy" },
            {
              key: "status",
              label: "Trạng thái",
              render: (item) => <StatusPill value={item.status} />,
            },
          ]}
        />
        {selected && (
          <div className="space-y-3 rounded-xl border border-border p-4">
            <div className="flex flex-wrap items-center justify-between gap-3">
              <div className="grid min-w-0 gap-2">
                <p className="break-words font-medium">{selected.name}</p>
                <div className="flex flex-wrap items-center gap-x-4 gap-y-1 text-xs text-ink-muted">
                  <StatusPill value={selected.status} />
                  <span>
                    {selected.runner === "playwright" ? "Playwright" : "Postman bằng Newman"}
                  </span>
                  {selected.environment_snapshot?.name && (
                    <span>Môi trường: {selected.environment_snapshot.name}</span>
                  )}
                  <span>Thông tin bí mật được ẩn trong nhật ký và bằng chứng</span>
                </div>
              </div>
              <div className="flex gap-2">
                {selected.status === "CREATED" && can("automation.execute") && (
                  <button className="apple-button" type="button" onClick={start}>
                    Bắt đầu {selected.runner === "playwright" ? "Playwright" : "Newman"}
                  </button>
                )}
                {selected.status === "QUEUED" && can("automation.execute") && (
                  <button className="secondary-button" type="button" onClick={cancel}>
                    Hủy tác vụ
                  </button>
                )}
                <button
                  className="secondary-button"
                  type="button"
                  disabled={loadingExecutionId === selected._id}
                  onClick={() => open(selected)}
                >
                  {loadingExecutionId === selected._id
                    ? "Đang tải kết quả…"
                    : "Tải kết quả mới nhất"}
                </button>
              </div>
            </div>
            {evidence && (
              <div className="grid gap-4 border-t border-border pt-4">
                <div className="flex flex-wrap gap-x-5 gap-y-1 text-sm text-ink-muted">
                  <span>{evidence.results?.length || 0} kết quả</span>
                  <span>{evidence.logs?.length || 0} dòng nhật ký</span>
                  <span>{evidence.artifact_refs?.length || 0} tệp bằng chứng</span>
                </div>
                {evidence.results?.length > 0 && (
                  <section aria-label="Kết quả từng request" className="grid gap-2">
                    <h3 className="text-sm font-semibold">Kết quả từng mục</h3>
                    {evidence.results.map((result, index) => (
                      <article
                        className="grid min-w-0 gap-2 rounded-control border border-border p-3"
                        key={`${result.name || "result"}-${index}`}
                      >
                        <h4 className="break-words text-sm font-medium">
                          {result.name || `Kết quả ${index + 1}`}
                        </h4>
                        {selected.runner === "newman" ? (
                          <div className="grid gap-2 text-xs text-ink-muted sm:grid-cols-2">
                            {result.status_code !== null && result.status_code !== undefined && (
                              <p>Mã phản hồi: {result.status_code}</p>
                            )}
                            {result.response_time_ms !== null &&
                              result.response_time_ms !== undefined && (
                                <p>Thời gian phản hồi: {result.response_time_ms} ms</p>
                              )}
                            {result.assertions?.map((assertion, assertionIndex) => (
                              <p
                                className="flex flex-wrap items-center gap-2 break-words"
                                key={`${assertion.name || "assertion"}-${assertionIndex}`}
                              >
                                <StatusPill value={assertion.passed ? "PASS" : "FAIL"} />
                                <span>{assertion.name || "Điều kiện kiểm tra"}</span>
                              </p>
                            ))}
                          </div>
                        ) : (
                          <div className="flex flex-wrap items-center gap-x-4 gap-y-1 text-xs text-ink-muted">
                            {result.status && <StatusPill value={result.status} />}
                            {result.duration_ms !== null && result.duration_ms !== undefined && (
                              <span>Thời lượng: {result.duration_ms} ms</span>
                            )}
                            {result.retry > 0 && <span>Số lần chạy lại: {result.retry}</span>}
                          </div>
                        )}
                      </article>
                    ))}
                  </section>
                )}
                {evidence.logs?.length > 0 && (
                  <details className="rounded-control border border-border p-3">
                    <summary className="cursor-pointer text-sm font-medium">Nhật ký xử lý</summary>
                    <ul className="mt-3 grid gap-2">
                      {evidence.logs.map((line, index) => (
                        <li
                          className="whitespace-pre-wrap break-words text-sm text-ink-muted"
                          key={index}
                        >
                          {line}
                        </li>
                      ))}
                    </ul>
                  </details>
                )}
              </div>
            )}
          </div>
        )}
      </div>
      {dialog}
    </Panel>
  );
}
