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
      <form className="space-y-3 p-5" onSubmit={onSubmit}>
        <input
          aria-label="Tên kịch bản"
          className="apple-input"
          required
          value={form.title}
          onChange={(event) => update({ title: event.target.value })}
          placeholder="Tên kịch bản"
        />
        <textarea
          aria-label="Mục tiêu kịch bản"
          className="apple-input min-h-20"
          value={form.objective}
          onChange={(event) => update({ objective: event.target.value })}
          placeholder="Mục tiêu và phạm vi"
        />
        <select
          aria-label="Nhóm kịch bản"
          className="apple-input"
          value={form.category}
          onChange={(event) => update({ category: event.target.value })}
        >
          {TEST_SCENARIO_CATEGORIES.map((value) => (
            <option key={value} value={value}>
              {valueLabel(value)}
            </option>
          ))}
        </select>
        <MultiSelect
          label="Điều kiện kiểm thử đã phê duyệt"
          options={testConditions.map((item) => ({
            value: item._id,
            label: `${item.condition_key} ${item.title}`,
          }))}
          value={form.testConditionIds}
          onChange={(testConditionIds) => update({ testConditionIds })}
        />
        <div className="flex justify-end gap-3">
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
