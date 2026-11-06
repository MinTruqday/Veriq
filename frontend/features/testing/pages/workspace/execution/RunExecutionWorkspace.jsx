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
  const activeTesters = (members || []).filter(
    (member) => member.status === "ACTIVE" && member.project_role === "TESTER",
  );
  const [assignmentEditing, setAssignmentEditing] = useState(false);
  const [assignmentDraft, setAssignmentDraft] = useState({});
  const [runAssigneeDraft, setRunAssigneeDraft] = useState("");
  const [savingAssignment, setSavingAssignment] = useState(false);
  const [assignmentProposal, setAssignmentProposal] = useState(null);
  const [loadingAssignmentProposal, setLoadingAssignmentProposal] = useState(false);
  const [executionAssistanceByResult, setExecutionAssistanceByResult] = useState({});
  const [executionAssistanceErrors, setExecutionAssistanceErrors] = useState({});
  const [loadingExecutionAssistanceIds, setLoadingExecutionAssistanceIds] = useState(
    () => new Set(),
  );
  const [creatingRerun, setCreatingRerun] = useState(false);
  const [resumingRun, setResumingRun] = useState(false);
  const [focusedCaseIndex, setFocusedCaseIndex] = useState(0);
  const rerunKey = useRef(null);
  const resumeOperation = useRef(null);
  const testCaseVersions = run.test_case_versions || [];
  const navigateCase = (index) => {
    const nextIndex = Math.max(0, Math.min(index, testCaseVersions.length - 1));
    setFocusedCaseIndex(nextIndex);
    document.getElementById(`execution-case-${nextIndex}`)?.scrollIntoView({
      behavior: "smooth",
      block: "start",
    });
  };
  const beginAssignmentEdit = () => {
    setAssignmentProposal(null);
    const assignments = { ...(run.test_case_assignments || {}) };
    setAssignmentDraft(assignments);
    setRunAssigneeDraft(
      run.assignee_id ||
        Object.values(assignments).find(Boolean) ||
        activeTesters[0]?.user_id ||
        "",
    );
    setAssignmentEditing(true);
  };
  const saveAssignments = async () => {
    const testCaseAssignments = Object.fromEntries(
      Object.entries(assignmentDraft).filter(
        ([versionId, assigneeId]) =>
          run.test_case_version_ids?.includes(versionId) && Boolean(assigneeId),
      ),
    );
    const proposedAssignments = Object.fromEntries(
      (assignmentProposal?.case_recommendations || [])
        .filter((item) => item.status === "PROPOSED" && item.assignee_id)
        .map((item) => [item.test_case_version_id, item.assignee_id]),
    );
    const effectiveProposal = { ...(run.test_case_assignments || {}), ...proposedAssignments };
    const proposalWasAccepted =
      assignmentProposal &&
      Object.entries(effectiveProposal).every(
        ([versionId, assigneeId]) => testCaseAssignments[versionId] === assigneeId,
      );
    const proposalWasAdjusted =
      assignmentProposal &&
      Object.entries(proposedAssignments).some(
        ([versionId, assigneeId]) => testCaseAssignments[versionId] !== assigneeId,
      );
    const assignmentDecisionSource =
      proposalWasAccepted && !proposalWasAdjusted
        ? "QA_APPROVED_RECOMMENDATION"
        : assignmentProposal
          ? "QA_ADJUSTED_RECOMMENDATION"
          : "MANUAL";
    const assignedProfileRevisions = Object.fromEntries(
      Object.entries(assignmentProposal?.skill_profile_revisions || {}).filter(([userId]) =>
        new Set([...Object.values(testCaseAssignments), runAssigneeDraft]).has(userId),
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
        expected_skill_profile_revisions: assignmentProposal ? assignedProfileRevisions : {},
        decision_source: assignmentDecisionSource,
      });
      onRunChange(updatedRun);
      setAssignmentEditing(false);
      setAssignmentProposal(null);
    } catch (reason) {
      onError(messageOf(reason));
    } finally {
      setSavingAssignment(false);
    }
  };
  const proposeAssignments = async () => {
    setLoadingAssignmentProposal(true);
    onError("");
    try {
      const proposal = await testingApi.recommendRunAssignment(projectId, run._id, {
        expected_run_revision: run.revision,
      });
      setAssignmentProposal(proposal);
      const recommended = Object.fromEntries(
        (proposal.case_recommendations || [])
          .filter((item) => item.status === "PROPOSED" && item.assignee_id)
          .map((item) => [item.test_case_version_id, item.assignee_id]),
      );
      setAssignmentDraft((current) => ({ ...current, ...recommended }));
      setRunAssigneeDraft(
        (current) => current || Object.values(recommended)[0] || activeTesters[0]?.user_id || "",
      );
      setAssignmentEditing(true);
    } catch (reason) {
      onError(messageOf(reason));
    } finally {
      setLoadingAssignmentProposal(false);
    }
  };
  const analyzeExecutionResult = async (result) => {
    setLoadingExecutionAssistanceIds((current) => new Set(current).add(result._id));
    setExecutionAssistanceErrors((current) => ({ ...current, [result._id]: "" }));
    setExecutionAssistanceByResult((current) => {
      const next = { ...current };
      delete next[result._id];
      return next;
    });
    try {
      const cached = await testingApi.getExecutionAssistance(projectId, run._id, result._id);
      if (cached?.stale) {
        setExecutionAssistanceByResult((current) => ({ ...current, [result._id]: cached }));
      }
      const response =
        cached && !cached.stale && cached.suggestions?.length
          ? cached
          : await testingApi.analyzeExecutionResult(projectId, run._id, result._id);
      setExecutionAssistanceByResult((current) => ({ ...current, [result._id]: response }));
    } catch (reason) {
      setExecutionAssistanceErrors((current) => ({
        ...current,
        [result._id]: messageOf(reason),
      }));
    } finally {
      setLoadingExecutionAssistanceIds((current) => {
        const next = new Set(current);
        next.delete(result._id);
        return next;
      });
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
                  disabled={!activeTesters.length || loadingAssignmentProposal}
                  onClick={() => void proposeAssignments()}
                >
                  {loadingAssignmentProposal ? "Đang lập đề xuất" : "Đề xuất người thực hiện"}
                </button>
                <button
                  className="secondary-button"
                  type="button"
                  disabled={!activeTesters.length}
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
            {["COMPLETED", "ABORTED"].includes(run.status) && can("testrun.create") && (
              <button
                className="secondary-button"
                type="button"
                disabled={creatingRerun}
                onClick={async () => {
                  setCreatingRerun(true);
                  rerunKey.current ||= crypto.randomUUID();
                  try {
                    const created = await testingApi.rerunRun(projectId, run._id, {
                      idempotency_key: rerunKey.current,
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
                {creatingRerun ? "Đang tạo lần chạy mới…" : "Chạy lại bằng lần chạy mới"}
              </button>
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
            {assignmentProposal && (
              <div className="rounded-control border border-border bg-surface-raised p-3 text-sm">
                <p className="font-medium">Đề xuất phân công</p>
                <p className="mt-1 text-ink-muted">
                  Gợi ý chưa được áp dụng. Kiểm tra từng ca, có thể đổi người hoặc chọn thủ công rồi
                  bấm “Duyệt và lưu phân công”.
                </p>
              </div>
            )}
            <label className="field-label block">
              Người phụ trách lần chạy
              <select
                aria-label="Người phụ trách lần chạy"
                className="apple-input mt-2"
                disabled={savingAssignment}
                value={runAssigneeDraft}
                onChange={(event) => setRunAssigneeDraft(event.target.value)}
              >
                <option value="">Chọn người kiểm thử</option>
                {activeTesters.map((member) => (
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
                      {activeTesters.map((member) => (
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
                  {assignmentProposal &&
                    (() => {
                      const item = assignmentProposal.case_recommendations?.find(
                        (candidate) => candidate.test_case_version_id === version._id,
                      );
                      if (!item) return null;
                      const suggestedMember = activeTesters.find(
                        (candidate) => candidate.user_id === item.assignee_id,
                      );
                      return (
                        <p className="text-xs text-ink-muted">
                          {item.status === "PROPOSED" ? (
                            <>
                              Veriq đề xuất theo hồ sơ kỹ năng và tải công việc:{" "}
                              <span className="font-medium text-ink">
                                {suggestedMember?.user_label ||
                                  suggestedMember?.user?.label ||
                                  suggestedMember?.user?.full_name ||
                                  suggestedMember?.user?.email ||
                                  item.assignee_label ||
                                  "Thành viên không còn trong dự án"}
                              </span>
                              {item.required_skills?.length
                                ? ` · Kỹ năng yêu cầu: ${item.required_skills.join(", ")}`
                                : " · Không yêu cầu kỹ năng cụ thể"}
                            </>
                          ) : item.status === "EXISTING_ASSIGNMENT_PRESERVED" ? (
                            "Giữ nguyên phân công hiện tại"
                          ) : item.status === "MAX_CONCURRENT_PROJECTS_REACHED" ? (
                            "Ứng viên đủ kỹ năng đã chạm mức dự án tối đa được Admin khai báo. Hãy xem lại giới hạn trước khi phân công thủ công."
                          ) : (
                            "Chưa có người khớp điều kiện; hãy chọn thủ công nếu cần."
                          )}
                        </p>
                      );
                    })()}
                </div>
              ))}
            </div>
            {!activeTesters.length && (
              <p className="text-sm text-danger">
                Không có người kiểm thử đang hoạt động để phân công.
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
                disabled={!activeTesters.length || savingAssignment}
                onClick={saveAssignments}
              >
                {savingAssignment
                  ? "Đang lưu"
                  : assignmentProposal
                    ? "Duyệt và lưu phân công"
                    : "Lưu phân công"}
              </button>
            </div>
          </div>
        </Panel>
      )}
      {!!run.unassigned_assignment_reasons?.length && (
        <Panel title="Ca chưa được tự phân công">
          <div className="space-y-2 p-5">
            <p className="text-sm text-ink-muted">
              Không có thành viên khả dụng khớp đủ kỹ năng đã xác nhận. Các ca này vẫn thuộc lần
              chạy nhưng cần người quản lý phân công.
            </p>
            {run.unassigned_assignment_reasons.map((item) => {
              const version = run.test_case_versions?.find(
                (candidate) => candidate._id === item.test_case_version_id,
              );
              return (
                <p className="break-words text-sm" key={item.test_case_version_id}>
                  {version?.test_case_key || "Ca kiểm thử không còn khả dụng"} ·{" "}
                  {version?.title || "Ca kiểm thử"}
                  {" — "}
                  {item.reason === "NO_FULL_SKILL_MATCH"
                    ? "Chưa có người khớp đủ kỹ năng"
                    : "Chưa có người kiểm thử khả dụng trong dự án"}
                </p>
              );
            })}
          </div>
        </Panel>
      )}
      {run.assignment_strategy === "CONFIRMED_SKILLS" &&
        Object.keys(run.test_case_assignment_decisions || {}).length > 0 && (
          <Panel title="Vì sao Veriq đề xuất phân công này">
            <div className="space-y-3 p-5">
              <p className="text-sm text-ink-muted">
                Đây là thông tin được ghi lại tại thời điểm tạo lần chạy; thay đổi hồ sơ thành viên
                sau đó không làm thay đổi lịch sử phân công.
              </p>
              {Object.entries(run.test_case_assignment_decisions).map(([versionId, decision]) => {
                const version = run.test_case_versions?.find(
                  (candidate) => candidate._id === versionId,
                );
                const reasonLabel = [
                  "CONFIRMED_SKILLS_THEN_LOWEST_ACTIVE_CASE_AND_RUN_LOAD",
                  "CONFIRMED_SKILLS_THEN_AVAILABILITY_AND_LOWEST_ACTIVE_CASE_AND_RUN_LOAD",
                ].includes(decision.reason)
                  ? "Khớp kỹ năng đã xác nhận, sau đó cân bằng tải ca và lần chạy"
                  : "Không yêu cầu kỹ năng cụ thể; cân bằng tải ca và lần chạy";

                return (
                  <section
                    className="grid min-w-0 gap-1 border-b border-border pb-3 text-sm last:border-b-0 last:pb-0"
                    key={versionId}
                  >
                    <h3 className="break-words font-medium">
                      {version?.test_case_key || "Ca kiểm thử không còn khả dụng"} ·{" "}
                      {version?.title || ""}
                    </h3>
                    <p className="break-words text-ink-muted">
                      Người thực hiện:{" "}
                      {run.test_case_assignment_identities?.[decision.assignee_id]?.display_name ||
                        "Thành viên không còn trong dự án"}
                      {" · "}
                      {reasonLabel}
                    </p>
                    <p className="break-words text-ink-muted">
                      Kỹ năng yêu cầu: {decision.required_skills?.join(", ") || "Không yêu cầu"}
                      {" · "}
                      Kỹ năng khớp: {decision.matched_skills?.join(", ") || "Không có"}
                    </p>
                    <p className="break-words text-ink-muted">
                      Trước khi phân công: {decision.active_run_count_before_assignment ?? 0} lần
                      chạy đang hoạt động, {decision.active_case_count_before_assignment ?? 0} ca
                      đang phụ trách
                      {" · "}
                      Khả dụng: {decision.availability_at_assignment || "Chưa ghi nhận"}
                    </p>
                  </section>
                );
              })}
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
                ? run.defects?.some((defect) => defect.linked_test_result_id === result._id)
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
                        {can("testrun.execute") && (
                          <button
                            className="secondary-button border-violet-300 text-violet-800"
                            type="button"
                            disabled={loadingExecutionAssistanceIds.has(result._id)}
                            onClick={() => void analyzeExecutionResult(result)}
                          >
                            {loadingExecutionAssistanceIds.has(result._id)
                              ? "Đang xem kết quả"
                              : "Nhờ Veriq phân tích kết quả"}
                          </button>
                        )}
                        {result.status === "FAIL" && !linkedDefect && can("defect.create") && (
                          <button
                            className="apple-button"
                            type="button"
                            disabled={creatingDefectResultIds.has(result._id)}
                            onClick={() => onCreateDefect(result, item)}
                          >
                            {creatingDefectResultIds.has(result._id)
                              ? "Đang tạo lỗi…"
                              : "Tạo lỗi từ kết quả thất bại"}
                          </button>
                        )}
                        {linkedDefect && (
                          <span className="text-sm text-ink-muted">Đã liên kết lỗi</span>
                        )}
                      </div>
                      {executionAssistanceErrors[result._id] && (
                        <p className="text-sm text-danger" role="alert">
                          {executionAssistanceErrors[result._id]}
                        </p>
                      )}
                      {executionAssistanceByResult[result._id]?.stale && (
                        <p className="text-sm text-ink-muted" role="status">
                          Kết quả thực thi đã thay đổi. Gợi ý cũ đã được ẩn; hãy chạy phân tích lại.
                        </p>
                      )}
                      {executionAssistanceByResult[result._id]?.suggestions?.[0] && (
                        <ExecutionAssistanceResult
                          result={executionAssistanceByResult[result._id]}
                          testResult={result}
                          caseVersion={item}
                          canCreateDefect={can("defect.create") && !linkedDefect}
                          creatingDefect={creatingDefectResultIds.has(result._id)}
                          onCreateDefect={onCreateDefect}
                        />
                      )}
                    </div>
                  ) : run.status !== "IN_PROGRESS" ||
                    !can("testrun.execute") ? null : result.status === "NOT_RUN" ? (
                    <div className="flex flex-wrap gap-2">
                      <button
                        className="secondary-button"
                        type="button"
                        disabled={savingExecution}
                        onClick={() => onTransition(result, "IN_PROGRESS", item)}
                      >
                        Bắt đầu ca kiểm thử
                      </button>
                      <button
                        className="secondary-button"
                        type="button"
                        disabled={savingExecution}
                        onClick={() => onTransition(result, "SKIPPED", item)}
                      >
                        Bỏ qua
                      </button>
                    </div>
                  ) : (
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
                              <div className="min-w-0 space-y-3">
                                <label className="field-label block">
                                  Kết quả bước
                                  <select
                                    aria-label={`Trạng thái bước ${stepIndex + 1} ${item.test_case_key}`}
                                    className="apple-input mt-1 w-full min-w-0"
                                    disabled={savingExecution}
                                    value={edited.status || existing?.status || "PASS"}
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
                              </div>
                            </div>
                          </fieldset>
                        );
                      })}
                      <label className="field-label block">
                        Kết quả chung của ca
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
                            onClick={() => onTransition(result, value, item)}
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

function ExecutionAssistanceResult({
  result,
  testResult,
  caseVersion,
  canCreateDefect,
  creatingDefect,
  onCreateDefect,
}) {
  const suggestion = result.suggestions[0];
  const warningLabels = (result.warnings || []).flatMap((warning) => {
    if (warning === "SENSITIVE_REQUEST_SUPPRESSED")
      return [
        "AI đã bỏ qua yêu cầu cung cấp thông tin đăng nhập; không gửi mật khẩu hoặc mã truy cập.",
      ];
    return /^[A-Z0-9]+(?:_[A-Z0-9]+)*$/.test(warning) ? [] : [warning];
  });
  const sourceLabel = (reference) =>
    reference.startsWith(`${testResult._id}:`)
      ? "Kết quả đã ghi"
      : reference.startsWith(`${caseVersion._id}:`)
        ? "Ca kiểm thử đang chạy"
        : "Thông tin lần chạy";

  return (
    <section className="space-y-3 rounded-control border border-violet-300 bg-violet-50/60 p-4 text-sm">
      <div>
        <p className="font-semibold text-violet-950">Veriq gợi ý xem xét</p>
        <p className="mt-1 text-violet-900">
          Đây là nhận xét tham khảo từ ca và kết quả đã lưu. Trạng thái kiểm thử không bị thay đổi.
        </p>
      </div>
      {suggestion.observations.map((observation, index) => (
        <article
          className="space-y-1 rounded-control border border-violet-200 bg-white/70 p-3"
          key={`${observation.step_id || "general"}-${index}`}
        >
          <p className="font-medium text-ink">
            {observation.kind === "OBSERVED"
              ? "Thông tin đã ghi"
              : observation.kind === "POSSIBLE_INTERPRETATION"
                ? "Cách diễn giải có thể có"
                : "Giới hạn thông tin"}
            {observation.step_id ? ` · Bước ${observation.step_id}` : ""}
          </p>
          <p className="whitespace-pre-wrap text-ink-muted">{observation.text}</p>
          {observation.evidence_quotes.map((quote, quoteIndex) => (
            <blockquote
              className="border-l-2 border-violet-300 pl-3 text-xs text-ink-muted"
              key={`${quote.evidence_ref}-${quoteIndex}`}
            >
              “{quote.quote}” <span>— {sourceLabel(quote.evidence_ref)}</span>
            </blockquote>
          ))}
        </article>
      ))}
      {!!suggestion.missing_information.length && (
        <div>
          <p className="font-medium">Thông tin nên bổ sung</p>
          <ul className="mt-1 list-disc space-y-1 pl-5 text-ink-muted">
            {suggestion.missing_information.map((value, index) => (
              <li key={`${index}-${value}`}>{value}</li>
            ))}
          </ul>
        </div>
      )}
      {!!warningLabels.length && <p className="text-ink-muted">{warningLabels.join(" · ")}</p>}
      {suggestion.defect_draft && (
        <div className="space-y-2 rounded-control border border-violet-200 bg-white/70 p-3">
          <div>
            <p className="font-medium">Bản nháp lỗi</p>
            <p className="text-xs text-ink-muted">
              Chưa tạo lỗi. Bạn có thể mở bản nháp, chỉnh nội dung và xác nhận riêng.
            </p>
          </div>
          <p className="font-medium">{suggestion.defect_draft.title}</p>
          <p className="whitespace-pre-wrap text-ink-muted">
            {suggestion.defect_draft.description}
          </p>
          {suggestion.defect_draft.evidence_quotes.map((quote, index) => (
            <blockquote
              className="border-l-2 border-violet-300 pl-3 text-xs text-ink-muted"
              key={`${quote.evidence_ref}-${index}`}
            >
              “{quote.quote}” <span>— {sourceLabel(quote.evidence_ref)}</span>
            </blockquote>
          ))}
          {canCreateDefect && (
            <button
              className="secondary-button border-violet-300 text-violet-800"
              type="button"
              disabled={creatingDefect}
              onClick={() => onCreateDefect(testResult, caseVersion, suggestion.defect_draft)}
            >
              {creatingDefect ? "Đang mở bản nháp" : "Rà soát bản nháp lỗi"}
            </button>
          )}
        </div>
      )}
    </section>
  );
}
