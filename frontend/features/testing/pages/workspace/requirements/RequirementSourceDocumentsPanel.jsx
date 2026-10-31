import { useRef, useState } from "react";
import DataTable from "../../../components/DataTable";
import { Panel, StatusPill } from "../../../components/WorkspacePrimitives";
import { messageOf, valueLabel } from "../../../lib/testing";
import { projectRoute } from "../../../routes";
import { testingApi } from "../../../services/testing.service";
import {
  REQUIREMENT_SOURCE_APPROVAL_OPTIONS,
  REQUIREMENT_SOURCE_AUTHORITY_OPTIONS,
  REQUIREMENT_SOURCE_TYPE_OPTIONS,
} from "./requirements.model";

function dateTimeLocalValue(value) {
  if (!value) return "";
  const date = new Date(value);
  if (Number.isNaN(date.getTime())) return "";
  const local = new Date(date.getTime() - date.getTimezoneOffset() * 60_000);
  return local.toISOString().slice(0, 16);
}

function dateTimeApiValue(value) {
  if (!value) return null;
  const date = new Date(value);
  return Number.isNaN(date.getTime()) ? null : date.toISOString();
}

function metadataFields(item) {
  return [
    {
      name: "title",
      label: "Tiêu đề",
      initialValue: item.title || item.filename,
      required: true,
    },
    {
      name: "source_type",
      label: "Loại nguồn",
      initialValue: item.source_type || "REFERENCE",
      options: REQUIREMENT_SOURCE_TYPE_OPTIONS,
    },
    {
      name: "authority",
      label: "Độ tin cậy của nguồn",
      initialValue: item.authority || "PROJECT_REFERENCE",
      options: REQUIREMENT_SOURCE_AUTHORITY_OPTIONS,
    },
    { name: "owner_id", label: "Người phụ trách", initialValue: item.owner_id || "" },
    { name: "module", label: "Phân hệ", initialValue: item.module || "" },
    { name: "component", label: "Thành phần", initialValue: item.component || "" },
    {
      name: "product_area",
      label: "Khu vực sản phẩm",
      initialValue: item.product_area || "",
    },
    { name: "release_id", label: "Bản phát hành", initialValue: item.release_id || "" },
    {
      name: "external_source_id",
      label: "Mã nguồn bên ngoài",
      initialValue: item.external_source_id || "",
    },
    {
      name: "approval_status",
      label: "Trạng thái phê duyệt",
      initialValue: item.approval_status || "DRAFT",
      options: REQUIREMENT_SOURCE_APPROVAL_OPTIONS,
    },
    {
      name: "approved_by",
      label: "Người phê duyệt",
      initialValue: item.approved_by || "",
    },
    {
      name: "approved_at",
      label: "Thời điểm phê duyệt",
      initialValue: dateTimeLocalValue(item.approved_at),
      type: "datetime-local",
    },
    {
      name: "source_version",
      label: "Phiên bản nguồn",
      initialValue: item.source_version || "1",
      required: true,
      disabled: Boolean(item.source_series_id),
    },
    {
      name: "effective_from",
      label: "Bắt đầu có hiệu lực",
      initialValue: dateTimeLocalValue(item.effective_from),
      type: "datetime-local",
    },
    {
      name: "tags",
      label: "Nhãn phân cách bằng dấu phẩy",
      initialValue: (item.tags || []).join(", "),
    },
  ];
}

function lifecycleFields() {
  return [
    {
      name: "reason",
      label: "Lý do",
      required: true,
      multiline: true,
    },
  ];
}

function documentFormatLabel(format) {
  const labels = {
    md: "Markdown",
    markdown: "Markdown",
    doc: "Word",
    docx: "Word",
    xls: "Excel",
    xlsx: "Excel",
    yml: "OpenAPI YAML",
    yaml: "OpenAPI YAML",
  };
  return labels[String(format || "").toLowerCase()] || valueLabel(format || "Tệp tài liệu");
}

