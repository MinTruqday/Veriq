"use client";
import { useCallback, useEffect, useState } from "react";
import DataTable from "./DataTable";
import { ErrorState, Panel, StatusPill, useActionDialog } from "./WorkspacePrimitives";
import { testingApi } from "../services/testing.service";
import { formatDate, messageOf, valueLabel } from "../lib/testing";

const providers = [
  ["jira", "Jira"],
  ["github", "GitHub"],
  ["gitlab", "GitLab"],
  ["azure_devops", "Azure DevOps"],
];

const parseMapping = (value) => {
  const parsed = JSON.parse(value || "{}");
  if (!parsed || Array.isArray(parsed) || typeof parsed !== "object") {
    throw new Error("Ánh xạ trường phải là một đối tượng JSON");
  }
  return parsed;
};

export default function ProjectConnectorsPanel({ project }) {
  const { ask, dialog } = useActionDialog();
  const [items, setItems] = useState([]);
  const [logs, setLogs] = useState([]);
  const [conflicts, setConflicts] = useState([]);
  const [error, setError] = useState("");
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

  const bind = async () => {
    const answer = await ask({
      title: "Liên kết dịch vụ với dự án",
      description: "Chỉ sử dụng tham chiếu kết nối đã được quản trị viên cấu hình trên nền tảng",
      confirmLabel: "Xác nhận liên kết",
      fields: [
        {
          name: "provider",
          label: "Nhà cung cấp",
          required: true,
          options: providers.map(([value, label]) => ({ value, label })),
          initialValue: "jira",
        },
        {
          name: "connectorReference",
          label: "Tham chiếu kết nối nền tảng",
          required: true,
          initialValue: "connector://platform/",
        },
        { name: "externalTarget", label: "Dự án hoặc kho mã nguồn đích", required: true },
        { name: "fieldMapping", label: "Ánh xạ trường JSON", multiline: true, initialValue: "{}" },
      ],
    });
    if (!answer) return;
    try {
      await testingApi.bindProjectConnector(project._id, {
        provider: answer.provider,
        connector_reference: answer.connectorReference.trim(),
        external_target: answer.externalTarget.trim(),
        confirm_external_target: true,
        field_mapping: parseMapping(answer.fieldMapping),
      });
      await load();
    } catch (reason) {
      setError(messageOf(reason));
    }
  };

  const editMapping = async (item) => {
    const answer = await ask({
      title: "Cập nhật ánh xạ trường",
      description: `Ánh xạ hiện tại phiên bản ${item.mapping_version}`,
      confirmLabel: "Lưu phiên bản ánh xạ",
      fields: [
        {
          name: "fieldMapping",
          label: "Ánh xạ trường JSON",
          required: true,
          multiline: true,
          initialValue: JSON.stringify(item.field_mapping || {}, null, 2),
        },
      ],
    });
    if (!answer) return;
    try {
      await testingApi.updateProjectConnector(project._id, item._id, {
        expected_revision: item.revision,
        field_mapping: parseMapping(answer.fieldMapping),
      });
      await load();
    } catch (reason) {
      setError(messageOf(reason));
    }
  };

  const sync = async (item) => {
    const answer = await ask({
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
    });
    if (!answer) return;
    try {
      await testingApi.startProjectConnectorSync(project._id, item._id, {
        direction: answer.direction,
        scopes: ["requirements", "defects", "statuses"],
        idempotency_key: crypto.randomUUID(),
      });
      await load();
    } catch (reason) {
      setError(messageOf(reason));
    }
  };

  const unbind = async (item) => {
    const answer = await ask({
      title: "Ngắt kết nối dự án",
      description: `Xác nhận ngắt ${item.external_target}`,
      confirmLabel: "Ngắt kết nối",
      danger: true,
      fields: [
        { name: "reason", label: "Lý do", required: true, multiline: true, autoFocus: true },
      ],
    });
    if (!answer) return;
    try {
      await testingApi.unbindProjectConnector(project._id, item._id, {
        expected_revision: item.revision,
        reason: answer.reason.trim(),
        confirm_external_target: true,
      });
      await load();
    } catch (reason) {
      setError(messageOf(reason));
    }
  };

  const resolve = async (item) => {
    const answer = await ask({
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
    });
    if (!answer) return;
    try {
      await testingApi.resolveProjectConnectorConflict(project._id, item._id, {
        expected_revision: item.revision,
        resolution: answer.resolution,
        reason: answer.reason.trim(),
      });
      await load();
    } catch (reason) {
      setError(messageOf(reason));
    }
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
    </Panel>
  );
}
