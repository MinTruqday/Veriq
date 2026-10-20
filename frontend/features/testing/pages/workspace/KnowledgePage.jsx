"use client";
import { useCallback, useEffect, useRef, useState } from "react";
import DataTable from "../../components/DataTable";
import {
  DegradedBanner,
  ErrorState,
  LoadingState,
  Panel,
  ProjectCrumb,
  WorkspacePage,
  StatusPill,
  useActionDialog,
} from "../../components/WorkspacePrimitives";
import { testingApi } from "../../services/testing.service";
import { messageOf, valueLabel } from "../../lib/testing";
import { Modal, ModalHeader, ModalTitle } from "@/shared/components/ui/Modal";

const sourceTypes = [
  ["SRS", "Đặc tả yêu cầu phần mềm"],
  ["BRD", "Tài liệu yêu cầu nghiệp vụ"],
  ["USER_STORY", "Câu chuyện người dùng"],
  ["ACCEPTANCE_CRITERIA", "Tiêu chí chấp nhận"],
  ["BUSINESS_RULE", "Quy tắc nghiệp vụ"],
  ["API_SPEC", "Đặc tả giao diện lập trình ứng dụng"],
  ["UI_SPEC", "Đặc tả giao diện người dùng"],
  ["ARCHITECTURE", "Kiến trúc"],
  ["MEETING_NOTE", "Biên bản họp"],
  ["RELEASE_NOTE", "Ghi chú phát hành"],
  ["BUG_HISTORY", "Lịch sử lỗi"],
  ["TEST_ARTIFACT", "Tài sản kiểm thử"],
  ["REGULATION", "Quy định"],
  ["REFERENCE", "Tài liệu tham chiếu"],
  ["OTHER", "Nguồn khác"],
];

const authorityLevels = [
  ["APPROVED_SOURCE", "Đã được phê duyệt"],
  ["CONTROLLED_SOURCE", "Được quản lý chính thức"],
  ["PROJECT_REFERENCE", "Tài liệu tham chiếu của dự án"],
  ["SUPPLEMENTAL", "Tài liệu bổ sung"],
  ["DRAFT", "Bản nháp"],
  ["UNVERIFIED", "Chưa xác minh"],
];

