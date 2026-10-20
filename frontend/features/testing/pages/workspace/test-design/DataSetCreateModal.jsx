import { Modal, ModalHeader, ModalTitle } from "@/shared/components/ui/Modal";

export default function DataSetCreateModal({ isOpen, onClose, form, setForm, saving, onSubmit }) {
  const update = (patch) => setForm((value) => ({ ...value, ...patch }));

  return (
    <Modal
      isOpen={isOpen}
      onClose={() => {
        if (!saving) onClose();
      }}
      ariaLabel="Tạo bộ dữ liệu"
      className="max-w-2xl max-h-[90dvh] overflow-y-auto"
    >
      <ModalHeader>
        <ModalTitle>Tạo bộ dữ liệu</ModalTitle>
      </ModalHeader>
      <form className="grid gap-3 p-5" onSubmit={onSubmit}>
        <label className="field-label">
          Tên bộ dữ liệu
          <input
            className="apple-input mt-2"
            required
            value={form.name}
            onChange={(event) => update({ name: event.target.value })}
          />
        </label>
        <label className="field-label">
          Biến JSON
          <textarea
            className="apple-input mt-2 min-h-28 font-mono"
            required
            value={form.variables}
            onChange={(event) => update({ variables: event.target.value })}
          />
        </label>
        <label className="field-label">
          Secret refs JSON
          <textarea
            className="apple-input mt-2 min-h-28 font-mono"
            required
            value={form.secretRefs}
            onChange={(event) => update({ secretRefs: event.target.value })}
          />
        </label>
        <div className="action-dialog-footer flex justify-end gap-3">
          <button className="secondary-button" type="button" disabled={saving} onClick={onClose}>
            Hủy
          </button>
          <button className="apple-button" type="submit" disabled={saving}>
            {saving ? "Đang tạo" : "Tạo bộ dữ liệu"}
          </button>
        </div>
      </form>
    </Modal>
  );
}
