import { useState } from "react";
import DataTable from "../../../components/DataTable";
import { Panel } from "../../../components/WorkspacePrimitives";
import { messageOf } from "../../../lib/testing";
import { testingApi } from "../../../services/testing.service";
import { requirementFieldLabel, requirementSuggestionPreview } from "./requirements.model";

export default function RequirementQualityPanel({
  lint,
  current,
  selected,
  can,
  onSelectedChange,
  onLintChange,
  onError,
}) {
  const [applyingSuggestionId, setApplyingSuggestionId] = useState("");
  if (!lint) return null;
  return (
    <Panel
      title={
        lint.degraded_mode
          ? "Chưa thể xác minh chất lượng"
          : lint.valid
            ? "Kiểm tra chất lượng không có lỗi chặn"
            : "Kiểm tra chất lượng phát hiện vấn đề"
      }
    >
      <DataTable
        items={lint.findings}
        empty="Không có vấn đề"
        columns={[
          {
            key: "origin",
            label: "Nguồn",
            render: (item) => (item.origin === "AI" ? "AI" : "Quy tắc"),
          },
          { key: "severity", label: "Mức độ" },
          { key: "rule_id", label: "Mã" },
          { key: "message", label: "Nội dung" },
          { key: "suggestion", label: "Đề xuất" },
        ]}
      />
      {lint.degraded_mode && (
        <p className="mt-3 text-sm text-warning">
          Mô hình AI chưa sẵn sàng nên kết quả hiện chỉ gồm kiểm tra bằng quy tắc
        </p>
      )}
      <div className="mt-4">
        <DataTable
          items={lint.suggestions || []}
          empty="Chưa có đề xuất chỉnh sửa có đủ căn cứ"
          columns={[
            {
              key: "suggestion",
              label: "Bản vá đề xuất",
              render: (item) => (
                <dl className="space-y-2">
                  {requirementSuggestionPreview(item).map(([label, value]) => (
                    <div key={label}>
                      <dt className="field-label">{label}</dt>
                      <dd className="mt-1 whitespace-pre-wrap text-sm">{value}</dd>
                    </div>
                  ))}
                </dl>
              ),
            },
            {
              key: "target_fields",
              label: "Trường được cập nhật",
              render: (item) =>
                item.target_fields?.map(requirementFieldLabel).filter(Boolean).join(" · ") ||
                "Nội dung",
            },
            { key: "rationale", label: "Cơ sở" },
            {
              key: "actions",
              label: "Thao tác",
              hideWhenEmpty: true,
              render: (item) =>
                current.status === "DRAFT" && can("requirement.update") ? (
                  <button
                    className="apple-button"
                    type="button"
                    disabled={Boolean(applyingSuggestionId)}
                    onClick={async () => {
                      setApplyingSuggestionId(item.suggestion_id);
                      try {
                        await testingApi.applyRequirementAiSuggestion(current._id, {
                          expected_revision: current.revision,
                          ai_result_id: lint._id,
                          suggestion_id: item.suggestion_id,
                        });
                        const updatedRequirement = await testingApi.getRequirement(selected._id);
                        onSelectedChange(updatedRequirement);
                        onLintChange(
                          await testingApi.lintRequirement(updatedRequirement.current_version._id, {
                            idempotency_key: crypto.randomUUID(),
                            instruction:
                              "Kiểm tra lại bản đã áp dụng và chỉ trả về kết quả cuối cùng",
                          }),
                        );
                      } catch (reason) {
                        onError(messageOf(reason));
                      } finally {
                        setApplyingSuggestionId("");
                      }
                    }}
                  >
                    {applyingSuggestionId === item.suggestion_id
                      ? "Đang áp dụng và kiểm tra lại"
                      : "Áp dụng vào bản nháp"}
                  </button>
                ) : null,
            },
          ]}
        />
      </div>
    </Panel>
  );
}
