"use client";
import { useCallback, useEffect, useState } from "react";
import DataTable from "./DataTable";
import ReviewChecklist from "./ReviewChecklist";
import ReviewFindingsTable from "./ReviewFindingsTable";
import { ErrorState, Panel, StatusPill, useActionDialog } from "./WorkspacePrimitives";
import { messageOf, valueLabel } from "../lib/testing";
import { testingApi } from "../services/testing.service";

export default function FormalReviewPanel({
  project,
  artifactType,
  artifactId,
  artifactVersionId,
  reviewType,
  readOnly = false,
}) {
  const [sessions, setSessions] = useState([]);
  const [selected, setSelected] = useState(null);
  const [members, setMembers] = useState([]);
  const [error, setError] = useState("");
  const { ask, dialog } = useActionDialog();
  const can = (permission) => project.current_permissions?.includes(permission);
  const userId = project.current_membership?.user_id;
  const membershipRoles = project.current_membership?.project_roles;
  const memberRoles =
    Array.isArray(membershipRoles) && membershipRoles.length
      ? membershipRoles
      : [project.current_membership?.project_role].filter(Boolean);
  const load = useCallback(async () => {
    try {
      const permissions = new Set(project.current_permissions || []);
      const [result, memberValues] = await Promise.all([
        testingApi.listReviewSessions(project._id, { artifact_type: artifactType }),
        permissions.has("project.members.read")
          ? testingApi.listMembers(project._id)
          : Promise.resolve([]),
      ]);
      const values = (result.items || []).filter(
        (item) => item.artifact_id === artifactId && item.artifact_version_id === artifactVersionId,
      );
      setSessions(values);
      setMembers(memberValues.filter((item) => item.status === "ACTIVE"));
      if (selected?._id) setSelected(await testingApi.getReviewSession(selected._id));
    } catch (reason) {
      setError(messageOf(reason));
    }
  }, [
    artifactId,
    artifactType,
    artifactVersionId,
    project._id,
    project.current_permissions,
    selected?._id,
  ]);
  useEffect(() => {
    void load();
  }, [load]);
  const memberOptions = members.map((item) => ({
    value: item.user_id,
    label: item.user_label || item.email || "Thành viên",
  }));
  const memberName = (value) =>
    !value
      ? "Chưa phân công"
      : memberOptions.find((item) => item.value === value)?.label ||
        "Thành viên không còn trong danh sách";
  const participantsAreValid = (moderatorId, authorId, reviewerIds) => {
    const values = Array.isArray(reviewerIds) ? reviewerIds : [reviewerIds];
    if (values.includes(moderatorId) || values.includes(authorId)) {
      setError("Người rà soát phải khác người điều phối và tác giả");
      return false;
    }
    return true;
  };
  const create = async () => {
    const answer = await ask({
      title: "Tạo phiên rà soát chính thức",
      confirmLabel: "Tạo phiên",
      fields: [
        { name: "objective", label: "Mục tiêu", required: true, multiline: true, autoFocus: true },
        {
          name: "moderator_id",
          label: "Người điều phối",
          required: true,
          options: [{ value: "", label: "Chọn thành viên" }, ...memberOptions],
        },
        {
          name: "reviewer_ids",
          label: "Người rà soát",
          required: true,
          multiple: true,
          options: memberOptions,
        },
        {
          name: "author_id",
          label: "Tác giả",
          required: true,
          options: [{ value: "", label: "Chọn thành viên" }, ...memberOptions],
        },
        {
          name: "scribe_id",
          label: "Người ghi biên bản",
          options: [{ value: "", label: "Không phân công" }, ...memberOptions],
        },
      ],
    });
    if (!answer) return;
    if (!participantsAreValid(answer.moderator_id, answer.author_id, answer.reviewer_ids)) return;
    try {
      const value = await testingApi.createReviewSession(project._id, {
        idempotency_key: crypto.randomUUID(),
        review_type: reviewType,
        artifact_type: artifactType,
        artifact_id: artifactId,
        artifact_version_id: artifactVersionId,
        objective: answer.objective,
        checklist_version: "1",
        moderator_id: answer.moderator_id,
        author_id: answer.author_id,
        reviewers: answer.reviewer_ids,
        scribe_id: answer.scribe_id || null,
        checklist: [],
      });
      setSelected(value);
      await load();
    } catch (reason) {
      setError(messageOf(reason));
    }
  };
  const transition = async (action, mode = "start") => {
    if (!selected) return;
    const decision = mode === "decision";
    const complete = mode === "complete";
    const answer = await ask({
      title: decision
        ? "Ghi nhận quyết định rà soát"
        : complete
          ? "Hoàn tất phiên rà soát"
          : "Bắt đầu phiên rà soát",
      confirmLabel: decision ? "Ghi quyết định" : complete ? "Hoàn tất" : "Bắt đầu",
      fields: decision
        ? [
            {
              name: "decision",
              label: "Quyết định",
              required: true,
              options: ["ACCEPTED", "ACCEPTED_WITH_ACTIONS", "REWORK_REQUIRED", "REJECTED"].map(
                (value) => ({ value, label: valueLabel(value) }),
              ),
            },
            { name: "note", label: "Ghi chú", multiline: true },
          ]
        : [{ name: "note", label: "Ghi chú", multiline: true }],
    });
    if (!answer) return;
    try {
      setSelected(await action(selected._id, { expected_revision: selected.revision, ...answer }));
      await load();
    } catch (reason) {
      setError(messageOf(reason));
    }
  };
  const addFinding = async () => {
    const answer = await ask({
      title: "Thêm phát hiện",
      confirmLabel: "Thêm",
      fields: [
        {
          name: "severity",
          label: "Mức độ",
          options: ["MAJOR", "MINOR", "QUESTION", "IMPROVEMENT"].map((value) => ({
            value,
            label: valueLabel(value),
          })),
        },
        {
          name: "category",
          label: "Nhóm",
          options: [
            "CORRECTNESS",
            "COMPLETENESS",
            "CONSISTENCY",
            "TESTABILITY",
            "TRACEABILITY",
            "SECURITY",
            "PERFORMANCE",
            "MAINTAINABILITY",
          ].map((value) => ({ value, label: valueLabel(value) })),
        },
        { name: "description", label: "Nội dung", required: true, multiline: true },
        {
          name: "owner_id",
          label: "Người xử lý",
          options: [{ value: "", label: "Chưa phân công" }, ...memberOptions],
        },
        { name: "due_at", label: "Hạn xử lý", type: "datetime-local" },
      ],
    });
    if (!answer) return;
    try {
      await testingApi.createReviewFinding(selected._id, {
        ...answer,
        owner_id: answer.owner_id || null,
        due_at: answer.due_at ? new Date(answer.due_at).toISOString() : null,
        anchor: {},
        suggested_action: "",
      });
      setSelected(await testingApi.getReviewSession(selected._id));
    } catch (reason) {
      setError(messageOf(reason));
    }
  };
  const assignParticipants = async () => {
    const answer = await ask({
      title: "Phân công phiên rà soát",
      confirmLabel: "Lưu phân công",
      fields: [
        {
          name: "moderator_id",
          label: "Người điều phối",
          required: true,
          options: [{ value: "", label: "Chọn thành viên" }, ...memberOptions],
          initialValue: selected.moderator_id,
        },
        {
          name: "reviewer_ids",
          label: "Người rà soát",
          required: true,
          multiple: true,
          options: memberOptions,
          initialValue: selected.reviewer_ids || selected.reviewers || [],
        },
        {
          name: "scribe_id",
          label: "Người ghi biên bản",
          options: [{ value: "", label: "Không phân công" }, ...memberOptions],
          initialValue: selected.scribe_id || "",
        },
      ],
    });
    if (!answer) return;
    if (!participantsAreValid(answer.moderator_id, selected.author_id, answer.reviewer_ids)) return;
    try {
      setSelected(
        await testingApi.assignReviewSessionReviewers(selected._id, {
          expected_revision: selected.revision,
          moderator_id: answer.moderator_id,
          reviewer_ids: answer.reviewer_ids,
          scribe_id: answer.scribe_id || null,
        }),
      );
      await load();
    } catch (reason) {
      setError(messageOf(reason));
    }
  };
  const assignFinding = async (item) => {
    const answer = await ask({
      title: "Gán phát hiện",
      confirmLabel: "Gán",
      fields: [
        {
          name: "owner_id",
          label: "Người xử lý",
          required: true,
          options: [{ value: "", label: "Chọn thành viên" }, ...memberOptions],
          initialValue: item.owner_id,
        },
      ],
    });
    if (!answer) return;
    try {
      await testingApi.assignReviewFinding(item._id, {
        expected_revision: item.revision,
        owner_id: answer.owner_id,
      });
      setSelected(await testingApi.getReviewSession(selected._id));
    } catch (reason) {
      setError(messageOf(reason));
    }
  };
  const resolveFinding = async (item) => {
    const answer = await ask({
      title: "Giải quyết phát hiện",
      confirmLabel: "Ghi nhận",
      fields: [{ name: "resolution", label: "Kết quả", required: true, multiline: true }],
    });
    if (!answer) return;
    try {
      await testingApi.resolveReviewFinding(item._id, {
        expected_revision: item.revision,
        resolution: answer.resolution,
      });
      setSelected(await testingApi.getReviewSession(selected._id));
    } catch (reason) {
      setError(messageOf(reason));
    }
  };
  const verifyFinding = async (item) => {
    const answer = await ask({
      title: "Xác minh phát hiện",
      confirmLabel: "Xác minh",
      fields: [{ name: "note", label: "Kết quả xác minh", required: true, multiline: true }],
    });
    if (!answer) return;
    try {
      await testingApi.verifyReviewFinding(item._id, {
        expected_revision: item.revision,
        note: answer.note,
      });
      setSelected(await testingApi.getReviewSession(selected._id));
    } catch (reason) {
      setError(messageOf(reason));
    }
  };
  const createFollowUp = async () => {
    const answer = await ask({
      title: "Tạo phiên rà soát tiếp theo",
      confirmLabel: "Tạo phiên",
      fields: [
        { name: "objective", label: "Mục tiêu", required: true, multiline: true },
        {
          name: "moderator_id",
          label: "Người điều phối",
          required: true,
          options: [{ value: "", label: "Chọn thành viên" }, ...memberOptions],
          initialValue: selected.moderator_id,
        },
        {
          name: "reviewer_ids",
          label: "Người rà soát",
          required: true,
          multiple: true,
          options: memberOptions,
          initialValue: selected.reviewer_ids || selected.reviewers || [],
        },
      ],
    });
    if (!answer) return;
    if (!participantsAreValid(answer.moderator_id, selected.author_id, answer.reviewer_ids)) return;
    try {
      setSelected(
        await testingApi.createFollowUpReviewSession(selected._id, {
          expected_revision: selected.revision,
          idempotency_key: crypto.randomUUID(),
          objective: answer.objective,
          moderator_id: answer.moderator_id,
          reviewer_ids: answer.reviewer_ids,
          scribe_id: null,
        }),
      );
      await load();
    } catch (reason) {
      setError(messageOf(reason));
    }
  };
  const terminalTransition = async (targetStatus) => {
    const title = targetStatus === "ARCHIVED" ? "Lưu trữ phiên rà soát" : "Hủy phiên rà soát";
    const answer = await ask({
      title,
      confirmLabel: title,
      fields: [{ name: "note", label: "Lý do", required: true, multiline: true }],
    });
    if (!answer) return;
    try {
      setSelected(
        await testingApi.transitionReviewSessionTerminal(selected._id, {
          expected_revision: selected.revision,
          target_status: targetStatus,
          note: answer.note,
        }),
      );
      await load();
    } catch (reason) {
      setError(messageOf(reason));
    }
  };
  return (
    <Panel
      title="Rà soát chính thức"
      actions={
        !readOnly && can("reviewsession.create") && can("project.members.read") ? (
          <button className="apple-button" type="button" onClick={create}>
            Tạo phiên rà soát
          </button>
        ) : null
      }
    >
      {dialog}
      {error && (
        <div className="p-4">
          <ErrorState message={error} />
        </div>
      )}
      {readOnly && (
        <p className="px-5 pt-4 text-sm text-ink-muted" role="status">
          Chỉ xem lịch sử rà soát.
        </p>
      )}
      <DataTable
        items={sessions}
        empty="Chưa có phiên rà soát"
        columns={[
          { key: "review_type", label: "Loại", render: (item) => valueLabel(item.review_type) },
          {
            key: "status",
            label: "Trạng thái",
            render: (item) => <StatusPill value={item.status} />,
          },
          {
            key: "decision",
            label: "Quyết định",
            render: (item) => (item.decision ? valueLabel(item.decision) : "Chưa có"),
          },
          {
            key: "action",
            label: "Thao tác",
            render: (item) => (
              <button
                className="secondary-button"
                type="button"
                onClick={async () => setSelected(await testingApi.getReviewSession(item._id))}
              >
                Mở
              </button>
            ),
          },
        ]}
      />
      {selected && (
        <div className="space-y-4 border-t border-border p-5">
          <div className="flex flex-wrap items-center justify-between gap-3">
            <div>
              <p className="font-semibold">{selected.objective}</p>
              <p className="text-sm text-ink-muted">
                {selected.checklist_version
                  ? `Danh sách tiêu chí phiên bản ${selected.checklist_version}`
                  : "Danh sách tiêu chí rà soát"}
              </p>
            </div>
            <div className="flex flex-wrap gap-2">
              {!readOnly && (
                <>
                  {selected.status === "PLANNED" && can("reviewsession.update") && (
                    <>
                      <button
                        className="secondary-button"
                        type="button"
                        onClick={assignParticipants}
                      >
                        Phân công
                      </button>
                      {selected.moderator_id === userId && (
                        <button
                          className="secondary-button"
                          type="button"
                          onClick={() => transition(testingApi.startReviewSession)}
                        >
                          Bắt đầu
                        </button>
                      )}
                      {can("reviewsession.complete") && selected.moderator_id === userId && (
                        <button
                          className="danger-button"
                          type="button"
                          onClick={() => terminalTransition("CANCELLED")}
                        >
                          Hủy phiên
                        </button>
                      )}
                    </>
                  )}
                  {selected.status === "IN_PROGRESS" && can("reviewsession.finding.manage") && (
                    <button className="secondary-button" type="button" onClick={addFinding}>
                      Thêm phát hiện
                    </button>
                  )}
                  {selected.status === "IN_PROGRESS" &&
                    can("reviewsession.complete") &&
                    selected.moderator_id === userId && (
                      <button
                        className="apple-button"
                        type="button"
                        onClick={() =>
                          transition(testingApi.recordReviewSessionDecision, "decision")
                        }
                      >
                        Ghi quyết định
                      </button>
                    )}
                  {selected.status === "DECISION_PENDING" &&
                    can("reviewsession.complete") &&
                    selected.moderator_id === userId && (
                      <button
                        className="apple-button"
                        type="button"
                        onClick={() => transition(testingApi.completeReviewSession, "complete")}
                      >
                        Hoàn tất
                      </button>
                    )}
                  {selected.status === "COMPLETED" && can("reviewsession.create") && (
                    <button className="secondary-button" type="button" onClick={createFollowUp}>
                      Tạo phiên tiếp theo
                    </button>
                  )}
                  {selected.status === "COMPLETED" &&
                    can("reviewsession.complete") &&
                    selected.moderator_id === userId && (
                      <button
                        className="secondary-button"
                        type="button"
                        onClick={() => terminalTransition("ARCHIVED")}
                      >
                        Lưu trữ
                      </button>
                    )}
                </>
              )}
              <button
                className="secondary-button"
                type="button"
                onClick={() =>
                  testingApi
                    .exportReviewSession(selected._id)
                    .catch((reason) => setError(messageOf(reason)))
                }
              >
                Xuất CSV
              </button>
            </div>
          </div>
          <div className="grid gap-3 text-sm sm:grid-cols-4">
            <p>
              <span className="field-label">Người điều phối</span>
              <br />
              {memberName(selected.moderator_id)}
            </p>
            <p>
              <span className="field-label">Tác giả</span>
              <br />
              {memberName(selected.author_id)}
            </p>
            <p>
              <span className="field-label">Người rà soát</span>
              <br />
              {(selected.reviewer_ids || selected.reviewers || []).map(memberName).join(" · ")}
            </p>
            <p>
              <span className="field-label">Người ghi biên bản</span>
              <br />
              {memberName(selected.scribe_id)}
            </p>
          </div>
          {selected.metrics && (
            <div className="grid gap-3 text-sm sm:grid-cols-4">
              <p>
                <span className="field-label">Tổng phát hiện</span>
                <br />
                {selected.metrics.finding_count || 0}
              </p>
              <p>
                <span className="field-label">Phát hiện nghiêm trọng</span>
                <br />
                {selected.metrics.major_count || 0}
              </p>
              <p>
                <span className="field-label">Chưa xử lý</span>
                <br />
                {selected.metrics.open_count || 0}
              </p>
              <p>
                <span className="field-label">Đã xác minh</span>
                <br />
                {selected.metrics.verified_count || 0}
              </p>
            </div>
          )}
          <ReviewChecklist items={selected.checklist} />
          <ReviewFindingsTable
            findings={selected.findings}
            canAssign={() => !readOnly && can("reviewsession.finding.manage")}
            canResolve={(item) =>
              !readOnly &&
              can("reviewsession.finding.manage") &&
              (memberRoles.includes("QA") || item.owner_id === userId)
            }
            canVerify={(item) =>
              !readOnly &&
              can("reviewsession.finding.manage") &&
              (selected.moderator_id === userId ||
                (selected.reviewer_ids || selected.reviewers || []).includes(userId)) &&
              item.resolved_by !== userId
            }
            onAssign={assignFinding}
            onResolve={resolveFinding}
            onVerify={verifyFinding}
          />
        </div>
      )}
    </Panel>
  );
}
