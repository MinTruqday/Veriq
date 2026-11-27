"use client";

import { useCallback, useEffect, useMemo, useState } from "react";
import Link from "next/link";
import { testingApi } from "../services/testing.service";
import { downloadTestingFile, testingRequest } from "../services/testing.transport";
import { ErrorState, Panel } from "./WorkspacePrimitives";
import { messageOf } from "../lib/testing";
import { PROJECT_SECTION_SLUGS, projectRoute } from "../routes";

const labels = {
  PASS: "Đạt",
  FAIL: "Thất bại",
  BLOCKED: "Bị chặn",
  SKIPPED: "Bỏ qua",
  NOT_APPLICABLE: "Không áp dụng",
  NOT_RUN: "Chưa chạy",
};
const chartColors = {
  PASS: "hsl(var(--chart-pass))",
  FAIL: "hsl(var(--chart-fail))",
  BLOCKED: "hsl(var(--chart-blocked))",
  SKIPPED: "hsl(var(--chart-skipped))",
  NOT_APPLICABLE: "hsl(var(--chart-not-applicable))",
  NOT_RUN: "hsl(var(--chart-not-run))",
};

function reportQuery(type, planId) {
  return new URLSearchParams({ type, test_plan_id: planId }).toString();
}

function ReportOverview({ report }) {
  const total = Number(report.total) || 0;
  const counts = report.counts || {};
  const completed = Math.max(0, total - (Number(counts.NOT_RUN) || 0));
  const executionRate = total ? Math.round((completed / total) * 100) : null;
  let offset = 0;
  const segments = Object.keys(labels).map((status) => {
    const value = Math.max(0, Number(counts[status]) || 0);
    const start = offset;
    offset += total ? (value / total) * 100 : 0;
    return { status, value, start, end: offset };
  });
  const gradient = segments
    .filter((segment) => segment.value > 0)
    .map((segment) => `${chartColors[segment.status]} ${segment.start}% ${segment.end}%`)
    .join(", ");

  return (
    <section aria-label="Tổng quan kết quả kiểm thử" className="space-y-4">
      <div className="grid gap-3 sm:grid-cols-2 xl:grid-cols-4">
        <Metric label="Tổng số ca trong phạm vi" value={total} />
        <Metric
          label="Đã có kết quả"
          value={
            executionRate === null
              ? "Chưa có dữ liệu"
              : `${completed} / ${total} · ${executionRate}%`
          }
        />
        <Metric
          label="Tỷ lệ đạt trong ca Pass/Fail"
          value={report.pass_rate == null ? "Chưa có dữ liệu" : `${report.pass_rate}%`}
        />
        {report.defects ? (
          <Metric label="Lỗi đang mở" value={`${report.defects.open} / ${report.defects.total}`} />
        ) : (
          <Metric label="Lỗi liên kết" value="Không có dữ liệu theo quyền hiện tại" />
        )}
      </div>
      {total > 0 && (
        <div className="grid gap-4 lg:grid-cols-[minmax(12rem,0.8fr)_minmax(0,1.2fr)]">
          <div className="flex min-w-0 flex-col items-center gap-4 rounded-control border border-border p-4">
            <div
              aria-label={`Phân bố kết quả: ${segments
                .filter((segment) => segment.value > 0)
                .map((segment) => `${labels[segment.status]} ${segment.value}`)
                .join(", ")}`}
              className="relative size-28 shrink-0 rounded-full sm:size-32"
              role="img"
              style={{ background: `conic-gradient(${gradient})` }}
            >
              <div className="absolute inset-[22%] grid place-items-center rounded-full bg-surface text-center">
                <div>
                  <p className="text-xl font-semibold">{total}</p>
                  <p className="text-[11px] text-ink-muted">ca kiểm thử</p>
                </div>
              </div>
            </div>
            <ul className="flex w-full min-w-0 flex-wrap justify-center gap-2 text-xs">
              {segments
                .filter((segment) => segment.value > 0)
                .map((segment) => (
                  <li
                    className="inline-flex min-w-0 items-center gap-1.5 rounded-control bg-surface-quiet px-2 py-1"
                    key={segment.status}
                  >
                    <span
                      aria-hidden="true"
                      className="size-2 shrink-0 rounded-full"
                      style={{ backgroundColor: chartColors[segment.status] }}
                    />
                    <span>{labels[segment.status]}</span>
                    <span className="font-medium tabular-nums">{segment.value}</span>
                  </li>
                ))}
            </ul>
          </div>
          <div className="rounded-control border border-border p-4">
            <h3 className="text-sm font-semibold">Kết quả theo trạng thái</h3>
            <div className="mt-3 space-y-3">
              {segments
                .filter((segment) => segment.value > 0)
                .map((segment) => (
                  <div
                    className="grid grid-cols-[6.5rem_minmax(0,1fr)_2.5rem] items-center gap-3 text-xs"
                    key={segment.status}
                  >
                    <span className="truncate text-ink-muted">{labels[segment.status]}</span>
                    <div
                      className="h-2 overflow-hidden rounded-full bg-surface-quiet"
                      role="progressbar"
                      aria-label={`${labels[segment.status]}: ${segment.value} trên ${total}`}
                      aria-valuemin={0}
                      aria-valuemax={total}
                      aria-valuenow={segment.value}
                    >
                      <div
                        className="h-full rounded-full"
                        style={{
                          width: `${Math.min(100, (segment.value / total) * 100)}%`,
                          backgroundColor: chartColors[segment.status],
                        }}
                      />
                    </div>
                    <span className="text-right font-medium tabular-nums">{segment.value}</span>
                  </div>
                ))}
            </div>
          </div>
        </div>
      )}
    </section>
  );
}

