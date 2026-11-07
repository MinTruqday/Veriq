import { useEffect } from "react";
import { Panel, StatusPill } from "../../../components/WorkspacePrimitives";
import Link from "next/link";
import DocumentEditor from "../../../editor/DocumentEditor";
import { messageOf, valueLabel } from "../../../lib/testing";
import { testingApi } from "../../../services/testing.service";
import { REQUIREMENT_LEVELS, REQUIREMENT_TYPES } from "./requirements.model";

export default function RequirementCurrentVersionPanel({
  projectId,
  current,
  selected,
  focusAcceptanceCriterionId,
  draft,
  members,
  customFields,
  saveState,
  can,
  checkingWithAi,
  onCheckWithAI,
  onOpenClarifications,
  saveDraft,
  onCreateVersion,
  onSplit,
  ask,
  reload,
  onDraftChange,
}) {
  useEffect(() => {
    if (!focusAcceptanceCriterionId || !current?._id) return;
    document
      .getElementById(`acceptance-criterion-${focusAcceptanceCriterionId}`)
      ?.scrollIntoView({ behavior: "smooth", block: "center" });
  }, [current?._id, focusAcceptanceCriterionId]);

  const submitReview = async () => {
    await ask({
      title: "Gửi yêu cầu đi rà soát",
      description: `${selected.requirement_key} sẽ được chuyển sang người rà soát. Bản nháp sẽ được lưu trước khi gửi.`,
      confirmLabel: "Gửi rà soát",
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
          {current.status === "BASELINED" && can("testplan.create") && (
            <Link
              className="secondary-button"
              href={`/du-an/${projectId}/ke-hoach-kiem-thu?requirementVersionId=${encodeURIComponent(current._id)}`}
            >
              Lập kế hoạch kiểm thử
            </Link>
          )}
          {can("ai.run_lint") && (
            <button
              className="secondary-button"
              aria-busy={checkingWithAi}
              disabled={checkingWithAi}
              type="button"
              onClick={onCheckWithAI}
            >
              {checkingWithAi ? "Đang kiểm tra…" : "Kiểm tra AI"}
            </button>
          )}
          {current.status === "IN_REVIEW" &&
            can("requirement.review") &&
            current.technical_review_revision !== current.revision && (
              <button
                className="secondary-button"
                type="button"
                onClick={() =>
                  ask({
                    title: "Ghi nhận rà soát Requirement",
                    description:
                      "Ghi nhận kết quả rà soát cho phiên bản này. Đây là bước riêng; thao tác này chưa chốt Requirement làm chuẩn.",
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
          {current.status === "IN_REVIEW" && can("requirement.review") && (
            <button
              className="secondary-button"
              type="button"
              onClick={() =>
                ask({
                  title: "Yêu cầu chỉnh sửa",
                  description:
                    "Phiên bản sẽ trở về bản nháp để người phụ trách cập nhật nội dung. Ghi rõ điểm cần sửa; có thể kèm Phiếu làm rõ riêng.",
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
                    "Yêu cầu sẽ trở về bản nháp. Sau khi cập nhật, cần gửi rà soát lại trước khi chốt chuẩn.",
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
          {current.status === "IN_REVIEW" && can("requirement.approve") && (
            <button
              className="apple-button"
              type="button"
              onClick={async () => {
                await ask({
                  title: "Chấp nhận Requirement",
                  description: `${selected.requirement_key} sẽ trở thành phiên bản chuẩn để các bước kiểm thử sử dụng. Cảnh báo nhẹ không chặn thao tác; lỗi rà soát cần được xử lý qua Phiếu làm rõ trước.`,
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
                      const detail = value?.response?.data?.detail || value?.detail;
                      if (detail?.code === "REQUIREMENT_LINT_BLOCKED") {
                        await testingApi.createClarificationsFromReview(current._id);
                        onOpenClarifications?.();
                        throw new Error(
                          "Đã tạo Phiếu làm rõ cho các lỗi cần xử lý và mở danh sách phiếu. Cảnh báo nhẹ không chặn chấp nhận.",
                        );
                      }
                      throw new Error(messageOf(value));
                    }
                  },
                });
              }}
            >
              Rà soát và chấp nhận
            </button>
          )}
          {current.status === "BASELINED" && can("requirement.version.create") && (
            <button className="secondary-button" type="button" onClick={onCreateVersion}>
              Tạo bản nháp để chỉnh sửa
            </button>
          )}
          {current.status === "BASELINED" && can("requirement.split") && (
            <button className="secondary-button" type="button" onClick={onSplit}>
              Tách yêu cầu
            </button>
          )}
          {current.status !== "OBSOLETE" && can("requirement.archive") && (
            <button
              className="secondary-button"
              type="button"
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
              Đánh dấu không còn hiệu lực
            </button>
          )}
          {current.status === "OBSOLETE" && can("requirement.restore") && (
            <button
              className="secondary-button"
              type="button"
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
              Khôi phục yêu cầu
            </button>
          )}
        </div>
      }
    >
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
                  id={`acceptance-criterion-${criterion._id}`}
                  key={criterion._id}
                  tabIndex={-1}
                >
                  <p className="text-xs font-medium text-ink-muted">
                    {criterion.key || "Tiêu chí chấp nhận"}
                  </p>
                  <p className="mt-1 text-sm">
                    {criterion.plain_text || "Không có nội dung văn bản để hiển thị."}
                  </p>
                </div>
              ))}
            {!(current?.acceptance_criteria || []).some(
              (criterion) => criterion._id === focusAcceptanceCriterionId,
            ) && (
              <p className="mt-2 text-sm text-ink-muted">
                Tiêu chí này không còn thuộc phiên bản yêu cầu đang mở. Hãy kiểm tra lại phiên bản
                nguồn.
              </p>
            )}
          </section>
        )}
        <div>
          <p className="field-label">Trạng thái</p>
          <div className="mt-2">
            <StatusPill value={current.status} />
          </div>
          {current.status === "IN_REVIEW" &&
            current.technical_review_revision === current.revision && (
              <p className="mt-2 text-sm text-ink-muted">Đã ghi nhận rà soát cho phiên bản này</p>
            )}
          {current.status === "IN_REVIEW" && (
            <p className="mt-2 max-w-prose text-sm text-ink-muted">
              Requirement đang chờ rà soát. Cảnh báo nhẹ có thể chấp nhận; lỗi chặn cần được đưa vào
              Phiếu làm rõ và xử lý trước khi chấp nhận.
            </p>
          )}
          {current.status === "DRAFT" &&
            current.changes_requested_by &&
            can("requirement.update") && (
              <p className="mt-2 max-w-prose text-sm text-ink-muted">
                Có yêu cầu chỉnh sửa. Hãy cập nhật bản nháp bên dưới rồi gửi rà soát lại.
              </p>
            )}
        </div>
        <div>
          <p className="field-label">Phiên bản</p>
          <p className="mt-2 font-semibold">v{current.version}</p>
        </div>
        <div>
          <p className="field-label">Rủi ro</p>
          <p className="mt-2 font-semibold">{valueLabel(current.risk)}</p>
        </div>
        {current.status === "DRAFT" && draft && can("requirement.update") ? (
          <div className="space-y-4 md:col-span-3">
            <input
              aria-label="Tên yêu cầu"
              className="apple-input"
              value={draft.title}
              onChange={(event) => onDraftChange({ title: event.target.value })}
            />
            <div className="grid gap-3 sm:grid-cols-3">
              <select
                aria-label="Loại yêu cầu"
                className="apple-input"
                value={draft.type}
                onChange={(event) => onDraftChange({ type: event.target.value })}
              >
                {REQUIREMENT_TYPES.map((value) => (
                  <option key={value} value={value}>
                    {valueLabel(value)}
                  </option>
                ))}
              </select>
              <select
                aria-label="Ưu tiên yêu cầu"
                className="apple-input"
                value={draft.priority}
                onChange={(event) => onDraftChange({ priority: event.target.value })}
              >
                {REQUIREMENT_LEVELS.map((value) => (
                  <option key={value} value={value}>
                    {valueLabel(value)}
                  </option>
                ))}
              </select>
              <select
                aria-label="Rủi ro yêu cầu"
                className="apple-input"
                value={draft.risk}
                onChange={(event) => onDraftChange({ risk: event.target.value })}
              >
                {REQUIREMENT_LEVELS.map((value) => (
                  <option key={value} value={value}>
                    {valueLabel(value)}
                  </option>
                ))}
              </select>
            </div>
            <div>
              <p className="field-label mb-2">Nội dung yêu cầu</p>
              <DocumentEditor
                value={draft.content_doc}
                onChange={(content_doc) => onDraftChange({ content_doc })}
                ignoreUnfocusedUpdates
                label="Nội dung yêu cầu"
              />
            </div>
            <label className="field-label grid gap-2">
              Tiêu chí chấp nhận
              <textarea
                aria-label="Tiêu chí chấp nhận"
                className="apple-input min-h-28"
                value={draft.acceptance}
                onChange={(event) => onDraftChange({ acceptance: event.target.value })}
                placeholder="Mỗi dòng nhập một tiêu chí"
              />
            </label>
            <div className="grid gap-3 lg:grid-cols-3">
              <textarea
                aria-label="Quy tắc nghiệp vụ"
                className="apple-input min-h-24"
                value={draft.businessRules}
                onChange={(event) => onDraftChange({ businessRules: event.target.value })}
                placeholder="Mỗi dòng nhập một quy tắc nghiệp vụ"
              />
              <textarea
                aria-label="Tác nhân"
                className="apple-input min-h-24"
                value={draft.actors}
                onChange={(event) => onDraftChange({ actors: event.target.value })}
                placeholder="Nhập các tác nhân, phân cách bằng dấu phẩy"
              />
              <textarea
                aria-label="Phụ thuộc yêu cầu"
                className="apple-input min-h-24"
                value={draft.dependencies}
                onChange={(event) => onDraftChange({ dependencies: event.target.value })}
                placeholder="Mỗi dòng nhập một yêu cầu phụ thuộc"
              />
            </div>
            <div className="grid gap-3 sm:grid-cols-2">
              <input
                aria-label="Nhãn yêu cầu"
                className="apple-input"
                value={draft.tags}
                onChange={(event) => onDraftChange({ tags: event.target.value })}
                placeholder="Nhập nhãn, phân cách bằng dấu phẩy"
              />
              <select
                aria-label="Người phụ trách yêu cầu"
                className="apple-input"
                value={draft.ownerId}
                onChange={(event) => onDraftChange({ ownerId: event.target.value })}
              >
                <option value="">Chưa phân công</option>
                {members.map((item) => (
                  <option key={item.user_id} value={item.user_id}>
                    {item.user_label ||
                      item.user?.full_name ||
                      item.user?.email ||
                      "Thành viên dự án"}
                  </option>
                ))}
              </select>
            </div>
            <details className="rounded-control border border-border p-3">
              <summary className="cursor-pointer text-sm font-medium">
                Thông tin theo loại yêu cầu
              </summary>
              <div className="mt-3 grid gap-3 md:grid-cols-2">
                {[
                  ["user_story.actor", "Tác nhân trong câu chuyện người dùng"],
                  ["user_story.goal", "Mục tiêu trong câu chuyện người dùng"],
                  ["user_story.value", "Giá trị trong câu chuyện người dùng"],
                  ["main_flow", "Luồng chính"],
                  ["exception_flow", "Luồng ngoại lệ"],
                  ["data_rules", "Dữ liệu và quy tắc"],
                  ["integration", "Giao diện hoặc tích hợp"],
                  ["quality_measure", "Thuộc tính chất lượng và mức đo"],
                ].map(([key, label]) => {
                  const [group, child] = key.split(".");
                  const value = child ? draft.details?.[group]?.[child] : draft.details?.[key];
                  return (
                    <div className="space-y-2" key={key}>
                      <label className="field-label block">
                        {label}
                        <textarea
                          className="apple-input mt-2"
                          rows={2}
                          value={value || ""}
                          onChange={(event) => {
                            const nested = child
                              ? { ...draft.details?.[group], [child]: event.target.value }
                              : null;
                            onDraftChange({
                              details: child
                                ? { ...draft.details, [group]: nested }
                                : { ...draft.details, [key]: event.target.value },
                              sectionStates: {
                                ...draft.sectionStates,
                                [key]: event.target.value.trim() ? "provided" : "missing",
                                ...(child
                                  ? {
                                      [group]: Object.values(nested).some((item) =>
                                        String(item).trim(),
                                      )
                                        ? "provided"
                                        : "missing",
                                    }
                                  : {}),
                              },
                            });
                          }}
                        />
                      </label>
                      <select
                        className="apple-input"
                        aria-label={`Trạng thái ${label}`}
                        value={draft.sectionStates?.[key] || ""}
                        onChange={(event) => {
                          const sectionStates = { ...draft.sectionStates };
                          if (event.target.value) sectionStates[key] = event.target.value;
                          else delete sectionStates[key];
                          onDraftChange({ sectionStates });
                        }}
                      >
                        <option value="">Chưa xác định</option>
                        <option value="provided">Đã có</option>
                        <option value="missing">Còn thiếu</option>
                        <option value="not_applicable">Không áp dụng</option>
                      </select>
                    </div>
                  );
                })}
                {customFields
                  .filter(
                    (field) =>
                      !field.requirement_types?.length ||
                      field.requirement_types.includes(draft.type),
                  )
                  .map((field) => (
                    <label className="field-label" key={field.key}>
                      {field.label}
                      {field.value_type === "boolean" ? (
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
                      ) : field.value_type === "choice" ? (
                        <select
                          className="apple-input mt-2"
                          value={draft.customValues?.[field.key] || ""}
                          onChange={(event) =>
                            onDraftChange({
                              customValues: {
                                ...draft.customValues,
                                [field.key]: event.target.value,
                              },
                            })
                          }
                        >
                          <option value="">Chưa chọn</option>
                          {field.choices.map((choice) => (
                            <option key={choice}>{choice}</option>
                          ))}
                        </select>
                      ) : (
                        <input
                          className="apple-input mt-2"
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
              </div>
            </details>
            <div className="flex flex-wrap items-center gap-3">
              <button className="secondary-button" type="button" onClick={saveDraft}>
                Lưu bản nháp
              </button>
              {current.status === "DRAFT" && can("requirement.submit_review") && (
                <button className="apple-button" type="button" onClick={submitReview}>
                  Gửi rà soát
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
            {(Object.keys(current.details || {}).length > 0 ||
              Object.keys(current.custom_values || {}).length > 0) && (
              <div className="mt-4 grid gap-3 md:grid-cols-2">
                {Object.entries(current.details || {}).map(([key, value]) => (
                  <div className="rounded-control border border-border p-3" key={key}>
                    <p className="field-label">{valueLabel(key)}</p>
                    <p className="mt-1 whitespace-pre-wrap text-sm">
                      {key === "api_operations" && Array.isArray(value)
                        ? value
                            .map(
                              (operation) =>
                                `${operation.method} ${operation.path || operation.url_template}`,
                            )
                            .join("  ")
                        : typeof value === "object"
                          ? Object.values(value).filter(Boolean).join("  ")
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
