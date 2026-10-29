"use client";
import { useCallback, useEffect, useState } from "react";
import { platformApi } from "@/features/authentication/services/platform.service";
import DataTable from "./DataTable";
import {
  ErrorState,
  LoadingState,
  Panel,
  StatusPill,
  useActionDialog,
} from "./WorkspacePrimitives";
import { Pagination } from "@/shared/components/ui/Pagination";
import { formatDate, messageOf, valueLabel } from "../lib/testing";
import PlatformControlsPanel from "./PlatformControlsPanel";
import { useAuth } from "@/features/authentication/contexts/AuthContext";

export default function PlatformOperationsPanel() {
  const { user, isLoading: authLoading } = useAuth();
  const isPlatformAdmin = user?.system_role === "ADMIN";
  const { ask, dialog } = useActionDialog();
  const [projects, setProjects] = useState([]);
  const [policy, setPolicy] = useState(null);
  const [providers, setProviders] = useState([]);
  const [models, setModels] = useState([]);
  const [health, setHealth] = useState(null);
  const [jobs, setJobs] = useState([]);
  const [selectedProject, setSelectedProject] = useState(null);
  const [projectMemberships, setProjectMemberships] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");
  const [hasLoaded, setHasLoaded] = useState(false);
  const [projectPage, setProjectPage] = useState(1);
  const [jobPage, setJobPage] = useState(1);
  const [modelPage, setModelPage] = useState(1);
  const projectPageSize = 10;
  const jobPageSize = 20;
  const modelPageSize = 10;

  const load = useCallback(async () => {
    if (!isPlatformAdmin) return;
    setLoading(true);
    setError("");
    try {
      const [projectValues, policyValue, providerValues, modelValues, healthValue, jobValues] =
        await Promise.all([
          platformApi.listProjects(),
          platformApi.getProjectPolicy(),
          platformApi.listProviders(),
          platformApi.listModels(),
          platformApi.getHealth(),
          platformApi.listJobs(),
        ]);
      setProjects(projectValues);
      setPolicy(policyValue);
      setProviders(providerValues);
      setModels(modelValues);
      setHealth(healthValue);
      setJobs(jobValues);
      setHasLoaded(true);
    } catch (reason) {
      setError(messageOf(reason));
    } finally {
      setLoading(false);
    }
  }, [isPlatformAdmin]);

  useEffect(() => {
    if (authLoading || !isPlatformAdmin) return;
    void load();
  }, [authLoading, isPlatformAdmin, load]);

  if (authLoading || !isPlatformAdmin) return null;

  if (loading) return <LoadingState />;
  if (error && !hasLoaded) {
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
  }

  return (
    <div className="space-y-5">
      {error && (
        <div className="space-y-3">
          <ErrorState message={error} />
          <button className="secondary-button" type="button" onClick={() => void load()}>
            Thử tải lại
          </button>
        </div>
      )}
      <Panel title="Trạng thái dịch vụ nền tảng">
        <DataTable
          items={health?.services || []}
          empty="Chưa có dữ liệu trạng thái"
          columns={[
            {
              key: "service",
              label: "Dịch vụ",
              render: (item) => valueLabel(item.service),
            },
            {
              key: "healthy",
              label: "Trạng thái",
              render: (item) => <StatusPill value={item.healthy ? "ACTIVE" : "FAILED"} />,
            },
            { key: "status_code", label: "Mã phản hồi" },
          ]}
        />
      </Panel>
      <Panel title="Chính sách tạo dự án">
        <div className="flex flex-wrap items-end gap-3 p-5">
          <label className="field-label">
            Người được phép tạo dự án
            <select
              className="apple-input mt-2"
              value={policy?.project_creation_policy || "AUTHENTICATED"}
              onChange={async (event) => {
                const desired = event.target.value;
                const answer = await ask({
                  title: "Thay đổi chính sách tạo dự án",
                  description:
                    desired === "ADMIN_ONLY"
                      ? "Chỉ quản trị viên hệ thống được tạo dự án mới"
                      : "Mọi tài khoản đã xác thực được tạo dự án mới",
                  confirmLabel: "Áp dụng",
                  fields: [
                    {
                      name: "reason",
                      label: "Lý do",
                      required: true,
                      multiline: true,
                    },
                  ],
                });
                if (!answer) return;
                try {
                  await platformApi.updateProjectPolicy(desired, answer.reason);
                  await load();
                } catch (reason) {
                  setError(messageOf(reason));
                }
              }}
            >
              <option value="AUTHENTICATED">Tài khoản đã xác thực</option>
              <option value="ADMIN_ONLY">Chỉ quản trị viên</option>
            </select>
          </label>
        </div>
      </Panel>

      <Panel title="Danh sách dự án">
        <DataTable
          items={projects.slice((projectPage - 1) * projectPageSize, projectPage * projectPageSize)}
          empty="Chưa có dự án"
          columns={[
            { key: "key", label: "Mã" },
            { key: "name", label: "Tên" },
            {
              key: "project_type",
              label: "Loại",
              render: (item) => valueLabel(item.project_type),
            },
            {
              key: "status",
              label: "Trạng thái",
              render: (item) => <StatusPill value={String(item.status).toUpperCase()} />,
            },
            { key: "member_count", label: "Thành viên" },
            {
              key: "updated_at",
              label: "Cập nhật",
              render: (item) => formatDate(item.updated_at),
            },
            {
              key: "actions",
              label: "Thao tác",
              render: (item) => (
                <span className="flex flex-wrap gap-2">
                  <button
                    className="secondary-button"
                    type="button"
                    onClick={async () => {
                      try {
                        const [detail, memberships] = await Promise.all([
                          platformApi.getProject(item._id),
                          platformApi.listProjectMemberships(item._id),
                        ]);
                        setSelectedProject(detail);
                        setProjectMemberships(memberships);
                      } catch (reason) {
                        setError(messageOf(reason));
                      }
                    }}
                  >
                    Chẩn đoán
                  </button>
                  <button
                    className="secondary-button"
                    type="button"
                    onClick={async () => {
                      const suspended = item.administrative_status === "SUSPENDED";
                      const answer = await ask({
                        title: suspended ? "Kích hoạt lại dự án" : "Tạm ngưng dự án",
                        confirmLabel: suspended ? "Kích hoạt" : "Tạm ngưng",
                        danger: !suspended,
                        fields: [
                          { name: "reason", label: "Lý do", required: true, multiline: true },
                        ],
                      });
                      if (!answer) return;
                      try {
                        await platformApi.updateProjectStatus(
                          item._id,
                          suspended ? "ACTIVE" : "SUSPENDED",
                          answer.reason,
                        );
                        await load();
                      } catch (reason) {
                        setError(messageOf(reason));
                      }
                    }}
                  >
                    {item.administrative_status === "SUSPENDED" ? "Kích hoạt" : "Tạm ngưng"}
                  </button>
                  <button
                    className="secondary-button"
                    type="button"
                    onClick={async () => {
                      const answer = await ask({
                        title: "Cập nhật hạn mức dự án",
                        confirmLabel: "Lưu hạn mức",
                        fields: [
                          {
                            name: "storage_bytes",
                            label: "Dung lượng lưu trữ (byte)",
                            initialValue: String(item.quota?.storage_bytes || 0),
                          },
                          {
                            name: "ai_requests_per_day",
                            label: "Lượt AI mỗi ngày",
                            initialValue: String(item.quota?.ai_requests_per_day || 0),
                          },
                          {
                            name: "concurrent_jobs",
                            label: "Tác vụ đồng thời",
                            initialValue: String(item.quota?.concurrent_jobs || 0),
                          },
                          { name: "reason", label: "Lý do", required: true },
                        ],
                      });
                      if (!answer) return;
                      try {
                        await platformApi.updateProjectQuota(
                          item._id,
                          {
                            storage_bytes: Number(answer.storage_bytes),
                            ai_requests_per_day: Number(answer.ai_requests_per_day),
                            concurrent_jobs: Number(answer.concurrent_jobs),
                          },
                          answer.reason,
                        );
                        await load();
                      } catch (reason) {
                        setError(messageOf(reason));
                      }
                    }}
                  >
                    Hạn mức
                  </button>
                  <button
                    className="danger-button"
                    type="button"
                    onClick={async () => {
                      const answer = await ask({
                        title: "Xóa cứng dự án",
                        description: `Nhập chính xác ${item.key} để xác nhận`,
                        confirmLabel: "Xóa dự án",
                        danger: true,
                        fields: [
                          { name: "confirmation", label: "Mã dự án", required: true },
                          { name: "reason", label: "Lý do", required: true, multiline: true },
                        ],
                      });
                      if (!answer) return;
                      try {
                        await platformApi.deleteProject(
                          item._id,
                          answer.confirmation,
                          answer.reason,
                        );
                        if (selectedProject?._id === item._id) {
                          setSelectedProject(null);
                          setProjectMemberships([]);
                        }
                        await load();
                      } catch (reason) {
                        setError(messageOf(reason));
                      }
                    }}
                  >
                    Xóa cứng
                  </button>
                </span>
              ),
            },
          ]}
        />
        <Pagination
          page={projectPage}
          pageSize={projectPageSize}
          total={projects.length}
          onChange={setProjectPage}
        />
      </Panel>

      {selectedProject && (
        <Panel title={`Chẩn đoán dự án ${selectedProject.key}`}>
          <div className="grid gap-4 border-b border-border p-5 md:grid-cols-3">
            <div>
              <p className="field-label">Thành viên</p>
              <p>{selectedProject.member_count}</p>
            </div>
            <div>
              <p className="field-label">Thành viên hoạt động</p>
              <p>{selectedProject.active_member_count}</p>
            </div>
            <div>
              <p className="field-label">Tác vụ nền</p>
              <p>{selectedProject.job_count}</p>
            </div>
          </div>
          <DataTable
            items={projectMemberships}
            empty="Không có thành viên"
            columns={[
              { key: "user_id", label: "Tài khoản" },
              {
                key: "project_role",
                label: "Vai trò",
                render: (item) => valueLabel(item.project_role),
              },
              {
                key: "status",
                label: "Trạng thái",
                render: (item) => valueLabel(String(item.status).toUpperCase()),
              },
              { key: "membership_revision", label: "Phiên bản" },
            ]}
          />
        </Panel>
      )}

      <Panel title="Nhà cung cấp và mô hình AI">
        <DataTable
          items={providers}
          empty="Chưa có cấu hình AI"
          columns={[
            { key: "_id", label: "Nhà cung cấp" },
            { key: "model", label: "Mô hình" },
            {
              key: "enabled",
              label: "Trạng thái",
              render: (item) => <StatusPill value={item.enabled ? "ACTIVE" : "DISABLED"} />,
            },
            { key: "timeout_seconds", label: "Thời gian chờ (giây)" },
            { key: "max_output_tokens", label: "Số token đầu ra tối đa" },
            {
              key: "actions",
              label: "Thao tác",
              render: (item) => (
                <span className="flex flex-wrap gap-2">
                  <button
                    className="secondary-button"
                    type="button"
                    onClick={async () => {
                      try {
                        await platformApi.testProvider(item._id);
                      } catch (reason) {
                        setError(messageOf(reason));
                      }
                    }}
                  >
                    Kiểm tra kết nối
                  </button>
                  <button
                    className="secondary-button"
                    type="button"
                    onClick={async () => {
                      const answer = await ask({
                        title: item.enabled ? "Tắt nhà cung cấp AI" : "Bật nhà cung cấp AI",
                        description: "Thay đổi được ghi nhận và yêu cầu khởi động lại dịch vụ AI",
                        confirmLabel: "Lưu cấu hình",
                        fields: [
                          {
                            name: "reason",
                            label: "Lý do",
                            required: true,
                          },
                        ],
                      });
                      if (!answer) return;
                      try {
                        await platformApi.updateProvider(item._id, {
                          enabled: !item.enabled,
                          reason: answer.reason,
                        });
                        await load();
                      } catch (reason) {
                        setError(messageOf(reason));
                      }
                    }}
                  >
                    {item.enabled ? "Tắt" : "Bật"}
                  </button>
                </span>
              ),
            },
          ]}
        />
      </Panel>
      <Panel title="Tác vụ nền">
        <DataTable
          items={jobs.slice((jobPage - 1) * jobPageSize, jobPage * jobPageSize)}
          empty="Chưa có tác vụ nền"
          columns={[
            { key: "_id", label: "Mã tác vụ" },
            {
              key: "kind",
              label: "Loại",
              render: (item) => valueLabel(item.kind),
            },
            {
              key: "status",
              label: "Trạng thái",
              render: (item) => <StatusPill value={String(item.status).toUpperCase()} />,
            },
            {
              key: "error_code",
              label: "Chi tiết xử lý",
              render: (item) =>
                item.error_code ? (
                  <span className="block max-w-72 whitespace-normal text-xs text-ink-muted">
                    {valueLabel(item.error_code)}
                    {item.status === "reconciliation_required"
                      ? ". Cần đối soát trước khi thử lại; hệ thống không tự chạy lại job này."
                      : ""}
                  </span>
                ) : (
                  "—"
                ),
            },
            {
              key: "updated_at",
              label: "Cập nhật",
              render: (item) => formatDate(item.updated_at),
            },
            {
              key: "retry",
              label: "Thao tác",
              render: (item) =>
                String(item.status).toLowerCase() === "failed" ? (
                  <button
                    className="secondary-button"
                    type="button"
                    onClick={async () => {
                      try {
                        await platformApi.retryJob(item._id);
                        await load();
                      } catch (reason) {
                        setError(messageOf(reason));
                      }
                    }}
                  >
                    Thử lại
                  </button>
                ) : String(item.status).toLowerCase() === "queued" ? (
                  <button
                    className="danger-button"
                    type="button"
                    onClick={async () => {
                      try {
                        await platformApi.cancelJob(item._id);
                        await load();
                      } catch (reason) {
                        setError(messageOf(reason));
                      }
                    }}
                  >
                    Hủy
                  </button>
                ) : null,
            },
          ]}
        />
        <Pagination
          page={jobPage}
          pageSize={jobPageSize}
          total={jobs.length}
          onChange={setJobPage}
        />
      </Panel>
      <Panel title="Danh mục mô hình AI">
        <DataTable
          items={models.slice((modelPage - 1) * modelPageSize, modelPage * modelPageSize)}
          empty="Chưa có mô hình AI được đăng ký"
          columns={[
            { key: "provider_id", label: "Nhà cung cấp" },
            { key: "model", label: "Mô hình" },
            { key: "version", label: "Phiên bản" },
            {
              key: "enabled",
              label: "Trạng thái",
              render: (item) => <StatusPill value={item.enabled ? "ACTIVE" : "DISABLED"} />,
            },
            {
              key: "capabilities",
              label: "Năng lực",
              render: (item) => (item.capabilities || []).join(", "),
            },
          ]}
        />
        <Pagination
          page={modelPage}
          pageSize={modelPageSize}
          total={models.length}
          onChange={setModelPage}
        />
      </Panel>
      <PlatformControlsPanel />
      {dialog}
    </div>
  );
}
