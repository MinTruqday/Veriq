import { valueLabel } from "../../../lib/testing";
import { Modal, ModalHeader, ModalTitle } from "@/shared/components/ui/Modal";
import MultiSelect from "@/shared/components/ui/MultiSelect";
import { TEST_SCENARIO_CATEGORIES } from "./testDesign.model";

export default function ScenarioCreateModal({
  isOpen,
  onClose,
  form,
  setForm,
  testConditions,
  saving,
  onSubmit,
}) {
  const update = (patch) => setForm((value) => ({ ...value, ...patch }));

  return (
    <Modal
      isOpen={isOpen}
      onClose={() => {
        if (!saving) onClose();
      }}
      ariaLabel="Tạo kịch bản"
      className="max-w-xl"
    >
      <ModalHeader>
        <ModalTitle>Tạo kịch bản</ModalTitle>
      </ModalHeader>
      <form className="min-w-0 space-y-3 p-5" onSubmit={onSubmit}>
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
          label="Điều kiện kiểm thử đã phê duyệt"
          options={testConditions.map((item) => ({
            value: item._id,
            label: `${item.condition_key || "Điều kiện kiểm thử"}${item.title ? ` · ${item.title}` : ""}`,
          }))}
          value={form.testConditionIds}
          onChange={(testConditionIds) => update({ testConditionIds })}
        />
        <div className="flex flex-wrap justify-end gap-3">
          <button className="secondary-button" type="button" disabled={saving} onClick={onClose}>
            Hủy
          </button>
          <button className="apple-button" type="submit" disabled={saving}>
            {saving ? "Đang lưu" : "Lưu kịch bản"}
          </button>
        </div>
      </form>
    </Modal>
  );
}
