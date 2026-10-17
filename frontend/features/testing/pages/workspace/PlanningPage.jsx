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
import { formatDate, messageOf, valueLabel } from "../../lib/testing";
import {
  Modal,
  ModalContent,
  ModalFooter,
  ModalHeader,
  ModalTitle,
} from "@/shared/components/ui/Modal";

function itemOptions(items) {
  return [
    { value: "", label: "Không có" },
    ...items.map((item) => ({
      value: item._id,
      label: `${valueLabel(item.item_type)} ${item.title}`,
    })),
  ];
}

export default function PlanningPage({ project, section }) {
  const { ask, dialog } = useActionDialog();
  const [items, setItems] = useState([]);
  const [boardValue, setBoardValue] = useState(null);
  const [sprints, setSprints] = useState([]);
  const [roadmap, setRoadmap] = useState(null);
  const [configurationMode, setConfigurationMode] = useState("");
  const [error, setError] = useState("");
  const [loading, setLoading] = useState(true);
  const tab = section?.[0] || "backlog";
  const isBa = project.current_membership?.project_role === "BA";
  const planningMethod = project.planning_method || "SCRUM";
  const isScrum = planningMethod === "SCRUM";
  const load = useCallback(async () => {
    setLoading(true);
    try {
      const [board, roadmapValue, sprintValues] = await Promise.all([
        testingApi.workBoard(project._id),
        testingApi.roadmap(project._id),
        isScrum ? testingApi.listSprints(project._id) : Promise.resolve([]),
      ]);
      setItems(board.items || []);
      setBoardValue(board);
      setRoadmap(roadmapValue);
      setSprints(sprintValues);
      setError("");
    } catch (reason) {
      setError(messageOf(reason));
    } finally {
      setLoading(false);
    }
  }, [isScrum, project._id]);
  useEffect(() => {
    void load();
  }, [load]);
  const createItem = async () => {
    const answer = await ask({
      title: "Tạo công việc",
      confirmLabel: "Tạo công việc",
      fields: [
        {
          name: "item_type",
          label: "Loại",
          options: ["INITIATIVE", "EPIC", "STORY", "TASK", "BUG", "SUBTASK"].map((value) => ({
            value,
            label: valueLabel(value),
          })),
        },
        { name: "title", label: "Tên", required: true },
        { name: "description", label: "Mô tả", multiline: true },
        { name: "parent_id", label: "Thuộc công việc", options: itemOptions(items) },
        {
          name: "priority",
          label: "Ưu tiên",
          options: ["LOW", "MEDIUM", "HIGH", "HIGHEST"].map((value) => ({
            value,
            label: valueLabel(value),
          })),
        },
        { name: "estimate", label: "Ước lượng", type: "number" },
        { name: "due_at", label: "Hạn hoàn thành", type: "date" },
      ],
    });
    if (!answer) return;
    try {
      await testingApi.createWorkItem(project._id, {
        ...answer,
        title: answer.title.trim(),
        description: answer.description.trim(),
        parent_id: answer.parent_id || null,
        estimate: answer.estimate ? Number(answer.estimate) : null,
        due_at: answer.due_at || null,
      });
      await load();
    } catch (reason) {
      setError(messageOf(reason));
    }
  };
  const createSprint = async () => {
    const answer = await ask({
      title: "Tạo đợt lặp",
      confirmLabel: "Tạo đợt lặp",
      fields: [
        { name: "name", label: "Tên đợt lặp", required: true },
        { name: "goal", label: "Mục tiêu", multiline: true },
        { name: "start_at", label: "Bắt đầu", type: "date", required: true },
        { name: "end_at", label: "Kết thúc", type: "date", required: true },
      ],
    });
    if (!answer) return;
    try {
      await testingApi.createSprint(project._id, answer);
      await load();
    } catch (reason) {
      setError(messageOf(reason));
    }
  };
  const migrateLegacyTasks = async () => {
    try {
      const preview = await testingApi.previewProjectTaskMigration(project._id);
      if (preview.already_migrated) {
        setError("Công việc cũ đã được chuyển đổi trước đó");
        return;
      }
      if (!preview.task_count) {
        setError("Không có công việc cũ cần chuyển đổi");
        return;
      }
      const answer = await ask({
        title: "Xem trước chuyển đổi công việc cũ",
        description: `${preview.task_count} công việc sẽ được chuyển đổi`,
        confirmLabel: "Xác nhận chuyển đổi",
        fields: preview.legacy_statuses.map((legacy_status) => ({
          name: legacy_status,
          label: `Trạng thái ${legacy_status}`,
          required: true,
          options: preview.workflow_statuses.map((status) => ({
            value: status.key,
            label: status.name,
          })),
        })),
      });
      if (!answer) return;
      await testingApi.migrateProjectTasks(project._id, {
        mappings: preview.legacy_statuses.map((legacy_status) => ({
          legacy_status,
          target_status: answer[legacy_status],
        })),
      });
      await load();
    } catch (reason) {
      setError(messageOf(reason));
    }
  };
  const transition = async (item, status) => {
    const answer = await ask({
      title: "Chuyển trạng thái",
      confirmLabel: "Xác nhận",
      fields: [{ name: "reason", label: "Lý do", multiline: true }],
    });
    if (!answer) return;
    try {
      await testingApi.transitionWorkItem(project._id, item._id, {
        expected_revision: item.revision,
        status,
        reason: answer.reason.trim(),
      });
      await load();
    } catch (reason) {
      setError(messageOf(reason));
    }
  };
  const rank = async (item, beforeItemId) => {
    try {
      await testingApi.rankWorkItem(project._id, item._id, {
        expected_revision: item.revision,
        before_item_id: beforeItemId || null,
      });
      await load();
    } catch (reason) {
      setError(messageOf(reason));
    }
  };
  const addDependency = async (item) => {
    const answer = await ask({
      title: "Thêm liên kết phụ thuộc",
      description: item.title,
      confirmLabel: "Lưu liên kết",
      fields: [
        {
          name: "target_item_id",
          label: "Công việc liên quan",
          required: true,
          options: items
            .filter((value) => value._id !== item._id)
            .map((value) => ({
              value: value._id,
              label: `${valueLabel(value.item_type)} · ${value.title}`,
            })),
        },
        {
          name: "dependency_type",
          label: "Loại liên kết",
          options: [
            { value: "BLOCKS", label: "Chặn công việc này" },
            { value: "RELATES_TO", label: "Liên quan" },
          ],
        },
      ],
    });
    if (!answer) return;
    try {
      await testingApi.createWorkItemDependency(project._id, item._id, answer);
      await load();
    } catch (reason) {
      setError(messageOf(reason));
    }
  };
  const manageSprint = async (sprint, action) => {
    if (action === "scope") {
      const answer = await ask({
        title: "Phạm vi Sprint",
        description: sprint.name,
        confirmLabel: "Lưu phạm vi",
        fields: [
          {
            name: "work_item_ids",
            label: "Công việc",
            multiple: true,
            options: items
              .filter((item) => !item.sprint_id || item.sprint_id === sprint._id)
              .map((item) => ({
                value: item._id,
                label: `${valueLabel(item.item_type)} · ${item.title}`,
              })),
            initialValue: sprint.work_item_ids || [],
          },
        ],
      });
      if (!answer) return;
      try {
        await testingApi.patchSprintScope(project._id, sprint._id, {
          expected_revision: sprint.revision,
          work_item_ids: answer.work_item_ids || [],
        });
        await load();
      } catch (reason) {
        setError(messageOf(reason));
      }
      return;
    }
    const answer = await ask({
      title: action === "START" ? "Bắt đầu đợt lặp" : "Kết thúc đợt lặp",
      description: sprint.name,
      confirmLabel: action === "START" ? "Bắt đầu" : "Kết thúc",
      fields: [
        ...(action === "COMPLETE"
          ? [
              {
                name: "unfinished_action",
                label: "Công việc chưa hoàn thành",
                required: true,
                options: [
                  { value: "BACKLOG", label: "Đưa về danh sách chờ" },
                  { value: "NEXT_SPRINT", label: "Chuyển sang đợt lặp kế tiếp" },
                  { value: "CANCEL", label: "Đóng theo trạng thái đã chọn" },
                ],
              },
              {
                name: "target_sprint_id",
                label: "Đợt lặp nhận công việc",
                options: sprints
                  .filter((value) => value._id !== sprint._id && value.status === "PLANNED")
                  .map((value) => ({ value: value._id, label: value.name })),
              },
              {
                name: "target_status",
                label: "Trạng thái khi đóng",
                options: (boardValue?.workflow?.statuses || []).map((value) => ({
                  value: value.key,
                  label: value.name,
                })),
              },
            ]
          : []),
        { name: "reason", label: "Ghi chú", multiline: true },
      ],
    });
    if (!answer) return;
    try {
      await testingApi.transitionSprint(project._id, sprint._id, {
        expected_revision: sprint.revision,
        action,
        reason: answer.reason.trim(),
        unfinished_action: answer.unfinished_action || null,
        target_sprint_id: answer.target_sprint_id || null,
        target_status: answer.target_status || null,
      });
      await load();
    } catch (reason) {
      setError(messageOf(reason));
    }
  };
  if (loading)
    return (
      <WorkspacePage title="Lập kế hoạch">
        <LoadingState />
      </WorkspacePage>
    );
  return (
    <WorkspacePage
      title="Lập kế hoạch"
      description={
        isScrum
          ? "Danh sách chờ và đợt lặp được quản lý theo Scrum"
          : "Danh sách chờ và dòng công việc được quản lý theo Kanban"
      }
      actions={
        isBa ? (
          <div className="flex flex-wrap gap-2">
            <button className="secondary-button" type="button" onClick={createItem}>
              <Plus size={16} />
              Tạo công việc
            </button>
            <button
              className="secondary-button"
              type="button"
              onClick={() => setConfigurationMode("board")}
            >
              Cấu hình bảng
            </button>
            <button
              className="secondary-button"
              type="button"
              onClick={() => setConfigurationMode("workflow")}
            >
              Quy trình
            </button>
            <button className="secondary-button" type="button" onClick={migrateLegacyTasks}>
              Chuyển công việc cũ
            </button>
            {planningMethod === "KANBAN" && (
              <button
                className="secondary-button"
                type="button"
                onClick={() => setConfigurationMode("board")}
              >
                Giới hạn đang thực hiện
              </button>
            )}
            {isScrum && (
              <button className="apple-button" type="button" onClick={createSprint}>
                <Plus size={16} />
                Tạo đợt lặp
              </button>
            )}
          </div>
        ) : null
      }
    >
      {error && <ErrorState message={error} />}
      <div className="flex flex-wrap gap-2 border-b border-border pb-4 text-sm">
        {["backlog", "board", ...(isScrum ? ["sprint"] : []), "roadmap"].map((value) => (
          <a
            key={value}
            className={tab === value ? "apple-button" : "secondary-button"}
            href={`/du-an/${project._id}/lap-ke-hoach/${value}`}
          >
            {value === "backlog"
              ? "Danh sách chờ"
              : value === "board"
                ? "Bảng công việc"
                : value === "sprint"
                  ? "Đợt lặp"
                  : "Lộ trình"}
          </a>
        ))}
      </div>
      {tab === "backlog" && (
        <Panel title="Danh sách chờ" description="Công việc được sắp xếp theo ưu tiên">
          <Backlog
            items={items.filter((item) => item.status === "BACKLOG")}
            canRank={isBa}
            onRank={rank}
            onAddDependency={addDependency}
          />
        </Panel>
      )}
      {tab === "board" && (
        <Board
          items={items}
          board={boardValue?.board}
          workflow={boardValue?.workflow}
          onTransition={transition}
          role={project.current_membership?.project_role}
          canTransition={isBa || project.current_membership?.project_role === "DEVELOPER"}
        />
      )}
      {tab === "sprint" && isScrum && (
        <Panel title="Đợt lặp">
          <DataTable
            items={sprints}
            empty="Chưa có đợt lặp"
            columns={[
              { key: "name", label: "Đợt lặp" },
              { key: "goal", label: "Mục tiêu" },
              {
                key: "status",
                label: "Trạng thái",
                render: (item) => <StatusPill value={item.status} />,
              },
              { key: "start_at", label: "Bắt đầu", render: (item) => formatDate(item.start_at) },
              { key: "end_at", label: "Kết thúc", render: (item) => formatDate(item.end_at) },
              ...(isBa
                ? [
                    {
                      key: "actions",
                      label: "Thao tác",
                      render: (item) => (
                        <span className="flex flex-wrap gap-2">
                          {item.status === "PLANNED" && (
                            <button
                              className="secondary-button"
                              type="button"
                              onClick={() => manageSprint(item, "scope")}
                            >
                              Phạm vi
                            </button>
                          )}
                          {item.status === "PLANNED" && (
                            <button
                              className="apple-button"
                              type="button"
                              onClick={() => manageSprint(item, "START")}
                            >
                              Bắt đầu
                            </button>
                          )}
                          {item.status === "ACTIVE" && (
                            <button
                              className="apple-button"
                              type="button"
                              onClick={() => manageSprint(item, "COMPLETE")}
                            >
                              Kết thúc
                            </button>
                          )}
                        </span>
                      ),
                    },
                  ]
                : []),
            ]}
          />
        </Panel>
      )}
      {tab === "roadmap" && <Roadmap value={roadmap} />}
      <PlanningConfigurationModal
        mode={configurationMode}
        board={boardValue?.board}
        workflow={boardValue?.workflow}
        onClose={() => setConfigurationMode("")}
        onSaveBoard={async (columns) => {
          await testingApi.updateWorkBoard(project._id, {
            expected_revision: boardValue.board.revision,
            columns,
          });
          await load();
        }}
        onSaveWorkflow={async ({ statuses, transitions }) => {
          await testingApi.updatePlanningWorkflow(project._id, {
            expected_revision: boardValue.workflow.revision,
            statuses,
            transitions,
          });
          await load();
        }}
        onError={(reason) => setError(messageOf(reason))}
      />
      {dialog}
    </WorkspacePage>
  );
}

