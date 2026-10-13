"use client";
import Link from "next/link";
import { useEffect, useState } from "react";
import DataTable from "../../components/DataTable";
import {
  ErrorState,
  LoadingState,
  Metric,
  Panel,
  WorkspacePage,
  StatusPill,
  useActionDialog,
} from "../../components/WorkspacePrimitives";
import { testingApi } from "../../services/testing.service";
import { formatDate, messageOf, valueLabel } from "../../lib/testing";

export default function DashboardPage({ project }) {
  const { ask, dialog } = useActionDialog();
  const [value, setValue] = useState(null);
  const [error, setError] = useState("");
  const [progress, setProgress] = useState({
    percent: project.project_completion_percent ?? 0,
    revision: project.revision,
    taskSummary: project.task_summary,
  });
  const isQa = project.current_membership?.project_role === "QA";
  useEffect(() => {
    Promise.all([
      testingApi.dashboard(project._id),
      testingApi.coverage(project._id),
      testingApi.getProject(project._id),
    ])
      .then(([dashboard, coverage, currentProject]) => {
        setValue({ ...dashboard, ...coverage });
        setProgress({
          percent: currentProject.project_completion_percent ?? 0,
          revision: currentProject.revision,
          taskSummary: currentProject.task_summary,
        });
      })
      .catch((reason) => setError(messageOf(reason)));
  }, [project._id]);
  const base = `/du-an/${project._id}`;
  return (
    <WorkspacePage title={project.name}>
      {error && <ErrorState message={error} />}
      {!value ? (
        <LoadingState />
      ) : (
        <>
          <Panel
            title="Tiến độ dự án"
            actions={
              isQa ? (
                <button
                  className="secondary-button"
                  type="button"
                  onClick={async () => {
                    const answer = await ask({
                      title: "Cập nhật tiến độ dự án",
                      confirmLabel: "Lưu tiến độ",
                      fields: [
                        {
                          name: "project_completion_percent",
                          label: "Project %",
                          type: "number",
                          initialValue: String(progress.percent),
                          required: true,
                        },
                        { name: "note", label: "Ghi chú", multiline: true, required: true },
                      ],
                    });
                    if (!answer) return;
                    try {
                      const updated = await testingApi.updateProjectProgress(project._id, {
                        expected_revision: progress.revision,
                        project_completion_percent: Number(answer.project_completion_percent),
                        note: answer.note.trim(),
                      });
                      setProgress((current) => ({
                        ...current,
                        percent: updated.project_completion_percent,
                        revision: updated.revision,
                      }));
                    } catch (reason) {
                      setError(messageOf(reason));
                    }
                  }}
                >
                  Cập nhật tiến độ
                </button>
              ) : null
            }
          >
            <div className="grid gap-5 p-5 lg:grid-cols-2">
              <div>
                <div className="flex items-center justify-between text-sm">
                  <span>Project {progress.percent}%</span>
                  <span className="text-ink-muted">Đánh giá của QA</span>
                </div>
                <div className="mt-3 h-2 overflow-hidden rounded-full bg-surface-quiet">
                  <div
                    className="h-full rounded-full bg-brand"
                    style={{ width: `${progress.percent}%` }}
                  />
                </div>
              </div>
              <div>
                <div className="flex items-center justify-between text-sm">
                  <span>
                    {progress.taskSummary?.completion_percent === null
                      ? "Chưa có công việc"
                      : `Tasks ${progress.taskSummary?.completion_percent ?? 0}%`}
                  </span>
                  <span className="text-ink-muted">
                    {progress.taskSummary?.completed ?? 0} hoàn thành
                  </span>
                </div>
                {progress.taskSummary?.completion_percent !== null && (
                  <div className="mt-3 h-2 overflow-hidden rounded-full bg-surface-quiet">
                    <div
                      className="h-full rounded-full bg-brand"
                      style={{ width: `${progress.taskSummary?.completion_percent ?? 0}%` }}
                    />
                  </div>
                )}
              </div>
            </div>
          </Panel>
          <div className="grid grid-cols-2 gap-3 xl:grid-cols-4">
            <Metric label="Yêu cầu" value={value.requirements} />
            <Metric label="Kiểm thử đang hoạt động" value={value.active_tests} />
            <Metric label="Lỗi đang mở" value={value.open_defects} />
            <Metric label="Độ phủ yêu cầu" value={`${value.requirement_coverage}%`} />
          </div>
          <details className="rounded-panel border border-border bg-surface p-4 shadow-card">
            <summary className="cursor-pointer text-sm font-medium">
              Chỉ số chất lượng chi tiết
            </summary>
            <div className="mt-4 grid grid-cols-2 gap-3 xl:grid-cols-4">
              <Metric label="Kiểm thử cần cập nhật" value={value.tests_needing_update} />
              <Metric
                label="Độ phủ tiêu chí chấp nhận"
                value={`${value.acceptance_criterion_coverage}%`}
              />
              <Metric label="Độ phủ còn hiệu lực" value={`${value.fresh_coverage}%`} />
              <Metric label="Độ phủ thực thi" value={`${value.execution_coverage}%`} />
              <Metric label="Đề xuất chờ duyệt" value={value.pending_proposals} />
              <Metric label="Lần chạy hiện tại" value={value.current_runs} />
              <Metric label="Thay đổi chờ rà soát" value={value.changes_waiting_impact} />
            </div>
          </details>
          <div className="grid gap-4 lg:grid-cols-3">
            <Panel title="Luồng công việc" className="lg:col-span-2">
              <div className="grid gap-3 p-5 sm:grid-cols-2">
                {[
                  ["yeu-cau", "Yêu cầu"],
                  ["thiet-ke-kiem-thu", "Thiết kế kiểm thử"],
                  ["truy-vet", "Truy vết"],
                  ["thay-doi", "Phân tích thay đổi"],
                  ["ra-soat-ai", "Rà soát đề xuất AI"],
                  ["thuc-thi", "Thực thi kiểm thử"],
                  ["loi", "Lỗi"],
                  ["bao-cao", "Báo cáo"],
                ].map(([href, label]) => (
                  <Link
                    className="rounded-control border border-border p-4 text-[13px] font-semibold hover:border-brand hover:text-brand"
                    href={`${base}/${href}`}
                    key={href}
                  >
                    {label}
                  </Link>
                ))}
              </div>
            </Panel>
            <Panel title="Tài liệu tham chiếu">
              <div className="space-y-3 p-5">
                <Link className="apple-button w-full" href={`${base}/tri-thuc`}>
                  Xem tài liệu tham chiếu
                </Link>
              </div>
            </Panel>
          </div>
          <div className="grid gap-4 lg:grid-cols-2">
            <Panel title="Lỗi đang mở theo mức độ">
              <div className="grid grid-cols-2 gap-3 p-5 sm:grid-cols-5">
                {Object.entries(value.open_defects_by_severity || {}).map(([severity, count]) => (
                  <div className="rounded-xl border border-border p-3" key={severity}>
                    <p className="text-[11px] text-ink-muted">{valueLabel(severity)}</p>
                    <p className="mt-1 text-xl font-semibold">{count}</p>
                  </div>
                ))}
              </div>
            </Panel>
            <Panel title="Lần chạy mới nhất">
              {value.latest_run ? (
                <div className="space-y-3 p-5">
                  <div className="flex flex-wrap items-center justify-between gap-3">
                    <Link
                      className="font-semibold text-brand"
                      href={`${base}/thuc-thi/${value.latest_run._id}`}
                    >
                      {value.latest_run.name}
                    </Link>
                    <StatusPill value={value.latest_run.status} />
                  </div>
                  <p className="text-[12px] text-ink-muted">
                    Bản dựng {value.latest_run.build || "Chưa đặt"} tại{" "}
                    {value.latest_run.environment || "Chưa đặt"}
                  </p>
                  <div className="flex flex-wrap gap-3 text-[12px]">
                    {Object.entries(value.latest_run.result_counts || {}).map(([status, count]) => (
                      <span className="rounded-full border border-border px-3 py-1" key={status}>
                        {status} {count}
                      </span>
                    ))}
                  </div>
                </div>
              ) : (
                <p className="p-5 text-[13px] text-ink-muted">Chưa có lần chạy</p>
              )}
            </Panel>
          </div>
          <Panel title="Thay đổi gần đây">
            <DataTable
              items={value.recent_changes}
              empty="Chưa có bộ thay đổi"
              columns={[
                { key: "requirement_label", label: "Yêu cầu" },
                {
                  key: "status",
                  label: "Trạng thái",
                  render: (item) => <StatusPill value={item.status} />,
                },
                {
                  key: "created_at",
                  label: "Tạo lúc",
                  render: (item) => formatDate(item.created_at),
                },
              ]}
            />
          </Panel>
        </>
      )}
      {dialog}
    </WorkspacePage>
  );
}
