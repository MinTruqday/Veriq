import DocumentEditor from "../../../editor/DocumentEditor";
import { ErrorState } from "../../../components/WorkspacePrimitives";
import RequirementLines from "./RequirementLines";

export default function RequirementCreateModal({ error, form, setForm, customFields, onSubmit }) {
  const updateForm = (patch) => setForm((value) => ({ ...value, ...patch }));

  return (
    <div className="rounded-control border border-border bg-surface">
      {error && (
        <div className="px-5 pt-4">
          <ErrorState message={error} />
        </div>
      )}
      <form id="requirement-create-form" className="space-y-4 p-5" onSubmit={onSubmit}>
        <label className="field-label">
          Tên <span className="text-danger">*</span>
          <input
            className="apple-input mt-2"
            required
            minLength={2}
            value={form.title}
            onChange={(event) => updateForm({ title: event.target.value })}
          />
        </label>
        <div>
          <p className="field-label mb-2">
            Nội dung yêu cầu <span className="text-danger">*</span>
          </p>
          <DocumentEditor
            value={form.content_doc}
            onChange={(content_doc) => updateForm({ content_doc })}
            label="Nội dung yêu cầu"
          />
        </div>
        <RequirementLines
          label="Tiêu chí chấp nhận"
          value={form.acceptance}
          onChange={(acceptance) => updateForm({ acceptance })}
        />
        <RequirementLines
          label="Quy tắc nghiệp vụ"
          value={form.businessRules}
          onChange={(businessRules) => updateForm({ businessRules })}
        />
        <label className="field-label">
          Liên kết thiết kế hoặc tài liệu
          <input
            className="apple-input mt-2"
            value={form.designReference}
            onChange={(event) => updateForm({ designReference: event.target.value })}
            placeholder="Dán liên kết liên quan"
          />
        </label>
        <details className="rounded-control border border-border p-4">
          <summary className="cursor-pointer font-medium">Tùy chọn</summary>
          <div className="mt-3 grid gap-3 sm:grid-cols-2">
            <label className="field-label">
              Ưu tiên
              <select
                className="apple-input mt-2"
                value={form.priority}
                onChange={(event) => updateForm({ priority: event.target.value })}
              >
                <option value="">-</option>
                <option value="HIGH">Cao</option>
                <option value="MEDIUM">Trung bình</option>
                <option value="LOW">Thấp</option>
              </select>
            </label>
            <label className="field-label">
              Trạng thái theo dõi
              <select
                className="apple-input mt-2"
                value={form.progressStatus}
                onChange={(event) => updateForm({ progressStatus: event.target.value })}
              >
                <option value="">-</option>
                <option value="DRAFT">Bản nháp</option>
                <option value="APPROVED">Đã phê duyệt</option>
                <option value="IN_DEV">Đang phát triển</option>
                <option value="DONE">Hoàn thành</option>
              </select>
            </label>
          </div>
        </details>
        {customFields
          .filter(
            (field) =>
              field.required &&
              (!field.requirement_types?.length || field.requirement_types.includes(form.type)),
          )
          .map((field) => (
            <label className="field-label block" key={field.key}>
              {field.label} (bắt buộc theo cấu hình dự án)
              {field.value_type === "choice" ? (
                <select
                  className="apple-input mt-2"
                  required
                  value={form.customValues?.[field.key] || ""}
                  onChange={(event) =>
                    updateForm({
                      customValues: { ...form.customValues, [field.key]: event.target.value },
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
                  checked={Boolean(form.customValues?.[field.key])}
                  onChange={(event) =>
                    updateForm({
                      customValues: { ...form.customValues, [field.key]: event.target.checked },
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
      </form>
    </div>
  );
}