function PlanningConfigurationModal({
  mode,
  board,
  workflow,
  onClose,
  onSaveBoard,
  onSaveWorkflow,
  onError,
}) {
  const [columns, setColumns] = useState([]);
  const [statuses, setStatuses] = useState([]);
  const [transitions, setTransitions] = useState([]);
  const [saving, setSaving] = useState(false);
  useEffect(() => {
    if (!mode) return;
    setColumns(
      (board?.columns || []).map((item) => ({ ...item, wip_limit: item.wip_limit ?? "" })),
    );
    setStatuses((workflow?.statuses || []).map((item) => ({ ...item })));
    setTransitions(
      (workflow?.transitions || []).map((item) => ({
        ...item,
        allowed_roles: item.allowed_roles || [],
      })),
    );
  }, [board, mode, workflow]);
  const save = async (event) => {
    event.preventDefault();
    try {
      setSaving(true);
      if (mode === "board") {
        const next = columns.map((item, position) => ({
          status: item.status.trim(),
          name: item.name.trim(),
          position,
          wip_limit: item.wip_limit === "" ? null : Number(item.wip_limit),
        }));
        if (
          next.some(
            (item) =>
              !item.status ||
              !item.name ||
              (item.wip_limit !== null &&
                (!Number.isInteger(item.wip_limit) || item.wip_limit < 1)),
          )
        ) {
          onError("Mỗi cột cần trạng thái, tên và giới hạn WIP hợp lệ nếu có");
          return;
        }
        await onSaveBoard(next);
      } else {
        const nextStatuses = statuses.map((item) => ({
          key: item.key.trim(),
          name: item.name.trim(),
          counts_as_completed: Boolean(item.counts_as_completed),
        }));
        const nextTransitions = transitions.map((item) => ({
          from_status: item.from_status,
          to_status: item.to_status,
          allowed_roles: item.allowed_roles,
        }));
        if (
          nextStatuses.some((item) => !item.key || !item.name) ||
          nextTransitions.some(
            (item) => !item.from_status || !item.to_status || !item.allowed_roles.length,
          )
        ) {
          onError("Mỗi trạng thái và chuyển trạng thái cần đủ thông tin");
          return;
        }
        await onSaveWorkflow({ statuses: nextStatuses, transitions: nextTransitions });
      }
      onClose();
    } catch (reason) {
      onError(reason);
    } finally {
      setSaving(false);
    }
  };
  const availableStatusOptions = statuses.filter((item) => item.key.trim());
  return (
    <Modal
      isOpen={Boolean(mode)}
      onClose={onClose}
      ariaLabel={mode === "board" ? "Cấu hình bảng công việc" : "Cấu hình quy trình"}
      className="max-h-[94dvh] max-w-4xl overflow-y-auto"
    >
      <ModalHeader>
        <ModalTitle>
          {mode === "board" ? "Cấu hình bảng công việc" : "Cấu hình quy trình"}
        </ModalTitle>
      </ModalHeader>
      <form onSubmit={save}>
        <ModalContent>
          {mode === "board" ? (
            <div className="space-y-3">
              <p className="text-sm text-ink-muted">
                Mỗi cột phản ánh một trạng thái công việc. Giới hạn WIP chỉ áp dụng khi dự án dùng
                Kanban.
              </p>
              {columns.map((column, index) => (
                <div
                  className="grid gap-3 rounded-control border border-border p-3 md:grid-cols-[1fr_1fr_140px_auto]"
                  key={`${column.status}-${index}`}
                >
                  <input
                    className="apple-input"
                    aria-label={`Trạng thái cột ${index + 1}`}
                    value={column.status}
                    onChange={(event) =>
                      setColumns((items) =>
                        items.map((item, itemIndex) =>
                          itemIndex === index ? { ...item, status: event.target.value } : item,
                        ),
                      )
                    }
                    placeholder="Mã trạng thái"
                    required
                  />
                  <input
                    className="apple-input"
                    aria-label={`Tên cột ${index + 1}`}
                    value={column.name}
                    onChange={(event) =>
                      setColumns((items) =>
                        items.map((item, itemIndex) =>
                          itemIndex === index ? { ...item, name: event.target.value } : item,
                        ),
                      )
                    }
                    placeholder="Tên cột"
                    required
                  />
                  <input
                    className="apple-input"
                    aria-label={`Giới hạn WIP cột ${index + 1}`}
                    type="number"
                    min="1"
                    value={column.wip_limit}
                    onChange={(event) =>
                      setColumns((items) =>
                        items.map((item, itemIndex) =>
                          itemIndex === index ? { ...item, wip_limit: event.target.value } : item,
                        ),
                      )
                    }
                    placeholder="WIP"
                  />
                  <button
                    className="secondary-button"
                    type="button"
                    onClick={() =>
                      setColumns((items) => items.filter((_, itemIndex) => itemIndex !== index))
                    }
                  >
                    Xóa
                  </button>
                </div>
              ))}
              <button
                className="secondary-button"
                type="button"
                onClick={() =>
                  setColumns((items) => [...items, { status: "", name: "", wip_limit: "" }])
                }
              >
                Thêm cột
              </button>
            </div>
          ) : (
            <div className="space-y-6">
              <div className="space-y-3">
                <div>
                  <h4 className="font-semibold">Trạng thái</h4>
                  <p className="mt-1 text-sm text-ink-muted">
                    Đánh dấu hoàn thành chỉ dành cho trạng thái kết thúc công việc.
                  </p>
                </div>
                {statuses.map((status, index) => (
                  <div
                    className="grid gap-3 rounded-control border border-border p-3 md:grid-cols-[1fr_1fr_auto_auto]"
                    key={`${status.key}-${index}`}
                  >
                    <input
                      className="apple-input"
                      aria-label={`Mã trạng thái ${index + 1}`}
                      value={status.key}
                      onChange={(event) =>
                        setStatuses((items) =>
                          items.map((item, itemIndex) =>
                            itemIndex === index ? { ...item, key: event.target.value } : item,
                          ),
                        )
                      }
                      placeholder="Mã"
                      required
                    />
                    <input
                      className="apple-input"
                      aria-label={`Tên trạng thái ${index + 1}`}
                      value={status.name}
                      onChange={(event) =>
                        setStatuses((items) =>
                          items.map((item, itemIndex) =>
                            itemIndex === index ? { ...item, name: event.target.value } : item,
                          ),
                        )
                      }
                      placeholder="Tên hiển thị"
                      required
                    />
                    <label className="flex items-center gap-2 text-sm">
                      <input
                        type="checkbox"
                        checked={status.counts_as_completed}
                        onChange={(event) =>
                          setStatuses((items) =>
                            items.map((item, itemIndex) =>
                              itemIndex === index
                                ? { ...item, counts_as_completed: event.target.checked }
                                : item,
                            ),
                          )
                        }
                      />{" "}
                      Hoàn thành
                    </label>
                    <button
                      className="secondary-button"
                      type="button"
                      onClick={() =>
                        setStatuses((items) => items.filter((_, itemIndex) => itemIndex !== index))
                      }
                    >
                      Xóa
                    </button>
                  </div>
                ))}
                <button
                  className="secondary-button"
                  type="button"
                  onClick={() =>
                    setStatuses((items) => [
                      ...items,
                      { key: "", name: "", counts_as_completed: false },
                    ])
                  }
                >
                  Thêm trạng thái
                </button>
              </div>
              <div className="space-y-3">
                <div>
                  <h4 className="font-semibold">Chuyển trạng thái</h4>
                  <p className="mt-1 text-sm text-ink-muted">
                    Chỉ các vai trò được chọn mới được chuyển công việc theo tuyến này.
                  </p>
                </div>
                {transitions.map((transition, index) => (
                  <div
                    className="grid gap-3 rounded-control border border-border p-3 md:grid-cols-[1fr_1fr_1fr_auto]"
                    key={`${transition.from_status}-${transition.to_status}-${index}`}
                  >
                    <select
                      className="apple-input"
                      aria-label={`Từ trạng thái ${index + 1}`}
                      value={transition.from_status}
                      onChange={(event) =>
                        setTransitions((items) =>
                          items.map((item, itemIndex) =>
                            itemIndex === index
                              ? { ...item, from_status: event.target.value }
                              : item,
                          ),
                        )
                      }
                    >
                      {availableStatusOptions.map((status) => (
                        <option key={status.key} value={status.key}>
                          {status.name}
                        </option>
                      ))}
                    </select>
                    <select
                      className="apple-input"
                      aria-label={`Đến trạng thái ${index + 1}`}
                      value={transition.to_status}
                      onChange={(event) =>
                        setTransitions((items) =>
                          items.map((item, itemIndex) =>
                            itemIndex === index ? { ...item, to_status: event.target.value } : item,
                          ),
                        )
                      }
                    >
                      {availableStatusOptions.map((status) => (
                        <option key={status.key} value={status.key}>
                          {status.name}
                        </option>
                      ))}
                    </select>
                    <select
                      className="apple-input"
                      aria-label={`Vai trò chuyển trạng thái ${index + 1}`}
                      multiple
                      value={transition.allowed_roles}
                      onChange={(event) =>
                        setTransitions((items) =>
                          items.map((item, itemIndex) =>
                            itemIndex === index
                              ? {
                                  ...item,
                                  allowed_roles: Array.from(
                                    event.target.selectedOptions,
                                    (option) => option.value,
                                  ),
                                }
                              : item,
                          ),
                        )
                      }
                    >
                      {["BA", "QA", "TESTER", "DEVELOPER"].map((role) => (
                        <option key={role} value={role}>
                          {role}
                        </option>
                      ))}
                    </select>
                    <button
                      className="secondary-button"
                      type="button"
                      onClick={() =>
                        setTransitions((items) =>
                          items.filter((_, itemIndex) => itemIndex !== index),
                        )
                      }
                    >
                      Xóa
                    </button>
                  </div>
                ))}
                <button
                  className="secondary-button"
                  type="button"
                  onClick={() =>
                    setTransitions((items) => [
                      ...items,
                      {
                        from_status: availableStatusOptions[0]?.key || "",
                        to_status: availableStatusOptions[0]?.key || "",
                        allowed_roles: [],
                      },
                    ])
                  }
                >
                  Thêm chuyển trạng thái
                </button>
              </div>
            </div>
          )}
        </ModalContent>
        <ModalFooter>
          <button className="secondary-button" type="button" onClick={onClose}>
            Hủy
          </button>
          <button className="apple-button" type="submit" disabled={saving}>
            {saving ? "Đang lưu" : "Lưu thay đổi"}
          </button>
        </ModalFooter>
      </form>
    </Modal>
  );
}

