import { useEffect } from "react";
import { Archive, CalendarPlus, CheckCheck, FilePenLine, GitFork, RotateCcw } from "lucide-react";
import { Panel, StatusPill } from "../../../components/WorkspacePrimitives";
import Link from "next/link";
import DocumentEditor from "../../../editor/DocumentEditor";
import RequirementLines from "./RequirementLines";
import { messageOf, valueLabel } from "../../../lib/testing";
import { testingApi } from "../../../services/testing.service";
import { PROJECT_SECTION_SLUGS, projectRoute } from "../../../routes";

function numberedDocumentItems(items, prefix, getText) {
  return items
    .map((value, index) => {
      const text = getText(value);
      const match = String(text || "").match(new RegExp(`^\\s*${prefix}\\s*-\\s*(\\d+)`, "i"));
      return { value, index, sequence: match ? Number(match[1]) : null };
    })
    .sort((left, right) => {
      if (left.sequence === null && right.sequence !== null) return 1;
      if (right.sequence === null && left.sequence !== null) return -1;
      if (left.sequence !== null && right.sequence !== null && left.sequence !== right.sequence) {
        return left.sequence - right.sequence;
      }
      return left.index - right.index;
    });
}

function businessRuleContent(value) {
  return String(value || "")
    .replace(/^\s*[-–—•]\s*/, "")
    .replace(/^\s*BR\s*[-–—]\s*\d+\s*[-:.)]?\s*/i, "")
    .replace(/^\s*[-–—:.)]+\s*/, "");
}

function acceptanceCriterionContent(value) {
  return String(value || "")
    .replace(/^\s*[-–—•]\s*/, "")
    .replace(/^\s*AC\s*[-–—]\s*\d+\s*[-:.)]?\s*/i, "")
    .replace(/^\s*[-–—:.)]+\s*/, "");
}

function sourceLocationLabel(reference) {
  return reference.source_start !== undefined
    ? `Vị trí ${reference.source_start}–${reference.source_end}`
    : reference.candidate_index !== undefined
      ? `Mục ${reference.candidate_index + 1}`
      : "Không có vị trí cụ thể";
}

