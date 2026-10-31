"use client";

import { useCallback, useEffect, useRef, useState } from "react";
import Image from "next/image";
import ReactMarkdown from "react-markdown";
import remarkGfm from "remark-gfm";
import { ErrorState, LoadingState, Panel } from "../../components/WorkspacePrimitives";
import { messageOf } from "../../lib/testing";
import { projectRoute } from "../../routes";
import { testingApi } from "../../services/testing.service";

export default function DocumentReaderPage({ project, section = [] }) {
  const documentId = section[0] || "";
  const [document, setDocument] = useState(null);
  const [content, setContent] = useState("");
  const [nextOffset, setNextOffset] = useState(null);
  const [sheets, setSheets] = useState([]);
  const [selectedSheet, setSelectedSheet] = useState("");
  const [selectedPage, setSelectedPage] = useState("");
  const [sourceBlocks, setSourceBlocks] = useState([]);
  const [pdfPreviewUrl, setPdfPreviewUrl] = useState("");
  const [pdfPreviewError, setPdfPreviewError] = useState("");
  const [sourceImageUrls, setSourceImageUrls] = useState({});
  const sourceImageUrlsRef = useRef({});
  const [sourceImageLoading, setSourceImageLoading] = useState({});
  const [sourceImageErrors, setSourceImageErrors] = useState({});
  const [loading, setLoading] = useState(true);
  const [loadingMore, setLoadingMore] = useState(false);
  const [summaryLoading, setSummaryLoading] = useState(false);
  const [summary, setSummary] = useState(null);
  const [summaryJob, setSummaryJob] = useState(null);
  const [error, setError] = useState("");
  const [query, setQuery] = useState("");
  const [searchResults, setSearchResults] = useState(null);
  const [searchLoading, setSearchLoading] = useState(false);
  const [searchError, setSearchError] = useState("");
  const [language, setLanguage] = useState(
    project?.locale?.toLowerCase().startsWith("en") ? "en" : "vi",
  );

  const loadPage = useCallback(
    async (offset = 0, append = false, sheet = "", pageNo = null) => {
      try {
        if (append) setLoadingMore(true);
        else setLoading(true);
        const result = await testingApi.readRequirementDocumentPage(
          documentId,
          offset,
          sheet,
          pageNo,
        );
        setDocument(result);
        setSourceBlocks(result.blocks || []);
        setSheets(result.sheets || []);
        if (result.sheet) setSelectedSheet(result.sheet);
        setSelectedPage(result.page_no ? String(result.page_no) : "");
        setContent((value) => (append ? value + result.content : result.content));
        setNextOffset(result.next_offset);
        setError("");
      } catch (reason) {
        setError(messageOf(reason));
      } finally {
        setLoading(false);
        setLoadingMore(false);
      }
    },
    [documentId],
  );

  useEffect(() => {
    setContent("");
    setSummary(null);
    loadPage(0);
  }, [loadPage]);

  useEffect(() => {
    setLanguage(project?.locale?.toLowerCase().startsWith("en") ? "en" : "vi");
  }, [project?.locale]);

  useEffect(() => {
    if (document?.format !== "pdf") return undefined;
    let active = true;
    let objectUrl = "";
    setPdfPreviewError("");
    testingApi
      .previewRequirementDocument(documentId)
      .then((url) => {
        objectUrl = url;
        if (active) setPdfPreviewUrl(url);
        else URL.revokeObjectURL(url);
      })
      .catch((reason) => {
        if (active) setPdfPreviewError(messageOf(reason));
      });
    return () => {
      active = false;
      if (objectUrl) URL.revokeObjectURL(objectUrl);
    };
  }, [document?.format, documentId]);

  useEffect(
    () => () =>
      Object.values(sourceImageUrlsRef.current).forEach((url) => URL.revokeObjectURL(url)),
    [],
  );

  const loadSourceImage = async (block) => {
    const key = String(block.block_index);
    setSourceImageLoading((current) => ({ ...current, [key]: true }));
    setSourceImageErrors((current) => ({ ...current, [key]: "" }));
    try {
      const blob = await testingApi.getRequirementDocumentImage(documentId, block.block_index);
      const url = URL.createObjectURL(blob);
      if (sourceImageUrlsRef.current[key]) URL.revokeObjectURL(sourceImageUrlsRef.current[key]);
      sourceImageUrlsRef.current[key] = url;
      setSourceImageUrls((current) => {
        return { ...current, [key]: url };
      });
    } catch (reason) {
      setSourceImageErrors((current) => ({ ...current, [key]: messageOf(reason) }));
    } finally {
      setSourceImageLoading((current) => ({ ...current, [key]: false }));
    }
  };

  useEffect(() => {
    const normalized = query.trim();
    if (normalized.length < 2 || !documentId) {
      setSearchResults(null);
      setSearchError("");
      return undefined;
    }
    let active = true;
    const timeout = window.setTimeout(async () => {
      setSearchLoading(true);
      setSearchError("");
      try {
        const result = await testingApi.searchRequirementDocument(documentId, normalized);
        if (active) setSearchResults(result);
      } catch (reason) {
        if (active) setSearchError(messageOf(reason));
      } finally {
        if (active) setSearchLoading(false);
      }
    }, 300);
    return () => {
      active = false;
      window.clearTimeout(timeout);
    };
  }, [documentId, query]);

  const openSearchMatch = (match) => {
    setContent("");
    if (match.page_no) {
      changePage(String(match.page_no));
      return;
    }
    if (match.row_offset !== null && match.row_offset !== undefined) {
      const sheet = match.sheet || selectedSheet;
      if (sheet) setSelectedSheet(sheet);
      loadPage(match.row_offset, false, sheet);
      return;
    }
    loadPage(match.offset || 0);
  };

  const summarize = async () => {
    setSummaryLoading(true);
    setSummary(null);
    setError("");
    try {
      const started = await testingApi.summarizeRequirementDocuments(project._id, {
        document_ids: [documentId],
        all_readable: false,
        output_language: language,
        idempotency_key: `summary-${crypto.randomUUID()}`,
      });
      setSummaryJob({ _id: started._id, status: started.status, progress: started.progress });
      let current = started;
      while (["QUEUED", "RUNNING"].includes(current.status)) {
        await new Promise((resolve) => window.setTimeout(resolve, 1200));
        current = await testingApi.getRequirementDocumentSummaryJob(project._id, started._id);
        setSummaryJob(current);
      }
      setSummary(current.result || null);
      if (current.status === "FAILED") {
        setError(
          current.error_code
            ? `Không thể tóm tắt tài liệu (${current.error_code}).`
            : "Không có tài liệu đủ điều kiện để tóm tắt.",
        );
      }
    } catch (reason) {
      setError(messageOf(reason));
    } finally {
      setSummaryLoading(false);
    }
  };

  const cancelSummary = async () => {
    if (!summaryJob?._id) return;
    try {
      await testingApi.cancelRequirementDocumentSummaryJob(project._id, summaryJob._id);
    } catch (reason) {
      setError(messageOf(reason));
    }
  };

  const retrySummary = async () => {
    if (!summaryJob?._id) return;
    setSummaryLoading(true);
    setError("");
    try {
      let current = await testingApi.retryRequirementDocumentSummaryJob(
        project._id,
        summaryJob._id,
      );
      setSummaryJob({ ...current, _id: summaryJob._id });
      while (["QUEUED", "RUNNING"].includes(current.status)) {
        await new Promise((resolve) => window.setTimeout(resolve, 1200));
        current = await testingApi.getRequirementDocumentSummaryJob(project._id, summaryJob._id);
        setSummaryJob(current);
      }
      setSummary(current.result || null);
      if (current.status === "FAILED") setError("Không thể hoàn tất tóm tắt. Bạn có thể thử lại.");
    } catch (reason) {
      setError(messageOf(reason));
    } finally {
      setSummaryLoading(false);
    }
  };

  const changeSheet = (value) => {
    setSelectedSheet(value);
    setContent("");
    setSummary(null);
    loadPage(0, false, value);
  };

  const changePage = (value) => {
    setSelectedPage(value);
    setContent("");
    setNextOffset(null);
    setError("");
    loadPage(0, false, selectedSheet, value ? Number(value) : null);
  };

  if (loading && !document) return <LoadingState />;
  if (error && !document) return <ErrorState message={error} />;

  return (
    <div className="workspace-page min-w-0 space-y-5">
      <div className="flex flex-wrap items-start justify-between gap-4">
        <div className="min-w-0">
          <a
            className="text-sm text-ink-muted hover:text-primary"
            href={projectRoute(project._id, "yeu-cau")}
          >
            Tài liệu dự án
          </a>
          <h1 className="mt-2 break-words text-3xl font-semibold text-ink">
            {document?.filename || "Tài liệu"}
          </h1>
          <p className="mt-1 text-sm text-ink-muted">
            Phiên bản {document?.source_version || "1"}
            {document?.page_count ? ` · ${document.page_count} trang` : ""}
          </p>
        </div>
        <div className="flex flex-wrap items-center gap-2">
          <select
            className="form-input w-auto"
            aria-label="Ngôn ngữ tóm tắt"
            value={language}
            onChange={(event) => setLanguage(event.target.value)}
          >
            <option value="vi">Tiếng Việt</option>
            <option value="en">English</option>
          </select>
          <button
            className="apple-button"
            type="button"
            onClick={summarize}
            disabled={summaryLoading}
          >
            {summaryLoading ? "Đang tóm tắt…" : "Tóm tắt tài liệu"}
          </button>
          {summaryLoading && summaryJob?._id && (
            <button className="secondary-button" type="button" onClick={cancelSummary}>
              Hủy tóm tắt
            </button>
          )}
          <button
            className="secondary-button"
            type="button"
            onClick={() =>
              testingApi.downloadRequirementDocument(documentId, document?.filename || "tai-lieu")
            }
          >
            Tải tệp gốc
          </button>
        </div>
      </div>

      {error && (
        <div
          role="alert"
          className="rounded-xl border border-danger/30 bg-danger/5 p-3 text-sm text-danger"
        >
          {error}
        </div>
      )}
      {document?.unprocessed_blocks?.length > 0 && (
        <div role="status" className="rounded-xl border border-warning/30 bg-warning/5 p-3 text-sm">
          Một phần tài liệu chưa đọc được. Nội dung và bản tóm tắt có thể chưa đầy đủ.
        </div>
      )}
      {pdfPreviewError && (
        <div role="status" className="rounded-xl border border-warning/30 bg-warning/5 p-3 text-sm">
          Không mở được bản PDF gốc; nội dung đã trích xuất vẫn có thể xem bên dưới.
        </div>
      )}
      {summaryLoading && summaryJob && (
        <div className="rounded-xl border border-border bg-surface p-3 text-sm" role="status">
          {summaryJob.status === "QUEUED" ? "Đang chờ xử lý" : "Đang tóm tắt tài liệu"}
          {summaryJob.progress?.chunks_total
            ? ` · ${summaryJob.progress.chunks_processed}/${summaryJob.progress.chunks_total} phần`
            : ""}
        </div>
      )}

      {summary && (
        <Panel title={summary.status === "COMPLETED" ? "Tóm tắt tài liệu" : "Tóm tắt chưa đầy đủ"}>
          <div className="prose max-w-none">
            <ReactMarkdown remarkPlugins={[remarkGfm]}>
              {summary.summary || "Chưa tạo được nội dung tóm tắt."}
            </ReactMarkdown>
          </div>
          {summary.results?.map((source) => (
            <div
              className="mt-4 border-t border-border pt-3 text-sm text-ink-muted"
              key={source.document_id}
            >
              Nguồn: {source.filename} · phiên bản {source.source_version}
            </div>
          ))}
          {summary.excluded?.length > 0 && (
            <p className="mt-3 text-sm text-warning">
              {summary.excluded.length} tài liệu hoặc phần nội dung không thể đưa vào kết quả.
            </p>
          )}
        </Panel>
      )}
      {summaryJob && ["FAILED", "INCOMPLETE"].includes(summaryJob.status) && !summaryLoading && (
        <button className="secondary-button" type="button" onClick={retrySummary}>
          Thử lại phần chưa hoàn tất
        </button>
      )}

      {document?.format === "pdf" && pdfPreviewUrl && (
        <Panel title="Bản PDF gốc">
          <iframe
            className="h-[72vh] min-h-[36rem] w-full rounded-xl border border-border"
            src={pdfPreviewUrl}
            title={`Bản PDF gốc: ${document.filename || "Tài liệu"}`}
          />
        </Panel>
      )}

      <Panel title={document?.format === "pdf" ? "Nội dung đã trích xuất" : "Nội dung tài liệu"}>
        <div className="mb-4 flex flex-wrap items-center gap-3">
          {["pdf", "docx"].includes(document?.format) &&
            document?.page_count > 0 &&
            document?.source_pages_available && (
              <select
                className="form-input w-auto min-w-[10rem]"
                aria-label="Trang tài liệu"
                value={selectedPage}
                onChange={(event) => changePage(event.target.value)}
              >
                <option value="">Toàn văn</option>
                {Array.from({ length: document.page_count }, (_, index) => (
                  <option key={index + 1} value={String(index + 1)}>
                    Trang {index + 1}
                  </option>
                ))}
              </select>
            )}
          {sheets.length > 0 && (
            <select
              className="form-input w-auto min-w-[12rem]"
              aria-label="Trang tính"
              value={selectedSheet}
              onChange={(event) => changeSheet(event.target.value)}
            >
              {sheets.map((name) => (
                <option key={name} value={name}>
                  {name}
                </option>
              ))}
            </select>
          )}
          <input
            className="form-input min-w-[16rem] flex-1"
            value={query}
            onChange={(event) => setQuery(event.target.value)}
            placeholder="Tìm trong nội dung đã tải"
            aria-label="Tìm trong tài liệu"
          />
          {query && (
            <span className="text-sm text-ink-muted">
              {searchLoading
                ? "Đang tìm trong toàn bộ tài liệu…"
                : searchResults
                  ? `${searchResults.total_matches}${searchResults.truncated ? "+" : ""} kết quả trong tài liệu`
                  : "Nhập ít nhất 2 ký tự"}
            </span>
          )}
          {Number.isFinite(document?.total_rows) && (
            <span className="text-sm text-ink-muted">
              {Math.min(document.offset + 100, document.total_rows)} / {document.total_rows} dòng
            </span>
          )}
        </div>
        {searchError && (
          <p className="mb-3 text-sm text-danger" role="alert">
            {searchError}
          </p>
        )}
        {searchResults?.matches?.length > 0 && (
          <ul className="mb-4 max-h-64 space-y-2 overflow-auto rounded-xl border border-border p-3">
            {searchResults.matches.map((match, index) => (
              <li key={`${match.block_id || match.offset}-${index}`}>
                <button
                  className="w-full rounded-lg p-2 text-left text-sm hover:bg-surface-muted"
                  type="button"
                  onClick={() => openSearchMatch(match)}
                >
                  <span className="mb-1 block text-xs font-semibold text-brand">
                    {match.page_no
                      ? `Trang ${match.page_no}`
                      : match.sheet
                        ? `${match.sheet} · dòng ${Number(match.row_offset) + 2}`
                        : "Mở vị trí phù hợp"}
                  </span>
                  <span className="line-clamp-2 text-ink-muted">{match.snippet}</span>
                </button>
              </li>
            ))}
          </ul>
        )}
        <div className="max-h-[72vh] overflow-auto rounded-xl border border-border bg-surface p-5">
          <article className="prose prose-sm max-w-none break-words">
            <ReactMarkdown remarkPlugins={[remarkGfm]}>{content}</ReactMarkdown>
          </article>
          {sourceBlocks
            .filter((block) => block.image_metadata)
            .map((block) => {
              const key = String(block.block_index);
              const metadata = block.image_metadata;
              return (
                <figure className="mt-5 border-t border-border pt-4" key={block.block_id}>
                  <figcaption className="mb-2 text-sm text-ink-muted">
                    {metadata.image_id || "Hình trong tài liệu"}
                    {block.locations?.[0]?.page_no ? ` · Trang ${block.locations[0].page_no}` : ""}
                  </figcaption>
                  {sourceImageUrls[key] ? (
                    <Image
                      className="max-h-[36rem] max-w-full rounded-lg border border-border object-contain"
                      src={sourceImageUrls[key]}
                      alt={metadata.image_id || "Hình nguồn tài liệu"}
                      width={Number(metadata.width) || 1200}
                      height={Number(metadata.height) || 800}
                      unoptimized
                    />
                  ) : (
                    <button
                      className="secondary-button"
                      type="button"
                      disabled={sourceImageLoading[key] || !metadata.asset_available}
                      onClick={() => void loadSourceImage(block)}
                    >
                      {sourceImageLoading[key]
                        ? "Đang tải hình…"
                        : metadata.asset_available
                          ? "Mở hình nguồn"
                          : "Hình nguồn không khả dụng"}
                    </button>
                  )}
                  {sourceImageErrors[key] && (
                    <p className="mt-2 text-sm text-danger" role="alert">
                      Không tải được hình nguồn.
                    </p>
                  )}
                </figure>
              );
            })}
          {sourceBlocks.some((block) => block.extraction_status === "NO_TEXT_EXTRACTED") && (
            <p className="mt-4 rounded-lg bg-warning/5 p-3 text-sm text-warning">
              Trang này có nội dung chưa trích xuất được. Hãy đối chiếu bản gốc.
            </p>
          )}
        </div>
        {nextOffset !== null && (
          <button
            className="secondary-button mt-4"
            type="button"
            disabled={loadingMore}
            onClick={() => loadPage(nextOffset, true, selectedSheet)}
          >
            {loadingMore ? "Đang tải…" : "Tải thêm nội dung"}
          </button>
        )}
        {document?.extraction_warnings?.length > 0 && (
          <p className="mt-3 text-sm text-ink-muted">
            Có cảnh báo khi đọc tệp. Kiểm tra bản gốc nếu thiếu nội dung.
          </p>
        )}
      </Panel>
    </div>
  );
}