function Backlog({ items, canRank, onRank, onAddDependency }) {
  const [draggedId, setDraggedId] = useState("");
  if (!items.length)
    return <p className="p-5 text-sm text-ink-muted">Chưa có công việc trong danh sách chờ</p>;
  return (
    <ol className="divide-y divide-border" aria-label="Thứ tự công việc trong danh sách chờ">
      {items.map((item, index) => (
        <li
          key={item._id}
          draggable={canRank}
          onDragStart={() => setDraggedId(item._id)}
          onDragOver={(event) => event.preventDefault()}
          onDrop={() => {
            const dragged = items.find((value) => value._id === draggedId);
            if (dragged && dragged._id !== item._id) void onRank(dragged, item._id);
            setDraggedId("");
          }}
          className={`grid gap-3 p-4 transition ${canRank ? "cursor-grab active:cursor-grabbing" : ""} md:grid-cols-[minmax(0,1fr)_auto] md:items-center`}
        >
          <div className="min-w-0">
            <div className="flex flex-wrap items-center gap-2">
              <span className="flex h-6 min-w-6 items-center justify-center rounded-full bg-surface-quiet px-2 text-[11px] font-semibold text-ink-muted">
                {index + 1}
              </span>
              <StatusPill value={item.item_type} />
              <StatusPill value={item.priority} />
              {item.due_at && (
                <span className="text-xs text-ink-muted">Hạn {formatDate(item.due_at)}</span>
              )}
            </div>
            <strong className="mt-2 block break-words text-sm">{item.title}</strong>
            {item.description && (
              <p className="mt-1 line-clamp-2 text-xs leading-5 text-ink-muted">
                {item.description}
              </p>
            )}
          </div>
          {canRank && (
            <span className="flex flex-wrap items-center justify-end gap-2">
              <button
                className="secondary-button"
                type="button"
                onClick={() => onAddDependency(item)}
              >
                Phụ thuộc
              </button>
              <span className="text-xs font-medium text-ink-muted" aria-hidden="true">
                Kéo để sắp xếp
              </span>
            </span>
          )}
        </li>
      ))}
    </ol>
  );
}

