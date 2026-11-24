"use client";

import { useRef, useState } from "react";
import { uploadAssetAPI } from "@/features/cloud/services/upload.service";
import FilePicker from "../../../components/FilePicker";
import {
  ErrorState,
  Panel,
  ProjectCrumb,
  StatusPill,
  WorkspacePage,
} from "../../../components/WorkspacePrimitives";
import { docText, messageOf, valueLabel } from "../../../lib/testing";
import { testingApi } from "../../../services/testing.service";

export default function RunExecutionWorkspace({
  run,
  projectId,
  members,
  error,
  can,
  resumeContext,
  onResumeChange,
  ask,
  onRunChange,
  onError,
  onTransition,
  onCreateDefect,
  onCreateInlineDefect,
  creatingDefectResultIds = new Set(),
  stepResults,
  onStepResultsChange,
  terminalResultStatuses,
  actuals,
  onActualsChange,
  attachments,
  onAttachmentsChange,
  dialog,
  savingExecution = false,
}) {
  const eligibleExecutors = (members || []).filter(
    (member) => member.status === "ACTIVE" && member.permissions?.includes("testrun.execute"),
  );
  const [assignmentEditing, setAssignmentEditing] = useState(false);
  const [assignmentDraft, setAssignmentDraft] = useState({});
  const [runAssigneeDraft, setRunAssigneeDraft] = useState("");
  const [savingAssignment, setSavingAssignment] = useState(false);
  const [creatingRerun, setCreatingRerun] = useState(false);
  const [selectedFailedCases, setSelectedFailedCases] = useState([]);
  const [pendingFail, setPendingFail] = useState({});
  const [resumingRun, setResumingRun] = useState(false);
  const [focusedCaseIndex, setFocusedCaseIndex] = useState(0);
  const rerunKey = useRef(null);
  const resumeOperation = useRef(null);
  const testCaseVersions = run.test_case_versions || [];
  const totalCases = (run.test_case_version_ids || []).length;
  const recordedCases = (run.results || []).filter((result) =>
    ["PASS", "FAIL", "BLOCKED", "SKIPPED", "NOT_APPLICABLE"].includes(result.status),
  ).length;
  const navigateCase = (index) => {
    const nextIndex = Math.max(0, Math.min(index, testCaseVersions.length - 1));
    setFocusedCaseIndex(nextIndex);
    document.getElementById(`execution-case-${nextIndex}`)?.scrollIntoView({
      behavior: "smooth",
      block: "start",
    });
  };
  const beginAssignmentEdit = () => {
    const assignments = { ...(run.test_case_assignments || {}) };
    setAssignmentDraft(assignments);
    setRunAssigneeDraft(run.assignee_id || "");
    setAssignmentEditing(true);
  };
  const saveAssignments = async () => {
    const testCaseAssignments = Object.fromEntries(
      Object.entries(assignmentDraft).filter(
        ([versionId, assigneeId]) =>
          run.test_case_version_ids?.includes(versionId) && Boolean(assigneeId),
      ),
    );
    if (!runAssigneeDraft) {
      onError("Chọn người phụ trách lần chạy trước khi lưu phân công");
      return;
    }
    setSavingAssignment(true);
    try {
      const updatedRun = await testingApi.assignRun(projectId, run._id, {
        expected_revision: run.revision,
        assignee_id: runAssigneeDraft,
        test_case_assignments: testCaseAssignments,
      });
      onRunChange(updatedRun);
      setAssignmentEditing(false);
    } catch (reason) {
      onError(messageOf(reason));
    } finally {
      setSavingAssignment(false);
    }
  };
  return (
    <WorkspacePage title={run.name} actions={<ProjectCrumb projectId={projectId} />}>
      {error && <ErrorState message={error} />}
      <Panel
        title="Trạng thái"
        actions={
          <div className="flex flex-wrap gap-2">
            {can("testrun.assign") && can("project.members.read") && (
              <>
                <button
                  className="secondary-button"
                  type="button"
                  disabled={!eligibleExecutors.length}
                  onClick={beginAssignmentEdit}
                >
                  Chọn thủ công
                </button>
              </>
            )}
            {can("report.export") && (
              <button
                className="secondary-button"
                type="button"
                onClick={() =>
                  testingApi.exportRunReport(run._id).catch((reason) => onError(messageOf(reason)))
                }
              >
                Xuất báo cáo
              </button>
            )}
            {["COMPLETED", "ABORTED"].includes(run.status) &&
              can("testrun.create") &&
              run.results?.some((result) => result.status === "FAIL") && (
                <details className="rounded-control border border-border p-3">
                  <summary className="cursor-pointer">Chạy lại ca thất bại</summary>
                  <div className="mt-3 space-y-2">
                    {(run.results || [])
                      .filter((result) => result.status === "FAIL")
                      .map((result) => {
                        const version = testCaseVersions.find(
                          (item) => item._id === result.test_case_version_id,
                        );
                        return (
                          <label className="flex items-center gap-2" key={result._id}>
                            <input
                              type="checkbox"
                              checked={selectedFailedCases.includes(result.test_case_version_id)}
                              onChange={(event) => {
                                rerunKey.current = null;
                                setSelectedFailedCases((current) =>
                                  event.target.checked
                                    ? [...current, result.test_case_version_id]
                                    : current.filter((id) => id !== result.test_case_version_id),
                                );
                              }}
                            />
                            <span>
                              {version
                                ? `${version.test_case_key} · ${version.title}`
                                : result.test_case_version_id}
                            </span>
                          </label>
                        );
                      })}
                    <button
                      className="apple-button"
                      type="button"
                      disabled={creatingRerun || !selectedFailedCases.length}
                      onClick={async () => {
                        setCreatingRerun(true);
                        rerunKey.current ||= crypto.randomUUID();
                        try {
                          const created = await testingApi.rerunRun(projectId, run._id, {
                            idempotency_key: rerunKey.current,
                            failed_only: true,
                            test_case_version_ids: selectedFailedCases,
                          });
                          rerunKey.current = null;
                          window.location.assign(`/du-an/${projectId}/thuc-thi/${created._id}`);
                        } catch (reason) {
                          onError(messageOf(reason));
                        } finally {
                          setCreatingRerun(false);
                        }
                      }}
                    >
                      {creatingRerun ? "Đang tạo lần chạy mới…" : "Tạo lần chạy lại"}
                    </button>
                  </div>
                </details>
              )}
            {run.status === "DRAFT" && can("testrun.start") && (
              <button
                className="apple-button"
                type="button"
                onClick={async () => {
                  try {
                    await testingApi.startRun(run._id);
                    onRunChange(await testingApi.getRun(run._id));
                  } catch (reason) {
                    onError(messageOf(reason));
                  }
                }}
              >
                Bắt đầu
              </button>
            )}
            {run.status === "IN_PROGRESS" && (
              <>
                {can("testrun.execute") && (
                  <button
                    className="apple-button"
                    type="button"
                    disabled={savingExecution || resumingRun}
                    onClick={async () => {
                      if (resumingRun) return;
                      if (!resumeOperation.current || resumeOperation.current.runId !== run._id) {
                        resumeOperation.current = {
                          runId: run._id,
                          expectedRevision: run.revision,
                          idempotencyKey: crypto.randomUUID(),
                        };
                      }
                      const operation = resumeOperation.current;
                      setResumingRun(true);
                      try {
                        const value = await testingApi.resumeRun(projectId, run._id, {
                          expected_revision: operation.expectedRevision,
                          idempotency_key: operation.idempotencyKey,
                        });
                        resumeOperation.current = null;
                        onResumeChange(value);
                        onRunChange(value.run);
                      } catch (reason) {
                        if (reason?.status === 409) {
                          resumeOperation.current = null;
                          try {
                            onRunChange(await testingApi.getRun(run._id));
                          } catch (reloadError) {
                            onError(messageOf(reloadError));
                          }
                        }
                        onError(messageOf(reason));
                      } finally {
                        setResumingRun(false);
                      }
                    }}
                  >
                    {resumingRun ? "Đang tiếp tục…" : "Tiếp tục thực thi"}
                  </button>
                )}
                {can("testrun.abort") && (
                  <button
                    className="secondary-button"
                    type="button"
                    disabled={savingExecution}
                    onClick={async () => {
                      await ask({
                        title: "Hủy lần chạy kiểm thử",
                        description: `${run.name} sẽ dừng và giữ nguyên toàn bộ kết quả đã ghi nhận`,
                        confirmLabel: "Hủy lần chạy",
                        danger: true,
                        fields: [
                          {
                            name: "reason",
                            label: "Lý do hủy",
                            initialValue: "Dừng theo quyết định kiểm thử",
                            required: true,
                            multiline: true,
                            autoFocus: true,
                          },
                        ],
                        onConfirm: async (answer) => {
                          try {
                            await testingApi.abortRun(run._id, answer.reason);
                            onRunChange(await testingApi.getRun(run._id));
                          } catch (reason) {
                            throw new Error(messageOf(reason));
                          }
                        },
                      });
                    }}
                  >
                    Hủy lần chạy
                  </button>
                )}
                {can("testrun.complete") && (
                  <button
                    className="apple-button"
                    type="button"
                    disabled={savingExecution}
                    onClick={async () => {
                      try {
                        await testingApi.completeRun(run._id);
                        onRunChange(await testingApi.getRun(run._id));
                      } catch (reason) {
                        onError(messageOf(reason));
                      }
                    }}
                  >
                    Hoàn tất
                  </button>
                )}
              </>
            )}
          </div>
        }
      >
        <div className="flex flex-wrap items-center gap-x-6 gap-y-3 p-4">
          <StatusPill value={run.status} />
          <p className="text-sm">Mã: {run._id}</p>
          {run.test_plan_id && (
            <a
              className="text-sm underline"
              href={`/du-an/${encodeURIComponent(projectId)}/ke-hoach-kiem-thu/${encodeURIComponent(run.test_plan_id)}`}
            >
              Xem kế hoạch
            </a>
          )}
          <div className="min-w-48 text-sm">
            <p>
              Đã ghi nhận {recordedCases}/{totalCases} ca
            </p>
            <progress
              className="mt-1 w-full"
              value={recordedCases}
              max={totalCases || 1}
              aria-label="Tiến độ ghi nhận kết quả"
            />
          </div>
          {run.environment && (
            <p className="text-[13px]">
              <span className="text-ink-muted">Môi trường: </span>
              <span className="font-medium">{run.environment}</span>
            </p>
          )}
          {run.release && (
            <p className="text-[13px]">
              <span className="text-ink-muted">Bản phát hành: </span>
              <span className="font-medium">{run.release}</span>
            </p>
          )}
          {run.build && (
            <p className="break-all text-[13px]">
              <span className="text-ink-muted">Bản dựng: </span>
              <span className="font-medium">{run.build}</span>
            </p>
          )}
          {resumeContext && (
            <div className="mt-4 rounded-xl border border-border bg-surface-raised p-4 text-[13px]">
              {resumeContext.current_test_case_version ? (
                <>
                  <p className="font-semibold">Vị trí tiếp tục</p>
                  <p className="mt-2">
                    {resumeContext.current_test_case_version.test_case_key}{" "}
                    {resumeContext.current_test_case_version.title}
                  </p>
                  <p className="mt-1 text-ink-muted">
                    Ca {resumeContext.position} / {resumeContext.total_count} · còn{" "}
                    {resumeContext.remaining_count} ca chưa hoàn tất
                  </p>
                </>
              ) : (
                <p>Không còn ca kiểm thử được phân công cần thực thi</p>
              )}
            </div>
          )}
        </div>
      </Panel>
      {can("testrun.assign") && can("project.members.read") && assignmentEditing && (
        <Panel title="Phân công lần chạy">
          <div className="space-y-4 p-5">
            <label className="field-label block">
              Người phụ trách lần chạy
              <select
                aria-label="Người phụ trách lần chạy"
                className="apple-input mt-2"
                disabled={savingAssignment}
                value={runAssigneeDraft}
                onChange={(event) => setRunAssigneeDraft(event.target.value)}
              >
                <option value="">Chọn thành viên</option>
                {eligibleExecutors.map((member) => (
                  <option key={member.user_id} value={member.user_id}>
                    {member.user_label ||
                      member.user?.label ||
                      member.user?.full_name ||
                      member.user?.email ||
                      "Thành viên chưa có tên"}
                  </option>
                ))}
              </select>
            </label>
            {runAssigneeDraft && testCaseVersions.length > 1 && (
              <button
                className="secondary-button"
                type="button"
                disabled={savingAssignment}
                onClick={() =>
                  setAssignmentDraft(
                    Object.fromEntries(testCaseVersions.map(({ _id }) => [_id, runAssigneeDraft])),
                  )
                }
              >
                Gán người này cho tất cả ca
              </button>
            )}
            <div className="space-y-3">
              {(run.test_case_versions || []).map((version) => (
                <div
                  className="space-y-2 rounded-control border border-border p-3"
                  key={version._id}
                >
                  <label className="grid min-w-0 gap-2 text-sm sm:grid-cols-[minmax(0,1fr)_minmax(12rem,20rem)] sm:items-center">
                    <span className="break-words">
                      {version.test_case_key} · {version.title}
                    </span>
                    <select
                      aria-label={`Người thực hiện ${version.test_case_key}`}
                      className="apple-input"
                      disabled={savingAssignment}
                      value={assignmentDraft[version._id] || ""}
                      onChange={(event) =>
                        setAssignmentDraft((current) => ({
                          ...current,
                          [version._id]: event.target.value,
                        }))
                      }
                    >
                      <option value="">Chưa phân công ca này</option>
                      {eligibleExecutors.map((member) => (
                        <option key={member.user_id} value={member.user_id}>
                          {member.user_label ||
                            member.user?.label ||
                            member.user?.full_name ||
                            member.user?.email ||
                            "Thành viên chưa có tên"}
                        </option>
                      ))}
                    </select>
                  </label>
                </div>
              ))}
            </div>
            {!eligibleExecutors.length && (
              <p className="text-sm text-danger">
                Không có thành viên đủ quyền thực hiện để phân công.
              </p>
            )}
            <div className="flex flex-wrap justify-end gap-2">
              <button
                className="secondary-button"
                type="button"
                disabled={savingAssignment}
                onClick={() => setAssignmentEditing(false)}
              >
                Hủy
              </button>
              <button
                className="apple-button"
                type="button"
                disabled={!eligibleExecutors.length || savingAssignment}
                onClick={saveAssignments}
              >
                {savingAssignment ? "Đang lưu" : "Lưu phân công"}
              </button>
            </div>
          </div>
        </Panel>
      )}
      <div className="w-full">
        <Panel
          title="Kết quả từng ca"
          actions={
            testCaseVersions.length > 1 && (
              <nav aria-label="Điều hướng ca kiểm thử" className="flex items-center gap-2">
                <button
                  className="secondary-button"
                  type="button"
                  disabled={focusedCaseIndex <= 0}
                  onClick={() => navigateCase(focusedCaseIndex - 1)}
                >
                  Ca trước
                </button>
                <span className="min-w-12 text-center text-sm text-ink-muted">
                  {focusedCaseIndex + 1}/{testCaseVersions.length}
                </span>
                <button
                  className="secondary-button"
                  type="button"
                  disabled={focusedCaseIndex >= testCaseVersions.length - 1}
                  onClick={() => navigateCase(focusedCaseIndex + 1)}
                >
                  Ca tiếp
                </button>
              </nav>
            )
          }
        >
          {savingExecution && (
            <p className="px-5 pt-4 text-sm text-ink-muted" role="status">
              Đang lưu kết quả thực thi…
            </p>
          )}
          <div className="divide-y divide-border">
            {testCaseVersions.map((item, caseIndex) => {
              const result = run.results?.find((value) => value.test_case_version_id === item._id);
              const assigneeId = run.test_case_assignments?.[item._id];
              const assignee = assigneeId
                ? run.test_case_assignment_identities?.[assigneeId]?.display_name ||
                  "Thành viên không còn trong dự án"
                : "Chưa phân công";
              const linkedDefect = result
                ? (result.linked_defect_ids || []).length > 0 ||
                  run.defects?.some(
                    (defect) =>
                      defect.linked_test_result_id === result._id ||
                      (result.linked_defect_ids || []).includes(defect._id),
                  )
                : false;

              return (
                <article
                  className="min-w-0 scroll-mt-6 space-y-4 p-5"
                  id={`execution-case-${caseIndex}`}
                  key={item._id}
                >
                  <header className="flex min-w-0 flex-wrap items-start justify-between gap-3">
                    <div className="min-w-0 flex-1">
                      <div className="flex min-w-0 flex-wrap items-center gap-x-2 gap-y-1">
                        <span className="font-semibold">{item.test_case_key}</span>
                        {item.version !== null && item.version !== undefined && (
                          <span className="text-sm text-ink-muted">v{item.version}</span>
                        )}
                      </div>
                      <h3 className="mt-1 break-words font-medium">{item.title}</h3>
                    </div>
                    <div className="flex shrink-0 flex-wrap items-center gap-2">
                      {result ? (
                        <StatusPill value={result.status} />
                      ) : (
                        <span className="text-sm text-ink-muted">Chưa có kết quả</span>
                      )}
                    </div>
                  </header>
                  <p className="text-sm text-ink-muted">
                    Người thực hiện: <span className="text-ink">{assignee}</span>
                  </p>
                  {!result ? (
                    <p className="rounded-control bg-surface-raised px-3 py-2 text-sm text-ink-muted">
                      Chưa có kết quả cho ca này.
                    </p>
                  ) : !["NOT_RUN", "IN_PROGRESS"].includes(result.status) ? (
                    <div className="space-y-3">
                      <details className="rounded-control border border-border px-4 py-3">
                        <summary className="cursor-pointer text-sm font-medium text-ink">
                          Xem kết quả đã ghi nhận
                        </summary>
                        <div className="mt-3 space-y-4 border-t border-border pt-3 text-sm">
                          <div className="grid gap-4 md:grid-cols-2">
                            <div className="min-w-0">
                              <h4 className="text-xs font-medium text-ink-muted">
                                Kết quả mong đợi
                              </h4>
                              <p className="mt-1 whitespace-pre-wrap break-words">
                                {docText(item.expected_result_doc) || "Chưa có kết quả mong đợi"}
                              </p>
                            </div>
                            <div className="min-w-0">
                              <h4 className="text-xs font-medium text-ink-muted">
                                Kết quả thực tế
                              </h4>
                              <p className="mt-1 whitespace-pre-wrap break-words">
                                {docText(result.actual_result_doc) ||
                                  "Chưa ghi nhận kết quả thực tế"}
                              </p>
                            </div>
                          </div>
                          {(item.steps || []).map((step, stepIndex) => {
                            const stepResult = result.step_results?.find(
                              (value) => value.step_id === step.id,
                            );
                            if (!stepResult) return null;
                            return (
                              <section
                                className="border-t border-border pt-3"
                                key={step.id}
                                aria-label={`Kết quả bước ${stepIndex + 1}`}
                              >
                                <div className="flex flex-wrap items-center justify-between gap-2">
                                  <h4 className="font-medium">Bước {stepIndex + 1}</h4>
                                  <StatusPill value={stepResult.status} />
                                </div>
                                <p className="mt-2 break-words">{docText(step.action_doc)}</p>
                                <p className="mt-1 break-words text-ink-muted">
                                  Mong đợi: {docText(step.expected_doc) || "Chưa có"}
                                </p>
                                <p className="mt-1 whitespace-pre-wrap break-words">
                                  Thực tế: {docText(stepResult.actual_doc) || "Chưa ghi nhận"}
                                </p>
                                {stepResult.note && (
                                  <p className="mt-1 whitespace-pre-wrap break-words text-ink-muted">
                                    Ghi chú: {stepResult.note}
                                  </p>
                                )}
                              </section>
                            );
                          })}
                          {result.attachments?.length > 0 && (
                            <section className="border-t border-border pt-3">
                              <h4 className="font-medium">Tệp bằng chứng</h4>
                              <ul className="mt-2 space-y-1">
                                {result.attachments.map((attachment) => (
                                  <li className="break-all text-ink-muted" key={attachment.url}>
                                    {attachment.filename}
                                  </li>
                                ))}
                              </ul>
                            </section>
                          )}
                        </div>
                      </details>
                      <div className="flex flex-wrap items-center gap-3">
                        {linkedDefect && (
                          <span className="text-sm text-ink-muted">Đã liên kết lỗi</span>
                        )}
                      </div>
                      {result.status === "FAIL" &&
                        !linkedDefect &&
                        (can("defect.create") ||
                          (can("defect.read") && can("testrun.execute"))) && (
                          <InlineDefectForm
                            key={result._id}
                            result={result}
                            version={item}
                            members={members}
                            projectId={projectId}
                            canCreate={can("defect.create")}
                            canLink={can("defect.read") && can("testrun.execute")}
                            onLinked={async () => onRunChange(await testingApi.getRun(run._id))}
                            saving={creatingDefectResultIds.has(result._id)}
                            onCreate={onCreateInlineDefect}
                          />
                        )}
                      {linkedDefect &&
                        (run.defects || [])
                          .filter(
                            (defect) =>
                              defect.linked_test_result_id === result._id ||
                              (result.linked_defect_ids || []).includes(defect._id),
                          )
                          .map((defect) => {
                            const next = {
                              NEW: ["CONFIRMED", "defect.triage"],
                              CONFIRMED: ["IN_PROGRESS", "defect.transition.resolve"],
                              IN_PROGRESS: ["RESOLVED", "defect.transition.resolve"],
                              RESOLVED: ["READY_FOR_RETEST", "defect.transition.resolve"],
                              REOPENED: ["IN_PROGRESS", "defect.transition.resolve"],
                            }[defect.status];
                            return (
                              <div
                                className="flex flex-wrap items-center gap-3 text-sm"
                                key={defect._id}
                              >
                                <span>
                                  {defect.defect_key || defect._id} · {defect.title} ·{" "}
                                  {valueLabel(defect.status)} · {valueLabel(defect.severity)}
                                </span>
                                {next && can(next[1]) && (
                                  <button
                                    className="secondary-button"
                                    type="button"
                                    onClick={() =>
                                      ask({
                                        title: "Cập nhật trạng thái lỗi",
                                        confirmLabel: "Cập nhật",
                                        fields: [
                                          {
                                            name: "reason",
                                            label: "Lý do",
                                            required: true,
                                            multiline: true,
                                          },
                                        ],
                                        onConfirm: async ({ reason }) => {
                                          await testingApi.transitionDefect(defect._id, {
                                            expected_revision: defect.revision,
                                            to_status: next[0],
                                            reason,
                                          });
                                          onRunChange(await testingApi.getRun(run._id));
                                        },
                                      })
                                    }
                                  >
                                    {valueLabel(next[0])}
                                  </button>
                                )}
                              </div>
                            );
                          })}
                    </div>
                  ) : run.status !== "IN_PROGRESS" || !can("testrun.execute") ? null : (
                    <div className="min-w-0 space-y-4">
                      {(item.steps || []).map((step, stepIndex) => {
                        const existing = result.step_results?.find(
                          (value) => value.step_id === step.id,
                        );
                        const edited = stepResults[result._id]?.[step.id] || {};
                        return (
                          <fieldset
                            className="min-w-0 rounded-xl border border-border p-4"
                            key={step.id}
                          >
                            <legend className="px-2 text-[12px] font-semibold">
                              Bước {stepIndex + 1}
                            </legend>
                            <div className="grid min-w-0 gap-4 lg:grid-cols-[minmax(0,0.9fr)_minmax(0,1.1fr)]">
                              <div className="min-w-0 space-y-3">
                                <div>
                                  <h4 className="text-xs font-medium text-ink-muted">Thao tác</h4>
                                  <p className="mt-1 break-words text-[13px]">
                                    {docText(step.action_doc) || "Chưa có hướng dẫn thao tác"}
                                  </p>
                                </div>
                                <div>
                                  <h4 className="text-xs font-medium text-ink-muted">
                                    Kết quả mong đợi
                                  </h4>
                                  <p className="mt-1 break-words text-[13px]">
                                    {docText(step.expected_doc) || "Chưa có kết quả mong đợi"}
                                  </p>
                                </div>
                              </div>
                              <details className="min-w-0 space-y-3">
                                <summary className="cursor-pointer text-sm">
                                  Kết quả từng bước (tùy chọn)
                                </summary>
                                <label className="field-label block">
                                  Kết quả bước
                                  <select
                                    aria-label={`Trạng thái bước ${stepIndex + 1} ${item.test_case_key}`}
                                    className="apple-input mt-1 w-full min-w-0"
                                    disabled={savingExecution}
                                    value={edited.status || existing?.status || ""}
                                    onChange={(event) =>
                                      onStepResultsChange((values) => ({
                                        ...values,
                                        [result._id]: {
                                          ...values[result._id],
                                          [step.id]: {
                                            ...values[result._id]?.[step.id],
                                            status: event.target.value,
                                          },
                                        },
                                      }))
                                    }
                                  >
                                    <option value="">-</option>
                                    {terminalResultStatuses.map((value) => (
                                      <option value={value} key={value}>
                                        {valueLabel(value)}
                                      </option>
                                    ))}
                                  </select>
                                </label>
                                <label className="field-label block">
                                  Ghi nhận thực tế
                                  <textarea
                                    aria-label={`Kết quả bước ${stepIndex + 1} ${item.test_case_key}`}
                                    className="apple-input mt-1 min-h-16 w-full min-w-0"
                                    disabled={savingExecution}
                                    value={edited.actual ?? docText(existing?.actual_doc)}
                                    onChange={(event) =>
                                      onStepResultsChange((values) => ({
                                        ...values,
                                        [result._id]: {
                                          ...values[result._id],
                                          [step.id]: {
                                            ...values[result._id]?.[step.id],
                                            actual: event.target.value,
                                          },
                                        },
                                      }))
                                    }
                                  />
                                </label>
                                <label className="field-label block">
                                  Ghi chú
                                  <textarea
                                    aria-label={`Lý do trạng thái bước ${stepIndex + 1} ${item.test_case_key}`}
                                    className="apple-input mt-1 min-h-16 w-full min-w-0"
                                    disabled={savingExecution}
                                    value={edited.note ?? existing?.note ?? ""}
                                    onChange={(event) =>
                                      onStepResultsChange((values) => ({
                                        ...values,
                                        [result._id]: {
                                          ...values[result._id],
                                          [step.id]: {
                                            ...values[result._id]?.[step.id],
                                            note: event.target.value,
                                          },
                                        },
                                      }))
                                    }
                                    placeholder="Bắt buộc khi chọn Không áp dụng"
                                  />
                                </label>
                              </details>
                            </div>
                          </fieldset>
                        );
                      })}
                      {pendingFail[result._id] && (
                        <p className="text-sm">
                          Nhập kết quả thực tế. Bạn có thể lưu kết quả hoặc tạo hay liên kết lỗi
                          ngay bên dưới.
                        </p>
                      )}
                      <label className="field-label block">
                        Kết quả thực tế
                        <textarea
                          aria-label={`Kết quả thực tế ${item.test_case_key}`}
                          className="apple-input mt-1 min-h-20 w-full min-w-0"
                          disabled={savingExecution}
                          value={actuals[result._id] ?? docText(result.actual_result_doc)}
                          onChange={(event) =>
                            onActualsChange({ ...actuals, [result._id]: event.target.value })
                          }
                        />
                      </label>
                      {pendingFail[result._id] &&
                        !linkedDefect &&
                        (can("defect.create") ||
                          (can("defect.read") && can("testrun.execute"))) && (
                          <InlineDefectForm
                            result={result}
                            version={item}
                            members={members}
                            projectId={projectId}
                            canCreate={can("defect.create")}
                            canLink={can("defect.read") && can("testrun.execute")}
                            onLinked={async () => onRunChange(await testingApi.getRun(run._id))}
                            saving={creatingDefectResultIds.has(result._id) || savingExecution}
                            onCreate={onCreateInlineDefect}
                            ensureFail={async () => {
                              if (!(await onTransition(result, "FAIL", item)))
                                throw new Error("Chưa lưu được kết quả thất bại.");
                              const refreshed = await testingApi.getRun(run._id);
                              const updated = refreshed.results?.find(
                                (entry) => entry._id === result._id,
                              );
                              if (!updated || updated.status !== "FAIL")
                                throw new Error("Không tìm thấy kết quả thất bại vừa lưu.");
                              return updated;
                            }}
                          />
                        )}
                      <FilePicker
                        ariaLabel={`Tệp bằng chứng ${item.test_case_key}`}
                        buttonLabel="Chọn tệp bằng chứng"
                        disabled={savingExecution}
                        onChange={async (event) => {
                          const file = event.target.files?.[0];
                          if (!file) return;
                          try {
                            const uploaded = await uploadAssetAPI(file);
                            const linked = await testingApi.registerAttachment(projectId, {
                              filename: uploaded.data.filename,
                              url: uploaded.data.url,
                              item_id: uploaded.data.item_id,
                              size: uploaded.data.size,
                              content_type: uploaded.data.content_type,
                              artifact_type: "test_result",
                              artifact_id: result._id,
                            });
                            onAttachmentsChange((current) => ({
                              ...current,
                              [result._id]: [
                                ...(current[result._id] || result.attachments || []),
                                linked,
                              ],
                            }));
                          } catch (reason) {
                            onError(messageOf(reason));
                          }
                        }}
                      />
                      {(attachments[result._id] || result.attachments || []).map((attachment) => (
                        <p className="break-all text-[11px] text-ink-muted" key={attachment.url}>
                          {attachment.filename}
                        </p>
                      ))}
                      <div className="flex flex-wrap gap-2">
                        {terminalResultStatuses.map((value) => (
                          <button
                            className="secondary-button"
                            type="button"
                            disabled={savingExecution}
                            key={value}
                            onClick={async () => {
                              if (value === "FAIL" && !pendingFail[result._id]) {
                                setPendingFail((current) => ({ ...current, [result._id]: true }));
                                return;
                              }
                              const saved = await onTransition(result, value, item);
                              if (
                                saved &&
                                value === "PASS" &&
                                caseIndex + 1 < testCaseVersions.length
                              ) {
                                navigateCase(caseIndex + 1);
                              }
                            }}
                          >
                            {valueLabel(value)}
                          </button>
                        ))}
                      </div>
                    </div>
                  )}
                </article>
              );
            })}
          </div>
        </Panel>
      </div>
      {dialog}
    </WorkspacePage>
  );
}

