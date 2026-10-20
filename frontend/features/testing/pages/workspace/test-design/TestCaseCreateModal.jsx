import DocumentEditor from "../../../editor/DocumentEditor";
import { valueLabel } from "../../../lib/testing";
import { Modal, ModalHeader, ModalTitle } from "@/shared/components/ui/Modal";
import MultiSelect from "@/shared/components/ui/MultiSelect";
import { selectedValues, TEST_CASE_TYPES, TEST_LEVELS } from "./testDesign.model";

export default function TestCaseCreateModal({
  isOpen,
  onClose,
  form,
  setForm,
  dataSets,
  testConditions,
  repositoryNodes,
  reusableSteps,
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
      ariaLabel="Tạo ca kiểm thử"
      className="max-w-3xl max-h-[90dvh] overflow-y-auto"
    >
      <ModalHeader>
        <ModalTitle>Tạo ca kiểm thử</ModalTitle>
      </ModalHeader>
      <form onSubmit={onSubmit} className="space-y-4 p-5">
        <label className="field-label">
          Tên
          <input
            className="apple-input mt-2"
            required
            value={form.title}
            onChange={(event) => update({ title: event.target.value })}
          />
        </label>
        <div className="grid gap-3 sm:grid-cols-2 lg:grid-cols-4">
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
            <select
              aria-label="Loại ca kiểm thử"
              className="apple-input"
              value={form.type}
              onChange={(event) => update({ type: event.target.value })}
            >
              {TEST_CASE_TYPES.map((value) => (
                <option key={value} value={value}>
                  {valueLabel(value)}
                </option>
              ))}
            </select>
          </label>
          <label className="field-label">
            Ưu tiên
            <select
              aria-label="Ưu tiên ca kiểm thử"
              className="apple-input"
              value={form.priority}
              onChange={(event) => update({ priority: event.target.value })}
            >
              {TEST_LEVELS.map((value) => (
                <option key={value} value={value}>
                  {valueLabel(value)}
                </option>
              ))}
            </select>
          </label>
          <label className="field-label">
            Rủi ro
            <select
              aria-label="Rủi ro ca kiểm thử"
              className="apple-input"
              value={form.risk}
              onChange={(event) => update({ risk: event.target.value })}
            >
              {TEST_LEVELS.map((value) => (
                <option key={value} value={value}>
                  {valueLabel(value)}
                </option>
              ))}
            </select>
          </label>
        </div>
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
        <div>
          <p className="field-label mb-2">Thao tác</p>
          <DocumentEditor
            value={form.action}
            onChange={(action) => update({ action })}
            label="Thao tác của ca kiểm thử"
            minHeight="min-h-24"
          />
        </div>
        <div>
          <p className="field-label mb-2">Kết quả mong đợi</p>
          <DocumentEditor
            value={form.expected}
            onChange={(expected) => update({ expected })}
            label="Kết quả mong đợi của ca kiểm thử"
            minHeight="min-h-24"
          />
        </div>
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
          options={testConditions.map((item) => ({
            value: item._id,
            label: `${item.condition_key} ${item.title}`,
          }))}
          value={form.testConditionIds}
          onChange={(testConditionIds) => update({ testConditionIds })}
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
