import DataTable from "../../../components/DataTable";
import { Panel } from "../../../components/WorkspacePrimitives";
import { valueLabel } from "../../../lib/testing";

export default function RequirementDuplicatePanel({ result }) {
  if (!result) return null;

  return (
    <Panel
      title="Ứng viên yêu cầu trùng lặp"
      actions={
        <span className="text-[12px] text-ink-muted">
          {result.candidate_count} cặp cần đối chiếu
        </span>
      }
    >
      <DataTable
        items={(result.candidates || []).map((item, index) => ({
          ...item,
          _id: `${item.left_requirement_id}-${item.right_requirement_id}-${index}`,
        }))}
        empty="Không phát hiện cặp yêu cầu vượt ngưỡng trùng lặp"
        columns={[
          { key: "left_requirement_label", label: "Yêu cầu thứ nhất" },
          { key: "right_requirement_label", label: "Yêu cầu thứ hai" },
          {
            key: "match_type",
            label: "Loại khớp",
            render: (item) => valueLabel(item.match_type),
          },
          {
            key: "score",
            label: "Điểm",
            render: (item) => `${Math.round(item.score * 100)}%`,
          },
          { key: "reasons", label: "Cơ sở", render: (item) => item.reasons.join(" · ") },
        ]}
      />
    </Panel>
  );
}
