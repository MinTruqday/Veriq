"use client";

import { useRef, useState } from "react";
import { uploadAssetAPI } from "@/features/cloud/services/upload.service";
import DataTable from "../../../components/DataTable";
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
  const activeTesters = (members || []).filter((member) => {
    const roles = member.project_roles || [member.project_role];
    return member.status === "ACTIVE" && roles.includes("TESTER");
  });
  const [assignmentEditing, setAssignmentEditing] = useState(false);
  const [assignmentDraft, setAssignmentDraft] = useState({});
  const [runAssigneeDraft, setRunAssigneeDraft] = useState("");
  const [savingAssignment, setSavingAssignment] = useState(false);
  const [creatingRerun, setCreatingRerun] = useState(false);
  const rerunKey = useRef(null);
  const beginAssignmentEdit = () => {
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
        title="Điều khiển lần chạy"
        actions={
          <div className="flex flex-wrap gap-2">
            {can("testrun.assign") && can("project.members.read") && (
              <button
                className="secondary-button"
                type="button"
                disabled={!activeTesters.length}
                onClick={beginAssignmentEdit}
              >
                Sửa phân công
              </button>
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
                    disabled={savingExecution}
                    onClick={async () => {
                      try {
                        const value = await testingApi.resumeRun(projectId, run._id, {
                          expected_revision: run.revision,
                          idempotency_key: crypto.randomUUID(),
                        });
                        onResumeChange(value);
                        onRunChange(await testingApi.getRun(run._id));
                      } catch (reason) {
                        onError(messageOf(reason));
                      }
                    }}
                  >
                    Tiếp tục thực thi
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
        <div className="p-5">
          <StatusPill value={run.status} />
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
                    Vị trí {resumeContext.position} trên {resumeContext.total_count} còn lại{" "}
                    {resumeContext.remaining_count}
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
                <option value="">Chọn Tester</option>
                {activeTesters.map((member) => (
                  <option key={member.user_id} value={member.user_id}>
                    {member.user_label || member.user?.label || member.user_id}
                  </option>
                ))}
              </select>
            </label>
            <div className="space-y-3">
              {(run.test_case_versions || []).map((version) => (
                <label
                  className="grid min-w-0 gap-2 text-sm sm:grid-cols-[minmax(0,1fr)_minmax(12rem,20rem)] sm:items-center"
                  key={version._id}
                >
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
                        {member.user_label || member.user?.label || member.user_id}
                      </option>
                    ))}
                  </select>
                </label>
              ))}
            </div>
            {!activeTesters.length && (
              <p className="text-sm text-danger">Không có Tester đang hoạt động để phân công.</p>
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
                {savingAssignment ? "Đang lưu" : "Lưu phân công"}
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
                  {version?.test_case_key || item.test_case_version_id} ·{" "}
                  {version?.title || "Ca kiểm thử"}
                  {" — "}
                  {item.reason === "NO_FULL_SKILL_MATCH"
                    ? "Chưa có người khớp đủ kỹ năng"
                    : "Chưa có Tester khả dụng trong dự án"}
                </p>
              );
            })}
          </div>
        </Panel>
      )}
      {run.assignment_strategy === "CONFIRMED_SKILLS" &&
        Object.keys(run.test_case_assignment_decisions || {}).length > 0 && (
          <Panel title="Căn cứ phân công tự động">
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
                      {version?.test_case_key || versionId} · {version?.title || "Ca kiểm thử"}
                    </h3>
                    <p className="break-words text-ink-muted">
                      Người thực hiện:{" "}
                      {run.test_case_assignment_identities?.[decision.assignee_id]?.display_name ||
                        decision.assignee_id ||
                        "Chưa phân công"}
                      {" · "}
                      {reasonLabel}
                    </p>
                    <p className="break-words text-ink-muted">
                      Kỹ năng yêu cầu: {decision.required_skills?.join(", ") || "Không yêu cầu"}
                      {" · "}
                      Kỹ năng khớp: {decision.matched_skills?.join(", ") || "Không có"}
                    </p>
                    {!!decision.matched_skill_evidence?.length && (
                      <ul className="space-y-1 pl-4 text-xs text-ink-muted">
                        {decision.matched_skill_evidence.map((item, index) => (
                          <li className="break-words" key={`${item.name}-${index}`}>
                            {item.name}: {item.evidence || "Đã xác nhận, không có trích dẫn"}
                            {item.source_block_id ? ` · nguồn ${item.source_block_id}` : ""}
                            {item.source_page_no ? ` · trang ${item.source_page_no}` : ""}
                          </li>
                        ))}
                      </ul>
                    )}
                    <p className="break-words text-ink-muted">
                      Hồ sơ kỹ năng phiên bản {decision.skill_profile_revision ?? 0}
                      {" · "}
                      Số đợt đang chạy trước khi gán:{" "}
                      {decision.active_run_count_before_assignment ?? 0}
                      {" · "}
                      Tải ca trước khi gán: {decision.active_case_count_before_assignment ?? 0}
                      {" · "}
                      Tình trạng khả dụng: {decision.availability_at_assignment || "Chưa ghi nhận"}
                    </p>
                  </section>
                );
              })}
            </div>
          </Panel>
        )}
      <Panel title="Kết quả thủ công">
        {savingExecution && (
          <p className="px-5 pt-4 text-sm text-ink-muted" role="status">
            Đang lưu kết quả thực thi…
          </p>
        )}
        <DataTable
          items={run.test_case_versions || []}
          columns={[
            { key: "test_case_key", label: "Ca kiểm thử" },
            { key: "version", label: "Phiên bản", render: (item) => `v${item.version}` },
            { key: "title", label: "Tên" },
            {
              key: "assignee",
              label: "Người thực hiện",
              render: (item) => {
                const assigneeId = run.test_case_assignments?.[item._id];
                return (
                  run.test_case_assignment_identities?.[assigneeId]?.display_name ||
                  assigneeId ||
                  "Chưa phân công"
                );
              },
            },
            {
              key: "result",
              label: "Kết quả",
              render: (item) => {
                const result = run.results?.find(
                  (value) => value.test_case_version_id === item._id,
                );
                if (!result) return "Không có ảnh chụp thực thi";
                if (!["NOT_RUN", "IN_PROGRESS"].includes(result.status)) {
                  const hasDefect = run.defects?.some(
                    (defect) => defect.linked_test_result_id === result._id,
                  );
                  return (
                    <span className="flex min-w-0 flex-col items-start gap-2">
                      <StatusPill value={result.status} />
                      {result.status === "FAIL" && !hasDefect && can("defect.create") && (
                        <button
                          className="apple-button"
                          type="button"
                          onClick={() => onCreateDefect(result, item)}
                        >
                          Tạo lỗi từ kết quả thất bại
                        </button>
                      )}
                      {hasDefect && (
                        <span className="text-[11px] text-ink-muted">Đã liên kết lỗi</span>
                      )}
                    </span>
                  );
                }
                if (run.status !== "IN_PROGRESS") {
                  return <StatusPill value={result.status} />;
                }
                if (!can("testrun.execute")) {
                  return <StatusPill value={result.status} />;
                }
                if (result.status === "NOT_RUN") {
                  return (
                    <span className="flex flex-wrap gap-2">
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
                    </span>
                  );
                }
                return (
                  <div className="min-w-0 space-y-3">
                    {(item.steps || []).map((step, stepIndex) => {
                      const existing = result.step_results?.find(
                        (value) => value.step_id === step.id,
                      );
                      const edited = stepResults[result._id]?.[step.id] || {};
                      return (
                        <fieldset
                          className="space-y-2 rounded-xl border border-border p-3"
                          key={step.id}
                        >
                          <legend className="px-2 text-[12px] font-semibold">
                            Bước {stepIndex + 1}
                          </legend>
                          <p className="text-[12px]">{docText(step.action_doc)}</p>
                          <p className="text-[12px] text-ink-muted">
                            Mong đợi {docText(step.expected_doc)}
                          </p>
                          <select
                            aria-label={`Trạng thái bước ${stepIndex + 1} ${item.test_case_key}`}
                            className="apple-input"
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
                          <textarea
                            aria-label={`Kết quả bước ${stepIndex + 1} ${item.test_case_key}`}
                            className="apple-input min-h-16"
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
                            placeholder="Kết quả thực tế của bước"
                          />
                          <textarea
                            aria-label={`Lý do trạng thái bước ${stepIndex + 1} ${item.test_case_key}`}
                            className="apple-input min-h-16"
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
                            placeholder="Ghi chú hoặc lý do Không áp dụng"
                          />
                        </fieldset>
                      );
                    })}
                    <textarea
                      aria-label={`Kết quả thực tế ${item.test_case_key}`}
                      className="apple-input min-h-20"
                      disabled={savingExecution}
                      value={actuals[result._id] ?? docText(result.actual_result_doc)}
                      onChange={(event) =>
                        onActualsChange({ ...actuals, [result._id]: event.target.value })
                      }
                      placeholder="Kết quả thực tế và bằng chứng"
                    />
                    <FilePicker
                      ariaLabel={`Tệp bằng chứng ${item.test_case_key}`}
                      buttonLabel="Chọn tệp bằng chứng"
                      disabled={savingExecution}
                      onChange={async (event) => {
                        const file = event.target.files?.[0];
                        if (!file) return;
                        try {
                          const uploaded = await uploadAssetAPI(file);
                          onAttachmentsChange((current) => ({
                            ...current,
                            [result._id]: [
                              ...(current[result._id] || result.attachments || []),
                              uploaded.data,
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
                    <span className="flex flex-wrap gap-2">
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
                    </span>
                  </div>
                );
              },
              mobileRender: (item) => {
                const result = run.results?.find(
                  (value) => value.test_case_version_id === item._id,
                );
                return result
                  ? `Kết quả ${valueLabel(result.status)}`
                  : "Không có ảnh chụp thực thi";
              },
            },
          ]}
        />
      </Panel>
      {dialog}
    </WorkspacePage>
  );
}
