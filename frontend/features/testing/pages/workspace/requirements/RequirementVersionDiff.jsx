import { StructuredValueView } from "../../../components/StructuredValueEditor";

const changeLabels = {
  ADD: "Được thêm",
  ADDED: "Được thêm",
  CREATE: "Được thêm",
  INSERT: "Được thêm",
  REMOVE: "Đã loại bỏ",
  REMOVED: "Đã loại bỏ",
  DELETE: "Đã loại bỏ",
  DELETED: "Đã loại bỏ",
  CHANGE: "Đã thay đổi",
  CHANGED: "Đã thay đổi",
  MODIFY: "Đã thay đổi",
  MODIFIED: "Đã thay đổi",
  UPDATE: "Đã thay đổi",
  UPDATED: "Đã thay đổi",
};

function changeLabel(type) {
  const normalized = String(type || "CHANGE").toUpperCase();
  return changeLabels[normalized] || "Khác biệt";
}

export default function RequirementVersionDiff({ changes = [], empty = "Không có khác biệt" }) {
  if (!changes.length) {
    return <p className="p-5 text-sm text-ink-muted">{empty}</p>;
  }

  return (
    <ol className="divide-y divide-border">
      {changes.map((item, index) => (
        <li className="p-4" key={item.id || item.field || index}>
          <div className="mb-3 flex flex-wrap items-center justify-between gap-2">
            <h3 className="text-sm font-semibold">{item.label || item.field || "Nội dung"}</h3>
            <span className="rounded-control border border-border px-2 py-1 text-xs font-medium text-ink-muted">
              {changeLabel(item.type)}
            </span>
          </div>
          <div className="grid min-w-0 gap-3 md:grid-cols-2">
            <section
              aria-label={`Giá trị trước: ${item.label || item.field || "Nội dung"}`}
              className="min-w-0 rounded-control border border-border bg-surface-quiet/50 p-3"
            >
              <p className="mb-2 text-xs font-semibold text-ink-muted">Phiên bản trước</p>
              <div className="min-w-0 break-words text-sm">
                <StructuredValueView value={item.before} />
              </div>
            </section>
            <section
              aria-label={`Giá trị mới: ${item.label || item.field || "Nội dung"}`}
              className="min-w-0 rounded-control border border-border p-3"
            >
              <p className="mb-2 text-xs font-semibold text-ink-muted">Phiên bản mới</p>
              <div className="min-w-0 break-words text-sm">
                <StructuredValueView value={item.after} />
              </div>
            </section>
          </div>
        </li>
      ))}
    </ol>
  );
}
