"use client";
import { useCallback, useEffect, useRef, useState } from "react";
import { useRouter } from "next/navigation";
import {
  ArrowDown,
  ArrowLeft,
  ArrowRight,
  ArrowUp,
  ArchiveRestore,
  ChevronLeft,
  ChevronRight,
  Columns3,
  GitBranch,
  GripVertical,
  History,
  Pencil,
  Plus,
  RefreshCw,
  Workflow,
} from "lucide-react";
import DataTable from "../../components/DataTable";
import {
  ErrorState,
  LoadingState,
  Panel,
  WorkspacePage,
  useActionDialog,
} from "../../components/WorkspacePrimitives";
import { testingApi } from "../../services/testing.service";
import { formatCalendarDate, messageOf, valueLabel } from "../../lib/testing";
import {
  invalidTimelineRange,
  projectPlannedDurationDays,
} from "../../lib/projectSchedule.logic.mjs";
import {
  Modal,
  ModalContent,
  ModalFooter,
  ModalHeader,
  ModalTitle,
} from "@/shared/components/ui/Modal";
import MultiSelect from "@/shared/components/ui/MultiSelect";
import { PROJECT_SECTION_SLUGS, projectRoute } from "../../routes";

function itemOptions(items) {
  return [
    { value: "", label: "Không có" },
    ...items.map((item) => ({
      value: item._id,
      label: `${valueLabel(item.item_type)} ${item.title}`,
    })),
  ];
}

function ensureEndAfterStart(start, end) {
  if (start && end && end <= start) {
    throw new Error("Ngày kết thúc phải sau ngày bắt đầu.");
  }
}

function planningErrorMessage(reason) {
  const messages = {
    KANBAN_WIP_LIMIT_REACHED: "Cột đích đã đạt giới hạn WIP. Công việc vẫn ở trạng thái cũ.",
    KANBAN_WIP_CONCURRENT_UPDATE:
      "Bảng Kanban vừa thay đổi. Công việc chưa được chuyển; hãy tải lại bảng.",
    KANBAN_WIP_CONFIGURATION_INVALID:
      "Cấu hình giới hạn WIP không hợp lệ. Công việc chưa được chuyển.",
    KANBAN_STATUS_COLUMN_MISSING:
      "Trạng thái đích chưa có cột Kanban. Công việc vẫn ở trạng thái cũ.",
    KANBAN_BOARD_UNAVAILABLE: "Bảng Kanban chưa sẵn sàng. Công việc vẫn ở trạng thái cũ.",
    SCRUM_SPRINT_SCOPE_REQUIRED:
      "Trong dự án Scrum, cần đưa công việc vào đợt lặp trước khi bắt đầu.",
    WORK_ITEM_WORKFLOW_TRANSITION_INVALID:
      "Quy trình không cho phép chuyển công việc theo cách này.",
    WORK_ITEM_WORKFLOW_CHANGED:
      "Quy trình vừa thay đổi. Công việc chưa được chuyển; hãy tải lại bảng rồi thử lại.",
    WORK_ITEM_TRANSITION_CONFLICT:
      "Không thể ghi nhận lần chuyển trạng thái này do xung đột dữ liệu. Công việc chưa được cập nhật.",
    WORK_ITEM_PLANNING_CONCURRENT_UPDATE:
      "Lập kế hoạch vừa được thay đổi ở nơi khác. Công việc chưa được cập nhật; hãy tải lại rồi thử lại.",
    WORK_ITEM_TRANSITION_DENIED: "Bạn không có quyền chuyển công việc này.",
    REVISION_CONFLICT: "Công việc vừa được cập nhật ở nơi khác. Hãy tải lại rồi thử lại.",
    WORK_ITEM_NOT_FOUND: "Công việc không còn tồn tại trong dự án. Hãy tải lại danh sách.",
    WORK_ITEM_EMPTY: "Cần nhập ít nhất một thông tin thay đổi cho công việc.",
    WORK_ITEM_ASSIGNEE_INVALID: "Người phụ trách phải là thành viên đang hoạt động của dự án.",
    WORK_ITEM_REQUIREMENT_INVALID: "Một yêu cầu liên kết không còn thuộc dự án này.",
    WORK_ITEM_PARENT_INVALID: "Hạng mục cha không còn hợp lệ trong dự án.",
    WORK_ITEM_HIERARCHY_INVALID: "Loại công việc này không thể nằm dưới hạng mục cha đã chọn.",
    SUBTASK_PARENT_REQUIRED: "Công việc con cần có một Story hoặc Task cha.",
    WORK_ITEM_SCHEDULE_INVALID: "Ngày kết thúc dự kiến phải sau ngày bắt đầu.",
    WORK_ITEM_SCHEDULE_TIMEZONE_MISMATCH:
      "Không thể so sánh ngày do khác múi giờ. Hãy chọn lại ngày theo cùng múi giờ.",
    WORK_ITEM_RANK_CONCURRENT_UPDATE: "Thứ tự danh sách vừa thay đổi. Hãy tải lại rồi thử lại.",
    WORK_ITEM_RANK_TARGET_INVALID: "Vị trí đích không còn hợp lệ. Thứ tự danh sách chưa thay đổi.",
    WORK_ITEM_DEPENDENCY_INVALID: "Hai công việc được chọn không thể tạo liên kết phụ thuộc.",
    WORK_ITEM_DEPENDENCY_EXISTS: "Liên kết phụ thuộc này đã tồn tại.",
    WORK_ITEM_DEPENDENCY_CYCLE: "Liên kết này tạo vòng phụ thuộc nên chưa được lưu.",
    WORK_ITEM_DEPENDENCY_CONCURRENT_UPDATE:
      "Một công việc trong liên kết vừa thay đổi. Hãy tải lại rồi thử lại.",
    WORK_ITEM_PLANNING_BOARD_UNAVAILABLE:
      "Bảng lập kế hoạch chưa sẵn sàng. Thứ tự danh sách chưa được thay đổi.",
    PROJECT_NOT_FOUND: "Không tìm thấy dự án. Hãy quay lại danh sách dự án.",
    ENTITY_NOT_FOUND: "Dữ liệu không còn tồn tại. Hãy tải lại trang.",
    BOARD_COLUMN_STATUS_DUPLICATE: "Mỗi trạng thái chỉ được xuất hiện một lần trên bảng.",
    BOARD_COLUMN_STATUS_INVALID: "Cột bảng phải dùng trạng thái đã có trong quy trình.",
    BOARD_COLUMN_POSITION_DUPLICATE: "Thứ tự các cột bị trùng. Hãy sắp xếp lại trước khi lưu.",
    BOARD_WIP_LIMIT_REQUIRES_KANBAN: "Giới hạn WIP chỉ áp dụng cho dự án Kanban.",
    WORKFLOW_STATUS_DUPLICATE: "Mã trạng thái không được trùng nhau.",
    WORKFLOW_STATUS_IN_USE:
      "Không thể xóa trạng thái đang được công việc sử dụng. Hãy chuyển các công việc đó trước.",
    WORKFLOW_TRANSITION_STATUS_INVALID: "Chuyển trạng thái phải tham chiếu trạng thái đã cấu hình.",
    WORKFLOW_TRANSITION_DUPLICATE: "Một tuyến chuyển trạng thái đang bị khai báo trùng.",
    SPRINT_REQUIRED: "Chức năng đợt lặp chỉ dùng trong dự án Scrum.",
    SCRUM_REQUIRED: "Thao tác này chỉ dùng trong dự án Scrum.",
    SPRINT_NOT_FOUND: "Đợt lặp không còn tồn tại. Hãy tải lại danh sách.",
    SPRINT_DATES_INVALID: "Ngày kết thúc đợt lặp phải sau ngày bắt đầu.",
    SPRINT_TRANSITION_INVALID: "Đợt lặp vừa đổi trạng thái. Hãy tải lại trước khi thao tác.",
    SPRINT_SCOPE_LOCKED: "Không thể đổi phạm vi sau khi đợt lặp đã bắt đầu.",
    SPRINT_ITEM_ALREADY_ASSIGNED: "Một công việc đã thuộc đợt lặp khác.",
    SPRINT_WORK_ITEM_INVALID: "Một công việc trong phạm vi không còn hợp lệ.",
    SPRINT_TARGET_INVALID: "Đợt lặp nhận công việc phải là đợt lặp đã lên kế hoạch.",
    SPRINT_UNFINISHED_ACTION_REQUIRED:
      "Hãy chọn cách xử lý công việc chưa hoàn thành trước khi kết thúc đợt lặp.",
    SPRINT_UNFINISHED_ACTION_INVALID: "Cách xử lý công việc chưa hoàn thành không hợp lệ.",
    SPRINT_CANCEL_STATUS_INVALID: "Trạng thái đóng phải là trạng thái hợp lệ trong quy trình.",
    PROJECT_TASK_MIGRATION_CONCURRENT_UPDATE:
      "Công việc cũ vừa thay đổi. Hãy tải lại trước khi chuyển đổi.",
    PROJECT_TASK_MIGRATION_MAPPING_INVALID:
      "Không thể chuyển một số công việc cũ vì thiếu ánh xạ hợp lệ.",
    PROJECT_TASK_MIGRATION_SOURCE_CHANGED:
      "Nguồn công việc cũ đã thay đổi; chưa có dữ liệu nào được chuyển.",
    BA_PLANNING_REQUIRED: "Chỉ BA của dự án được thay đổi cấu hình lập kế hoạch.",
  };
  return messages[reason?.code] || messageOf(reason);
}

function matchesPlanningFilters(item, filters = { query: "", status: "", type: "" }) {
  const normalizedQuery = filters.query.trim().toLocaleLowerCase();
  const matchesQuery =
    !normalizedQuery ||
    [item._id, item.title, item.name, item.description, item.assignee_id, ...(item.tags || [])]
      .filter(Boolean)
      .some((value) => String(value).toLocaleLowerCase().includes(normalizedQuery));
  return (
    matchesQuery &&
    (!filters.status || item.status === filters.status) &&
    (!filters.type || item.item_type === filters.type)
  );
}

function emptyPlanningFilters() {
  return { query: "", status: "", type: "" };
}

function priorityClass() {
  return "border-border bg-surface-quiet text-ink";
}

function PlanningBadge({ children, className = "" }) {
  return (
    <span
      className={`inline-flex rounded-full bg-surface-quiet px-2.5 py-1 text-[11px] font-medium text-ink-muted ${className}`}
    >
      {children}
    </span>
  );
}

function tagsFromInput(value) {
  return [
    ...new Set(
      value
        .split(/[\n,]/)
        .map((tag) => tag.trim())
        .filter(Boolean),
    ),
  ];
}

function auditActionLabel(action) {
  return (
    {
      work_item_created: "Tạo công việc",
      work_item_updated: "Cập nhật công việc",
      work_item_transitioned: "Chuyển trạng thái",
    }[action] || "Thay đổi công việc"
  );
}

function workItemFieldLabel(field) {
  return (
    {
      title: "tên",
      description: "mô tả",
      priority: "mức ưu tiên",
      estimate: "ước lượng",
      assignee_id: "người phụ trách",
      planned_start_at: "ngày bắt đầu dự kiến",
      planned_end_at: "ngày kết thúc dự kiến",
      due_at: "hạn hoàn thành",
      tags: "thẻ",
      requirement_ids: "liên kết yêu cầu",
    }[field] || field
  );
}

function readPlanningFilters(projectId) {
  if (typeof window === "undefined") return emptyPlanningFilters();
  try {
    const value = JSON.parse(window.sessionStorage.getItem(`veriq:planning-filters:${projectId}`));
    return {
      query: typeof value?.query === "string" ? value.query : "",
      status: typeof value?.status === "string" ? value.status : "",
      type: typeof value?.type === "string" ? value.type : "",
    };
  } catch {
    return emptyPlanningFilters();
  }
}

