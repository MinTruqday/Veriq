import DocumentEditor from "../../../editor/DocumentEditor";
import { valueLabel } from "../../../lib/testing";
import { ErrorState } from "../../../components/WorkspacePrimitives";
import { Modal, ModalHeader, ModalTitle } from "@/shared/components/ui/Modal";
import { REQUIREMENT_LEVELS, REQUIREMENT_TYPES } from "./requirements.model";

export default function RequirementCreateModal({
  isOpen,
  onClose,
  error,
  form,
  setForm,
  members,
  customFields,
  saving,
  onSubmit,
}) {
  const updateForm = (patch) => setForm((value) => ({ ...value, ...patch }));

  return (
    <Modal
      isOpen={isOpen}
      onClose={() => {
        if (!saving) onClose();
      }}
      ariaLabel="Tạo yêu cầu"
      className="max-w-3xl max-h-[90dvh] overflow-y-auto"
    >
      <ModalHeader>
        <ModalTitle>Tạo yêu cầu</ModalTitle>
      </ModalHeader>
      {error && (
        <div className="px-5 pt-4">
          <ErrorState message={error} />
        </div>
      )}
      <form className="space-y-4 p-5" onSubmit={onSubmit}>
        <label className="field-label">
          Tên
          <input
            className="apple-input mt-2"
            required
            minLength={2}
            value={form.title}
            onChange={(event) => updateForm({ title: event.target.value })}
          />
        </label>
        <div className="grid gap-3 sm:grid-cols-3">
          <label className="field-label">
            Loại
            <select
              className="apple-input mt-2"
              value={form.type}
              onChange={(event) => updateForm({ type: event.target.value })}
            >
              {REQUIREMENT_TYPES.map((value) => (
                <option key={value} value={value}>
                  {valueLabel(value)}
                </option>
              ))}
            </select>
          </label>
          <label className="field-label">
            Ưu tiên
            <select
              className="apple-input mt-2"
              value={form.priority}
              onChange={(event) => updateForm({ priority: event.target.value })}
            >
              {REQUIREMENT_LEVELS.map((value) => (
                <option key={value} value={value}>
                  {valueLabel(value)}
                </option>
              ))}
            </select>
          </label>
          <label className="field-label">
            Rủi ro
            <select
              className="apple-input mt-2"
              value={form.risk}
              onChange={(event) => updateForm({ risk: event.target.value })}
            >
              {REQUIREMENT_LEVELS.map((value) => (
                <option key={value} value={value}>
                  {valueLabel(value)}
                </option>
              ))}
            </select>
          </label>
        </div>
        <div>
          <p className="field-label mb-2">Nội dung yêu cầu</p>
          <DocumentEditor
            value={form.content_doc}
            onChange={(content_doc) => updateForm({ content_doc })}
            label="Nội dung yêu cầu"
          />
        </div>
        <label className="field-label">
          Tiêu chí chấp nhận (mỗi dòng một điều kiện)
          <textarea
            className="apple-input mt-2 min-h-28"
            value={form.acceptance}
            onChange={(event) => updateForm({ acceptance: event.target.value })}
          />
        </label>
        <label className="field-label">
          Quy tắc nghiệp vụ (mỗi dòng một quy tắc)
          <textarea
            className="apple-input mt-2 min-h-24"
            value={form.businessRules}
            onChange={(event) => updateForm({ businessRules: event.target.value })}
          />
        </label>
        <label className="field-label">
          Tác nhân (phân cách bằng dấu phẩy)
          <input
            className="apple-input mt-2"
            value={form.actors}
            onChange={(event) => updateForm({ actors: event.target.value })}
          />
        </label>
        <label className="field-label">
          Yêu cầu phụ thuộc (mỗi dòng một mục)
          <textarea
            className="apple-input mt-2 min-h-20"
            value={form.dependencies}
            onChange={(event) => updateForm({ dependencies: event.target.value })}
          />
        </label>
        <div className="grid gap-3 sm:grid-cols-2">
          <label className="field-label">
            Nhãn (phân cách bằng dấu phẩy)
            <input
              className="apple-input mt-2"
              value={form.tags}
              onChange={(event) => updateForm({ tags: event.target.value })}
            />
          </label>
          <label className="field-label">
            Người phụ trách
            <select
              className="apple-input mt-2"
              value={form.ownerId}
              onChange={(event) => updateForm({ ownerId: event.target.value })}
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
          </label>
        </div>
        {customFields
          .filter(
            (field) =>
              !field.requirement_types?.length || field.requirement_types.includes(form.type),
          )
          .map((field) => (
            <label className="field-label block" key={field.key}>
              {field.label}
              {field.value_type === "boolean" ? (
                <input
                  className="ml-2"
                  type="checkbox"
                  checked={Boolean(form.customValues?.[field.key])}
                  onChange={(event) =>
                    updateForm({
                      customValues: { ...form.customValues, [field.key]: event.target.checked },
                    })
                  }
                />
              ) : field.value_type === "choice" ? (
                <select
                  className="apple-input mt-2"
                  required={field.required}
                  value={form.customValues?.[field.key] || ""}
                  onChange={(event) =>
                    updateForm({
                      customValues: { ...form.customValues, [field.key]: event.target.value },
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
                  required={field.required}
                  type={
                    field.value_type === "number"
                      ? "number"
                      : field.value_type === "date"
                        ? "date"
                        : "text"
                  }
                  value={form.customValues?.[field.key] ?? ""}
                  onChange={(event) =>
                    updateForm({
                      customValues: {
                        ...form.customValues,
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
        <div className="action-dialog-footer flex justify-end gap-3">
          <button className="secondary-button" type="button" disabled={saving} onClick={onClose}>
            Hủy
          </button>
          <button className="apple-button" type="submit" disabled={saving}>
            {saving ? "Đang lưu" : "Lưu yêu cầu"}
          </button>
        </div>
      </form>
    </Modal>
  );
}
