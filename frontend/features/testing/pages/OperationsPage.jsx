"use client";
import { useDateTimeOptions } from "../hooks/useDateTimeOptions";
import { useCallback, useEffect, useRef, useState } from "react";
import { RotateCcw } from "lucide-react";
import DataTable from "../components/DataTable";
import PlatformOperationsPanel from "../components/PlatformOperationsPanel";
import PlatformUsersPanel from "../components/PlatformUsersPanel";
import ResourceCapacityPanel from "../components/ResourceCapacityPanel";
import {
  ErrorState,
  LoadingState,
  Metric,
  Panel,
  WorkspacePage,
  StatusPill,
} from "../components/WorkspacePrimitives";
import { Pagination } from "@/shared/components/ui/Pagination";
import SegmentedTabs from "@/shared/components/navigation/SegmentedTabs";
import { formatDate as formatDateValue, messageOf, valueLabel } from "../lib/testing";
import { testingApi } from "../services/testing.service";
import { useAuth } from "@/features/authentication/contexts/AuthContext";
import { useRouter } from "next/navigation";
import { formatNumber } from "@/shared/lib/locale.mjs";

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

function formatStorageSize(value, locale) {
  if (value == null || value === "") return "Chưa có dữ liệu";
  const bytes = Number(value);
  if (!Number.isFinite(bytes)) return "Chưa có dữ liệu";
  if (bytes === 0) return "0 byte";
  if (bytes < 1000) return `${formatNumber(Math.round(bytes), locale)} byte`;
  const units = ["kB", "MB", "GB", "TB"];
  let size = bytes;
  let unitIndex = -1;
  while (size >= 1000 && unitIndex < units.length - 1) {
    size /= 1000;
    unitIndex += 1;
  }
  return `${formatNumber(size, locale, { maximumFractionDigits: 1 })} ${units[unitIndex]}`;
}

