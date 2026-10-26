"use client";
import { useCallback, useEffect, useState } from "react";
import DataTable from "./DataTable";
import { ErrorState, Panel, StatusPill, useActionDialog } from "./WorkspacePrimitives";
import { testingApi } from "../services/testing.service";
import { formatDate, messageOf, valueLabel } from "../lib/testing";
import {
  Modal,
  ModalContent,
  ModalFooter,
  ModalHeader,
  ModalTitle,
} from "@/shared/components/ui/Modal";
import StructuredValueEditor, { StructuredValueView } from "./StructuredValueEditor";

const providers = [
  ["jira", "Jira"],
  ["github", "GitHub"],
  ["gitlab", "GitLab"],
  ["azure_devops", "Azure DevOps"],
];

export default function ProjectConnectorsPanel({ project }) {
  const { ask, dialog } = useActionDialog();
  const [items, setItems] = useState([]);
  const [logs, setLogs] = useState([]);
  const [conflicts, setConflicts] = useState([]);
  const [error, setError] = useState("");
  const [connectorEditor, setConnectorEditor] = useState(null);
  const [connectorEditorError, setConnectorEditorError] = useState("");
  const [savingConnector, setSavingConnector] = useState(false);
  const canRead = project.current_permissions?.includes("project.connector.read");
  const canManage = project.current_permissions?.includes("project.connector.manage");
  const canSync = project.current_permissions?.includes("project.connector.sync");
  const canReview = project.current_permissions?.includes("project.connector.review");

  const load = useCallback(async () => {
    if (!canRead) return;
    try {
      const [connectorValues, logValues, conflictValues] = await Promise.all([
        testingApi.listProjectConnectors(project._id),
        testingApi.listProjectConnectorSyncLog(project._id),
        canReview ? testingApi.listProjectConnectorConflicts(project._id) : Promise.resolve([]),
      ]);
      setItems(connectorValues);
      setLogs(logValues);
      setConflicts(conflictValues);
      setError("");
    } catch (reason) {
      setError(messageOf(reason));
    }
  }, [canRead, canReview, project._id]);

  useEffect(() => {
    void load();
  }, [load]);

  const openConnectorEditor = (item = null) => {
    setConnectorEditorError("");
    setConnectorEditor({
      source: item,
      provider: item?.provider || "jira",
      connectorReference: item?.connector_reference || "connector://platform/",
      externalTarget: item?.external_target || "",
      fieldMapping: structuredClone(item?.field_mapping || {}),
    });
  };

  const saveConnector = async (event) => {
    event.preventDefault();
    if (!connectorEditor || savingConnector) return;
    setSavingConnector(true);
    setConnectorEditorError("");
    try {
      if (connectorEditor.source) {
        await testingApi.updateProjectConnector(project._id, connectorEditor.source._id, {
          expected_revision: connectorEditor.source.revision,
          field_mapping: connectorEditor.fieldMapping,
        });
      } else {
        await testingApi.bindProjectConnector(project._id, {
          provider: connectorEditor.provider,
          connector_reference: connectorEditor.connectorReference.trim(),
          external_target: connectorEditor.externalTarget.trim(),
          confirm_external_target: true,
          field_mapping: connectorEditor.fieldMapping,
        });
      }
      await load();
      setConnectorEditor(null);
    } catch (reason) {
      setConnectorEditorError(messageOf(reason));
    } finally {
      setSavingConnector(false);
    }
  };

  const bind = () => openConnectorEditor();
  const editMapping = (item) => openConnectorEditor(item);

  const sync = async (item) => {
    await ask({
      title: "Đồng bộ thủ công",
      description: `${item.provider} ${item.external_target}`,
      confirmLabel: "Đưa tác vụ vào hàng đợi",
      fields: [
        {
          name: "direction",
          label: "Chiều đồng bộ",
          required: true,
          initialValue: "PULL",
          options: [
            { value: "PULL", label: "Lấy về" },
            { value: "PUSH", label: "Đẩy lên" },
            { value: "BIDIRECTIONAL", label: "Hai chiều" },
          ],
        },
      ],
      onConfirm: async (answer) => {
        try {
          await testingApi.startProjectConnectorSync(project._id, item._id, {
            direction: answer.direction,
            scopes: ["requirements", "defects", "statuses"],
            idempotency_key: crypto.randomUUID(),
          });
          await load();
        } catch (reason) {
          throw new Error(messageOf(reason));
        }
      },
    });
  };

  const unbind = async (item) => {
    await ask({
      title: "Ngắt kết nối dự án",
      description: `Xác nhận ngắt ${item.external_target}`,
      confirmLabel: "Ngắt kết nối",
      danger: true,
      fields: [
        { name: "reason", label: "Lý do", required: true, multiline: true, autoFocus: true },
      ],
      onConfirm: async (answer) => {
        try {
          await testingApi.unbindProjectConnector(project._id, item._id, {
            expected_revision: item.revision,
            reason: answer.reason.trim(),
            confirm_external_target: true,
          });
          await load();
        } catch (reason) {
          throw new Error(messageOf(reason));
        }
      },
    });
  };

  const resolve = async (item) => {
    await ask({
      title: "Giải quyết xung đột đồng bộ",
      description: "Không có dữ liệu nào bị ghi đè nếu chưa xác nhận phương án",
      confirmLabel: "Xác nhận phương án",
      fields: [
        {
          name: "resolution",
          label: "Phương án",
          required: true,
          initialValue: "KEEP_LOCAL",
          options: [
            { value: "KEEP_LOCAL", label: "Giữ dữ liệu dự án" },
            { value: "KEEP_REMOTE", label: "Giữ dữ liệu bên ngoài" },
          ],
        },
        { name: "reason", label: "Lý do", required: true, multiline: true },
      ],
      onConfirm: async (answer) => {
        try {
          await testingApi.resolveProjectConnectorConflict(project._id, item._id, {
            expected_revision: item.revision,
            resolution: answer.resolution,
            reason: answer.reason.trim(),
          });
          await load();
        } catch (reason) {
          throw new Error(messageOf(reason));
        }
      },
    });
  };

  if (!canRead) return null;

  return (
    <Panel
      title="Kết nối dự án"
      actions={
        canManage ? (
          <button className="apple-button" type="button" onClick={bind}>
            Liên kết dịch vụ
          </button>
        ) : null
      }
    >
      <div className="space-y-5 p-5">
        {error && <ErrorState message={error} />}
        <DataTable
          items={items}
          empty="Chưa có kết nối dự án"
          columns={[
            { key: "provider", label: "Nhà cung cấp" },
            { key: "external_target", label: "Đích bên ngoài" },
            { key: "mapping_version", label: "Phiên bản ánh xạ" },
            { key: "last_sync_status", label: "Lần đồng bộ gần nhất" },
            {
              key: "status",
              label: "Trạng thái",
              render: (item) => <StatusPill value={item.status} />,
            },
            {
              key: "actions",
              label: "Thao tác",
              hideWhenEmpty: true,
              render: (item) => {
                const canSyncItem = canSync && item.status === "BOUND";
                const canManageItem = canManage && item.status === "BOUND";
                if (!canSyncItem && !canManageItem) return null;
                return (
                  <span className="flex flex-wrap gap-2">
                    {canSyncItem && (
                      <button className="secondary-button" type="button" onClick={() => sync(item)}>
                        Đồng bộ
                      </button>
                    )}
                    {canManageItem && (
                      <>
                        <button
                          className="secondary-button"
                          type="button"
                          onClick={() => editMapping(item)}
                        >
                          Sửa ánh xạ
                        </button>
                        <button
                          className="secondary-button"
                          type="button"
                          onClick={() => unbind(item)}
                        >
                          Ngắt kết nối
                        </button>
                      </>
                    )}
                  </span>
                );
              },
            },
          ]}
        />
        {canReview && conflicts.length > 0 && (
          <DataTable
            items={conflicts}
            empty="Không có xung đột"
            columns={[
              {
                key: "artifact_type",
                label: "Loại dữ liệu",
                render: (item) => valueLabel(item.artifact_type),
              },
              { key: "artifact_id", label: "Mã dữ liệu" },
              {
                key: "status",
                label: "Trạng thái",
                render: (item) => valueLabel(item.status),
              },
              {
                key: "action",
                label: "Thao tác",
                hideWhenEmpty: true,
                render: (item) =>
                  item.status === "OPEN" ? (
                    <button
                      className="secondary-button"
                      type="button"
                      onClick={() => resolve(item)}
                    >
                      Giải quyết xung đột
                    </button>
                  ) : null,
              },
            ]}
          />
        )}
        <DataTable
          items={logs}
          empty="Chưa có lần đồng bộ"
          columns={[
            { key: "direction", label: "Chiều" },
            {
              key: "status",
              label: "Trạng thái",
              render: (item) => <StatusPill value={item.status} />,
            },
            {
              key: "created_at",
              label: "Thời điểm",
              render: (item) => formatDate(item.created_at),
            },
          ]}
        />
      </div>
      {dialog}
      {connectorEditor && (
        <Modal
          isOpen
          ariaLabel={
            connectorEditor.source ? "Cập nhật ánh xạ trường" : "Liên kết dịch vụ với dự án"
          }
          className="max-h-[94dvh] max-w-3xl overflow-y-auto"
          onClose={() => {
            if (!savingConnector) setConnectorEditor(null);
          }}
        >
          <form onSubmit={saveConnector}>
            <ModalHeader>
              <ModalTitle>
                {connectorEditor.source ? "Cập nhật ánh xạ trường" : "Liên kết dịch vụ với dự án"}
              </ModalTitle>
              <p className="mt-2 text-sm text-ink-muted">
                Chỉ dùng tham chiếu kết nối đã được quản trị viên cấu hình trên nền tảng.
              </p>
            </ModalHeader>
            <ModalContent className="space-y-4">
              {connectorEditorError && <ErrorState message={connectorEditorError} />}
              {!connectorEditor.source && (
                <>
                  <label className="field-label block">
                    Nhà cung cấp
                    <select
                      className="apple-input mt-2 w-full"
                      value={connectorEditor.provider}
                      onChange={(event) =>
                        setConnectorEditor((current) => ({
                          ...current,
                          provider: event.target.value,
                        }))
                      }
                    >
                      {providers.map(([value, label]) => (
                        <option key={value} value={value}>
                          {label}
                        </option>
                      ))}
                    </select>
                  </label>
                  <label className="field-label block">
                    Tham chiếu kết nối nền tảng
                    <input
                      className="apple-input mt-2 w-full"
                      required
                      value={connectorEditor.connectorReference}
                      onChange={(event) =>
                        setConnectorEditor((current) => ({
                          ...current,
                          connectorReference: event.target.value,
                        }))
                      }
                    />
                  </label>
                  <label className="field-label block">
                    Dự án hoặc kho mã nguồn đích
                    <input
                      className="apple-input mt-2 w-full"
                      required
                      value={connectorEditor.externalTarget}
                      onChange={(event) =>
                        setConnectorEditor((current) => ({
                          ...current,
                          externalTarget: event.target.value,
                        }))
                      }
                    />
                  </label>
                </>
              )}
              <StructuredValueEditor
                label="Ánh xạ trường"
                value={connectorEditor.fieldMapping}
                fixedType="object"
                onChange={(fieldMapping) =>
                  setConnectorEditor((current) => ({ ...current, fieldMapping }))
                }
              />
            </ModalContent>
            <ModalFooter>
              <button
                className="secondary-button"
                type="button"
                disabled={savingConnector}
                onClick={() => setConnectorEditor(null)}
              >
                Hủy
              </button>
              <button className="apple-button" type="submit" disabled={savingConnector}>
                {savingConnector
                  ? "Đang lưu"
                  : connectorEditor.source
                    ? "Lưu ánh xạ"
                    : "Xác nhận liên kết"}
              </button>
            </ModalFooter>
          </form>
        </Modal>
      )}
    </Panel>
  );
}