export default function RequirementCurrentVersionPanel({
  projectId,
  current,
  currentUserId,
  canSelfApprove = false,
  selected,
  sourceDocuments = [],
  onOpenTrace,
  focusAcceptanceCriterionId,
  draft,
  members = [],
  customFields,
  saveState,
  can,
  saveDraft,
  onCreateVersion,
  onSplit,
  ask,
  reload,
  onDraftChange,
  onError,
}) {
  const isAuthor = Boolean(
    currentUserId &&
      (current.created_by === currentUserId ||
        (current.content_author_ids || []).includes(currentUserId)),
  );
  const ownerId = draft?.ownerId || selected.owner_id || current.owner_id || "";
  const owner = members.find((member) => member.user_id === ownerId);
  const acceptanceCriteria = current.acceptance_criteria || [];
  const businessRules = current.business_rules || [];
  const orderedAcceptanceCriteria = numberedDocumentItems(
    acceptanceCriteria,
    "AC",
    (criterion) => criterion.key,
  );
  const orderedBusinessRules = numberedDocumentItems(businessRules, "BR", (rule) => rule);
  const sourceReferenceGroups = Array.from(
    (current.source_refs || []).reduce((groups, reference, index) => {
      const documentId = reference.requirement_document_id || `missing-${index}`;
      const group = groups.get(documentId) || { documentId, references: [] };
      group.references.push(reference);
      groups.set(documentId, group);
      return groups;
    }, new Map()),
    ([documentId, group]) => ({
      ...group,
      source: sourceDocuments.find((document) => document._id === documentId),
    }),
  );
  useEffect(() => {
    if (!focusAcceptanceCriterionId || !current?._id) return;
    document
      .getElementById(`acceptance-criterion-${focusAcceptanceCriterionId}`)
      ?.scrollIntoView({ behavior: "smooth", block: "center" });
  }, [current?._id, focusAcceptanceCriterionId]);

  const submitReview = async () => {
    const title = canSelfApprove ? "Chốt Requirement" : "Gửi yêu cầu đi rà soát";
    await ask({
      title,
      description: canSelfApprove
        ? `${selected.requirement_key} sẽ được kiểm tra điều kiện và chốt ngay`
        : `${selected.requirement_key} sẽ được chuyển sang người rà soát. Bản nháp sẽ được lưu trước khi gửi`,
      confirmLabel: canSelfApprove ? "Chốt Requirement" : "Gửi rà soát",
      fields: [
        {
          name: "review_note",
          label: "Ghi chú cho người rà soát",
          initialValue: "",
          multiline: true,
          autoFocus: true,
        },
      ],
      onConfirm: async (answer) => {
        try {
          const saved = await saveDraft();
          const savedVersion = saved?.current_version || current;
          await testingApi.submitRequirementReview(projectId, selected._id, {
            expected_revision: savedVersion.revision,
            review_note: answer.review_note.trim(),
          });
          await reload();
        } catch (value) {
          throw new Error(messageOf(value));
        }
      },
    });
  };

  return (
    <Panel
      title="Phiên bản hiện tại"
      actions={
        <div className="flex flex-wrap gap-2">
          {["READY", "BASELINED"].includes(current.status) && can("testplan.create") && (
            <Link
              className="icon-button h-9 w-9"
              aria-label="Lập kế hoạch kiểm thử"
              title="Lập kế hoạch kiểm thử"
              href={`/du-an/${projectId}/ke-hoach-kiem-thu?requirementVersionId=${encodeURIComponent(current._id)}`}
            >
              <CalendarPlus aria-hidden="true" size={16} />
            </Link>
          )}
          {current.status === "READY" && can("requirement.submit_review") && (
            <button className="secondary-button" type="button" onClick={submitReview}>
              {canSelfApprove ? "Chốt Requirement" : "Gửi rà soát"}
            </button>
          )}
          {current.status === "IN_REVIEW" &&
            (!isAuthor || canSelfApprove) &&
            can("requirement.review") &&
            current.technical_review_revision !== current.revision && (
              <button
                className="secondary-button"
                type="button"
                onClick={() =>
                  ask({
                    title: "Ghi nhận rà soát Requirement",
                    description:
                      "Ghi nhận kết quả rà soát cho phiên bản này. Đây là bước riêng; thao tác này chưa chốt Requirement làm chuẩn",
                    confirmLabel: "Ghi nhận rà soát",
                    fields: [
                      {
                        name: "review_note",
                        label: "Ghi chú rà soát",
                        initialValue: "",
                        multiline: true,
                        autoFocus: true,
                      },
                    ],
                    onConfirm: async (answer) => {
                      try {
                        await testingApi.reviewRequirementTechnically(current._id, {
                          expected_revision: current.revision,
                          review_note: answer.review_note.trim(),
                        });
                        await reload();
                      } catch (value) {
                        throw new Error(messageOf(value));
                      }
                    },
                  })
                }
              >
                Ghi nhận rà soát
              </button>
            )}
          {current.status === "IN_REVIEW" &&
            (!isAuthor || canSelfApprove) &&
            can("requirement.review") && (
              <button
                className="secondary-button"
                type="button"
                onClick={() =>
                  ask({
                    title: "Yêu cầu chỉnh sửa",
                    description:
                      "Phiên bản sẽ trở về bản nháp để người phụ trách cập nhật nội dung. Ghi rõ điểm cần sửa",
                    confirmLabel: "Trả về bản nháp",
                    fields: [
                      {
                        name: "review_note",
                        label: "Nội dung cần chỉnh sửa",
                        required: true,
                        minLength: 2,
                        multiline: true,
                        autoFocus: true,
                      },
                    ],
                    onConfirm: async (answer) => {
                      try {
                        await testingApi.requestRequirementChanges(projectId, selected._id, {
                          expected_revision: current.revision,
                          review_note: answer.review_note.trim(),
                        });
                        await reload();
                      } catch (value) {
                        const detail = value?.response?.data?.detail || value?.detail;
                        if (detail?.code === "REQUIREMENT_LINT_BLOCKED") {
                          throw new Error(
                            "Còn lỗi kiểm tra bắt buộc. Xem gợi ý hoàn thiện yêu cầu, sửa nội dung rồi gửi lại",
                          );
                        }
                        throw new Error(messageOf(value));
                      }
                    },
                  })
                }
              >
                Yêu cầu chỉnh sửa
              </button>
            )}
          {current.status === "IN_REVIEW" && can("requirement.update") && (
            <button
              className="secondary-button"
              type="button"
              onClick={() =>
                ask({
                  title: "Mở lại để chỉnh sửa",
                  description:
                    "Yêu cầu sẽ trở về bản nháp. Sau khi cập nhật, cần gửi rà soát lại trước khi chốt chuẩn",
                  confirmLabel: "Mở bản nháp",
                  fields: [
                    {
                      name: "review_note",
                      label: "Lý do chỉnh sửa",
                      required: true,
                      minLength: 2,
                      multiline: true,
                      autoFocus: true,
                    },
                  ],
                  onConfirm: async (answer) => {
                    try {
                      await testingApi.reopenRequirementForEditing(projectId, selected._id, {
                        expected_revision: current.revision,
                        review_note: answer.review_note.trim(),
                      });
                      await reload();
                    } catch (value) {
                      throw new Error(messageOf(value));
                    }
                  },
                })
              }
            >
              Mở lại để chỉnh sửa
            </button>
          )}
          {current.status === "IN_REVIEW" &&
            (!isAuthor || canSelfApprove) &&
            can("requirement.approve") && (
              <button
                className="icon-button h-9 w-9"
                type="button"
                aria-label="Rà soát và chấp nhận"
                title="Rà soát và chấp nhận"
                onClick={async () => {
                  await ask({
                    title: "Chấp nhận Requirement",
                    description: `${selected.requirement_key} sẽ trở thành phiên bản chuẩn để các bước kiểm thử sử dụng. Cảnh báo nhẹ không chặn thao tác; các lỗi bắt buộc cần được xử lý trong nội dung yêu cầu trước khi chấp nhận`,
                    confirmLabel: "Chấp nhận Requirement",
                    fields: [
                      {
                        name: "review_note",
                        label: "Ghi chú rà soát",
                        initialValue: "",
                        multiline: true,
                        autoFocus: true,
                      },
                    ],
                    onConfirm: async (answer) => {
                      try {
                        await testingApi.approveRequirement(projectId, selected._id, {
                          expected_revision: current.revision,
                          review_note: answer.review_note.trim(),
                        });
                        await reload();
                      } catch (value) {
                        throw new Error(messageOf(value));
                      }
                    },
                  });
                }}
              >
                <CheckCheck aria-hidden="true" size={16} />
              </button>
            )}
          {["BASELINED", "READY"].includes(current.status) && can("requirement.version.create") && (
            <button
              className="icon-button h-9 w-9"
              type="button"
              aria-label="Tạo bản nháp để chỉnh sửa"
              title="Tạo bản nháp để chỉnh sửa"
              onClick={onCreateVersion}
            >
              <FilePenLine aria-hidden="true" size={16} />
            </button>
          )}
          {current.status === "BASELINED" && can("requirement.split") && (
            <button
              className="icon-button h-9 w-9"
              type="button"
              aria-label="Tách yêu cầu"
              title="Tách yêu cầu"
              onClick={onSplit}
            >
              <GitFork aria-hidden="true" size={16} />
            </button>
          )}
          {current.status !== "OBSOLETE" && can("requirement.archive") && (
            <button
              className="icon-button h-9 w-9"
              type="button"
              aria-label="Đánh dấu yêu cầu không còn hiệu lực"
              title="Đánh dấu yêu cầu không còn hiệu lực"
              onClick={async () => {
                await ask({
                  title: "Đánh dấu yêu cầu không còn hiệu lực",
                  description: `${selected.requirement_key} vẫn được giữ trong lịch sử truy vết`,
                  confirmLabel: "Đánh dấu",
                  danger: true,
                  fields: [
                    {
                      name: "reason",
                      label: "Lý do",
                      initialValue: "Yêu cầu không còn thuộc phạm vi sản phẩm",
                      required: true,
                      multiline: true,
                      autoFocus: true,
                    },
                  ],
                  onConfirm: async (answer) => {
                    try {
                      await testingApi.obsoleteRequirement(selected._id, {
                        expected_current_version_id: selected.current_version_id,
                        reason: answer.reason,
                      });
                      await reload();
                    } catch (value) {
                      throw new Error(messageOf(value));
                    }
                  },
                });
              }}
            >
              <Archive aria-hidden="true" size={16} />
            </button>
          )}
          {current.status === "OBSOLETE" && can("requirement.restore") && (
            <button
              className="icon-button h-9 w-9"
              type="button"
              aria-label="Khôi phục yêu cầu"
              title="Khôi phục yêu cầu"
              onClick={async () => {
                await ask({
                  title: "Khôi phục yêu cầu",
                  description: `${selected.requirement_key} sẽ trở lại trạng thái trước khi bị đánh dấu không còn hiệu lực`,
                  confirmLabel: "Khôi phục",
                  fields: [
                    {
                      name: "reason",
                      label: "Lý do",
                      initialValue: "Yêu cầu tiếp tục thuộc phạm vi sản phẩm",
                      required: true,
                      multiline: true,
                      autoFocus: true,
                    },
                  ],
                  onConfirm: async (answer) => {
                    try {
                      await testingApi.restoreRequirement(selected._id, {
                        expected_current_version_id: selected.current_version_id,
                        reason: answer.reason,
                      });
                      await reload();
                    } catch (value) {
                      throw new Error(messageOf(value));
                    }
                  },
                });
              }}
            >
              <RotateCcw aria-hidden="true" size={16} />
            </button>
          )}
        </div>
      }
    >
      <div className="grid gap-4 border-b border-border bg-surface-quiet/40 p-4 sm:grid-cols-3">
        <div>
          <p className="field-label">Trạng thái</p>
          <div className="mt-1.5">
            {current.status === "READY" ? (
              <span className="text-sm">Đã lưu, chưa duyệt</span>
            ) : (
              <StatusPill value={current.status} />
            )}
          </div>
        </div>
        <div>
          <p className="field-label">Phiên bản</p>
          <p className="mt-1.5 text-sm font-semibold">v{current.version}</p>
        </div>
        {current.status === "DRAFT" && draft && can("requirement.update") ? (
          <label className="field-label grid gap-1.5">
            Người phụ trách
            <select
              aria-label="Người phụ trách yêu cầu"
              className="apple-input w-full"
              value={draft.ownerId || ""}
              onChange={(event) => onDraftChange({ ownerId: event.target.value })}
            >
              <option value="">Chưa phân công</option>
              {members.map((member) => (
                <option key={member.user_id} value={member.user_id}>
                  {member.user_label || member.user?.email || "Thành viên dự án"}
                </option>
              ))}
            </select>
          </label>
        ) : (
          <div>
            <p className="field-label">Người phụ trách</p>
            <p className="mt-1.5 text-sm">
              {owner?.user_label ||
                owner?.user?.email ||
                (ownerId ? "Thành viên dự án" : "Chưa phân công")}
            </p>
          </div>
        )}
      </div>
      <div className="grid gap-5 p-5 md:grid-cols-3">
        {focusAcceptanceCriterionId && (
          <section
            aria-label="Tiêu chí nguồn được trích dẫn"
            className="rounded-control border border-violet-300 bg-violet-50/60 p-4 md:col-span-3"
          >
            <h3 className="text-sm font-semibold">Tiêu chí nguồn được trích dẫn</h3>
            {(current?.acceptance_criteria || [])
              .filter((criterion) => criterion._id === focusAcceptanceCriterionId)
              .map((criterion) => (
                <div
                  className="mt-2 rounded-control border border-violet-300 bg-white p-3"
                  key={criterion._id}
                >
                  <p className="text-xs font-medium text-ink-muted">
                    {criterion.key || "Tiêu chí chấp nhận"}
                  </p>
                  <p className="mt-1 text-sm">
                    {criterion.plain_text || "Không có nội dung văn bản để hiển thị"}
                  </p>
                </div>
              ))}
            {!(current?.acceptance_criteria || []).some(
              (criterion) => criterion._id === focusAcceptanceCriterionId,
            ) && (
              <p className="mt-2 text-sm text-ink-muted">
                Tiêu chí này không còn thuộc phiên bản yêu cầu đang mở. Hãy kiểm tra lại phiên bản
                nguồn
              </p>
            )}
          </section>
        )}
        {!(current.status === "DRAFT" && draft && can("requirement.update")) && (
          <details className="rounded-control border border-border p-3 md:col-span-3">
            <summary className="cursor-pointer text-sm font-medium">Tùy chọn</summary>
            <div className="mt-3 grid gap-3 sm:grid-cols-2">
              <div>
                <p className="field-label">Ưu tiên</p>
                <p className="mt-1 font-semibold">{valueLabel(current.priority || "unassessed")}</p>
              </div>
            </div>
          </details>
        )}
        {current.status === "DRAFT" && draft && can("requirement.update") ? (
          <div className="space-y-4 md:col-span-3">
            <label className="grid gap-2 text-sm font-medium text-ink">
              Tên yêu cầu <span className="text-danger">*</span>
              <input
                aria-label="Tên yêu cầu"
                className="apple-input"
                value={draft.title}
                onChange={(event) => onDraftChange({ title: event.target.value })}
              />
            </label>
            <div>
              <p className="field-label mb-2">
                Nội dung yêu cầu <span className="text-danger">*</span>
              </p>
              <DocumentEditor
                value={draft.content_doc}
                onChange={(content_doc) => onDraftChange({ content_doc })}
                ignoreUnfocusedUpdates
                label="Nội dung yêu cầu"
              />
            </div>
            <RequirementLines
              label="Tiêu chí chấp nhận (tùy chọn)"
              identifierPrefix="AC"
              value={draft.acceptance}
              onChange={(acceptance) => onDraftChange({ acceptance })}
            />
            <RequirementLines
              label="Quy tắc nghiệp vụ (tùy chọn)"
              identifierPrefix="BR"
              value={draft.businessRules}
              onChange={(businessRules) => onDraftChange({ businessRules })}
            />
            <details className="rounded-control border border-border p-4">
              <summary className="cursor-pointer font-medium">Tùy chọn</summary>
              <div className="mt-3 grid gap-3">
                <label className="field-label">
                  Mức ưu tiên
                  <select
                    aria-label="Ưu tiên yêu cầu"
                    className="apple-input mt-2"
                    value={draft.priority || ""}
                    onChange={(event) => onDraftChange({ priority: event.target.value })}
                  >
                    <option value="">-</option>
                    <option value="HIGH">Cao</option>
                    <option value="MEDIUM">Trung bình</option>
                    <option value="LOW">Thấp</option>
                    {draft.priority && !["HIGH", "MEDIUM", "LOW"].includes(draft.priority) && (
                      <option value={draft.priority}>{valueLabel(draft.priority)}</option>
                    )}
                  </select>
                </label>
                <label className="field-label grid gap-2">
                  Liên kết thiết kế hoặc tài liệu (tùy chọn)
                  <input
                    className="apple-input"
                    value={draft.details?.design_reference || ""}
                    onChange={(event) =>
                      onDraftChange({
                        details: { ...draft.details, design_reference: event.target.value },
                      })
                    }
                  />
                </label>
              </div>
            </details>
            {customFields
              .filter(
                (field) =>
                  field.required &&
                  (!field.requirement_types?.length ||
                    field.requirement_types.includes(current.type)),
              )
              .map((field) => (
                <label className="field-label block" key={field.key}>
                  {field.label} <span className="text-danger">*</span>
                  {field.value_type === "choice" ? (
                    <select
                      className="apple-input mt-2"
                      required
                      value={draft.customValues?.[field.key] ?? ""}
                      onChange={(event) =>
                        onDraftChange({
                          customValues: {
                            ...draft.customValues,
                            [field.key]: event.target.value,
                          },
                        })
                      }
                    >
                      <option value="">-</option>
                      {field.choices.map((choice) => (
                        <option key={choice}>{choice}</option>
                      ))}
                    </select>
                  ) : field.value_type === "boolean" ? (
                    <input
                      className="ml-2"
                      type="checkbox"
                      checked={Boolean(draft.customValues?.[field.key])}
                      onChange={(event) =>
                        onDraftChange({
                          customValues: {
                            ...draft.customValues,
                            [field.key]: event.target.checked,
                          },
                        })
                      }
                    />
                  ) : (
                    <input
                      className="apple-input mt-2"
                      required
                      type={
                        field.value_type === "number"
                          ? "number"
                          : field.value_type === "date"
                            ? "date"
                            : "text"
                      }
                      value={draft.customValues?.[field.key] ?? ""}
                      onChange={(event) =>
                        onDraftChange({
                          customValues: {
                            ...draft.customValues,
                            [field.key]:
                              field.value_type === "number" && event.target.value !== ""
                                ? Number(event.target.value)
                                : event.target.value,
                          },
                        })
                      }
                    />
                  )}
                </label>
              ))}
            {current.parent_version_id && (
              <details className="rounded-control border border-border p-4">
                <summary className="cursor-pointer font-medium">
                  Thay đổi và ảnh hưởng (tùy chọn)
                </summary>
                <div className="mt-3 grid gap-4">
                  {[
                    ["change", "Nội dung thay đổi"],
                    ["impact", "Ảnh hưởng"],
                    ["time", "Ảnh hưởng đến thời gian"],
                  ].map(([key, label]) => (
                    <label className="field-label" key={key}>
                      {label}
                      <textarea
                        className="apple-input mt-2 min-h-20"
                        value={
                          draft.details?.change_impact?.[key] ??
                          (key === "change" ? current.change_reason || "" : "")
                        }
                        onChange={(event) =>
                          onDraftChange({
                            details: {
                              ...draft.details,
                              change_impact: {
                                ...draft.details?.change_impact,
                                [key]: event.target.value,
                              },
                            },
                          })
                        }
                      />
                    </label>
                  ))}
                </div>
              </details>
            )}
            <div className="flex flex-wrap items-center gap-3">
              <button className="secondary-button" type="button" onClick={saveDraft}>
                Lưu bản nháp
              </button>
              <button
                className="apple-button"
                type="button"
                onClick={async () => {
                  try {
                    const saved = await saveDraft();
                    await testingApi.saveRequirement(projectId, selected._id, {
                      expected_revision: (saved?.current_version || current).revision,
                    });
                    await reload();
                  } catch (reason) {
                    onError(messageOf(reason));
                  }
                }}
              >
                Lưu yêu cầu
              </button>
              {current.status === "DRAFT" && can("requirement.submit_review") && (
                <button className="apple-button" type="button" onClick={submitReview}>
                  {canSelfApprove ? "Chốt Requirement" : "Gửi rà soát"}
                </button>
              )}
              <span className="text-[12px] text-ink-muted" aria-live="polite">
                {saveState === "saving"
                  ? "Đang tự động lưu"
                  : saveState === "pending"
                    ? "Có thay đổi chưa lưu"
                    : saveState === "error"
                      ? "Tự động lưu thất bại"
                      : "Đã tự động lưu"}
              </span>
            </div>
          </div>
        ) : (
          <div className="md:col-span-3">
            <DocumentEditor
              value={current.content_doc}
              onChange={() => {}}
              label="Nội dung yêu cầu"
              readOnly
            />
            <div className="mt-5 grid gap-4 lg:grid-cols-2">
              <section
                className="rounded-control border border-border p-4"
                aria-label="Tiêu chí chấp nhận"
              >
                <h3 className="text-sm font-semibold">Tiêu chí chấp nhận</h3>
                {acceptanceCriteria.length ? (
                  <ol className="mt-3 space-y-2">
                    {orderedAcceptanceCriteria.map(({ value: criterion, index }) => (
                      <li
                        className="flex gap-3 rounded-control border border-border bg-surface p-3"
                        id={`acceptance-criterion-${criterion._id}`}
                        key={criterion._id || criterion.key || index}
                      >
                        <span className="shrink-0 font-mono text-xs font-semibold text-brand">
                          {criterion.key || `AC-${String(index + 1).padStart(2, "0")}`}
                        </span>
                        <span className="whitespace-pre-wrap text-sm">
                          {acceptanceCriterionContent(criterion.plain_text) ||
                            "Không có nội dung văn bản để hiển thị"}
                        </span>
                      </li>
                    ))}
                  </ol>
                ) : (
                  <p className="mt-2 text-sm text-ink-muted">Chưa có tiêu chí chấp nhận</p>
                )}
              </section>
              <section
                className="rounded-control border border-border p-4"
                aria-label="Quy tắc nghiệp vụ"
              >
                <h3 className="text-sm font-semibold">Quy tắc nghiệp vụ</h3>
                {businessRules.length ? (
                  <ol className="mt-3 space-y-2">
                    {orderedBusinessRules.map(({ value: rule, index, sequence }) => (
                      <li
                        className="flex gap-3 rounded-control border border-border bg-surface p-3"
                        key={`${index}-${rule}`}
                      >
                        <span className="shrink-0 font-mono text-xs font-semibold text-brand">
                          BR-{String(sequence ?? index + 1).padStart(2, "0")}
                        </span>
                        <span className="whitespace-pre-wrap text-sm">
                          {businessRuleContent(rule)}
                        </span>
                      </li>
                    ))}
                  </ol>
                ) : (
                  <p className="mt-2 text-sm text-ink-muted">Chưa có quy tắc nghiệp vụ</p>
                )}
              </section>
            </div>
            <section
              className="mt-4 rounded-control border border-border p-4"
              aria-label="Tài liệu nguồn"
            >
              <div className="flex flex-wrap items-start justify-between gap-3">
                <div>
                  <h3 className="text-sm font-semibold">Tài liệu nguồn</h3>
                  <p className="mt-1 text-xs text-ink-muted">
                    Nguồn trích dẫn đã lưu cùng phiên bản yêu cầu
                  </p>
                </div>
                {current.source_refs?.length > 0 && (
                  <button className="text-link text-xs" type="button" onClick={onOpenTrace}>
                    Xem chi tiết nguồn
                  </button>
                )}
              </div>
              {current.source_refs?.length ? (
                <ul className="mt-3 divide-y divide-border rounded-control border border-border">
                  {sourceReferenceGroups.map(({ documentId, references, source }) => {
                    const referenceGroupLabel = `${references.length} trích dẫn`;
                    return (
                      <li className="min-w-0 p-3" key={documentId}>
                        <div className="flex min-w-0 flex-wrap items-center justify-between gap-3">
                          <div className="min-w-0">
                            <p className="break-words text-sm font-medium">
                              {source?.title ||
                                source?.filename ||
                                "Tài liệu nguồn không còn khả dụng"}
                            </p>
                            <p className="mt-1 text-xs text-ink-muted">{referenceGroupLabel}</p>
                          </div>
                          {source?._id && (
                            <Link
                              className="secondary-button shrink-0"
                              href={projectRoute(
                                projectId,
                                PROJECT_SECTION_SLUGS.documentReader,
                                source._id,
                              )}
                            >
                              Mở tài liệu
                            </Link>
                          )}
                        </div>
                        <details className="mt-2">
                          <summary className="cursor-pointer text-xs font-medium text-ink-muted">
                            Xem vị trí trích dẫn
                          </summary>
                          <ul className="mt-2 grid gap-2 border-l border-border pl-3 text-xs text-ink-muted">
                            {references.map((reference, index) => (
                              <li className="break-words" key={`${documentId}-${index}`}>
                                {sourceLocationLabel(reference)}
                              </li>
                            ))}
                          </ul>
                        </details>
                      </li>
                    );
                  })}
                </ul>
              ) : (
                <p className="mt-3 rounded-control bg-surface-quiet/50 p-3 text-sm text-ink-muted">
                  Yêu cầu này chưa có tài liệu nguồn được liên kết
                </p>
              )}
            </section>
            {(Object.keys(current.details || {}).length > 0 ||
              Object.keys(current.custom_values || {}).length > 0) && (
              <div className="mt-4 grid gap-3 md:grid-cols-2">
                {Object.entries(current.details || {})
                  .filter(
                    ([key]) =>
                      !["actor", "actors", "progress_status", "change_impact"].includes(key),
                  )
                  .map(([key, value]) => (
                    <div className="rounded-control border border-border p-3" key={key}>
                      <p className="field-label">
                        {key === "design_reference"
                          ? "Liên kết thiết kế hoặc tài liệu"
                          : valueLabel(key)}
                      </p>
                      <p className="mt-1 whitespace-pre-wrap text-sm">
                        {key === "api_operations" && Array.isArray(value)
                          ? value
                              .map(
                                (operation) =>
                                  `${operation.method} ${operation.path || operation.url_template}`,
                              )
                              .join("  ")
                          : typeof value === "object"
                            ? Object.entries(value)
                                .filter(([child]) => child !== "actor")
                                .map(([, item]) => item)
                                .filter(Boolean)
                                .join("  ")
                            : value}
                      </p>
                    </div>
                  ))}
                {Object.entries(current.custom_values || {}).map(([key, value]) => (
                  <div className="rounded-control border border-border p-3" key={key}>
                    <p className="field-label">
                      {customFields.find((field) => field.key === key)?.label || key}
                    </p>
                    <p className="mt-1 text-sm">{String(value)}</p>
                  </div>
                ))}
              </div>
            )}
          </div>
        )}
      </div>
    </Panel>
  );
}