export default function OperationsPage() {
  const dateTimeOptions = useDateTimeOptions();
  const formatDate = (value) => formatDateValue(value, dateTimeOptions);
  const { user, isLoading: authLoading } = useAuth();
  const router = useRouter();
  const [section, setSection] = useState("overview");
  const [overviewSection, setOverviewSection] = useState("summary");
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
  useEffect(() => {
    if (authLoading) return;
    if (!user) {
      router.replace("/dang-nhap");
      return;
    }
    if (!isPlatformAdmin) router.replace("/du-an");
  }, [authLoading, isPlatformAdmin, router, user]);
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
    {
      _id: "impact_degraded",
      name: "Lượt phân tích có giới hạn",
      count: impactMetrics.degraded || 0,
    },
    {
      _id: "impact_success_rate",
      name: "Tỷ lệ thành công",
      count: `${Math.round((impactMetrics.success_rate || 0) * 100)}%`,
    },
    {
      _id: "impact_latency",
      name: "Thời gian xử lý trung bình",
      count: `${Math.round(impactMetrics.average_latency_ms || 0)} mili giây`,
    },
  ];
  if (authLoading)
    return (
      <div className="p-8">
        <LoadingState />
      </div>
    );
  if (!isPlatformAdmin) return <LoadingState />;
  return (
    <WorkspacePage title="Vận hành nền tảng">
      <SegmentedTabs
        label="Khu vực quản trị"
        value={section}
        onChange={(value) => {
          setSection(value);
          setError("");
        }}
        tabs={[
          { id: "overview", label: "Tổng quan" },
          { id: "users", label: "Tài khoản" },
          { id: "capacity", label: "Công suất" },
          { id: "platform", label: "Cấu hình nền tảng" },
        ]}
      />
      {error && <ErrorState message={error} />}
      {section === "users" ? (
        <PlatformUsersPanel />
      ) : section === "capacity" ? (
        <ResourceCapacityPanel />
      ) : section === "platform" ? (
        <PlatformOperationsPanel />
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
          <SegmentedTabs
            label="Tổng quan vận hành"
            value={overviewSection}
            onChange={setOverviewSection}
            tabs={[
              { id: "summary", elementId: "operations-overview-tab-summary", label: "Tình trạng" },
              { id: "issues", elementId: "operations-overview-tab-issues", label: "Sự cố" },
              {
                id: "storage",
                elementId: "operations-overview-tab-storage",
                label: "Dung lượng",
              },
              { id: "audit", elementId: "operations-overview-tab-audit", label: "Nhật ký" },
            ]}
          />
          {overviewSection === "summary" ? (
            <section aria-label="Tình trạng vận hành" className="space-y-5">
              <div className="grid grid-cols-2 gap-3 xl:grid-cols-4">
                <Metric label="Tài liệu chờ lập chỉ mục" value={value.knowledge_indexing_backlog} />
                <Metric
                  label="Lần nhập liệu bị lỗi"
                  value={(value.failed_ingestion_jobs || []).length}
                />
                <Metric
                  label="Phân tích ảnh hưởng lỗi"
                  value={(value.failed_impact_jobs || []).length}
                />
                <Metric label="Lỗi xử lý nền" value={(value.worker_failures || []).length} />
              </div>
              <div className="grid items-start gap-5 xl:grid-cols-2">
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
                        align: "center",
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
            </section>
          ) : null}
          {overviewSection === "issues" ? (
            <section aria-label="Sự cố vận hành" className="space-y-5">
              <Panel title="Lần nhập liệu bị lỗi">
                <DataTable
                  items={value.failed_ingestion_jobs || []}
                  empty="Không có lần nhập liệu bị lỗi"
                  columns={[
                    {
                      key: "summary",
                      label: "Thông tin",
                      render: (item) => (
                        <div className="grid gap-1">
                          <span className="font-medium">Không nhập được tài liệu</span>
                          <OperationalDiagnostics item={item} includeFileName />
                        </div>
                      ),
                    },
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
              </Panel>
              <Panel title="Lỗi xử lý nền">
                <DataTable
                  items={value.worker_failures || []}
                  empty="Không có lỗi xử lý nền"
                  columns={[
                    {
                      key: "summary",
                      label: "Công việc",
                      render: (item) => (
                        <div className="grid gap-1">
                          <span className="font-medium">{operationalEventSummary(item.event)}</span>
                          <OperationalDiagnostics item={item} includeEvent />
                        </div>
                      ),
                    },
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
                          aria-label={`Thử lại công việc ${item._id}`}
                          title={retryingJobs.has(item._id) ? "Đang thử lại" : "Thử lại"}
                          className="icon-button h-9 w-9"
                          type="button"
                          disabled={retryingJobs.has(item._id)}
                          onClick={() => retryJob(item._id)}
                        >
                          <RotateCcw aria-hidden="true" size={16} />
                        </button>
                      ),
                    },
                  ]}
                />
              </Panel>
              <Panel title="Phân tích ảnh hưởng cần xem lại">
                <DataTable
                  items={value.failed_impact_jobs || []}
                  empty="Không có phân tích ảnh hưởng cần xem lại"
                  columns={[
                    {
                      key: "summary",
                      label: "Thông tin",
                      render: (item) => (
                        <div className="grid gap-1">
                          <span className="font-medium">Phân tích chưa hoàn tất</span>
                          <OperationalDiagnostics item={item} />
                        </div>
                      ),
                    },
                    {
                      key: "status",
                      label: "Trạng thái",
                      render: (item) => <StatusPill value={item.status} />,
                    },
                    {
                      key: "updated_at",
                      label: "Cập nhật",
                      render: (item) => formatDate(item.updated_at),
                    },
                  ]}
                />
              </Panel>
            </section>
          ) : null}
          {overviewSection === "storage" ? (
            <section aria-label="Dung lượng dự án">
              <Panel title="Dung lượng theo dự án">
                <DataTable
                  items={visibleStorageUsage}
                  empty="Chưa có dữ liệu dung lượng"
                  columns={[
                    {
                      key: "project_key",
                      label: "Dự án",
                      render: (item) => (
                        <div className="grid gap-0.5">
                          <span className="font-medium">{item.project_name || "Dự án"}</span>
                          {item.project_key && (
                            <span className="text-xs text-ink-muted">{item.project_key}</span>
                          )}
                        </div>
                      ),
                    },
                    { key: "files", label: "Tệp" },
                    {
                      key: "bytes",
                      label: "Dung lượng",
                      render: (item) => formatStorageSize(item.bytes, dateTimeOptions.locale),
                    },
                  ]}
                />
                <Pagination
                  page={storagePage}
                  pageSize={storagePageSize}
                  total={storageUsage.length}
                  onChange={setStoragePage}
                />
              </Panel>
            </section>
          ) : null}
          {overviewSection === "audit" ? (
            <section aria-label="Nhật ký hệ thống">
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
                    placeholder="Sự kiện, mã đối tượng hoặc người thực hiện"
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
            </section>
          ) : null}
        </>
      )}
    </WorkspacePage>
  );
}

function operationalEventSummary(event) {
  if (!event) return "Tác vụ nền chưa hoàn tất";
  const label = valueLabel(event);
  return label === event ? "Tác vụ nền chưa hoàn tất" : label;
}

function OperationalDiagnostics({ item, includeEvent = false, includeFileName = false }) {
  return (
    <details className="text-xs text-ink-muted">
      <summary className="w-fit cursor-pointer">Chi tiết xử lý</summary>
      <dl className="mt-1 grid gap-1 break-all">
        {includeFileName && (item.file_name || item.filename || item.name) && (
          <div>
            <dt className="inline">Tệp: </dt>
            <dd className="inline">{item.file_name || item.filename || item.name}</dd>
          </div>
        )}
        {item._id && (
          <div>
            <dt className="inline">Mã bản ghi: </dt>
            <dd className="inline font-mono">{item._id}</dd>
          </div>
        )}
        {includeEvent && item.event && (
          <div>
            <dt className="inline">Mã sự kiện: </dt>
            <dd className="inline font-mono">{item.event}</dd>
          </div>
        )}
        {item.error_code && (
          <div>
            <dt className="inline">Mã lỗi: </dt>
            <dd className="inline font-mono">{item.error_code}</dd>
          </div>
        )}
      </dl>
    </details>
  );
}
