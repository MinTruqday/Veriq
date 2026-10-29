import DataTable from "./DataTable";
import { valueLabel } from "../lib/testing";

function groups(values) {
  return (values || []).map((item, index) => ({
    ...item,
    _id: item._id || `${item.artifact_type || item.type || "GROUP"}-${item.artifact_id || index}`,
  }));
}

export default function TestwareHandoverPanel({ handover = [], archived = [], environments = [] }) {
  return (
    <section className="space-y-5">
      <div>
        <h3 className="mb-3 font-semibold text-ink">Bàn giao tài sản kiểm thử</h3>
        <DataTable
          items={groups(handover)}
          empty="Chưa có tài sản kiểm thử cần bàn giao"
          columns={[
            {
              key: "artifact_type",
              label: "Loại",
              render: (item) => valueLabel(item.artifact_type || item.type),
            },
            {
              key: "artifact_id",
              label: "Tài sản",
              render: (item) =>
                item.artifact_key ||
                item.artifact_name ||
                item.artifact_title ||
                (Array.isArray(item.items) ? `${item.items.length} mục` : "Tài sản kiểm thử"),
            },
            { key: "handover_to", label: "Bàn giao cho" },
            { key: "storage_location", label: "Vị trí lưu trữ" },
            { key: "status", label: "Trạng thái", render: (item) => valueLabel(item.status) },
          ]}
        />
      </div>
      <div>
        <h3 className="mb-3 font-semibold text-ink">Tài sản lưu trữ</h3>
        <DataTable
          items={groups(archived)}
          empty="Không có tài sản lưu trữ"
          columns={[
            { key: "type", label: "Loại", render: (item) => valueLabel(item.type) },
            {
              key: "items",
              label: "Số lượng",
              render: (item) => (Array.isArray(item.items) ? item.items.length : 1),
            },
          ]}
        />
      </div>
      <div>
        <h3 className="mb-3 font-semibold text-ink">Đóng môi trường</h3>
        <DataTable
          items={groups(environments)}
          empty="Không có môi trường trong phạm vi"
          columns={[
            {
              key: "name",
              label: "Môi trường",
              render: (item) => item.name || "Môi trường không còn khả dụng",
            },
            {
              key: "availability",
              label: "Khả dụng",
              render: (item) => valueLabel(item.availability || item.status),
            },
            { key: "revision", label: "Phiên bản" },
          ]}
        />
      </div>
    </section>
  );
}
