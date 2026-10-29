"use client";
import Image from "next/image";
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

const sourceHierarchyFor = (blocks) => {
  const normalizedId = (value) => (typeof value === "string" ? value.trim() : "");
  const byId = new Map(
    (blocks || [])
      .map((block) => [normalizedId(block.block_id), block])
      .filter(([blockId]) => blockId),
  );
  const hierarchy = new Map();

  for (const block of blocks || []) {
    const blockId = normalizedId(block.block_id);
    const key = blockId || `${block.block_index}`;
    let parentId = normalizedId(block.parent_block_id);
    let depth = 0;
    const visited = new Set([blockId].filter(Boolean));
    let parentLoaded = !parentId;
    let cycle = false;

    while (parentId) {
      const parent = byId.get(parentId);
      if (!parent) break;
      parentLoaded = true;
      if (visited.has(parentId)) {
        cycle = true;
        break;
      }
      visited.add(parentId);
      depth += 1;
      parentId = normalizedId(parent.parent_block_id);
    }

    hierarchy.set(key, { depth: Math.min(depth, 8), parentLoaded, cycle });
  }

  return hierarchy;
};

export default function KnowledgePage({ project, initialQuery = "", useGlobalSearch = false }) {
  const { ask, dialog } = useActionDialog();
  const [query, setQuery] = useState(initialQuery);
  const [result, setResult] = useState(null);
  const [sources, setSources] = useState([]);
  const [error, setError] = useState("");
  const [sourcesLoading, setSourcesLoading] = useState(true);
  const [sourcesLoadFailed, setSourcesLoadFailed] = useState(false);
  const sourcesLoaded = useRef(false);
  const sourceListRequestGeneration = useRef(0);
  const [creatingSource, setCreatingSource] = useState(false);
  const [metadataSource, setMetadataSource] = useState(null);
  const [metadataPage, setMetadataPage] = useState(null);
  const [metadataLoading, setMetadataLoading] = useState(false);
  const [metadataError, setMetadataError] = useState("");
  const [sourceStructurePage, setSourceStructurePage] = useState(null);
  const [sourceStructureLoading, setSourceStructureLoading] = useState(false);
  const [sourceStructureError, setSourceStructureError] = useState("");
  const [sourceImageUrls, setSourceImageUrls] = useState({});
  const [sourceImageLoading, setSourceImageLoading] = useState({});
  const [sourceImageErrors, setSourceImageErrors] = useState({});
  const sourceImageUrlsRef = useRef({});
  const sourceImageRequestGeneration = useRef(0);
  const metadataRequestGeneration = useRef(0);
  const sourceStructureRequestGeneration = useRef(0);
  const projectSearchRequestGeneration = useRef(0);
  const sourceProjectId = useRef(project._id);
  const canManage = project.current_permissions?.includes("knowledge.manage");
  const sourceHierarchy = sourceHierarchyFor(sourceStructurePage?.items);
  const loadSources = useCallback(async () => {
    const requestGeneration = ++sourceListRequestGeneration.current;
    if (!sourcesLoaded.current) setSourcesLoading(true);
    try {
      const nextSources = await testingApi.listKnowledgeSources(project._id);
      if (requestGeneration === sourceListRequestGeneration.current) {
        setSources(nextSources);
        sourcesLoaded.current = true;
        setSourcesLoadFailed(false);
      }
    } catch (reason) {
      if (requestGeneration === sourceListRequestGeneration.current) {
        setError(messageOf(reason));
        if (!sourcesLoaded.current) setSourcesLoadFailed(true);
      }
    } finally {
      if (requestGeneration === sourceListRequestGeneration.current) {
        setSourcesLoading(false);
      }
    }
  }, [project._id]);
  const loadChunkMetadata = async (source, cursor = "") => {
    const requestGeneration = ++metadataRequestGeneration.current;
    setMetadataLoading(true);
    setMetadataError("");
    try {
      const page = await testingApi.listKnowledgeSourceChunks(project._id, source._id, 50, cursor);
      if (requestGeneration === metadataRequestGeneration.current) {
        setMetadataPage((previous) =>
          cursor && previous
            ? { ...page, items: [...(previous.items || []), ...(page.items || [])] }
            : page,
        );
      }
    } catch (reason) {
      if (requestGeneration === metadataRequestGeneration.current) {
        setMetadataError(messageOf(reason));
      }
    } finally {
      if (requestGeneration === metadataRequestGeneration.current) {
        setMetadataLoading(false);
      }
    }
  };
  const loadSourceStructure = async (source, offset = 0) => {
    const requestGeneration = ++sourceStructureRequestGeneration.current;
    setSourceStructureLoading(true);
    setSourceStructureError("");
    try {
      const page = await testingApi.listKnowledgeSourceStructure(
        project._id,
        source._id,
        offset,
        100,
      );
      if (requestGeneration === sourceStructureRequestGeneration.current) {
        setSourceStructurePage((previous) =>
          offset && previous
            ? { ...page, items: [...(previous.items || []), ...(page.items || [])] }
            : page,
        );
      }
    } catch (reason) {
      if (requestGeneration === sourceStructureRequestGeneration.current) {
        setSourceStructureError(messageOf(reason));
      }
    } finally {
      if (requestGeneration === sourceStructureRequestGeneration.current) {
        setSourceStructureLoading(false);
      }
    }
  };
  const clearSourceImageUrls = () => {
    sourceImageRequestGeneration.current += 1;
    Object.values(sourceImageUrlsRef.current).forEach((url) => URL.revokeObjectURL(url));
    sourceImageUrlsRef.current = {};
    setSourceImageUrls({});
    setSourceImageLoading({});
    setSourceImageErrors({});
  };
  const clearSourceInspection = () => {
    metadataRequestGeneration.current += 1;
    sourceStructureRequestGeneration.current += 1;
    clearSourceImageUrls();
    setMetadataPage(null);
    setMetadataLoading(false);
    setMetadataError("");
    setSourceStructurePage(null);
    setSourceStructureLoading(false);
    setSourceStructureError("");
  };
  const loadSourceImage = async (source, block) => {
    const key = `${source._id}:${block.block_index}`;
    const requestGeneration = sourceImageRequestGeneration.current;
    setSourceImageLoading((current) => ({ ...current, [key]: true }));
    setSourceImageErrors((current) => ({ ...current, [key]: "" }));
    try {
      const blob = await testingApi.getKnowledgeSourceImage(
        project._id,
        source._id,
        block.block_index,
      );
      const url = URL.createObjectURL(blob);
      if (requestGeneration !== sourceImageRequestGeneration.current) {
        URL.revokeObjectURL(url);
        return;
      }
      const previousUrl = sourceImageUrlsRef.current[key];
      if (previousUrl) URL.revokeObjectURL(previousUrl);
      sourceImageUrlsRef.current[key] = url;
      setSourceImageUrls((current) => ({ ...current, [key]: url }));
    } catch (reason) {
      if (requestGeneration === sourceImageRequestGeneration.current) {
        setSourceImageErrors((current) => ({ ...current, [key]: messageOf(reason) }));
      }
    } finally {
      if (requestGeneration === sourceImageRequestGeneration.current) {
        setSourceImageLoading((current) => ({ ...current, [key]: false }));
      }
    }
  };
  useEffect(() => {
    loadSources();
  }, [loadSources]);
  useEffect(() => {
    if (sourceProjectId.current !== project._id) {
      sourceProjectId.current = project._id;
      sourcesLoaded.current = false;
      setSources([]);
      setSourcesLoadFailed(false);
      setSourcesLoading(true);
      setError("");
      metadataRequestGeneration.current += 1;
      sourceStructureRequestGeneration.current += 1;
      setMetadataSource(null);
      setMetadataPage(null);
      setMetadataLoading(false);
      setMetadataError("");
      setSourceStructurePage(null);
      setSourceStructureLoading(false);
      setSourceStructureError("");
      setSourceImageUrls({});
      setSourceImageLoading({});
      setSourceImageErrors({});
    }
    return () => {
      sourceListRequestGeneration.current += 1;
      metadataRequestGeneration.current += 1;
      sourceStructureRequestGeneration.current += 1;
      sourceImageRequestGeneration.current += 1;
      Object.values(sourceImageUrlsRef.current).forEach((url) => URL.revokeObjectURL(url));
      sourceImageUrlsRef.current = {};
    };
  }, [project._id]);
  useEffect(() => {
    if (!useGlobalSearch || !initialQuery) return;
    const requestGeneration = ++projectSearchRequestGeneration.current;
    testingApi
      .searchProject(project._id, initialQuery)
      .then((searchResult) => {
        if (requestGeneration === projectSearchRequestGeneration.current) {
          setResult(searchResult);
        }
      })
      .catch((reason) => {
        if (requestGeneration === projectSearchRequestGeneration.current) {
          setError(messageOf(reason));
        }
      });
    return () => {
      if (requestGeneration === projectSearchRequestGeneration.current) {
        projectSearchRequestGeneration.current += 1;
      }
    };
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
            placeholder="Nhập nội dung cần tìm, ví dụ: quy tắc đăng nhập hoặc ca kiểm thử"
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
                label: "Mức độ chính thức",
                render: (item) => valueLabel(item.authority),
              },
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
                label: "Mức độ chính thức",
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
                        <span className="flex max-w-[28rem] flex-wrap items-center gap-2">
                          <button
                            className="secondary-button !min-h-9 !px-3 !py-1.5 text-xs"
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
                            className="secondary-button !min-h-9 !px-3 !py-1.5 text-xs"
                            type="button"
                            onClick={async () => {
                              await ask({
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
                                onConfirm: async (answer) => {
                                  try {
                                    await testingApi.archiveKnowledgeSource(item._id, {
                                      expected_revision: item.revision,
                                      reason: answer.reason,
                                    });
                                    await loadSources();
                                  } catch (reason) {
                                    throw new Error(messageOf(reason));
                                  }
                                },
                              });
                            }}
                          >
                            Lưu trữ
                          </button>
                        </span>
                      ),
                    },
                  ]
                : []),
              {
                key: "metadata",
                label: "Chỉ mục",
                render: (item) => (
                  <button
                    className="secondary-button"
                    type="button"
                    onClick={() => {
                      clearSourceInspection();
                      setMetadataSource(item);
                      void loadChunkMetadata(item);
                    }}
                  >
                    Xem chi tiết chỉ mục
                  </button>
                ),
              },
            ]}
          />
        )}
      </Panel>
      <Modal
        isOpen={Boolean(metadataSource)}
        onClose={() => {
          clearSourceInspection();
          setMetadataSource(null);
        }}
        ariaLabel="Chi tiết các đoạn tài liệu đã lập chỉ mục"
        className="max-h-[94dvh] max-w-6xl"
      >
        <ModalHeader>
          <ModalTitle>Chi tiết chỉ mục tài liệu</ModalTitle>
        </ModalHeader>
        <details className="mb-4 rounded-lg border border-border bg-surface-quiet p-4 text-sm">
          <summary className="cursor-pointer font-medium">
            Cách hệ thống tìm nội dung trong tài liệu
          </summary>
          <div className="pt-1">
            <div className="mt-3 grid gap-3 md:grid-cols-3">
              <div className="min-w-0 rounded-md bg-surface p-3">
                <p className="font-semibold">Mã bản ghi</p>
                <p className="mt-1 text-ink-muted">
                  Mỗi đoạn được gán một mã để hệ thống tìm và cập nhật đúng bản ghi. Mã này không
                  phải mã tài liệu hay mã yêu cầu.
                </p>
              </div>
              <div className="min-w-0 rounded-md bg-surface p-3">
                <p className="font-semibold">Dữ liệu tìm theo ý nghĩa</p>
                <p className="mt-1 text-ink-muted">
                  Hệ thống chuyển nội dung đoạn thành dãy số để tìm các nội dung gần nghĩa. Dãy số
                  này không cần hiển thị khi đọc tài liệu.
                </p>
              </div>
              <div className="min-w-0 rounded-md bg-surface p-3">
                <p className="font-semibold">Nội dung và thông tin nguồn</p>
                <p className="mt-1 text-ink-muted">
                  Nội dung đoạn đi kèm thông tin để lọc kết quả và mở lại đúng tài liệu, phiên bản,
                  trang hoặc vị trí nguồn khi có.
                </p>
              </div>
            </div>
            <p className="mt-3 text-ink-muted">
              Tài liệu dài được chia thành nhiều đoạn để tìm kiếm. Bảng có thể được tách theo hàng
              và lặp tiêu đề cột; ảnh gốc được lưu riêng, còn bản ghi tìm kiếm giữ nội dung trích
              xuất hoặc liên kết ảnh khi có.
            </p>
            <p className="mt-2 text-ink-muted">
              Quyền truy cập tài liệu vẫn được kiểm tra trước khi hệ thống trả kết quả tìm kiếm.
            </p>
          </div>
        </details>
        {metadataSource && (
          <div className="space-y-4 p-5">
            <div className="rounded-lg bg-surface-quiet p-4 text-sm">
              <p className="font-semibold">{metadataSource.title || metadataSource.filename}</p>
              <p className="mt-1 text-ink-muted">
                Trạng thái chỉ mục:{" "}
                {valueLabel(String(metadataSource.index_status || "unknown").toUpperCase())}
              </p>
              <div className="mt-3 grid gap-2 text-xs text-ink-muted sm:grid-cols-3">
                <p>
                  <strong>Nguồn:</strong> tệp gốc và nội dung đã phân tích được quản lý riêng; khối
                  có mã cha khi bộ phân tích cung cấp.
                </p>
                <p>
                  <strong>Kho tìm kiếm:</strong> lưu mã bản ghi, dữ liệu tìm theo ý nghĩa và nội
                  dung đoạn kèm thông tin nguồn.
                </p>
                <p>
                  <strong>Cấu trúc nguồn:</strong> đoạn có thể trỏ về khối cha và đường dẫn trong
                  tài liệu; kho tìm kiếm không tự tổ chức tài liệu thành cây.
                </p>
              </div>
            </div>
            {metadataError && <ErrorState message={metadataError} />}
            <details className="rounded-lg border border-border p-4">
              <summary className="cursor-pointer text-sm font-semibold">
                Cấu trúc các phần trong tài liệu
              </summary>
              <div className="mt-3 space-y-3 text-sm">
                <p className="text-ink-muted">
                  Đây là các phần mà bộ phân tích nhận diện được trong tài liệu. Quan hệ cha–con chỉ
                  hiển thị khi nguồn cung cấp; một số tài liệu không có cấu trúc phân cấp.
                </p>
                {!sourceStructurePage && !sourceStructureLoading && (
                  <button
                    className="secondary-button"
                    type="button"
                    onClick={() => void loadSourceStructure(metadataSource)}
                  >
                    Tải cấu trúc nguồn
                  </button>
                )}
                {sourceStructureError && <ErrorState message={sourceStructureError} />}
                {sourceStructureLoading && <LoadingState />}
                {sourceStructurePage && (
                  <>
                    <p className="text-xs text-ink-muted">
                      {sourceStructurePage.source_structure_available
                        ? `${sourceStructurePage.source_structure_count ?? sourceStructurePage.items.length} khối nguồn`
                        : "Bộ phân tích không lưu cấu trúc khối cho tài liệu này"}
                      {sourceStructurePage.parse_report?.page_count
                        ? ` · ${sourceStructurePage.parse_report.page_count} trang`
                        : ""}
                      {sourceStructurePage.parse_report?.ocr_enabled === true
                        ? ` · OCR đã bật${sourceStructurePage.parse_report.ocr_language ? ` (${sourceStructurePage.parse_report.ocr_language})` : ""}`
                        : sourceStructurePage.parse_report?.ocr_enabled === false
                          ? " · OCR không được dùng"
                          : " · trạng thái OCR không được ghi nhận"}
                    </p>
                    {sourceStructurePage.items.length > 0 && (
                      <ol className="max-h-[45dvh] space-y-2 overflow-auto">
                        {sourceStructurePage.items.map((block) => {
                          const firstLine = String(block.text_preview || block.text || "").split(
                            "\n",
                            1,
                          )[0];
                          const hierarchy = sourceHierarchy.get(
                            typeof block.block_id === "string" && block.block_id.trim()
                              ? block.block_id.trim()
                              : `${block.block_index}`,
                          );
                          return (
                            <li
                              className="min-w-0 rounded-md bg-surface-quiet p-3"
                              key={`${block.block_index}-${block.block_id || "source-block"}`}
                              style={{
                                marginInlineStart: `${(hierarchy?.depth || 0) * 16}px`,
                              }}
                            >
                              <div className="flex flex-wrap items-center gap-2">
                                <span className="font-medium">
                                  {valueLabel(block.type || "khối nguồn")}
                                </span>
                                {block.page_no != null && (
                                  <span className="text-ink-muted">Trang {block.page_no}</span>
                                )}
                                <span className="break-all text-xs text-ink-muted">
                                  {block.block_id || "Không có mã khối"}
                                </span>
                                {block.parent_block_id && (
                                  <span className="break-all text-xs text-ink-muted">
                                    Khối cha: {block.parent_block_id}
                                  </span>
                                )}
                                {block.level != null && (
                                  <span className="text-xs text-ink-muted">
                                    Cấp bộ phân tích {block.level}
                                  </span>
                                )}
                                {hierarchy?.cycle && (
                                  <span className="text-xs text-danger">
                                    Quan hệ cha–con bị vòng lặp
                                  </span>
                                )}
                                {block.parent_block_id && !hierarchy?.parentLoaded && (
                                  <span className="text-xs text-ink-muted">
                                    Khối cha chưa nằm trong phần đã tải
                                  </span>
                                )}
                              </div>
                              <p className="mt-1 break-words">
                                {firstLine || "Khối không có văn bản trích xuất"}
                                {block.text_truncated && (
                                  <span className="text-ink-muted">
                                    {" "}
                                    · Bản xem trước, {block.text_length} ký tự
                                  </span>
                                )}
                              </p>
                              {block.image_metadata?.asset_available === true && (
                                <div className="mt-2 space-y-2">
                                  {sourceImageUrls[`${metadataSource._id}:${block.block_index}`] ? (
                                    <Image
                                      alt={`Ảnh nguồn ${block.image_metadata.image_id || block.block_id || block.block_index}`}
                                      className="max-h-96 max-w-full rounded-md border border-border object-contain"
                                      height={Number(block.image_metadata.height) || 800}
                                      unoptimized
                                      src={
                                        sourceImageUrls[
                                          `${metadataSource._id}:${block.block_index}`
                                        ]
                                      }
                                      width={Number(block.image_metadata.width) || 1200}
                                    />
                                  ) : (
                                    <button
                                      className="secondary-button"
                                      type="button"
                                      disabled={
                                        sourceImageLoading[
                                          `${metadataSource._id}:${block.block_index}`
                                        ]
                                      }
                                      onClick={() => void loadSourceImage(metadataSource, block)}
                                    >
                                      {sourceImageLoading[
                                        `${metadataSource._id}:${block.block_index}`
                                      ]
                                        ? "Đang tải ảnh nguồn…"
                                        : "Xem ảnh nguồn"}
                                    </button>
                                  )}
                                  {sourceImageErrors[
                                    `${metadataSource._id}:${block.block_index}`
                                  ] && (
                                    <ErrorState
                                      message={
                                        sourceImageErrors[
                                          `${metadataSource._id}:${block.block_index}`
                                        ]
                                      }
                                    />
                                  )}
                                </div>
                              )}
                              <p className="mt-1 break-all text-xs text-ink-muted">
                                Khối cha: {block.parent_block_id || "Không có mã cha"}
                              </p>
                            </li>
                          );
                        })}
                      </ol>
                    )}
                    {sourceStructurePage.next_offset != null && (
                      <button
                        className="secondary-button"
                        type="button"
                        disabled={sourceStructureLoading}
                        onClick={() =>
                          void loadSourceStructure(metadataSource, sourceStructurePage.next_offset)
                        }
                      >
                        Tải thêm khối nguồn
                      </button>
                    )}
                    {sourceStructurePage.parse_report?.unprocessed_block_count > 0 && (
                      <p className="rounded-md border border-border p-3 text-sm text-ink-muted">
                        Có {sourceStructurePage.parse_report.unprocessed_block_count} khối chưa được
                        trích xuất đầy đủ; trạng thái này không có nghĩa OCR đã chính xác.
                      </p>
                    )}
                    {sourceStructurePage.parse_report?.unprocessed_blocks?.some(
                      (block) => typeof block.ocr_page_confidence === "number",
                    ) && (
                      <div className="rounded-md border border-border p-3 text-sm">
                        <p className="font-medium">Điểm OCR do bộ phân tích cung cấp theo trang</p>
                        <p className="mt-1 text-ink-muted">
                          Đây là chẩn đoán của bộ phân tích, không phải cam kết độ chính xác nội
                          dung.
                        </p>
                        <ul className="mt-2 flex flex-wrap gap-x-4 gap-y-1 text-xs">
                          {sourceStructurePage.parse_report.unprocessed_blocks
                            .filter((block) => typeof block.ocr_page_confidence === "number")
                            .map((block, index) => (
                              <li key={`${block.page_no ?? "page"}-${index}`}>
                                Trang {block.page_no ?? "không rõ"}:{" "}
                                {block.ocr_page_confidence.toFixed(3)}
                              </li>
                            ))}
                        </ul>
                      </div>
                    )}
                  </>
                )}
              </div>
            </details>
            {metadataLoading ? (
              <LoadingState />
            ) : metadataPage?.items?.length ? (
              <div className="space-y-3">
                <p className="text-xs text-ink-muted">
                  Đã tải {metadataPage.items.length} đoạn
                  {metadataPage.next_cursor ? "; còn trang tiếp theo" : "; hết kết quả"}.
                </p>
                {metadataPage.items.map((chunk) => {
                  const metadata = chunk.metadata || {};
                  return (
                    <article
                      className="min-w-0 rounded-lg border border-border p-4"
                      key={chunk.point_id}
                    >
                      <div className="flex flex-wrap items-center justify-between gap-2">
                        <h3 className="text-sm font-semibold">
                          Đoạn {Number(metadata.chunk_index ?? 0) + 1}
                        </h3>
                      </div>
                      <dl className="mt-3 grid gap-x-6 gap-y-2 text-sm sm:grid-cols-2 lg:grid-cols-3">
                        {[
                          ["Nguồn", metadata.source_name || metadata.title],
                          ["Vị trí", metadata.section],
                          ["Trang", (metadata.page_numbers || []).join(", ")],
                          ["Nội dung", valueLabel(metadata.content_type)],
                          ["Trạng thái phân tích", valueLabel(metadata.extraction_status)],
                        ]
                          .filter(
                            ([, value]) => value !== null && value !== undefined && value !== "",
                          )
                          .map(([label, value]) => (
                            <div className="min-w-0" key={label}>
                              <dt className="text-xs text-ink-muted">{label}</dt>
                              <dd className="break-words">{value}</dd>
                            </div>
                          ))}
                      </dl>
                      <details className="mt-3 rounded-md bg-surface-quiet p-3">
                        <summary className="cursor-pointer text-sm font-medium">
                          Xem toàn bộ thông tin nguồn và chỉ mục
                        </summary>
                        <span className="mt-2 block break-all text-xs text-ink-muted">
                          Mã bản ghi tìm kiếm: {chunk.point_id}
                        </span>
                        <dl className="mt-3 grid gap-x-6 gap-y-2 text-sm sm:grid-cols-2 lg:grid-cols-3">
                          {[
                            ["Mã dự án", metadata.project_id],
                            ["Loại đối tượng nguồn", valueLabel(metadata.artifact_type)],
                            ["Mã đối tượng nguồn", metadata.artifact_id],
                            ["Mã phiên bản đối tượng", metadata.artifact_version_id],
                            ["Tên nguồn", metadata.source_name],
                            ["Tác giả nguồn", metadata.author],
                            ["Mức độ thẩm quyền nguồn", valueLabel(metadata.authority)],
                            ["Trạng thái nguồn", valueLabel(metadata.status)],
                            ["Phạm vi hiển thị", valueLabel(metadata.visibility)],
                            ["Loại nội dung", valueLabel(metadata.content_type)],
                            ["Tình trạng duyệt nguồn", valueLabel(metadata.approval_status)],
                            ["Lĩnh vực sản phẩm", metadata.product_area],
                            ["Module", metadata.module],
                            ["Thành phần", metadata.component],
                            ["Mục nguồn", metadata.section],
                            ["Trang khai báo", metadata.page],
                            ["Mã bản phát hành", metadata.release_id],
                            ["Mã nguồn bên ngoài", metadata.external_source_id],
                            ["Thẻ", (metadata.tags || []).join(", ")],
                            ["Người duyệt nguồn", metadata.approved_by],
                            [
                              "Thời điểm duyệt",
                              metadata.approved_at
                                ? new Date(metadata.approved_at).toLocaleString("vi-VN")
                                : null,
                            ],
                            [
                              "Thời điểm có hiệu lực",
                              metadata.effective_from
                                ? new Date(metadata.effective_from).toLocaleString("vi-VN")
                                : null,
                            ],
                            [
                              "Yêu cầu liên quan",
                              [
                                ...(metadata.requirement_ids || []),
                                ...(metadata.requirement_version_ids || []),
                                ...(metadata.linked_requirement_version_ids || []),
                              ].join(", "),
                            ],
                            [
                              "Tiêu chí chấp nhận liên quan",
                              (metadata.acceptance_criterion_ids || []).join(", "),
                            ],
                            [
                              "Tài liệu nguồn liên quan",
                              (metadata.source_document_ids || []).join(", "),
                            ],
                            [
                              "Phiên bản ca kiểm thử liên quan",
                              [
                                ...(metadata.test_case_version_ids || []),
                                metadata.test_case_version_id,
                              ]
                                .filter(Boolean)
                                .join(", "),
                            ],
                            ["Đợt chạy kiểm thử liên quan", metadata.test_run_id],
                            ["Kết quả kiểm thử liên quan", metadata.linked_test_result_id],
                            ["Mã tài liệu", metadata.document_id],
                            ["Mã tài liệu nguồn", metadata.source_document_id],
                            ["Loại nguồn", valueLabel(metadata.source_type)],
                            ["Định dạng nội dung", valueLabel(metadata.content_format)],
                            ["Dấu băm nguồn", metadata.source_hash],
                            ["Dấu băm nội dung chuẩn hóa", metadata.normalized_content_hash],
                            ["Tiêu đề trong chỉ mục", metadata.title],
                            ["Mã đoạn", metadata.chunk_id],
                            ["Mã đoạn ổn định theo nguồn", metadata.logical_chunk_id],
                            ["Dấu băm nội dung đoạn", metadata.chunk_hash],
                            ["Loại đoạn", valueLabel(metadata.chunk_type)],
                            [
                              "Loại khối nguồn",
                              (metadata.structure_types || []).map(valueLabel).join(", "),
                            ],
                            ["Phiên bản nguồn", metadata.version || metadata.source_version],
                            ["Mã phiên bản chỉ mục", metadata.index_generation],
                            ["Mã lần xử lý tài liệu", metadata.indexing_attempt_id],
                            ["Mô hình biểu diễn", metadata.embedding_model],
                            [
                              "Cách tạo đầu vào biểu diễn",
                              valueLabel(metadata.embedding_input_mode),
                            ],
                            ["Dấu băm đầu vào mô hình biểu diễn", metadata.embedding_input_hash],
                            ["Phạm vi điểm tóm tắt", valueLabel(metadata.summary_scope)],
                            ["Số đoạn nguồn của tài liệu", metadata.document_chunk_count],
                            ["Số ký tự mẫu tóm tắt", metadata.summary_sample_char_count],
                            [
                              "Mã đoạn được lấy mẫu",
                              (metadata.summary_sample_chunk_ids || []).join(", "),
                            ],
                            [
                              "Trang được lấy mẫu",
                              (metadata.summary_sample_page_numbers || []).join(", "),
                            ],
                            [
                              "Bộ phân tích",
                              metadata.parser_name
                                ? `${metadata.parser_name}${metadata.parser_version ? ` · ${metadata.parser_version}` : ""}`
                                : null,
                            ],
                            [
                              "OCR",
                              metadata.ocr_enabled === true
                                ? `Đã bật${metadata.ocr_language ? ` · ${metadata.ocr_language}` : ""}`
                                : metadata.ocr_enabled === false
                                  ? "Không bật"
                                  : null,
                            ],
                            ["Tổng số trang nguồn", metadata.page_count],
                            ["Số khối nguồn parser trả về", metadata.source_block_count],
                            ["Trạng thái trích xuất", valueLabel(metadata.extraction_status)],
                            ["Khối chưa xử lý", metadata.unprocessed_block_count],
                            ["Số cảnh báo trích xuất", metadata.extraction_warning_count],
                            [
                              "Mã cảnh báo trích xuất",
                              (metadata.extraction_warning_codes || []).map(valueLabel).join(", "),
                            ],
                            ["Phương pháp trích xuất", valueLabel(metadata.extraction_method)],
                            [
                              "Thời điểm tài liệu được tạo",
                              metadata.source_created_at
                                ? new Date(metadata.source_created_at).toLocaleString("vi-VN")
                                : null,
                            ],
                            [
                              "Thời điểm tài liệu được cập nhật",
                              metadata.source_updated_at
                                ? new Date(metadata.source_updated_at).toLocaleString("vi-VN")
                                : null,
                            ],
                            [
                              "Thời điểm lập chỉ mục",
                              metadata.indexed_at
                                ? new Date(metadata.indexed_at).toLocaleString("vi-VN")
                                : null,
                            ],
                            [
                              "Số ký tự / từ",
                              metadata.char_count != null
                                ? `${metadata.char_count} / ${metadata.word_count ?? "—"}`
                                : null,
                            ],
                            ["Trang nguồn", (metadata.page_numbers || []).join(", ")],
                            [
                              "Khoảng trang",
                              metadata.page_start != null || metadata.page_end != null
                                ? `${metadata.page_start ?? "—"}–${metadata.page_end ?? "—"}`
                                : null,
                            ],
                          ]
                            .filter(
                              ([, value]) => value !== null && value !== undefined && value !== "",
                            )
                            .map(([label, value]) => (
                              <div className="min-w-0" key={label}>
                                <dt className="text-xs text-ink-muted">{label}</dt>
                                <dd className="break-words">{value}</dd>
                              </div>
                            ))}
                        </dl>
                      </details>
                      <details className="mt-3 rounded-md bg-surface-quiet p-3">
                        <summary className="cursor-pointer text-sm font-medium">
                          Văn bản đoạn
                        </summary>
                        <p className="mt-2 whitespace-pre-wrap break-words text-sm text-ink">
                          {chunk.text}
                        </p>
                      </details>
                      <details className="mt-2 rounded-md bg-surface-quiet p-3">
                        <summary className="cursor-pointer text-sm font-medium">
                          Vị trí và liên kết khối nguồn
                        </summary>
                        {metadata.source_spans?.length ? (
                          <ol className="mt-3 space-y-3">
                            {metadata.source_spans.map((span, index) => (
                              <li
                                className="border-l-2 border-accent pl-3 text-sm"
                                key={`${span.block_id || "block"}-${index}`}
                              >
                                <p>
                                  <strong>Khối:</strong>{" "}
                                  {span.block_id || "Parser không cung cấp mã khối"}
                                </p>
                                <p>
                                  <strong>Khối cha:</strong>{" "}
                                  {span.parent_block_id || "Không có mã khối cha"}
                                </p>
                                <p>
                                  <strong>Chuỗi tổ tiên trong tài liệu:</strong>{" "}
                                  {span.ancestor_chain_status === "ROOT"
                                    ? "Khối gốc"
                                    : span.ancestor_chain_status === "COMPLETE"
                                      ? span.ancestor_block_ids?.join(" → ") ||
                                        "Không có mã khối tổ tiên"
                                      : span.ancestor_chain_status === "PARTIAL"
                                        ? `${span.ancestor_block_ids?.join(" → ") || "Chưa có tổ tiên nội bộ"} · nguồn còn thiếu khối cha được tham chiếu`
                                        : "Point cũ chưa ghi nhận trạng thái chuỗi tổ tiên"}
                                </p>
                                <p>
                                  <strong>Loại:</strong> {valueLabel(span.content_type)}
                                </p>
                                <p>
                                  <strong>Đường dẫn mục:</strong>{" "}
                                  {(span.section_path || []).join(" / ") || "Không có"}
                                </p>
                                {span.table_metadata && (
                                  <div>
                                    <p>
                                      <strong>Bảng:</strong>{" "}
                                      {span.table_metadata.table_id || "Không có mã"}
                                      {span.table_metadata.row_count != null
                                        ? ` · ${span.table_metadata.row_count} hàng`
                                        : ""}
                                      {span.table_metadata.column_count != null
                                        ? ` · ${span.table_metadata.column_count} cột`
                                        : ""}
                                      {span.table_metadata.column_headers?.length
                                        ? ` · Tiêu đề cột: ${span.table_metadata.column_headers.join(" | ")}`
                                        : ""}
                                      {span.table_metadata.metadata_source
                                        ? ` · Metadata từ ${span.table_metadata.metadata_source}`
                                        : ""}
                                    </p>
                                    {span.table_metadata.cell_spans?.length > 0 && (
                                      <details className="mt-2 rounded-md bg-surface-quiet p-2">
                                        <summary className="cursor-pointer">
                                          Vị trí các ô trong đoạn (
                                          {span.table_metadata.cell_spans.length})
                                        </summary>
                                        <ul className="mt-2 space-y-1">
                                          {span.table_metadata.cell_spans.map((cell) => (
                                            <li
                                              className="break-words"
                                              key={`${cell.row_index}-${cell.column_index}-${cell.chunk_start}`}
                                            >
                                              Hàng {cell.row_index + 1}, cột {cell.column_index + 1}
                                              : {chunk.text.slice(cell.chunk_start, cell.chunk_end)}{" "}
                                              · nguồn {cell.source_start}–{cell.source_end}, đoạn{" "}
                                              {cell.chunk_start}–{cell.chunk_end}
                                            </li>
                                          ))}
                                        </ul>
                                      </details>
                                    )}
                                  </div>
                                )}
                                {span.image_metadata && (
                                  <p>
                                    <strong>Hình:</strong>{" "}
                                    {span.image_metadata.image_id || "Không có mã"}
                                    {span.image_metadata.extracted_text_present === true
                                      ? " · Có văn bản trích xuất"
                                      : " · Không có văn bản trích xuất"}
                                    {span.image_metadata.page_ocr_confidence != null
                                      ? ` · Điểm OCR cấp trang ${span.image_metadata.page_ocr_confidence}`
                                      : ""}
                                    {span.image_metadata.asset_available === true
                                      ? ` · Ảnh nguồn đã lưu riêng tư${span.image_metadata.width && span.image_metadata.height ? ` (${span.image_metadata.width} × ${span.image_metadata.height})` : ""}`
                                      : span.image_metadata.asset_status === "FAILED"
                                        ? " · Lưu tệp ảnh thất bại, cần xử lý lại tài liệu"
                                        : span.image_metadata.asset_status === "UNAVAILABLE"
                                          ? " · Bộ phân tích không cung cấp dữ liệu ảnh"
                                          : " · Chưa yêu cầu lưu tệp ảnh riêng"}
                                  </p>
                                )}
                                <p>
                                  <strong>Trang/vùng:</strong>{" "}
                                  {(span.locations || [])
                                    .map((location) => {
                                      const box = location.bbox;
                                      const coordinates =
                                        box &&
                                        [box.x0, box.y0, box.x1, box.y1].every(Number.isFinite)
                                          ? ` · vùng ${[box.x0, box.y0, box.x1, box.y1].join(", ")}`
                                          : "";
                                      return `Trang ${location.page_no ?? "không rõ"}${coordinates}`;
                                    })
                                    .join("; ") || "Parser không cung cấp vị trí"}
                                </p>
                                <p>
                                  <strong>Offset khối / đoạn:</strong> {span.source_start ?? "—"}–
                                  {span.source_end ?? "—"} / {span.chunk_start ?? "—"}–
                                  {span.chunk_end ?? "—"} ({span.offset_basis || "không rõ cơ sở"})
                                </p>
                                {span.source_segments?.length > 0 && (
                                  <p>
                                    <strong>Ánh xạ từng phần:</strong>{" "}
                                    {span.source_segments
                                      .map((segment) => {
                                        const segmentLabel =
                                          segment.role === "REPEATED_HEADER"
                                            ? "tiêu đề bảng lặp"
                                            : segment.role === "HEADER"
                                              ? "tiêu đề bảng"
                                              : segment.role === "DATA_ROWS"
                                                ? "các hàng dữ liệu"
                                                : valueLabel(segment.role);
                                        return `${segmentLabel}: nguồn ${segment.source_start}–${segment.source_end} → đoạn ${segment.chunk_start}–${segment.chunk_end}`;
                                      })
                                      .join("; ")}
                                  </p>
                                )}
                              </li>
                            ))}
                          </ol>
                        ) : (
                          <p className="mt-2 text-sm text-ink-muted">
                            Không có liên kết đến phần nguồn cho đoạn này.
                          </p>
                        )}
                      </details>
                    </article>
                  );
                })}
                {metadataPage.next_cursor && (
                  <button
                    className="secondary-button"
                    type="button"
                    disabled={metadataLoading}
                    onClick={() => void loadChunkMetadata(metadataSource, metadataPage.next_cursor)}
                  >
                    Tải thêm đoạn
                  </button>
                )}
              </div>
            ) : !metadataError ? (
              <p className="rounded-lg border border-border p-5 text-sm text-ink-muted">
                Chưa tìm thấy đoạn tìm kiếm cho phiên bản này. Nguồn có thể chưa được lập chỉ mục,
                dùng kiểu chỉ mục khác hoặc chưa có thông tin chi tiết cho từng đoạn.
              </p>
            ) : null}
          </div>
        )}
      </Modal>
      {dialog}
    </WorkspacePage>
  );
}
