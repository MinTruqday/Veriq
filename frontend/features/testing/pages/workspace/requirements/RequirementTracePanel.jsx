import DataTable from "../../../components/DataTable";
import { Panel } from "../../../components/WorkspacePrimitives";
import { valueLabel } from "../../../lib/testing";

export default function RequirementTracePanel({ current, sourceDocuments }) {
  return (
    <Panel title="Nguồn tài liệu">
      <DataTable
        items={(current.source_refs || []).map((item, index) => ({
          ...item,
          _id: `${item.requirement_document_id || "source"}-${index}`,
        }))}
        empty="Yêu cầu được tạo thủ công và chưa có nguồn tài liệu đính kèm"
        columns={[
          {
            key: "requirement_document_id",
            label: "Tài liệu",
            render: (item) => {
              const source = sourceDocuments.find(
                (document) => document._id === item.requirement_document_id,
              );
              return (
                <span className="break-words">
                  {source?.title || source?.filename || "Tài liệu nguồn không còn khả dụng"}
                </span>
              );
            },
          },
          { key: "format", label: "Định dạng", render: (item) => valueLabel(item.format) },
          {
            key: "location",
            label: "Vị trí",
            render: (item) =>
              item.source_start !== undefined
                ? `${item.source_start} đến ${item.source_end}`
                : item.candidate_index !== undefined
                  ? `Mục ${item.candidate_index + 1}`
                  : "Toàn bộ tài liệu",
          },
        ]}
      />
    </Panel>
  );
}
