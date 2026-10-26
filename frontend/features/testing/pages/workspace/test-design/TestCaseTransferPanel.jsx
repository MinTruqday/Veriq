import { useEffect, useRef, useState } from "react";
import FilePicker from "../../../components/FilePicker";
import { Panel } from "../../../components/WorkspacePrimitives";
import { messageOf, valueLabel } from "../../../lib/testing";
import { testingApi } from "../../../services/testing.service";

const relevantImportMatches = (item, selectedIndexes) =>
  (item.similar_cases || []).filter(
    (match) =>
      !match.id.startsWith("preview:") ||
      selectedIndexes.includes(Number(match.id.slice("preview:".length))),
  );

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
  const [versionResolutions, setVersionResolutions] = useState({});
  const [busy, setBusy] = useState(false);
  const [fileResetKey, setFileResetKey] = useState(0);
  const initializedPreviewId = useRef(null);
  const previousProjectId = useRef(projectId);
  const projectScope = useRef({ projectId, epoch: 0 });
  if (projectScope.current.projectId !== projectId) {
    projectScope.current = { projectId, epoch: projectScope.current.epoch + 1 };
  }
  useEffect(() => {
    if (previousProjectId.current === projectId) return;
    previousProjectId.current = projectId;
    initializedPreviewId.current = null;
    setPreview(null);
    setAcceptIncomplete(false);
    setSelectedIndexes([]);
    setSeparateReasons({});
    setVersionResolutions({});
    setFileResetKey((current) => current + 1);
  }, [projectId, setPreview]);
  useEffect(() => {
    if (!preview?._id || initializedPreviewId.current === preview._id) return;
    initializedPreviewId.current = preview._id;
    setAcceptIncomplete(false);
    setSelectedIndexes(
      preview.preview.reduce(
        (selected, item, index) =>
          relevantImportMatches(item, selected).length ? selected : [...selected, index],
        [],
      ),
    );
    setSeparateReasons({});
    setVersionResolutions({});
  }, [preview]);
  const exportCases = (format) => {
    testingApi.exportTestCases(projectId, format).catch((reason) => onError(messageOf(reason)));
  };
  const upload = async (event) => {
    const input = event.target;
    const file = input.files?.[0];
    if (!file || busy) return;
    const requestScope = projectScope.current;
    setBusy(true);
    try {
      const result = await testingApi.uploadTestImport(requestScope.projectId, file);
      if (projectScope.current.epoch === requestScope.epoch) setPreview(result);
    } catch (reason) {
      onError(messageOf(reason));
    } finally {
      input.value = "";
      setFileResetKey((current) => current + 1);
      setBusy(false);
    }
  };
  const confirm = async () => {
    if (!selectedIndexes.length) {
      onError("Cần chọn ít nhất một ca kiểm thử để nhập");
      return;
    }
    if (selectedIndexes.some((index) => preview.preview[index].incomplete) && !acceptIncomplete) {
      onError("Cần xác nhận sẽ bổ sung dữ liệu kiểm thử cụ thể cho các ca còn thiếu");
      return;
    }
    const separateIndexes = selectedIndexes.filter(
      (index) =>
        relevantImportMatches(preview.preview[index], selectedIndexes).length &&
        !versionResolutions[index]?.target_version_id,
    );
    if (separateIndexes.some((index) => (separateReasons[index] || "").trim().length < 2)) {
      onError("Cần ghi lý do tạo ca riêng cho từng ca gần giống");
      return;
    }
    const selectedVersions = Object.fromEntries(
      selectedIndexes
        .filter((index) => versionResolutions[index]?.target_version_id)
        .map((index) => [index, versionResolutions[index]]),
    );
    if (Object.values(selectedVersions).some((item) => (item.reason || "").trim().length < 2)) {
      onError("Cần ghi lý do tạo phiên bản mới cho từng ca được cập nhật");
      return;
    }
    if (
      new Set(Object.values(selectedVersions).map((item) => item.target_version_id)).size !==
      Object.keys(selectedVersions).length
    ) {
      onError("Không thể tạo nhiều phiên bản cho cùng một ca trong một lượt nhập");
      return;
    }
    setBusy(true);
    try {
      await testingApi.confirmTestImport(preview._id, {
        selected_indexes: selectedIndexes,
        separate_indexes: separateIndexes,
        separate_reasons: separateReasons,
        version_resolutions: selectedVersions,
        accept_incomplete: acceptIncomplete,
      });
      setPreview(null);
      setSelectedIndexes([]);
      setVersionResolutions({});
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
              Xuất danh sách CSV
            </button>
          )}
          {can("testcase.export") && (
            <button className="secondary-button" type="button" onClick={() => exportCases("xlsx")}>
              Xuất danh sách XLSX
            </button>
          )}
        </div>
      }
    >
      {can("testcase.import") && (
        <div className="space-y-4 p-5">
          <p className="text-sm text-ink-muted">
            Tệp xuất giữ cấu trúc ca kiểm thử để có thể nhập lại thành bản nháp và đối chiếu trùng
            trước khi xác nhận
          </p>
          <FilePicker
            buttonLabel="Tải tệp ca kiểm thử CSV hoặc XLSX"
            accept=".csv,.xlsx"
            disabled={busy}
            resetKey={fileResetKey}
            onChange={upload}
          />
          {preview && (
            <>
              {preview.format === "api_operation" && (
                <p className="text-sm text-ink-muted">
                  Bản xem trước từ {preview.filename} chưa được lưu thành ca kiểm thử
                </p>
              )}
              <div className="space-y-3">
                {preview.preview.map((item, index) => {
                  const matches = relevantImportMatches(item, selectedIndexes);
                  const existing = matches.filter((match) => match.target_version_id);
                  const selected = selectedIndexes.includes(index);
                  return (
                    <div className="space-y-3 rounded-control border border-border p-4" key={index}>
                      <label className="flex items-start gap-3">
                        <input
                          type="checkbox"
                          aria-label={`Nhập ca kiểm thử dòng ${index + 1}`}
                          checked={selected}
                          onChange={(event) =>
                            setSelectedIndexes((current) =>
                              event.target.checked
                                ? [...current, index]
                                : current.filter((value) => value !== index),
                            )
                          }
                        />
                        <span className="min-w-0 break-words font-medium">
                          Dòng {index + 1} {item.title}
                        </span>
                      </label>
                      <div className="grid gap-2 text-sm sm:grid-cols-2">
                        <p>Loại {valueLabel(item.type)}</p>
                        <p>Ưu tiên {valueLabel(item.priority)}</p>
                        <p className="break-words">Kết quả mong đợi {item.expected}</p>
                        <p>
                          Truy vết yêu cầu{" "}
                          {item.draft?.requirement_version_ids?.length
                            ? "Đã liên kết"
                            : "Cần liên kết yêu cầu"}
                        </p>
                        <p>
                          Dữ liệu bước{" "}
                          {item.incomplete
                            ? preview.format === "api_operation"
                              ? "Cần bổ sung bước và dữ liệu đầu vào"
                              : "Cần bổ sung bước và kết quả"
                            : "Đã có bước và kết quả"}
                        </p>
                      </div>
                      {matches.length > 0 && (
                        <p className="break-words text-sm text-ink-muted">
                          Ca gần giống{" "}
                          {matches
                            .map((match) =>
                              match.id.startsWith("preview:")
                                ? `Dòng ${Number(match.id.slice(8)) + 1} trong tệp`
                                : match.target_version_id
                                  ? match.title || match.id
                                  : `${match.title || match.id} bản nháp chưa duyệt`,
                            )
                            .join("  ")}
                        </p>
                      )}
                      {selected && matches.length > 0 && (
                        <div className="grid gap-3 sm:grid-cols-2">
                          <label className="field-label">
                            Cách xử lý
                            <select
                              className="apple-input mt-2 w-full"
                              aria-label={`Cách xử lý ca kiểm thử dòng ${index + 1}`}
                              value={versionResolutions[index]?.target_version_id || ""}
                              onChange={(event) =>
                                setVersionResolutions((current) => ({
                                  ...current,
                                  [index]: {
                                    target_version_id: event.target.value,
                                    reason: current[index]?.reason || "",
                                  },
                                }))
                              }
                            >
                              <option value="">Tạo ca riêng</option>
                              {existing.map((match) => (
                                <option value={match.target_version_id} key={match.id}>
                                  Tạo phiên bản mới của {match.title || match.id}
                                </option>
                              ))}
                            </select>
                          </label>
                          <label className="field-label">
                            Lý do xử lý
                            <input
                              className="apple-input mt-2 w-full"
                              aria-label={`Lý do xử lý ca kiểm thử dòng ${index + 1}`}
                              value={
                                versionResolutions[index]?.target_version_id
                                  ? versionResolutions[index]?.reason || ""
                                  : separateReasons[index] || ""
                              }
                              onChange={(event) =>
                                versionResolutions[index]?.target_version_id
                                  ? setVersionResolutions((current) => ({
                                      ...current,
                                      [index]: { ...current[index], reason: event.target.value },
                                    }))
                                  : setSeparateReasons((current) => ({
                                      ...current,
                                      [index]: event.target.value,
                                    }))
                              }
                            />
                          </label>
                        </div>
                      )}
                    </div>
                  );
                })}
              </div>
              {selectedIndexes.some((index) => preview.preview[index].incomplete) && (
                <label className="flex items-start gap-2 text-sm">
                  <input
                    type="checkbox"
                    checked={acceptIncomplete}
                    onChange={(event) => setAcceptIncomplete(event.target.checked)}
                  />
                  Tôi hiểu các ca này còn thiếu bước hoặc dữ liệu kiểm thử cụ thể và cần bổ sung
                  trước khi duyệt
                </label>
              )}
              {selectedIndexes.some(
                (index) => !preview.preview[index].draft?.requirement_version_ids?.length,
              ) && (
                <p className="text-sm text-ink-muted">
                  Ca chưa liên kết yêu cầu cần được bổ sung truy vết trước khi gửi duyệt
                </p>
              )}
              {selectedIndexes.some((index) => versionResolutions[index]?.target_version_id) && (
                <p className="text-sm text-ink-muted">
                  Phiên bản mới chỉ là bản nháp Dữ liệu nhập cần được rà soát và phê duyệt trước khi
                  thay phiên bản hiện hành
                </p>
              )}
              <button
                className="apple-button"
                type="button"
                disabled={
                  busy ||
                  !selectedIndexes.length ||
                  selectedIndexes.some(
                    (index) =>
                      relevantImportMatches(preview.preview[index], selectedIndexes).length &&
                      (versionResolutions[index]?.target_version_id
                        ? (versionResolutions[index]?.reason || "").trim().length < 2
                        : (separateReasons[index] || "").trim().length < 2),
                  ) ||
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
