import DataTable from "./DataTable";

export default function PlanVsActualPanel({ snapshot }) {
  const metrics = snapshot?.metrics || {};
  const rows = [
    {
      metric: "Số lượt kiểm thử",
      planned: metrics.planned_test_count,
      actual: metrics.executed_test_count,
    },
    { metric: "Nỗ lực giờ", planned: metrics.planned_effort, actual: metrics.actual_effort },
    { metric: "Ngày bắt đầu", planned: metrics.planned_start, actual: metrics.actual_start },
    {
      metric: "Ngày hoàn thành dự kiến",
      planned: metrics.planned_end,
      actual: metrics.expected_completion,
    },
  ];
  const display = (value) =>
    value == null || value === ""
      ? "Chưa có"
      : typeof value === "string" && value.includes("T")
        ? new Date(value).toLocaleString("vi-VN")
        : String(value);
  return (
    <DataTable
      items={snapshot ? rows : []}
      empty="Chưa có bản ghi kế hoạch và kết quả để đối chiếu"
      columns={[
        { key: "metric", label: "Chỉ số" },
        { key: "planned", label: "Kế hoạch", render: (item) => display(item.planned) },
        { key: "actual", label: "Thực tế", render: (item) => display(item.actual) },
      ]}
    />
  );
}
