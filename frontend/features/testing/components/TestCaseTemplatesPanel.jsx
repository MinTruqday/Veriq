"use client";
import { useCallback, useEffect, useState } from "react";
import DataTable from "./DataTable";
import {
  EmptyState,
  ErrorState,
  LoadingState,
  Panel,
  StatusPill,
  useActionDialog,
} from "./WorkspacePrimitives";
import { testingApi } from "../services/testing.service";
import { formatDate, messageOf } from "../lib/testing";
import {
  Modal,
  ModalContent,
  ModalFooter,
  ModalHeader,
  ModalTitle,
} from "@/shared/components/ui/Modal";
import StructuredValueEditor, { StructuredValueView } from "./StructuredValueEditor";

const templateTypes = [
  ["functional", "Chức năng"],
  ["api", "API"],
  ["rbac", "Phân quyền RBAC"],
  ["state", "Chuyển trạng thái"],
  ["bva", "Giá trị biên BVA"],
];

const typeLabel = (value) =>
  templateTypes.find(([templateType]) => templateType === value)?.[1] || value;

const splitTags = (value) =>
  Array.from(
    new Set(
      String(value || "")
        .split(",")
        .map((item) => item.trim())
        .filter(Boolean),
    ),
  );

export default function TestCaseTemplatesPanel({ project }) {
  const { ask, dialog } = useActionDialog();
  const [items, setItems] = useState([]);
  const [selected, setSelected] = useState(null);
  const [templateType, setTemplateType] = useState("");
  const [templateEditor, setTemplateEditor] = useState(null);
  const [templateError, setTemplateError] = useState("");
  const [savingTemplate, setSavingTemplate] = useState(false);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");
  const canManage = project.current_permissions?.includes("testcase.template.manage");
  const membershipRoles = project.current_membership?.project_roles;
  const memberRoles =
    Array.isArray(membershipRoles) && membershipRoles.length
      ? membershipRoles
      : [project.current_membership?.project_role].filter(Boolean);
  const canArchive =
    canManage &&
    (memberRoles.includes("QA") ||
      (memberRoles.includes("TESTER") &&
        project.settings?.tester_can_archive_testcase_templates === true));

  const load = useCallback(async () => {
    setLoading(true);
    setError("");
    try {
      const values = await testingApi.listTestCaseTemplates(project._id, templateType);
      setItems(values);
      setSelected((current) =>
        current && values.some((item) => item._id === current._id) ? current : null,
      );
    } catch (reason) {
      setError(messageOf(reason));
    } finally {
      setLoading(false);
    }
  }, [project._id, templateType]);

  useEffect(() => {
    void load();
  }, [load]);

  const openDetail = async (item) => {
    setError("");
    try {
      setSelected(await testingApi.getTestCaseTemplate(item._id));
    } catch (reason) {
      setError(messageOf(reason));
    }
  };

  const openTemplateEditor = (item = null) => {
    setTemplateError("");
    setTemplateEditor({
      source: item,
      name: item?.name || "",
      templateType: item?.template_type || "functional",
      description: item?.description || "",
      definition: structuredClone(item?.definition || {}),
      tags: (item?.tags || []).join(", "),
    });
  };

  const saveTemplate = async (event) => {
    event.preventDefault();
    if (!templateEditor || savingTemplate) return;
    setSavingTemplate(true);
    setTemplateError("");
    const payload = {
      name: templateEditor.name.trim(),
      template_type: templateEditor.templateType,
      description: templateEditor.description.trim(),
      definition: templateEditor.definition,
      tags: splitTags(templateEditor.tags),
    };
    try {
      const saved = templateEditor.source
        ? await testingApi.updateTestCaseTemplate(templateEditor.source._id, {
            ...payload,
            expected_revision: templateEditor.source.revision,
          })
        : await testingApi.createTestCaseTemplate(project._id, payload);
      await load();
      setSelected(saved);
      setTemplateEditor(null);
    } catch (reason) {
      setTemplateError(messageOf(reason));
    } finally {
      setSavingTemplate(false);
    }
  };

  const createTemplate = () => openTemplateEditor();

  const editTemplate = () => {
    if (selected) openTemplateEditor(selected);
  };

  const archiveTemplate = async () => {
    if (!selected) return;
    await ask({
      title: "Lưu trữ mẫu ca kiểm thử",
      description: "Các ca kiểm thử đã tạo từ mẫu này vẫn được giữ nguyên",
      confirmLabel: "Lưu trữ mẫu",
      danger: true,
      fields: [
        {
          name: "reason",
          label: "Lý do lưu trữ",
          required: true,
          multiline: true,
          autoFocus: true,
        },
      ],
      onConfirm: async (answer) => {
        setError("");
        try {
          await testingApi.archiveTestCaseTemplate(selected._id, {
            expected_revision: selected.revision,
            reason: answer.reason.trim(),
          });
          setSelected(null);
          await load();
        } catch (reason) {
          throw new Error(messageOf(reason));
        }
      },
    });
  };

  return (
    <Panel
      title="Danh sách mẫu ca kiểm thử"
      actions={
        <div className="flex flex-wrap gap-2">
          <select
            aria-label="Lọc loại mẫu ca kiểm thử"
            className="apple-input min-w-48"
            value={templateType}
            onChange={(event) => setTemplateType(event.target.value)}
          >
            <option value="">Tất cả loại mẫu</option>
            {templateTypes.map(([value, label]) => (
              <option key={value} value={value}>
                {label}
              </option>
            ))}
          </select>
          {canManage && (
            <button className="apple-button" type="button" onClick={createTemplate}>
              Tạo mẫu
            </button>
          )}
        </div>
      }
    >
      <div className="space-y-4 p-5">
        {error && <ErrorState message={error} />}
        {loading && !items.length ? (
          <LoadingState />
        ) : (
          <div className="grid gap-5 xl:grid-cols-[minmax(0,1.25fr)_minmax(320px,0.75fr)]">
            <div className="overflow-hidden rounded-xl border border-border">
              <DataTable
                items={items}
                empty="Chưa có mẫu ca kiểm thử đang hoạt động"
                onSelect={openDetail}
                columns={[
                  { key: "name", label: "Tên mẫu" },
                  {
                    key: "template_type",
                    label: "Loại",
                    render: (item) => typeLabel(item.template_type),
                  },
                  {
                    key: "status",
                    label: "Trạng thái",
                    render: (item) => <StatusPill value={item.status} />,
                  },
                  { key: "revision", label: "Phiên bản" },
                ]}
              />
            </div>
            {selected ? (
              <section className="space-y-4 rounded-xl border border-border bg-surface-raised p-5">
                <div className="flex flex-wrap items-start justify-between gap-3">
                  <div>
                    <p className="text-[11px] font-semibold uppercase tracking-wide text-ink-faint">
                      {typeLabel(selected.template_type)}
                    </p>
                    <h3 className="mt-1 font-semibold">{selected.name}</h3>
                  </div>
                  <StatusPill value={selected.status} />
                </div>
                {selected.description && (
                  <p className="text-[13px] leading-6 text-ink-muted">{selected.description}</p>
                )}
                <div>
                  <p className="field-label mb-2">Định nghĩa</p>
                  <StructuredValueView value={selected.definition || {}} />
                </div>
                <div>
                  <p className="field-label mb-2">Nhãn</p>
                  {(selected.tags || []).length ? (
                    <div className="flex flex-wrap gap-2">
                      {selected.tags.map((tag) => (
                        <span
                          className="rounded-full bg-brand-soft px-2.5 py-1 text-[11px] font-semibold text-brand"
                          key={tag}
                        >
                          {tag}
                        </span>
                      ))}
                    </div>
                  ) : (
                    <p className="text-[12px] text-ink-muted">Không có nhãn</p>
                  )}
                </div>
                <dl className="grid gap-3 text-[12px] sm:grid-cols-2">
                  <div>
                    <dt className="text-ink-faint">Người tạo</dt>
                    <dd className="mt-1 break-all">
                      {selected.created_by_label || selected.created_by}
                    </dd>
                  </div>
                  <div>
                    <dt className="text-ink-faint">Cập nhật</dt>
                    <dd className="mt-1">{formatDate(selected.updated_at)}</dd>
                  </div>
                </dl>
                {canManage && (
                  <div className="flex flex-wrap gap-2 border-t border-border pt-4">
                    <button className="secondary-button" type="button" onClick={editTemplate}>
                      Chỉnh sửa
                    </button>
                    {canArchive && (
                      <button className="danger-button" type="button" onClick={archiveTemplate}>
                        Lưu trữ
                      </button>
                    )}
                  </div>
                )}
              </section>
            ) : (
              <div className="rounded-xl border border-border bg-surface-raised">
                <EmptyState>Chọn một mẫu để xem định nghĩa chi tiết</EmptyState>
              </div>
            )}
          </div>
        )}
      </div>
      {templateEditor && (
        <Modal
          isOpen
          ariaLabel={templateEditor.source ? "Chỉnh sửa mẫu ca kiểm thử" : "Tạo mẫu ca kiểm thử"}
          className="max-h-[94dvh] max-w-4xl overflow-y-auto"
          onClose={() => {
            if (!savingTemplate) setTemplateEditor(null);
          }}
        >
          <form onSubmit={saveTemplate}>
            <ModalHeader>
              <ModalTitle>
                {templateEditor.source ? "Chỉnh sửa mẫu ca kiểm thử" : "Tạo mẫu ca kiểm thử"}
              </ModalTitle>
            </ModalHeader>
            <ModalContent className="space-y-4">
              {templateError && <ErrorState message={templateError} />}
              <label className="field-label block">
                Tên mẫu
                <input
                  autoFocus
                  className="apple-input mt-2 w-full"
                  required
                  value={templateEditor.name}
                  onChange={(event) =>
                    setTemplateEditor((current) => ({ ...current, name: event.target.value }))
                  }
                />
              </label>
              <label className="field-label block">
                Loại mẫu
                <select
                  className="apple-input mt-2 w-full"
                  value={templateEditor.templateType}
                  onChange={(event) =>
                    setTemplateEditor((current) => ({
                      ...current,
                      templateType: event.target.value,
                    }))
                  }
                >
                  {templateTypes.map(([value, label]) => (
                    <option key={value} value={value}>
                      {label}
                    </option>
                  ))}
                </select>
              </label>
              <label className="field-label block">
                Mô tả
                <textarea
                  className="apple-input mt-2 min-h-20 w-full"
                  value={templateEditor.description}
                  onChange={(event) =>
                    setTemplateEditor((current) => ({
                      ...current,
                      description: event.target.value,
                    }))
                  }
                />
              </label>
              <StructuredValueEditor
                label="Nội dung mẫu"
                value={templateEditor.definition}
                fixedType="object"
                onChange={(definition) =>
                  setTemplateEditor((current) => ({ ...current, definition }))
                }
              />
              <label className="field-label block">
                Nhãn, phân cách bằng dấu phẩy
                <input
                  className="apple-input mt-2 w-full"
                  value={templateEditor.tags}
                  onChange={(event) =>
                    setTemplateEditor((current) => ({ ...current, tags: event.target.value }))
                  }
                />
              </label>
            </ModalContent>
            <ModalFooter>
              <button
                className="secondary-button"
                type="button"
                disabled={savingTemplate}
                onClick={() => setTemplateEditor(null)}
              >
                Hủy
              </button>
              <button className="apple-button" type="submit" disabled={savingTemplate}>
                {savingTemplate ? "Đang lưu" : "Lưu mẫu"}
              </button>
            </ModalFooter>
          </form>
        </Modal>
      )}
      {dialog}
    </Panel>
  );
}
