"use client";
import { useCallback, useEffect, useState } from "react";
import { Plus } from "lucide-react";
import DataTable from "../../components/DataTable";
import {
  ErrorState,
  LoadingState,
  Panel,
  StatusPill,
  WorkspacePage,
  useActionDialog,
} from "../../components/WorkspacePrimitives";
import { testingApi } from "../../services/testing.service";
import { formatDate, messageOf } from "../../lib/testing";

export default function ProjectTasksPage({ project }) {
  const { ask, dialog } = useActionDialog();
  const [value, setValue] = useState(null);
  const [members, setMembers] = useState([]);
  const [error, setError] = useState("");
  const [saving, setSaving] = useState(false);
  const isQa = project.current_membership?.project_role === "QA";
  const load = useCallback(async () => {
    try {
      setError("");
      const [tasks, projectMembers] = await Promise.all([
        testingApi.listProjectTasks(project._id),
        testingApi.listMembers(project._id),
      ]);
      setValue(tasks);
      setMembers(projectMembers.filter((member) => member.status === "ACTIVE"));
    } catch (reason) {
      setError(messageOf(reason));
    }
  }, [project._id]);
  useEffect(() => {
    void load();
  }, [load]);
  const save = async (task = null) => {
    const answer = await ask({
      title: task ? "Cập nhật công việc" : "Tạo công việc",
      confirmLabel: task ? "Lưu thay đổi" : "Tạo công việc",
      fields: [
        { name: "title", label: "Tên công việc", initialValue: task?.title || "", required: true },
        {
          name: "description",
          label: "Mô tả",
          initialValue: task?.description || "",
          multiline: true,
        },
        {
          name: "weight",
          label: "Trọng số",
          initialValue: String(task?.weight || 1),
          required: true,
          type: "number",
        },
        {
          name: "assignee_id",
          label: "Người phụ trách",
          initialValue: task?.assignee_id || "",
          options: [
            { value: "", label: "Chưa phân công" },
            ...members.map((member) => ({
              value: member.user_id,
              label: member.user_label || member.user_id,
            })),
          ],
        },
        {
          name: "due_at",
          label: "Hạn hoàn thành",
          initialValue: task?.due_at?.slice(0, 10) || "",
          type: "date",
        },
        {
          name: "status",
          label: "Trạng thái",
          initialValue: task?.status || "NOT_STARTED",
          options: [
            { value: "NOT_STARTED", label: "Chưa bắt đầu" },
            { value: "IN_PROGRESS", label: "Đang thực hiện" },
            { value: "BLOCKED", label: "Bị chặn" },
            { value: "COMPLETED", label: "Hoàn thành" },
            { value: "CANCELLED", label: "Đã hủy" },
          ],
        },
      ],
    });
    if (!answer) return;
    setSaving(true);
    try {
      const payload = {
        ...answer,
        title: answer.title.trim(),
        description: answer.description.trim(),
        weight: Number(answer.weight),
        assignee_id: answer.assignee_id.trim() || null,
        due_at: answer.due_at || null,
      };
      if (task)
        await testingApi.updateProjectTask(project._id, task._id, {
          ...payload,
          expected_revision: task.revision,
        });
      else await testingApi.createProjectTask(project._id, payload);
      await load();
    } catch (reason) {
      setError(messageOf(reason));
    } finally {
      setSaving(false);
    }
  };
  const remove = async (task) => {
    const answer = await ask({
      title: "Xóa công việc",
      description: `Xóa ${task.title}`,
      confirmLabel: "Xóa",
    });
    if (!answer) return;
    try {
      await testingApi.deleteProjectTask(project._id, task._id, {
        expected_revision: task.revision,
      });
      await load();
    } catch (reason) {
      setError(messageOf(reason));
    }
  };
  const summary = value?.summary;
  return (
    <WorkspacePage
      title="Công việc dự án"
      actions={
        isQa ? (
          <button className="apple-button" type="button" disabled={saving} onClick={() => save()}>
            <Plus size={16} />
            Tạo công việc
          </button>
        ) : null
      }
    >
      {error && <ErrorState message={error} />}
      {!value ? (
        <LoadingState />
      ) : (
        <>
          <Panel title="Tiến độ công việc">
            <div className="grid grid-cols-2 gap-3 p-5 md:grid-cols-4">
              <div>
                <p className="text-xs text-ink-muted">Tasks</p>
                <p className="mt-1 text-2xl font-semibold">
                  {summary.completion_percent === null
                    ? "Chưa có công việc"
                    : `${summary.completion_percent}%`}
                </p>
              </div>
              <div>
                <p className="text-xs text-ink-muted">Tổng công việc</p>
                <p className="mt-1 text-2xl font-semibold">{summary.total}</p>
              </div>
              <div>
                <p className="text-xs text-ink-muted">Hoàn thành</p>
                <p className="mt-1 text-2xl font-semibold">{summary.completed}</p>
              </div>
              <div>
                <p className="text-xs text-ink-muted">Bị chặn</p>
                <p className="mt-1 text-2xl font-semibold">{summary.blocked}</p>
              </div>
            </div>
          </Panel>
          <Panel title="Danh sách công việc">
            <DataTable
              items={value.items}
              empty="Chưa có công việc"
              columns={[
                {
                  key: "title",
                  label: "Công việc",
                  render: (item) => (
                    <div>
                      <strong>{item.title}</strong>
                      {item.description && (
                        <p className="mt-1 text-xs text-ink-muted">{item.description}</p>
                      )}
                    </div>
                  ),
                },
                { key: "weight", label: "Trọng số" },
                {
                  key: "status",
                  label: "Trạng thái",
                  render: (item) => <StatusPill value={item.status} />,
                },
                {
                  key: "due_at",
                  label: "Hạn hoàn thành",
                  render: (item) => (item.due_at ? formatDate(item.due_at) : "Chưa đặt"),
                },
                {
                  key: "assignee_id",
                  label: "Người phụ trách",
                  render: (item) => item.assignee_id || "Chưa phân công",
                },
                ...(isQa
                  ? [
                      {
                        key: "actions",
                        label: "Thao tác",
                        render: (item) => (
                          <div className="flex gap-2">
                            <button
                              className="secondary-button"
                              type="button"
                              onClick={() => save(item)}
                            >
                              Sửa
                            </button>
                            <button
                              className="secondary-button"
                              type="button"
                              onClick={() => remove(item)}
                            >
                              Xóa
                            </button>
                          </div>
                        ),
                      },
                    ]
                  : []),
              ]}
            />
          </Panel>
        </>
      )}
      {dialog}
    </WorkspacePage>
  );
}
