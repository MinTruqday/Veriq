import { useState } from "react";
import DataTable from "../../../components/DataTable";
import { Panel } from "../../../components/WorkspacePrimitives";
import { messageOf, valueLabel } from "../../../lib/testing";
import { testingApi } from "../../../services/testing.service";

export default function TestCaseTransferPanel({
  projectId,
  can,
  preview,
  setPreview,
  reload,
  onError,
}) {
  const [acceptIncomplete, setAcceptIncomplete] = useState(false);
  const [selectedIndexes, setSelectedIndexes] = useState([]);
  const [separateReasons, setSeparateReasons] = useState({});
  const [busy, setBusy] = useState(false);
  const exportCases = (format) => {
    testingApi.exportTestCases(projectId, format).catch((reason) => onError(messageOf(reason)));
  };
  const upload = async (event) => {
    const file = event.target.files?.[0];
    if (!file) return;
    try {
      setAcceptIncomplete(false);
      const result = await testingApi.uploadTestImport(projectId, file);
      setPreview(result);
      setSelectedIndexes(
        result.preview.flatMap((item, index) => (item.similar_cases?.length ? [] : [index])),
      );
      setSeparateReasons({});
    } catch (reason) {
      onError(messageOf(reason));
    }
  };
  const confirm = async () => {
    if (!selectedIndexes.length) {
      onError("Cần chọn ít nhất một ca kiểm thử để nhập");
      return;
    }
    if (selectedIndexes.some((index) => preview.preview[index].incomplete) && !acceptIncomplete) {
      onError(
        "Cần xác nhận sẽ bổ sung bước kiểm thử cho các ca nhập từ bản xuất chỉ có nội dung tóm tắt",
      );
      return;
    }
    const separateIndexes = selectedIndexes.filter(
      (index) => preview.preview[index].similar_cases?.length,
    );
    if (separateIndexes.some((index) => !separateReasons[index]?.trim())) {
      onError("Cần ghi lý do tạo ca riêng cho từng ca gần giống");
      return;
    }
    setBusy(true);
    try {
      await testingApi.confirmTestImport(preview._id, {
        selected_indexes: selectedIndexes,
        separate_indexes: separateIndexes,
        separate_reasons: separateReasons,
        accept_incomplete: acceptIncomplete,
      });
      setPreview(null);
      setSelectedIndexes([]);
      await reload();
    } catch (reason) {
      if (reason.code === "TEST_IMPORT_DUPLICATE_REVIEW_REQUIRED" && reason.details?.matches) {
        setPreview((current) => ({
          ...current,
          preview: current.preview.map((item, index) =>
            reason.details.matches[index]
              ? { ...item, similar_cases: reason.details.matches[index] }
              : item,
          ),
        }));
        setSelectedIndexes((current) => current.filter((index) => !reason.details.matches[index]));
      }
      onError(messageOf(reason));
    } finally {
      setBusy(false);
    }
  };

  return (
    <Panel
      title="Nhập và xuất ca kiểm thử"
      actions={
        <div className="flex flex-wrap gap-2">
          {can("testcase.export") && (
            <button className="secondary-button" type="button" onClick={() => exportCases("csv")}>
              Xuất CSV
            </button>
          )}
          {can("testcase.export") && (
            <button className="secondary-button" type="button" onClick={() => exportCases("xlsx")}>
              Xuất XLSX
            </button>
          )}
        </div>
      }
    >
      {can("testcase.import") && (
        <div className="space-y-4 p-5">
          <input
            className="apple-input"
            aria-label="Tệp ca kiểm thử CSV hoặc XLSX"
            type="file"
            accept=".csv,.xlsx"
            onChange={upload}
          />
          {preview && (
            <>
              <DataTable
                items={preview.preview.map((item, index) => ({ ...item, _id: index }))}
                empty="Tệp không có ca kiểm thử hợp lệ"
                columns={[
                  {
                    key: "selection",
                    label: "Nhập",
                    render: (item) => (
                      <input
                        type="checkbox"
                        aria-label={`Nhập ca kiểm thử dòng ${item._id + 1}`}
                        checked={selectedIndexes.includes(item._id)}
                        onChange={(event) =>
                          setSelectedIndexes((current) =>
                            event.target.checked
                              ? [...current, item._id]
                              : current.filter((index) => index !== item._id),
                          )
                        }
                      />
                    ),
                  },
                  { key: "title", label: "Tên" },
                  { key: "type", label: "Loại", render: (item) => valueLabel(item.type) },
                  {
                    key: "priority",
                    label: "Ưu tiên",
                    render: (item) => valueLabel(item.priority),
                  },
                  { key: "expected", label: "Kết quả mong đợi" },
                  {
                    key: "similar_cases",
                    label: "Ca gần giống",
                    render: (item) =>
                      item.similar_cases?.length
                        ? item.similar_cases
                            .map((match) =>
                              match.id.startsWith("preview:")
                                ? `Dòng ${Number(match.id.slice(8)) + 1} trong tệp`
                                : match.title || match.id,
                            )
                            .join("  ")
                        : "Không thấy ca gần giống",
                  },
                  {
                    key: "separate_reason",
                    label: "Lý do tạo riêng",
                    render: (item) =>
                      item.similar_cases?.length && selectedIndexes.includes(item._id) ? (
                        <input
                          className="apple-input"
                          aria-label={`Lý do tạo riêng ca kiểm thử dòng ${item._id + 1}`}
                          value={separateReasons[item._id] || ""}
                          onChange={(event) =>
                            setSeparateReasons((current) => ({
                              ...current,
                              [item._id]: event.target.value,
                            }))
                          }
                        />
                      ) : null,
                  },
                  {
                    key: "incomplete",
                    label: "Dữ liệu bước",
                    render: (item) =>
                      item.incomplete ? "Cần bổ sung bước và kết quả" : "Đã có bước và kết quả",
                  },
                ]}
              />
              {selectedIndexes.some((index) => preview.preview[index].incomplete) && (
                <label className="flex items-start gap-2 text-sm">
                  <input
                    type="checkbox"
                    checked={acceptIncomplete}
                    onChange={(event) => setAcceptIncomplete(event.target.checked)}
                  />
                  Tôi hiểu những ca chỉ có nội dung tóm tắt sẽ là bản nháp thiếu bước và kết quả
                  kiểm chứng cần bổ sung trước khi duyệt
                </label>
              )}
              <button
                className="apple-button"
                type="button"
                disabled={
                  busy ||
                  !selectedIndexes.length ||
                  (selectedIndexes.some((index) => preview.preview[index].incomplete) &&
                    !acceptIncomplete)
                }
                onClick={confirm}
              >
                Xác nhận nhập ca đã chọn
              </button>
            </>
          )}
        </div>
      )}
    </Panel>
  );
}
