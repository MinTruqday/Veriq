import DocumentEditor from "../../../editor/DocumentEditor";
import { Trash2 } from "lucide-react";
import { docText, valueLabel } from "../../../lib/testing";
import { Modal, ModalHeader, ModalTitle } from "@/shared/components/ui/Modal";
import MultiSelect from "@/shared/components/ui/MultiSelect";
import TestCaseCustomValues from "./TestCaseCustomValues";
import TestCaseOwnerRecommendation from "./TestCaseOwnerRecommendation";
import RequirementCoverageSelector from "./RequirementCoverageSelector";
import { emptyDoc } from "../../../lib/testing.logic.mjs";

function TestDataEntries({ label, entries, onChange }) {
  const updateEntry = (index, patch) =>
    onChange(
      entries.map((entry, entryIndex) => (entryIndex === index ? { ...entry, ...patch } : entry)),
    );
  return (
    <fieldset className="space-y-3 rounded-control border border-border p-3">
      <legend className="field-label px-1">{label}</legend>
      <button
        className="secondary-button"
        type="button"
        onClick={() => onChange([...entries, { id: crypto.randomUUID(), name: "", value: "" }])}
      >
        Thêm dòng dữ liệu
      </button>
      {entries.map((entry, index) => (
        <div
          className="grid gap-2 sm:grid-cols-[minmax(0,1fr)_minmax(0,1fr)_auto]"
          key={entry.id || index}
        >
          <input
            className="apple-input"
            aria-label={`${label}: tên trường ${index + 1}`}
            value={entry.name}
            onChange={(event) => updateEntry(index, { name: event.target.value })}
            placeholder="Tên trường"
          />
          <input
            className="apple-input"
            aria-label={`${label}: giá trị ${index + 1}`}
            value={entry.value}
            onChange={(event) => updateEntry(index, { value: event.target.value })}
            placeholder="Giá trị"
          />
          <div className="flex gap-2">
            {entries.length > 1 && (
              <button
                className="icon-button h-9 w-9 text-danger"
                type="button"
                aria-label={`Xóa dòng dữ liệu ${index + 1}`}
                title="Xóa dòng dữ liệu"
                onClick={() => onChange(entries.filter((_, entryIndex) => entryIndex !== index))}
              >
                <Trash2 aria-hidden="true" size={16} />
              </button>
            )}
          </div>
        </div>
      ))}
    </fieldset>
  );
}

function matchesConditionScope(condition, requirementIds, criterionIds, scenarioConditionIds) {
  if (scenarioConditionIds.has(condition._id)) return true;
  if (!requirementIds.size && !criterionIds.size) return true;
  return (condition.basis_refs || []).some((reference) => {
    const sourceId = reference.artifact_version_id || reference.artifact_id;
    return (
      (reference.artifact_type === "REQUIREMENT_VERSION" && requirementIds.has(sourceId)) ||
      (reference.artifact_type === "ACCEPTANCE_CRITERION" && criterionIds.has(sourceId))
    );
  });
}

