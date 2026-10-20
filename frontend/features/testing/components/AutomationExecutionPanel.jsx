"use client";
import { useCallback, useEffect, useMemo, useState } from "react";
import DataTable from "./DataTable";
import { ErrorState, Panel, StatusPill, useActionDialog } from "./WorkspacePrimitives";
import { testingApi } from "../services/testing.service";
import { messageOf } from "../lib/testing";

export default function AutomationExecutionPanel({ project }) {
  const { ask, dialog } = useActionDialog();
  const [items, setItems] = useState([]);
  const [artifacts, setArtifacts] = useState([]);
  const [scripts, setScripts] = useState([]);
  const [environments, setEnvironments] = useState([]);
  const [runner, setRunner] = useState("newman");
  const [selected, setSelected] = useState(null);
  const [evidence, setEvidence] = useState(null);
  const [error, setError] = useState("");
  const permissions = useMemo(
    () => project.current_permissions || [],
    [project.current_permissions],
  );
  const can = (permission) => permissions.includes(permission);
  const load = useCallback(async () => {
    if (!permissions.includes("automation.read")) return;
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
      setError(messageOf(reason));
    }
  }, [permissions, project._id]);
  useEffect(() => {
    void load();
  }, [load]);
  const create = async () => {
    const choices = runner === "newman" ? artifacts : scripts;
    const answer = await ask({
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
    });
    if (!answer) return;
    try {
      const value = await testingApi.createAutomationExecution(project._id, {
        name: answer.name.trim(),
        runner,
        ...(runner === "newman"
          ? { postman_artifact_id: answer.artifactId }
          : { automation_script_id: answer.artifactId }),
        environment_id: answer.environmentId || null,
        idempotency_key: crypto.randomUUID(),
      });
      setSelected(value);
      await load();
    } catch (reason) {
      setError(messageOf(reason));
    }
  };
  const open = async (item) => {
    try {
      const value = await testingApi.getAutomationExecution(item._id);
      setSelected(value);
      setEvidence(await testingApi.getAutomationEvidence(item._id));
    } catch (reason) {
      setError(messageOf(reason));
    }
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
      setError(messageOf(reason));
    }
  };
  if (!can("automation.read")) return null;
  return (
    <Panel
      title="Thực thi tự động hóa"
      actions={
        can("automation.create") ? (
          <div className="flex flex-wrap gap-2">
            <select
              aria-label="Công cụ thực thi tự động hóa"
              className="apple-input"
              value={runner}
              onChange={(event) => setRunner(event.target.value)}
            >
              <option value="newman">Postman bằng Newman</option>
              <option value="playwright">Playwright</option>
            </select>
            <button
              className="apple-button"
              disabled={runner === "newman" ? !artifacts.length : !scripts.length}
              type="button"
              onClick={create}
            >
              Tạo lần chạy tự động
            </button>
          </div>
        ) : null
      }
    >
      <div className="space-y-5 p-5">
        {error && <ErrorState message={error} />}
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
          columns={[
            { key: "name", label: "Tên" },
            { key: "runner", label: "Runner" },
            {
              key: "status",
              label: "Trạng thái",
              render: (item) => <StatusPill value={item.status} />,
            },
            { key: "operation_id", label: "Mã tác vụ" },
          ]}
        />
        {selected && (
          <div className="space-y-3 rounded-xl border border-border p-4">
            <div className="flex flex-wrap items-center justify-between gap-3">
              <div>
                <p className="font-medium">{selected.name}</p>
                <p className="mt-1 text-xs text-ink-muted">
                  Không hiển thị giá trị bí mật trong log và evidence
                </p>
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
                <button className="secondary-button" type="button" onClick={() => open(selected)}>
                  Tải bằng chứng
                </button>
              </div>
            </div>
            {evidence && (
              <div className="grid gap-3 sm:grid-cols-3">
                <div>
                  <p className="text-2xl font-semibold">{evidence.results?.length || 0}</p>
                  <p className="field-label">Kết quả request</p>
                </div>
                <div>
                  <p className="text-2xl font-semibold">{evidence.logs?.length || 0}</p>
                  <p className="field-label">Dòng nhật ký an toàn</p>
                </div>
                <div>
                  <p className="text-2xl font-semibold">{evidence.artifact_refs?.length || 0}</p>
                  <p className="field-label">Tệp bằng chứng</p>
                </div>
              </div>
            )}
          </div>
        )}
      </div>
      {dialog}
    </Panel>
  );
}
