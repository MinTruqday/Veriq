import DocumentEditor from "../../../editor/DocumentEditor";
import { ErrorState } from "../../../components/WorkspacePrimitives";
import RequirementLines from "./RequirementLines";

export default function RequirementCreateModal({ error, form, setForm, customFields, onSubmit }) {
  const updateForm = (patch) => setForm((value) => ({ ...value, ...patch }));
  const requiredCustomFields = customFields.filter(
    (field) =>
      field.required &&
      (!field.requirement_types?.length || field.requirement_types.includes(form.type)),
  );

  return (
    <div className="rounded-control border border-border bg-surface">
      {error && (
        <div className="px-5 pt-4">
          <ErrorState message={error} />
        </div>
      )}
      <form id="requirement-create-form" className="space-y-6 p-5" onSubmit={onSubmit}>
        <section aria-labelledby="requirement-create-content" className="space-y-4">
          <div>
            <h2 id="requirement-create-content" className="text-sm font-semibold text-ink">
              Thông tin yêu cầu
            </h2>
            <p className="mt-1 text-xs text-ink-muted">
              Tên và nội dung là căn cứ để liên kết tiêu chí, ca kiểm thử và nguồn tài liệu.
            </p>
          </div>
          <label className="field-label block">
            Tên <span className="text-danger">*</span>
            <input
              className="apple-input mt-2 w-full"
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
        </section>

        <section
          aria-labelledby="requirement-create-acceptance"
          className="space-y-4 border-t border-border pt-5"
        >
          <div>
            <h2 id="requirement-create-acceptance" className="text-sm font-semibold text-ink">
              Tiêu chí và quy tắc
            </h2>
            <p className="mt-1 text-xs text-ink-muted">
              Tách điều kiện nghiệm thu và quy tắc nghiệp vụ thành từng dòng để dễ truy vết.
            </p>
          </div>
          <RequirementLines
            label="Tiêu chí chấp nhận (tùy chọn)"
            value={form.acceptance}
            onChange={(acceptance) => updateForm({ acceptance })}
          />
          <RequirementLines
            label="Quy tắc nghiệp vụ (tùy chọn)"
            value={form.businessRules}
            onChange={(businessRules) => updateForm({ businessRules })}
          />
        </section>

        <details className="rounded-control border border-border">
          <summary className="cursor-pointer px-4 py-3 text-[13px] font-semibold text-ink hover:bg-surface-quiet focus-visible:outline focus-visible:outline-2 focus-visible:outline-brand">
            Trường tùy chọn
          </summary>
          <div className="grid gap-4 border-t border-border p-4 sm:grid-cols-2">
            <label className="field-label block">
              Ưu tiên
              <select
                className="apple-input mt-2 w-full"
                value={form.priority}
                onChange={(event) => updateForm({ priority: event.target.value })}
              >
                <option value="">-</option>
                <option value="HIGH">Cao</option>
                <option value="MEDIUM">Trung bình</option>
                <option value="LOW">Thấp</option>
              </select>
            </label>
            <label className="field-label block sm:col-span-2">
              Liên kết thiết kế hoặc tài liệu (tùy chọn)
              <input
                className="apple-input mt-2 w-full"
                value={form.designReference}
                onChange={(event) => updateForm({ designReference: event.target.value })}
              />
            </label>
          </div>
        </details>

        {requiredCustomFields.length > 0 && (
          <fieldset className="space-y-4 border-t border-border pt-5">
            <legend className="px-1 text-sm font-semibold text-ink">
              Trường bắt buộc theo cấu hình dự án
            </legend>
            <div className="grid gap-4 sm:grid-cols-2">
              {requiredCustomFields.map((field) => (
                <label className="field-label block min-w-0" key={field.key}>
                  {field.label} <span className="text-danger">*</span>
                  {field.value_type === "choice" ? (
                    <select
                      className="apple-input mt-2 w-full"
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
                    <span className="mt-2 flex min-h-10 items-center gap-2">
                      <input
                        type="checkbox"
                        checked={Boolean(form.customValues?.[field.key])}
                        onChange={(event) =>
                          updateForm({
                            customValues: {
                              ...form.customValues,
                              [field.key]: event.target.checked,
                            },
                          })
                        }
                      />
                      <span className="text-xs font-normal text-ink-muted">Đã xác nhận</span>
                    </span>
                  ) : (
                    <input
                      className="apple-input mt-2 w-full"
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
            </div>
          </fieldset>
        )}
      </form>
    </div>
  );
}
