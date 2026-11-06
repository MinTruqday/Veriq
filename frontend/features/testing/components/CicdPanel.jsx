"use client";
import { useCallback, useEffect, useRef, useState } from "react";
import { Power, RefreshCw } from "lucide-react";
import DataTable from "./DataTable";
import {
  ErrorState,
  LoadingState,
  Panel,
  StatusPill,
  useActionDialog,
} from "./WorkspacePrimitives";
import { testingApi } from "../services/testing.service";
import { formatDate, messageOf, valueLabel } from "../lib/testing";

export default function CicdPanel({ project }) {
  const { ask, dialog } = useActionDialog();
  const [state, setState] = useState({ bindings: [], runs: [], reconciliations: [] });
  const [connectors, setConnectors] = useState([]);
  const [error, setError] = useState("");
  const [loading, setLoading] = useState(true);
  const hasLoaded = useRef(false);
  const can = (permission) => project.current_permissions?.includes(permission);
  const canReadConnectors = project.current_permissions?.includes("project.connector.read");
  const load = useCallback(async () => {
    if (!project.current_permissions?.includes("cicd.read")) return false;
    if (!hasLoaded.current) setLoading(true);
    try {
      const [value, connectorValues] = await Promise.all([
        testingApi.getCicdState(project._id),
        canReadConnectors ? testingApi.listProjectConnectors(project._id) : Promise.resolve([]),
      ]);
      setState(value);
      setConnectors(connectorValues.filter((item) => item.status === "BOUND"));
      setError("");
      hasLoaded.current = true;
      return true;
    } catch (reason) {
      setError(messageOf(reason));
      return false;
    } finally {
      setLoading(false);
    }
  }, [canReadConnectors, project._id, project.current_permissions]);
  useEffect(() => {
    hasLoaded.current = false;
    setState({ bindings: [], runs: [], reconciliations: [] });
    setConnectors([]);
    setError("");
    void load();
  }, [load]);
  const create = async () =>
    ask({
      title: "Ánh xạ quy trình CI/CD",
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
            label: `${valueLabel(item.provider)} · ${item.external_target}`,
          })),
          initialValue: connectors[0]?._id || "",
        },
        {
          name: "pipelineReference",
          label: "Mã quy trình trên nền tảng",
          required: true,
          placeholder: "Nhập mã quy trình từ nền tảng đã liên kết",
        },
      ],
      onConfirm: async (answer) => {
        await testingApi
          .createCicdBinding(project._id, {
            name: answer.name.trim(),
            connector_id: answer.connectorId,
            pipeline_reference: answer.pipelineReference.trim(),
            test_case_version_ids: [],
          })
          .catch((reason) => {
            throw new Error(messageOf(reason));
          });
        await load();
      },
    });
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
    await ask({
      title: "Đối soát lại lần chạy CI",
      description: "Tác vụ mới không tạo trùng lần thực thi đã có",
      confirmLabel: "Đưa vào hàng đợi",
      fields: [
        { name: "reason", label: "Lý do", required: true, multiline: true, autoFocus: true },
      ],
      onConfirm: async (answer) => {
        try {
          await testingApi.retryCicdRun(project._id, run._id, {
            expected_revision: run.revision,
            idempotency_key: crypto.randomUUID(),
            reason: answer.reason.trim(),
          });
          await load();
        } catch (reason) {
          throw new Error(messageOf(reason));
        }
      },
    });
  };
  if (!can("cicd.read")) return null;
  return (
    <Panel
      title="Tích hợp CI/CD"
      actions={
        <div className="flex flex-wrap items-center gap-2">
          <button
            aria-label={loading ? "Đang tải CI/CD" : "Tải lại CI/CD"}
            className="icon-button h-10 w-10"
            disabled={loading}
            onClick={() => void load()}
            title={loading ? "Đang tải CI/CD" : "Tải lại CI/CD"}
            type="button"
          >
            <RefreshCw aria-hidden="true" size={16} />
          </button>
          {can("cicd.manage") && connectors.length > 0 && (
            <button className="apple-button" type="button" onClick={create}>
              Ánh xạ quy trình
            </button>
          )}
        </div>
      }
    >
      <div className="space-y-5 p-5">
        {error && <ErrorState message={error} />}
        {error && (
          <button
            className="secondary-button"
            type="button"
            disabled={loading}
            onClick={() => void load()}
          >
            Thử tải lại
          </button>
        )}
        {loading && !hasLoaded.current ? (
          <LoadingState />
        ) : (
          <>
            {!connectors.length && can("cicd.manage") && (
              <p className="rounded-control border border-border bg-surface-quiet p-3 text-sm text-ink-muted">
                Liên kết một dịch vụ dự án trước khi tạo ánh xạ quy trình.
              </p>
            )}
            <section className="space-y-3 rounded-xl border border-border bg-white p-4 sm:p-5">
              <div className="flex flex-wrap items-center justify-between gap-2">
                <h3 className="text-sm font-semibold text-ink">Quy trình đã ánh xạ</h3>
                <span className="text-xs text-ink-muted">{state.bindings.length} quy trình</span>
              </div>
              <DataTable
                items={state.bindings}
                empty="Chưa có quy trình được ánh xạ"
                columns={[
                  { key: "name", label: "Tên" },
                  { key: "pipeline_reference", label: "Mã quy trình trên nền tảng" },
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
                        <button
                          className="icon-button h-9 w-9"
                          type="button"
                          aria-label={item.enabled ? "Tắt kết nối CI/CD" : "Bật kết nối CI/CD"}
                          title={item.enabled ? "Tắt kết nối CI/CD" : "Bật kết nối CI/CD"}
                          onClick={() => toggle(item)}
                        >
                          <Power aria-hidden="true" size={16} />
                        </button>
                      ) : null,
                  },
                ]}
              />
            </section>
            <section className="space-y-3 rounded-xl border border-border bg-white p-4 sm:p-5">
              <div className="flex flex-wrap items-center justify-between gap-2">
                <h3 className="text-sm font-semibold text-ink">Lần chạy từ nền tảng</h3>
                <span className="text-xs text-ink-muted">{state.runs.length} lần chạy</span>
              </div>
              <DataTable
                items={state.runs}
                empty="Chưa nhận lần chạy CI/CD"
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
                        <button
                          className="icon-button h-9 w-9"
                          type="button"
                          aria-label="Thử đối soát lại"
                          title="Thử đối soát lại"
                          onClick={() => retry(item)}
                        >
                          <RefreshCw aria-hidden="true" size={16} />
                        </button>
                      ) : null,
                  },
                ]}
              />
            </section>
            <section className="space-y-3 rounded-xl border border-border bg-white p-4 sm:p-5">
              <div className="flex flex-wrap items-center justify-between gap-2">
                <h3 className="text-sm font-semibold text-ink">Lịch sử đối soát</h3>
                <span className="text-xs text-ink-muted">
                  {state.reconciliations.length} lần xử lý
                </span>
              </div>
              <DataTable
                items={state.reconciliations}
                empty="Chưa có lần đối soát"
                columns={[
                  {
                    key: "status",
                    label: "Trạng thái",
                    render: (item) => <StatusPill value={item.status} />,
                  },
                  { key: "reason", label: "Lý do" },
                  {
                    key: "created_at",
                    label: "Thời điểm",
                    render: (item) => formatDate(item.created_at),
                  },
                ]}
              />
            </section>
          </>
        )}
      </div>
      {dialog}
    </Panel>
  );
}
