import { TestDataEntries, TechniqueSelector, TestTypeSelector } from "./TestCaseOptions";
import { docText, valueLabel } from "../../../lib/testing";
import MultiSelect from "@/shared/components/ui/MultiSelect";
import RequirementCoverageSelector from "./RequirementCoverageSelector";
import { emptyDoc, textDoc } from "../../../lib/testing.logic.mjs";

function matchesConditionScope(condition, requirementIds, criterionIds) {
  if (!requirementIds.size && !criterionIds.size) return true;
  return (condition.basis_refs || []).some((reference) => {
    const sourceId = reference.artifact_version_id || reference.artifact_id;
    return (
      (reference.artifact_type === "REQUIREMENT_VERSION" && requirementIds.has(sourceId)) ||
      (reference.artifact_type === "ACCEPTANCE_CRITERION" && criterionIds.has(sourceId))
    );
  });
}

export default function TestCaseCreateForm({
  form,
  setForm,
  testConditions,
  requirements = [],
  members = [],
  canReadMembers = false,
  membersUnavailable = false,
  onRetryMembers,
  onSubmit,
  error = "",
  saving = false,
  onCancel,
  cancelLabel = "Hủy",
}) {
  const update = (patch) => setForm((value) => ({ ...value, ...patch }));
  const updateStep = (index, patch) =>
    setForm((current) => ({
      ...current,
      steps: current.steps.map((step, stepIndex) =>
        stepIndex === index ? { ...step, ...patch } : step,
      ),
    }));
  const selectedCriteria = requirements
    .filter((item) => form.requirementVersionIds.includes(item.current_version_id))
    .flatMap((item) =>
      (item.current_version?.acceptance_criteria || []).map((criterion) => ({
        ...criterion,
        requirement_key: item.requirement_key,
      })),
    );
  const requirementIds = new Set(form.requirementVersionIds || []);
  const selectedCriterionIds = new Set(form.acceptanceCriterionIds || []);
  const scopedCriterionIds = new Set(
    selectedCriterionIds.size
      ? selectedCriterionIds
      : selectedCriteria.map((criterion) => criterion._id),
  );
  const scopedTestConditions = testConditions.filter((condition) =>
    matchesConditionScope(condition, requirementIds, scopedCriterionIds),
  );
  const hasAnalysisLinks = form.requirementVersionIds.length > 0 || scopedTestConditions.length > 0;
  const testLevelOptions = [
    ["COMPONENT", "Thành phần"],
    ["COMPONENT_INTEGRATION", "Tích hợp thành phần"],
    ["SYSTEM", "Hệ thống"],
    ["SYSTEM_INTEGRATION", "Tích hợp hệ thống"],
    ["ACCEPTANCE", "Chấp nhận"],
  ];
  const priorityOptions = ["HIGH", "MEDIUM", "LOW"];
  const retainScopedConditionIds = (conditionIds, scopedRequirements, scopedCriteria) =>
    conditionIds.filter((conditionId) => {
      const condition = testConditions.find((item) => item._id === conditionId);
      return condition && matchesConditionScope(condition, scopedRequirements, scopedCriteria);
    });

  return (
    <form id="test-case-create-form" onSubmit={onSubmit} className="test-design-form space-y-6 p-5">
      <section aria-labelledby="test-case-basics-heading" className="space-y-4">
        <div>
          <h2 id="test-case-basics-heading" className="text-sm font-semibold text-ink">
            Thông tin ca kiểm thử
          </h2>
        </div>
        <div className="grid gap-4 sm:grid-cols-[minmax(0,1fr)_12rem]">
          <label className="field-label">
            Tên ca kiểm thử <span className="text-danger">*</span>
            <input
              className="apple-input mt-2"
              required
              minLength={2}
              value={form.title}
              onChange={(event) => update({ title: event.target.value })}
            />
          </label>
          <label className="field-label">
            Ước lượng (phút)
            <input
              aria-label="Ước lượng thời gian thực hiện ca kiểm thử (phút)"
              className="apple-input mt-2"
              type="number"
              min="1"
              max="10080"
              step="1"
              value={form.durationMinutes}
              onChange={(event) => update({ durationMinutes: event.target.value })}
            />
          </label>
        </div>
      </section>
      {form.testStyle !== "BDD" && (
        <section
          aria-labelledby="test-case-steps-heading"
          className="space-y-4 border-t border-border pt-5"
        >
          <div className="flex items-start justify-between gap-3">
            <div>
              <h3 id="test-case-steps-heading" className="text-sm font-semibold text-ink">
                Các bước kiểm thử
              </h3>
              <p className="mt-1 text-xs text-ink-muted">
                Mỗi bước gồm thao tác, dữ liệu thực hiện và kết quả mong đợi.
              </p>
            </div>
            <button
              className="icon-button h-9 w-9 shrink-0 text-lg"
              type="button"
              aria-label="Thêm bước"
              onClick={() =>
                update({
                  steps: [
                    ...form.steps,
                    {
                      id: crypto.randomUUID(),
                      action: emptyDoc(),
                      expected: emptyDoc(),
                      data: [],
                    },
                  ],
                })
              }
            >
              +
            </button>
          </div>
          {form.steps.map((step, index) => (
            <div className="space-y-3 rounded-control border border-border p-4" key={step.id}>
              <div className="flex items-center justify-between">
                <span className="font-medium">{index + 1}.</span>
                {form.steps.length > 1 && (
                  <button
                    className="icon-button h-9 w-9 text-lg"
                    type="button"
                    aria-label={`Xóa bước ${index + 1}`}
                    onClick={() =>
                      update({ steps: form.steps.filter((_, position) => position !== index) })
                    }
                  >
                    −
                  </button>
                )}
              </div>
              <label className="field-label">
                Thao tác <span className="text-danger">*</span>
                <textarea
                  className="apple-input mt-2 min-h-20"
                  required
                  value={docText(step.action)}
                  onChange={(event) => updateStep(index, { action: textDoc(event.target.value) })}
                />
              </label>
              <TestDataEntries
                label={`Dữ liệu bước ${index + 1}`}
                entries={step.data || []}
                onChange={(data) => updateStep(index, { data })}
              />
              <label className="field-label">
                Kết quả mong đợi <span className="text-danger">*</span>
                <textarea
                  className="apple-input mt-2 min-h-20"
                  required
                  value={docText(step.expected)}
                  onChange={(event) => updateStep(index, { expected: textDoc(event.target.value) })}
                />
              </label>
            </div>
          ))}
        </section>
      )}
      {form.testStyle === "BDD" && (
        <section
          aria-labelledby="test-case-bdd-heading"
          className="space-y-4 border-t border-border pt-5"
        >
          <div>
            <h3 id="test-case-bdd-heading" className="text-sm font-semibold text-ink">
              Kịch bản BDD
            </h3>
          </div>
          <div className="grid gap-4 sm:grid-cols-2">
            {[
              ["feature", "Tính năng"],
              ["scenario", "Tên kịch bản"],
              ["given", "Given · Điều kiện ban đầu"],
              ["when", "When · Hành động"],
              ["then", "Then · Kết quả mong đợi"],
            ].map(([field, label]) => (
              <label className="field-label" key={field}>
                {label} <span className="text-danger">*</span>
                <input
                  aria-label={label}
                  className="apple-input mt-2"
                  value={form[field]}
                  onChange={(event) => update({ [field]: event.target.value })}
                  required
                />
              </label>
            ))}
          </div>
        </section>
      )}
      <section
        aria-labelledby="test-case-requirements-heading"
        className="space-y-4 border-t border-border pt-5"
      >
        <h3 id="test-case-requirements-heading" className="text-sm font-semibold text-ink">
          Liên kết yêu cầu
        </h3>
        <p className="text-sm text-ink-muted">Chọn phiên bản yêu cầu mà ca này kiểm thử.</p>
        <MultiSelect
          showSearch={false}
          label={
            <span>
              Phiên bản yêu cầu liên quan <span className="text-danger">*</span>
            </span>
          }
          searchPlaceholder="Tìm yêu cầu"
          options={requirements.map((item) => ({
            value: item.current_version_id,
            label: `${item.requirement_key} · ${item.current_version?.title || "Không có tiêu đề"}`,
          }))}
          value={form.requirementVersionIds}
          onChange={(requirementVersionIds) => {
            const allowedCriteria = new Set(
              requirements
                .filter((item) => requirementVersionIds.includes(item.current_version_id))
                .flatMap((item) =>
                  (item.current_version?.acceptance_criteria || []).map(
                    (criterion) => criterion._id,
                  ),
                ),
            );
            const nextAcceptanceCriterionIds = form.acceptanceCriterionIds.filter((id) =>
              allowedCriteria.has(id),
            );
            const nextRequirementIds = new Set(requirementVersionIds);
            const nextCriterionIds = new Set(
              nextAcceptanceCriterionIds.length ? nextAcceptanceCriterionIds : [...allowedCriteria],
            );
            update({
              requirementVersionIds,
              acceptanceCriterionIds: nextAcceptanceCriterionIds,
              testConditionIds: retainScopedConditionIds(
                form.testConditionIds,
                nextRequirementIds,
                nextCriterionIds,
              ),
            });
          }}
        />
        {form.requirementVersionIds.length > 0 && (
          <MultiSelect
            showSearch={false}
            label="Tiêu chí chấp nhận được ca này kiểm thử"
            searchPlaceholder="Tìm tiêu chí chấp nhận"
            options={selectedCriteria.map((criterion) => ({
              value: criterion._id,
              label: `${criterion.requirement_key} · ${criterion.key || "Tiêu chí"}`,
              description: criterion.plain_text || docText(criterion.content_doc),
            }))}
            value={form.acceptanceCriterionIds}
            onChange={(acceptanceCriterionIds) =>
              update({
                acceptanceCriterionIds,
                testConditionIds: retainScopedConditionIds(
                  form.testConditionIds,
                  requirementIds,
                  new Set(
                    acceptanceCriterionIds.length
                      ? acceptanceCriterionIds
                      : selectedCriteria.map((criterion) => criterion._id),
                  ),
                ),
              })
            }
          />
        )}
      </section>
      <details className="rounded-control border border-border">
        <summary className="cursor-pointer px-4 py-3 text-[13px] font-semibold text-ink hover:bg-surface-quiet focus-visible:outline focus-visible:outline-2 focus-visible:outline-brand">
          Thông tin mở rộng
        </summary>
        <div
          className={`mt-4 grid min-w-0 items-start gap-4 ${
            hasAnalysisLinks ? "xl:grid-cols-[minmax(0,2fr)_minmax(0,1fr)]" : "grid-cols-1"
          }`}
        >
          <div className="min-w-0 space-y-4">
            {form.testStyle !== "BDD" && (
              <section className="space-y-3 rounded-control border border-border p-4">
                <h3 className="font-semibold">Luồng (tùy chọn)</h3>
                <label className="field-label block">
                  Luồng chính
                  <textarea
                    className="apple-input mt-2 min-h-20"
                    value={docText(form.mainFlow)}
                    placeholder="-"
                    onChange={(event) => update({ mainFlow: textDoc(event.target.value) })}
                  />
                </label>
                <fieldset className="space-y-3 rounded-control border border-border p-4">
                  <legend className="px-1 font-medium">Luồng thay thế và ngoại lệ</legend>
                  <div className="grid gap-4 md:grid-cols-2">
                    {[
                      ["alternateFlows", "Luồng thay thế"],
                      ["exceptionFlows", "Luồng ngoại lệ"],
                    ].map(([field, label]) => (
                      <label className="field-label" key={field}>
                        {label}
                        <textarea
                          className="apple-input mt-2 min-h-20"
                          value={docText(form[field])}
                          placeholder="-"
                          onChange={(event) => update({ [field]: textDoc(event.target.value) })}
                        />
                      </label>
                    ))}
                  </div>
                </fieldset>
              </section>
            )}
            <section className="space-y-3 rounded-control border border-border p-4">
              <h3 className="font-semibold">Thông tin chung</h3>
              <label className="field-label">
                Cách viết ca (tùy chọn)
                <select
                  aria-label="Cách viết ca kiểm thử"
                  className="apple-input mt-2"
                  value={form.testStyle}
                  onChange={(event) => update({ testStyle: event.target.value })}
                >
                  <option value="MANUAL">Thủ công</option>
                  <option value="BDD">BDD</option>
                </select>
              </label>
              <TestTypeSelector value={form.type} onChange={(type) => update({ type })} />
              <label className="field-label">
                Module / Tính năng
                <input
                  className="apple-input mt-2"
                  maxLength={300}
                  value={form.moduleName}
                  onChange={(event) => update({ moduleName: event.target.value })}
                />
              </label>
              <div className="space-y-3">
                <div className="mt-3 grid gap-3 sm:grid-cols-2">
                  <label className="field-label">
                    Ưu tiên
                    <select
                      aria-label="Ưu tiên ca kiểm thử"
                      className="apple-input mt-2"
                      value={form.priority || ""}
                      onChange={(event) => update({ priority: event.target.value })}
                    >
                      <option value="">-</option>
                      {form.priority && !priorityOptions.includes(form.priority) && (
                        <option value={form.priority}>{valueLabel(form.priority)}</option>
                      )}
                      {priorityOptions.map((value) => (
                        <option key={value} value={value}>
                          {valueLabel(value)}
                        </option>
                      ))}
                    </select>
                  </label>
                  <label className="field-label">
                    Cấp kiểm thử
                    <select
                      className="apple-input mt-2"
                      value={form.testLevel || ""}
                      onChange={(event) => update({ testLevel: event.target.value })}
                    >
                      <option value="">-</option>
                      {form.testLevel &&
                        !testLevelOptions.some(([value]) => value === form.testLevel) && (
                          <option value={form.testLevel}>{valueLabel(form.testLevel)}</option>
                        )}
                      {testLevelOptions.map(([value, label]) => (
                        <option key={value} value={value}>
                          {label}
                        </option>
                      ))}
                    </select>
                  </label>
                </div>
              </div>
              {canReadMembers && (
                <div>
                  <label className="field-label">
                    Người phụ trách ca kiểm thử
                    <select
                      aria-label="Người phụ trách ca kiểm thử"
                      className="apple-input mt-2"
                      value={form.ownerId || ""}
                      disabled={membersUnavailable}
                      onChange={(event) => update({ ownerId: event.target.value })}
                    >
                      <option value="">-</option>
                      {members
                        .filter((member) => member.status === "ACTIVE")
                        .map((member) => (
                          <option key={member.user_id} value={member.user_id}>
                            {member.user_label ||
                              member.user?.full_name ||
                              member.user?.email ||
                              "Thành viên dự án"}
                            {member.project_roles?.length
                              ? ` · ${member.project_roles.map(valueLabel).join(", ")}`
                              : member.project_role
                                ? ` · ${valueLabel(member.project_role)}`
                                : ""}
                          </option>
                        ))}
                    </select>
                  </label>
                  {membersUnavailable && (
                    <div className="mt-2 flex flex-wrap items-center gap-3 text-sm text-amber-800">
                      <span role="status">
                        Không tải được thành viên dự án nên chưa thể chọn người phụ trách.
                      </span>
                      {onRetryMembers && (
                        <button
                          type="button"
                          className="text-forest underline"
                          onClick={onRetryMembers}
                        >
                          Tải lại danh sách thành viên
                        </button>
                      )}
                    </div>
                  )}
                </div>
              )}
            </section>
            <section className="space-y-3 rounded-control border border-border p-4">
              <h3 className="font-semibold">Tiền điều kiện và hậu điều kiện</h3>
              <div className="grid gap-3 md:grid-cols-2">
                <label className="field-label">
                  Tiền điều kiện
                  <textarea
                    className="apple-input mt-2 min-h-20"
                    value={docText(form.preconditions)}
                    onChange={(event) => update({ preconditions: textDoc(event.target.value) })}
                  />
                </label>
                <label className="field-label">
                  Hậu điều kiện
                  <textarea
                    className="apple-input mt-2 min-h-20"
                    value={docText(form.postconditions)}
                    onChange={(event) => update({ postconditions: textDoc(event.target.value) })}
                  />
                </label>
              </div>
            </section>
            <div className="grid gap-3 sm:grid-cols-2">
              <TechniqueSelector
                value={form.techniques}
                onChange={(techniques) => update({ techniques })}
              />
              <label className="field-label">
                Nhãn (phân cách bằng dấu phẩy)
                <input
                  className="apple-input mt-2"
                  value={form.tags}
                  onChange={(event) => update({ tags: event.target.value })}
                />
              </label>
              <label className="field-label">
                Trạng thái tự động hóa
                <select
                  className="apple-input mt-2"
                  value={form.automationStatus}
                  onChange={(event) => update({ automationStatus: event.target.value })}
                >
                  <option value="manual">Thủ công</option>
                  <option value="candidate">Đề xuất tự động hóa</option>
                  <option value="automated">Đã tự động hóa</option>
                </select>
              </label>
            </div>
          </div>
          {hasAnalysisLinks && (
            <section className="min-w-0 space-y-4 rounded-control border border-border p-4">
              <h3 className="font-semibold">Liên kết phân tích</h3>
              {form.requirementVersionIds.length > 0 && (
                <RequirementCoverageSelector
                  requirements={requirements}
                  requirementVersionIds={form.requirementVersionIds}
                  value={form.coverageItemIds || []}
                  onChange={(coverageItemIds) => update({ coverageItemIds })}
                />
              )}
              {scopedTestConditions.length > 0 && (
                <MultiSelect
                  showSearch={false}
                  label="Điều kiện kiểm thử đã duyệt"
                  options={scopedTestConditions.map((item) => ({
                    value: item._id,
                    label: `${item.condition_key} ${item.title}`,
                  }))}
                  value={form.testConditionIds}
                  onChange={(testConditionIds) => update({ testConditionIds })}
                />
              )}
            </section>
          )}
        </div>
      </details>
      <footer className="action-dialog-footer sticky bottom-0 z-20 -mx-5 flex flex-wrap items-center justify-between gap-3 border-t border-border px-5 py-3">
        {error ? (
          <p className="min-w-0 flex-1 text-sm text-danger" role="alert">
            {error}
          </p>
        ) : (
          <p className="min-w-0 flex-1 text-xs text-ink-muted">
            Lưu nháp để tiếp tục hoàn thiện, hoặc lưu ca khi đã đủ thông tin bắt buộc.
          </p>
        )}
        <div className="ml-auto flex flex-wrap justify-end gap-2">
          <button className="secondary-button" disabled={saving} onClick={onCancel} type="button">
            {cancelLabel}
          </button>
          <button
            className="secondary-button"
            disabled={saving}
            formNoValidate
            type="submit"
            value="draft"
          >
            {saving ? "Đang lưu…" : "Lưu nháp"}
          </button>
          <button className="apple-button" disabled={saving} type="submit" value="ready">
            {saving ? "Đang lưu…" : "Lưu ca kiểm thử"}
          </button>
        </div>
      </footer>
    </form>
  );
}
