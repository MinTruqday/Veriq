import { valueLabel } from "../../../lib/testing";
import { Modal, ModalHeader, ModalTitle } from "@/shared/components/ui/Modal";
import MultiSelect from "@/shared/components/ui/MultiSelect";
import {
  TEST_SCENARIO_CATEGORIES,
  TESTING_LEVELS,
  TEST_KINDS,
  TEST_LEVELS,
} from "./testDesign.model";

export default function ScenarioCreateModal({
  isOpen,
  onClose,
  form,
  setForm,
  testConditions,
  saving,
  onSubmit,
  title = "Tạo kịch bản",
  readOnly = false,
  requirements = [],
  members = [],
  children,
}) {
  const update = (patch) => setForm((value) => ({ ...value, ...patch }));

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
            <select
              className="apple-input mt-2 w-full min-w-0"
              value={form.category}
              onChange={(event) => update({ category: event.target.value })}
            >
              {TEST_SCENARIO_CATEGORIES.map((value) => (
                <option key={value} value={value}>
                  {valueLabel(value)}
                </option>
              ))}
            </select>
          </label>
          <MultiSelect
            label="Phiên bản yêu cầu"
            options={requirements.map((item) => ({
              value: item.current_version_id,
              label: `${item.requirement_key} ${item.current_version?.title || item.title || ""}`,
            }))}
            value={form.requirementVersionIds}
            onChange={(requirementVersionIds) =>
              update({ requirementVersionIds, acceptanceCriterionIds: [] })
            }
          />
          <MultiSelect
            label="Tiêu chí chấp nhận"
            options={requirements
              .filter((item) => form.requirementVersionIds.includes(item.current_version_id))
              .flatMap((item) =>
                (item.current_version?.acceptance_criteria || []).map((criterion) => ({
                  value: criterion._id,
                  label: `${item.requirement_key} · ${criterion.key || criterion._id}`,
                })),
              )}
            value={form.acceptanceCriterionIds}
            onChange={(acceptanceCriterionIds) => update({ acceptanceCriterionIds })}
          />
          <MultiSelect
            label="Điều kiện kiểm thử đã phê duyệt"
            options={testConditions.map((item) => ({
              value: item._id,
              label: `${item.condition_key || "Điều kiện kiểm thử"}${item.title ? ` · ${item.title}` : ""}`,
            }))}
            value={form.testConditionIds}
            onChange={(testConditionIds) => update({ testConditionIds })}
          />
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
              ["risk", "Rủi ro", TEST_LEVELS],
              ["priority", "Ưu tiên", TEST_LEVELS],
              ["test_level", "Cấp kiểm thử", TESTING_LEVELS],
              ["test_kind", "Loại kiểm thử", TEST_KINDS],
            ].map(([key, label, options]) => (
              <label className="field-label" key={key}>
                {label}
                <select
                  className="apple-input mt-2"
                  value={form[key]}
                  onChange={(event) => update({ [key]: event.target.value })}
                >
                  <option value="">Chưa chọn</option>
                  {options.map((option) => (
                    <option key={option} value={option}>
                      {valueLabel(option)}
                    </option>
                  ))}
                </select>
              </label>
            ))}
            <label className="field-label">
              Người phụ trách
              <select
                className="apple-input mt-2"
                value={form.owner_id}
                onChange={(event) => update({ owner_id: event.target.value })}
              >
                <option value="">Chưa phân công</option>
                {members
                  .filter((item) => {
                    const roles = item.project_role
                      ? [item.project_role]
                      : Array.isArray(item.project_roles) && item.project_roles.length === 1
                        ? item.project_roles
                        : [];
                    return item.status === "ACTIVE" && roles.includes("QA");
                  })
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
