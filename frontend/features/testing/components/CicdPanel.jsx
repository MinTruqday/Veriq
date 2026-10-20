"use client";
import { useCallback, useEffect, useState } from "react";
import DataTable from "./DataTable";
import { ErrorState, Panel, StatusPill, useActionDialog } from "./WorkspacePrimitives";
import { testingApi } from "../services/testing.service";
import { messageOf } from "../lib/testing";

export default function CicdPanel({ project }) {
  const { ask, dialog } = useActionDialog();
  const [state, setState] = useState({ bindings: [], runs: [], reconciliations: [] });
  const [connectors, setConnectors] = useState([]);
  const [error, setError] = useState("");
  const can = (permission) => project.current_permissions?.includes(permission);
  const canReadConnectors = project.current_permissions?.includes("project.connector.read");
  const load = useCallback(async () => {
    if (!project.current_permissions?.includes("cicd.read")) return;
    try {
      const [value, connectorValues] = await Promise.all([
        testingApi.getCicdState(project._id),
        canReadConnectors ? testingApi.listProjectConnectors(project._id) : Promise.resolve([]),
      ]);
      setState(value);
      setConnectors(connectorValues.filter((item) => item.status === "BOUND"));
      setError("");
    } catch (reason) {
      setError(messageOf(reason));
    }
  }, [canReadConnectors, project._id, project.current_permissions]);
  useEffect(() => {
    void load();
  }, [load]);
  const create = async () => {
    const answer = await ask({
      title: "Ánh xạ quy trình CI CD",
      description: "Quy trình phải thuộc một kết nối dự án đang hoạt động",
      confirmLabel: "Tạo ánh xạ",
      fields: [
        { name: "name", label: "Tên ánh xạ", required: true, autoFocus: true },
        {
          name: "connectorId",
          label: "Kết nối dự án",
          required: true,
          options: connectors.map((item) => ({
            value: item._id,
            label: `${item.provider} ${item.external_target}`,
          })),
          initialValue: connectors[0]?._id || "",
        },
        {
          name: "pipelineReference",
          label: "Tham chiếu quy trình nền tảng",
          required: true,
          initialValue: "pipeline://platform/",
        },
      ],
    });
    if (!answer) return;
    try {
      await testingApi.createCicdBinding(project._id, {
        name: answer.name.trim(),
        connector_id: answer.connectorId,
        pipeline_reference: answer.pipelineReference.trim(),
        test_case_version_ids: [],
      });
      await load();
    } catch (reason) {
      setError(messageOf(reason));
    }
  };
  const toggle = async (item) => {
    try {
      await testingApi.updateCicdBinding(project._id, item._id, {
        expected_revision: item.revision,
        enabled: !item.enabled,
      });
      await load();
    } catch (reason) {
      setError(messageOf(reason));
    }
  };
  const retry = async (run) => {
    const answer = await ask({
      title: "Đối soát lại lần chạy CI",
      description: "Tác vụ mới không tạo trùng lần thực thi đã có",
      confirmLabel: "Đưa vào hàng đợi",
      fields: [
        { name: "reason", label: "Lý do", required: true, multiline: true, autoFocus: true },
      ],
    });
    if (!answer) return;
    try {
      await testingApi.retryCicdRun(project._id, run._id, {
        expected_revision: run.revision,
        idempotency_key: crypto.randomUUID(),
        reason: answer.reason.trim(),
      });
      await load();
    } catch (reason) {
      setError(messageOf(reason));
    }
  };
  if (!can("cicd.read")) return null;
  return (
    <Panel
      title="Tích hợp CI CD"
      actions={
        can("cicd.manage") && connectors.length > 0 ? (
          <button className="apple-button" type="button" onClick={create}>
            Ánh xạ quy trình
          </button>
        ) : null
      }
    >
      <div className="space-y-5 p-5">
        {error && <ErrorState message={error} />}
        <DataTable
          items={state.bindings}
          empty="Chưa có quy trình được ánh xạ"
          columns={[
            { key: "name", label: "Tên" },
            { key: "pipeline_reference", label: "Quy trình" },
            {
              key: "enabled",
              label: "Trạng thái",
              render: (item) => (item.enabled ? "Đang hoạt động" : "Đã tắt"),
            },
            {
              key: "action",
              label: "Thao tác",
              render: (item) =>
                can("cicd.manage") && canReadConnectors ? (
                  <button className="secondary-button" type="button" onClick={() => toggle(item)}>
                    {item.enabled ? "Tắt" : "Bật"}
                  </button>
                ) : null,
            },
          ]}
        />
        <DataTable
          items={state.runs}
          empty="Chưa nhận lần chạy CI"
          columns={[
            { key: "external_run_id", label: "Mã lần chạy ngoài" },
            { key: "commit_reference", label: "Phiên bản mã nguồn" },
            {
              key: "status",
              label: "Trạng thái",
              render: (item) => <StatusPill value={item.status} />,
            },
            {
              key: "action",
              label: "Đối soát",
              render: (item) =>
                item.status === "FAILED" && can("cicd.retry") ? (
                  <button className="secondary-button" type="button" onClick={() => retry(item)}>
                    Thử đối soát lại
                  </button>
                ) : null,
            },
          ]}
        />
        {state.reconciliations.length > 0 && (
          <p className="text-sm text-ink-muted">
            Có {state.reconciliations.length} tác vụ đối soát trong lịch sử
          </p>
        )}
      </div>
      {dialog}
    </Panel>
  );
}
