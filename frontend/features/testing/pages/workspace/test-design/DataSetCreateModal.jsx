import { Modal, ModalHeader, ModalTitle } from "@/shared/components/ui/Modal";
import StructuredValueEditor from "../../../components/StructuredValueEditor";

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
        <div className="min-w-0 space-y-2">
          <p className="field-label">Biến dữ liệu</p>
          <StructuredValueEditor
            label="Biến dữ liệu"
            value={form.variables || {}}
            fixedType="object"
            onChange={(variables) => update({ variables })}
          />
          <span
            id="dataset-variables-help"
            className="mt-1 block text-xs font-normal text-ink-muted"
          >
            Khai báo dữ liệu kiểm thử theo cặp tên và giá trị. Không nhập mật khẩu, mã truy cập hoặc
            khóa bí mật ở đây.
          </span>
        </div>
        <div className="min-w-0 space-y-2">
          <p className="field-label">Tham chiếu đến bí mật</p>
          <StructuredValueEditor
            label="Tham chiếu đến bí mật"
            value={form.secretRefs || {}}
            fixedType="object"
            onChange={(secretRefs) => update({ secretRefs })}
          />
          <span
            id="dataset-secret-refs-help"
            className="mt-1 block text-xs font-normal text-ink-muted"
          >
            Dùng địa chỉ bắt đầu bằng <code>secret://</code>; không nhập giá trị bí mật trực tiếp.
          </span>
        </div>
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
