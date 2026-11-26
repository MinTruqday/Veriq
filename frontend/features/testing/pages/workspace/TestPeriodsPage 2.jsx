"use client";

import { useCallback, useEffect, useState } from "react";
import Link from "next/link";
import { useRouter } from "next/navigation";
import { testingApi } from "../../services/testing.service";
import {
  ErrorState,
  Panel,
  ProjectCrumb,
  WorkspacePage,
} from "../../components/WorkspacePrimitives";
import { PROJECT_SECTION_SLUGS, projectRoute } from "../../routes";

export default function TestPeriodsPage({ project, section = [] }) {
  const router = useRouter();
  const periodId = section[0] || "";
  const [periods, setPeriods] = useState([]);
  const [periodsLoading, setPeriodsLoading] = useState(true);
  const [newPeriodName, setNewPeriodName] = useState("");
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

  const loadPeriods = useCallback(async () => {
    setPeriodsLoading(true);
    setListError("");
    try {
      const items = await testingApi.listTestPeriods(project._id);
      setPeriods(Array.isArray(items) ? items : []);
    } catch (reason) {
      setListError(reason.message || "Không tải được chu kỳ.");
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
      setError(reason.message || "Không tải được chu kỳ.");
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
      setError("Nhập lý do cho từng ca được chọn chuyển tiếp.");
      return;
    }
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
      setError(reason.message || "Không đóng được chu kỳ.");
    } finally {
      setSaving(false);
    }
  };

  if (!periodId) {
    return (
      <WorkspacePage
        title="Chu kỳ kiểm thử"
        description="Gom các kế hoạch thuộc cùng một giai đoạn làm việc. Kế hoạch không cần chu kỳ vẫn dùng được."
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
                  setListError(reason.message || "Không tạo được chu kỳ.");
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
            <ul className="divide-y divide-border">
              {periods.map((item) => (
                <li
                  className="flex min-w-0 flex-wrap items-center justify-between gap-3 px-4 py-4 sm:px-5"
                  key={item._id}
                >
                  <div className="min-w-0">
                    <p className="font-semibold">
                      Chu kỳ {item.sequence}: {item.name}
                    </p>
                    <p className="mt-1 text-sm text-ink-muted">
                      {item.status === "CLOSED"
                        ? "Đã đóng"
                        : item.status === "ACTIVE"
                          ? "Đang thực hiện"
                          : "Chưa bắt đầu"}
                      {item.planned_start_date || item.planned_end_date
                        ? ` · ${[item.planned_start_date, item.planned_end_date].filter(Boolean).join(" – ")}`
                        : ""}
                    </p>
                  </div>
                  <Link
                    className="secondary-button"
                    href={projectRoute(project._id, PROJECT_SECTION_SLUGS.testPeriods, item._id)}
                  >
                    Mở chu kỳ
                  </Link>
                </li>
              ))}
            </ul>
          ) : (
            <p className="p-5 text-sm text-ink-muted">
              Chưa có chu kỳ. Bạn cũng có thể tạo chu kỳ ngay trong form kế hoạch.
            </p>
          )}
        </Panel>
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
          : "Tổng hợp kế hoạch và kết quả trong chu kỳ."
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
          <Panel title="Kế hoạch trong chu kỳ">
            {plans.length ? (
              <div className="divide-y divide-border">
                {plans.map((item) => (
                  <div
                    className="flex flex-wrap items-center justify-between gap-3 px-5 py-3"
                    key={item._id}
                  >
                    <div className="min-w-0">
                      <p className="font-medium">{item.name}</p>
                      <p className="mt-1 text-xs text-ink-muted">
                        {item.plan_key || item._id} ·{" "}
                        {item.status === "APPROVED" ? "Đã duyệt" : item.status}
                      </p>
                    </div>
                    <Link
                      className="text-sm font-medium text-brand hover:underline"
                      href={projectRoute(project._id, PROJECT_SECTION_SLUGS.testPlans, item._id)}
                    >
                      Mở kế hoạch
                    </Link>
                  </div>
                ))}
              </div>
            ) : (
              <p className="p-5 text-sm text-ink-muted">Chu kỳ này chưa có kế hoạch kiểm thử.</p>
            )}
          </Panel>

          <Panel title="Tổng kết thực thi">
            <div className="grid gap-4 p-5 sm:grid-cols-2 lg:grid-cols-4">
              <div>
                <p className="field-label">Lần chạy</p>
                <p className="mt-1">{summary.run_count}</p>
              </div>
              <div>
                <p className="field-label">Ca trong phạm vi</p>
                <p className="mt-1">{summary.case_count}</p>
              </div>
              <div>
                <p className="field-label">Đạt / Thất bại</p>
                <p className="mt-1">
                  {summary.latest_case_statuses.PASS || 0} /{" "}
                  {summary.latest_case_statuses.FAIL || 0}
                </p>
              </div>
              <div>
                <p className="field-label">Lỗi còn mở</p>
                <p className="mt-1">{summary.open_defect_count}</p>
              </div>
            </div>
          </Panel>

          <Panel title={closed ? "Ca được chuyển tiếp" : "Rà soát trước khi đóng chu kỳ"}>
            {summary.cases.length === 0 ? (
              <p className="p-5 text-sm text-ink-muted">
                {closed
                  ? "Không có ca được chọn chuyển tiếp."
                  : "Chu kỳ chưa có ca trong phạm vi kế hoạch."}
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
                          {item.source_test_run_name || item.source_test_plan_name || "Kế hoạch"} ·{" "}
                          {item.status}
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
                        {item.status}
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
                    Cần hoàn tất hoặc hủy {summary.open_run_count} lần chạy trước khi đóng chu kỳ.
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
      )}
    </WorkspacePage>
  );
}
