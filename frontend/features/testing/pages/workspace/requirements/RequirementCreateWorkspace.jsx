import DocumentEditor from "../../../editor/DocumentEditor";
import { ErrorState } from "../../../components/WorkspacePrimitives";
import RequirementLines from "./RequirementLines";

export default function RequirementCreateWorkspace({
  error,
  form,
  setForm,
  customFields,
  onSubmit,
}) {
  const updateForm = (patch) => setForm((value) => ({ ...value, ...patch }));
  const applicableFields = customFields.filter(
    (field) =>
      field.required &&
      (!field.requirement_types?.length || field.requirement_types.includes(form.type)),
  );

  return (
    <div className="min-w-0">
      {error && (
        <div className="mb-5">
          <ErrorState message={error} />
        </div>
      )}
      <form
        id="requirement-create-form"
        className="grid min-w-0 gap-6 lg:grid-cols-[minmax(0,1fr)_18rem]"
        onSubmit={onSubmit}
      >
        <div className="min-w-0 space-y-8">
          <section aria-labelledby="requirement-content-heading" className="min-w-0 space-y-5">
            <div>
              <h2 id="requirement-content-heading" className="text-[18px] font-semibold">
                Nội dung yêu cầu
              </h2>
              <p className="mt-1 text-[13px] text-ink-muted">
                Mô tả yêu cầu và nội dung cần dùng làm căn cứ kiểm thử.
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
            <div className="min-w-0">
              <p className="field-label mb-2">
                Mô tả chi tiết <span className="text-danger">*</span>
              </p>
              <DocumentEditor
                value={form.content_doc}
                onChange={(content_doc) => updateForm({ content_doc })}
                label="Mô tả chi tiết"
              />
            </div>
          </section>
          <section aria-labelledby="requirement-acceptance-heading" className="space-y-4">
            <div>
              <h2 id="requirement-acceptance-heading" className="text-[18px] font-semibold">
                Tiêu chí chấp nhận
              </h2>
              <p className="mt-1 text-[13px] text-ink-muted">
                Ghi rõ điều kiện để xác nhận yêu cầu được đáp ứng.
              </p>
            </div>
            <RequirementLines
              label="Tiêu chí chấp nhận"
              value={form.acceptance}
              onChange={(acceptance) => updateForm({ acceptance })}
            />
          </section>
          <section aria-labelledby="requirement-rules-heading" className="space-y-4">
            <div>
              <h2 id="requirement-rules-heading" className="text-[18px] font-semibold">
                Quy tắc nghiệp vụ
              </h2>
              <p className="mt-1 text-[13px] text-ink-muted">
                Bổ sung các quy tắc áp dụng cho yêu cầu này.
              </p>
            </div>
            <RequirementLines
              label="Quy tắc nghiệp vụ"
              value={form.businessRules}
              onChange={(businessRules) => updateForm({ businessRules })}
            />
          </section>
        </div>
        <aside className="min-w-0 space-y-5 lg:sticky lg:top-4 lg:self-start">
          <nav aria-label="Mục trong biểu mẫu yêu cầu" className="border-y border-border py-2">
            <a
              className="block rounded-control px-3 py-2 text-[13px] font-medium hover:bg-surface-quiet"
              href="#requirement-content-heading"
            >
              Nội dung yêu cầu
            </a>
            <a
              className="block rounded-control px-3 py-2 text-[13px] font-medium hover:bg-surface-quiet"
              href="#requirement-acceptance-heading"
            >
              Tiêu chí chấp nhận
            </a>
            <a
              className="block rounded-control px-3 py-2 text-[13px] font-medium hover:bg-surface-quiet"
              href="#requirement-rules-heading"
            >
              Quy tắc nghiệp vụ
            </a>
            <a
              className="block rounded-control px-3 py-2 text-[13px] font-medium hover:bg-surface-quiet"
              href="#requirement-metadata-heading"
            >
              Thông tin bổ sung
            </a>
          </nav>
          <section
            aria-labelledby="requirement-metadata-heading"
            className="min-w-0 space-y-4 border-y border-border py-4"
          >
            <div>
              <h2 id="requirement-metadata-heading" className="font-semibold">
                Thông tin bổ sung
              </h2>
              <p className="mt-1 text-[12px] text-ink-muted">
                Các trường này không thay thế nội dung yêu cầu.
              </p>
            </div>
            <label className="field-label block">
              Liên kết thiết kế hoặc tài liệu
              <input
                className="apple-input mt-2 w-full"
                value={form.designReference}
                onChange={(event) => updateForm({ designReference: event.target.value })}
                placeholder="Dán liên kết liên quan"
              />
            </label>
            <details className="border-t border-border pt-3">
              <summary className="cursor-pointer text-[13px] font-medium">
                Ưu tiên và tiến độ
              </summary>
              <div className="mt-3 grid gap-3">
                <label className="field-label">
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
                <label className="field-label">
                  Trạng thái theo dõi
                  <select
                    className="apple-input mt-2 w-full"
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
            {applicableFields.map((field) => (
              <label className="field-label block border-t border-border pt-4" key={field.key}>
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
          </section>
        </aside>
      </form>
    </div>
  );
}