export default function SimpleTestReports({ project }) {
  const permissions = useMemo(
    () => project.current_permissions || [],
    [project.current_permissions],
  );
  const can = (permission) => permissions.includes(permission);
  const canReadProgress = can("teststatusreport.read");
  const canReadCompletion = can("testcompletion.read");
  const canReadReports = canReadProgress || canReadCompletion;
  const canReadPlans = can("testplan.read");
  const reportTypes = useMemo(
    () => [
      ...(canReadProgress ? [{ value: "PROGRESS", label: "Tiến độ" }] : []),
      ...(canReadCompletion ? [{ value: "COMPLETION", label: "Hoàn tất" }] : []),
    ],
    [canReadCompletion, canReadProgress],
  );
  const [plans, setPlans] = useState([]);
  const [reports, setReports] = useState([]);
  const [type, setType] = useState(reportTypes[0]?.value || "PROGRESS");
  const [planId, setPlanId] = useState("");
  const [live, setLive] = useState(null);
  const [selected, setSelected] = useState(null);
  const [error, setError] = useState("");
  const [busy, setBusy] = useState(false);
  const root = `/du-an/${project._id}/bao-cao-kiem-thu`;

  const loadSavedReports = useCallback(async () => {
    if (!canReadReports) return;
    const items = await testingRequest(root);
    setReports(items);
  }, [canReadReports, root]);

  useEffect(() => {
    let active = true;
    Promise.all([
      canReadPlans ? testingApi.listPlans(project._id, { status: "APPROVED" }) : [],
      canReadReports ? testingRequest(root) : [],
    ])
      .then(([planItems, reportItems]) => {
        if (!active) return;
        const approved = Array.isArray(planItems) ? planItems : [];
        setPlans(approved);
        setPlanId((current) => current || approved[0]?._id || "");
        setReports(Array.isArray(reportItems) ? reportItems : []);
      })
      .catch((reason) => {
        if (active) setError(messageOf(reason));
      });
    return () => {
      active = false;
    };
  }, [canReadPlans, canReadReports, project._id, root]);

  useEffect(() => {
    setType(reportTypes[0]?.value || "PROGRESS");
  }, [reportTypes]);

  const loadLive = useCallback(async () => {
    if (selected) return;
    if (!planId || !reportTypes.some((item) => item.value === type)) {
      setLive(null);
      return;
    }
    try {
      const value = await testingRequest(`${root}/tu-dong?${reportQuery(type, planId)}`);
      setLive(value);
      setSelected(null);
      setError("");
    } catch (reason) {
      setLive(null);
      setError(messageOf(reason));
    }
  }, [planId, reportTypes, root, selected, type]);

  useEffect(() => {
    loadLive();
    const timer = window.setInterval(loadLive, 30000);
    window.addEventListener("focus", loadLive);
    return () => {
      window.clearInterval(timer);
      window.removeEventListener("focus", loadLive);
    };
  }, [loadLive]);

  const saveSnapshot = async () => {
    if (!live) return;
    setBusy(true);
    setError("");
    try {
      const saved = await testingRequest(root, {
        method: "POST",
        body: JSON.stringify({
          type: live.type,
          title: live.title,
          test_plan_id: live.test_plan_id,
          test_period_id: live.test_period_id || null,
          test_run_id: null,
          start_at: live.start_at,
          end_at: live.end_at,
          preview_hash: live.preview_hash,
          idempotency_key: crypto.randomUUID(),
        }),
      });
      await loadSavedReports();
      setSelected(saved);
      setLive(null);
    } catch (reason) {
      setError(messageOf(reason));
    } finally {
      setBusy(false);
    }
  };

  const openSavedReport = async (reportId) => {
    setBusy(true);
    setError("");
    try {
      setSelected(await testingRequest(`${root}/${reportId}`));
      setLive(null);
    } catch (reason) {
      setError(messageOf(reason));
    } finally {
      setBusy(false);
    }
  };

  const displayed = live || selected;
  const exportReport = (format) => {
    const path = live
      ? `${root}/tu-dong/xuat?${reportQuery(type, planId)}&format=${format}`
      : `${root}/${selected?._id}/xuat?format=${format}`;
    downloadTestingFile(path, `bao-cao.${format}`).catch((reason) => setError(messageOf(reason)));
  };

  return (
    <div className="space-y-4">
      {error && <ErrorState message={error} />}
      {canReadReports ? (
        <>
          <section
            aria-label="Phạm vi báo cáo"
            className="grid gap-3 rounded-panel border border-border bg-surface p-4 sm:grid-cols-[minmax(0,1fr)_minmax(12rem,0.45fr)] sm:items-end sm:p-5"
          >
            <label className="field-label block min-w-0">
              Kế hoạch đã duyệt
              <select
                className="apple-input mt-2"
                value={planId}
                onChange={(event) => {
                  setSelected(null);
                  setPlanId(event.target.value);
                }}
              >
                <option value="">-</option>
                {plans.map((plan) => (
                  <option key={plan._id} value={plan._id}>
                    {plan.name}
                  </option>
                ))}
              </select>
            </label>
            <label className="field-label block min-w-0">
              Loại báo cáo
              {reportTypes.length > 1 ? (
                <select
                  className="apple-input mt-2"
                  value={type}
                  onChange={(event) => {
                    setSelected(null);
                    setType(event.target.value);
                  }}
                >
                  {reportTypes.map((item) => (
                    <option key={item.value} value={item.value}>
                      {item.label}
                    </option>
                  ))}
                </select>
              ) : (
                <span className="mt-2 flex min-h-10 items-center rounded-control border border-border bg-surface-raised px-3 text-sm text-ink">
                  {reportTypes[0]?.label || "-"}
                </span>
              )}
            </label>
            <p className="text-xs text-ink-muted sm:col-span-2">
              Kết quả mới nhất được tổng hợp tự động và làm mới mỗi 30 giây.
            </p>
          </section>

          {plans.length === 0 ? (
            <Panel title="Chưa có phạm vi để lập báo cáo">
              <div className="space-y-3 p-5 text-sm text-ink-muted">
                <p>
                  Cần có kế hoạch kiểm thử đã duyệt. Hoàn tất Requirement, sau đó tạo kế hoạch có
                  liên kết Requirement và gửi duyệt.
                </p>
                <div className="flex flex-wrap gap-2">
                  <Link
                    className="secondary-button"
                    href={projectRoute(project._id, PROJECT_SECTION_SLUGS.requirements)}
                  >
                    Mở Yêu cầu
                  </Link>
                  {can("testplan.read") && (
                    <Link
                      className="apple-button"
                      href={projectRoute(project._id, PROJECT_SECTION_SLUGS.testPlans)}
                    >
                      Mở kế hoạch kiểm thử
                    </Link>
                  )}
                </div>
              </div>
            </Panel>
          ) : displayed ? (
            <>
              <section className="space-y-3" aria-labelledby="report-preview-title">
                <header className="flex flex-wrap items-start justify-between gap-3">
                  <div className="min-w-0">
                    <p className="text-xs font-medium uppercase tracking-wide text-ink-muted">
                      {selected ? "Bản chốt đã lưu" : "Báo cáo trực tiếp"}
                      {live ? " · Tự làm mới" : ""}
                    </p>
                    <h2 id="report-preview-title" className="mt-1 text-xl font-semibold text-ink">
                      {displayed.title}
                    </h2>
                    <p className="mt-1 text-sm text-ink-muted">
                      {displayed.plan_name} · {displayed.period_name || "Không thuộc đợt"}
                    </p>
                  </div>
                  <div className="flex flex-wrap gap-2">
                    {selected && (
                      <button
                        className="secondary-button"
                        type="button"
                        onClick={() => setSelected(null)}
                      >
                        Báo cáo hiện tại
                      </button>
                    )}
                    {live &&
                      (type === "PROGRESS"
                        ? can("teststatusreport.create")
                        : can("testcompletion.create")) && (
                        <button
                          className="apple-button"
                          type="button"
                          disabled={busy}
                          onClick={saveSnapshot}
                        >
                          {busy ? "Đang lưu…" : "Lưu bản chốt"}
                        </button>
                      )}
                    {can("report.export") &&
                      ["pdf", "docx"].map((format) => (
                        <button
                          className="secondary-button"
                          type="button"
                          key={format}
                          onClick={() => exportReport(format)}
                        >
                          Xuất {format === "pdf" ? "PDF" : "Word"}
                        </button>
                      ))}
                  </div>
                </header>

                <ReportOverview report={displayed} />

                {(displayed.scope_in?.length > 0 ||
                  displayed.environments?.length > 0 ||
                  displayed.builds?.length > 0) && (
                  <dl className="grid gap-3 rounded-control border border-border bg-surface p-4 text-sm sm:grid-cols-3">
                    {displayed.scope_in?.length > 0 && (
                      <div className="min-w-0">
                        <dt className="text-xs text-ink-muted">Phạm vi</dt>
                        <dd className="mt-1 break-words font-medium">
                          {displayed.scope_in.join(", ")}
                        </dd>
                      </div>
                    )}
                    {displayed.environments?.length > 0 && (
                      <div className="min-w-0">
                        <dt className="text-xs text-ink-muted">Môi trường</dt>
                        <dd className="mt-1 break-words font-medium">
                          {displayed.environments.join(", ")}
                        </dd>
                      </div>
                    )}
                    {displayed.builds?.length > 0 && (
                      <div className="min-w-0">
                        <dt className="text-xs text-ink-muted">Bản dựng</dt>
                        <dd className="mt-1 break-words font-medium">
                          {displayed.builds.join(", ")}
                        </dd>
                      </div>
                    )}
                  </dl>
                )}
              </section>

              <Panel title="Kết quả theo ca kiểm thử" className="min-w-0">
                <div className="border-b border-border px-4 py-3 text-xs text-ink-muted sm:px-5">
                  Mỗi ca lấy kết quả mới nhất kể từ khi kế hoạch được duyệt. Tỷ lệ đạt tính trên{" "}
                  {displayed.pass_rate_denominator ?? 0} ca có kết luận Pass hoặc Fail.
                </div>
                <div className="overflow-x-auto">
                  <table className="w-full min-w-[38rem] text-left text-sm">
                    <thead className="bg-surface-quiet text-xs text-ink-muted">
                      <tr>
                        <th className="px-4 py-3 font-medium sm:px-5">Mã ca</th>
                        <th className="px-4 py-3 font-medium sm:px-5">Ca kiểm thử</th>
                        <th className="px-4 py-3 font-medium sm:px-5">Kết quả mới nhất</th>
                        <th className="px-4 py-3 font-medium sm:px-5">Lần chạy</th>
                      </tr>
                    </thead>
                    <tbody className="divide-y divide-border">
                      {(displayed.case_results || []).map((item) => (
                        <tr key={item.test_case_version_id}>
                          <td className="whitespace-nowrap px-4 py-3 font-medium sm:px-5">
                            {item.test_case_key}
                          </td>
                          <td className="max-w-0 px-4 py-3 sm:px-5">
                            <span className="block truncate" title={item.title}>
                              {item.title}
                            </span>
                            <span className="mt-0.5 block text-xs text-ink-muted">
                              Phiên bản {item.version || "—"}
                            </span>
                          </td>
                          <td className="whitespace-nowrap px-4 py-3">
                            <span className="inline-flex rounded-full border border-border bg-surface-quiet px-2.5 py-1 text-xs font-medium">
                              {labels[item.status] || item.status}
                            </span>
                          </td>
                          <td className="max-w-48 px-4 py-3 sm:px-5">
                            {item.test_run_id ? (
                              <Link
                                className="block truncate text-brand hover:underline"
                                href={projectRoute(
                                  project._id,
                                  PROJECT_SECTION_SLUGS.testRuns,
                                  item.test_run_id,
                                )}
                              >
                                {item.test_run_name || item.test_run_id}
                              </Link>
                            ) : (
                              <span className="text-ink-muted">Chưa chạy</span>
                            )}
                          </td>
                        </tr>
                      ))}
                    </tbody>
                  </table>
                </div>
              </Panel>

              {displayed.type === "COMPLETION" && (
                <Panel title="Tiêu chí kết thúc" className="min-w-0">
                  <div className="p-4 sm:p-5">
                    {displayed.exit_criteria?.length ? (
                      <ul className="divide-y divide-border text-sm">
                        {displayed.exit_criteria.map((criterion, index) => (
                          <li
                            className="flex items-start gap-3 py-3 first:pt-0 last:pb-0"
                            key={`${criterion}-${index}`}
                          >
                            <span
                              aria-hidden="true"
                              className="mt-0.5 size-4 shrink-0 rounded border border-border"
                            />
                            <span className="min-w-0 flex-1">{criterion}</span>
                            <span className="shrink-0 text-xs text-ink-muted">Chưa đánh giá</span>
                          </li>
                        ))}
                      </ul>
                    ) : (
                      <p className="text-sm text-ink-muted">
                        Chưa cấu hình tiêu chí kết thúc trong kế hoạch.
                      </p>
                    )}
                    <p className="mt-4 border-t border-border pt-3 text-xs text-ink-muted">
                      Người phụ trách quyết định việc chấp nhận kết quả hoặc phát hành.
                    </p>
                  </div>
                </Panel>
              )}
            </>
          ) : (
            <Panel title="Đang tổng hợp báo cáo">
              <p className="p-5 text-sm text-ink-muted">Đang tải kết quả cho kế hoạch đã chọn.</p>
            </Panel>
          )}

          <Panel title="Lịch sử báo cáo đã lưu" className="min-w-0">
            {reports.length ? (
              <div className="divide-y divide-border">
                {reports.map((report) => (
                  <button
                    aria-pressed={selected?._id === report._id}
                    className={`grid w-full gap-2 p-4 text-left transition hover:bg-surface-raised sm:grid-cols-[minmax(0,1fr)_auto] sm:items-center sm:px-5 ${selected?._id === report._id ? "bg-brand-soft/40" : ""}`}
                    type="button"
                    key={report._id}
                    onClick={() => openSavedReport(report._id)}
                  >
                    <span className="min-w-0">
                      <span className="block break-words text-sm font-semibold text-ink">
                        {report.title}
                      </span>
                      <span className="mt-1 block break-words text-xs text-ink-muted">
                        {report.type === "PROGRESS" ? "Tiến độ" : "Hoàn tất"} · {report.plan_name}
                        {report.period_name ? ` · ${report.period_name}` : ""}
                      </span>
                    </span>
                    <span className="text-xs font-medium text-brand">
                      {busy && selected?._id === report._id ? "Đang mở…" : "Mở bản chốt"}
                    </span>
                  </button>
                ))}
              </div>
            ) : (
              <p className="p-4 text-sm text-ink-muted">
                Chưa có bản chốt. Báo cáo trực tiếp vẫn được tổng hợp từ dữ liệu hiện tại.
              </p>
            )}
          </Panel>
        </>
      ) : (
        <Panel title="Báo cáo">
          <p className="p-4 text-sm text-ink-muted">
            Tài khoản hiện tại không có quyền xem báo cáo trong dự án này.
          </p>
        </Panel>
      )}
    </div>
  );
}

function Metric({ label, value }) {
  return (
    <div className="rounded-control bg-surface-raised p-3">
      <p className="text-sm text-ink-muted">{label}</p>
      <p className="mt-1 font-semibold">{value}</p>
    </div>
  );
}
