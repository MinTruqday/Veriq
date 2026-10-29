import DataTable from "../../../components/DataTable";
import { Panel } from "../../../components/WorkspacePrimitives";

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
            render: (item) =>
              sourceDocuments.find((document) => document._id === item.requirement_document_id)
                ?.title ||
              sourceDocuments.find((document) => document._id === item.requirement_document_id)
                ?.filename ||
              item.requirement_document_id,
          },
          { key: "format", label: "Định dạng" },
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