function Board({ items, board, workflow, onTransition, canTransition, role }) {
  const [draggedItem, setDraggedItem] = useState(null);
  const statusName = (status) =>
    (workflow?.statuses || []).find((value) => value.key === status)?.name || valueLabel(status);
  const groups = (board?.columns || [])
    .slice()
    .sort((left, right) => left.position - right.position)
    .map((column) => ({
      ...column,
      items: items.filter((item) => item.status === column.status),
    }));
  if (!groups.length) {
    return (
      <Panel title="Bảng công việc">
        <p className="p-5 text-sm text-ink-muted">Chưa có cột nào trong bảng công việc</p>
      </Panel>
    );
  }
  return (
    <div className="overflow-x-auto pb-2">
      <div className="flex min-w-max items-start gap-4">
        {groups.map((column) => (
          <Panel
            key={column.status}
            className="w-[min(86vw,360px)] shrink-0"
            title={column.name}
            description={
              column.wip_limit
                ? `${column.items.length}/${column.wip_limit} công việc`
                : `${column.items.length} công việc`
            }
          >
            <div
              className="min-h-24 space-y-3 p-4"
              onDragOver={(event) => event.preventDefault()}
              onDrop={() => {
                if (draggedItem && draggedItem.status !== column.status) {
                  void onTransition(draggedItem, column.status);
                }
                setDraggedItem(null);
              }}
            >
              {column.items.map((item) => (
                <article
                  className={`rounded-xl border border-border bg-surface-raised p-3 shadow-[0_4px_14px_rgba(48,47,42,0.035)] ${canTransition ? "cursor-grab active:cursor-grabbing" : ""}`}
                  draggable={canTransition}
                  onDragStart={() => setDraggedItem(item)}
                  key={item._id}
                >
                  <strong className="block text-sm">{item.title}</strong>
                  <p className="mt-1 text-xs text-ink-muted">
                    {valueLabel(item.item_type)} · {valueLabel(item.priority)}
                  </p>
                  {canTransition &&
                    (workflow?.transitions || [])
                      .filter((value) => value.from_status === item.status)
                      .filter((value) => value.allowed_roles?.includes(role))
                      .map((value) => (
                        <button
                          className="secondary-button mt-3 mr-2"
                          type="button"
                          key={`${item._id}:${value.to_status}`}
                          onClick={() => onTransition(item, value.to_status)}
                        >
                          Chuyển {statusName(value.to_status)}
                        </button>
                      ))}
                </article>
              ))}
            </div>
          </Panel>
        ))}
      </div>
    </div>
  );
}