export default function RequirementSourceDocumentsPanel({
  projectId,
  projectLocale,
  items,
  members,
  can,
  currentUserId,
  isPlatformAdmin,
  ask,
  reload,
  onError,
  onContinueImport,
}) {
  const [retryingDocumentId, setRetryingDocumentId] = useState("");
  const [continuingImportDocumentId, setContinuingImportDocumentId] = useState("");
  const [activatingAiDocumentId, setActivatingAiDocumentId] = useState("");
  const [startingAiDocumentId, setStartingAiDocumentId] = useState("");
  const [aiActivationNotice, setAiActivationNotice] = useState("");
  const [expandedReportId, setExpandedReportId] = useState("");
  const [selectedIds, setSelectedIds] = useState([]);
  const [summaryBusy, setSummaryBusy] = useState(false);
  const [summaryResult, setSummaryResult] = useState(null);
  const [summaryJob, setSummaryJob] = useState(null);
  const [summaryLanguage, setSummaryLanguage] = useState(
    projectLocale?.toLowerCase().startsWith("en") ? "en" : "vi",
  );
  const summaryIdempotencyRef = useRef({ scope: "", key: "" });

  useEffect(() => {
    setSummaryLanguage(projectLocale?.toLowerCase().startsWith("en") ? "en" : "vi");
  }, [projectLocale]);

  const extractionIssueLabel = (reasonCode) => {
    const labels = {
      PICTURE_TEXT_NOT_EXTRACTED: "Chưa trích xuất được nội dung hoặc chú thích hình",
      TABLE_TEXT_NOT_EXTRACTED: "Chưa trích xuất được nội dung bảng",
      DOCUMENT_BLOCK_TEXT_NOT_EXTRACTED: "Chưa trích xuất được văn bản trong khối tài liệu",
    };
    return labels[reasonCode] || "Khối này chưa được đọc đầy đủ";
  };

  const sourceLocationLabel = (block) => {
    const location = block.locations?.find((item) => item?.page_no || item?.bbox);
    const pageNo = location?.page_no ?? block.page_no;
    const bbox = location?.bbox;
    const coordinateValues = bbox && [
      bbox.x0 ?? bbox.l,
      bbox.y0 ?? bbox.t,
      bbox.x1 ?? bbox.r,
      bbox.y1 ?? bbox.b,
    ];
    const coordinates =
      coordinateValues &&
      coordinateValues.every(
        (value) =>
          value !== null && value !== undefined && value !== "" && Number.isFinite(Number(value)),
      )
        ? ` · vùng ${[bbox.x0 ?? bbox.l, bbox.y0 ?? bbox.t, bbox.x1 ?? bbox.r, bbox.y1 ?? bbox.b]
            .map((value) => Math.round(Number(value)))
            .join(", ")}`
        : "";
    return `${pageNo ? `Trang ${pageNo}` : "Chưa xác định trang"}${coordinates}`;
  };

  const retryParse = async (item) => {
    setRetryingDocumentId(item._id);
    try {
      const document = await testingApi.retryRequirementDocumentParse(item._id, item.revision);
      await reload();
      if (document.status !== "READY") {
        const message =
          document.parse_error_type === "TimeoutError"
            ? "Đã hết thời gian phân tích tài liệu; bạn có thể thử lại sau."
            : "Tệp vẫn chưa phân tích được; trạng thái và lỗi đã được cập nhật trong kho tài liệu.";
        onError(message);
      } else if (document.ai_enabled && !["INDEXED", "DEGRADED"].includes(document.index_status)) {
        onError("Đã phân tích tệp nhưng lập chỉ mục AI chưa hoàn tất; có thể thử lại sau.");
      }
    } catch (reason) {
      onError(messageOf(reason));
    } finally {
      setRetryingDocumentId("");
    }
  };

  const changeAccess = async (item) => {
    await ask({
      title: "Quyền xem tài liệu",
      description: item.filename,
      confirmLabel: "Lưu quyền xem",
      fields: [
        {
          name: "visibility",
          label: "Phạm vi xem",
          initialValue: item.visibility || "private",
          options: [
            { value: "private", label: "Riêng tư chỉ người tải lên" },
            { value: "project", label: "Toàn bộ thành viên dự án" },
            { value: "shared", label: "Chọn thành viên dự án" },
          ],
        },
        {
          name: "shared_with",
          label: "Thành viên được xem khi chọn chia sẻ",
          initialValue: item.shared_with || [],
          multiple: true,
          options: members.map((member) => ({
            value: member.user_id,
            label: member.user_label || member.user?.email || "Thành viên dự án",
          })),
        },
      ],
      onConfirm: async (answer) => {
        if (answer.visibility === "shared" && answer.shared_with.length === 0) {
          throw new Error("Chọn ít nhất một thành viên để chia sẻ tài liệu");
        }
        try {
          await testingApi.updateRequirementDocumentAccess(item._id, {
            expected_revision: item.revision,
            visibility: answer.visibility,
            shared_with: answer.visibility === "shared" ? answer.shared_with : [],
          });
          await reload();
        } catch (reason) {
          throw new Error(messageOf(reason));
        }
      },
    });
  };
  const enableAiRead = async (item) => {
    setActivatingAiDocumentId(item._id);
    setAiActivationNotice("");
    try {
      await testingApi.updateRequirementDocumentAiRead(item._id, {
        expected_revision: item.revision,
        ai_enabled: true,
      });
      await reload();
      setAiActivationNotice(
        `Đã cho phép AI đọc “${item.filename}”. Bạn có thể chủ động bắt đầu sau khi tài liệu sẵn sàng.`,
      );
    } catch (reason) {
      onError(messageOf(reason));
    } finally {
      setActivatingAiDocumentId("");
    }
  };
  const startAiProcessing = async (item) => {
    setStartingAiDocumentId(item._id);
    setAiActivationNotice("");
    try {
      const result = await testingApi.startRequirementDocumentAI(item._id, {
        expected_revision: item.revision,
        idempotency_key: `start-${item._id}-r${item.revision}`,
      });
      await reload();
      setAiActivationNotice(
        `Đã gửi yêu cầu xử lý “${item.filename}”. Theo dõi trạng thái trong Hoạt động AI.`,
      );
      return result;
    } catch (reason) {
      onError(messageOf(reason));
    } finally {
      setStartingAiDocumentId("");
    }
  };
  const classify = async (item) => {
    await ask({
      title: "Phân loại tài liệu nguồn",
      description: item.filename,
      confirmLabel: "Lưu thông tin phân loại",
      fields: metadataFields(item),
      onConfirm: async (answer) => {
        try {
          await testingApi.updateRequirementDocument(item._id, {
            expected_revision: item.revision,
            title: answer.title,
            source_type: answer.source_type,
            authority: answer.authority,
            owner_id: answer.owner_id || null,
            module: answer.module || null,
            component: answer.component || null,
            product_area: answer.product_area || null,
            release_id: answer.release_id || null,
            external_source_id: answer.external_source_id || null,
            approval_status: answer.approval_status,
            approved_by: answer.approved_by || null,
            approved_at: dateTimeApiValue(answer.approved_at),
            source_version: answer.source_version,
            effective_from: dateTimeApiValue(answer.effective_from),
            tags: answer.tags
              .split(",")
              .map((value) => value.trim())
              .filter(Boolean),
          });
          await reload();
        } catch (reason) {
          throw new Error(messageOf(reason));
        }
      },
    });
  };

  const reindex = async (item) => {
    try {
      await testingApi.reindexRequirementDocument(item._id);
      await reload();
    } catch (reason) {
      onError(messageOf(reason));
    }
  };

  const download = async (item) => {
    try {
      await testingApi.downloadRequirementDocument(item._id, item.filename);
    } catch (reason) {
      onError(messageOf(reason));
    }
  };

  const continueImport = async (item) => {
    if (!item.last_import_job_id || !onContinueImport) return;
    setContinuingImportDocumentId(item._id);
    try {
      await onContinueImport(item);
    } finally {
      setContinuingImportDocumentId("");
    }
  };

  const changeArchiveStatus = async (item, restore) => {
    await ask({
      title: restore ? "Khôi phục tài liệu nguồn" : "Lưu trữ tài liệu nguồn",
      description: item.filename,
      confirmLabel: restore ? "Khôi phục" : "Lưu trữ",
      danger: !restore,
      fields: lifecycleFields(),
      onConfirm: async (answer) => {
        try {
          const payload = { expected_revision: item.revision, reason: answer.reason };
          if (restore) await testingApi.restoreRequirementDocument(item._id, payload);
          else await testingApi.archiveRequirementDocument(item._id, payload);
          await reload();
        } catch (reason) {
          throw new Error(messageOf(reason));
        }
      },
    });
  };

  const summarizeDocuments = async (documentIds, allReadable = false) => {
    setSummaryBusy(true);
    setSummaryJob(null);
    setSummaryResult(null);
    setAiActivationNotice("");
    try {
      const scope = allReadable ? "all" : [...documentIds].sort().join(",");
      if (summaryIdempotencyRef.current.scope !== scope) {
        summaryIdempotencyRef.current = {
          scope,
          key: `summary-${crypto.randomUUID()}`,
        };
      }
      const started = await testingApi.summarizeRequirementDocuments(projectId, {
        document_ids: documentIds,
        all_readable: allReadable,
        output_language: summaryLanguage,
        idempotency_key: summaryIdempotencyRef.current.key,
      });
      const jobId = started._id;
      setSummaryJob({ _id: jobId, status: started.status, progress: started.progress });
      let current = started;
      while (["QUEUED", "RUNNING"].includes(current.status)) {
        await new Promise((resolve) => window.setTimeout(resolve, 1200));
        current = await testingApi.getRequirementDocumentSummaryJob(projectId, jobId);
        setSummaryJob(current);
      }
      const result = current.result || {
        status: current.status,
        results: [],
        excluded: [],
        summary: "",
      };
      setSummaryResult(result);
      if (current.status === "CANCELLED") {
        setAiActivationNotice("Đã hủy yêu cầu tóm tắt.");
        return;
      }
      if (current.status === "FAILED") {
        onError(
          current.error_code
            ? `Không thể hoàn tất tóm tắt (${current.error_code}). Bạn có thể thử lại.`
            : "Không có tài liệu nào đủ điều kiện để tóm tắt. Kiểm tra quyền AI và trạng thái xử lý tài liệu.",
        );
        return;
      }
      const skipped = result.excluded?.length || 0;
      setAiActivationNotice(
        `${result.status === "COMPLETED" ? "Đã tóm tắt" : "Tóm tắt chưa đầy đủ"} ${result.results.length} tài liệu${skipped ? `; ${skipped} tài liệu bị bỏ qua` : ""}.`,
      );
    } catch (reason) {
      onError(messageOf(reason));
    } finally {
      setSummaryBusy(false);
    }
  };

  const cancelSummary = async () => {
    if (!summaryJob?._id) return;
    try {
      await testingApi.cancelRequirementDocumentSummaryJob(projectId, summaryJob._id);
    } catch (reason) {
      onError(messageOf(reason));
    }
  };

  const retrySummary = async () => {
    if (!summaryJob?._id) return;
    setSummaryBusy(true);
    try {
      const started = await testingApi.retryRequirementDocumentSummaryJob(
        projectId,
        summaryJob._id,
      );
      let current = started;
      setSummaryJob({ ...started, _id: summaryJob._id });
      while (["QUEUED", "RUNNING"].includes(current.status)) {
        await new Promise((resolve) => window.setTimeout(resolve, 1200));
        current = await testingApi.getRequirementDocumentSummaryJob(projectId, summaryJob._id);
        setSummaryJob(current);
      }
      setSummaryResult(current.result || null);
      if (current.status === "FAILED") {
        onError("Không thể hoàn tất tóm tắt. Bạn có thể thử lại khi dịch vụ xử lý sẵn sàng.");
      }
    } catch (reason) {
      onError(messageOf(reason));
    } finally {
      setSummaryBusy(false);
    }
  };

  return (
    <Panel title="Kho tài liệu nguồn">
      {aiActivationNotice && (
        <p
          className="mb-3 rounded-control bg-brand-soft px-3 py-2 text-sm text-brand"
          role="status"
        >
          {aiActivationNotice}
        </p>
      )}
      {summaryBusy && summaryJob && (
        <div className="mb-4 flex flex-wrap items-center gap-3 rounded-xl border border-border bg-surface p-3 text-sm">
          <span>
            {summaryJob.status === "QUEUED" ? "Đang chờ xử lý" : "Đang tóm tắt tài liệu"}
            {summaryJob.progress?.total
              ? ` · ${summaryJob.progress.processed}/${summaryJob.progress.total} tệp`
              : ""}
            {summaryJob.progress?.chunks_total
              ? ` · ${summaryJob.progress.chunks_processed}/${summaryJob.progress.chunks_total} phần của ${summaryJob.progress.current_document || "tài liệu hiện tại"}`
              : ""}
          </span>
          <button
            className="secondary-button !min-h-8 !px-3 !py-1 text-xs"
            type="button"
            onClick={cancelSummary}
          >
            Hủy
          </button>
        </div>
      )}
      {summaryResult && summaryResult.status !== "FAILED" && (
        <div className="mb-4 rounded-xl border border-border bg-surface p-4">
          <h3 className="font-semibold">
            {summaryResult.status === "COMPLETED" ? "Tóm tắt tài liệu" : "Tóm tắt chưa đầy đủ"}
          </h3>
          <p className="mt-3 whitespace-pre-wrap text-sm leading-6">{summaryResult.summary}</p>
          {summaryResult.results?.length > 0 && (
            <ul className="mt-4 flex flex-wrap gap-2 border-t border-border pt-3">
              {summaryResult.results.map((source) => (
                <li key={source.document_id}>
                  <a
                    className="secondary-button !min-h-8 !px-3 !py-1 text-xs"
                    href={projectRoute(projectId, "tai-lieu", source.document_id)}
                  >
                    Nguồn: {source.filename} · v{source.source_version}
                  </a>
                </li>
              ))}
            </ul>
          )}
        </div>
      )}
      <div className="mb-4 flex flex-wrap items-center gap-2">
        <select
          className="form-input w-auto !min-h-9"
          aria-label="Ngôn ngữ tóm tắt"
          value={summaryLanguage}
          onChange={(event) => setSummaryLanguage(event.target.value)}
          disabled={summaryBusy}
        >
          <option value="vi">Tiếng Việt</option>
          <option value="en">English</option>
        </select>
        <button
          className="secondary-button !min-h-9 !px-3 !py-1.5 text-xs"
          type="button"
          disabled={!selectedIds.length || summaryBusy}
          onClick={() => summarizeDocuments(selectedIds)}
        >
          {summaryBusy
            ? "Đang tóm tắt…"
            : `Tóm tắt mục đã chọn${selectedIds.length ? ` (${selectedIds.length})` : ""}`}
        </button>
        <button
          className="secondary-button !min-h-9 !px-3 !py-1.5 text-xs"
          type="button"
          disabled={summaryBusy || !items.some((item) => item.status !== "ARCHIVED")}
          onClick={() => summarizeDocuments([], true)}
        >
          Tóm tắt toàn bộ tài liệu được phép đọc
        </button>
      </div>
      {summaryJob && ["FAILED", "INCOMPLETE"].includes(summaryJob.status) && !summaryBusy && (
        <button
          className="secondary-button mb-4 !min-h-8 !px-3 !py-1 text-xs"
          type="button"
          onClick={retrySummary}
        >
          Thử lại phần chưa hoàn tất
        </button>
      )}
      <DataTable
        items={items}
        selectedIds={selectedIds}
        onSelectionChange={setSelectedIds}
        selectionLabel="Chọn tài liệu"
        selectionDisabled={!can("requirement_document.extract")}
        empty="Chưa có tài liệu nguồn"
        columns={[
          {
            key: "document",
            label: "Tài liệu",
            minWidth: 210,
            render: (item) => (
              <div className="space-y-1">
                <p className="break-words font-medium">{item.title || item.filename}</p>
                {item.title && item.title !== item.filename && (
                  <p className="break-all text-xs text-ink-muted">{item.filename}</p>
                )}
                <p className="text-xs text-ink-muted">
                  {valueLabel(item.source_type || "REFERENCE")} · {documentFormatLabel(item.format)}
                </p>
              </div>
            ),
          },
          {
            key: "scope",
            label: "Phạm vi",
            minWidth: 180,
            render: (item) => {
              const moduleScope = [item.product_area, item.module, item.component]
                .filter(Boolean)
                .join(" · ");
              const visibility =
                item.visibility === "project"
                  ? "Toàn dự án"
                  : item.visibility === "shared"
                    ? "Thành viên được chọn"
                    : "Riêng tư";
              return (
                <div className="space-y-1 text-sm">
                  <p>{valueLabel(item.authority || "PROJECT_REFERENCE")}</p>
                  <p className="text-xs text-ink-muted">{moduleScope || "Chưa khai báo phân hệ"}</p>
                  <p className="text-xs text-ink-muted">{visibility}</p>
                </div>
              );
            },
          },
          {
            key: "processing",
            label: "Tình trạng xử lý",
            minWidth: 280,
            render: (item) => {
              const issues = item.parse_report?.unprocessed_blocks || [];
              const parseReport = item.parse_report;
              const expanded = expandedReportId === item._id;
              const status =
                item.index_status === "INDEXED"
                  ? "Có thể tìm trong tài liệu"
                  : item.index_status === "DEGRADED"
                    ? `Một phần tài liệu chưa đọc được${issues.length ? ` · ${issues.length} phần cần xem` : ""}`
                    : item.index_status === "FAILED"
                      ? "Chưa thể xử lý tài liệu"
                      : "Đang chờ xử lý tài liệu";
              return (
                <div className="flex min-w-0 flex-col items-start gap-3">
                  <div className="flex w-full min-w-0 flex-col items-start gap-1">
                    <p className="text-xs font-medium text-ink-muted">Phân tích tài liệu</p>
                    <div className="block w-full">
                      <StatusPill value={item.status} />
                    </div>
                  </div>
                  <div className="flex w-full min-w-0 flex-col items-start gap-1">
                    <p className="text-xs font-medium text-ink-muted">Tra cứu nội dung</p>
                    <p className="break-words text-sm">{status}</p>
                  </div>
                  <p className="text-xs text-ink-muted">
                    {item.ai_enabled ? "Đã cho phép AI đọc" : "Chưa cho phép AI đọc"}
                  </p>
                  {parseReport &&
                    (parseReport.page_count > 0 || parseReport.ocr_enabled === true) && (
                      <p className="text-xs text-ink-muted">
                        {parseReport.page_count > 0 ? `${parseReport.page_count} trang` : ""}
                        {parseReport.ocr_enabled === true &&
                          `${parseReport.page_count > 0 ? " · " : ""}Đã nhận dạng chữ trong ảnh`}
                      </p>
                    )}
                  {issues.length > 0 && (
                    <>
                      <button
                        type="button"
                        className="text-left text-sm font-medium text-brand underline-offset-2 hover:underline"
                        aria-expanded={expanded}
                        aria-controls={`parse-report-${item._id}`}
                        onClick={() => setExpandedReportId(expanded ? "" : item._id)}
                      >
                        {expanded ? "Ẩn chi tiết" : "Xem phần chưa đọc"}
                      </button>
                      {expanded && (
                        <ul
                          id={`parse-report-${item._id}`}
                          className="space-y-2 rounded-control bg-surface-quiet p-3 text-sm"
                        >
                          {issues.slice(0, 20).map((issue, index) => (
                            <li
                              className="break-words"
                              key={`${issue.block_id || issue.reason_code || "issue"}-${index}`}
                            >
                              <p className="font-medium">
                                {extractionIssueLabel(issue.reason_code)}
                              </p>
                              <p className="text-ink-muted">{sourceLocationLabel(issue)}</p>
                            </li>
                          ))}
                          {issues.length > 20 && (
                            <li className="text-ink-muted">
                              Còn {issues.length - 20} phần nội dung chưa đọc; tổng số phần được giữ
                              trong báo cáo phân tích.
                            </li>
                          )}
                        </ul>
                      )}
                    </>
                  )}
                </div>
              );
            },
          },
          {
            key: "version",
            label: "Phiên bản nguồn",
            minWidth: 140,
            render: (item) => (
              <div className="space-y-1 text-sm">
                <p>Phiên bản {item.source_version || "1"}</p>
                <p className="text-xs text-ink-muted">
                  {item.previous_source_version_id ? "Có kế thừa phiên bản trước" : "Tài liệu gốc"}
                </p>
                <p className="text-xs text-ink-muted">Lần chỉnh sửa {item.revision ?? 1}</p>
              </div>
            ),
          },
          {
            key: "actions",
            label: "Thao tác",
            minWidth: 220,
            hideWhenEmpty: true,
            render: (item) => (
              <span className="flex max-w-[32rem] flex-wrap items-center gap-2">
                {can("requirement_document.read") && item.status === "READY" && (
                  <button
                    className="secondary-button !min-h-9 !px-3 !py-1.5 text-xs"
                    type="button"
                    onClick={() =>
                      window.location.assign(projectRoute(projectId, "tai-lieu", item._id))
                    }
                  >
                    Mở đọc
                  </button>
                )}
                {can("requirement_document.review_extraction") &&
                  item.status === "EXTRACTED" &&
                  item.last_import_job_id && (
                    <button
                      className="secondary-button !min-h-9 !px-3 !py-1.5 text-xs"
                      type="button"
                      disabled={continuingImportDocumentId === item._id}
                      aria-busy={continuingImportDocumentId === item._id}
                      onClick={() => continueImport(item)}
                    >
                      {continuingImportDocumentId === item._id
                        ? "Đang mở bản xem trước…"
                        : "Tiếp tục nhập yêu cầu"}
                    </button>
                  )}
                {can("knowledge.manage") && item.status !== "ARCHIVED" && (
                  <>
                    <button
                      className="secondary-button !min-h-9 !px-3 !py-1.5 text-xs"
                      type="button"
                      onClick={() => classify(item)}
                    >
                      Phân loại
                    </button>
                    <button
                      className="secondary-button !min-h-9 !px-3 !py-1.5 text-xs"
                      type="button"
                      onClick={() => reindex(item)}
                    >
                      Lập chỉ mục lại
                    </button>
                  </>
                )}
                {can("requirement_document.extract") &&
                  (["UPLOADED", "PARSE_FAILED"].includes(item.status) || item.can_retry_parse) && (
                    <button
                      className="secondary-button !min-h-9 !px-3 !py-1.5 text-xs"
                      type="button"
                      disabled={retryingDocumentId === item._id}
                      aria-busy={retryingDocumentId === item._id}
                      onClick={() => retryParse(item)}
                    >
                      {retryingDocumentId === item._id
                        ? "Đang tiếp tục…"
                        : item.status === "UPLOADED"
                          ? "Tiếp tục xử lý"
                          : item.status === "PARSING"
                            ? "Khôi phục phân tích bị gián đoạn"
                            : "Thử phân tích lại"}
                    </button>
                  )}
                {(isPlatformAdmin || item.created_by === currentUserId) &&
                  (isPlatformAdmin || can("requirement_document.extract")) &&
                  item.status !== "ARCHIVED" &&
                  !item.ai_enabled &&
                  (item.status === "READY" ? (
                    <button
                      className="secondary-button !min-h-9 !px-3 !py-1.5 text-xs"
                      type="button"
                      disabled={activatingAiDocumentId === item._id}
                      aria-busy={activatingAiDocumentId === item._id}
                      onClick={() => enableAiRead(item)}
                    >
                      {activatingAiDocumentId === item._id
                        ? "Đang cấp quyền đọc…"
                        : "Cho phép AI đọc"}
                    </button>
                  ) : (
                    <span className="self-center text-xs text-ink-muted">
                      AI xử lý sau khi phân tích tài liệu xong
                    </span>
                  ))}
                {(isPlatformAdmin || item.created_by === currentUserId) &&
                  (isPlatformAdmin || can("requirement_document.extract")) &&
                  item.status !== "ARCHIVED" &&
                  item.ai_enabled &&
                  item.status === "READY" &&
                  ["INDEXED", "DEGRADED"].includes(item.index_status) && (
                    <button
                      className="apple-button !min-h-9 !px-3 !py-1.5 text-xs"
                      type="button"
                      disabled={startingAiDocumentId === item._id}
                      aria-busy={startingAiDocumentId === item._id}
                      onClick={() => startAiProcessing(item)}
                    >
                      {startingAiDocumentId === item._id
                        ? "Đang bắt đầu…"
                        : "Chạy AI trên tài liệu"}
                    </button>
                  )}
                {(isPlatformAdmin || item.created_by === currentUserId) &&
                  item.status !== "ARCHIVED" && (
                    <button
                      className="secondary-button !min-h-9 !px-3 !py-1.5 text-xs"
                      type="button"
                      onClick={() => changeAccess(item)}
                    >
                      Quyền xem
                    </button>
                  )}
                {can("requirement_document.download") && (
                  <button
                    className="secondary-button !min-h-9 !px-3 !py-1.5 text-xs"
                    type="button"
                    onClick={() => download(item)}
                  >
                    Tải xuống
                  </button>
                )}
                {item.status === "ARCHIVED"
                  ? can("requirement_document.restore") && (
                      <button
                        className="secondary-button !min-h-9 !px-3 !py-1.5 text-xs"
                        type="button"
                        onClick={() => changeArchiveStatus(item, true)}
                      >
                        Khôi phục
                      </button>
                    )
                  : can("requirement_document.archive") && (
                      <button
                        className="secondary-button !min-h-9 !px-3 !py-1.5 text-xs"
                        type="button"
                        onClick={() => changeArchiveStatus(item, false)}
                      >
                        Lưu trữ
                      </button>
                    )}
              </span>
            ),
          },
        ]}
      />
    </Panel>
  );
}
