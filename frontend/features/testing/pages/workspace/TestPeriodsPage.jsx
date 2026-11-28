"use client";

import { useCallback, useEffect, useState } from "react";
import Link from "next/link";
import { useRouter } from "next/navigation";
import { Grid2X2, List } from "lucide-react";
import { useDateTimeOptions } from "../../hooks/useDateTimeOptions";
import { testingApi } from "../../services/testing.service";
import {
  ErrorState,
  Panel,
  ProjectCrumb,
  useActionDialog,
  WorkspacePage,
} from "../../components/WorkspacePrimitives";
import { formatCalendarDate as formatCalendarDateValue, valueLabel } from "../../lib/testing";
import { PROJECT_SECTION_SLUGS, projectRoute } from "../../routes";
import SearchField from "@/shared/components/ui/SearchField";

export default function TestPeriodsPage({ project, section = [] }) {
  const { ask, dialog } = useActionDialog();
  const dateTimeOptions = useDateTimeOptions(project);
  const formatCalendarDate = (value) => formatCalendarDateValue(value, dateTimeOptions);
  const router = useRouter();
  const periodId = section[0] || "";
  const [periods, setPeriods] = useState([]);
  const [periodsLoading, setPeriodsLoading] = useState(true);
  const [newPeriodName, setNewPeriodName] = useState("");
  const [periodQuery, setPeriodQuery] = useState("");
  const [periodStatusFilter, setPeriodStatusFilter] = useState("ALL");
  const [periodView, setPeriodView] = useState("cards");
  const [creatingPeriod, setCreatingPeriod] = useState(false);
  const [listError, setListError] = useState("");
  const [summary, setSummary] = useState(null);
  const [plans, setPlans] = useState([]);
  const [selectedCases, setSelectedCases] = useState({});
  const [reasons, setReasons] = useState({});
  const [closeNote, setCloseNote] = useState("");
  const [error, setError] = useState("");
  const [loading, setLoading] = useState(true);
  const [saving, setSaving] = useState(false);
  const canClose = project.current_permissions?.includes("testplan.update");
  const canCreate = project.current_permissions?.includes("testplan.create");
  const periodStatusCounts = periods.reduce(
    (counts, period) => {
      counts.total += 1;
      if (period.status === "ACTIVE") counts.active += 1;
      else if (period.status === "CLOSED") counts.closed += 1;
      else counts.upcoming += 1;
      return counts;
    },
    { total: 0, active: 0, closed: 0, upcoming: 0 },
  );
  const visiblePeriods = periods.filter((period) => {
    const query = periodQuery.trim().toLocaleLowerCase("vi");
    const matchesQuery =
      !query ||
      [period.name, period.sequence, period.status]
        .filter(Boolean)
        .some((value) => String(value).toLocaleLowerCase("vi").includes(query));
    const status =
      period.status === "ACTIVE" ? "ACTIVE" : period.status === "CLOSED" ? "CLOSED" : "UPCOMING";
    return matchesQuery && (periodStatusFilter === "ALL" || status === periodStatusFilter);
  });
  const caseStatusCounts = Object.entries(summary?.latest_case_statuses || {}).map(
    ([status, value]) => [status, Number(value) || 0],
  );
  const caseStatusTotal = caseStatusCounts.reduce((total, [, count]) => total + count, 0);
  const caseStatusColors = {
    PASS: "bg-brand",
    FAIL: "bg-danger",
    BLOCKED: "bg-warning",
    IN_PROGRESS: "bg-brand-soft",
    NOT_RUN: "bg-border-strong",
    SKIPPED: "bg-ink-faint",
  };

  const loadPeriods = useCallback(async () => {
    setPeriodsLoading(true);
    setListError("");
    try {
      const items = await testingApi.listTestPeriods(project._id);
      setPeriods(Array.isArray(items) ? items : []);
    } catch (reason) {
      setListError(reason.message || "Không tải được chu kỳ");
    } finally {
      setPeriodsLoading(false);
    }
  }, [project._id]);

  useEffect(() => {
    if (!periodId) void loadPeriods();
  }, [loadPeriods, periodId]);

  const load = useCallback(async () => {
    if (!periodId) return;
    setLoading(true);
    setError("");
    try {
      const [periodSummary, periodPlans] = await Promise.all([
        testingApi.getTestPeriodSummary(periodId),
        testingApi.listPlans(project._id, { test_period_id: periodId }),
      ]);
      setSummary(periodSummary);
      setPlans(Array.isArray(periodPlans) ? periodPlans : []);
    } catch (reason) {
      setError(reason.message || "Không tải được chu kỳ");
    } finally {
      setLoading(false);
    }
  }, [periodId, project._id]);

  useEffect(() => {
    if (!periodId) return;
    void load();
  }, [load, periodId]);

  useEffect(() => {
    setSummary(null);
    setPlans([]);
    setSelectedCases({});
    setReasons({});
    setCloseNote("");
  }, [periodId]);

  const closePeriod = async () => {
    const period = summary?.period;
    if (!period || saving) return;
    const carryOverItems = summary.cases
      .filter((item) => selectedCases[item.test_case_version_id])
      .map((item) => ({
        source_test_run_id: item.source_test_run_id || null,
        source_test_plan_id: item.source_test_run_id ? null : item.source_test_plan_id,
        test_case_version_id: item.test_case_version_id,
        reason: String(reasons[item.test_case_version_id] || "").trim(),
      }));
    if (carryOverItems.some((item) => !item.reason)) {
      setError("Nhập lý do cho từng ca được chọn chuyển tiếp");
      return;
    }
    const confirmed = await ask({
      title: "Xác nhận đóng chu kỳ",
      description: carryOverItems.length
        ? `Đóng chu kỳ “${period.name}” và chuyển tiếp ${carryOverItems.length} ca đã chọn. Lịch sử thực thi sẽ được giữ lại`
        : `Đóng chu kỳ “${period.name}”. Lịch sử kế hoạch và thực thi sẽ được giữ lại`,
      confirmLabel: "Đóng chu kỳ",
      danger: true,
    });
    if (!confirmed) return;
    setSaving(true);
    setError("");
    try {
      await testingApi.closeTestPeriod(period._id, {
        expected_revision: period.revision,
        note: closeNote.trim(),
        carry_over_items: carryOverItems,
      });
      await load();
    } catch (reason) {
      setError(reason.message || "Không đóng được chu kỳ");
    } finally {
      setSaving(false);
    }
  };

  if (!periodId) {
    return (
      <WorkspacePage
        title="Chu kỳ kiểm thử"
        description="Gom các kế hoạch thuộc cùng một giai đoạn làm việc. Kế hoạch không cần chu kỳ vẫn dùng được"
        actions={
          <Link
            className="secondary-button"
            href={projectRoute(project._id, PROJECT_SECTION_SLUGS.testPlans)}
          >
            Danh sách kế hoạch
          </Link>
        }
      >
        {listError && <ErrorState message={listError} />}
        <section aria-label="Tóm tắt chu kỳ" className="grid gap-3 sm:grid-cols-2 xl:grid-cols-4">
          {[
            { label: "Tổng chu kỳ", value: periodStatusCounts.total },
            { label: "Đang thực hiện", value: periodStatusCounts.active },
            { label: "Sắp diễn ra", value: periodStatusCounts.upcoming },
            { label: "Đã đóng", value: periodStatusCounts.closed },
          ].map((metric) => (
            <div className="rounded-panel border border-border bg-surface p-4" key={metric.label}>
              <p className="text-xs font-medium text-ink-muted">{metric.label}</p>
              <p className="mt-2 text-2xl font-semibold tabular-nums">{metric.value}</p>
            </div>
          ))}
        </section>
        <div
          className={`grid items-start gap-5 ${canCreate ? "xl:grid-cols-[minmax(18rem,0.8fr)_minmax(0,2fr)]" : "grid-cols-1"}`}
        >
          {canCreate && (
            <Panel title="Tạo chu kỳ">
              <form
                className="grid gap-3 p-4 sm:grid-cols-[minmax(0,1fr)_auto] sm:items-end sm:p-5"
                onSubmit={async (event) => {
                  event.preventDefault();
                  if (creatingPeriod || newPeriodName.trim().length < 2) return;
                  setCreatingPeriod(true);
                  setListError("");
                  try {
                    const created = await testingApi.createTestPeriod({
                      project_id: project._id,
                      name: newPeriodName.trim(),
                    });
                    setNewPeriodName("");
                    await loadPeriods();
                    router.push(
                      projectRoute(project._id, PROJECT_SECTION_SLUGS.testPeriods, created._id),
                    );
                  } catch (reason) {
                    setListError(reason.message || "Không tạo được chu kỳ");
                  } finally {
                    setCreatingPeriod(false);
                  }
                }}
              >
                <label className="field-label">
                  Tên chu kỳ <span className="text-danger">*</span>
                  <input
                    className="apple-input mt-2"
                    maxLength={200}
                    minLength={2}
                    required
                    value={newPeriodName}
                    onChange={(event) => setNewPeriodName(event.target.value)}
                  />
                </label>
                <button className="primary-button" type="submit" disabled={creatingPeriod}>
                  {creatingPeriod ? "Đang tạo…" : "Tạo chu kỳ"}
                </button>
              </form>
            </Panel>
          )}
          <Panel title="Các chu kỳ">
            {periodsLoading ? (
              <p className="p-5 text-sm text-ink-muted">Đang tải chu kỳ…</p>
            ) : periods.length ? (
              <div className="space-y-4 p-4 sm:p-5">
                <details className="border-b border-border pb-3">
                  <summary className="cursor-pointer text-sm font-medium">Bộ lọc</summary>
                  <div className="mt-3 grid min-w-0 gap-3">
                    <div className="w-full min-w-0">
                      <SearchField
                        ariaLabel="Tìm chu kỳ"
                        value={periodQuery}
                        onChange={setPeriodQuery}
                        placeholder="Tìm theo tên hoặc số chu kỳ"
                      />
                    </div>
                    <div className="flex min-w-0 flex-col gap-3 lg:flex-row lg:items-start lg:justify-between">
                      <div
                        aria-label="Lọc trạng thái chu kỳ"
                        className="flex flex-wrap gap-1"
                        role="group"
                      >
                        {[
                          ["ALL", "Tất cả", periodStatusCounts.total],
                          ["ACTIVE", "Đang thực hiện", periodStatusCounts.active],
                          ["UPCOMING", "Sắp diễn ra", periodStatusCounts.upcoming],
                          ["CLOSED", "Đã đóng", periodStatusCounts.closed],
                        ].map(([status, label, count]) => (
                          <button
                            aria-pressed={periodStatusFilter === status}
                            className={`rounded-control px-3 py-2 text-xs font-medium transition-colors ${periodStatusFilter === status ? "bg-brand text-white" : "border border-border text-ink-muted hover:bg-surface-quiet hover:text-ink"}`}
                            key={status}
                            onClick={() => setPeriodStatusFilter(status)}
                            type="button"
                          >
                            {label} <span className="ml-1 tabular-nums">{count}</span>
                          </button>
                        ))}
                      </div>
                      <div
                        aria-label="Cách hiển thị chu kỳ"
                        className="flex shrink-0 gap-1 lg:justify-end"
                        role="group"
                      >
                        {[
                          ["cards", "Thẻ", Grid2X2],
                          ["list", "Danh sách", List],
                        ].map(([view, label, Icon]) => (
                          <button
                            aria-label={label}
                            aria-pressed={periodView === view}
                            className={`icon-button h-9 w-9 ${periodView === view ? "bg-brand/10 text-brand" : ""}`}
                            key={view}
                            onClick={() => setPeriodView(view)}
                            title={label}
                            type="button"
                          >
                            <Icon aria-hidden="true" size={16} />
                          </button>
                        ))}
                      </div>
                    </div>
                  </div>
                </details>
                <p aria-live="polite" className="text-xs text-ink-muted">
                  Hiển thị {visiblePeriods.length} / {periods.length} chu kỳ
                </p>
                {visiblePeriods.length ? (
                  periodView === "cards" ? (
                    <ul className="grid gap-3 sm:grid-cols-2 2xl:grid-cols-3">
                      {visiblePeriods.map((item) => (
                        <li
                          className="flex min-w-0 flex-col rounded-panel border border-border bg-surface p-4 transition-colors hover:border-border-strong"
                          key={item._id}
                        >
                          <div className="flex items-start justify-between gap-3">
                            <div className="min-w-0">
                              <p className="text-xs font-semibold uppercase tracking-wide text-brand">
                                Chu kỳ {item.sequence}
                              </p>
                              <p className="mt-1 break-words font-semibold [overflow-wrap:anywhere]">
                                {item.name}
                              </p>
                            </div>
                            <span className="shrink-0 rounded-full bg-surface-quiet px-2.5 py-1 text-xs font-medium text-ink-muted">
                              {valueLabel(item.status)}
                            </span>
                          </div>
                          <p className="mt-4 border-t border-border pt-3 text-xs text-ink-muted">
                            <span className="font-medium text-ink">Thời gian</span>
                            <span className="ml-2">
                              {[item.planned_start_date, item.planned_end_date]
                                .filter(Boolean)
                                .map(formatCalendarDate)
                                .join(" – ") || "Chưa thiết lập"}
                            </span>
                          </p>
                          <Link
                            className="secondary-button mt-4 self-start"
                            href={projectRoute(
                              project._id,
                              PROJECT_SECTION_SLUGS.testPeriods,
                              item._id,
                            )}
                          >
                            Mở chu kỳ
                          </Link>
                        </li>
                      ))}
                    </ul>
                  ) : (
                    <ul className="divide-y divide-border rounded-panel border border-border">
                      {visiblePeriods.map((item) => (
                        <li
                          className="grid min-w-0 gap-3 p-4 sm:grid-cols-[minmax(0,1fr)_minmax(10rem,0.8fr)_auto] sm:items-center"
                          key={item._id}
                        >
                          <div className="min-w-0">
                            <p className="text-xs text-ink-muted">Chu kỳ {item.sequence}</p>
                            <p className="break-words font-medium [overflow-wrap:anywhere]">
                              {item.name}
                            </p>
                          </div>
                          <div>
                            <span className="text-xs text-ink-muted">
                              {valueLabel(item.status)}
                            </span>
                            <p className="mt-1 text-xs text-ink-muted">
                              {[item.planned_start_date, item.planned_end_date]
                                .filter(Boolean)
                                .map(formatCalendarDate)
                                .join(" – ") || "Chưa thiết lập thời gian"}
                            </p>
                          </div>
                          <Link
                            className="secondary-button justify-self-start sm:justify-self-end"
                            href={projectRoute(
                              project._id,
                              PROJECT_SECTION_SLUGS.testPeriods,
                              item._id,
                            )}
                          >
                            Mở chu kỳ
                          </Link>
                        </li>
                      ))}
                    </ul>
                  )
                ) : (
                  <div className="rounded-panel border border-dashed border-border p-6 text-center">
                    <p className="text-sm font-medium text-ink">Không tìm thấy chu kỳ phù hợp</p>
                    <p className="mt-1 text-sm text-ink-muted">
                      Thử từ khóa khác hoặc xóa bộ lọc trạng thái
                    </p>
                    <button
                      className="secondary-button mt-3"
                      onClick={() => {
                        setPeriodQuery("");
                        setPeriodStatusFilter("ALL");
                      }}
                      type="button"
                    >
                      Xóa bộ lọc
                    </button>
                  </div>
                )}
              </div>
            ) : (
              <p className="p-5 text-sm text-ink-muted">
                Chưa có chu kỳ. Bạn cũng có thể tạo chu kỳ ngay trong form kế hoạch
              </p>
            )}
          </Panel>
        </div>
      </WorkspacePage>
    );
  }

  const period = summary?.period;
  const closed = period?.status === "CLOSED";
  return (
    <WorkspacePage
      title={period?.name || "Chu kỳ kiểm thử"}
      description={
        period
          ? `Chu kỳ ${period.sequence} · ${period.status === "ACTIVE" ? "Đang thực hiện" : closed ? "Đã đóng" : "Sắp diễn ra"}`
          : "Tổng hợp kế hoạch và kết quả trong chu kỳ"
      }
      actions={
        <div className="flex flex-wrap items-center gap-3">
          <ProjectCrumb projectId={project._id} projectName={project.name} />
          {closed && (
            <Link
              className="primary-button"
              href={`${projectRoute(project._id, PROJECT_SECTION_SLUGS.testPlans, "tao-moi")}?source_period_id=${encodeURIComponent(period._id)}`}
            >
              Tạo kế hoạch tiếp theo
            </Link>
          )}
          <Link
            className="secondary-button"
            href={projectRoute(project._id, PROJECT_SECTION_SLUGS.testPlans)}
          >
            Danh sách kế hoạch
          </Link>
        </div>
      }
    >
      {error && <ErrorState message={error} />}
      {loading && <p className="text-sm text-ink-muted">Đang tải chu kỳ…</p>}
      {summary && (
        <div className="space-y-5">
          <section aria-label="Chỉ số chu kỳ" className="grid gap-3 sm:grid-cols-3">
            {[
              {
                label: "Lần chạy",
                value: summary.run_count,
                detail: "Đã tạo trong chu kỳ",
              },
              {
                label: "Ca trong phạm vi",
                value: summary.case_count,
                detail: `${caseStatusTotal} ca đã có trạng thái gần nhất`,
              },
              {
                label: "Lỗi còn mở",
                value: summary.open_defect_count,
                detail: "Cần theo dõi trước khi đóng chu kỳ",
              },
            ].map((metric) => (
              <article
                className="min-w-0 rounded-panel border border-border bg-surface p-4"
                key={metric.label}
              >
                <p className="text-xs font-medium text-ink-muted">{metric.label}</p>
                <p className="mt-2 text-2xl font-semibold tabular-nums text-ink">{metric.value}</p>
                <p className="mt-1 text-xs leading-5 text-ink-faint">{metric.detail}</p>
              </article>
            ))}
          </section>

          <div className="grid min-w-0 items-start gap-5 xl:grid-cols-[minmax(0,1.4fr)_minmax(18rem,0.8fr)]">
            <Panel title="Kế hoạch trong chu kỳ">
              {plans.length ? (
                <ul className="grid gap-3 p-4 sm:grid-cols-2 sm:p-5">
                  {plans.map((item) => (
                    <li
                      className="flex min-w-0 flex-col rounded-panel border border-border bg-surface p-4"
                      key={item._id}
                    >
                      <div className="flex items-start justify-between gap-3">
                        <div className="min-w-0">
                          <p className="break-words font-semibold text-ink">{item.name}</p>
                          <p className="mt-1 break-words font-mono text-[11px] text-ink-muted">
                            {item.plan_key || item._id}
                          </p>
                        </div>
                        <span className="shrink-0 rounded-full bg-surface-quiet px-2.5 py-1 text-xs font-medium text-ink-muted">
                          {valueLabel(item.status)}
                        </span>
                      </div>
                      <Link
                        className="secondary-button mt-4 self-start"
                        href={projectRoute(project._id, PROJECT_SECTION_SLUGS.testPlans, item._id)}
                      >
                        Mở kế hoạch
                      </Link>
                    </li>
                  ))}
                </ul>
              ) : (
                <p className="p-5 text-sm text-ink-muted">Chu kỳ này chưa có kế hoạch kiểm thử</p>
              )}
            </Panel>

            <Panel title="Tổng kết thực thi" className="h-full">
              <section aria-labelledby="period-case-status-heading" className="p-4">
                <div className="mb-3 flex flex-wrap items-baseline justify-between gap-2">
                  <h3 id="period-case-status-heading" className="text-sm font-semibold">
                    Trạng thái ca gần nhất
                  </h3>
                  <span className="text-xs text-ink-muted">{caseStatusTotal} ca có trạng thái</span>
                </div>
                {caseStatusTotal === 0 ? (
                  <p className="text-xs leading-5 text-ink-muted">
                    Chu kỳ chưa có kết quả thực thi để phân bố
                  </p>
                ) : (
                  <div className="space-y-2.5">
                    {caseStatusCounts
                      .filter(([, count]) => count > 0)
                      .map(([status, count]) => {
                        const percent = Math.round((count / caseStatusTotal) * 100);
                        return (
                          <div
                            aria-label={`${valueLabel(status)}: ${count} trên ${caseStatusTotal} ca`}
                            className="grid grid-cols-[minmax(4.5rem,auto)_minmax(0,1fr)_2rem] items-center gap-2 text-xs"
                            key={status}
                          >
                            <span className="truncate text-ink-muted">{valueLabel(status)}</span>
                            <div
                              aria-valuemax={100}
                              aria-valuemin={0}
                              aria-valuenow={percent}
                              className="h-2 overflow-hidden rounded-full bg-surface-quiet"
                              role="progressbar"
                            >
                              <span
                                className={`block h-full rounded-full ${caseStatusColors[status] || "bg-brand"}`}
                                style={{ width: `${percent}%` }}
                              />
                            </div>
                            <span className="text-right font-semibold tabular-nums">{count}</span>
                          </div>
                        );
                      })}
                  </div>
                )}
              </section>
            </Panel>
            <div className="space-y-5 xl:col-span-2">
              <Panel title={closed ? "Ca được chuyển tiếp" : "Rà soát trước khi đóng chu kỳ"}>
                {summary.cases.length === 0 ? (
                  <p className="p-5 text-sm text-ink-muted">
                    {closed
                      ? "Không có ca được chọn chuyển tiếp"
                      : "Chu kỳ chưa có ca trong phạm vi kế hoạch"}
                  </p>
                ) : (
                  <div className="divide-y divide-border">
                    {summary.cases.map((item) => {
                      const checked = closed
                        ? (period.carry_over_items || []).some(
                            (carry) => carry.test_case_version_id === item.test_case_version_id,
                          )
                        : Boolean(selectedCases[item.test_case_version_id]);
                      return (
                        <div
                          className="grid gap-3 p-4 md:grid-cols-[auto_minmax(0,1fr)_auto] md:items-start"
                          key={`${item.source_test_run_id || item.source_test_plan_id}:${item.test_case_version_id}`}
                        >
                          {!closed && (
                            <input
                              aria-label={`Chuyển tiếp ${item.title}`}
                              type="checkbox"
                              disabled={!item.carry_over_eligible}
                              checked={checked}
                              onChange={(event) =>
                                setSelectedCases((current) => ({
                                  ...current,
                                  [item.test_case_version_id]: event.target.checked,
                                }))
                              }
                            />
                          )}
                          {closed && <span className="text-sm">{checked ? "✓" : "—"}</span>}
                          <div className="min-w-0">
                            <p className="font-medium">
                              {item.title}{" "}
                              <span className="text-xs text-ink-muted">v{item.version || "-"}</span>
                            </p>
                            <p className="mt-1 text-xs text-ink-muted">
                              {item.source_test_run_name ||
                                item.source_test_plan_name ||
                                "Kế hoạch"}{" "}
                              · {valueLabel(item.status)}
                            </p>
                            {checked && !closed && (
                              <input
                                className="apple-input mt-2 w-full"
                                required
                                maxLength={2000}
                                placeholder="Lý do chuyển ca này sang chu kỳ sau"
                                value={reasons[item.test_case_version_id] || ""}
                                onChange={(event) =>
                                  setReasons((current) => ({
                                    ...current,
                                    [item.test_case_version_id]: event.target.value,
                                  }))
                                }
                              />
                            )}
                          </div>
                          <span className="rounded-full bg-surface-muted px-3 py-1 text-xs">
                            {valueLabel(item.status)}
                          </span>
                        </div>
                      );
                    })}
                  </div>
                )}
                {!closed && period && canClose && (
                  <div className="space-y-3 border-t border-border p-4">
                    <label className="field-label block">
                      Ghi chú khi đóng (nếu có)
                      <textarea
                        className="apple-input mt-2 min-h-20 w-full"
                        value={closeNote}
                        onChange={(event) => setCloseNote(event.target.value)}
                      />
                    </label>
                    {summary.open_run_count > 0 && (
                      <p className="text-sm text-ink-muted">
                        Cần hoàn tất hoặc hủy {summary.open_run_count} lần chạy trước khi đóng chu
                        kỳ
                      </p>
                    )}
                    <button
                      className="primary-button"
                      type="button"
                      disabled={saving || summary.open_run_count > 0}
                      onClick={closePeriod}
                    >
                      {saving ? "Đang đóng…" : "Đóng chu kỳ"}
                    </button>
                  </div>
                )}
              </Panel>
            </div>
          </div>
        </div>
      )}
      {dialog}
    </WorkspacePage>
  );
}
