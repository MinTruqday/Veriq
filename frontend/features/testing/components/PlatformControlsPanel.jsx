"use client";
import { useCallback, useEffect, useState } from "react";
import { platformApi } from "@/features/authentication/services/platform.service";
import DataTable from "./DataTable";
import {
  ErrorState,
  LoadingState,
  Metric,
  Panel,
  StatusPill,
  useActionDialog,
} from "./WorkspacePrimitives";
import { Pagination } from "@/shared/components/ui/Pagination";
import { formatDate, messageOf, valueLabel } from "../lib/testing";
import {
  Modal,
  ModalContent,
  ModalFooter,
  ModalHeader,
  ModalTitle,
} from "@/shared/components/ui/Modal";
import StructuredValueEditor, { StructuredValueView } from "./StructuredValueEditor";

const configGroups = [
  ["authPolicy", "Chính sách xác thực", "auth-policy"],
  ["rateLimits", "Giới hạn truy cập", "rate-limits"],
  ["breakGlassPolicy", "Chính sách truy cập khẩn cấp", "break-glass-policy"],
  ["aiLimits", "Giới hạn AI", "ai-limits"],
  ["aiRetrieval", "Embedding và reranker", "ai-retrieval"],
  ["aiDefaults", "Mô hình AI mặc định và dự phòng", "ai-defaults"],
  ["integrations", "Tích hợp", "integrations"],
  ["storage", "Kho lưu trữ", "storage"],
  ["featureFlags", "Cờ tính năng", "co-tinh-nang"],
  ["localization", "Ngôn ngữ và múi giờ", "dia-phuong-hoa"],
  ["retention", "Lưu giữ dữ liệu", "luu-giu"],
  ["defaultQuotas", "Hạn mức mặc định", "han-muc-mac-dinh"],
  ["importExport", "Nhập và xuất dữ liệu", "nhap-xuat"],
];

function editableConfigValue(value) {
  const clean = Object.fromEntries(
    Object.entries(value || {}).filter(
      ([key]) => !["created_at", "updated_at", "updated_by"].includes(key),
    ),
  );
  return clean;
}