export default function KnowledgePage({ project, initialQuery = "", useGlobalSearch = false }) {
  const { ask, dialog } = useActionDialog();
  const [query, setQuery] = useState(initialQuery);
  const [result, setResult] = useState(null);
  const [question, setQuestion] = useState("");
  const [answer, setAnswer] = useState(null);
  const [sources, setSources] = useState([]);
  const [error, setError] = useState("");
  const [sourcesLoading, setSourcesLoading] = useState(true);
  const [sourcesLoadFailed, setSourcesLoadFailed] = useState(false);
  const sourcesLoaded = useRef(false);
  const [creatingSource, setCreatingSource] = useState(false);
  const [askingAi, setAskingAi] = useState(false);
  const canAsk = project.current_permissions?.includes("ai.ask_project");
  const canManage = project.current_permissions?.includes("knowledge.manage");
  const loadSources = useCallback(async () => {
    if (!sourcesLoaded.current) setSourcesLoading(true);
    try {
      setSources(await testingApi.listKnowledgeSources(project._id));
      sourcesLoaded.current = true;
      setSourcesLoadFailed(false);
    } catch (reason) {
      setError(messageOf(reason));
      if (!sourcesLoaded.current) setSourcesLoadFailed(true);
    } finally {
      setSourcesLoading(false);
    }
  }, [project._id]);
  useEffect(() => {
    loadSources();
  }, [loadSources]);
  useEffect(() => {
    if (!useGlobalSearch || !initialQuery) return;
    testingApi
      .searchProject(project._id, initialQuery)
      .then(setResult)
      .catch((reason) => setError(messageOf(reason)));
  }, [initialQuery, project._id, useGlobalSearch]);
  return (
    <WorkspacePage
      title="Tài liệu tham chiếu"
      actions={
        <div className="flex flex-wrap items-center gap-3">
          <ProjectCrumb projectId={project._id} />
          {canManage && (
            <button className="apple-button" type="button" onClick={() => setCreatingSource(true)}>
              Thêm tài liệu tham chiếu
            </button>
          )}
        </div>
      }
    >
      {error && <ErrorState message={error} />}
      <DegradedBanner mode={result?.degraded_mode} />
      {canAsk && (
        <Panel title="Hỏi AI về dữ liệu dự án">
          <form
            className="space-y-3 p-5"
            onSubmit={async (event) => {
              event.preventDefault();
              setError("");
              setAskingAi(true);
              try {
                setAnswer(
                  await testingApi.askProject(project._id, {
                    question,
                    artifact_types: [],
                    evidence_limit: 20,
                  }),
                );
              } catch (reason) {
                setError(messageOf(reason));
              } finally {
                setAskingAi(false);
              }
            }}
          >
            <textarea
              aria-label="Câu hỏi về dự án"
              className="apple-input min-h-28 w-full"
              required
              value={question}
              onChange={(event) => setQuestion(event.target.value)}
              placeholder="Nhập câu hỏi cần trả lời từ yêu cầu tài liệu ca kiểm thử và lỗi của dự án"
            />
            <button aria-busy={askingAi} className="apple-button" disabled={askingAi} type="submit">
              {askingAi ? "AI đang tìm bằng chứng và trả lời" : "Trả lời"}
            </button>
          </form>
          {answer && (
            <div className="space-y-4 border-t border-line p-5">
              <p className="whitespace-pre-wrap text-sm text-ink">{answer.answer}</p>
              <p className="text-xs text-ink-muted">Độ tin cậy {answer.confidence}</p>
              <DataTable
                items={answer.evidence || []}
                empty="Không có bằng chứng"
                columns={[
                  {
                    key: "artifact_type",
                    label: "Loại",
                    render: (item) => valueLabel(item.artifact_type),
                  },
                  { key: "title", label: "Nguồn" },
                  {
                    key: "authority",
                    label: "Thẩm quyền",
                    render: (item) => valueLabel(item.authority),
                  },
                  { key: "score", label: "Điểm" },
                ]}
              />
            </div>
          )}
        </Panel>
      )}
      <Panel title="Tìm trong dữ liệu dự án">
        <form
          className="flex flex-col gap-3 p-5 sm:flex-row"
          onSubmit={async (event) => {
            event.preventDefault();
            try {
              setResult(
                useGlobalSearch
                  ? await testingApi.searchProject(project._id, query)
                  : await testingApi.searchKnowledge(project._id, {
                      query,
                      artifact_types: [],
                      limit: 50,
                    }),
              );
            } catch (reason) {
              setError(messageOf(reason));
            }
          }}
        >
          <input
            aria-label="Tìm trong dữ liệu dự án"
            className="apple-input flex-1"
            required
            value={query}
            onChange={(event) => setQuery(event.target.value)}
            placeholder="Nhập hành vi quy tắc lỗi hoặc ca kiểm thử cần tìm"
          />
          <button className="apple-button" type="submit">
            Tìm kiếm
          </button>
        </form>
      </Panel>
      {result && (
        <Panel title="Kết quả tìm kiếm">
          <DataTable
            items={result.items}
            empty="Không tìm thấy dữ liệu phù hợp"
            columns={[
              {
                key: "artifact_type",
                label: "Loại",
                render: (item) => valueLabel(item.artifact_type),
              },
              { key: "title", label: "Tên" },
              {
                key: "status",
                label: "Trạng thái",
                render: (item) => <StatusPill value={item.status} />,
              },
              {
                key: "authority",
                label: "Độ tin cậy",
                render: (item) => valueLabel(item.authority),
              },
              { key: "score", label: "Điểm" },
              {
                key: "text",
                label: "Bằng chứng",
                render: (item) => <span className="line-clamp-3 max-w-xl">{item.text}</span>,
              },
            ]}
          />
        </Panel>
      )}
      <Panel title="Tài liệu tham chiếu của dự án">
        {canManage && (
          <Modal
            isOpen={creatingSource}
            onClose={() => setCreatingSource(false)}
            ariaLabel="Thêm tài liệu tham chiếu"
            className="max-w-3xl max-h-[90dvh] overflow-y-auto"
          >
            <ModalHeader>
              <ModalTitle>Thêm tài liệu tham chiếu</ModalTitle>
            </ModalHeader>
            <form
              className="grid gap-3 p-5 md:grid-cols-2"
              onSubmit={async (event) => {
                event.preventDefault();
                const form = event.currentTarget;
                const values = new FormData(form);
                try {
                  await testingApi.createKnowledgeSource(project._id, {
                    title: values.get("title"),
                    content: values.get("content"),
                    source_type: values.get("source_type"),
                    authority: values.get("authority"),
                    source_url: values.get("source_url") || null,
                    owner_id: values.get("owner_id") || null,
                    module: values.get("module") || null,
                    component: values.get("component") || null,
                    product_area: values.get("product_area") || null,
                    release_id: values.get("release_id") || null,
                    external_source_id: values.get("external_source_id") || null,
                    approval_status: values.get("approval_status"),
                    approved_by: values.get("approved_by") || null,
                    approved_at: values.get("approved_at") || null,
                    source_version: values.get("source_version"),
                    effective_from: values.get("effective_from") || null,
                    tags: String(values.get("tags") || "")
                      .split(",")
                      .map((value) => value.trim())
                      .filter(Boolean),
                  });
                  form.reset();
                  setCreatingSource(false);
                  await loadSources();
                } catch (reason) {
                  setError(messageOf(reason));
                }
              }}
            >
              <label className="field-label">
                Tiêu đề nguồn
                <input className="apple-input mt-2" name="title" required minLength={2} />
              </label>
              <label className="field-label">
                Loại nguồn
                <select className="apple-input mt-2" name="source_type" defaultValue="REFERENCE">
                  {sourceTypes.map(([value, label]) => (
                    <option key={value} value={value}>
                      {label}
                    </option>
                  ))}
                </select>
              </label>
              <label className="field-label">
                Độ tin cậy của nguồn
                <select
                  className="apple-input mt-2"
                  name="authority"
                  defaultValue="PROJECT_REFERENCE"
                >
                  {authorityLevels.map(([value, label]) => (
                    <option key={value} value={value}>
                      {label}
                    </option>
                  ))}
                </select>
              </label>
              <label className="field-label">
                Người phụ trách
                <input className="apple-input mt-2" name="owner_id" />
              </label>
              <label className="field-label">
                Phân hệ
                <input className="apple-input mt-2" name="module" />
              </label>
              <label className="field-label">
                Thành phần
                <input className="apple-input mt-2" name="component" />
              </label>
              <label className="field-label">
                Khu vực sản phẩm
                <input className="apple-input mt-2" name="product_area" />
              </label>
              <label className="field-label">
                Bản phát hành
                <input className="apple-input mt-2" name="release_id" />
              </label>
              <label className="field-label">
                Mã nguồn bên ngoài
                <input className="apple-input mt-2" name="external_source_id" />
              </label>
              <label className="field-label">
                Trạng thái phê duyệt
                <select className="apple-input mt-2" name="approval_status" defaultValue="DRAFT">
                  <option value="DRAFT">Bản nháp</option>
                  <option value="IN_REVIEW">Đang rà soát</option>
                  <option value="APPROVED">Đã phê duyệt</option>
                  <option value="REJECTED">Từ chối</option>
                </select>
              </label>
              <label className="field-label">
                Phiên bản nguồn
                <input
                  className="apple-input mt-2"
                  name="source_version"
                  defaultValue="1"
                  required
                />
              </label>
              <label className="field-label">
                Người phê duyệt
                <input className="apple-input mt-2" name="approved_by" />
              </label>
              <label className="field-label">
                Thời điểm phê duyệt
                <input className="apple-input mt-2" name="approved_at" type="datetime-local" />
              </label>
              <label className="field-label">
                Hiệu lực từ
                <input className="apple-input mt-2" name="effective_from" type="datetime-local" />
              </label>
              <label className="field-label">
                Liên kết nguồn
                <input className="apple-input mt-2" name="source_url" type="url" />
              </label>
              <label className="field-label">
                Nhãn phân cách bằng dấu phẩy
                <input className="apple-input mt-2" name="tags" />
              </label>
              <label className="field-label md:col-span-2">
                Nội dung tài liệu
                <textarea className="apple-input mt-2 min-h-36" name="content" required />
              </label>
              <div className="action-dialog-footer flex justify-end gap-3 md:col-span-2">
                <button
                  className="secondary-button"
                  type="button"
                  onClick={() => setCreatingSource(false)}
                >
                  Hủy
                </button>
                <button className="apple-button" type="submit">
                  Thêm tài liệu tham chiếu
                </button>
              </div>
            </form>
          </Modal>
        )}
        {sourcesLoading ? (
          <div className="p-5">
            <LoadingState />
          </div>
        ) : sourcesLoadFailed ? (
          <div className="space-y-3 p-5">
            <ErrorState message={error || "Không thể tải tài liệu tham chiếu"} />
            <button className="secondary-button" type="button" onClick={() => void loadSources()}>
              Tải lại
            </button>
          </div>
        ) : (
          <DataTable
            items={sources}
            empty="Chưa có tài liệu tham chiếu"
            columns={[
              { key: "title", label: "Tài liệu" },
              { key: "source_type", label: "Loại", render: (item) => valueLabel(item.source_type) },
              {
                key: "authority",
                label: "Độ tin cậy",
                render: (item) => valueLabel(item.authority),
              },
              {
                key: "module",
                label: "Phạm vi",
                render: (item) =>
                  [item.product_area, item.module, item.component].filter(Boolean).join(" · ") ||
                  "Chưa khai báo",
              },
              {
                key: "index_status",
                label: "Lập chỉ mục",
                render: (item) => valueLabel(String(item.index_status).toUpperCase()),
              },
              ...(canManage
                ? [
                    {
                      key: "actions",
                      label: "Thao tác",
                      render: (item) => (
                        <span className="flex flex-wrap gap-2">
                          <button
                            className="secondary-button"
                            type="button"
                            onClick={async () => {
                              try {
                                await testingApi.reindexKnowledgeSource(item._id);
                                await loadSources();
                              } catch (reason) {
                                setError(messageOf(reason));
                              }
                            }}
                          >
                            Lập chỉ mục lại
                          </button>
                          <button
                            className="secondary-button"
                            type="button"
                            onClick={async () => {
                              const answer = await ask({
                                title: "Lưu trữ tài liệu tham chiếu",
                                description: item.title || item.filename,
                                confirmLabel: "Lưu trữ",
                                danger: true,
                                fields: [
                                  {
                                    name: "reason",
                                    label: "Lý do",
                                    required: true,
                                    multiline: true,
                                  },
                                ],
                              });
                              if (!answer) return;
                              try {
                                await testingApi.archiveKnowledgeSource(item._id, {
                                  expected_revision: item.revision,
                                  reason: answer.reason,
                                });
                                await loadSources();
                              } catch (reason) {
                                setError(messageOf(reason));
                              }
                            }}
                          >
                            Lưu trữ
                          </button>
                        </span>
                      ),
                    },
                  ]
                : []),
            ]}
          />
        )}
      </Panel>
      {dialog}
    </WorkspacePage>
  );
}
