import { useEffect, useRef, useState } from "react";
import { Panel, StatusPill } from "../../../components/WorkspacePrimitives";
import ContentOriginBadge from "@/shared/components/common/ContentOriginBadge";
import { messageOf } from "../../../lib/testing";
import { agentRunErrorMessage } from "../../../lib/agentRun.logic";
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
  const [agentRuns, setAgentRuns] = useState([]);
  const [agentRunsError, setAgentRunsError] = useState("");
  const confirmed = artifacts.filter((item) => item.status === "CONFIRMED");
  const canReadAgentRuns = can("automation.read") || can("proposal.read");

  useEffect(() => {
    if (!canReadAgentRuns || !confirmed.length) return undefined;
    let active = true;
    let pending = false;
    const refreshRuns = async () => {
      if (pending) return;
      pending = true;
      try {
        const runs = await testingApi.listAgentRuns(projectId);
        if (active) {
          setAgentRuns(runs || []);
          setAgentRunsError("");
        }
      } catch (reason) {
        if (active) setAgentRunsError(messageOf(reason));
      } finally {
        pending = false;
      }
    };
    void refreshRuns();
    return () => {
      active = false;
    };
  }, [canReadAgentRuns, confirmed.length, projectId]);

  const agentRunFor = (operation) => {
    const eventId = `api-operation:${operation._id}:r${operation.revision}`;
    return agentRuns.find(
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
  const refreshAgentState = async () => {
    try {
      await reload();
      if (canReadAgentRuns) {
        setAgentRuns(await testingApi.listAgentRuns(projectId));
        setAgentRunsError("");
      }
    } catch (reason) {
      onError(messageOf(reason));
    }
  };

  return (
    <Panel title="OpenAPI và Postman">
      <div className="grid gap-5 p-5">
        {can("apiartifact.import") && (
          <details className="group rounded-lg border border-border">
            <summary className="cursor-pointer px-4 py-3 font-medium">
              Nhập nguồn đặc tả API
            </summary>
            <form
              className="max-w-3xl space-y-4 border-t border-border p-4"
              onSubmit={importArtifact}
            >
              <label className="field-label block max-w-sm">
                Định dạng
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
              <label className="field-label block">
                Nội dung JSON
                <textarea
                  className="apple-input mt-2 min-h-48 w-full font-mono"
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
          </details>
        )}
        <section className="space-y-3">
          <div className="flex flex-wrap items-baseline justify-between gap-2">
            <h3 className="font-semibold">Nguồn đặc tả</h3>
            <span className="text-[12px] text-ink-muted">{artifacts.length} nguồn</span>
          </div>
          {artifacts.length ? (
            <div className="divide-y divide-border border-t border-border">
              {artifacts.map((item) => (
                <article
                  className="grid min-w-0 gap-3 py-3 lg:grid-cols-[minmax(0,1fr)_auto] lg:items-center"
                  key={item._id}
                >
                  <div className="min-w-0">
                    <h4 className="break-all font-medium">{item.filename}</h4>
                    <div className="mt-1 flex flex-wrap items-center gap-x-3 gap-y-1 text-[12px] text-ink-muted">
                      <span>{item.format === "postman" ? "Postman" : "OpenAPI"}</span>
                      <StatusPill value={item.status} />
                      <span>
                        {item.status === "PREVIEW_READY"
                          ? `${item.preview_count} thao tác chưa rà soát`
                          : `${item.selected_indexes?.length || 0} / ${item.preview_count} thao tác được chọn`}
                      </span>
                    </div>
                  </div>
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
                        Xác nhận và gửi thao tác cho AI
                      </button>
                    )}
                    {item.status !== "ARCHIVED" && can("apiartifact.archive") && (
                      <button className="danger-button" type="button" onClick={() => archive(item)}>
                        Lưu trữ
                      </button>
                    )}
                  </div>
                </article>
              ))}
            </div>
          ) : (
            <p className="rounded-lg border border-dashed border-border px-4 py-6 text-sm text-ink-muted">
              Chưa có nguồn đặc tả API
            </p>
          )}
        </section>
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
                Đã chọn {selectedOperationIndexes.length} trong {reviewArtifact.preview.length} thao
                tác
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
          <section className="space-y-3 border-t border-border pt-5">
            <h3 className="font-semibold">So sánh phiên bản đặc tả</h3>
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
          </section>
        )}
        <section className="space-y-3 border-t border-border pt-5">
          <div className="flex flex-wrap items-center justify-between gap-2">
            <h3 className="font-semibold">Thao tác API đã xác nhận</h3>
            {canReadAgentRuns && confirmed.length > 0 && (
              <button
                className="secondary-button"
                type="button"
                onClick={() => void refreshAgentState()}
              >
                Cập nhật trạng thái AI
              </button>
            )}
          </div>
          {operations.length ? (
            <div className="divide-y divide-border border-b border-border">
              {operations.map((item) => {
                const run = agentRunFor(item);
                return (
                  <article
                    className="grid min-w-0 gap-3 py-4 lg:grid-cols-[minmax(0,1fr)_minmax(17rem,0.7fr)] lg:gap-6"
                    key={item._id}
                  >
                    <div className="min-w-0 space-y-2">
                      <div className="flex min-w-0 flex-wrap items-center gap-2">
                        <span className="rounded-md border border-border bg-surface-quiet px-2 py-1 font-mono text-[11px] font-semibold">
                          {item.method}
                        </span>
                        <code className="min-w-0 break-all text-[12px] text-ink-muted">
                          {item.path}
                        </code>
                      </div>
                      <h4 className="break-words text-[14px] font-medium leading-5">
                        {item.title}
                      </h4>
                      {item.test_import_preview_id && can("testcase.import") && (
                        <div className="flex flex-wrap items-center gap-2 pt-1">
                          <StatusPill value={item.test_import_preview_status || "PREVIEW_READY"} />
                          <button
                            className="secondary-button"
                            type="button"
                            onClick={() => void openTestImportPreview(item)}
                          >
                            Xem bản xem trước ca kiểm thử
                          </button>
                        </div>
                      )}
                    </div>
                    <div className="min-w-0 space-y-2 text-[13px] text-ink-muted">
                      <p className="text-[11px] font-semibold uppercase tracking-wide">AI</p>
                      {run ? (
                        <>
                          <StatusPill value={run.status} />
                          {(run.error_code || run.result?.summary) && (
                            <div className="grid justify-items-start gap-1">
                              {run.result?.summary && <ContentOriginBadge origin="ai_generated" />}
                              <span className="break-words">
                                {run.error_code
                                  ? agentRunErrorMessage(run.error_code)
                                  : run.result.summary}
                              </span>
                            </div>
                          )}
                          <a
                            className="block text-accent underline underline-offset-2"
                            href={`/du-an/${projectId}/ca-kiem-thu/ai`}
                          >
                            Xem hoạt động AI
                          </a>
                        </>
                      ) : (
                        <p>
                          {item.automation_dispatch_status === "PENDING" ||
                          item.automation_dispatch_status === "DISPATCHING"
                            ? "Đang gửi yêu cầu đến AI"
                            : item.automation_dispatch_status === "DELIVERED"
                              ? "Đã gửi yêu cầu đến AI"
                              : item.automation_dispatch_status === "SUPPRESSED"
                                ? "Chưa gửi yêu cầu đến AI"
                                : "Chưa có lượt AI"}
                        </p>
                      )}
                      {agentRunsError && canReadAgentRuns && (
                        <p role="status">Chưa tải được trạng thái AI: {agentRunsError}</p>
                      )}
                    </div>
                  </article>
                );
              })}
            </div>
          ) : (
            <p className="rounded-lg border border-dashed border-border px-4 py-6 text-sm text-ink-muted">
              Chưa có thao tác API đã xác nhận
            </p>
          )}
        </section>
      </div>
    </Panel>
  );
}
