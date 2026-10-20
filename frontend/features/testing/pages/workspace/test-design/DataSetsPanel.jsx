import DataTable from "../../../components/DataTable";
import { Panel } from "../../../components/WorkspacePrimitives";
import { messageOf } from "../../../lib/testing";
import { testingApi } from "../../../services/testing.service";
import DataSetCreateModal from "./DataSetCreateModal";

export default function DataSetsPanel({
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
  if (!canRead) return null;
  return (
    <Panel
      title="Bộ dữ liệu kiểm thử có phiên bản"
      actions={
        can("testcase.create") ? (
          <button className="secondary-button" type="button" onClick={() => setCreating(true)}>
            Tạo bộ dữ liệu
          </button>
        ) : null
      }
    >
      {can("testcase.create") && (
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
        onSelect={async (item) => {
          if (!can("testcase.update")) return;
          const answer = await ask({
            title: "Tạo phiên bản bộ dữ liệu mới",
            description: `${item.name} v${item.current_version?.version}`,
            confirmLabel: "Tạo phiên bản",
            fields: [
              {
                name: "name",
                label: "Tên bộ dữ liệu",
                initialValue: item.name,
                required: true,
                autoFocus: true,
              },
              {
                name: "variables",
                label: "Biến JSON",
                initialValue: JSON.stringify(item.current_version?.variables || {}, null, 2),
                required: true,
                multiline: true,
              },
              {
                name: "secretRefs",
                label: "Danh sách tham chiếu bí mật dạng JSON",
                initialValue: JSON.stringify(item.current_version?.secret_refs || {}, null, 2),
                required: true,
                multiline: true,
              },
              {
                name: "reason",
                label: "Lý do thay đổi",
                initialValue: "Cập nhật dữ liệu kiểm thử",
                required: true,
                multiline: true,
              },
            ],
          });
          if (!answer) return;
          try {
            await testingApi.createDataSetVersion(item._id, {
              expected_current_version_id: item.current_version_id,
              name: answer.name,
              variables: JSON.parse(answer.variables),
              secret_refs: JSON.parse(answer.secretRefs),
              change_reason: answer.reason,
            });
            await reload();
          } catch (reason) {
            onError(
              reason instanceof SyntaxError ? "Bộ dữ liệu phải là JSON hợp lệ" : messageOf(reason),
            );
          }
        }}
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
            render: (item) => Object.keys(item.current_version?.variables || {}).join(", "),
          },
          {
            key: "secret_refs",
            label: "Tham chiếu bí mật",
            render: (item) => Object.keys(item.current_version?.secret_refs || {}).join(", "),
          },
        ]}
      />
    </Panel>
  );
}
