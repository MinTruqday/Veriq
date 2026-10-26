import DataTable from "../../../components/DataTable";
import { Panel, StatusPill } from "../../../components/WorkspacePrimitives";
import { messageOf, valueLabel } from "../../../lib/testing";
import { testingApi } from "../../../services/testing.service";
import { StructuredValueView } from "../../../components/StructuredValueEditor";

export default function RequirementHistoryPanel({
  projectId,
  selected,
  versions,
  compareFrom,
  setCompareFrom,
  compareTo,
  setCompareTo,
  comparison,
  setComparison,
  onError,
}) {
  return (
    <>
      <Panel title="Lịch sử phiên bản">
        <DataTable
          items={versions}
          columns={[
            { key: "version", label: "Phiên bản", render: (item) => `v${item.version}` },
            { key: "title", label: "Tên" },
            {
              key: "status",
              label: "Trạng thái",
              render: (item) => <StatusPill value={item.status} />,
            },
            { key: "change_reason", label: "Lý do" },
          ]}
        />
        {versions.length > 1 && (
          <div className="flex flex-wrap gap-3 border-t border-border p-5">
            <select
              aria-label="Phiên bản gốc"
              className="apple-input min-w-48"
              value={compareFrom}
              onChange={(event) => setCompareFrom(event.target.value)}
            >
              {versions.map((item) => (
                <option key={item._id} value={item._id}>
                  v{item.version} {item.title}
                </option>
              ))}
            </select>
            <select
              aria-label="Phiên bản so sánh"
              className="apple-input min-w-48"
              value={compareTo}
              onChange={(event) => setCompareTo(event.target.value)}
            >
              {versions.map((item) => (
                <option key={item._id} value={item._id}>
                  v{item.version} {item.title}
                </option>
              ))}
            </select>
            <button
              className="secondary-button"
              type="button"
              disabled={!compareFrom || !compareTo || compareFrom === compareTo}
              onClick={async () => {
                try {
                  setComparison(
                    await testingApi.compareRequirement(selected._id, compareFrom, compareTo),
                  );
                } catch (reason) {
                  onError(messageOf(reason));
                }
              }}
            >
              So sánh phiên bản
            </button>
          </div>
        )}
      </Panel>
      {comparison && (
        <Panel
          title="Khác biệt phiên bản"
          actions={
            <button
              className="apple-button"
              type="button"
              onClick={async () => {
                try {
                  await testingApi.createChangeSet(selected._id, {
                    from_version_id: compareFrom,
                    to_version_id: compareTo,
                  });
                  window.location.assign(`/du-an/${projectId}/thay-doi`);
                } catch (reason) {
                  onError(messageOf(reason));
                }
              }}
            >
              Tạo bộ thay đổi
            </button>
          }
        >
          <DataTable
            items={comparison.changes.map((item, index) => ({ ...item, _id: index }))}
            empty="Hai phiên bản không có khác biệt ngữ nghĩa"
            columns={[
              {
                key: "type",
                label: "Loại thay đổi",
                render: (item) => valueLabel(item.type),
              },
              { key: "field", label: "Trường" },
              {
                key: "before",
                label: "Trước",
                render: (item) => <StructuredValueView value={item.before} />,
              },
              {
                key: "after",
                label: "Sau",
                render: (item) => <StructuredValueView value={item.after} />,
              },
            ]}
          />
        </Panel>
      )}
    </>
  );
}
