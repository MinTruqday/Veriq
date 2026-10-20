import { uploadAssetAPI } from "@/features/cloud/services/upload.service";
import DataTable from "../../../components/DataTable";
import FilePicker from "../../../components/FilePicker";
import {
  ErrorState,
  Panel,
  ProjectCrumb,
  StatusPill,
  WorkspacePage,
} from "../../../components/WorkspacePrimitives";
import { docText, messageOf, valueLabel } from "../../../lib/testing";
import { testingApi } from "../../../services/testing.service";

export default function RunExecutionWorkspace({
  run,
  projectId,
  error,
  can,
  resumeContext,
  onResumeChange,
  ask,
  onRunChange,
  onError,
  onTransition,
  onCreateDefect,
  stepResults,
  onStepResultsChange,
  terminalResultStatuses,
  actuals,
  onActualsChange,
  attachments,
  onAttachmentsChange,
  dialog,
}) {
  return (
    <WorkspacePage title={run.name} actions={<ProjectCrumb projectId={projectId} />}>
      {error && <ErrorState message={error} />}
      <Panel
        title="Điều khiển lần chạy"
        actions={
          <div className="flex flex-wrap gap-2">
            {can("report.export") && (
              <button
                className="secondary-button"
                type="button"
                onClick={() =>
                  testingApi.exportRunReport(run._id).catch((reason) => onError(messageOf(reason)))
                }
              >
                Xuất báo cáo
              </button>
            )}
            {run.status === "DRAFT" && can("testrun.start") && (
              <button
                className="apple-button"
                type="button"
                onClick={async () => {
                  try {
                    await testingApi.startRun(run._id);
                    onRunChange(await testingApi.getRun(run._id));
                  } catch (reason) {
                    onError(messageOf(reason));
                  }
                }}
              >
                Bắt đầu
              </button>
            )}
            {run.status === "IN_PROGRESS" && (
              <>
                {can("testrun.execute") && (
                  <button
                    className="apple-button"
                    type="button"
                    onClick={async () => {
                      try {
                        const value = await testingApi.resumeRun(projectId, run._id, {
                          expected_revision: run.revision,
                          idempotency_key: crypto.randomUUID(),
                        });
                        onResumeChange(value);
                        onRunChange(await testingApi.getRun(run._id));
                      } catch (reason) {
                        onError(messageOf(reason));
                      }
                    }}
                  >
                    Tiếp tục thực thi
                  </button>
                )}
                {can("testrun.abort") && (
                  <button
                    className="secondary-button"
                    type="button"
                    onClick={async () => {
                      const answer = await ask({
                        title: "Hủy lần chạy kiểm thử",
                        description: `${run.name} sẽ dừng và giữ nguyên toàn bộ kết quả đã ghi nhận`,
                        confirmLabel: "Hủy lần chạy",
                        danger: true,
                        fields: [
                          {
                            name: "reason",
                            label: "Lý do hủy",
                            initialValue: "Dừng theo quyết định kiểm thử",
                            required: true,
                            multiline: true,
                            autoFocus: true,
                          },
                        ],
                      });
                      if (!answer) return;
                      try {
                        await testingApi.abortRun(run._id, answer.reason);
                        onRunChange(await testingApi.getRun(run._id));
                      } catch (value) {
                        onError(messageOf(value));
                      }
                    }}
                  >
                    Hủy lần chạy
                  </button>
                )}
                {can("testrun.complete") && (
                  <button
                    className="apple-button"
                    type="button"
                    onClick={async () => {
                      try {
                        await testingApi.completeRun(run._id);
                        onRunChange(await testingApi.getRun(run._id));
                      } catch (reason) {
                        onError(messageOf(reason));
                      }
                    }}
                  >
                    Hoàn tất
                  </button>
                )}
              </>
            )}
          </div>
        }
      >
        <div className="p-5">
          <StatusPill value={run.status} />
          {resumeContext && (
            <div className="mt-4 rounded-xl border border-border bg-surface-raised p-4 text-[13px]">
              {resumeContext.current_test_case_version ? (
                <>
                  <p className="font-semibold">Vị trí tiếp tục</p>
                  <p className="mt-2">
                    {resumeContext.current_test_case_version.test_case_key}{" "}
                    {resumeContext.current_test_case_version.title}
                  </p>
                  <p className="mt-1 text-ink-muted">
                    Vị trí {resumeContext.position} trên {resumeContext.total_count} còn lại{" "}
                    {resumeContext.remaining_count}
                  </p>
                </>
              ) : (
                <p>Không còn ca kiểm thử được phân công cần thực thi</p>
              )}
            </div>
          )}
        </div>
      </Panel>
      <Panel title="Kết quả thủ công">
        <DataTable
          items={run.test_case_versions || []}
          columns={[
            { key: "test_case_key", label: "Ca kiểm thử" },
            { key: "version", label: "Phiên bản", render: (item) => `v${item.version}` },
            { key: "title", label: "Tên" },
            {
              key: "result",
              label: "Kết quả",
              render: (item) => {
                const result = run.results?.find(
                  (value) => value.test_case_version_id === item._id,
                );
                if (!result) return "Không có ảnh chụp thực thi";
                if (!["NOT_RUN", "IN_PROGRESS"].includes(result.status)) {
                  const hasDefect = run.defects?.some(
                    (defect) => defect.linked_test_result_id === result._id,
                  );
                  return (
                    <span className="flex min-w-0 flex-col items-start gap-2">
                      <StatusPill value={result.status} />
                      {result.status === "FAIL" && !hasDefect && can("defect.create") && (
                        <button
                          className="apple-button"
                          type="button"
                          onClick={() => onCreateDefect(result, item)}
                        >
                          Tạo lỗi từ kết quả thất bại
                        </button>
                      )}
                      {hasDefect && (
                        <span className="text-[11px] text-ink-muted">Đã liên kết lỗi</span>
                      )}
                    </span>
                  );
                }
                if (run.status !== "IN_PROGRESS") {
                  return <StatusPill value={result.status} />;
                }
                if (!can("testrun.execute")) {
                  return <StatusPill value={result.status} />;
                }
                if (result.status === "NOT_RUN") {
                  return (
                    <span className="flex flex-wrap gap-2">
                      <button
                        className="secondary-button"
                        type="button"
                        onClick={() => onTransition(result, "IN_PROGRESS", item)}
                      >
                        Bắt đầu ca kiểm thử
                      </button>
                      <button
                        className="secondary-button"
                        type="button"
                        onClick={() => onTransition(result, "SKIPPED", item)}
                      >
                        Bỏ qua
                      </button>
                    </span>
                  );
                }
                return (
                  <div className="min-w-0 space-y-3">
                    {(item.steps || []).map((step, stepIndex) => {
                      const existing = result.step_results?.find(
                        (value) => value.step_id === step.id,
                      );
                      const edited = stepResults[result._id]?.[step.id] || {};
                      return (
                        <fieldset
                          className="space-y-2 rounded-xl border border-border p-3"
                          key={step.id}
                        >
                          <legend className="px-2 text-[12px] font-semibold">
                            Bước {stepIndex + 1}
                          </legend>
                          <p className="text-[12px]">{docText(step.action_doc)}</p>
                          <p className="text-[12px] text-ink-muted">
                            Mong đợi {docText(step.expected_doc)}
                          </p>
                          <select
                            aria-label={`Trạng thái bước ${stepIndex + 1} ${item.test_case_key}`}
                            className="apple-input"
                            value={edited.status || existing?.status || "PASS"}
                            onChange={(event) =>
                              onStepResultsChange((values) => ({
                                ...values,
                                [result._id]: {
                                  ...values[result._id],
                                  [step.id]: {
                                    ...values[result._id]?.[step.id],
                                    status: event.target.value,
                                  },
                                },
                              }))
                            }
                          >
                            {terminalResultStatuses.map((value) => (
                              <option value={value} key={value}>
                                {valueLabel(value)}
                              </option>
                            ))}
                          </select>
                          <textarea
                            aria-label={`Kết quả bước ${stepIndex + 1} ${item.test_case_key}`}
                            className="apple-input min-h-16"
                            value={edited.actual ?? docText(existing?.actual_doc)}
                            onChange={(event) =>
                              onStepResultsChange((values) => ({
                                ...values,
                                [result._id]: {
                                  ...values[result._id],
                                  [step.id]: {
                                    ...values[result._id]?.[step.id],
                                    actual: event.target.value,
                                  },
                                },
                              }))
                            }
                            placeholder="Kết quả thực tế của bước"
                          />
                          <textarea
                            aria-label={`Lý do trạng thái bước ${stepIndex + 1} ${item.test_case_key}`}
                            className="apple-input min-h-16"
                            value={edited.note ?? existing?.note ?? ""}
                            onChange={(event) =>
                              onStepResultsChange((values) => ({
                                ...values,
                                [result._id]: {
                                  ...values[result._id],
                                  [step.id]: {
                                    ...values[result._id]?.[step.id],
                                    note: event.target.value,
                                  },
                                },
                              }))
                            }
                            placeholder="Ghi chú hoặc lý do Không áp dụng"
                          />
                        </fieldset>
                      );
                    })}
                    <textarea
                      aria-label={`Kết quả thực tế ${item.test_case_key}`}
                      className="apple-input min-h-20"
                      value={actuals[result._id] ?? docText(result.actual_result_doc)}
                      onChange={(event) =>
                        onActualsChange({ ...actuals, [result._id]: event.target.value })
                      }
                      placeholder="Kết quả thực tế và bằng chứng"
                    />
                    <FilePicker
                      ariaLabel={`Tệp bằng chứng ${item.test_case_key}`}
                      buttonLabel="Chọn tệp bằng chứng"
                      onChange={async (event) => {
                        const file = event.target.files?.[0];
                        if (!file) return;
                        try {
                          const uploaded = await uploadAssetAPI(file);
                          const current = attachments[result._id] || result.attachments || [];
                          onAttachmentsChange({
                            ...attachments,
                            [result._id]: [...current, uploaded.data],
                          });
                        } catch (reason) {
                          onError(messageOf(reason));
                        }
                      }}
                    />
                    {(attachments[result._id] || result.attachments || []).map((attachment) => (
                      <p className="break-all text-[11px] text-ink-muted" key={attachment.url}>
                        {attachment.filename}
                      </p>
                    ))}
                    <span className="flex flex-wrap gap-2">
                      {terminalResultStatuses.map((value) => (
                        <button
                          className="secondary-button"
                          type="button"
                          key={value}
                          onClick={() => onTransition(result, value, item)}
                        >
                          {valueLabel(value)}
                        </button>
                      ))}
                    </span>
                  </div>
                );
              },
              mobileRender: (item) => {
                const result = run.results?.find(
                  (value) => value.test_case_version_id === item._id,
                );
                return result
                  ? `Kết quả ${valueLabel(result.status)}`
                  : "Không có ảnh chụp thực thi";
              },
            },
          ]}
        />
      </Panel>
      {dialog}
    </WorkspacePage>
  );
}
