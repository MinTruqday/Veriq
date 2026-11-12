import { Modal, ModalHeader, ModalTitle } from "@/shared/components/ui/Modal";
import MultiSelect from "@/shared/components/ui/MultiSelect";
import { valueLabel } from "../../../lib/testing";

export default function ScenarioCreateModal({
  isOpen,
  onClose,
  form,
  setForm,
  testConditions,
  strategyTestLevels = [],
  strategyTestTypes = [],
  saving,
  onSubmit,
  title = "Tạo kịch bản",
  readOnly = false,
  canAssignOwner = true,
  requirements = [],
  members = [],
  canReadTestConditions = false,
  children,
}) {
  const update = (patch) => setForm((value) => ({ ...value, ...patch }));
  const requirementVersionIds = form.requirementVersionIds || [];
  const acceptanceCriterionIds = form.acceptanceCriterionIds || [];
  const testConditionIds = form.testConditionIds || [];
  const selectedRequirements = requirements.filter((item) =>
    requirementVersionIds.includes(item.current_version_id),
  );
  const criterionOptions = selectedRequirements.flatMap((item) =>
    (item.current_version?.acceptance_criteria || []).map((criterion) => ({
      value: criterion._id,
      label: `${item.requirement_key} · ${criterion.key || criterion._id}`,
    })),
  );
  const selectedCriterionIds = new Set(acceptanceCriterionIds);
  const selectedRequirementIds = new Set(requirementVersionIds);
  const selectedConditionIds = new Set(testConditionIds);
  const relevantConditions = testConditions.filter((condition) => {
    if (selectedConditionIds.has(condition._id)) return true;
    const references = condition.basis_refs || [];
    return references.some((reference) => {
      const id = reference.artifact_version_id || reference.artifact_id;
      return (
        (reference.artifact_type === "ACCEPTANCE_CRITERION" && selectedCriterionIds.has(id)) ||
        (reference.artifact_type === "REQUIREMENT_VERSION" && selectedRequirementIds.has(id))
      );
    });
  });
  const conditionsForClassification = relevantConditions.filter(
    (condition) => !testConditionIds.length || selectedConditionIds.has(condition._id),
  );
  const testLevelOptions = [
    ...new Set(
      [
        ...strategyTestLevels,
        ...conditionsForClassification.map((condition) => condition.test_level),
        form.test_level,
      ]
        .map((item) => String(item || "").trim())
        .filter(Boolean),
    ),
  ];
  const testKindOptions = [
    ...new Set(
      [
        ...strategyTestTypes,
        ...conditionsForClassification.map((condition) => condition.test_type),
        form.test_kind,
      ]
        .map((item) => String(item || "").trim())
        .filter(Boolean),
    ),
  ];

  return (
    <Modal
      isOpen={isOpen}
      onClose={() => {
        if (!saving) onClose();
      }}
      ariaLabel={title}
      className="max-w-3xl max-h-[90dvh] overflow-y-auto"
    >
      <ModalHeader>
        <ModalTitle>{title}</ModalTitle>
      </ModalHeader>
      <form className="min-w-0 space-y-3 p-5" onSubmit={onSubmit}>
        <fieldset disabled={readOnly || saving} className="min-w-0 space-y-4">
          <label className="field-label block min-w-0">
            Tên kịch bản
            <input
              className="apple-input mt-2 w-full min-w-0"
              required
              value={form.title}
              onChange={(event) => update({ title: event.target.value })}
            />
          </label>
          <label className="field-label block min-w-0">
            Mục tiêu và phạm vi
            <textarea
              className="apple-input mt-2 min-h-20 w-full min-w-0"
              value={form.objective}
              onChange={(event) => update({ objective: event.target.value })}
            />
          </label>
          <label className="field-label block min-w-0">
            Nhóm kịch bản
            <input
              className="apple-input mt-2 w-full min-w-0"
              required
              maxLength={100}
              value={form.category}
              onChange={(event) => update({ category: event.target.value })}
              placeholder="Nhập nhóm kịch bản"
            />
          </label>
          <MultiSelect
            label="Phạm vi yêu cầu"
            options={requirements.map((item) => ({
              value: item.current_version_id,
              label: `${item.requirement_key} ${item.current_version?.title || item.title || ""}`,
            }))}
            value={requirementVersionIds}
            onChange={(requirementVersionIds) =>
              update({ requirementVersionIds, acceptanceCriterionIds: [], testConditionIds: [] })
            }
          />
          {requirementVersionIds.length > 0 && (
            <>
              <MultiSelect
                label="Tiêu chí cần bao phủ"
                options={criterionOptions}
                value={acceptanceCriterionIds}
                onChange={(acceptanceCriterionIds) =>
                  update({ acceptanceCriterionIds, testConditionIds: [] })
                }
              />
              {canReadTestConditions ? (
                <>
                  <MultiSelect
                    label="Điều kiện kiểm thử liên quan"
                    options={relevantConditions.map((item) => ({
                      value: item._id,
                      label: `${item.condition_key || "Điều kiện kiểm thử"}${item.title ? ` · ${item.title}` : ""}`,
                    }))}
                    value={testConditionIds.filter((id) =>
                      relevantConditions.some((item) => item._id === id),
                    )}
                    onChange={(testConditionIds) => update({ testConditionIds })}
                  />
                  {!relevantConditions.length && (
                    <p className="text-sm text-ink-muted">
                      Chưa có điều kiện kiểm thử đã duyệt gắn với phạm vi yêu cầu đang chọn.
                    </p>
                  )}
                </>
              ) : (
                <p className="text-sm text-ink-muted">
                  Tài khoản hiện không có quyền xem điều kiện kiểm thử của dự án.
                </p>
              )}
            </>
          )}
          <div className="grid gap-4 md:grid-cols-2">
            {[
              ["description", "Mô tả tình huống"],
              ["actors", "Tác nhân"],
              ["preconditions", "Điều kiện trước"],
              ["business_flow", "Luồng nghiệp vụ và ngoại lệ"],
              ["expected_outcome", "Kết quả mong đợi"],
              ["test_data_notes", "Dữ liệu và biến thể cần kiểm tra"],
            ].map(([key, label]) => (
              <label className="field-label" key={key}>
                {label}
                <textarea
                  className="apple-input mt-2 min-h-20"
                  value={form[key]}
                  onChange={(event) => update({ [key]: event.target.value })}
                />
              </label>
            ))}
            {[
              ["risk", "Mức rủi ro theo quy ước dự án"],
              ["priority", "Mức ưu tiên theo quy ước dự án"],
            ].map(([key, label]) => (
              <label className="field-label" key={key}>
                {label}
                <input
                  className="apple-input mt-2"
                  maxLength={100}
                  required={key === "risk" || key === "priority"}
                  value={form[key] ? valueLabel(form[key]) : ""}
                  onChange={(event) => update({ [key]: event.target.value })}
                />
              </label>
            ))}
            {[
              ["test_level", "Cấp kiểm thử", testLevelOptions],
              ["test_kind", "Loại kiểm thử", testKindOptions],
            ].map(([key, label, options]) => (
              <label className="field-label" key={key}>
                {label}
                <select
                  className="apple-input mt-2"
                  aria-label={label}
                  value={form[key] || ""}
                  disabled={
                    !options.length ||
                    (!canReadTestConditions &&
                      !strategyTestLevels.length &&
                      !strategyTestTypes.length)
                  }
                  onChange={(event) => update({ [key]: event.target.value })}
                >
                  <option value="">Chưa chọn</option>
                  {options.map((option) => (
                    <option value={option} key={option}>
                      {valueLabel(option)}
                    </option>
                  ))}
                </select>
                {!options.length && (
                  <span className="mt-1 block text-xs font-normal text-ink-muted">
                    {canReadTestConditions
                      ? "Chọn yêu cầu và điều kiện kiểm thử đã duyệt để có lựa chọn phù hợp."
                      : "Cần quyền xem điều kiện kiểm thử để chọn giá trị đã duyệt."}
                  </span>
                )}
              </label>
            ))}
            <label className="field-label">
              Người phụ trách
              <select
                className="apple-input mt-2"
                value={form.owner_id}
                disabled={!canAssignOwner}
                onChange={(event) => update({ owner_id: event.target.value })}
              >
                <option value="">Chưa phân công</option>
                {form.owner_id && !members.some((member) => member.user_id === form.owner_id) && (
                  <option value={form.owner_id}>Người phụ trách hiện tại</option>
                )}
                {members
                  .filter((item) => item.status === "ACTIVE")
                  .map((item) => (
                    <option key={item.user_id} value={item.user_id}>
                      {item.user_label ||
                        item.user?.full_name ||
                        item.user?.email ||
                        "Thành viên chưa có tên"}
                    </option>
                  ))}
              </select>
            </label>
            <label className="field-label">
              Nhãn
              <input
                className="apple-input mt-2"
                value={form.tags}
                onChange={(event) => update({ tags: event.target.value })}
              />
            </label>
          </div>
        </fieldset>
        {children}
        <div className="flex flex-wrap justify-end gap-3">
          <button className="secondary-button" type="button" disabled={saving} onClick={onClose}>
            {readOnly ? "Đóng" : "Hủy"}
          </button>
          {!readOnly && (
            <button className="apple-button" type="submit" disabled={saving}>
              {saving ? "Đang lưu" : "Lưu kịch bản"}
            </button>
          )}
        </div>
      </form>
    </Modal>
  );
}
