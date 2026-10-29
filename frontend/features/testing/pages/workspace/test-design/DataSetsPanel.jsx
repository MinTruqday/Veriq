import { useState } from "react";
import DataTable from "../../../components/DataTable";
import { ErrorState, Panel } from "../../../components/WorkspacePrimitives";
import { messageOf } from "../../../lib/testing";
import { testingApi } from "../../../services/testing.service";
import DataSetCreateModal from "./DataSetCreateModal";
import { Modal, ModalHeader, ModalTitle } from "@/shared/components/ui/Modal";
import StructuredValueEditor, {
  StructuredValueView,
} from "../../../components/StructuredValueEditor";

export default function DataSetsPanel({
  projectId,
  can,
  canRead,
  items,
  isCreating,
  setCreating,
  saving,
  form,
  setForm,
  onSubmit,
  ask,
  reload,
  onError,
}) {
  const [preview, setPreview] = useState(null);
  const [previewingId, setPreviewingId] = useState("");
  const [versioningId, setVersioningId] = useState("");
  const [versionEditor, setVersionEditor] = useState(null);
  const [versionError, setVersionError] = useState("");
  const [savingVersion, setSavingVersion] = useState(false);
  if (!canRead) return null;

  const previewDataSet = async (item) => {
    setPreviewingId(item._id);
    try {
      const result = await testingApi.previewDataSet(projectId, item._id, {
        data_set_version_id: item.current_version_id,
        max_rows: 100,
      });
      setPreview({ ...result, name: item.name, version: item.current_version?.version });
    } catch (reason) {
      onError(messageOf(reason));
    } finally {
      setPreviewingId("");
    }
  };

  const archiveDataSet = async (item) => {
    await ask({
      title: "Lưu trữ bộ dữ liệu",
      description: `${item.name} · v${item.current_version?.version || 1}`,
      confirmLabel: "Lưu trữ",
      danger: true,
      fields: [{ name: "reason", label: "Lý do lưu trữ", required: true, multiline: true }],
      onConfirm: async ({ reason }) => {
        try {
          await testingApi.archiveDataSet(projectId, item._id, {
            expected_revision: item.revision,
            reason: reason.trim(),
          });
          await reload();
        } catch (failure) {
          throw new Error(messageOf(failure));
        }
      },
    });
  };
  const createDataSetVersion = async (item) => {
    if (versioningId) return;
    setVersioningId(item._id);
    setVersionError("");
    setVersionEditor({
      item,
      name: item.name,
      variables: structuredClone(item.current_version?.variables || {}),
      secretRefs: {},
      reason: "Cập nhật dữ liệu kiểm thử",
    });
  };
  const saveDataSetVersion = async (event) => {
    event.preventDefault();
    if (!versionEditor || savingVersion) return;
    setVersionError("");
    setSavingVersion(true);
    try {
      await testingApi.createDataSetVersion(versionEditor.item._id, {
        expected_current_version_id: versionEditor.item.current_version_id,
        name: versionEditor.name,
        variables: versionEditor.variables,
        secret_refs: versionEditor.secretRefs,
        change_reason: versionEditor.reason,
      });
      setVersionEditor(null);
      await reload();
    } catch (reason) {
      setVersionError(messageOf(reason));
    } finally {
      setSavingVersion(false);
    }
  };
  const previewKeys = Object.keys(preview?.items?.[0] || {});

  return (
    <Panel
      title="Bộ dữ liệu kiểm thử"
      actions={
        can("testdata.create") ? (
          <button className="secondary-button" type="button" onClick={() => setCreating(true)}>
            Tạo bộ dữ liệu
          </button>
        ) : null
      }
    >
      {can("testdata.create") && (
        <DataSetCreateModal
          isOpen={isCreating}
          onClose={() => {
            if (!saving) setCreating(false);
          }}
          saving={saving}
          form={form}
          setForm={setForm}
          onSubmit={onSubmit}
        />
      )}
      <DataTable
        items={items}
        empty="Chưa có bộ dữ liệu tham số"
        columns={[
          { key: "name", label: "Tên" },
          {
            key: "version",
            label: "Phiên bản",
            render: (item) => `v${item.current_version?.version || 1}`,
          },
          {
            key: "variables",
            label: "Biến",
            render: (item) => {
              const names = Object.keys(item.current_version?.variables || {});
              return names.length ? names.join(", ") : "Chưa khai báo";
            },
          },
          {
            key: "secret_refs",
            label: "Tham chiếu bí mật",
            render: (item) => {
              const names = Object.keys(item.current_version?.secret_refs || {});
              return names.length ? names.join(", ") : "Không dùng";
            },
          },
          {
            key: "actions",
            label: "Thao tác",
            hideWhenEmpty: true,
            render: (item) => (
              <span className="flex flex-wrap gap-2">
                <button
                  className="secondary-button"
                  type="button"
                  disabled={previewingId === item._id}
                  onClick={() => void previewDataSet(item)}
                >
                  {previewingId === item._id ? "Đang xem…" : "Xem dữ liệu mẫu"}
                </button>
                {can("testdata.update") && (
                  <button
                    className="secondary-button"
                    type="button"
                    disabled={Boolean(versioningId)}
                    onClick={() => void createDataSetVersion(item)}
                  >
                    Tạo phiên bản mới
                  </button>
                )}
                {can("testdata.archive") && (
                  <button
                    className="secondary-button"
                    type="button"
                    onClick={() => void archiveDataSet(item)}
                  >
                    Lưu trữ
                  </button>
                )}
              </span>
            ),
          },
        ]}
      />
      <Modal
        isOpen={Boolean(preview)}
        onClose={() => setPreview(null)}
        ariaLabel="Xem trước bộ dữ liệu kiểm thử"
        className="max-w-3xl"
      >
        <ModalHeader>
          <ModalTitle>
            {preview?.name} · phiên bản {preview?.version}
          </ModalTitle>
          <p className="mt-2 text-sm text-ink-muted">
            Đây là các tổ hợp biến mẫu. Giá trị bí mật không được hiển thị.
            {preview?.truncated ? " Danh sách đã được giới hạn ở 100 dòng." : ""}
          </p>
        </ModalHeader>
        <div className="space-y-4 p-5">
          {preview?.secret_names?.length > 0 && (
            <p className="break-words text-sm text-ink-muted">
              Tên tham chiếu bí mật: {preview.secret_names.join(", ")}
            </p>
          )}
          <DataTable
            items={
              previewKeys.length
                ? (preview?.items || []).map((item, index) => ({ ...item, _id: String(index) }))
                : []
            }
            empty="Bộ dữ liệu chưa có biến để xem trước"
            columns={previewKeys.map((key) => ({
              key,
              label: key,
              render: (item) => <StructuredValueView value={item[key]} />,
            }))}
          />
        </div>
      </Modal>
      <Modal
        isOpen={Boolean(versionEditor)}
        onClose={() => {
          if (!savingVersion) {
            setVersionEditor(null);
            setVersioningId("");
          }
        }}
        ariaLabel="Tạo phiên bản bộ dữ liệu mới"
        className="max-h-[94dvh] max-w-4xl overflow-y-auto"
      >
        <ModalHeader>
          <ModalTitle>Tạo phiên bản bộ dữ liệu mới</ModalTitle>
          <p className="mt-2 text-sm text-ink-muted">
            Tham chiếu bí mật đã lưu được che khi đọc. Khai báo lại những tham chiếu cần giữ; để
            trống sẽ loại bỏ chúng khỏi phiên bản mới.
          </p>
        </ModalHeader>
        {versionEditor && (
          <form className="space-y-4 p-5" onSubmit={saveDataSetVersion}>
            {versionError && <ErrorState message={versionError} />}
            <label className="field-label block">
              Tên bộ dữ liệu
              <input
                className="apple-input mt-2 w-full"
                name="name"
                required
                value={versionEditor.name}
                onChange={(event) =>
                  setVersionEditor((current) => ({ ...current, name: event.target.value }))
                }
              />
            </label>
            <div className="min-w-0 space-y-2">
              <p className="field-label">Biến dữ liệu</p>
              <StructuredValueEditor
                label="Biến dữ liệu"
                value={versionEditor.variables}
                fixedType="object"
                onChange={(variables) => setVersionEditor((current) => ({ ...current, variables }))}
              />
            </div>
            <div className="min-w-0 space-y-2">
              <p className="field-label">Tham chiếu đến bí mật</p>
              <StructuredValueEditor
                label="Tham chiếu đến bí mật"
                value={versionEditor.secretRefs}
                fixedType="object"
                onChange={(secretRefs) =>
                  setVersionEditor((current) => ({ ...current, secretRefs }))
                }
              />
            </div>
            <label className="field-label block">
              Lý do thay đổi
              <textarea
                className="apple-input mt-2 min-h-20 w-full"
                name="reason"
                required
                value={versionEditor.reason}
                onChange={(event) =>
                  setVersionEditor((current) => ({ ...current, reason: event.target.value }))
                }
              />
            </label>
            <div className="flex justify-end gap-2">
              <button
                className="secondary-button"
                type="button"
                disabled={savingVersion}
                onClick={() => {
                  setVersionEditor(null);
                  setVersioningId("");
                }}
              >
                Hủy
              </button>
              <button className="apple-button" type="submit" disabled={savingVersion}>
                {savingVersion ? "Đang tạo" : "Tạo phiên bản"}
              </button>
            </div>
          </form>
        )}
      </Modal>
    </Panel>
  );
}