export default function TestCaseCreateModal({
  projectId,
  isOpen,
  onClose,
  form,
  setForm,
  dataSets,
  testConditions,
  strategyTestLevels = [],
  strategyTestTypes = [],
  repositoryNodes,
  reusableSteps,
  customFields,
  requirements = [],
  scenarios = [],
  scenarioRequired = false,
  members = [],
  canReadMembers = false,
  membersUnavailable = false,
  onRetryMembers,
  saving,
  onSubmit,
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
  const scenarioConditionIds = new Set(
    scenarios.find((item) => item._id === form.scenarioId)?.test_condition_ids || [],
  );
  const scopedCriterionIds = new Set(
    selectedCriterionIds.size
      ? selectedCriterionIds
      : selectedCriteria.map((criterion) => criterion._id),
  );
  const scopedTestConditions = testConditions.filter((condition) =>
    matchesConditionScope(condition, requirementIds, scopedCriterionIds, scenarioConditionIds),
  );
  const testLevelOptions = [
    ...new Set([
      ...strategyTestLevels,
      ...scopedTestConditions.map((item) => item.test_level).filter(Boolean),
    ]),
  ];
  const testKindOptions = [
    ...new Set([
      ...strategyTestTypes,
      ...scopedTestConditions.map((item) => item.test_type).filter(Boolean),
    ]),
  ];
  const retainScopedConditionIds = (conditionIds, scopedRequirements, scopedCriteria) =>
    conditionIds.filter((conditionId) => {
      const condition = testConditions.find((item) => item._id === conditionId);
      return (
        condition &&
        matchesConditionScope(condition, scopedRequirements, scopedCriteria, scenarioConditionIds)
      );
    });

  return (
    <Modal
      isOpen={isOpen}
      onClose={() => {
        if (!saving) onClose();
      }}
      ariaLabel="Tạo ca kiểm thử"
      className="max-w-3xl max-h-[90dvh] overflow-y-auto"
    >
      <ModalHeader>
        <ModalTitle>Tạo ca kiểm thử</ModalTitle>
      </ModalHeader>
      <form onSubmit={onSubmit} className="space-y-4 p-5">
        <label className="field-label block">
          Kịch bản kiểm thử
          <select
            className="apple-input mt-2"
            value={form.scenarioId || ""}
            required={scenarioRequired}
            onChange={(event) => {
              const scenario = scenarios.find((item) => item._id === event.target.value);
              const requirementVersionIds = scenario?.requirement_version_ids || [];
              const acceptanceCriterionIds = scenario?.acceptance_criterion_ids || [];
              const linkedConditionIds = new Set(scenario?.test_condition_ids || []);
              const scopedConditionIds = testConditions
                .filter((condition) =>
                  matchesConditionScope(
                    condition,
                    new Set(requirementVersionIds),
                    new Set(acceptanceCriterionIds),
                    linkedConditionIds,
                  ),
                )
                .map((condition) => condition._id);
              update({
                scenarioId: event.target.value,
                ...(scenario && {
                  requirementVersionIds,
                  acceptanceCriterionIds,
                  testConditionIds: (scenario.test_condition_ids || []).filter((id) =>
                    scopedConditionIds.includes(id),
                  ),
                }),
              });
            }}
          >
            <option value="">Chưa liên kết kịch bản</option>
            {scenarios
              .filter((item) => item.status !== "archived")
              .map((item) => (
                <option key={item._id} value={item._id}>
                  {item.scenario_key} · {item.title}
                </option>
              ))}
          </select>
        </label>
        <label className="field-label">
          Tên
          <input
            className="apple-input mt-2"
            required
            value={form.title}
            onChange={(event) => update({ title: event.target.value })}
          />
        </label>
        <div className="grid gap-3 sm:grid-cols-2">
          <label className="field-label">
            Cách viết ca
            <select
              aria-label="Cách viết ca kiểm thử"
              className="apple-input"
              value={form.testStyle}
              onChange={(event) => update({ testStyle: event.target.value })}
            >
              <option value="MANUAL">Thủ công</option>
              <option value="BDD">BDD</option>
            </select>
          </label>
          <label className="field-label">
            Loại
            <input
              aria-label="Loại ca kiểm thử"
              className="apple-input"
              required
              maxLength={100}
              value={form.type}
              onChange={(event) => update({ type: event.target.value })}
              placeholder="Nhập loại ca kiểm thử"
            />
          </label>
          <label className="field-label">
            Ưu tiên
            <input
              aria-label="Ưu tiên ca kiểm thử"
              className="apple-input"
              maxLength={100}
              placeholder="Nhập mức ưu tiên theo quy ước dự án"
              value={form.priority ? valueLabel(form.priority) : ""}
              onChange={(event) => update({ priority: event.target.value })}
            />
          </label>
          <label className="field-label">
            Rủi ro
            <input
              aria-label="Rủi ro ca kiểm thử"
              className="apple-input"
              maxLength={100}
              placeholder="Nhập mức rủi ro theo quy ước dự án"
              value={form.risk ? valueLabel(form.risk) : ""}
              onChange={(event) => update({ risk: event.target.value })}
            />
          </label>
        </div>
        <div className="grid gap-3 sm:grid-cols-3">
          {[
            { field: "testLevel", label: "Cấp kiểm thử", options: testLevelOptions },
            { field: "testKind", label: "Loại kiểm thử", options: testKindOptions },
            { field: "expectedImpact", label: "Ảnh hưởng dự kiến", freeText: true },
          ].map(({ field, label, options, freeText }) => (
            <label className="field-label font-medium" key={field}>
              {label}
              {freeText ? (
                <input
                  className="apple-input mt-2"
                  value={form[field] ? valueLabel(form[field]) : ""}
                  aria-label={label}
                  maxLength={100}
                  onChange={(event) => update({ [field]: event.target.value })}
                />
              ) : (
                <select
                  className="apple-input mt-2"
                  value={form[field] || ""}
                  aria-label={label}
                  disabled={!options.length}
                  onChange={(event) => update({ [field]: event.target.value })}
                >
                  <option value="">Chưa chọn</option>
                  {form[field] && !options.includes(form[field]) && (
                    <option value={form[field]}>{valueLabel(form[field])}</option>
                  )}
                  {options.map((option) => (
                    <option key={option} value={option}>
                      {valueLabel(option)}
                    </option>
                  ))}
                </select>
              )}
              {!freeText && !options.length && (
                <span className="mt-1 block text-xs font-normal text-ink-muted">
                  Chọn điều kiện kiểm thử để có danh sách giá trị phù hợp.
                </span>
              )}
            </label>
          ))}
        </div>
        <label className="field-label">
          Lý do đánh giá ảnh hưởng
          <textarea
            className="apple-input mt-2"
            value={form.assessmentReason}
            onChange={(event) => update({ assessmentReason: event.target.value })}
          />
        </label>
        <div>
          <p className="field-label mb-2">Mục tiêu</p>
          <DocumentEditor
            value={form.objective}
            onChange={(objective) => update({ objective })}
            label="Mục tiêu của ca kiểm thử"
            minHeight="min-h-20"
          />
        </div>
        <div>
          <p className="field-label mb-2">Điều kiện trước</p>
          <DocumentEditor
            value={form.preconditions}
            onChange={(preconditions) => update({ preconditions })}
            label="Điều kiện cần có trước khi chạy"
            minHeight="min-h-20"
          />
        </div>
        <label className="field-label">
          Kỹ năng cần có để thực hiện ca (phân cách bằng dấu phẩy)
          <input
            className="apple-input mt-2"
            value={form.requiredSkills}
            onChange={(event) => update({ requiredSkills: event.target.value })}
            placeholder="Ví dụ: kiểm thử API, bảo mật"
          />
        </label>
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
                <option value="">Chưa phân công</option>
                {members
                  .filter((member) => member.status === "ACTIVE")
                  .map((member) => (
                    <option key={member.user_id} value={member.user_id}>
                      {member.user_label ||
                        member.user?.full_name ||
                        member.user?.email ||
                        "Thành viên dự án"}
                      {member.project_role ? ` · ${valueLabel(member.project_role)}` : ""}
                    </option>
                  ))}
              </select>
            </label>
            <TestCaseOwnerRecommendation
              projectId={projectId}
              requiredSkills={form.requiredSkills}
              onSelect={(candidate) => update({ ownerId: candidate.user_id })}
            />
            <p className="mt-2 text-sm text-ink-muted">
              Đây là người phụ trách bản Test Case. Người thực chạy được phân công riêng trong từng
              Test Run.
            </p>
            {membersUnavailable && (
              <div className="mt-2 flex flex-wrap items-center gap-3 text-sm text-amber-800">
                <span role="status">
                  Không tải được thành viên dự án nên chưa thể chọn người phụ trách.
                </span>
                {onRetryMembers && (
                  <button type="button" className="text-forest underline" onClick={onRetryMembers}>
                    Tải lại danh sách thành viên
                  </button>
                )}
              </div>
            )}
          </div>
        )}
        {form.testStyle === "BDD" && (
          <div className="grid gap-3 rounded-control border border-border p-4">
            <p className="field-label">Kịch bản BDD</p>
            <input
              aria-label="Tính năng trong kịch bản BDD"
              className="apple-input"
              value={form.feature}
              onChange={(event) => update({ feature: event.target.value })}
              placeholder="Tính năng"
              required
            />
            <input
              aria-label="Tên kịch bản BDD"
              className="apple-input"
              value={form.scenario}
              onChange={(event) => update({ scenario: event.target.value })}
              placeholder="Tên kịch bản"
              required
            />
            <input
              aria-label="Điều kiện ban đầu của kịch bản BDD"
              className="apple-input"
              value={form.given}
              onChange={(event) => update({ given: event.target.value })}
              placeholder="Điều kiện ban đầu"
              required
            />
            <input
              aria-label="Hành động của kịch bản BDD"
              className="apple-input"
              value={form.when}
              onChange={(event) => update({ when: event.target.value })}
              placeholder="Hành động"
              required
            />
            <input
              aria-label="Kết quả mong đợi của kịch bản BDD"
              className="apple-input"
              value={form.then}
              onChange={(event) => update({ then: event.target.value })}
              placeholder="Kết quả mong đợi"
              required
            />
            <MultiSelect
              label="Bước dùng lại"
              options={reusableSteps.map((item) => ({
                value: item.current_version_id,
                label: `${item.name} v${item.version}`,
              }))}
              value={form.reusableStepVersionIds}
              onChange={(reusableStepVersionIds) => update({ reusableStepVersionIds })}
            />
          </div>
        )}
        <label className="field-label">
          Thư mục kho ca kiểm thử
          <select
            aria-label="Thư mục kho ca kiểm thử"
            className="apple-input mt-2"
            value={form.repositoryNodeId}
            onChange={(event) => update({ repositoryNodeId: event.target.value })}
          >
            <option value="">Thư mục gốc</option>
            {repositoryNodes.map((item) => (
              <option key={item._id} value={item._id}>
                {item.name}
              </option>
            ))}
          </select>
        </label>
        <MultiSelect
          label="Phiên bản yêu cầu liên quan"
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
            label="Tiêu chí chấp nhận được ca này kiểm thử"
            searchPlaceholder="Tìm tiêu chí chấp nhận"
            emptyMessage="Yêu cầu đã chọn chưa có tiêu chí chấp nhận"
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
        {form.requirementVersionIds.length > 0 && (
          <RequirementCoverageSelector
            requirements={requirements}
            requirementVersionIds={form.requirementVersionIds}
            value={form.coverageItemIds || []}
            onChange={(coverageItemIds) => update({ coverageItemIds })}
          />
        )}
        <section
          className="space-y-4 rounded-control border border-border p-4"
          aria-label="Các bước kiểm thử"
        >
          <div className="flex flex-wrap items-center justify-between gap-3">
            <div>
              <h3 className="font-semibold">Các bước kiểm thử</h3>
              <p className="text-sm text-muted-foreground">
                Mỗi bước có thao tác, dữ liệu đầu vào và kết quả mong đợi riêng.
              </p>
            </div>
            <button
              className="secondary-button"
              type="button"
              onClick={() =>
                update({
                  steps: [
                    ...form.steps,
                    {
                      id: crypto.randomUUID(),
                      action: emptyDoc(),
                      data: [{ id: crypto.randomUUID(), name: "", value: "" }],
                      expected: emptyDoc(),
                    },
                  ],
                })
              }
            >
              Thêm bước
            </button>
          </div>
          {form.steps.map((step, index) => (
            <div className="space-y-3 rounded-control border border-border p-3" key={step.id}>
              <div className="flex items-center justify-between gap-3">
                <h4 className="font-medium">Bước {index + 1}</h4>
                {form.steps.length > 1 && (
                  <button
                    aria-label={`Xóa bước ${index + 1}`}
                    className="icon-button h-9 w-9 text-danger"
                    title="Xóa bước"
                    type="button"
                    onClick={() =>
                      update({ steps: form.steps.filter((_, stepIndex) => stepIndex !== index) })
                    }
                  >
                    <Trash2 aria-hidden="true" size={16} />
                  </button>
                )}
              </div>
              <div>
                <p className="field-label mb-2">Thao tác</p>
                <DocumentEditor
                  value={step.action}
                  onChange={(action) => updateStep(index, { action })}
                  label={`Thao tác bước ${index + 1}`}
                  minHeight="min-h-20"
                />
              </div>
              <TestDataEntries
                label={`Dữ liệu bước ${index + 1}`}
                entries={step.data}
                onChange={(data) => updateStep(index, { data })}
              />
              <div>
                <p className="field-label mb-2">Kết quả mong đợi</p>
                <DocumentEditor
                  value={step.expected}
                  onChange={(expected) => updateStep(index, { expected })}
                  label={`Kết quả mong đợi bước ${index + 1}`}
                  minHeight="min-h-20"
                />
              </div>
            </div>
          ))}
        </section>
        <TestDataEntries
          label="Dữ liệu kiểm thử chung"
          entries={form.testData}
          onChange={(testData) => update({ testData })}
        />
        <div>
          <p className="field-label mb-2">Kết quả mong đợi chung</p>
          <DocumentEditor
            value={form.expectedResult}
            onChange={(expectedResult) => update({ expectedResult })}
            label="Kết quả mong đợi chung của ca kiểm thử"
            minHeight="min-h-20"
          />
        </div>
        <div>
          <p className="field-label mb-2">Điều kiện sau</p>
          <DocumentEditor
            value={form.postconditions}
            onChange={(postconditions) => update({ postconditions })}
            label="Điều kiện sau khi chạy ca kiểm thử"
            minHeight="min-h-20"
          />
        </div>
        <div className="grid gap-3 sm:grid-cols-2">
          <label className="field-label">
            Kỹ thuật kiểm thử (phân cách bằng dấu phẩy)
            <input
              className="apple-input mt-2"
              value={form.techniques}
              onChange={(event) => update({ techniques: event.target.value })}
              placeholder="Ví dụ: phân vùng tương đương, giá trị biên"
            />
          </label>
          <label className="field-label">
            Nhãn (phân cách bằng dấu phẩy)
            <input
              className="apple-input mt-2"
              value={form.tags}
              onChange={(event) => update({ tags: event.target.value })}
            />
          </label>
        </div>
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
        <MultiSelect
          label="Bộ dữ liệu tham số"
          options={dataSets.map((item) => ({
            value: item.current_version_id,
            label: `${item.name} v${item.current_version?.version}`,
          }))}
          value={form.dataSetVersionIds}
          onChange={(dataSetVersionIds) => update({ dataSetVersionIds })}
        />
        <MultiSelect
          label="Điều kiện kiểm thử đã phê duyệt"
          emptyMessage={
            form.requirementVersionIds.length
              ? "Chưa có điều kiện đã duyệt gắn với yêu cầu hoặc tiêu chí đang chọn"
              : "Chưa có điều kiện kiểm thử đã phê duyệt"
          }
          options={scopedTestConditions.map((item) => ({
            value: item._id,
            label: `${item.condition_key} ${item.title}`,
          }))}
          value={form.testConditionIds}
          onChange={(testConditionIds) => update({ testConditionIds })}
        />
        <TestCaseCustomValues
          fields={customFields}
          values={form.customValues || {}}
          onChange={(customValues) => update({ customValues })}
        />
        <div className="action-dialog-footer flex justify-end gap-3">
          <button className="secondary-button" type="button" disabled={saving} onClick={onClose}>
            Hủy
          </button>
          <button className="apple-button" type="submit" disabled={saving}>
            {saving ? "Đang lưu" : "Lưu bản nháp"}
          </button>
        </div>
      </form>
    </Modal>
  );
}
