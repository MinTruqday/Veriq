import DocumentEditor from "../../../editor/DocumentEditor";
import { valueLabel } from "../../../lib/testing";
import { Modal, ModalHeader, ModalTitle } from "@/shared/components/ui/Modal";
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
  onSubmit,
}) {
  const update = (patch) => setForm((value) => ({ ...value, ...patch }));

  return (
    <Modal
      isOpen={isOpen}
      onClose={onClose}
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
        <div className="grid gap-3 sm:grid-cols-3">
          <select
            aria-label="Cách viết ca kiểm thử"
            className="apple-input"
            value={form.testStyle}
            onChange={(event) => update({ testStyle: event.target.value })}
          >
            <option value="MANUAL">Manual</option>
            <option value="BDD">BDD</option>
          </select>
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
        </div>
        {form.testStyle === "BDD" && (
          <div className="grid gap-3 rounded-control border border-border p-4">
            <p className="field-label">Kịch bản BDD</p>
            <input
              className="apple-input"
              value={form.feature}
              onChange={(event) => update({ feature: event.target.value })}
              placeholder="Feature"
              required
            />
            <input
              className="apple-input"
              value={form.scenario}
              onChange={(event) => update({ scenario: event.target.value })}
              placeholder="Scenario"
              required
            />
            <input
              className="apple-input"
              value={form.given}
              onChange={(event) => update({ given: event.target.value })}
              placeholder="Given"
              required
            />
            <input
              className="apple-input"
              value={form.when}
              onChange={(event) => update({ when: event.target.value })}
              placeholder="When"
              required
            />
            <input
              className="apple-input"
              value={form.then}
              onChange={(event) => update({ then: event.target.value })}
              placeholder="Then"
              required
            />
            <label className="field-label">
              Bước dùng lại
              <select
                aria-label="Bước dùng lại cho kịch bản BDD"
                className="apple-input mt-2 min-h-24"
                multiple
                value={form.reusableStepVersionIds}
                onChange={(event) => update({ reusableStepVersionIds: selectedValues(event) })}
              >
                {reusableSteps.map((item) => (
                  <option key={item.current_version_id} value={item.current_version_id}>
                    {item.name} v{item.version}
                  </option>
                ))}
              </select>
            </label>
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
        <label className="field-label">
          Bộ dữ liệu tham số
          <select
            aria-label="Bộ dữ liệu cho ca kiểm thử mới"
            className="apple-input mt-2 min-h-28"
            multiple
            value={form.dataSetVersionIds}
            onChange={(event) => update({ dataSetVersionIds: selectedValues(event) })}
          >
            {dataSets.map((item) => (
              <option key={item.current_version_id} value={item.current_version_id}>
                {item.name} v{item.current_version?.version}
              </option>
            ))}
          </select>
        </label>
        <label className="field-label">
          Điều kiện kiểm thử đã phê duyệt
          <select
            aria-label="Điều kiện kiểm thử cho ca kiểm thử mới"
            className="apple-input mt-2 min-h-28"
            multiple
            value={form.testConditionIds}
            onChange={(event) => update({ testConditionIds: selectedValues(event) })}
          >
            {testConditions.map((item) => (
              <option key={item._id} value={item._id}>
                {item.condition_key} {item.title}
              </option>
            ))}
          </select>
        </label>
        <div className="flex justify-end gap-3">
          <button className="secondary-button" type="button" onClick={onClose}>
            Hủy
          </button>
          <button className="apple-button" type="submit">
            Lưu bản nháp
          </button>
        </div>
      </form>
    </Modal>
  );
}