export default function PlatformControlsPanel() {
  const { ask, dialog } = useActionDialog();
  const [data, setData] = useState(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");
  const [usagePage, setUsagePage] = useState(1);
  const [configEditor, setConfigEditor] = useState(null);
  const [configEditorError, setConfigEditorError] = useState("");
  const [savingConfig, setSavingConfig] = useState(false);
  const usagePageSize = 10;

  const load = useCallback(async () => {
    setLoading(true);
    setError("");
    try {
      const [
        queue,
        dlq,
        rag,
        cache,
        usage,
        versions,
        maintenance,
        integrationHealth,
        aiDefaults,
        aiVersions,
        secrets,
        serviceIdentities,
        breakGlass,
        authPolicy,
        rateLimits,
        breakGlassPolicy,
        aiLimits,
        aiRetrieval,
        integrations,
        storage,
        featureFlags,
        localization,
        retention,
        defaultQuotas,
        importExport,
      ] = await Promise.all([
        platformApi.getQueue(),
        platformApi.getDlq(),
        platformApi.getRagOperations(),
        platformApi.getCache(),
        platformApi.getStorageUsage(),
        platformApi.getRuntimeVersions(),
        platformApi.getMaintenance(),
        platformApi.getIntegrationHealth(),
        platformApi.getAiDefaults(),
        platformApi.getAiVersions(),
        platformApi.listSecrets(),
        platformApi.listServiceIdentities(),
        platformApi.listBreakGlass(),
        platformApi.getAuthPolicy(),
        platformApi.getRateLimits(),
        platformApi.getBreakGlassPolicy(),
        platformApi.getAiLimits(),
        platformApi.getAiRetrieval(),
        platformApi.getIntegrations(),
        platformApi.getStorage(),
        platformApi.getPlatformConfigGroup("co-tinh-nang"),
        platformApi.getPlatformConfigGroup("dia-phuong-hoa"),
        platformApi.getPlatformConfigGroup("luu-giu"),
        platformApi.getPlatformConfigGroup("han-muc-mac-dinh"),
        platformApi.getPlatformConfigGroup("nhap-xuat"),
      ]);
      setData({
        queue,
        dlq,
        rag,
        cache,
        usage,
        versions,
        maintenance,
        integrationHealth,
        aiDefaults,
        aiVersions,
        secrets,
        serviceIdentities,
        breakGlass,
        authPolicy,
        rateLimits,
        breakGlassPolicy,
        aiLimits,
        aiRetrieval,
        integrations,
        storage,
        featureFlags,
        localization,
        retention,
        defaultQuotas,
        importExport,
      });
    } catch (reason) {
      setError(messageOf(reason));
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    void load();
  }, [load]);

  const run = async (action) => {
    setError("");
    try {
      await action();
      await load();
    } catch (reason) {
      setError(messageOf(reason));
    }
  };

  const editConfig = (key, label) => {
    setConfigEditorError("");
    setConfigEditor({ key, label, values: editableConfigValue(data[key]), reason: "" });
  };

  const saveConfig = async (event) => {
    event.preventDefault();
    if (!configEditor || savingConfig) return;
    const updaters = {
      authPolicy: platformApi.updateAuthPolicy,
      rateLimits: platformApi.updateRateLimits,
      breakGlassPolicy: platformApi.updateBreakGlassPolicy,
      aiLimits: platformApi.updateAiLimits,
      aiRetrieval: platformApi.updateAiRetrieval,
      aiDefaults: platformApi.updateAiDefaults,
      integrations: platformApi.updateIntegrations,
      storage: platformApi.updateStorage,
    };
    const group = configGroups.find(([itemKey]) => itemKey === configEditor.key)?.[2];
    setSavingConfig(true);
    setConfigEditorError("");
    try {
      if (updaters[configEditor.key]) {
        await updaters[configEditor.key](configEditor.values, configEditor.reason.trim());
      } else {
        await platformApi.updatePlatformConfigGroup(
          group,
          configEditor.values,
          configEditor.reason.trim(),
        );
      }
      setConfigEditor(null);
      await load();
    } catch (reason) {
      setConfigEditorError(messageOf(reason));
    } finally {
      setSavingConfig(false);
    }
  };

  if (loading && !data)
    return (
      <Panel title="Cấu hình nền tảng">
        <LoadingState />
      </Panel>
    );
  if (error && !data)
    return (
      <Panel title="Cấu hình nền tảng">
        <div className="space-y-3 p-5">
          <ErrorState message={error} />
          <button className="secondary-button" type="button" onClick={() => void load()}>
            Thử tải lại
          </button>
        </div>
      </Panel>
    );

  return (
    <div className="space-y-5">
      {error && <ErrorState message={error} />}
      {error && (
        <button className="secondary-button" type="button" onClick={() => void load()}>
          Thử tải lại dữ liệu
        </button>
      )}
      <div className="grid grid-cols-2 gap-3 xl:grid-cols-5">
        <Metric label="Tác vụ đang chờ" value={data?.queue?.jobs_by_status?.queued || 0} />
        <Metric label="Tác vụ đang chạy" value={data?.queue?.jobs_by_status?.running || 0} />
        <Metric label="Tác vụ lỗi" value={data?.queue?.jobs_by_status?.failed || 0} />
        <Metric
          label="Cần đối soát"
          value={data?.queue?.jobs_by_status?.reconciliation_required || 0}
        />
        <Metric label="Dung lượng đã ghi nhận" value={data?.usage?.total_bytes || 0} />
      </div>

      <div className="grid gap-5 xl:grid-cols-2">
        <Panel title="Hàng đợi và consumer">
          <div className="grid grid-cols-2 gap-4 p-5 text-[13px]">
            <div>
              <p className="field-label">Dịch vụ xử lý nền</p>
              <StatusPill value={String(data?.queue?.worker_status || "UNKNOWN").toUpperCase()} />
            </div>
            <div>
              <p className="field-label">Tiến trình nhận tác vụ</p>
              <StatusPill value={String(data?.queue?.consumer_status || "UNKNOWN").toUpperCase()} />
            </div>
          </div>
        </Panel>
        <Panel
          title="Bộ đệm an toàn"
          actions={
            <button
              className="secondary-button"
              type="button"
              onClick={async () => {
                const answer = await ask({
                  title: "Xóa bộ đệm an toàn",
                  confirmLabel: "Xóa",
                  danger: true,
                  fields: [
                    {
                      name: "scope",
                      label: "Phạm vi",
                      required: true,
                      options: [
                        { value: "RATE_LIMITS", label: "Giới hạn truy cập" },
                        { value: "PASSKEY_CHALLENGES", label: "Thử thách passkey" },
                        { value: "PROJECT_METADATA", label: "Siêu dữ liệu dự án" },
                        { value: "SAFE_ALL", label: "Toàn bộ phạm vi an toàn" },
                      ],
                    },
                    { name: "reason", label: "Lý do", required: true, multiline: true },
                  ],
                });
                if (answer) await run(() => platformApi.clearCache(answer.scope, answer.reason));
              }}
            >
              Xóa theo phạm vi
            </button>
          }
        >
          <DataTable
            items={Object.entries(data?.cache || {}).map(([name, count]) => ({
              _id: name,
              name,
              count,
            }))}
            columns={[
              { key: "name", label: "Phạm vi" },
              { key: "count", label: "Số khóa" },
            ]}
          />
        </Panel>
      </div>

      <Panel title="Tác vụ lỗi trong DLQ">
        <DataTable
          items={data?.dlq || []}
          empty="Không có tác vụ lỗi"
          columns={[
            { key: "_id", label: "Mã" },
            { key: "kind", label: "Loại", render: (item) => valueLabel(item.kind) },
            { key: "error_code", label: "Mã lỗi" },
            {
              key: "actions",
              label: "Thao tác",
              render: (item) => (
                <span className="flex flex-wrap gap-2">
                  <button
                    className="secondary-button"
                    type="button"
                    onClick={async () => {
                      const answer = await ask({
                        title: "Đưa tác vụ trở lại hàng đợi",
                        confirmLabel: "Đưa lại",
                        fields: [{ name: "reason", label: "Lý do", required: true }],
                      });
                      if (answer) await run(() => platformApi.requeueDlq(item._id, answer.reason));
                    }}
                  >
                    Đưa lại hàng đợi
                  </button>
                  <button
                    className="danger-button"
                    type="button"
                    onClick={async () => {
                      const answer = await ask({
                        title: "Loại bỏ tác vụ lỗi",
                        confirmLabel: "Loại bỏ",
                        danger: true,
                        fields: [{ name: "reason", label: "Lý do", required: true }],
                      });
                      if (answer) await run(() => platformApi.discardDlq(item._id, answer.reason));
                    }}
                  >
                    Loại bỏ
                  </button>
                </span>
              ),
            },
          ]}
        />
      </Panel>

      <Panel
        title="Lập chỉ mục tri thức"
        actions={
          <button
            className="secondary-button"
            type="button"
            onClick={async () => {
              const answer = await ask({
                title: "Lập chỉ mục lại dự án",
                confirmLabel: "Tạo tác vụ",
                fields: [
                  { name: "project_id", label: "Mã dự án", required: true },
                  {
                    name: "artifact_version_ids",
                    label: "Mã phiên bản tùy chọn",
                    multiline: true,
                  },
                  { name: "reason", label: "Lý do", required: true, multiline: true },
                ],
              });
              if (!answer) return;
              await run(() =>
                platformApi.requestRagReindex({
                  project_id: answer.project_id,
                  artifact_version_ids: answer.artifact_version_ids.split(/[\s,]+/).filter(Boolean),
                  reason: answer.reason,
                }),
              );
            }}
          >
            Lập chỉ mục lại
          </button>
        }
      >
        <DataTable
          items={Object.entries(data?.rag || {}).flatMap(([collection, states]) =>
            Object.entries(states).map(([status, count]) => ({
              _id: `${collection}-${status}`,
              collection,
              status,
              count,
            })),
          )}
          columns={[
            {
              key: "collection",
              label: "Kho dữ liệu",
              render: (item) => valueLabel(item.collection),
            },
            {
              key: "status",
              label: "Trạng thái",
              render: (item) => valueLabel(String(item.status).toUpperCase()),
            },
            { key: "count", label: "Số lượng" },
          ]}
        />
      </Panel>

      <Panel title="Dung lượng theo dự án">
        <DataTable
          items={(data?.usage?.projects || []).slice(
            (usagePage - 1) * usagePageSize,
            usagePage * usagePageSize,
          )}
          empty="Chưa có dữ liệu dung lượng"
          columns={[
            { key: "project_key", label: "Dự án" },
            { key: "files", label: "Tệp" },
            { key: "bytes", label: "Byte" },
          ]}
        />
        <Pagination
          page={usagePage}
          pageSize={usagePageSize}
          total={(data?.usage?.projects || []).length}
          onChange={setUsagePage}
        />
      </Panel>

      <div className="grid gap-5 xl:grid-cols-2">
        <Panel title="Trạng thái tích hợp">
          <DataTable
            items={data?.integrationHealth?.services || []}
            columns={[
              { key: "service", label: "Dịch vụ" },
              {
                key: "healthy",
                label: "Trạng thái",
                render: (item) => <StatusPill value={item.healthy ? "ACTIVE" : "FAILED"} />,
              },
            ]}
          />
        </Panel>
        <Panel title="Phiên bản vận hành">
          <DataTable
            items={data?.versions?.services || []}
            columns={[
              { key: "service", label: "Dịch vụ" },
              { key: "runtime_version", label: "Phiên bản" },
              {
                key: "healthy",
                label: "Trạng thái",
                render: (item) => <StatusPill value={item.healthy ? "ACTIVE" : "FAILED"} />,
              },
            ]}
          />
        </Panel>
      </div>

      <Panel
        title="Kiểm tra hạ tầng và bảo mật"
        actions={
          <div className="flex flex-wrap gap-2">
            <button
              className="secondary-button"
              type="button"
              onClick={() => run(platformApi.testStorage)}
            >
              Kiểm tra kho lưu trữ
            </button>
            <button
              className="secondary-button"
              type="button"
              onClick={async () => {
                const answer = await ask({
                  title: "Gửi thư kiểm tra",
                  confirmLabel: "Gửi",
                  fields: [
                    { name: "recipient", label: "Email nhận", required: true },
                    { name: "reason", label: "Lý do", required: true },
                  ],
                });
                if (answer) await run(() => platformApi.testSmtp(answer.recipient, answer.reason));
              }}
            >
              Kiểm tra SMTP
            </button>
            <button
              className="danger-button"
              type="button"
              onClick={async () => {
                const answer = await ask({
                  title: "Thu hồi khẩn cấp",
                  description: "Thao tác có hiệu lực ngay lập tức",
                  confirmLabel: "Thu hồi",
                  danger: true,
                  fields: [
                    {
                      name: "scope",
                      label: "Phạm vi",
                      required: true,
                      options: [
                        { value: "USER", label: "Một tài khoản" },
                        { value: "SERVICE_IDENTITY", label: "Một danh tính dịch vụ" },
                        { value: "ALL_USERS", label: "Mọi phiên người dùng" },
                        {
                          value: "ALL_SERVICE_IDENTITIES",
                          label: "Mọi danh tính dịch vụ",
                        },
                      ],
                    },
                    { name: "target_id", label: "Mã đối tượng nếu cần" },
                    { name: "reason", label: "Lý do", required: true, multiline: true },
                  ],
                });
                if (answer)
                  await run(() =>
                    platformApi.emergencyRevoke({
                      scope: answer.scope,
                      target_id: answer.target_id || null,
                      confirmation: "EMERGENCY_REVOKE",
                      reason: answer.reason,
                    }),
                  );
              }}
            >
              Thu hồi khẩn cấp
            </button>
          </div>
        }
      >
        <p className="p-5 text-[13px] text-ink-muted">
          Các lần kiểm tra và thu hồi đều được ghi vào nhật ký bảo mật
        </p>
      </Panel>

      <Panel
        title="Chế độ bảo trì"
        actions={
          <button
            className={data?.maintenance?.enabled ? "danger-button" : "secondary-button"}
            type="button"
            onClick={async () => {
              const enabled = !data?.maintenance?.enabled;
              const answer = await ask({
                title: enabled ? "Bật chế độ bảo trì" : "Tắt chế độ bảo trì",
                confirmLabel: "Áp dụng",
                danger: enabled,
                fields: [
                  {
                    name: "banner",
                    label: "Nội dung thông báo",
                    initialValue: data?.maintenance?.banner || "",
                  },
                  { name: "reason", label: "Lý do", required: true, multiline: true },
                ],
              });
              if (answer)
                await run(() =>
                  platformApi.updateMaintenance(enabled, answer.banner, answer.reason),
                );
            }}
          >
            {data?.maintenance?.enabled ? "Tắt bảo trì" : "Bật bảo trì"}
          </button>
        }
      >
        <div className="p-5 text-[13px]">
          <StatusPill value={data?.maintenance?.enabled ? "ACTIVE" : "DISABLED"} />
          {data?.maintenance?.banner && <p className="mt-3">{data.maintenance.banner}</p>}
        </div>
      </Panel>

      <Panel title="Cấu hình nền tảng">
        <DataTable
          items={configGroups.map(([key, label]) => ({
            _id: key,
            key,
            label,
            value: editableConfigValue(data?.[key]),
          }))}
          columns={[
            { key: "label", label: "Nhóm" },
            {
              key: "value",
              label: "Giá trị",
              render: (item) => <StructuredValueView value={item.value} />,
            },
            {
              key: "edit",
              label: "Thao tác",
              render: (item) => (
                <button
                  className="secondary-button"
                  type="button"
                  onClick={() => editConfig(item.key, item.label)}
                >
                  Cập nhật
                </button>
              ),
            },
          ]}
        />
      </Panel>

      <Panel
        title="Tham chiếu bí mật"
        actions={
          <button
            className="secondary-button"
            type="button"
            onClick={async () => {
              const answer = await ask({
                title: "Tạo tham chiếu bí mật",
                confirmLabel: "Tạo",
                fields: [
                  { name: "name", label: "Tên", required: true },
                  { name: "provider", label: "Nhà cung cấp", required: true },
                  { name: "reference", label: "Tham chiếu", required: true },
                  { name: "reason", label: "Lý do", required: true },
                ],
              });
              if (answer) await run(() => platformApi.createSecret(answer));
            }}
          >
            Tạo tham chiếu
          </button>
        }
      >
        <DataTable
          items={data?.secrets || []}
          empty="Chưa có tham chiếu bí mật"
          columns={[
            { key: "name", label: "Tên" },
            { key: "provider", label: "Nhà cung cấp" },
            { key: "reference", label: "Tham chiếu" },
            {
              key: "actions",
              label: "Thao tác",
              render: (item) => (
                <span className="flex flex-wrap gap-2">
                  <button
                    className="secondary-button"
                    type="button"
                    onClick={async () => {
                      const answer = await ask({
                        title: "Luân chuyển tham chiếu bí mật",
                        confirmLabel: "Luân chuyển",
                        fields: [
                          { name: "reference", label: "Tham chiếu mới", required: true },
                          { name: "reason", label: "Lý do", required: true },
                        ],
                      });
                      if (answer)
                        await run(() =>
                          platformApi.rotateSecret(item._id, answer.reference, answer.reason),
                        );
                    }}
                  >
                    Luân chuyển
                  </button>
                  <button
                    className="danger-button"
                    type="button"
                    onClick={async () => {
                      const answer = await ask({
                        title: "Xóa tham chiếu bí mật",
                        confirmLabel: "Xóa",
                        danger: true,
                        fields: [{ name: "reason", label: "Lý do", required: true }],
                      });
                      if (answer)
                        await run(() => platformApi.deleteSecret(item._id, answer.reason));
                    }}
                  >
                    Xóa
                  </button>
                </span>
              ),
            },
          ]}
        />
      </Panel>

      <Panel
        title="Danh tính dịch vụ"
        actions={
          <button
            className="secondary-button"
            type="button"
            onClick={async () => {
              const answer = await ask({
                title: "Tạo danh tính dịch vụ",
                confirmLabel: "Tạo",
                fields: [
                  { name: "name", label: "Tên", required: true },
                  { name: "secret_reference", label: "Tham chiếu bí mật", required: true },
                  { name: "scopes", label: "Phạm vi phân tách bằng dấu phẩy" },
                  { name: "reason", label: "Lý do", required: true },
                ],
              });
              if (!answer) return;
              await run(() =>
                platformApi.createServiceIdentity({
                  ...answer,
                  scopes: answer.scopes
                    .split(",")
                    .map((value) => value.trim())
                    .filter(Boolean),
                }),
              );
            }}
          >
            Tạo danh tính
          </button>
        }
      >
        <DataTable
          items={data?.serviceIdentities || []}
          empty="Chưa có danh tính dịch vụ"
          columns={[
            { key: "name", label: "Tên" },
            {
              key: "status",
              label: "Trạng thái",
              render: (item) => valueLabel(String(item.status).toUpperCase()),
            },
            { key: "secret_reference", label: "Tham chiếu" },
            { key: "scopes", label: "Phạm vi", render: (item) => (item.scopes || []).join(", ") },
            {
              key: "rotate",
              label: "Thao tác",
              render: (item) => (
                <button
                  className="secondary-button"
                  type="button"
                  onClick={async () => {
                    const answer = await ask({
                      title: "Luân chuyển danh tính dịch vụ",
                      confirmLabel: "Luân chuyển",
                      fields: [
                        {
                          name: "secret_reference",
                          label: "Tham chiếu bí mật mới",
                          required: true,
                        },
                        { name: "reason", label: "Lý do", required: true },
                      ],
                    });
                    if (answer)
                      await run(() =>
                        platformApi.rotateServiceIdentity(
                          item._id,
                          answer.secret_reference,
                          answer.reason,
                        ),
                      );
                  }}
                >
                  Luân chuyển
                </button>
              ),
            },
          ]}
        />
      </Panel>

      <Panel
        title="Quyền truy cập khẩn cấp"
        actions={
          <button
            className="secondary-button"
            type="button"
            onClick={async () => {
              const answer = await ask({
                title: "Cấp quyền truy cập khẩn cấp",
                confirmLabel: "Cấp quyền",
                danger: true,
                fields: [
                  { name: "project_id", label: "Mã dự án", required: true },
                  { name: "user_id", label: "Mã tài khoản", required: true },
                  {
                    name: "permissions",
                    label: "Quyền hạn phân tách bằng dấu phẩy",
                    required: true,
                  },
                  { name: "ttl_minutes", label: "Số phút", required: true, initialValue: "30" },
                  { name: "reason", label: "Lý do", required: true, multiline: true },
                ],
              });
              if (!answer) return;
              await run(() =>
                platformApi.createBreakGlass({
                  project_id: answer.project_id,
                  user_id: answer.user_id,
                  permissions: answer.permissions
                    .split(",")
                    .map((value) => value.trim())
                    .filter(Boolean),
                  ttl_minutes: Number(answer.ttl_minutes),
                  reason: answer.reason,
                }),
              );
            }}
          >
            Cấp quyền khẩn cấp
          </button>
        }
      >
        <DataTable
          items={data?.breakGlass || []}
          empty="Không có quyền truy cập khẩn cấp đang hoạt động"
          columns={[
            { key: "project_id", label: "Dự án" },
            { key: "user_id", label: "Tài khoản" },
            {
              key: "permissions",
              label: "Permission",
              render: (item) => item.permissions.join(", "),
            },
            { key: "expires_at", label: "Hết hạn", render: (item) => formatDate(item.expires_at) },
            {
              key: "revoke",
              label: "Thao tác",
              render: (item) => (
                <button
                  className="danger-button"
                  type="button"
                  onClick={async () => {
                    const answer = await ask({
                      title: "Thu hồi quyền truy cập khẩn cấp",
                      confirmLabel: "Thu hồi",
                      danger: true,
                      fields: [{ name: "reason", label: "Lý do", required: true }],
                    });
                    if (answer)
                      await run(() => platformApi.revokeBreakGlass(item._id, answer.reason));
                  }}
                >
                  Thu hồi
                </button>
              ),
            },
          ]}
        />
      </Panel>

      <Panel
        title="Nhật ký toàn cục"
        actions={
          <button className="secondary-button" type="button" onClick={platformApi.exportAudit}>
            Xuất CSV
          </button>
        }
      >
        <p className="p-5 text-[13px] text-ink-muted">
          Bản xuất chỉ gồm thời điểm hành động người thực hiện đối tượng và lý do
        </p>
      </Panel>
      {configEditor && (
        <Modal
          isOpen
          ariaLabel={`Cập nhật ${configEditor.label}`}
          className="max-h-[94dvh] max-w-4xl overflow-y-auto"
          onClose={() => {
            if (!savingConfig) setConfigEditor(null);
          }}
        >
          <form onSubmit={saveConfig}>
            <ModalHeader>
              <ModalTitle>Cập nhật {configEditor.label}</ModalTitle>
            </ModalHeader>
            <ModalContent className="space-y-4">
              {configEditorError && <ErrorState message={configEditorError} />}
              <StructuredValueEditor
                label="Giá trị cấu hình"
                value={configEditor.values}
                fixedType="object"
                onChange={(values) => setConfigEditor((current) => ({ ...current, values }))}
              />
              <label className="field-label block">
                Lý do thay đổi
                <textarea
                  className="apple-input mt-2 min-h-20 w-full"
                  required
                  value={configEditor.reason}
                  onChange={(event) =>
                    setConfigEditor((current) => ({ ...current, reason: event.target.value }))
                  }
                />
              </label>
            </ModalContent>
            <ModalFooter>
              <button
                className="secondary-button"
                type="button"
                disabled={savingConfig}
                onClick={() => setConfigEditor(null)}
              >
                Hủy
              </button>
              <button className="apple-button" type="submit" disabled={savingConfig}>
                {savingConfig ? "Đang lưu" : "Lưu cấu hình"}
              </button>
            </ModalFooter>
          </form>
        </Modal>
      )}
      {dialog}
    </div>
  );
}
