"use client";
import { useCallback, useEffect, useRef, useState } from "react";
import DataTable from "../components/DataTable";
import PlatformOperationsPanel from "../components/PlatformOperationsPanel";
import PlatformUsersPanel from "../components/PlatformUsersPanel";
import PayrollImportPanel from "../components/PayrollImportPanel";
import TestabilityBenchmarkPanel from "../components/TestabilityBenchmarkPanel";
import {
  ErrorState,
  LoadingState,
  Metric,
  Panel,
  WorkspacePage,
  StatusPill,
} from "../components/WorkspacePrimitives";
import { Pagination } from "@/shared/components/ui/Pagination";
import { formatDate, messageOf, valueLabel } from "../lib/testing";
import { testingApi } from "../services/testing.service";
import { useAuth } from "@/features/authentication/contexts/AuthContext";

const taskLabels = {
  impact_analysis: "Phân tích ảnh hưởng",
  maintenance_proposal: "Đề xuất bảo trì",
  regression: "Kiểm thử hồi quy",
};

const modelLabels = {
  evidence_impact_analysis: "Phân tích ảnh hưởng dựa trên bằng chứng",
  maintenance_analysis: "Phân tích bảo trì",
  risk_scoring: "Chấm điểm rủi ro",
};

export default function OperationsPage() {
  const { user, isLoading: authLoading } = useAuth();
  const [section, setSection] = useState("overview");
  const [value, setValue] = useState(null);
  const [error, setError] = useState("");
  const [loading, setLoading] = useState(false);
  const [auditQuery, setAuditQuery] = useState("");
  const [storagePage, setStoragePage] = useState(1);
  const [auditPage, setAuditPage] = useState(1);
  const [retryingJobs, setRetryingJobs] = useState(() => new Set());
  const retryingJobsRef = useRef(new Set());
  const storagePageSize = 10;
  const auditPageSize = 20;
  const isPlatformAdmin = user?.system_role === "ADMIN";
  const load = useCallback(async () => {
    setLoading(true);
    setError("");
    try {
      setValue(await testingApi.operations());
    } catch (reason) {
      setError(messageOf(reason));
    } finally {
      setLoading(false);
    }
  }, []);
  useEffect(() => {
    if (authLoading || !user || !isPlatformAdmin) return;
    void load();
  }, [authLoading, isPlatformAdmin, load, user]);
  const retryJob = async (jobId) => {
    if (retryingJobsRef.current.has(jobId)) return;
    retryingJobsRef.current.add(jobId);
    setRetryingJobs(new Set(retryingJobsRef.current));
    try {
      await testingApi.retryOperationJob(jobId);
      await load();
    } catch (reason) {
      setError(messageOf(reason));
    } finally {
      retryingJobsRef.current.delete(jobId);
      setRetryingJobs(new Set(retryingJobsRef.current));
    }
  };
  const auditEvents = (value?.audit_events || []).filter((item) => {
    const query = auditQuery.trim().toLowerCase();
    return (
      !query ||
      [item.action, item.entity_type, item.entity_id, item.actor_label, item.actor_id].some(
        (field) =>
          String(field || "")
            .toLowerCase()
            .includes(query),
      )
    );
  });
  const impactMetrics = value?.ai_request_metrics?.impact_classification || {};
  const storageUsage = value?.storage_usage || [];
  const visibleStorageUsage = storageUsage.slice(
    (storagePage - 1) * storagePageSize,
    storagePage * storagePageSize,
  );
  const visibleAuditEvents = auditEvents.slice(
    (auditPage - 1) * auditPageSize,
    auditPage * auditPageSize,
  );
  const aiMetrics = [
    { _id: "impact_total", name: "Lượt phân loại ảnh hưởng", count: impactMetrics.total || 0 },
    { _id: "impact_success", name: "Lượt phân loại thành công", count: impactMetrics.success || 0 },
    { _id: "impact_degraded", name: "Lượt xử lý giới hạn", count: impactMetrics.degraded || 0 },
    {
      _id: "impact_success_rate",
      name: "Tỷ lệ thành công",
      count: `${Math.round((impactMetrics.success_rate || 0) * 100)}%`,
    },
    {
      _id: "impact_latency",
      name: "Độ trễ trung bình",
      count: `${Math.round(impactMetrics.average_latency_ms || 0)} mili giây`,
    },
  ];
  if (authLoading)
    return (
      <div className="p-8">
        <LoadingState />
      </div>
    );
  if (!isPlatformAdmin) return null;
  return (
    <WorkspacePage title="Vận hành nền tảng">
      <nav
        aria-label="Khu vực quản trị"
        className="flex max-w-full gap-1 overflow-x-auto rounded-xl bg-surface-quiet p-1"
      >
        {[
          ["overview", "Tổng quan"],
          ["users", "Tài khoản"],
          ["payroll", "Bảng lương"],
          ["platform", "Cấu hình nền tảng"],
          ["benchmark", "Đánh giá AI"],
        ].map(([value, label]) => (
          <button
            key={value}
            type="button"
            aria-current={section === value ? "page" : undefined}
            className={`min-h-10 shrink-0 rounded-lg px-4 text-[13px] font-semibold transition ${
              section === value ? "bg-surface text-ink shadow-sm" : "text-ink-muted hover:text-ink"
            }`}
            onClick={() => {
              setSection(value);
              setError("");
            }}
          >
            {label}
          </button>
        ))}
      </nav>
      {error && <ErrorState message={error} />}
      {section === "users" ? (
        <PlatformUsersPanel />
      ) : section === "payroll" ? (
        <PayrollImportPanel />
      ) : section === "platform" ? (
        <PlatformOperationsPanel />
      ) : section === "benchmark" ? (
        <TestabilityBenchmarkPanel />
      ) : !value ? (
        loading ? (
          <LoadingState />
        ) : error ? (
          <div className="space-y-3">
            <button className="secondary-button" type="button" onClick={() => void load()}>
              Thử tải lại
            </button>
          </div>
        ) : (
          <LoadingState />
        )
      ) : (
        <>
          <div className="grid grid-cols-2 gap-3 xl:grid-cols-4">
            <Metric label="Tài liệu chờ lập chỉ mục" value={value.knowledge_indexing_backlog} />
            <Metric label="Lần nhập liệu bị lỗi" value={value.failed_ingestion_jobs.length} />
            <Metric label="Phân tích ảnh hưởng lỗi" value={value.failed_impact_jobs.length} />
            <Metric label="Lỗi xử lý nền" value={value.worker_failures.length} />
          </div>
          <div className="grid gap-5 xl:grid-cols-2">
            <Panel title="Mô hình đang hoạt động">
              <DataTable
                items={Object.entries(value.ai_models).map(([name, version]) => ({
                  _id: name,
                  name,
                  version,
                }))}
                columns={[
                  {
                    key: "name",
                    label: "Tác vụ",
                    render: (item) => taskLabels[item.name] || item.name,
                  },
                  {
                    key: "version",
                    label: "Phiên bản",
                    render: (item) => modelLabels[item.version] || item.version,
                  },
                ]}
              />
            </Panel>
            <Panel title="Số liệu phân tích ảnh hưởng bằng AI">
              <DataTable
                items={aiMetrics}
                columns={[
                  { key: "name", label: "Loại" },
                  { key: "count", label: "Số lượng" },
                ]}
              />
            </Panel>
          </div>
          <Panel title="Lần nhập liệu bị lỗi">
            <DataTable
              items={value.failed_ingestion_jobs}
              empty="Không có lần nhập liệu bị lỗi"
              columns={[
                { key: "_id", label: "Mã" },
                {
                  key: "status",
                  label: "Trạng thái",
                  render: (item) => <StatusPill value={item.status} />,
                },
                { key: "error_code", label: "Mã lỗi" },
                {
                  key: "created_at",
                  label: "Thời điểm",
                  render: (item) => formatDate(item.created_at),
                },
              ]}
            />
          </Panel>
          <Panel title="Lỗi xử lý nền">
            <DataTable
              items={value.worker_failures}
              empty="Không có lỗi xử lý nền"
              columns={[
                { key: "_id", label: "Mã" },
                { key: "event", label: "Sự kiện" },
                { key: "error_code", label: "Mã lỗi" },
                {
                  key: "completed_at",
                  label: "Thời điểm",
                  render: (item) => formatDate(item.completed_at),
                },
                {
                  key: "retry",
                  label: "Thao tác",
                  render: (item) => (
                    <button
                      className="secondary-button"
                      type="button"
                      disabled={retryingJobs.has(item._id)}
                      onClick={() => retryJob(item._id)}
                    >
                      {retryingJobs.has(item._id) ? "Đang thử lại…" : "Thử lại"}
                    </button>
                  ),
                },
              ]}
            />
          </Panel>
          <Panel title="Dung lượng theo dự án">
            <DataTable
              items={visibleStorageUsage}
              empty="Chưa có dữ liệu dung lượng"
              columns={[
                { key: "project_key", label: "Dự án" },
                { key: "files", label: "Tệp" },
                { key: "bytes", label: "Dung lượng theo byte" },
              ]}
            />
            <Pagination
              page={storagePage}
              pageSize={storagePageSize}
              total={storageUsage.length}
              onChange={setStoragePage}
            />
          </Panel>
          <Panel
            title="Nhật ký hệ thống"
            actions={
              <input
                aria-label="Tìm trong nhật ký"
                id="operations-audit-query"
                className="apple-input w-full sm:w-80"
                value={auditQuery}
                onChange={(event) => {
                  setAuditQuery(event.target.value);
                  setAuditPage(1);
                }}
                placeholder="Sự kiện mã đối tượng hoặc người thực hiện"
              />
            }
          >
            <DataTable
              items={visibleAuditEvents}
              empty="Không có sự kiện phù hợp"
              columns={[
                {
                  key: "action",
                  label: "Sự kiện",
                  render: (item) => valueLabel(item.action),
                },
                {
                  key: "entity_type",
                  label: "Loại",
                  render: (item) => valueLabel(item.entity_type),
                },
                { key: "entity_id", label: "Mã" },
                { key: "actor_label", label: "Người thực hiện" },
                {
                  key: "created_at",
                  label: "Thời điểm",
                  render: (item) => formatDate(item.created_at),
                },
              ]}
            />
            <Pagination
              page={auditPage}
              pageSize={auditPageSize}
              total={auditEvents.length}
              onChange={setAuditPage}
            />
          </Panel>
        </>
      )}
    </WorkspacePage>
  );
}
