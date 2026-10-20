import DataTable from "../../../components/DataTable";
import { Panel, StatusPill } from "../../../components/WorkspacePrimitives";
import { messageOf, valueLabel } from "../../../lib/testing";
import { testingApi } from "../../../services/testing.service";
import {
  REQUIREMENT_SOURCE_APPROVAL_OPTIONS,
  REQUIREMENT_SOURCE_AUTHORITY_OPTIONS,
  REQUIREMENT_SOURCE_TYPE_OPTIONS,
} from "./requirements.model";

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
      label: "Thời điểm phê duyệt ISO 8601",
      initialValue: item.approved_at || "",
    },
    {
      name: "source_version",
      label: "Phiên bản nguồn",
      initialValue: item.source_version || "1",
      required: true,
    },
    {
      name: "effective_from",
      label: "Hiệu lực từ ISO 8601",
      initialValue: item.effective_from || "",
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

export default function RequirementSourceDocumentsPanel({
  items,
  members,
  can,
  currentUserId,
  isPlatformAdmin,
  ask,
  reload,
  onError,
}) {
  const changeAccess = async (item) => {
    const answer = await ask({
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
            label: member.user_label || member.user_id,
          })),
        },
      ],
    });
    if (!answer) return;
    if (answer.visibility === "shared" && answer.shared_with.length === 0) {
      onError("Chọn ít nhất một thành viên để chia sẻ tài liệu");
      return;
    }
    try {
      await testingApi.updateRequirementDocumentAccess(item._id, {
        expected_revision: item.revision,
        visibility: answer.visibility,
        shared_with: answer.visibility === "shared" ? answer.shared_with : [],
      });
      await reload();
    } catch (reason) {
      onError(messageOf(reason));
    }
  };
  const enableAiRead = async (item) => {
    try {
      await testingApi.updateRequirementDocumentAiRead(item._id, {
        expected_revision: item.revision,
        ai_enabled: true,
      });
      await reload();
    } catch (reason) {
      onError(messageOf(reason));
    }
  };
  const classify = async (item) => {
    const answer = await ask({
      title: "Phân loại tài liệu nguồn",
      description: item.filename,
      confirmLabel: "Lưu metadata",
      fields: metadataFields(item),
    });
    if (!answer) return;
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
        approved_at: answer.approved_at || null,
        source_version: answer.source_version,
        effective_from: answer.effective_from || null,
        tags: answer.tags
          .split(",")
          .map((value) => value.trim())
          .filter(Boolean),
      });
      await reload();
    } catch (reason) {
      onError(messageOf(reason));
    }
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

  const changeArchiveStatus = async (item, restore) => {
    const answer = await ask({
      title: restore ? "Khôi phục tài liệu nguồn" : "Lưu trữ tài liệu nguồn",
      description: item.filename,
      confirmLabel: restore ? "Khôi phục" : "Lưu trữ",
      danger: !restore,
      fields: lifecycleFields(),
    });
    if (!answer) return;
    try {
      const payload = { expected_revision: item.revision, reason: answer.reason };
      if (restore) await testingApi.restoreRequirementDocument(item._id, payload);
      else await testingApi.archiveRequirementDocument(item._id, payload);
      await reload();
    } catch (reason) {
      onError(messageOf(reason));
    }
  };

  return (
    <Panel title="Kho tài liệu nguồn">
      <DataTable
        items={items}
        empty="Chưa có tài liệu nguồn"
        columns={[
          { key: "filename", label: "Tên tệp" },
          { key: "format", label: "Định dạng" },
          {
            key: "source_type",
            label: "Loại nguồn",
            render: (item) => valueLabel(item.source_type || "REFERENCE"),
          },
          {
            key: "authority",
            label: "Thẩm quyền",
            render: (item) => valueLabel(item.authority || "PROJECT_REFERENCE"),
          },
          {
            key: "module",
            label: "Phạm vi",
            render: (item) =>
              [item.product_area, item.module, item.component].filter(Boolean).join(" · ") ||
              "Chưa khai báo",
          },
          {
            key: "status",
            label: "Trạng thái",
            render: (item) => <StatusPill value={item.status} />,
          },
          {
            key: "visibility",
            label: "Quyền xem",
            render: (item) =>
              item.visibility === "project"
                ? "Toàn dự án"
                : item.visibility === "shared"
                  ? "Đã chọn thành viên"
                  : "Riêng tư",
          },
          {
            key: "ai_enabled",
            label: "AI đọc",
            render: (item) => (item.ai_enabled ? "Đã cho phép" : "Chưa cho phép"),
          },
          {
            key: "index_status",
            label: "Chỉ mục AI",
            render: (item) =>
              item.index_status === "INDEXED"
                ? "Đã lập chỉ mục"
                : item.index_status === "FAILED"
                  ? "Lập chỉ mục thất bại"
                  : "Chưa lập chỉ mục",
          },
          { key: "revision", label: "Phiên bản" },
          {
            key: "actions",
            label: "Thao tác",
            hideWhenEmpty: true,
            render: (item) => (
              <span className="flex flex-wrap gap-2">
                {can("knowledge.manage") && item.status !== "ARCHIVED" && (
                  <>
                    <button
                      className="secondary-button"
                      type="button"
                      onClick={() => classify(item)}
                    >
                      Phân loại
                    </button>
                    <button
                      className="secondary-button"
                      type="button"
                      onClick={() => reindex(item)}
                    >
                      Lập chỉ mục lại
                    </button>
                  </>
                )}
                {(isPlatformAdmin || item.created_by === currentUserId) &&
                  item.status !== "ARCHIVED" &&
                  !item.ai_enabled && (
                    <button
                      className="secondary-button"
                      type="button"
                      onClick={() => enableAiRead(item)}
                    >
                      Cho AI đọc
                    </button>
                  )}
                {(isPlatformAdmin || item.created_by === currentUserId) &&
                  item.status !== "ARCHIVED" && (
                    <button
                      className="secondary-button"
                      type="button"
                      onClick={() => changeAccess(item)}
                    >
                      Quyền xem
                    </button>
                  )}
                {can("requirement_document.download") && (
                  <button className="secondary-button" type="button" onClick={() => download(item)}>
                    Tải xuống
                  </button>
                )}
                {item.status === "ARCHIVED"
                  ? can("requirement_document.restore") && (
                      <button
                        className="secondary-button"
                        type="button"
                        onClick={() => changeArchiveStatus(item, true)}
                      >
                        Khôi phục
                      </button>
                    )
                  : can("requirement_document.archive") && (
                      <button
                        className="secondary-button"
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
