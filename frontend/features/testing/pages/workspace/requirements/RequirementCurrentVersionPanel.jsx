import { Panel, StatusPill } from "../../../components/WorkspacePrimitives";
import DocumentEditor from "../../../editor/DocumentEditor";
import { messageOf, valueLabel } from "../../../lib/testing";
import { testingApi } from "../../../services/testing.service";
import { REQUIREMENT_LEVELS, REQUIREMENT_TYPES } from "./requirements.model";

export default function RequirementCurrentVersionPanel({
  current,
  selected,
  draft,
  members,
  customFields,
  saveState,
  can,
  onError,
  saveDraft,
  onCreateVersion,
  onSplit,
  ask,
  reload,
  onDraftChange,
}) {
  return (
    <Panel
      title="Phiên bản hiện tại"
      actions={
        <div className="flex flex-wrap gap-2">
          {current.status === "BASELINED" && can("requirement.version.create") && (
            <button className="secondary-button" type="button" onClick={onCreateVersion}>
              Tạo phiên bản mới
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
        <div>
          <p className="field-label">Trạng thái</p>
          <div className="mt-2">
            <StatusPill value={current.status} />
          </div>
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
                label="Nội dung yêu cầu"
              />
            </div>
            <textarea
              aria-label="Tiêu chí chấp nhận"
              className="apple-input min-h-28"
              value={draft.acceptance}
              onChange={(event) => onDraftChange({ acceptance: event.target.value })}
            />
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
                      "Tài khoản không xác định"}
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
            <button className="secondary-button" type="button" onClick={saveDraft}>
              Lưu bản nháp
            </button>
            <span className="ml-3 text-[12px] text-ink-muted" aria-live="polite">
              {saveState === "saving"
                ? "Đang tự động lưu"
                : saveState === "pending"
                  ? "Có thay đổi chưa lưu"
                  : saveState === "error"
                    ? "Tự động lưu thất bại"
                    : "Đã tự động lưu"}
            </span>
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
