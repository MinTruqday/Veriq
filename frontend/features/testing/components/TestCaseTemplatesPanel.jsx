"use client";
import { useCallback, useEffect, useMemo, useState } from "react";
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

const templateTypes = [
  ["functional", "Chức năng"],
  ["api", "API"],
  ["rbac", "Phân quyền RBAC"],
  ["state", "Chuyển trạng thái"],
  ["bva", "Giá trị biên BVA"],
];

const typeLabel = (value) =>
  templateTypes.find(([templateType]) => templateType === value)?.[1] || value;

const jsonObject = (value) => {
  let parsed;
  try {
    parsed = JSON.parse(value || "{}");
  } catch {
    throw new Error("Định nghĩa JSON không hợp lệ");
  }
  if (!parsed || Array.isArray(parsed) || typeof parsed !== "object") {
    throw new Error("Định nghĩa mẫu phải là một đối tượng JSON");
  }
  return parsed;
};

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
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");
  const canManage = project.current_permissions?.includes("testcase.template.manage");
  const role = project.current_membership?.project_role;
  const canArchive =
    canManage &&
    (role === "QA" ||
      (role === "TESTER" && project.settings?.tester_can_archive_testcase_templates === true));

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

  const templateFields = useCallback(
    (value = {}) => [
      {
        name: "name",
        label: "Tên mẫu",
        required: true,
        autoFocus: true,
        initialValue: value.name || "",
      },
      {
        name: "templateType",
        label: "Loại mẫu",
        required: true,
        initialValue: value.template_type || "functional",
        options: templateTypes.map(([type, label]) => ({ value: type, label })),
      },
      {
        name: "description",
        label: "Mô tả",
        multiline: true,
        initialValue: value.description || "",
      },
      {
        name: "definition",
        label: "Định nghĩa JSON",
        required: true,
        multiline: true,
        initialValue: JSON.stringify(value.definition || {}, null, 2),
      },
      {
        name: "tags",
        label: "Nhãn phân cách bằng dấu phẩy",
        initialValue: (value.tags || []).join(", "),
      },
    ],
    [],
  );

  const createTemplate = async () => {
    const answer = await ask({
      title: "Tạo mẫu ca kiểm thử",
      confirmLabel: "Tạo mẫu",
      fields: templateFields(),
    });
    if (!answer) return;
    setError("");
    try {
      const created = await testingApi.createTestCaseTemplate(project._id, {
        name: answer.name.trim(),
        template_type: answer.templateType,
        description: answer.description.trim(),
        definition: jsonObject(answer.definition),
        tags: splitTags(answer.tags),
      });
      await load();
      setSelected(created);
    } catch (reason) {
      setError(messageOf(reason));
    }
  };

  const editTemplate = async () => {
    if (!selected) return;
    const answer = await ask({
      title: "Chỉnh sửa mẫu ca kiểm thử",
      description: `Phiên bản chỉnh sửa hiện tại ${selected.revision}`,
      confirmLabel: "Lưu thay đổi",
      fields: templateFields(selected),
    });
    if (!answer) return;
    setError("");
    try {
      const updated = await testingApi.updateTestCaseTemplate(selected._id, {
        expected_revision: selected.revision,
        name: answer.name.trim(),
        template_type: answer.templateType,
        description: answer.description.trim(),
        definition: jsonObject(answer.definition),
        tags: splitTags(answer.tags),
      });
      await load();
      setSelected(updated);
    } catch (reason) {
      setError(messageOf(reason));
    }
  };

  const archiveTemplate = async () => {
    if (!selected) return;
    const answer = await ask({
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
    });
    if (!answer) return;
    setError("");
    try {
      await testingApi.archiveTestCaseTemplate(selected._id, {
        expected_revision: selected.revision,
        reason: answer.reason.trim(),
      });
      setSelected(null);
      await load();
    } catch (reason) {
      setError(messageOf(reason));
    }
  };

  const formattedDefinition = useMemo(
    () => (selected ? JSON.stringify(selected.definition || {}, null, 2) : ""),
    [selected],
  );

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
                  <pre className="max-h-72 overflow-auto whitespace-pre-wrap break-words rounded-control bg-surface-quiet p-4 text-[12px] leading-5">
                    {formattedDefinition}
                  </pre>
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
      {dialog}
    </Panel>
  );
}
