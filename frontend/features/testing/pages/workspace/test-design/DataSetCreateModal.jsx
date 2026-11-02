import { useEffect, useState } from "react";
import { LoaderCircle, Sparkles } from "lucide-react";
import { Modal, ModalHeader, ModalTitle } from "@/shared/components/ui/Modal";
import ContentOriginBadge from "@/shared/components/common/ContentOriginBadge";
import StructuredValueEditor from "../../../components/StructuredValueEditor";
import { ErrorState } from "../../../components/WorkspacePrimitives";
import { messageOf } from "../../../lib/testing";
import { testingApi } from "../../../services/testing.service";

export default function DataSetCreateModal({
  projectId,
  requirements,
  can,
  isOpen,
  onClose,
  form,
  setForm,
  saving,
  onSubmit,
}) {
  const [selectedRequirementIds, setSelectedRequirementIds] = useState([]);
  const [instruction, setInstruction] = useState("");
  const [suggestions, setSuggestions] = useState([]);
  const [evidenceLabels, setEvidenceLabels] = useState({});
  const [suggestionWarnings, setSuggestionWarnings] = useState([]);
  const [selectedSuggestionIndexes, setSelectedSuggestionIndexes] = useState([]);
  const [suggesting, setSuggesting] = useState(false);
  const [suggestionError, setSuggestionError] = useState("");
  useEffect(() => {
    if (isOpen) return;
    setSelectedRequirementIds([]);
    setInstruction("");
    setSuggestions([]);
    setEvidenceLabels({});
    setSuggestionWarnings([]);
    setSelectedSuggestionIndexes([]);
    setSuggestionError("");
  }, [isOpen, projectId]);
  const update = (patch) => setForm((value) => ({ ...value, ...patch }));
  const suggest = async () => {
    if (!selectedRequirementIds.length || suggesting) return;
    setSuggesting(true);
    setSuggestionError("");
    setSuggestions([]);
    setSelectedSuggestionIndexes([]);
    try {
      const result = await testingApi.suggestTestData(projectId, {
        requirement_version_ids: selectedRequirementIds,
        instruction: instruction.trim(),
      });
      setSuggestions(result.suggestions || []);
      setEvidenceLabels(result.evidence_labels || {});
      setSuggestionWarnings(result.warnings || []);
    } catch (error) {
      setSuggestionError(messageOf(error));
    } finally {
      setSuggesting(false);
    }
  };
  const applySuggestions = () => {
    const selected = selectedSuggestionIndexes.map((index) => suggestions[index]).filter(Boolean);
    if (!selected.length) return;
    const variables = { ...(form.variables || {}) };
    for (const item of selected) variables[item.variable_name] = item.values;
    update({
      name: form.name || "Dữ liệu kiểm thử từ gợi ý AI",
      variables,
      generationSource: "AI_ASSISTED",
      sourceRequirementVersionIds: selectedRequirementIds,
    });
  };

  return (
    <Modal
      isOpen={isOpen}
      onClose={() => {
        if (!saving) onClose();
      }}
      ariaLabel="Tạo bộ dữ liệu"
      className="max-w-2xl max-h-[90dvh] overflow-y-auto"
    >
      <ModalHeader>
        <ModalTitle>Tạo bộ dữ liệu</ModalTitle>
      </ModalHeader>
      <form className="grid min-w-0 gap-3 p-5" onSubmit={onSubmit}>
        {can("testdata.create") && (
          <section className="grid min-w-0 gap-3 rounded-control border border-border p-4">
            <div>
              <h3 className="font-medium">Đề xuất dữ liệu từ yêu cầu</h3>
              <p className="mt-1 text-sm text-ink-muted">
                Chỉ tạo giá trị mẫu để bạn xem và chọn. AI không lưu bộ dữ liệu và không tạo mật
                khẩu, thông tin cá nhân thật hoặc khóa bí mật.
              </p>
            </div>
            <label className="field-label min-w-0">
              Yêu cầu đã duyệt làm căn cứ
              <select
                className="apple-input mt-2 min-h-28 w-full"
                multiple
                value={selectedRequirementIds}
                disabled={suggesting || saving}
                onChange={(event) => {
                  setSelectedRequirementIds(
                    Array.from(event.target.selectedOptions, (option) => option.value),
                  );
                  setSuggestions([]);
                  setEvidenceLabels({});
                  setSuggestionWarnings([]);
                  setSelectedSuggestionIndexes([]);
                }}
              >
                {requirements.map((item) => (
                  <option key={item.current_version_id} value={item.current_version_id}>
                    {item.requirement_key} · {item.current_version?.title || "Không có tiêu đề"}
                  </option>
                ))}
              </select>
              <span className="mt-1 block text-xs font-normal text-ink-muted">
                Giữ Ctrl hoặc Command để chọn nhiều yêu cầu.
              </span>
            </label>
            <label className="field-label min-w-0">
              Hướng dẫn bổ sung (không bắt buộc)
              <textarea
                className="apple-input mt-2 min-h-20 w-full"
                maxLength={3000}
                value={instruction}
                disabled={suggesting || saving}
                onChange={(event) => {
                  setInstruction(event.target.value);
                  setSuggestions([]);
                  setEvidenceLabels({});
                  setSuggestionWarnings([]);
                  setSelectedSuggestionIndexes([]);
                }}
                placeholder="Ví dụ: ưu tiên trường hợp biên được nêu trong yêu cầu"
              />
            </label>
            {suggestionError && <ErrorState message={suggestionError} />}
            {suggestionWarnings.length > 0 && (
              <ul className="list-disc space-y-1 pl-5 text-sm text-ink-muted">
                {suggestionWarnings.map((warning, index) => (
                  <li key={`${warning}-${index}`}>{warning}</li>
                ))}
              </ul>
            )}
            <div>
              <button
                className="secondary-button inline-flex items-center gap-2"
                type="button"
                disabled={!selectedRequirementIds.length || suggesting || saving}
                onClick={() => void suggest()}
              >
                {suggesting ? (
                  <LoaderCircle aria-hidden="true" className="animate-spin" size={16} />
                ) : (
                  <Sparkles aria-hidden="true" size={16} />
                )}
                {suggesting ? "Đang đề xuất" : "Đề xuất dữ liệu"}
              </button>
            </div>
            {suggestions.length > 0 && (
              <div className="grid min-w-0 gap-3 border-t border-border pt-3">
                <p className="text-sm text-ink-muted">
                  Kiểm tra căn cứ trước khi chọn. Các giá trị dưới đây là dữ liệu tổng hợp, chưa
                  được xác nhận trên hệ thống thật.
                </p>
                {suggestions.map((item, index) => (
                  <label
                    className="grid min-w-0 grid-cols-[auto_minmax(0,1fr)] gap-3 rounded-control border border-border p-3"
                    key={`${item.variable_name}-${index}`}
                  >
                    <input
                      type="checkbox"
                      checked={selectedSuggestionIndexes.includes(index)}
                      disabled={saving}
                      onChange={(event) =>
                        setSelectedSuggestionIndexes((current) =>
                          event.target.checked
                            ? [...current, index]
                            : current.filter((value) => value !== index),
                        )
                      }
                    />
                    <div className="min-w-0 break-words text-sm">
                      <div className="flex flex-wrap items-center gap-2">
                        <strong>{item.variable_name}</strong>
                        <ContentOriginBadge origin="ai_generated" />
                      </div>
                      <p className="mt-1 text-ink-muted">{item.purpose}</p>
                      <p className="mt-2 text-xs font-medium text-ink-muted">Đang có</p>
                      <p className="mt-1 whitespace-pre-wrap">
                        {Array.isArray(form.variables?.[item.variable_name])
                          ? form.variables[item.variable_name].join(", ")
                          : String(form.variables?.[item.variable_name] ?? "").trim() ||
                            "Chưa có giá trị"}
                      </p>
                      <p className="mt-2 text-xs font-medium text-violet-800">AI đề xuất</p>
                      <span className="mt-1 block text-ink-muted">
                        {{ positive: "Hợp lệ", negative: "Không hợp lệ", boundary: "Biên" }[
                          item.category
                        ] || "Đề xuất"}{" "}
                        ·{" "}
                        {{
                          text: "Chữ",
                          integer: "Số nguyên",
                          decimal: "Số thập phân",
                          boolean: "Đúng/Sai",
                          date: "Ngày",
                          enum: "Danh sách lựa chọn",
                        }[item.value_type] || "Giá trị"}
                        : {item.values.join(", ")}
                      </span>
                      <span className="mt-1 block text-xs text-ink-muted">
                        {(item.evidence_quotes || [])
                          .map((quote) => {
                            const source = evidenceLabels[quote.evidence_ref];
                            return source ? `${source}: ${quote.quote}` : quote.quote;
                          })
                          .join(" · ")}
                      </span>
                    </div>
                  </label>
                ))}
                <button
                  className="secondary-button justify-self-start"
                  type="button"
                  disabled={!selectedSuggestionIndexes.length || saving}
                  onClick={applySuggestions}
                >
                  Dùng các giá trị đã chọn
                </button>
              </div>
            )}
          </section>
        )}
        <label className="field-label min-w-0">
          Tên bộ dữ liệu
          <input
            className="apple-input mt-2 w-full min-w-0"
            required
            value={form.name}
            onChange={(event) => update({ name: event.target.value })}
          />
        </label>
        <div className="min-w-0 space-y-2">
          <p className="field-label">Biến dữ liệu</p>
          <StructuredValueEditor
            label="Biến dữ liệu"
            value={form.variables || {}}
            fixedType="object"
            onChange={(variables) => update({ variables })}
          />
          <span
            id="dataset-variables-help"
            className="mt-1 block text-xs font-normal text-ink-muted"
          >
            Khai báo dữ liệu kiểm thử theo cặp tên và giá trị. Không nhập mật khẩu, mã truy cập hoặc
            khóa bí mật ở đây.
          </span>
        </div>
        <div className="min-w-0 space-y-2">
          <p className="field-label">Tham chiếu đến bí mật</p>
          <StructuredValueEditor
            label="Tham chiếu đến bí mật"
            value={form.secretRefs || {}}
            fixedType="object"
            onChange={(secretRefs) => update({ secretRefs })}
          />
          <span
            id="dataset-secret-refs-help"
            className="mt-1 block text-xs font-normal text-ink-muted"
          >
            Dùng địa chỉ bắt đầu bằng <code>secret://</code>; không nhập giá trị bí mật trực tiếp.
          </span>
        </div>
        <div className="action-dialog-footer flex justify-end gap-3">
          <button className="secondary-button" type="button" disabled={saving} onClick={onClose}>
            Hủy
          </button>
          <button className="apple-button" type="submit" disabled={saving}>
            {saving ? "Đang tạo" : "Tạo bộ dữ liệu"}
          </button>
        </div>
      </form>
    </Modal>
  );
}