function Roadmap({ value }) {
  const dependencies = value?.dependencies || [];
  const items = [...(value?.items || []), ...(value?.releases || [])].sort((left, right) => {
    const leftDate = left.due_at || left.planned_start_at || left.planned_end_at || "";
    const rightDate = right.due_at || right.planned_start_at || right.planned_end_at || "";
    return String(leftDate).localeCompare(String(rightDate));
  });
  return (
    <Panel
      title="Lộ trình"
      description="Sáng kiến, hạng mục lớn, bản phát hành và phụ thuộc trong phạm vi dự án"
    >
      {!items.length ? (
        <p className="p-4 text-sm text-ink-muted">
          Chưa có sáng kiến, hạng mục lớn hoặc bản phát hành
        </p>
      ) : (
        <ol className="space-y-3 p-4">
          {items.map((item) => {
            const itemId = item._id;
            const related = dependencies.filter(
              (dependency) =>
                dependency.source_item_id === itemId || dependency.target_item_id === itemId,
            );
            const date = item.due_at || item.planned_end_at || item.planned_start_at;
            return (
              <li className="border-l-2 border-accent pl-4" key={itemId}>
                <div className="flex flex-wrap items-center gap-2">
                  <strong>{item.name || item.title}</strong>
                  <StatusPill value={item.status} />
                  <span className="text-xs text-ink-muted">
                    {item.item_type ? valueLabel(item.item_type) : "Bản phát hành"}
                    {date ? ` · ${formatDate(date)}` : " · Chưa đặt lịch"}
                  </span>
                </div>
                {related.length > 0 && (
                  <p className="mt-1 text-xs text-ink-muted">{related.length} liên kết phụ thuộc</p>
                )}
              </li>
            );
          })}
        </ol>
      )}
    </Panel>
  );
}
