import { useEffect, useRef, useState } from "react";
import DataTable from "../../../components/DataTable";
import { Panel, StatusPill } from "../../../components/WorkspacePrimitives";
import ContentOriginBadge from "@/shared/components/common/ContentOriginBadge";
import { messageOf } from "../../../lib/testing";
import { testingApi } from "../../../services/testing.service";

export default function ApiArtifactsPanel({
  projectId,
  can,
  ask,
  apiImport,
  setApiImport,
  artifacts,
  operations,
  compareFrom,
  setCompareFrom,
  compareTo,
  setCompareTo,
  difference,
  setDifference,
  onTestImportPreview,
  reload,
  onError,
}) {
  const [reviewArtifact, setReviewArtifact] = useState(null);
  const [selectedOperationIndexes, setSelectedOperationIndexes] = useState([]);
  const [reviewNote, setReviewNote] = useState("");
  const [reviewBusy, setReviewBusy] = useState(false);
  const [impactAnalysis, setImpactAnalysis] = useState(null);
  const [impactBusy, setImpactBusy] = useState(false);
  const impactBusyRef = useRef(false);
  const [comparisonBusy, setComparisonBusy] = useState(false);
  const comparisonBusyRef = useRef(false);
  const [automationRuns, setAutomationRuns] = useState([]);
  const [automationRunsError, setAutomationRunsError] = useState("");
  const confirmed = artifacts.filter((item) => item.status === "CONFIRMED");
  const canReadAutomationRuns = can("automation.read") || can("proposal.read");

  useEffect(() => {
    if (!canReadAutomationRuns || !confirmed.length) return undefined;
    let active = true;
    let pending = false;
    const refreshRuns = async () => {
      if (pending) return;
      pending = true;
      try {
        const runs = await testingApi.listAutomationRuns(projectId);
        if (active) {
          setAutomationRuns(runs || []);
          setAutomationRunsError("");
        }
      } catch (reason) {
        if (active) setAutomationRunsError(messageOf(reason));
      } finally {
        pending = false;
      }
    };
    void refreshRuns();
    const timer = window.setInterval(() => {
      if (document.visibilityState === "visible") void refreshRuns();
    }, 5000);
    return () => {
      active = false;
      window.clearInterval(timer);
    };
  }, [canReadAutomationRuns, confirmed.length, projectId]);

  const automationRunFor = (operation) => {
    const eventId = `api-operation:${operation._id}:r${operation.revision}`;
    return automationRuns.find(
      (run) =>
        run.trigger === "API_OPERATION_CONFIRMED" &&
        (run.source_event_id === eventId ||
          (!run.source_event_id && (run.target_artifact_ids || []).includes(operation._id))),
    );
  };
  const importArtifact = async (event) => {
    event.preventDefault();
    try {
      const source = await testingApi.importApiArtifact(projectId, apiImport);
      setReviewArtifact(source);
      setSelectedOperationIndexes([]);
      setReviewNote("");
      setApiImport((value) => ({ ...value, content: "" }));
      await reload();
    } catch (reason) {
      onError(messageOf(reason));
    }
  };
  const review = async (item) => {
    setReviewBusy(true);
    try {
      const source = await testingApi.getApiArtifact(item._id);
      setReviewArtifact(source);
      setSelectedOperationIndexes(
        source.status === "REVIEWED" ? source.selected_indexes || [] : [],
      );
      setReviewNote(source.review_note || "");
    } catch (reason) {
      onError(messageOf(reason));
    } finally {
      setReviewBusy(false);
    }
  };
  const submitReview = async () => {
    if (!reviewArtifact || !selectedOperationIndexes.length) {
      onError("Cần chọn ít nhất một thao tác API để rà soát");
      return;
    }
    setReviewBusy(true);
    try {
      await testingApi.reviewApiArtifact(reviewArtifact._id, {
        expected_revision: reviewArtifact.revision,
        selected_indexes: [...selectedOperationIndexes].sort((left, right) => left - right),
        review_note: reviewNote.trim(),
      });
      setReviewArtifact(null);
      setSelectedOperationIndexes([]);
      await reload();
    } catch (reason) {
      onError(messageOf(reason));
    } finally {
      setReviewBusy(false);
    }
  };
  const confirm = async (item) => {
    try {
      await testingApi.confirmApiArtifact(item._id, {
        expected_revision: item.revision,
        idempotency_key: crypto.randomUUID(),
      });
      await reload();
    } catch (reason) {
      onError(messageOf(reason));
    }
  };
  const archive = async (item) => {
    await ask({
      title: "Lưu trữ nguồn đặc tả API",
      description: item.filename,
      confirmLabel: "Lưu trữ",
      fields: [
        {
          name: "reason",
          label: "Lý do",
          initialValue: "Nguồn đặc tả không còn được sử dụng",
          required: true,
          multiline: true,
        },
      ],
      onConfirm: async (answer) => {
        try {
          await testingApi.archiveApiArtifact(item._id, {
            expected_revision: item.revision,
            reason: answer.reason,
          });
          await reload();
        } catch (reason) {
          throw new Error(messageOf(reason));
        }
      },
    });
  };
  const compare = async () => {
    if (comparisonBusyRef.current) return;
    comparisonBusyRef.current = true;
    setComparisonBusy(true);
    try {
      setDifference(await testingApi.diffApiArtifacts(projectId, compareFrom, compareTo));
    } catch (reason) {
      onError(messageOf(reason));
    } finally {
      comparisonBusyRef.current = false;
      setComparisonBusy(false);
    }
  };
  const analyzeImpact = async () => {
    if (impactBusyRef.current) return;
    impactBusyRef.current = true;
    setImpactBusy(true);
    try {
      const analysis = await testingApi.analyzeApiArtifactImpact(projectId, {
        from_artifact_id: compareFrom,
        to_artifact_id: compareTo,
      });
      setImpactAnalysis({
        fromArtifactId: compareFrom,
        toArtifactId: compareTo,
        affectedCount: analysis.affected_test_cases?.length || 0,
        newTestCount: analysis.new_test_requirements?.length || 0,
      });
    } catch (reason) {
      onError(messageOf(reason));
    } finally {
      impactBusyRef.current = false;
      setImpactBusy(false);
    }
  };
  const openTestImportPreview = async (operation) => {
    try {
      if (!operation.test_import_preview_id) return;
      onTestImportPreview(await testingApi.getTestImportPreview(operation.test_import_preview_id));
    } catch (reason) {
      onError(messageOf(reason));
    }
  };
  const refreshAutomationState = async () => {
    try {
      await reload();
      if (canReadAutomationRuns) {
        setAutomationRuns(await testingApi.listAutomationRuns(projectId));
        setAutomationRunsError("");
      }
    } catch (reason) {
      onError(messageOf(reason));
    }
  };

  return (
    <Panel title="OpenAPI và Postman">
      <div className="grid gap-5 p-5">
        {can("apiartifact.import") && (
          <form className="max-w-2xl space-y-4" onSubmit={importArtifact}>
            <label className="field-label">
              Loại nguồn
              <select
                className="apple-input mt-2"
                value={apiImport.format}
                onChange={(event) =>
                  setApiImport((value) => ({
                    ...value,
                    format: event.target.value,
                    filename: `${event.target.value}.json`,
                  }))
                }
              >
                <option value="openapi">OpenAPI</option>
                <option value="postman">Postman</option>
              </select>
            </label>
            <label className="field-label">
              JSON đặc tả
              <textarea
                className="apple-input mt-2 min-h-48 font-mono"
                required
                value={apiImport.content}
                onChange={(event) =>
                  setApiImport((value) => ({ ...value, content: event.target.value }))
                }
              />
            </label>
            <button className="secondary-button" type="submit">
              Tạo bản xem trước
            </button>
          </form>
        )}
        <div className="space-y-5">
          <DataTable
            items={artifacts}
            empty="Chưa có nguồn đặc tả API"
            columns={[
              { key: "filename", label: "Nguồn" },
              { key: "format", label: "Định dạng" },
              {
                key: "status",
                label: "Trạng thái",
                render: (item) => <StatusPill value={item.status} />,
              },
              {
                key: "preview_count",
                label: "Thao tác đã chọn",
                render: (item) =>
                  item.status === "PREVIEW_READY"
                    ? `Chưa rà soát trong ${item.preview_count}`
                    : `${item.selected_indexes?.length || 0} trong ${item.preview_count}`,
              },
              {
                key: "actions",
                label: "Xử lý",
                hideWhenEmpty: true,
                render: (item) => (
                  <div className="flex flex-wrap gap-2">
                    {["PREVIEW_READY", "REVIEWED"].includes(item.status) &&
                      can("apiartifact.review") && (
                        <button
                          className="secondary-button"
                          type="button"
                          disabled={reviewBusy}
                          onClick={() => review(item)}
                        >
                          {item.status === "REVIEWED" ? "Sửa rà soát" : "Xem và rà soát"}
                        </button>
                      )}
                    {item.status === "REVIEWED" && can("apiartifact.confirm") && (
                      <button
                        className="apple-button"
                        type="button"
                        disabled={reviewBusy || reviewArtifact?._id === item._id}
                        onClick={() => confirm(item)}
                      >
                        Xác nhận
                      </button>
                    )}
                    {item.status !== "ARCHIVED" && can("apiartifact.archive") && (
                      <button className="danger-button" type="button" onClick={() => archive(item)}>
                        Lưu trữ
                      </button>
                    )}
                  </div>
                ),
              },
            ]}
          />
          {reviewArtifact && (
            <section className="space-y-4 rounded-control border border-border p-4">
              <div className="flex flex-wrap items-center justify-between gap-3">
                <div>
                  <h3 className="font-medium">Rà soát thao tác API</h3>
                  <p className="text-sm text-ink-muted">{reviewArtifact.filename}</p>
                </div>
                <button
                  className="secondary-button"
                  type="button"
                  disabled={reviewBusy}
                  onClick={() => setReviewArtifact(null)}
                >
                  Đóng
                </button>
              </div>
              <div className="flex flex-wrap items-center gap-3 text-sm">
                <span>
                  Đã chọn {selectedOperationIndexes.length} trong {reviewArtifact.preview.length}{" "}
                  thao tác
                </span>
                <button
                  className="secondary-button"
                  type="button"
                  disabled={reviewBusy}
                  onClick={() =>
                    setSelectedOperationIndexes(reviewArtifact.preview.map((_, index) => index))
                  }
                >
                  Chọn tất cả
                </button>
                <button
                  className="secondary-button"
                  type="button"
                  disabled={reviewBusy}
                  onClick={() => setSelectedOperationIndexes([])}
                >
                  Bỏ chọn
                </button>
              </div>
              <div className="max-h-96 space-y-2 overflow-y-auto">
                {reviewArtifact.preview.map((operation, index) => (
                  <label
                    className="flex items-start gap-3 rounded-control border border-border p-3 text-sm"
                    key={index}
                  >
                    <input
                      type="checkbox"
                      aria-label={`Chọn thao tác ${operation.method} ${operation.path}`}
                      checked={selectedOperationIndexes.includes(index)}
                      disabled={reviewBusy}
                      onChange={(event) =>
                        setSelectedOperationIndexes((current) =>
                          event.target.checked
                            ? [...current, index]
                            : current.filter((value) => value !== index),
                        )
                      }
                    />
                    <span className="min-w-0">
                      <span className="block font-medium">
                        {operation.method} {operation.path}
                      </span>
                      <span className="block break-words">{operation.title}</span>
                      <span className="block text-ink-muted">
                        Phản hồi trong nguồn{" "}
                        {Object.keys(operation.responses || {}).join("  ") || "Chưa mô tả"}
                      </span>
                    </span>
                  </label>
                ))}
              </div>
              <label className="field-label block">
                Ghi chú rà soát
                <textarea
                  className="apple-input mt-2 min-h-20"
                  value={reviewNote}
                  disabled={reviewBusy}
                  onChange={(event) => setReviewNote(event.target.value)}
                />
              </label>
              <button
                className="apple-button"
                type="button"
                disabled={reviewBusy || !selectedOperationIndexes.length}
                onClick={submitReview}
              >
                Xác nhận phần đã chọn
              </button>
            </section>
          )}
          {confirmed.length >= 2 && (
            <div className="rounded-2xl border border-border p-4">
              <div className="grid gap-3 md:grid-cols-2">
                <label className="field-label">
                  Phiên bản trước
                  <select
                    className="apple-input mt-2"
                    value={compareFrom}
                    disabled={comparisonBusy || impactBusy}
                    onChange={(event) => {
                      setCompareFrom(event.target.value);
                      setImpactAnalysis(null);
                      setDifference(null);
                    }}
                  >
                    {confirmed.map((item) => (
                      <option key={item._id} value={item._id}>
                        {item.filename}
                      </option>
                    ))}
                  </select>
                </label>
                <label className="field-label">
                  Phiên bản sau
                  <select
                    className="apple-input mt-2"
                    value={compareTo}
                    disabled={comparisonBusy || impactBusy}
                    onChange={(event) => {
                      setCompareTo(event.target.value);
                      setImpactAnalysis(null);
                      setDifference(null);
                    }}
                  >
                    {confirmed.map((item) => (
                      <option key={item._id} value={item._id}>
                        {item.filename}
                      </option>
                    ))}
                  </select>
                </label>
              </div>
              <div className="mt-3 flex flex-wrap gap-2">
                <button
                  className="secondary-button"
                  disabled={
                    !compareFrom ||
                    !compareTo ||
                    compareFrom === compareTo ||
                    comparisonBusy ||
                    impactBusy
                  }
                  type="button"
                  onClick={compare}
                >
                  {comparisonBusy ? "Đang so sánh…" : "So sánh đặc tả"}
                </button>
                {can("impact.execute") && (
                  <button
                    className="secondary-button"
                    disabled={
                      !compareFrom ||
                      !compareTo ||
                      compareFrom === compareTo ||
                      comparisonBusy ||
                      impactBusy
                    }
                    type="button"
                    onClick={analyzeImpact}
                  >
                    {impactBusy ? "Đang tính ảnh hưởng…" : "Phân tích ảnh hưởng"}
                  </button>
                )}
              </div>
              {impactAnalysis &&
                impactAnalysis.fromArtifactId === compareFrom &&
                impactAnalysis.toArtifactId === compareTo && (
                  <p className="mt-3 text-sm text-ink-muted" role="status">
                    Đã ghi nhận {impactAnalysis.affectedCount} ca cần rà soát và{" "}
                    {impactAnalysis.newTestCount} thao tác API mới cần kiểm thử.
                  </p>
                )}
              {difference && (
                <p className="mt-3 text-sm text-ink-muted">
                  Thêm {difference.added.length} thay đổi {difference.changed.length} loại bỏ{" "}
                  {difference.removed.length}
                </p>
              )}
            </div>
          )}
          <DataTable
            items={operations}
            empty="Chưa có thao tác API đã xác nhận"
            columns={[
              { key: "method", label: "Phương thức" },
              { key: "path", label: "Đường dẫn" },
              { key: "title", label: "Tên" },
              {
                key: "automation",
                label: "Tự động hóa",
                render: (item) => {
                  const run = automationRunFor(item);
                  if (item.test_import_preview_id && can("testcase.import")) {
                    return (
                      <div className="flex flex-wrap items-center gap-2">
                        <StatusPill value={item.test_import_preview_status || "PREVIEW_READY"} />
                        <button
                          className="secondary-button"
                          type="button"
                          onClick={() => void openTestImportPreview(item)}
                        >
                          Xem và xử lý bản xem trước
                        </button>
                      </div>
                    );
                  }
                  return (
                    <div className="grid min-w-48 gap-2 text-sm text-ink-muted">
                      <div className="flex flex-wrap items-center gap-2">
                        {run ? (
                          <>
                            <StatusPill value={run.status} />
                            <span>Trạng thái lượt AI</span>
                          </>
                        ) : (
                          <span>
                            {item.automation_dispatch_status === "PENDING" ||
                            item.automation_dispatch_status === "DISPATCHING"
                              ? "Sự kiện đang chờ được chuyển tới AI"
                              : item.automation_dispatch_status === "DELIVERED"
                                ? "Đã gửi thông tin đến AI; đang chờ xử lý"
                                : item.automation_dispatch_status === "SUPPRESSED"
                                  ? "Luồng tự động hóa đang tắt"
                                  : "Chưa có trạng thái xử lý tự động"}
                          </span>
                        )}
                        {item.automation_dispatch_status !== "SUPPRESSED" && (
                          <button
                            className="text-accent underline underline-offset-2"
                            type="button"
                            onClick={() => void refreshAutomationState()}
                          >
                            Làm mới
                          </button>
                        )}
                      </div>
                      {run && (
                        <div className="grid gap-1">
                          {(run.error_code || run.result?.summary) && (
                            <div className="grid justify-items-start gap-1">
                              {run.result?.summary && <ContentOriginBadge origin="ai_generated" />}
                              <span className="break-words text-xs">
                                {run.error_code || run.result.summary}
                              </span>
                            </div>
                          )}
                          <a
                            className="text-accent underline underline-offset-2"
                            href={`/du-an/${projectId}/ca-kiem-thu/ai`}
                          >
                            Mở hoạt động AI
                          </a>
                        </div>
                      )}
                      {automationRunsError && canReadAutomationRuns && (
                        <span className="text-xs" role="status">
                          Chưa tải được trạng thái lượt AI: {automationRunsError}
                        </span>
                      )}
                    </div>
                  );
                },
              },
            ]}
          />
        </div>
      </div>
    </Panel>
  );
}