function InlineDefectForm({
  result,
  version,
  members,
  saving,
  onCreate,
  projectId,
  canLink,
  canCreate,
  onLinked,
  ensureFail,
}) {
  const [title, setTitle] = useState(version.title || "");
  const [severity, setSeverity] = useState("");
  const [assignee, setAssignee] = useState("");
  const [error, setError] = useState("");
  const [candidates, setCandidates] = useState(null);
  const [selectedDefect, setSelectedDefect] = useState("");
  const [linking, setLinking] = useState(false);
  return (
    <section className="space-y-3 rounded-control border border-border p-4">
      <h4 className="font-medium">Lỗi từ kết quả thất bại</h4>
      {error && (
        <p className="text-sm text-danger" role="alert">
          {error}
        </p>
      )}
      {canCreate && (
        <>
          <label className="field-label block">
            Tiêu đề lỗi
            <input
              className="apple-input mt-2"
              value={title}
              onChange={(event) => setTitle(event.target.value)}
            />
          </label>
          <div className="grid gap-3 md:grid-cols-2">
            <label className="field-label">
              Mức độ nghiêm trọng
              <select
                className="apple-input mt-2"
                value={severity}
                onChange={(event) => setSeverity(event.target.value)}
              >
                <option value="">-</option>
                {[
                  ["critical", "Nghiêm trọng"],
                  ["high", "Cao"],
                  ["medium", "Trung bình"],
                  ["low", "Thấp"],
                ].map(([value, label]) => (
                  <option key={value} value={value}>
                    {label}
                  </option>
                ))}
              </select>
            </label>
            <label className="field-label">
              Người phụ trách
              <select
                className="apple-input mt-2"
                value={assignee}
                onChange={(event) => setAssignee(event.target.value)}
              >
                <option value="">-</option>
                {(members || [])
                  .filter((member) => member.status === "ACTIVE")
                  .map((member) => (
                    <option key={member.user_id} value={member.user_id}>
                      {member.user_label || member.user?.full_name || member.user_id}
                    </option>
                  ))}
              </select>
            </label>
          </div>
          <button
            className="apple-button"
            type="button"
            disabled={saving}
            onClick={async () => {
              if (title.trim().length < 2 || !severity) {
                setError("Nhập tiêu đề và chọn mức độ nghiêm trọng.");
                return;
              }
              setError("");
              try {
                const savedResult = ensureFail ? await ensureFail() : result;
                await onCreate(savedResult, version, { title, severity, assignee });
              } catch (reason) {
                setError(messageOf(reason));
              }
            }}
          >
            {saving ? "Đang tạo lỗi…" : "Tạo lỗi"}
          </button>
        </>
      )}
      {canLink && (
        <div className="space-y-2 border-t border-border pt-3">
          {candidates === null ? (
            <button
              className="secondary-button"
              type="button"
              onClick={async () => {
                try {
                  setCandidates(await testingApi.listDefects(projectId, { page_size: 500 }));
                } catch (reason) {
                  setError(messageOf(reason));
                }
              }}
            >
              Liên kết lỗi đã có
            </button>
          ) : (
            <div className="flex flex-wrap items-end gap-2">
              <label className="field-label min-w-0 flex-1">
                Lỗi đã có
                <select
                  className="apple-input mt-2"
                  value={selectedDefect}
                  onChange={(event) => setSelectedDefect(event.target.value)}
                >
                  <option value="">-</option>
                  {candidates.map((defect) => (
                    <option key={defect._id} value={defect._id}>
                      {defect.defect_key || defect._id} · {defect.title}
                    </option>
                  ))}
                </select>
              </label>
              <button
                className="secondary-button"
                type="button"
                disabled={!selectedDefect || linking}
                onClick={async () => {
                  setLinking(true);
                  setError("");
                  try {
                    const savedResult = ensureFail ? await ensureFail() : result;
                    await testingApi.linkResultDefect(projectId, savedResult._id, {
                      defect_id: selectedDefect,
                      expected_revision: savedResult.revision,
                    });
                    await onLinked();
                  } catch (reason) {
                    setError(messageOf(reason));
                  } finally {
                    setLinking(false);
                  }
                }}
              >
                {linking ? "Đang liên kết…" : "Liên kết"}
              </button>
            </div>
          )}
        </div>
      )}
    </section>
  );
}

