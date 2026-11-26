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

function reportQuery(type, planId) {
  return new URLSearchParams({ type, test_plan_id: planId }).toString();
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
    <div className="space-y-5">
      {error && <ErrorState message={error} />}
      {canReadReports && (
        <Panel title="Báo cáo hiện tại">
          <div className="space-y-4 p-5">
            <p className="text-sm text-ink-muted">
              Báo cáo được tổng hợp tự động từ kết quả mới nhất của từng ca trong kế hoạch. Dữ liệu
              tự làm mới khi mở lại trang, quay lại tab hoặc mỗi 30 giây.
            </p>
            <div className="grid gap-4 md:grid-cols-2">
              <label className="field-label block">
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
              {reportTypes.length > 1 ? (
                <label className="field-label block">
                  Loại báo cáo
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
                </label>
              ) : (
                <div className="field-label">
                  Loại báo cáo
                  <p className="mt-2 rounded-control border border-border px-4 py-3">
                    {reportTypes[0]?.label || "-"}
                  </p>
                </div>
              )}
            </div>
            {plans.length === 0 ? (
              <div className="rounded-control border border-border p-4 text-sm">
                Chưa có kế hoạch kiểm thử được duyệt. Hãy hoàn tất Requirement tại{" "}
                <Link
                  className="text-brand hover:underline"
                  href={projectRoute(project._id, PROJECT_SECTION_SLUGS.requirements)}
                >
                  Yêu cầu
                </Link>
                , sau đó lập kế hoạch có liên kết Requirement và gửi duyệt.
                {can("testplan.read") && (
                  <span>
                    {" "}
                    <Link
                      className="text-brand hover:underline"
                      href={projectRoute(project._id, PROJECT_SECTION_SLUGS.testPlans)}
                    >
                      Mở kế hoạch kiểm thử
                    </Link>
                  </span>
                )}
              </div>
            ) : displayed ? (
              <div className="space-y-3 rounded-control border border-border p-4">
                <div className="flex flex-wrap items-start justify-between gap-3">
                  <div>
                    <h2 className="text-lg font-semibold">{displayed.title}</h2>
                    <p className="text-sm text-ink-muted">
                      {displayed.plan_name} · {displayed.period_name || "Không thuộc đợt"}
                    </p>
                  </div>
                  {live && (
                    <span className="rounded-full bg-brand/10 px-3 py-1 text-sm text-brand">
                      Đang cập nhật
                    </span>
                  )}
                </div>
                <p className="text-sm">Phạm vi: {displayed.scope_in?.join(", ") || "-"}</p>
                {displayed.environments?.length > 0 && (
                  <p className="text-sm">Môi trường: {displayed.environments.join(", ")}</p>
                )}
                {displayed.builds?.length > 0 && (
                  <p className="text-sm">Bản dựng: {displayed.builds.join(", ")}</p>
                )}
                <div className="grid gap-3 sm:grid-cols-2 lg:grid-cols-4">
                  <Metric label="Tổng số ca" value={displayed.total} />
                  <Metric label="Đạt" value={displayed.counts?.PASS || 0} />
                  <Metric label="Thất bại" value={displayed.counts?.FAIL || 0} />
                  <Metric
                    label="Tỷ lệ đạt trong ca Pass/Fail"
                    value={
                      displayed.pass_rate == null ? "Chưa có dữ liệu" : `${displayed.pass_rate}%`
                    }
                  />
                </div>
                <p className="text-xs text-ink-muted">
                  Tính trên {displayed.pass_rate_denominator ?? 0} ca có kết luận Pass hoặc Fail.
                </p>
                <div className="flex flex-wrap gap-2 text-sm">
                  {Object.entries(labels).map(([status, label]) => (
                    <span className="rounded-full border border-border px-3 py-1" key={status}>
                      {label}: {displayed.counts?.[status] || 0}
                    </span>
                  ))}
                </div>
                <p className="text-sm text-ink-muted">
                  Mỗi ca tính theo kết quả mới nhất kể từ khi kế hoạch được duyệt; các lần chạy cũ
                  vẫn được giữ trong lịch sử.
                </p>
                {displayed.defects && (
                  <p className="text-sm">
                    Lỗi liên kết: {displayed.defects.total} · Đang mở: {displayed.defects.open}
                  </p>
                )}
                <div className="overflow-x-auto rounded-control border border-border">
                  <table className="w-full text-left text-sm">
                    <thead>
                      <tr className="border-b border-border">
                        <th className="p-3">Mã ca</th>
                        <th className="p-3">Ca kiểm thử</th>
                        <th className="p-3">Kết quả mới nhất</th>
                        <th className="p-3">Lần chạy</th>
                      </tr>
                    </thead>
                    <tbody>
                      {(displayed.case_results || []).map((item) => (
                        <tr
                          className="border-b border-border last:border-0"
                          key={item.test_case_version_id}
                        >
                          <td className="p-3">{item.test_case_key}</td>
                          <td className="p-3">
                            {item.title} · v{item.version || "—"}
                          </td>
                          <td className="p-3">{labels[item.status] || item.status}</td>
                          <td className="p-3">
                            {item.test_run_id ? (
                              <Link
                                className="text-brand hover:underline"
                                href={projectRoute(
                                  project._id,
                                  PROJECT_SECTION_SLUGS.testRuns,
                                  item.test_run_id,
                                )}
                              >
                                {item.test_run_name || item.test_run_id}
                              </Link>
                            ) : (
                              "—"
                            )}
                          </td>
                        </tr>
                      ))}
                    </tbody>
                  </table>
                </div>
                {displayed.type === "COMPLETION" && (
                  <div className="space-y-1 text-sm">
                    <p>
                      Tiêu chí kết thúc:{" "}
                      {displayed.exit_criteria?.join("; ") || "Chưa cấu hình trong kế hoạch"}
                    </p>
                    <p className="text-ink-muted">
                      Báo cáo tổng hợp dữ liệu hiện có; người phụ trách quyết định việc chấp nhận
                      kết quả hoặc phát hành.
                    </p>
                  </div>
                )}
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
              </div>
            ) : (
              <p className="text-sm text-ink-muted">Đang tổng hợp báo cáo…</p>
            )}
          </div>
        </Panel>
      )}
      {canReadReports && (
        <Panel title="Các bản báo cáo đã lưu">
          <div className="divide-y divide-border">
            {reports.length ? (
              reports.map((report) => (
                <button
                  className="block w-full p-4 text-left hover:bg-surface-raised"
                  type="button"
                  key={report._id}
                  onClick={() => openSavedReport(report._id)}
                >
                  {report.title} · {report.type === "PROGRESS" ? "Tiến độ" : "Hoàn tất"} ·{" "}
                  {report.plan_name}
                </button>
              ))
            ) : (
              <p className="p-4 text-sm text-ink-muted">
                Chưa lưu bản báo cáo nào. Báo cáo hiện tại vẫn được tổng hợp tự động ở phía trên.
              </p>
            )}
          </div>
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
