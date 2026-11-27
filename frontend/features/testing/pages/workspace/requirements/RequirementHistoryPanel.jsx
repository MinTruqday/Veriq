import DataTable from "../../../components/DataTable";
import { Panel, StatusPill } from "../../../components/WorkspacePrimitives";
import { messageOf, valueLabel } from "../../../lib/testing";
import { testingApi } from "../../../services/testing.service";
import RequirementVersionDiff from "./RequirementVersionDiff";

export default function RequirementHistoryPanel({
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
      <Panel title="Lịch sử và ảnh hưởng thay đổi">
        <DataTable
          items={versions}
          columns={[
            {
              key: "version",
              label: "Phiên bản",
              align: "center",
              render: (item) => `v${item.version}`,
            },
            { key: "title", label: "Tên" },
            {
              key: "status",
              label: "Trạng thái",
              render: (item) =>
                item.status === "READY" ? "Đã lưu, chưa duyệt" : <StatusPill value={item.status} />,
            },
            {
              key: "created_at",
              label: "Ngày tạo phiên bản",
              render: (item) =>
                item.created_at && !Number.isNaN(new Date(item.created_at).getTime())
                  ? new Date(item.created_at).toLocaleDateString("vi-VN")
                  : "-",
            },
            {
              key: "change_reason",
              label: "Nội dung thay đổi",
              render: (item) =>
                item.details?.change_impact?.change ??
                (item.parent_version_id ? item.change_reason || "-" : "-"),
            },
            {
              key: "impact",
              label: "Ảnh hưởng",
              render: (item) => item.details?.change_impact?.impact || "-",
            },
            {
              key: "time",
              label: "Ảnh hưởng đến thời gian",
              render: (item) => item.details?.change_impact?.time || "-",
            },
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
        <Panel title="Đối chiếu hai phiên bản">
          <div className="flex flex-wrap items-center gap-2 border-b border-border px-4 py-3 text-xs text-ink-muted">
            <span>
              Phiên bản trước: v{versions.find((item) => item._id === compareFrom)?.version}
            </span>
            <span aria-hidden="true">→</span>
            <span>Phiên bản mới: v{versions.find((item) => item._id === compareTo)?.version}</span>
            <span className="ml-auto font-medium text-ink">
              {(comparison.changes || []).length} mục thay đổi
            </span>
          </div>
          <RequirementVersionDiff
            changes={comparison.changes || []}
            empty="Hai phiên bản không có khác biệt ngữ nghĩa."
          />
        </Panel>
      )}
    </>
  );
}