export default function PlanningPage({ project, section }) {
  const router = useRouter();
  const { ask, dialog } = useActionDialog();
  const [items, setItems] = useState([]);
  const [projectMembers, setProjectMembers] = useState([]);
  const [boardValue, setBoardValue] = useState(null);
  const [sprints, setSprints] = useState([]);
  const [roadmap, setRoadmap] = useState(null);
  const [planningFilters, setPlanningFilters] = useState({ query: "", status: "", type: "" });
  const updatePlanningFilters = useCallback(
    (update) => {
      setPlanningFilters((current) => {
        const next = typeof update === "function" ? update(current) : update;
        try {
          window.sessionStorage.setItem(
            `veriq:planning-filters:${project._id}`,
            JSON.stringify(next),
          );
        } catch {}
        return next;
      });
    },
    [project._id],
  );
  const [configurationMode, setConfigurationMode] = useState("");
  const [error, setError] = useState("");
  const [loading, setLoading] = useState(true);
  const [ranking, setRanking] = useState(false);
  const rankingRef = useRef(false);
  const loadSequence = useRef(0);
  const tab = section?.[0] || "backlog";
  const pageTitle =
    tab === "list"
      ? "Danh sách công việc"
      : tab === "backlog"
        ? "Danh sách chờ"
        : tab === "board"
          ? "Bảng công việc"
          : tab === "sprint"
            ? "Đợt lặp"
            : tab === "roadmap"
              ? "Lộ trình"
              : "Lập kế hoạch";
  const memberRoles = [project.current_membership?.project_role].filter(Boolean);
  const isBa = memberRoles.includes("BA");
  const currentUserId = project.current_membership?.user_id;
  const canReadProjectMembers = (project.current_permissions || []).includes(
    "project.members.read",
  );
  const memberLabels = Object.fromEntries(
    projectMembers.map((member) => {
      const userId = member.user_id;
      const label =
        member.user?.display_name || member.user?.label || member.user?.email || member.user_label;
      return [userId, typeof label === "string" && label !== userId ? label : "Thành viên dự án"];
    }),
  );
  const assigneeOptions = [
    { value: "", label: "Chưa phân công" },
    ...projectMembers
      .filter((member) => member.status === "ACTIVE")
      .map((member) => ({
        value: member.user_id,
        label: memberLabels[member.user_id],
      })),
  ];
  const canTransitionItem = (item, targetStatus = null) => {
    const canActOnItem =
      isBa || (memberRoles.includes("DEVELOPER") && item.assignee_id === currentUserId);
    if (!canActOnItem) return false;
    const allowedTransitions = (boardValue?.workflow?.transitions || []).filter(
      (transitionValue) =>
        transitionValue.from_status === item.status &&
        memberRoles.some((role) => transitionValue.allowed_roles?.includes(role)),
    );
    return targetStatus
      ? allowedTransitions.some((transitionValue) => transitionValue.to_status === targetStatus)
      : allowedTransitions.length > 0;
  };
  const planningMethod = project.planning_method || "SCRUM";
  const isScrum = planningMethod === "SCRUM";
  const filterScopeItems =
    tab === "backlog" ? items.filter((item) => item.status === "BACKLOG") : items;
  const filteredItems = filterScopeItems.filter((item) =>
    matchesPlanningFilters(item, planningFilters),
  );
  const filterableTabs = ["backlog", "list", "board", "roadmap"].includes(tab);
  const typeOptions = [
    ...new Set(
      [
        ...items.map((item) => item.item_type),
        "INITIATIVE",
        "EPIC",
        "RELEASE",
        ...(isScrum ? ["SPRINT"] : []),
      ].filter(Boolean),
    ),
  ].sort((left, right) => String(left).localeCompare(String(right), "vi"));
  const load = useCallback(async () => {
    const sequence = ++loadSequence.current;
    setLoading(true);
    try {
      const [board, roadmapValue, sprintValues, members] = await Promise.all([
        testingApi.workBoard(project._id),
        testingApi.roadmap(project._id),
        isScrum ? testingApi.listSprints(project._id) : Promise.resolve([]),
        canReadProjectMembers
          ? testingApi.listMembers(project._id).catch(() => [])
          : Promise.resolve([]),
      ]);
      if (sequence !== loadSequence.current) return;
      setItems(board.items || []);
      setBoardValue(board);
      setRoadmap(roadmapValue);
      setSprints(sprintValues);
      setProjectMembers(members);
      setError("");
    } catch (reason) {
      if (sequence === loadSequence.current) setError(planningErrorMessage(reason));
    } finally {
      if (sequence === loadSequence.current) setLoading(false);
    }
  }, [canReadProjectMembers, isScrum, project._id]);
  useEffect(() => {
    void load();
    return () => {
      loadSequence.current += 1;
    };
  }, [load]);
  useEffect(() => {
    setPlanningFilters(readPlanningFilters(project._id));
  }, [project._id]);
  const createItem = async () => {
    await ask({
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
        ...(canReadProjectMembers
          ? [{ name: "assignee_id", label: "Người phụ trách", options: assigneeOptions }]
          : []),
        {
          name: "priority",
          label: "Ưu tiên",
          options: ["LOW", "MEDIUM", "HIGH", "HIGHEST"].map((value) => ({
            value,
            label: valueLabel(value),
          })),
        },
        { name: "estimate", label: "Ước lượng", type: "number" },
        { name: "planned_start_at", label: "Bắt đầu dự kiến", type: "date" },
        { name: "planned_end_at", label: "Kết thúc dự kiến", type: "date" },
        { name: "due_at", label: "Hạn hoàn thành", type: "date" },
        { name: "tags", label: "Thẻ", placeholder: "Ví dụ: đăng nhập, bảo mật" },
      ],
      onConfirm: async (answer) => {
        ensureEndAfterStart(answer.planned_start_at, answer.planned_end_at);
        await testingApi.createWorkItem(project._id, {
          ...answer,
          title: answer.title.trim(),
          description: answer.description.trim(),
          parent_id: answer.parent_id || null,
          assignee_id: answer.assignee_id || null,
          tags: tagsFromInput(answer.tags || ""),
          estimate: answer.estimate ? Number(answer.estimate) : null,
          planned_start_at: answer.planned_start_at
            ? new Date(`${answer.planned_start_at}T00:00:00.000Z`).toISOString()
            : null,
          planned_end_at: answer.planned_end_at
            ? new Date(`${answer.planned_end_at}T00:00:00.000Z`).toISOString()
            : null,
          due_at: answer.due_at ? new Date(`${answer.due_at}T00:00:00.000Z`).toISOString() : null,
        });
        await load();
      },
    });
  };
  const editItem = async (item) => {
    const editAssigneeOptions =
      item.assignee_id && !assigneeOptions.some((option) => option.value === item.assignee_id)
        ? [
            ...assigneeOptions,
            {
              value: item.assignee_id,
              label: memberLabels[item.assignee_id] || "Thành viên dự án",
            },
          ]
        : assigneeOptions;
    await ask({
      title: `Chỉnh sửa ${valueLabel(item.item_type).toLocaleLowerCase()}`,
      confirmLabel: "Lưu thay đổi",
      fields: [
        { name: "title", label: "Tên", required: true, initialValue: item.title },
        {
          name: "description",
          label: "Mô tả",
          multiline: true,
          initialValue: item.description || "",
        },
        ...(canReadProjectMembers
          ? [
              {
                name: "assignee_id",
                label: "Người phụ trách",
                initialValue: item.assignee_id || "",
                options: editAssigneeOptions,
              },
            ]
          : []),
        {
          name: "priority",
          label: "Ưu tiên",
          initialValue: item.priority || "MEDIUM",
          options: ["LOW", "MEDIUM", "HIGH", "HIGHEST"].map((value) => ({
            value,
            label: valueLabel(value),
          })),
        },
        {
          name: "estimate",
          label: "Ước lượng",
          type: "number",
          initialValue: item.estimate == null ? "" : String(item.estimate),
        },
        {
          name: "planned_start_at",
          label: "Bắt đầu dự kiến",
          type: "date",
          initialValue: item.planned_start_at ? String(item.planned_start_at).slice(0, 10) : "",
        },
        {
          name: "planned_end_at",
          label: "Kết thúc dự kiến",
          type: "date",
          initialValue: item.planned_end_at ? String(item.planned_end_at).slice(0, 10) : "",
        },
        {
          name: "due_at",
          label: "Hạn hoàn thành",
          type: "date",
          initialValue: item.due_at ? String(item.due_at).slice(0, 10) : "",
        },
        {
          name: "tags",
          label: "Thẻ",
          placeholder: "Nhập thẻ, cách nhau bằng dấu phẩy",
          initialValue: (item.tags || []).join(", "),
        },
      ],
      onConfirm: async (answer) => {
        ensureEndAfterStart(answer.planned_start_at, answer.planned_end_at);
        await testingApi.updateWorkItem(project._id, item._id, {
          expected_revision: item.revision,
          title: answer.title.trim(),
          description: answer.description.trim(),
          ...(canReadProjectMembers ? { assignee_id: answer.assignee_id || null } : {}),
          tags: tagsFromInput(answer.tags || ""),
          priority: answer.priority,
          estimate: answer.estimate === "" ? null : Number(answer.estimate),
          planned_start_at: answer.planned_start_at
            ? new Date(`${answer.planned_start_at}T00:00:00.000Z`).toISOString()
            : null,
          planned_end_at: answer.planned_end_at
            ? new Date(`${answer.planned_end_at}T00:00:00.000Z`).toISOString()
            : null,
          due_at: answer.due_at ? new Date(`${answer.due_at}T00:00:00.000Z`).toISOString() : null,
        });
        await load();
      },
    });
  };
  const createSprint = async () => {
    await ask({
      title: "Tạo đợt lặp",
      confirmLabel: "Tạo đợt lặp",
      fields: [
        { name: "name", label: "Tên đợt lặp", required: true },
        { name: "goal", label: "Mục tiêu", multiline: true },
        { name: "start_at", label: "Bắt đầu", type: "date", required: true },
        { name: "end_at", label: "Kết thúc", type: "date", required: true },
      ],
      onConfirm: async (answer) => {
        ensureEndAfterStart(answer.start_at, answer.end_at);
        await testingApi.createSprint(project._id, answer);
        await load();
      },
    });
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
      await ask({
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
        onConfirm: async (answer) => {
          await testingApi.migrateProjectTasks(project._id, {
            mappings: preview.legacy_statuses.map((legacy_status) => ({
              legacy_status,
              target_status: answer[legacy_status],
            })),
          });
          await load();
        },
      });
    } catch (reason) {
      setError(messageOf(reason));
    }
  };
  const transition = async (item, status) => {
    if (!canTransitionItem(item, status)) return;
    await ask({
      title: "Chuyển trạng thái",
      confirmLabel: "Xác nhận",
      fields: [{ name: "reason", label: "Lý do", multiline: true }],
      onConfirm: async (answer) => {
        try {
          await testingApi.transitionWorkItem(project._id, item._id, {
            expected_revision: item.revision,
            status,
            reason: answer.reason.trim(),
          });
          await load();
        } catch (reason) {
          throw new Error(planningErrorMessage(reason));
        }
      },
    });
  };
  const rank = async (item, beforeItemId) => {
    if (rankingRef.current) return;
    rankingRef.current = true;
    setRanking(true);
    try {
      await testingApi.rankWorkItem(project._id, item._id, {
        expected_revision: item.revision,
        before_item_id: beforeItemId || null,
      });
      await load();
    } catch (reason) {
      setError(planningErrorMessage(reason));
    } finally {
      rankingRef.current = false;
      setRanking(false);
    }
  };
  const addDependency = async (item) => {
    await ask({
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
      onConfirm: async (answer) => {
        await testingApi.createWorkItemDependency(project._id, item._id, answer);
        await load();
      },
    });
  };
  const manageSprint = async (sprint, action) => {
    if (action === "scope") {
      await ask({
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
        onConfirm: async (answer) => {
          await testingApi.patchSprintScope(project._id, sprint._id, {
            expected_revision: sprint.revision,
            work_item_ids: answer.work_item_ids || [],
          });
          await load();
        },
      });
      return;
    }
    await ask({
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
      onConfirm: async (answer) => {
        await testingApi.transitionSprint(project._id, sprint._id, {
          expected_revision: sprint.revision,
          action,
          reason: answer.reason.trim(),
          unfinished_action: answer.unfinished_action || null,
          target_sprint_id: answer.target_sprint_id || null,
          target_status: answer.target_status || null,
        });
        await load();
      },
    });
  };
  if (loading)
    return (
      <WorkspacePage title={pageTitle}>
        <LoadingState />
      </WorkspacePage>
    );
  return (
    <WorkspacePage
      title={pageTitle}
      actions={
        isBa ? (
          <div className="flex flex-wrap gap-2">
            <button className="secondary-button" type="button" onClick={createItem}>
              <Plus size={16} />
              Tạo công việc
            </button>
            <button
              aria-label={
                planningMethod === "KANBAN" ? "Cột bảng và giới hạn công việc" : "Cấu hình bảng"
              }
              title={
                planningMethod === "KANBAN" ? "Cột bảng và giới hạn công việc" : "Cấu hình bảng"
              }
              className="icon-button h-11 w-11"
              type="button"
              onClick={() => setConfigurationMode("board")}
            >
              <Columns3 aria-hidden="true" size={17} />
            </button>
            <button
              aria-label="Cấu hình quy trình"
              title="Quy trình"
              className="icon-button h-11 w-11"
              type="button"
              onClick={() => setConfigurationMode("workflow")}
            >
              <Workflow aria-hidden="true" size={17} />
            </button>
            <button
              aria-label="Chuyển công việc cũ"
              title="Chuyển công việc cũ"
              className="icon-button h-11 w-11"
              type="button"
              onClick={migrateLegacyTasks}
            >
              <ArchiveRestore aria-hidden="true" size={17} />
            </button>
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
      {error && (
        <div className="space-y-2">
          <ErrorState message={error} />
          <button
            aria-label="Tải lại dữ liệu lập kế hoạch"
            className="icon-button h-9 w-9"
            title="Tải lại"
            type="button"
            onClick={() => void load()}
          >
            <RefreshCw aria-hidden="true" size={16} />
          </button>
        </div>
      )}
      {(tab === "list" || tab === "board" || filterableTabs) && (
        <section
          aria-label="Lọc và xem công việc"
          className="min-w-0 rounded-xl border border-border bg-surface p-4"
        >
          {(tab === "list" || tab === "board") && (
            <div className={filterableTabs ? "mb-4 border-b border-border pb-4" : ""}>
              <div
                className="inline-flex max-w-full flex-wrap gap-2"
                role="group"
                aria-label="Cách xem"
              >
                <button
                  type="button"
                  className={tab === "list" ? "apple-button" : "secondary-button"}
                  aria-pressed={tab === "list"}
                  onClick={() =>
                    router.push(projectRoute(project._id, PROJECT_SECTION_SLUGS.planning, "list"))
                  }
                >
                  Danh sách
                </button>
                <button
                  type="button"
                  className={tab === "board" ? "apple-button" : "secondary-button"}
                  aria-pressed={tab === "board"}
                  onClick={() =>
                    router.push(projectRoute(project._id, PROJECT_SECTION_SLUGS.planning, "board"))
                  }
                >
                  Bảng công việc
                </button>
              </div>
            </div>
          )}
          {filterableTabs && (
            <div
              aria-label="Bộ lọc lập kế hoạch"
              className="grid min-w-0 gap-3 sm:grid-cols-2 xl:grid-cols-[minmax(16rem,1fr)_minmax(12rem,0.45fr)_minmax(12rem,0.45fr)_auto]"
            >
              <label className="field-label">
                Tìm công việc
                <input
                  aria-label="Tìm công việc trong lập kế hoạch"
                  className="apple-input mt-2"
                  disabled={loading}
                  value={planningFilters.query}
                  onChange={(event) =>
                    updatePlanningFilters((current) => ({ ...current, query: event.target.value }))
                  }
                  placeholder="Mã, tên hoặc mô tả"
                />
              </label>
              <label className="field-label">
                Trạng thái
                <select
                  aria-label="Lọc trạng thái lập kế hoạch"
                  className="apple-input mt-2"
                  disabled={loading}
                  value={planningFilters.status}
                  onChange={(event) =>
                    updatePlanningFilters((current) => ({ ...current, status: event.target.value }))
                  }
                >
                  <option value="">Tất cả trạng thái</option>
                  {(boardValue?.workflow?.statuses || []).map((status) => (
                    <option key={status.key} value={status.key}>
                      {status.name}
                    </option>
                  ))}
                </select>
              </label>
              <label className="field-label">
                Loại công việc
                <select
                  aria-label="Lọc loại công việc lập kế hoạch"
                  className="apple-input mt-2"
                  disabled={loading}
                  value={planningFilters.type}
                  onChange={(event) =>
                    updatePlanningFilters((current) => ({ ...current, type: event.target.value }))
                  }
                >
                  <option value="">Tất cả loại</option>
                  {typeOptions.map((type) => (
                    <option key={type} value={type}>
                      {valueLabel(type)}
                    </option>
                  ))}
                </select>
              </label>
              <div className="flex min-w-0 items-end gap-3">
                <button
                  className="secondary-button whitespace-nowrap"
                  type="button"
                  onClick={() => updatePlanningFilters(emptyPlanningFilters())}
                  disabled={
                    loading ||
                    (!planningFilters.query && !planningFilters.status && !planningFilters.type)
                  }
                >
                  Xóa lọc
                </button>
                <span className="pb-3 text-xs text-ink-muted" aria-live="polite">
                  Hiển thị {filteredItems.length}/{filterScopeItems.length} công việc
                </span>
              </div>
            </div>
          )}
        </section>
      )}
      {tab === "backlog" && (
        <Backlog
          items={filteredItems}
          allItems={items}
          dependencies={roadmap?.dependencies || []}
          memberLabels={memberLabels}
          canRank={isBa}
          ranking={ranking}
          onRank={rank}
          onAddDependency={addDependency}
          onEdit={editItem}
        />
      )}
      {tab === "list" && (
        <Panel>
          <WorkItemList
            items={filteredItems}
            memberLabels={memberLabels}
            canReadProjectMembers={canReadProjectMembers}
            totalCount={items.length}
            statuses={boardValue?.workflow?.statuses || []}
            transitions={boardValue?.workflow?.transitions || []}
            canEdit={isBa}
            canTransitionItem={canTransitionItem}
            onEdit={editItem}
            onTransition={transition}
          />
        </Panel>
      )}
      {tab === "board" && (
        <Board
          projectId={project._id}
          items={filteredItems}
          allItems={items}
          board={boardValue?.board}
          workflow={boardValue?.workflow}
          sprints={sprints}
          releases={roadmap?.releases || []}
          dependencies={roadmap?.dependencies || []}
          planningMethod={planningMethod}
          memberLabels={memberLabels}
          canReadProjectMembers={canReadProjectMembers}
          onTransition={transition}
          roles={memberRoles}
          canTransitionItem={canTransitionItem}
          canEdit={isBa}
          onEdit={editItem}
          canReadAudit={(project.current_permissions || []).includes("project.audit.read")}
          onReorderColumns={async (sourceStatus, targetStatus) => {
            const columns = [...(boardValue?.board?.columns || [])].sort(
              (left, right) => left.position - right.position,
            );
            const sourceIndex = columns.findIndex((column) => column.status === sourceStatus);
            const targetIndex = columns.findIndex((column) => column.status === targetStatus);
            if (sourceIndex < 0 || targetIndex < 0 || sourceIndex === targetIndex) return;
            const [moved] = columns.splice(sourceIndex, 1);
            columns.splice(targetIndex, 0, moved);
            try {
              await testingApi.updateWorkBoard(project._id, {
                expected_revision: boardValue.board.revision,
                columns: columns.map((column, position) => ({
                  status: column.status,
                  name: column.name,
                  position,
                  wip_limit: column.wip_limit ?? null,
                })),
              });
              await load();
            } catch (reason) {
              setError(planningErrorMessage(reason));
            }
          }}
        />
      )}
      {tab === "sprint" && isScrum && (
        <Panel>
          <DataTable
            items={sprints}
            empty="Chưa có đợt lặp"
            columns={[
              { key: "name", label: "Đợt lặp" },
              { key: "goal", label: "Mục tiêu" },
              {
                key: "status",
                label: "Trạng thái",
                render: (item) => (
                  <PlanningBadge>
                    {boardValue?.workflow?.statuses?.find((value) => value.key === item.status)
                      ?.name || valueLabel(item.status)}
                  </PlanningBadge>
                ),
              },
              {
                key: "start_at",
                label: "Bắt đầu",
                render: (item) => formatCalendarDate(item.start_at),
              },
              {
                key: "end_at",
                label: "Kết thúc",
                render: (item) => formatCalendarDate(item.end_at),
              },
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
      {tab === "roadmap" && (
        <Roadmap
          value={roadmap}
          project={project}
          sprints={isScrum ? sprints : []}
          filters={planningFilters}
          memberLabels={memberLabels}
          canReadProjectMembers={canReadProjectMembers}
          canEdit={isBa}
          onEdit={editItem}
        />
      )}
      <PlanningConfigurationModal
        mode={configurationMode}
        planningMethod={planningMethod}
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
        onError={(reason) => setError(planningErrorMessage(reason))}
      />
      {dialog}
    </WorkspacePage>
  );
}

function PlanningConfigurationModal({
  mode,
  planningMethod,
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
          wip_limit:
            planningMethod !== "KANBAN"
              ? null
              : item.wip_limit === ""
                ? null
                : Number(item.wip_limit),
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
  const closeIfIdle = () => {
    if (!saving) onClose();
  };
  const availableStatusOptions = statuses.filter((item) => item.key.trim());
  return (
    <Modal
      isOpen={Boolean(mode)}
      onClose={closeIfIdle}
      ariaLabel={mode === "board" ? "Cấu hình bảng công việc" : "Cấu hình quy trình"}
      className="max-h-[94dvh] max-w-4xl overflow-y-auto"
    >
      <ModalHeader>
        <ModalTitle>
          {mode === "board" ? "Cấu hình bảng công việc" : "Cấu hình quy trình"}
        </ModalTitle>
      </ModalHeader>
      <form onSubmit={save}>
        <fieldset disabled={saving} className="m-0 min-w-0 border-0 p-0">
          <ModalContent>
            {mode === "board" ? (
              <div className="space-y-3">
                <p className="text-sm text-ink-muted">
                  Mỗi cột phản ánh một trạng thái công việc.
                  {planningMethod === "KANBAN"
                    ? " Giới hạn số công việc đang thực hiện được kiểm tra khi chuyển cột."
                    : " Giới hạn số công việc đang thực hiện chỉ áp dụng cho dự án Kanban."}
                </p>
                {columns.map((column, index) => (
                  <div
                    className={`grid min-w-0 gap-3 rounded-control border border-border p-3 ${planningMethod === "KANBAN" ? "xl:grid-cols-[minmax(0,1fr)_minmax(0,1fr)_140px_auto]" : "xl:grid-cols-[minmax(0,1fr)_minmax(0,1fr)_auto]"}`}
                    key={`${column.status}-${index}`}
                  >
                    <input
                      className="apple-input min-w-0 w-full"
                      aria-label={`Trạng thái cột ${index + 1}`}
                      value={column.status}
                      onChange={(event) =>
                        setColumns((items) =>
                          items.map((item, itemIndex) =>
                            itemIndex === index ? { ...item, status: event.target.value } : item,
                          ),
                        )
                      }
                      placeholder="Mã dùng trong quy trình"
                      required
                    />
                    <input
                      className="apple-input min-w-0 w-full"
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
                    {planningMethod === "KANBAN" && (
                      <input
                        className="apple-input min-w-0 w-full"
                        aria-label={`Giới hạn số công việc đang thực hiện ở cột ${index + 1}`}
                        type="number"
                        min="1"
                        value={column.wip_limit}
                        onChange={(event) =>
                          setColumns((items) =>
                            items.map((item, itemIndex) =>
                              itemIndex === index
                                ? { ...item, wip_limit: event.target.value }
                                : item,
                            ),
                          )
                        }
                        placeholder="Giới hạn công việc"
                      />
                    )}
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
                      className="grid min-w-0 gap-3 rounded-control border border-border p-3 xl:grid-cols-[minmax(0,1fr)_minmax(0,1fr)_auto_auto]"
                      key={`${status.key}-${index}`}
                    >
                      <input
                        className="apple-input min-w-0 w-full"
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
                        className="apple-input min-w-0 w-full"
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
                          setStatuses((items) =>
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
                      className="grid min-w-0 gap-3 rounded-control border border-border p-3 xl:grid-cols-[minmax(0,1fr)_minmax(0,1fr)_minmax(0,1fr)_auto]"
                      key={`${transition.from_status}-${transition.to_status}-${index}`}
                    >
                      <select
                        className="apple-input min-w-0 w-full"
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
                        className="apple-input min-w-0 w-full"
                        aria-label={`Đến trạng thái ${index + 1}`}
                        value={transition.to_status}
                        onChange={(event) =>
                          setTransitions((items) =>
                            items.map((item, itemIndex) =>
                              itemIndex === index
                                ? { ...item, to_status: event.target.value }
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
                      <MultiSelect
                        label={`Vai trò được phép chuyển trạng thái ${index + 1}`}
                        options={["BA", "QA", "TESTER", "DEVELOPER"].map((role) => ({
                          value: role,
                          label: valueLabel(role),
                        }))}
                        searchPlaceholder="Tìm vai trò"
                        value={transition.allowed_roles}
                        onChange={(allowed_roles) =>
                          setTransitions((items) =>
                            items.map((item, itemIndex) =>
                              itemIndex === index ? { ...item, allowed_roles } : item,
                            ),
                          )
                        }
                      />
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
        </fieldset>
        <ModalFooter>
          <button
            className="secondary-button"
            type="button"
            disabled={saving}
            onClick={closeIfIdle}
          >
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

function Backlog({
  items,
  allItems,
  dependencies,
  memberLabels,
  canRank,
  ranking,
  onRank,
  onAddDependency,
  onEdit,
}) {
  const [draggedId, setDraggedId] = useState("");
  const parentTitles = new Map((allItems || []).map((item) => [item._id, item.title]));
  if (!items.length)
    return <p className="p-5 text-sm text-ink-muted">Chưa có công việc trong danh sách chờ</p>;
  return (
    <ol className="grid gap-3 p-3" aria-label="Thứ tự công việc trong danh sách chờ">
      {items.map((item, index) => (
        <li
          key={item._id}
          draggable={canRank && !ranking}
          onDragStart={() => setDraggedId(item._id)}
          onDragEnd={() => setDraggedId("")}
          onDragOver={(event) => event.preventDefault()}
          onDrop={(event) => {
            event.preventDefault();
            const dragged = items.find((value) => value._id === draggedId);
            if (dragged && dragged._id !== item._id && !ranking) void onRank(dragged, item._id);
            setDraggedId("");
          }}
          className={`grid gap-4 rounded-xl border border-border bg-surface p-4 shadow-sm transition hover:border-brand/40 xl:grid-cols-[minmax(0,1fr)_auto] xl:items-start ${canRank ? "cursor-grab active:cursor-grabbing" : ""}`}
        >
          <div className="min-w-0">
            <div className="flex flex-wrap items-center gap-2">
              {canRank && (
                <span
                  className="inline-flex h-8 items-center gap-1 rounded-md bg-surface-quiet px-2 text-xs font-semibold text-ink-muted"
                  title="Kéo để đổi thứ tự"
                >
                  <GripVertical aria-hidden="true" size={15} />
                  {index + 1}
                </span>
              )}
              {!canRank && (
                <span className="inline-flex h-8 min-w-8 items-center justify-center rounded-full bg-surface-quiet px-2 text-xs font-semibold text-ink-muted">
                  {index + 1}
                </span>
              )}
              <PlanningBadge>{valueLabel(item.item_type)}</PlanningBadge>
              <span
                className={`inline-flex min-h-7 items-center rounded-full border px-2.5 text-xs font-semibold ${priorityClass(item.priority)}`}
                aria-label={`Mức ưu tiên: ${valueLabel(item.priority)}`}
              >
                Ưu tiên {valueLabel(item.priority)}
              </span>
              {item.due_at && (
                <span className="inline-flex min-h-7 items-center text-xs font-medium text-ink-muted">
                  Hạn {formatCalendarDate(item.due_at)}
                </span>
              )}
            </div>
            <strong className="mt-2 block break-words text-base font-semibold leading-6 text-ink">
              {item.title}
            </strong>
            {item.description && (
              <p className="mt-1 line-clamp-2 text-sm leading-5 text-ink-muted">
                {item.description}
              </p>
            )}
            <div className="mt-3 flex min-w-0 flex-wrap items-baseline gap-x-6 gap-y-1.5 text-[13px] text-ink-muted">
              <span
                className="min-w-0 break-words [overflow-wrap:anywhere]"
                title={
                  item.assignee_id
                    ? memberLabels[item.assignee_id] || "Thành viên dự án"
                    : "Chưa phân công"
                }
              >
                Người phụ trách:{" "}
                <strong className="font-medium text-ink">
                  {item.assignee_id
                    ? memberLabels[item.assignee_id] || "Thành viên dự án"
                    : "Chưa phân công"}
                </strong>
              </span>
              <span className="min-w-0 break-words">
                {item.planned_start_at || item.planned_end_at ? (
                  <>
                    {item.planned_start_at && (
                      <>
                        Bắt đầu dự kiến{" "}
                        <strong className="font-medium text-ink">
                          {formatCalendarDate(item.planned_start_at)}
                        </strong>
                      </>
                    )}
                    {item.planned_start_at && item.planned_end_at && " · "}
                    {item.planned_end_at && (
                      <>
                        Kết thúc dự kiến{" "}
                        <strong className="font-medium text-ink">
                          {formatCalendarDate(item.planned_end_at)}
                        </strong>
                      </>
                    )}
                  </>
                ) : (
                  <>
                    Thời gian dự kiến:{" "}
                    <strong className="font-medium text-ink">Chưa xếp lịch</strong>
                  </>
                )}
              </span>
              {item.estimate != null && (
                <span className="whitespace-nowrap">
                  Ước lượng: <strong className="font-medium text-ink">{item.estimate}</strong>
                </span>
              )}
              {item.requirement_ids?.length > 0 && (
                <span className="whitespace-nowrap">
                  Yêu cầu liên quan:{" "}
                  <strong className="font-medium text-ink">{item.requirement_ids.length}</strong>
                </span>
              )}
            </div>
            {item.parent_id && parentTitles.has(item.parent_id) && (
              <p
                className="mt-1 min-w-0 truncate text-sm text-ink-muted"
                title={parentTitles.get(item.parent_id)}
              >
                Thuộc: {parentTitles.get(item.parent_id)}
              </p>
            )}
            {item.tags?.length > 0 && (
              <div className="mt-2 flex flex-wrap gap-1.5">
                {item.tags.map((tag) => (
                  <span
                    className="rounded-full bg-surface-quiet px-2.5 py-1.5 text-xs font-medium text-ink-muted"
                    key={`${item._id}-${tag}`}
                  >
                    {tag}
                  </span>
                ))}
              </div>
            )}
            {dependencies
              .filter(
                (dependency) =>
                  dependency.source_item_id === item._id || dependency.target_item_id === item._id,
              )
              .map((dependency) => {
                const isSource = dependency.source_item_id === item._id;
                const label =
                  dependency.dependency_type === "RELATES_TO"
                    ? "Liên quan"
                    : isSource
                      ? "Chặn"
                      : "Bị chặn bởi";
                const relatedTitle = isSource
                  ? dependency.target_item_title
                  : dependency.source_item_title;
                return (
                  <p className="mt-2 text-sm text-ink-muted" key={dependency._id}>
                    {label}: {relatedTitle || "Công việc liên quan"}
                  </p>
                );
              })}
          </div>
          {canRank && (
            <span className="flex items-center justify-end gap-2 xl:pt-1">
              <button
                aria-label={`Sửa ${item.title}`}
                className="icon-button h-10 w-10"
                title="Sửa công việc"
                disabled={ranking}
                type="button"
                onClick={() => onEdit(item)}
              >
                <Pencil aria-hidden="true" size={16} />
              </button>
              <button
                aria-label={`Đưa ${item.title} lên trước`}
                className="icon-button h-10 w-10"
                title="Đưa lên trước"
                disabled={index === 0 || ranking}
                type="button"
                onClick={() => void onRank(item, items[index - 1]?._id)}
              >
                <ArrowUp aria-hidden="true" size={14} />
              </button>
              <button
                aria-label={`Đưa ${item.title} xuống sau`}
                className="icon-button h-10 w-10"
                title="Đưa xuống sau"
                disabled={index === items.length - 1 || ranking}
                type="button"
                onClick={() => void onRank(items[index + 1], item._id)}
              >
                <ArrowDown aria-hidden="true" size={14} />
              </button>
              <button
                aria-label={`Quản lý phụ thuộc của ${item.title}`}
                className="icon-button h-10 w-10"
                title="Quản lý phụ thuộc"
                disabled={ranking}
                type="button"
                onClick={() => onAddDependency(item)}
              >
                <GitBranch aria-hidden="true" size={16} />
              </button>
              {ranking && (
                <span aria-live="polite" className="text-xs text-ink-muted">
                  Đang lưu thứ tự…
                </span>
              )}
            </span>
          )}
        </li>
      ))}
    </ol>
  );
}

function WorkItemList({
  items,
  memberLabels,
  canReadProjectMembers,
  totalCount,
  statuses,
  transitions,
  canEdit,
  canTransitionItem,
  onEdit,
  onTransition,
}) {
  const itemTitles = new Map(items.map((item) => [item._id, item.title]));
  const showActionColumn = canEdit || items.some((item) => canTransitionItem(item));
  const titleColumnWidth =
    100 - (13 + 11 + (canReadProjectMembers ? 16 : 0) + 11 + (showActionColumn ? 16 : 0));
  return (
    <div className="p-4">
      <DataTable
        items={items}
        empty={totalCount ? "Không có công việc khớp bộ lọc" : "Chưa có công việc trong dự án"}
        layout="wide-table"
        renderMobileCard={(item) => {
          const statusName =
            statuses.find((value) => value.key === item.status)?.name || valueLabel(item.status);
          const assignee = item.assignee_id
            ? memberLabels[item.assignee_id] || "Thành viên dự án"
            : "Chưa phân công";
          const parentTitle = item.parent_id ? itemTitles.get(item.parent_id) : "";
          const availableTransitions = transitions
            .filter((transitionValue) => transitionValue.from_status === item.status)
            .filter((transitionValue) => canTransitionItem(item, transitionValue.to_status));

          return (
            <div className="space-y-3">
              <div className="flex flex-wrap items-center gap-2">
                <PlanningBadge>{statusName}</PlanningBadge>
                <span
                  className={`inline-flex min-h-7 items-center rounded-full border px-2.5 text-xs font-semibold ${priorityClass(item.priority)}`}
                >
                  Ưu tiên: {valueLabel(item.priority)}
                </span>
              </div>

              <div className="min-w-0">
                <h3 className="break-words text-[15px] font-semibold leading-6 text-ink [overflow-wrap:anywhere]">
                  {item.title}
                </h3>
                {item.description && (
                  <p className="mt-1 line-clamp-2 break-words text-sm leading-5 text-ink-muted">
                    {item.description}
                  </p>
                )}
              </div>

              {(item.item_type || item.tags?.length > 0) && (
                <div className="flex flex-wrap gap-1.5">
                  {item.item_type && (
                    <span className="text-xs text-ink-muted">{valueLabel(item.item_type)}</span>
                  )}
                  {item.tags?.slice(0, 2).map((tag) => (
                    <span
                      key={`${item._id}-${tag}`}
                      className="max-w-40 truncate rounded-full bg-surface-quiet px-2.5 py-1 text-xs text-ink-muted"
                      title={tag}
                    >
                      {tag}
                    </span>
                  ))}
                  {item.tags?.length > 2 && (
                    <span
                      className="rounded-full bg-surface-quiet px-2.5 py-1 text-xs text-ink-muted"
                      title={item.tags.slice(2).join(", ")}
                    >
                      +{item.tags.length - 2}
                    </span>
                  )}
                </div>
              )}

              <dl className="grid min-w-0 gap-x-5 gap-y-2 border-t border-border pt-3 text-[13px] sm:grid-cols-2">
                {canReadProjectMembers && (
                  <div className="min-w-0">
                    <dt className="text-xs text-ink-muted">Người phụ trách</dt>
                    <dd className="mt-0.5 break-words font-medium text-ink [overflow-wrap:anywhere]">
                      {assignee}
                    </dd>
                  </div>
                )}
                {(item.planned_start_at || item.planned_end_at) && (
                  <div className="min-w-0">
                    <dt className="text-xs text-ink-muted">Thời gian dự kiến</dt>
                    <dd className="mt-0.5 break-words font-medium text-ink">
                      {item.planned_start_at
                        ? formatCalendarDate(item.planned_start_at)
                        : "Chưa đặt ngày bắt đầu"}
                      {item.planned_end_at && ` – ${formatCalendarDate(item.planned_end_at)}`}
                    </dd>
                  </div>
                )}
                {item.due_at && (
                  <div className="min-w-0">
                    <dt className="text-xs text-ink-muted">Hạn</dt>
                    <dd className="mt-0.5 font-medium text-ink">
                      {formatCalendarDate(item.due_at)}
                    </dd>
                  </div>
                )}
                {item.estimate != null && (
                  <div className="min-w-0">
                    <dt className="text-xs text-ink-muted">Ước lượng</dt>
                    <dd className="mt-0.5 font-medium text-ink">{item.estimate}</dd>
                  </div>
                )}
                {item.requirement_ids?.length > 0 && (
                  <div className="min-w-0">
                    <dt className="text-xs text-ink-muted">Yêu cầu liên quan</dt>
                    <dd className="mt-0.5 font-medium text-ink">{item.requirement_ids.length}</dd>
                  </div>
                )}
                {parentTitle && (
                  <div className="min-w-0 sm:col-span-2">
                    <dt className="text-xs text-ink-muted">Thuộc hạng mục</dt>
                    <dd className="mt-0.5 break-words font-medium text-ink [overflow-wrap:anywhere]">
                      {parentTitle}
                    </dd>
                  </div>
                )}
              </dl>

              {(canEdit || availableTransitions.length > 0) && (
                <div className="flex flex-wrap gap-2 border-t border-border pt-3">
                  {canEdit && (
                    <button
                      aria-label={`Sửa ${item.title}`}
                      className="icon-button h-10 w-10"
                      title="Sửa công việc"
                      type="button"
                      onClick={() => onEdit(item)}
                    >
                      <Pencil aria-hidden="true" size={16} />
                    </button>
                  )}
                  {availableTransitions.map((transitionValue) => (
                    <button
                      className="secondary-button"
                      key={`${item._id}-${transitionValue.to_status}`}
                      type="button"
                      onClick={() => onTransition(item, transitionValue.to_status)}
                    >
                      Chuyển{" "}
                      {statuses.find((value) => value.key === transitionValue.to_status)?.name ||
                        valueLabel(transitionValue.to_status)}
                    </button>
                  ))}
                </div>
              )}
            </div>
          );
        }}
        columns={[
          {
            key: "title",
            label: "Tên công việc",
            width: `${titleColumnWidth}%`,
            minWidth: 304,
            render: (item) => {
              const tags = Array.isArray(item.tags) ? item.tags : [];
              const parentTitle = item.parent_id ? itemTitles.get(item.parent_id) : "";
              return (
                <div className="min-w-0 space-y-1">
                  <p
                    className="line-clamp-2 break-words text-sm font-medium leading-5 text-ink [overflow-wrap:anywhere]"
                    title={item.title}
                  >
                    {item.title}
                  </p>
                  {item.description && (
                    <p className="line-clamp-1 text-xs leading-4 text-ink-muted">
                      {item.description}
                    </p>
                  )}
                  {(item.item_type || tags.length > 0) && (
                    <div className="flex flex-wrap gap-1.5 pt-1">
                      {item.item_type && (
                        <span className="text-[10px] font-medium text-ink-muted">
                          {valueLabel(item.item_type)}
                        </span>
                      )}
                      {tags.slice(0, 2).map((tag) => (
                        <span
                          key={`${item._id}-${tag}`}
                          className="max-w-32 truncate rounded-full bg-surface-quiet px-2 py-0.5 text-[11px] font-medium text-ink-muted"
                          title={tag}
                        >
                          {tag}
                        </span>
                      ))}
                      {tags.length > 2 && (
                        <span
                          className="rounded-full bg-surface-quiet px-2 py-0.5 text-[11px] font-medium text-ink-muted"
                          title={tags.slice(2).join(", ")}
                        >
                          +{tags.length - 2}
                        </span>
                      )}
                    </div>
                  )}
                  {(item.planned_start_at ||
                    item.planned_end_at ||
                    item.estimate != null ||
                    item.requirement_ids?.length > 0 ||
                    parentTitle) && (
                    <div className="flex flex-wrap gap-x-3 gap-y-1 text-xs leading-4 text-ink">
                      {(item.planned_start_at || item.planned_end_at) && (
                        <span>
                          <span className="font-medium text-ink-muted">Thời gian:</span>{" "}
                          <span>
                            {item.planned_start_at
                              ? formatCalendarDate(item.planned_start_at)
                              : "Chưa đặt"}
                            {item.planned_end_at && ` – ${formatCalendarDate(item.planned_end_at)}`}
                          </span>
                        </span>
                      )}
                      {item.estimate != null && (
                        <span>
                          <span className="font-medium text-ink-muted">Ước lượng:</span>{" "}
                          {item.estimate}
                        </span>
                      )}
                      {item.requirement_ids?.length > 0 && (
                        <span>
                          <span className="font-medium text-ink-muted">Yêu cầu liên quan:</span>{" "}
                          {item.requirement_ids.length}
                        </span>
                      )}
                      {parentTitle && (
                        <span className="max-w-full truncate" title={`Thuộc: ${parentTitle}`}>
                          <span className="font-medium text-ink-muted">Thuộc:</span> {parentTitle}
                        </span>
                      )}
                    </div>
                  )}
                </div>
              );
            },
          },
          {
            key: "status",
            label: "Trạng thái",
            width: "13%",
            minWidth: 136,
            render: (item) => (
              <PlanningBadge className="whitespace-nowrap">
                {statuses.find((value) => value.key === item.status)?.name ||
                  valueLabel(item.status)}
              </PlanningBadge>
            ),
          },
          {
            key: "priority",
            label: "Ưu tiên",
            width: "11%",
            minWidth: 112,
            render: (item) => (
              <span
                className={`inline-flex whitespace-nowrap rounded-full border px-2.5 py-1 text-xs font-semibold ${priorityClass(item.priority)}`}
              >
                {valueLabel(item.priority)}
              </span>
            ),
          },
          ...(canReadProjectMembers
            ? [
                {
                  key: "assignee_id",
                  label: "Người phụ trách",
                  width: "16%",
                  minWidth: 132,
                  render: (item) => {
                    const name =
                      (item.assignee_id && memberLabels[item.assignee_id]) || "Chưa phân công";
                    return (
                      <span
                        className="line-clamp-2 break-words [overflow-wrap:anywhere]"
                        title={name}
                      >
                        {name}
                      </span>
                    );
                  },
                  hideWhenEmpty: true,
                },
              ]
            : []),
          {
            key: "due_at",
            label: "Hạn",
            width: "11%",
            minWidth: 112,
            render: (item) => (item.due_at ? formatCalendarDate(item.due_at) : "Chưa đặt"),
          },
          ...(showActionColumn
            ? [
                {
                  key: "actions",
                  label: "Thao tác",
                  width: "16%",
                  minWidth: 184,
                  render: (item) => {
                    const availableTransitions = transitions
                      .filter((transitionValue) => transitionValue.from_status === item.status)
                      .filter((transitionValue) =>
                        canTransitionItem(item, transitionValue.to_status),
                      );
                    return (
                      <span className="flex min-w-0 flex-wrap items-center gap-2">
                        {canEdit && (
                          <button
                            aria-label={`Sửa ${item.title}`}
                            className="icon-button h-10 w-10"
                            title="Sửa công việc"
                            type="button"
                            onClick={() => onEdit(item)}
                          >
                            <Pencil aria-hidden="true" size={16} />
                          </button>
                        )}
                        {availableTransitions.length > 0 && (
                          <select
                            aria-label={`Chuyển trạng thái ${item.title}`}
                            className="apple-input min-w-0 flex-1 !py-2 text-xs"
                            value=""
                            onChange={(event) => {
                              const nextStatus = event.target.value;
                              if (nextStatus) onTransition(item, nextStatus);
                            }}
                          >
                            <option value="">Chuyển trạng thái</option>
                            {availableTransitions.map((transitionValue) => (
                              <option
                                key={`${item._id}-${transitionValue.to_status}`}
                                value={transitionValue.to_status}
                              >
                                {statuses.find((value) => value.key === transitionValue.to_status)
                                  ?.name || valueLabel(transitionValue.to_status)}
                              </option>
                            ))}
                          </select>
                        )}
                      </span>
                    );
                  },
                },
              ]
            : []),
        ]}
      />
    </div>
  );
}

function Board({
  projectId,
  items,
  allItems,
  board,
  workflow,
  planningMethod,
  sprints,
  releases,
  dependencies,
  memberLabels,
  canReadProjectMembers,
  onTransition,
  canTransitionItem,
  roles,
  canEdit,
  onEdit,
  canReadAudit,
  onReorderColumns,
}) {
  const [draggedItem, setDraggedItem] = useState(null);
  const [draggedColumnStatus, setDraggedColumnStatus] = useState(null);
  const [collapsedStatuses, setCollapsedStatuses] = useState([]);
  const [historyItem, setHistoryItem] = useState(null);
  const [historyEvents, setHistoryEvents] = useState([]);
  const [historyLoading, setHistoryLoading] = useState(false);
  const [historyError, setHistoryError] = useState("");
  const allItemTitles = new Map(allItems.map((item) => [item._id, item.title]));
  const sprintLabels = new Map(sprints.map((sprint) => [sprint._id, sprint.name]));
  const releaseLabels = new Map(
    releases.map((release) => [release._id, release.name || release.title]),
  );
  const [boardScroll, setBoardScroll] = useState({ overflow: false, start: true, end: true });
  const boardViewportRef = useRef(null);
  const statusName = (status) =>
    (workflow?.statuses || []).find((value) => value.key === status)?.name || valueLabel(status);
  const openHistory = async (item) => {
    setHistoryItem(item);
    setHistoryEvents([]);
    setHistoryError("");
    setHistoryLoading(true);
    try {
      const events = await testingApi.audit(projectId, {
        entity_type: "WorkItem",
        entity_id: item._id,
      });
      setHistoryEvents(
        events
          .filter((event) => event.entity_type === "WorkItem" && event.entity_id === item._id)
          .sort((left, right) => new Date(right.created_at) - new Date(left.created_at)),
      );
    } catch (reason) {
      setHistoryError(messageOf(reason));
    } finally {
      setHistoryLoading(false);
    }
  };
  const configuredColumns = (board?.columns || [])
    .slice()
    .sort((left, right) => left.position - right.position);
  const configuredStatuses = new Set(configuredColumns.map((column) => column.status));
  const unconfiguredStatuses = [...new Set(items.map((item) => item.status))]
    .filter((status) => status && !configuredStatuses.has(status))
    .map((status) => {
      const workflowStatus = (workflow?.statuses || []).find((value) => value.key === status);
      return {
        status,
        name: workflowStatus?.name || statusName(status),
        position: Number.MAX_SAFE_INTEGER,
        unconfigured: true,
      };
    });
  const groups = [...configuredColumns, ...unconfiguredStatuses].map((column) => ({
    ...column,
    items: items.filter((item) => item.status === column.status),
  }));
  useEffect(() => {
    const viewport = boardViewportRef.current;
    if (!viewport) return undefined;
    const updateScroll = () => {
      const maxScroll = viewport.scrollWidth - viewport.clientWidth;
      const next = {
        overflow: maxScroll > 4,
        start: viewport.scrollLeft <= 4,
        end: viewport.scrollLeft >= maxScroll - 4,
      };
      setBoardScroll((current) =>
        current.overflow === next.overflow &&
        current.start === next.start &&
        current.end === next.end
          ? current
          : next,
      );
    };
    const observer = new ResizeObserver(updateScroll);
    observer.observe(viewport);
    Array.from(viewport.children).forEach((child) => observer.observe(child));
    viewport.addEventListener("scroll", updateScroll, { passive: true });
    updateScroll();
    return () => {
      observer.disconnect();
      viewport.removeEventListener("scroll", updateScroll);
    };
  }, [groups.length]);
  if (!groups.length) {
    return (
      <Panel title="Bảng công việc">
        <p className="p-5 text-sm text-ink-muted">Chưa có cột nào trong bảng công việc</p>
      </Panel>
    );
  }
  const scrollBoard = (direction) =>
    boardViewportRef.current?.scrollBy({
      left: direction * Math.max(boardViewportRef.current.clientWidth * 0.75, 220),
      behavior: "smooth",
    });
  return (
    <div>
      {boardScroll.overflow && (
        <div className="mb-2 flex items-center justify-between gap-3 text-xs text-ink-muted">
          <span>Cuộn ngang để xem các cột còn lại</span>
          <div className="flex items-center gap-1">
            <button
              aria-label="Cuộn bảng sang trái"
              className="icon-button h-8 w-8"
              disabled={boardScroll.start}
              onClick={() => scrollBoard(-1)}
              type="button"
            >
              <ChevronLeft aria-hidden="true" size={16} />
            </button>
            <button
              aria-label="Cuộn bảng sang phải"
              className="icon-button h-8 w-8"
              disabled={boardScroll.end}
              onClick={() => scrollBoard(1)}
              type="button"
            >
              <ChevronRight aria-hidden="true" size={16} />
            </button>
          </div>
        </div>
      )}
      <div
        aria-label="Các cột trên bảng công việc"
        className="overflow-x-auto scroll-smooth pb-3 focus-visible:rounded-lg focus-visible:outline focus-visible:outline-2 focus-visible:outline-brand"
        role="region"
        ref={boardViewportRef}
        tabIndex={0}
      >
        <div
          className="grid min-w-0 items-stretch gap-4 transition-[grid-template-columns] duration-200"
          style={{
            gridTemplateColumns: groups
              .map((column) =>
                collapsedStatuses.includes(column.status) ? "72px" : "minmax(340px, 1fr)",
              )
              .join(" "),
          }}
        >
          {groups.map((column) => {
            const collapsed = collapsedStatuses.includes(column.status);
            const columnName = column.name || statusName(column.status);
            return (
              <div
                key={column.status}
                className={`h-full min-w-0 transition-opacity duration-150 ${draggedColumnStatus === column.status ? "opacity-45" : "opacity-100"}`}
                onDragOver={(event) => {
                  if (
                    draggedColumnStatus &&
                    !column.unconfigured &&
                    draggedColumnStatus !== column.status
                  ) {
                    event.preventDefault();
                    event.dataTransfer.dropEffect = "move";
                  }
                }}
                onDrop={(event) => {
                  event.preventDefault();
                  event.stopPropagation();
                  if (draggedColumnStatus && !column.unconfigured) {
                    void onReorderColumns?.(draggedColumnStatus, column.status);
                  }
                  setDraggedColumnStatus(null);
                }}
              >
                <Panel
                  className={`flex h-full flex-col ${
                    collapsed
                      ? "[&_.workspace-panel-header]:block [&_.workspace-panel-header]:p-2 [&_.workspace-panel-heading]:w-full [&_.workspace-panel-heading]:min-w-0 [&_.workspace-panel-heading]:flex-none"
                      : ""
                  }`}
                  title={
                    <span
                      className={`flex w-full ${collapsed ? "flex-col items-center gap-2" : "items-center justify-between gap-2"}`}
                    >
                      {canEdit && !column.unconfigured && !collapsed && (
                        <button
                          aria-label={`Kéo để di chuyển cột ${columnName}`}
                          className="icon-button h-8 w-8 shrink-0 cursor-grab active:cursor-grabbing"
                          draggable
                          onDragStart={(event) => {
                            event.stopPropagation();
                            event.dataTransfer.effectAllowed = "move";
                            event.dataTransfer.setData("text/plain", column.status);
                            setDraggedColumnStatus(column.status);
                          }}
                          onDragEnd={() => setDraggedColumnStatus(null)}
                          onClick={(event) => event.preventDefault()}
                          title="Kéo để đổi vị trí cột"
                          type="button"
                        >
                          <GripVertical aria-hidden="true" size={16} />
                        </button>
                      )}
                      <span
                        className={
                          collapsed
                            ? "max-h-48 [writing-mode:vertical-rl] rotate-180 text-xs"
                            : "min-w-0 truncate"
                        }
                      >
                        {columnName}
                      </span>
                      {canEdit && !column.unconfigured && !collapsed && (
                        <span className="flex shrink-0 items-center gap-1">
                          <button
                            aria-label={`Đưa cột ${columnName} sang trái`}
                            className="icon-button h-8 w-8"
                            disabled={
                              configuredColumns.findIndex(
                                (value) => value.status === column.status,
                              ) === 0
                            }
                            onClick={() => {
                              const index = configuredColumns.findIndex(
                                (value) => value.status === column.status,
                              );
                              const neighbor = configuredColumns[index - 1];
                              if (neighbor) void onReorderColumns?.(column.status, neighbor.status);
                            }}
                            title="Đưa cột sang trái"
                            type="button"
                          >
                            <ArrowLeft aria-hidden="true" size={15} />
                          </button>
                          <button
                            aria-label={`Đưa cột ${columnName} sang phải`}
                            className="icon-button h-8 w-8"
                            disabled={
                              configuredColumns.findIndex(
                                (value) => value.status === column.status,
                              ) ===
                              configuredColumns.length - 1
                            }
                            onClick={() => {
                              const index = configuredColumns.findIndex(
                                (value) => value.status === column.status,
                              );
                              const neighbor = configuredColumns[index + 1];
                              if (neighbor) void onReorderColumns?.(column.status, neighbor.status);
                            }}
                            title="Đưa cột sang phải"
                            type="button"
                          >
                            <ArrowRight aria-hidden="true" size={15} />
                          </button>
                        </span>
                      )}
                      <button
                        aria-expanded={!collapsed}
                        aria-label={`${collapsed ? "Mở rộng" : "Thu gọn"} cột ${columnName}`}
                        className="icon-button h-8 w-8 shrink-0"
                        onClick={() =>
                          setCollapsedStatuses((current) =>
                            current.includes(column.status)
                              ? current.filter((status) => status !== column.status)
                              : [...current, column.status],
                          )
                        }
                        type="button"
                      >
                        {collapsed ? (
                          <ChevronRight aria-hidden="true" size={16} />
                        ) : (
                          <ChevronLeft aria-hidden="true" size={16} />
                        )}
                      </button>
                    </span>
                  }
                  description={
                    collapsed
                      ? ""
                      : column.unconfigured
                        ? "Chưa cấu hình cột trên bảng"
                        : planningMethod === "KANBAN" && column.wip_limit != null
                          ? `${column.items.length}/${column.wip_limit} công việc`
                          : `${column.items.length} công việc`
                  }
                >
                  {!collapsed && (
                    <div
                      aria-label={`Công việc trong cột ${column.name || statusName(column.status)}`}
                      className={`min-h-0 flex-1 space-y-4 p-4 ${column.items.length ? "min-h-32" : "min-h-20"}`}
                      role="group"
                      onDragOver={(event) => {
                        if (
                          draggedItem &&
                          !column.unconfigured &&
                          draggedItem.status !== column.status &&
                          canTransitionItem(draggedItem, column.status)
                        ) {
                          event.preventDefault();
                        }
                      }}
                      onDrop={(event) => {
                        event.preventDefault();
                        event.stopPropagation();
                        if (
                          draggedItem &&
                          !column.unconfigured &&
                          canTransitionItem(draggedItem, column.status) &&
                          draggedItem.status !== column.status
                        ) {
                          void onTransition(draggedItem, column.status);
                        }
                        setDraggedItem(null);
                      }}
                    >
                      {column.items.length === 0 ? (
                        <p className="flex min-h-16 items-center justify-center rounded-lg border border-dashed border-border px-3 text-center text-xs text-ink-faint">
                          Chưa có công việc
                        </p>
                      ) : (
                        column.items.map((item) => {
                          const canTransition = canTransitionItem(item);
                          const nextTransition = (workflow?.transitions || [])
                            .filter((value) => value.from_status === item.status)
                            .find((value) =>
                              roles.some((role) => value.allowed_roles?.includes(role)),
                            );
                          const overdue =
                            item.due_at && new Date(item.due_at).getTime() < Date.now();
                          return (
                            <article
                              className={`min-w-0 rounded-xl border border-border bg-surface-raised p-3 shadow-[0_4px_14px_rgba(48,47,42,0.035)] transition-shadow hover:shadow-[0_8px_24px_rgba(48,47,42,0.09)] ${canTransition ? "cursor-grab active:cursor-grabbing" : ""}`}
                              draggable={canTransition}
                              onDragStart={() => setDraggedItem(item)}
                              onDragEnd={() => setDraggedItem(null)}
                              key={item._id}
                            >
                              <div className="flex flex-wrap items-center justify-between gap-2">
                                <PlanningBadge>{valueLabel(item.item_type)}</PlanningBadge>
                                <div className="flex items-center gap-2">
                                  <span
                                    className={`inline-flex min-h-7 items-center rounded-full border px-2.5 text-xs font-semibold ${priorityClass(item.priority)}`}
                                    aria-label={`Mức ưu tiên: ${valueLabel(item.priority)}`}
                                  >
                                    {valueLabel(item.priority)}
                                  </span>
                                  {canReadAudit && (
                                    <button
                                      aria-label={`Xem lịch sử ${item.title}`}
                                      className="icon-button h-8 w-8"
                                      onClick={() => void openHistory(item)}
                                      title="Lịch sử thay đổi"
                                      type="button"
                                    >
                                      <History aria-hidden="true" size={15} />
                                    </button>
                                  )}
                                </div>
                              </div>
                              <strong className="mt-3 block break-words text-base leading-6">
                                {item.title}
                              </strong>
                              {item.description && (
                                <p className="mt-2 line-clamp-3 text-sm leading-5 text-ink-muted">
                                  {item.description}
                                </p>
                              )}
                              {item.parent_id && allItemTitles.has(item.parent_id) && (
                                <p className="mt-3 truncate border-l-2 border-border pl-2 text-xs text-ink-muted">
                                  Trong: {allItemTitles.get(item.parent_id)}
                                </p>
                              )}
                              {(item.sprint_id || item.release_id) && (
                                <div className="mt-2 flex flex-wrap gap-1.5 text-xs">
                                  {item.sprint_id && sprintLabels.has(item.sprint_id) && (
                                    <span className="rounded-md bg-surface-quiet px-2 py-1 font-medium text-ink">
                                      Đợt lặp: {sprintLabels.get(item.sprint_id)}
                                    </span>
                                  )}
                                  {item.release_id && releaseLabels.has(item.release_id) && (
                                    <span className="rounded-md bg-surface-quiet px-2 py-1 font-medium text-ink">
                                      Bản phát hành: {releaseLabels.get(item.release_id)}
                                    </span>
                                  )}
                                </div>
                              )}
                              {dependencies
                                .filter(
                                  (dependency) =>
                                    dependency.source_item_id === item._id ||
                                    dependency.target_item_id === item._id,
                                )
                                .map((dependency) => {
                                  const isSource = dependency.source_item_id === item._id;
                                  const relatedId = isSource
                                    ? dependency.target_item_id
                                    : dependency.source_item_id;
                                  const relatedTitle = allItemTitles.get(relatedId);
                                  if (!relatedTitle) return null;
                                  const label = isSource ? "Chặn" : "Bị chặn bởi";
                                  return (
                                    <p
                                      className="mt-2 truncate text-xs text-ink-muted"
                                      key={dependency._id}
                                      title={`${label}: ${relatedTitle}`}
                                    >
                                      {label}: {relatedTitle}
                                    </p>
                                  );
                                })}
                              <div className="mt-3 grid gap-1.5 border-t border-border pt-2.5 text-sm">
                                {canReadProjectMembers && (
                                  <p className="flex min-w-0 items-center gap-2">
                                    <span className="truncate font-medium">
                                      {item.assignee_id
                                        ? memberLabels[item.assignee_id] || "Thành viên dự án"
                                        : "Chưa phân công"}
                                    </span>
                                  </p>
                                )}
                                {(item.planned_start_at || item.planned_end_at) && (
                                  <p className="flex min-w-0 items-center gap-2 text-ink-muted">
                                    <span className="truncate">
                                      {item.planned_start_at
                                        ? formatCalendarDate(item.planned_start_at)
                                        : "Chưa đặt ngày bắt đầu"}
                                      {item.planned_end_at &&
                                        ` – ${formatCalendarDate(item.planned_end_at)}`}
                                    </span>
                                  </p>
                                )}
                                {item.due_at && (
                                  <p className="flex min-w-0 items-center gap-2 font-medium text-ink">
                                    <span>
                                      {overdue ? "Quá hạn" : "Hạn"}:{" "}
                                      {formatCalendarDate(item.due_at)}
                                    </span>
                                  </p>
                                )}
                              </div>
                              {(item.tags?.length > 0 ||
                                item.estimate != null ||
                                item.requirement_ids?.length > 0) && (
                                <div className="mt-3 flex flex-wrap items-center gap-2">
                                  {(item.tags || []).map((tag) => (
                                    <span
                                      key={`${item._id}-${tag}`}
                                      className="inline-flex rounded-full bg-surface-quiet px-2.5 py-1 text-xs font-medium text-ink-muted"
                                    >
                                      {tag}
                                    </span>
                                  ))}
                                  {item.estimate != null && (
                                    <span className="rounded-full border border-border px-2.5 py-1 text-xs text-ink-muted">
                                      Ước lượng {item.estimate}
                                    </span>
                                  )}
                                  {item.requirement_ids?.length > 0 && (
                                    <span className="rounded-full border border-border px-2.5 py-1 text-xs text-ink-muted">
                                      {item.requirement_ids.length} yêu cầu liên quan
                                    </span>
                                  )}
                                </div>
                              )}
                              {(canEdit || canTransition) && (
                                <div className="mt-3 flex items-center justify-end gap-2 border-t border-border pt-2.5">
                                  {canEdit && (
                                    <button
                                      aria-label={`Sửa ${item.title}`}
                                      className="icon-button h-9 w-9"
                                      type="button"
                                      onClick={() => onEdit(item)}
                                      title="Sửa công việc"
                                    >
                                      <Pencil aria-hidden="true" size={16} />
                                    </button>
                                  )}
                                  {canTransition && nextTransition && (
                                    <button
                                      aria-label={`Chuyển ${item.title} sang ${statusName(nextTransition.to_status)}`}
                                      className="icon-button h-9 w-9"
                                      type="button"
                                      onClick={() => onTransition(item, nextTransition.to_status)}
                                      title={`Chuyển sang ${statusName(nextTransition.to_status)}`}
                                    >
                                      <ArrowRight aria-hidden="true" size={16} />
                                    </button>
                                  )}
                                </div>
                              )}
                            </article>
                          );
                        })
                      )}
                    </div>
                  )}
                </Panel>
              </div>
            );
          })}
        </div>
      </div>
      <Modal
        isOpen={Boolean(historyItem)}
        onClose={() => setHistoryItem(null)}
        ariaLabel="Lịch sử thay đổi công việc"
        className="max-h-[90dvh] max-w-2xl overflow-y-auto"
      >
        <ModalHeader>
          <ModalTitle>Lịch sử thay đổi</ModalTitle>
        </ModalHeader>
        <ModalContent>
          {historyItem && <p className="mb-4 text-sm font-medium">{historyItem.title}</p>}
          {historyLoading ? (
            <p className="text-sm text-ink-muted">Đang tải lịch sử…</p>
          ) : historyError ? (
            <p className="text-sm text-red-700" role="alert">
              {historyError}
            </p>
          ) : historyEvents.length ? (
            <ol className="space-y-3">
              {historyEvents.map((event) => (
                <li key={event._id} className="rounded-lg border border-border p-3">
                  <div className="flex flex-wrap items-center justify-between gap-2">
                    <strong className="text-sm">{auditActionLabel(event.action)}</strong>
                    <time className="text-xs text-ink-muted" dateTime={event.created_at}>
                      {event.created_at ? new Date(event.created_at).toLocaleString("vi-VN") : ""}
                    </time>
                  </div>
                  <p className="mt-1 text-xs text-ink-muted">
                    {event.actor_label || "Thành viên dự án"}
                  </p>
                  {event.details?.changed?.length > 0 && (
                    <p className="mt-2 text-sm">
                      Đã cập nhật: {event.details.changed.map(workItemFieldLabel).join(", ")}
                    </p>
                  )}
                </li>
              ))}
            </ol>
          ) : (
            <p className="text-sm text-ink-muted">
              Chưa có thay đổi được ghi nhận cho công việc này.
            </p>
          )}
        </ModalContent>
        <ModalFooter>
          <button className="secondary-button" onClick={() => setHistoryItem(null)} type="button">
            Đóng
          </button>
        </ModalFooter>
      </Modal>
    </div>
  );
}

function Roadmap({
  value,
  project,
  sprints = [],
  filters,
  memberLabels,
  canReadProjectMembers,
  canEdit,
  onEdit,
}) {
  const dateValue = (dateInput) => {
    if (!dateInput) return null;
    const dateOnly =
      typeof dateInput === "string" && dateInput.match(/^(\d{4})-(\d{2})-(\d{2})(?:$|T)/);
    const date = dateOnly
      ? new Date(Date.UTC(Number(dateOnly[1]), Number(dateOnly[2]) - 1, Number(dateOnly[3])))
      : new Date(dateInput);
    if (
      dateOnly &&
      (date.getUTCFullYear() !== Number(dateOnly[1]) ||
        date.getUTCMonth() + 1 !== Number(dateOnly[2]) ||
        date.getUTCDate() !== Number(dateOnly[3]))
    ) {
      return null;
    }
    return Number.isNaN(date.getTime()) ? null : date;
  };
  const formatTimelineDate = (date) =>
    date
      ? date.toLocaleDateString("vi-VN", {
          timeZone: "UTC",
          day: "2-digit",
          month: "2-digit",
          year: "numeric",
        })
      : "Chưa có";
  const items = [
    ...(value?.items || []),
    ...(value?.releases || []).map((release) => ({
      ...release,
      title: release.title || release.name,
      item_type: "RELEASE",
      timeline_kind: "RELEASE",
    })),
    ...sprints.map((sprint) => ({
      ...sprint,
      _id: sprint._id,
      title: sprint.name,
      item_type: "SPRINT",
      planned_start_at: sprint.start_at,
      planned_end_at: sprint.end_at,
      timeline_kind: "SPRINT",
    })),
  ];
  const visibleItems = items.filter((item) => matchesPlanningFilters(item, filters));
  const visibleItemTitles = new Map(
    visibleItems.map((item) => [item._id, item.name || item.title]),
  );
  const visibleItemIds = new Set(visibleItems.map((item) => item._id).filter(Boolean));
  const dependencies = (value?.dependencies || []).filter(
    (dependency) =>
      visibleItemIds.has(dependency.source_item_id) &&
      visibleItemIds.has(dependency.target_item_id),
  );
  const itemSchedules = visibleItems.map((item) => {
    const scheduledStart = item.planned_start_at ?? item.start_at;
    const scheduledEnd = item.planned_end_at ?? item.end_at;
    const hasStart = Boolean(scheduledStart);
    const hasEnd = Boolean(scheduledEnd);
    const hasDue = Boolean(item.due_at);
    const plannedStart = dateValue(scheduledStart);
    const plannedEnd = dateValue(scheduledEnd);
    const due = dateValue(item.due_at);
    const invalidDate = (hasStart && !plannedStart) || (hasEnd && !plannedEnd) || (hasDue && !due);
    const isRelease = !item.timeline_kind && !item.item_type;
    const invalidRange = invalidTimelineRange(plannedStart, plannedEnd, isRelease);
    const dates = [plannedStart, plannedEnd, due].filter(Boolean);
    return {
      item,
      plannedStart,
      plannedEnd,
      due,
      dates,
      invalid: invalidDate || invalidRange,
      invalidRange,
    };
  });
  const datedItems = itemSchedules
    .filter((entry) => entry.dates.length > 0 && !entry.invalid)
    .sort((left, right) => {
      const leftDate = Math.min(...left.dates.map((date) => date.getTime()));
      const rightDate = Math.min(...right.dates.map((date) => date.getTime()));
      return (
        leftDate - rightDate ||
        String(left.item.name || left.item.title || "").localeCompare(
          String(right.item.name || right.item.title || ""),
          "vi",
        )
      );
    });
  const undatedItems = itemSchedules.filter((entry) => entry.dates.length === 0 && !entry.invalid);
  const invalidItems = itemSchedules.filter((entry) => entry.invalid);
  const projectStart = dateValue(project.planned_start_at);
  const projectEnd = dateValue(project.planned_end_at);
  const invalidProjectDate =
    (Boolean(project.planned_start_at) && !projectStart) ||
    (Boolean(project.planned_end_at) && !projectEnd);
  const invalidProjectRange = invalidTimelineRange(projectStart, projectEnd);
  const projectRange =
    !invalidProjectDate && !invalidProjectRange && (projectStart || projectEnd)
      ? { start: projectStart || projectEnd, end: projectEnd || projectStart }
      : null;
  const projectDateLabel =
    projectStart && projectEnd
      ? "Khoảng thời gian dự kiến của dự án"
      : projectStart
        ? "Ngày bắt đầu dự kiến của dự án"
        : "Ngày kết thúc dự kiến của dự án";
  const projectDateDescription =
    projectStart && projectEnd
      ? `${formatTimelineDate(projectStart)} – ${formatTimelineDate(projectEnd)}`
      : projectStart
        ? `Từ ${formatTimelineDate(projectStart)}`
        : projectEnd
          ? `Đến ${formatTimelineDate(projectEnd)}`
          : "";
  const timelineDates = [
    ...datedItems.flatMap(({ dates }) => dates),
    ...(projectRange ? [projectRange.start, projectRange.end] : []),
  ];
  const timelineStart = timelineDates.length
    ? new Date(Math.min(...timelineDates.map((date) => date.getTime())))
    : null;
  const timelineEnd = timelineDates.length
    ? new Date(Math.max(...timelineDates.map((date) => date.getTime())))
    : null;
  const monthSpan =
    timelineStart && timelineEnd
      ? (timelineEnd.getUTCFullYear() - timelineStart.getUTCFullYear()) * 12 +
        timelineEnd.getUTCMonth() -
        timelineStart.getUTCMonth()
      : 0;
  const yearlyTicks = monthSpan > 24;
  const yearInterval = yearlyTicks ? Math.max(1, Math.ceil(monthSpan / 12 / 60)) : 1;
  const timelineScaleStart = timelineStart
    ? new Date(
        Date.UTC(timelineStart.getUTCFullYear(), yearlyTicks ? 0 : timelineStart.getUTCMonth(), 1),
      )
    : null;
  const timelineScaleEnd = timelineEnd
    ? yearlyTicks
      ? new Date(Date.UTC(timelineEnd.getUTCFullYear() + 1, 0, 1))
      : new Date(Date.UTC(timelineEnd.getUTCFullYear(), timelineEnd.getUTCMonth() + 1, 1))
    : null;
  const timelineTicks = [];
  if (timelineStart && timelineEnd) {
    const cursor = yearlyTicks
      ? new Date(Date.UTC(timelineStart.getUTCFullYear(), 0, 1))
      : new Date(Date.UTC(timelineStart.getUTCFullYear(), timelineStart.getUTCMonth(), 1));
    const lastTick = yearlyTicks
      ? new Date(Date.UTC(timelineEnd.getUTCFullYear(), 0, 1))
      : new Date(Date.UTC(timelineEnd.getUTCFullYear(), timelineEnd.getUTCMonth(), 1));
    while (cursor <= lastTick) {
      timelineTicks.push({
        date: new Date(cursor),
        label: cursor.toLocaleDateString(
          "vi-VN",
          yearlyTicks
            ? { timeZone: "UTC", year: "numeric" }
            : { timeZone: "UTC", month: "short", year: "numeric" },
        ),
      });
      if (yearlyTicks) cursor.setUTCFullYear(cursor.getUTCFullYear() + yearInterval);
      else cursor.setUTCMonth(cursor.getUTCMonth() + 1);
    }
    if (yearlyTicks && timelineTicks.at(-1)?.date.getTime() !== lastTick.getTime()) {
      timelineTicks.push({
        date: new Date(lastTick),
        label: lastTick.toLocaleDateString("vi-VN", { timeZone: "UTC", year: "numeric" }),
      });
    }
  }
  const timelineDays =
    timelineScaleStart && timelineScaleEnd
      ? Math.max(1, (timelineScaleEnd.getTime() - timelineScaleStart.getTime()) / 86400000)
      : 1;
  const projectDurationDays = projectPlannedDurationDays(
    project.planned_start_at,
    project.planned_end_at,
  );
  const timelinePosition = (date) =>
    timelineScaleStart && date
      ? Math.max(
          0,
          Math.min(
            100,
            ((date.getTime() - timelineScaleStart.getTime()) / 86400000 / timelineDays) * 100,
          ),
        )
      : 0;
  const timelineTickWeights = timelineTicks.map((tick, index) => {
    const next = timelineTicks[index + 1]?.date || timelineScaleEnd;
    return Math.max(1, next ? (next.getTime() - tick.date.getTime()) / 86400000 : 1);
  });
  const timelineChartWidth = Math.max(420, timelineTicks.length * 64);
  const timelineGridColumns = `minmax(300px, 1.2fr) minmax(${timelineChartWidth}px, 2fr)`;
  const timelineContentWidth = 300 + timelineChartWidth + 44;
  return (
    <div className="space-y-4">
      <Panel title="Thời gian dự án">
        <div className="grid gap-3 p-4 sm:grid-cols-2 lg:grid-cols-3">
          <div>
            <span className="text-xs text-ink-muted">Bắt đầu dự kiến</span>
            <p className="mt-1 text-sm font-semibold">
              {project.planned_start_at ? formatTimelineDate(projectStart) : "Chưa đặt"}
            </p>
          </div>
          <div>
            <span className="text-xs text-ink-muted">Kết thúc dự kiến</span>
            <p className="mt-1 text-sm font-semibold">
              {project.planned_end_at ? formatTimelineDate(projectEnd) : "Chưa đặt"}
            </p>
          </div>
          <div>
            <span className="text-xs text-ink-muted">Thời lượng dự kiến</span>
            <p className="mt-1 text-sm font-semibold">
              {projectDurationDays == null
                ? "Chưa đủ ngày để tính"
                : `${projectDurationDays} ngày lịch`}
            </p>
          </div>
        </div>
        {(invalidProjectDate || invalidProjectRange) && (
          <p
            role="status"
            className="mx-4 mb-4 rounded-control border border-amber-300 bg-amber-50 p-3 text-sm text-amber-900"
          >
            {invalidProjectRange
              ? "Ngày kết thúc dự án phải sau ngày bắt đầu; lộ trình không vẽ khoảng ngày sai này."
              : "Ngày dự án không đọc được; hãy kiểm tra lại cấu hình ngày trong dự án."}
          </p>
        )}
      </Panel>
      <Panel title="Lộ trình dự án theo thời gian">
        {!visibleItems.length && !projectRange && !invalidProjectDate && !invalidProjectRange ? (
          <p className="p-4 text-sm text-ink-muted">
            {items.length
              ? "Không có mục lộ trình khớp bộ lọc"
              : "Chưa có sáng kiến, hạng mục lớn hoặc bản phát hành"}
          </p>
        ) : (
          <div className="space-y-5 p-4">
            {(datedItems.length > 0 || projectRange) && (
              <div
                aria-label="Lộ trình dự án theo thời gian"
                className="overflow-x-auto border-y border-border focus-visible:outline focus-visible:outline-2 focus-visible:outline-brand"
                role="region"
                tabIndex={0}
              >
                <div className="py-2" style={{ minWidth: `${timelineContentWidth}px` }}>
                  <div
                    className="grid items-end gap-3"
                    style={{ gridTemplateColumns: timelineGridColumns }}
                  >
                    <span className="sticky left-0 z-10 min-w-0 border-r border-border bg-surface pr-3 text-sm font-semibold text-ink">
                      Hạng mục
                    </span>
                    <div
                      className="grid border-b border-border"
                      style={{
                        gridTemplateColumns: timelineTickWeights
                          .map((weight) => `minmax(64px, ${weight}fr)`)
                          .join(" "),
                      }}
                    >
                      {timelineTicks.map(({ date, label }) => (
                        <span
                          className="border-l border-border px-2 pb-2 text-xs text-ink-muted"
                          key={`${date.getUTCFullYear()}-${date.getUTCMonth()}`}
                        >
                          {label}
                        </span>
                      ))}
                    </div>
                  </div>
                  <ol className="divide-y divide-border">
                    {projectRange && (
                      <li
                        className="grid items-center gap-3 py-3"
                        style={{ gridTemplateColumns: timelineGridColumns }}
                      >
                        <div className="sticky left-0 z-10 min-w-0 border-r border-border bg-surface pr-3">
                          <strong className="text-sm">Toàn dự án</strong>
                          <p className="text-xs text-ink-muted">{projectDateLabel}</p>
                        </div>
                        <div
                          className="relative h-9 rounded bg-surface-quiet"
                          aria-label={`${projectDateLabel}: ${projectDateDescription}`}
                        >
                          {timelineTicks.map(({ date }) => (
                            <span
                              className="absolute inset-y-0 border-l border-border/70"
                              key={`project-${date.getUTCFullYear()}-${date.getUTCMonth()}`}
                              style={{ left: `${timelinePosition(date)}%` }}
                            />
                          ))}
                          {projectStart && projectEnd ? (
                            <div
                              className="absolute inset-y-1 rounded bg-ink-muted/70 px-2 text-[11px] leading-7 text-white"
                              style={{
                                left: `${timelinePosition(projectRange.start)}%`,
                                width: `${Math.max(1.5, timelinePosition(projectRange.end) - timelinePosition(projectRange.start))}%`,
                                minWidth: "3.25rem",
                              }}
                            >
                              <span className="block truncate">{projectDateDescription}</span>
                            </div>
                          ) : (
                            <span
                              className="absolute top-1/2 h-3 w-3 -translate-x-1/2 -translate-y-1/2 rotate-45 rounded-sm bg-ink-muted"
                              style={{ left: `${timelinePosition(projectRange.start)}%` }}
                              title={`${projectDateLabel}: ${formatTimelineDate(projectRange.start)}`}
                              aria-label={`${projectDateLabel}: ${formatTimelineDate(projectRange.start)}`}
                            />
                          )}
                        </div>
                      </li>
                    )}
                    {datedItems.map(({ item, plannedStart, plannedEnd, due }) => {
                      const itemId = item._id;
                      const related = dependencies.filter(
                        (dependency) =>
                          dependency.source_item_id === itemId ||
                          dependency.target_item_id === itemId,
                      );
                      const relatedDescriptions = related.map((dependency) => {
                        const isSource = dependency.source_item_id === itemId;
                        const relatedTitle = isSource
                          ? dependency.target_item_title
                          : dependency.source_item_title;
                        const relatedType = isSource
                          ? dependency.target_item_type
                          : dependency.source_item_type;
                        const relation =
                          dependency.dependency_type === "RELATES_TO"
                            ? "Liên quan đến"
                            : isSource
                              ? "Chặn"
                              : "Bị chặn bởi";
                        return `${relation} ${relatedType ? `${valueLabel(relatedType)} ` : ""}${relatedTitle || (isSource ? dependency.target_item_id : dependency.source_item_id)}`;
                      });
                      const dateFields = [
                        plannedStart && {
                          label: "Bắt đầu dự kiến:",
                          value: formatTimelineDate(plannedStart),
                        },
                        plannedEnd && {
                          label: "Kết thúc dự kiến:",
                          value: formatTimelineDate(plannedEnd),
                        },
                        due && { label: "Hạn:", value: formatTimelineDate(due) },
                      ].filter(Boolean);
                      const dateLabels = dateFields.map(({ label, value }) => `${label} ${value}`);
                      const rangeWidth =
                        plannedStart && plannedEnd
                          ? Math.max(
                              1.5,
                              timelinePosition(plannedEnd) - timelinePosition(plannedStart),
                            )
                          : 0;
                      return (
                        <li
                          className="grid items-center gap-3 py-3"
                          key={itemId}
                          style={{ gridTemplateColumns: timelineGridColumns }}
                        >
                          <div className="sticky left-0 z-10 min-w-0 border-r border-border bg-surface pr-3">
                            <div className="flex items-start justify-between gap-2">
                              <div className="min-w-0">
                                <strong
                                  className="line-clamp-2 break-words text-base font-semibold leading-6 text-ink [overflow-wrap:anywhere]"
                                  title={item.name || item.title}
                                >
                                  {item.name || item.title}
                                </strong>
                                <p className="mt-0.5 text-sm leading-5 text-ink-muted">
                                  {item.timeline_kind === "SPRINT"
                                    ? "Đợt lặp"
                                    : item.item_type
                                      ? valueLabel(item.item_type)
                                      : "Bản phát hành"}
                                  {item.status && ` · ${valueLabel(item.status)}`}
                                </p>
                              </div>
                              {canEdit && !["SPRINT", "RELEASE"].includes(item.timeline_kind) && (
                                <button
                                  aria-label={`Sửa mốc và thông tin của ${item.name || item.title}`}
                                  className="icon-button h-8 w-8 shrink-0"
                                  title="Sửa mốc và thông tin"
                                  type="button"
                                  onClick={() => onEdit(item)}
                                >
                                  <Pencil aria-hidden="true" size={13} />
                                </button>
                              )}
                            </div>
                            <dl className="mt-2 grid max-w-max grid-cols-[max-content,max-content] gap-x-2 gap-y-0.5 text-xs leading-5">
                              {dateFields.map(({ label, value }) => (
                                <div className="contents" key={`${itemId}-${label}`}>
                                  <dt className="text-ink-muted">{label}</dt>
                                  <dd className="font-medium text-ink">{value}</dd>
                                </div>
                              ))}
                            </dl>
                            {(canReadProjectMembers ||
                              item.priority ||
                              relatedDescriptions.length > 0) && (
                              <details className="mt-1 text-xs">
                                <summary className="w-fit cursor-pointer leading-5 text-ink-muted">
                                  Phân công, ưu tiên và liên kết
                                </summary>
                                <div className="mt-1 grid gap-1 leading-5">
                                  {canReadProjectMembers && (
                                    <p>
                                      <span className="text-ink-muted">Người phụ trách: </span>
                                      <span className="font-medium text-ink">
                                        {item.assignee_id
                                          ? memberLabels[item.assignee_id] || "Thành viên dự án"
                                          : "Chưa phân công"}
                                      </span>
                                    </p>
                                  )}
                                  <p>
                                    <span className="text-ink-muted">Ưu tiên: </span>
                                    <span className="font-medium text-ink">
                                      {item.priority ? valueLabel(item.priority) : "Chưa đánh giá"}
                                    </span>
                                  </p>
                                  {relatedDescriptions.map((description, index) => (
                                    <p
                                      className="text-ink-muted"
                                      key={`${itemId}-dependency-${index}`}
                                    >
                                      {description}
                                    </p>
                                  ))}
                                </div>
                              </details>
                            )}
                          </div>
                          <div
                            className="relative h-9 rounded bg-surface-quiet"
                            aria-label={`${item.name || item.title}: ${dateLabels.join(", ")}`}
                          >
                            {timelineTicks.map(({ date }) => (
                              <span
                                className="absolute inset-y-0 border-l border-border/70"
                                key={`${itemId}-${date.getUTCFullYear()}-${date.getUTCMonth()}`}
                                style={{ left: `${timelinePosition(date)}%` }}
                              />
                            ))}
                            {plannedStart && plannedEnd && (
                              <div
                                className="absolute inset-y-1 rounded bg-ink-muted/70"
                                style={{
                                  left: `${timelinePosition(plannedStart)}%`,
                                  width: `${rangeWidth}%`,
                                  minWidth: "0.75rem",
                                }}
                                title={`Khoảng thời gian dự kiến: ${formatTimelineDate(plannedStart)} – ${formatTimelineDate(plannedEnd)}`}
                              />
                            )}
                            {[
                              { date: plannedStart, label: "Bắt đầu dự kiến", offset: 0 },
                              { date: plannedEnd, label: "Kết thúc dự kiến", offset: 0 },
                              { date: due, label: "Hạn hoàn thành", offset: 1 },
                            ]
                              .filter((marker) => marker.date)
                              .map((marker) => (
                                <span
                                  className={`absolute h-3 w-3 -translate-x-1/2 rotate-45 rounded-sm ${marker.label === "Hạn hoàn thành" ? "bg-ink" : "bg-ink-muted/80"}`}
                                  key={`${itemId}-${marker.label}`}
                                  style={{
                                    left: `${timelinePosition(marker.date)}%`,
                                    top: marker.offset ? "1.25rem" : "0.625rem",
                                  }}
                                  title={`${marker.label}: ${formatTimelineDate(marker.date)}`}
                                  aria-label={`${marker.label}: ${formatTimelineDate(marker.date)}`}
                                />
                              ))}
                          </div>
                        </li>
                      );
                    })}
                  </ol>
                </div>
              </div>
            )}
            {undatedItems.length > 0 && (
              <section aria-label="Hạng mục chưa lập lịch" className="border-t border-border">
                <div className="px-0 py-3 text-sm font-semibold">
                  Chưa lập lịch ({undatedItems.length})
                </div>
                <DataTable
                  items={undatedItems.map(({ item }) => item)}
                  minTableWidth={canReadProjectMembers ? 760 : 650}
                  columns={[
                    {
                      key: "work-item",
                      label: "Hạng mục",
                      minWidth: 220,
                      render: (item) => (
                        <div className="min-w-0">
                          <p className="flex flex-wrap items-center gap-x-1 text-sm font-medium leading-5 text-ink">
                            {valueLabel(
                              item.timeline_kind === "SPRINT"
                                ? "SPRINT"
                                : item.item_type || "RELEASE",
                            )}
                            {item.status && (
                              <span className="text-ink-muted">· {valueLabel(item.status)}</span>
                            )}
                          </p>
                          <strong
                            className="mt-1 line-clamp-2 break-words text-base font-semibold leading-6 text-ink [overflow-wrap:anywhere]"
                            title={item.name || item.title}
                          >
                            {item.name || item.title}
                          </strong>
                          {item.description && (
                            <p className="mt-1 line-clamp-2 text-sm leading-5 text-ink-muted">
                              {item.description}
                            </p>
                          )}
                        </div>
                      ),
                    },
                    {
                      key: "priority",
                      label: "Ưu tiên",
                      minWidth: 100,
                      render: (item) =>
                        item.priority ? (
                          <span className="whitespace-nowrap text-sm font-medium text-ink">
                            {valueLabel(item.priority)}
                          </span>
                        ) : (
                          <span className="whitespace-nowrap text-ink-muted">Chưa đánh giá</span>
                        ),
                    },
                    ...(canReadProjectMembers
                      ? [
                          {
                            key: "assignee",
                            label: "Người phụ trách",
                            minWidth: 116,
                            render: (item) =>
                              item.assignee_id
                                ? memberLabels[item.assignee_id] || "Thành viên dự án"
                                : "Chưa phân công",
                          },
                        ]
                      : []),
                    {
                      key: "estimate",
                      label: "Ước lượng",
                      minWidth: 76,
                      render: (item) => item.estimate ?? "—",
                    },
                    {
                      key: "links",
                      label: "Liên kết",
                      minWidth: 150,
                      render: (item) => (
                        <div className="space-y-1 text-xs">
                          {item.requirement_ids?.length > 0 && (
                            <div>{item.requirement_ids.length} yêu cầu</div>
                          )}
                          {item.parent_id && visibleItemTitles.has(item.parent_id) && (
                            <div
                              className="max-w-40 truncate text-ink-muted"
                              title={visibleItemTitles.get(item.parent_id)}
                            >
                              Thuộc: {visibleItemTitles.get(item.parent_id)}
                            </div>
                          )}
                          {item.tags?.length > 0 && (
                            <div className="flex max-w-40 flex-wrap gap-1">
                              {item.tags.map((tag) => (
                                <span
                                  className="rounded-full bg-surface-quiet px-2 py-0.5 text-ink"
                                  key={`${item._id}-${tag}`}
                                >
                                  {tag}
                                </span>
                              ))}
                            </div>
                          )}
                          {!item.requirement_ids?.length &&
                            !item.parent_id &&
                            !item.tags?.length && <span className="text-ink-muted">—</span>}
                        </div>
                      ),
                    },
                    {
                      key: "actions",
                      label: "Thao tác",
                      minWidth: 56,
                      render: (item) =>
                        canEdit && !["SPRINT", "RELEASE"].includes(item.timeline_kind) ? (
                          <button
                            aria-label={`Thêm lịch cho ${item.name || item.title}`}
                            className="icon-button h-9 w-9"
                            title="Thêm lịch"
                            type="button"
                            onClick={() => onEdit(item)}
                          >
                            <Pencil aria-hidden="true" size={15} />
                          </button>
                        ) : null,
                    },
                  ]}
                />
              </section>
            )}
            {(invalidItems.length > 0 || invalidProjectDate || invalidProjectRange) && (
              <section
                aria-label="Lịch cần kiểm tra"
                className="rounded-lg border border-amber-300 bg-amber-50/60"
              >
                <h3 className="border-b border-amber-200 px-4 py-3 text-sm font-semibold text-amber-950">
                  Ngày cần kiểm tra (
                  {invalidItems.length + Number(invalidProjectDate || invalidProjectRange)})
                </h3>
                <ul className="divide-y divide-amber-200">
                  {(invalidProjectDate || invalidProjectRange) && (
                    <li className="px-4 py-3 text-sm">
                      Toàn dự án ·{" "}
                      {invalidProjectRange
                        ? "Ngày kết thúc phải sau ngày bắt đầu"
                        : "Ngày dự án không hợp lệ"}
                    </li>
                  )}
                  {invalidItems.map(({ item, invalidRange }) => (
                    <li className="px-4 py-3 text-sm" key={item._id}>
                      {item.name || item.title} ·{" "}
                      {invalidRange
                        ? "Ngày kết thúc phải sau ngày bắt đầu"
                        : "Một ngày không hợp lệ"}
                    </li>
                  ))}
                </ul>
              </section>
            )}
            {!items.length && projectRange && (
              <p className="text-sm text-ink-muted">
                Chưa có sáng kiến, hạng mục lớn hoặc bản phát hành được đưa vào lộ trình.
              </p>
            )}
          </div>
        )}
      </Panel>
    </div>
  );
}
