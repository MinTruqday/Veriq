"use client";

import { useCallback, useEffect, useRef, useState } from "react";
import { ArrowLeft, Download, Eye, Plus, Printer, RefreshCw, Save, X } from "lucide-react";
import Image from "next/image";
import { useAuth } from "@/features/authentication/contexts/AuthContext";
import { authenticatedFetch, API_URL } from "@/shared/services/api-client";
import DocumentEditor from "../editor/DocumentEditor";
import ReportAssignmentsPanel from "./ReportAssignmentsPanel";
import ContentOriginBadge from "@/shared/components/common/ContentOriginBadge";
import { testingApi, testingRequest } from "../services/testing.service";
import { reportDateInput, reportDateTime } from "../lib/reportTime.mjs";
import { summaryLanguageOptions } from "../lib/summaryLanguage";
import { ErrorState, LoadingState, Panel, useActionDialog } from "./WorkspacePrimitives";
import SegmentedTabs from "@/shared/components/navigation/SegmentedTabs";
import { valueLabel } from "../lib/testing";

const labels = {
  DRAFT: "Bản nháp",
  IN_REVIEW: "Đang rà soát",
  APPROVED: "Đã duyệt",
  PUBLISHED: "Đã phát hành",
  ARCHIVED: "Lưu trữ",
  PERSONAL: "Cá nhân",
  TEAM: "Nhóm",
  PROJECT: "Dự án",
  PENDING: "Chờ gửi",
  RECEIVED: "Đã nhận",
  VIEWED: "Đã xem",
  ACKNOWLEDGED: "Đã xác nhận",
  FAILED: "Thất bại",
  READY: "Đã xuất",
  QUEUED: "Đang chờ",
  RUNNING: "Đang xử lý",
  SUPERSEDED: "Nguồn đã thay đổi",
  REVOKED: "Đã thu hồi",
};
const errors = {
  REPORT_REVISION_CONFLICT:
    "Nội dung đã được người khác thay đổi. Bản đang soạn vẫn được giữ; tải lại sau khi sao lưu nội dung của bạn.",
  REPORT_EXPORT_REQUIRED:
    "Hãy xuất thành công ít nhất một bản DOCX hoặc PDF của phiên bản đã duyệt trước khi phát hành.",
  REPORT_TIMES_NEW_ROMAN_MISSING: "Máy chủ chưa được cấu hình font Times New Roman để tạo PDF.",
  REPORT_PDF_CONVERTER_UNAVAILABLE: "Máy chủ chưa sẵn sàng chuyển đổi PDF.",
  REPORT_EDITOR_PERMISSION_INVALID: "Người soạn cần được cấp quyền viết báo cáo trong dự án.",
  REPORT_REVIEW_PERMISSION_INVALID: "Người duyệt cần được cấp quyền rà soát báo cáo trong dự án.",
  REPORT_MEMBER_NOT_ACTIVE: "Có người được chọn không còn là thành viên đang hoạt động.",
  PROJECT_REPORTING_DISABLED: "Dự án chưa bật báo cáo công việc.",
  REPORT_TRANSITION_INVALID: "Báo cáo đã đổi trạng thái. Hãy tải lại để tiếp tục.",
  REPORT_CHANGE_REASON_REQUIRED: "Hãy nhập lý do chỉnh sửa.",
  REPORT_ACCESS_DENIED: "Bạn không được truy cập báo cáo này.",
  REPORT_REVIEWER_REQUIRED: "Thao tác này dành cho người duyệt được phân công.",
  REPORT_REVIEWER_MUST_BE_INDEPENDENT:
    "Người duyệt phải khác người tạo, người viết và những người cùng soạn.",
  REPORT_SELF_REVIEW_FORBIDDEN:
    "Người tạo hoặc sửa nội dung không thể tự rà soát, duyệt hoặc yêu cầu chỉnh sửa bản này.",
  REPORT_IMAGE_UPLOAD_REQUIRED: "Ảnh phải được tải lên kho báo cáo trước khi lưu.",
};
const blank = { type: "doc", content: [{ type: "paragraph" }] };
const key = () => crypto.randomUUID();
const dayInput = () => reportDateInput();
function message(error) {
  return (
    errors[error?.code] ||
    error?.message ||
    "Không thể hoàn tất thao tác. Nội dung đang nhập được giữ lại."
  );
}
function normalizeSettings(value) {
  return {
    ...value,
    allowed_kinds: Array.isArray(value?.allowed_kinds) ? value.allowed_kinds : [],
  };
}

export default function WorkReportsPanel({ project }) {
  const { user } = useAuth();
  const { ask, dialog } = useActionDialog();
  const date = (value) =>
    value
      ? new Date(value).toLocaleString(user?.locale || project.locale || undefined, {
          day: "2-digit",
          month: "2-digit",
          year: "numeric",
          hour: "2-digit",
          minute: "2-digit",
        })
      : "—";
  const can = (permission) => project.current_permissions?.includes(permission);
  const root = `/du-an/${project._id}/bao-cao-cong-viec`;
  const [tab, setTab] = useState("mine");
  const [settings, setSettings] = useState(null);
  const [reports, setReports] = useState([]);
  const [reportPage, setReportPage] = useState(0);
  const [reportSearch, setReportSearch] = useState("");
  const [activeSearch, setActiveSearch] = useState("");
  const [reportStatus, setReportStatus] = useState("");
  const [templates, setTemplates] = useState([]);
  const [members, setMembers] = useState([]);
  const [schedules, setSchedules] = useState([]);
  const [scheduleHistory, setScheduleHistory] = useState(null);
  const [selected, setSelected] = useState(null);
  const [content, setContent] = useState(blank);
  const [dirty, setDirty] = useState(false);
  const [previewDoc, setPreviewDoc] = useState(null);
  const [printDocument, setPrintDocument] = useState(null);
  const [exports, setExports] = useState([]);
  const [comments, setComments] = useState([]);
  const [deliveries, setDeliveries] = useState([]);
  const [comment, setComment] = useState("");
  const [note, setNote] = useState("");
  const [error, setError] = useState("");
  const [notice, setNotice] = useState("");
  const [loading, setLoading] = useState(true);
  const [busy, setBusy] = useState(false);
  const [creating, setCreating] = useState(false);
  const [title, setTitle] = useState("");
  const [kind, setKind] = useState("PERSONAL");
  const [templateId, setTemplateId] = useState("");
  const [owner, setOwner] = useState("");
  const [reviewer, setReviewer] = useState("");
  const [recipientIds, setRecipientIds] = useState([]);
  const [recipientAccess, setRecipientAccess] = useState("VIEW");
  const [allowDownload, setAllowDownload] = useState(false);
  const [start, setStart] = useState(dayInput());
  const [end, setEnd] = useState(dayInput());
  const [language, setLanguage] = useState(user?.locale || project.locale || "");
  const [templateDoc, setTemplateDoc] = useState(blank);
  const [editingTemplate, setEditingTemplate] = useState(null);
  const [replyTo, setReplyTo] = useState(null);
  const [cadence, setCadence] = useState("DAY");
  const [firstRun, setFirstRun] = useState("");
  const [scheduleInterval, setScheduleInterval] = useState(1);
  const [dueHours, setDueHours] = useState(24);
  const [templatePreview, setTemplatePreview] = useState(null);
  const [acceptTemplateWarnings, setAcceptTemplateWarnings] = useState(false);
  const [aiDraft, setAiDraft] = useState(null);
  const [aiSections, setAiSections] = useState([]);
  const aiRequest = useRef(null);
  const [aiMode, setAiMode] = useState("DRAFT");
  const [dataField, setDataField] = useState("report.title");
  const [editorIds, setEditorIds] = useState([]);
  const [subjectIds, setSubjectIds] = useState([]);
  const [dueAt, setDueAt] = useState("");
  const saveInFlight = useRef(false);
  const editSequence = useRef(0);
  const sequence = useRef(0);
  const operationKey = useRef(key());
  const userId = user?._id || user?.id;
  const assignedAuthor =
    selected &&
    can("workreport.write") &&
    (selected.owner_id === userId || selected.editor_ids?.includes(userId));
  const editable = assignedAuthor && ["DRAFT", "APPROVED"].includes(selected.status);
  const canProvideChangeReason =
    editable ||
    (selected?.reviewer_id === userId && selected.status === "IN_REVIEW") ||
    (assignedAuthor && ["PUBLISHED", "ARCHIVED"].includes(selected.status));
  const mayComment = Boolean(selected?.current_access?.can_comment || editable);
  const memberId = (member) => member.user_id || member._id;
  const memberName = (id) => {
    const member = members.find((item) => memberId(item) === id);
    return (
      member?.user_label ||
      member?.display_name ||
      member?.name ||
      member?.email ||
      "Tài khoản không xác định"
    );
  };
  const load = useCallback(async () => {
    const generation = ++sequence.current;
    setLoading(true);
    try {
      const [config, items, models] = await Promise.all([
        testingRequest(`${root}/cau-hinh`),
        testingRequest(
          `${root}?inbox=${tab === "inbox"}&limit=50&offset=${reportPage * 50}&search=${encodeURIComponent(activeSearch)}${reportStatus ? `&status=${reportStatus}` : ""}`,
        ),
        testingRequest(`${root}/mau`),
      ]);
      if (generation !== sequence.current) return;
      setSettings(normalizeSettings(config));
      setReports(items);
      setTemplates(models);
      if (project.current_permissions?.includes("workreport.write")) {
        const [people, reportParticipants] = await Promise.all([
          testingApi.listMembers(project._id),
          testingApi.listEligibleReportParticipants(project._id),
        ]);
        const writerIds = new Set(reportParticipants.writer_ids || []);
        const reviewerIds = new Set(reportParticipants.reviewer_ids || []);
        const items = Array.isArray(people) ? people : people.items || [];
        if (generation === sequence.current)
          setMembers(
            items.map((item) => {
              const id = item.user_id || item._id;
              return {
                ...item,
                report_capabilities: [
                  ...(writerIds.has(id) ? ["workreport.write"] : []),
                  ...(reviewerIds.has(id) ? ["workreport.review"] : []),
                ],
              };
            }),
          );
      }
      if (project.current_permissions?.includes("workreport.manage")) {
        const rows = await testingRequest(`${root}/lich`);
        if (generation === sequence.current) setSchedules(rows);
      }
    } catch (reason) {
      if (generation === sequence.current) setError(message(reason));
    } finally {
      if (generation === sequence.current) setLoading(false);
    }
  }, [root, tab, project._id, project.current_permissions, reportPage, activeSearch, reportStatus]);
  useEffect(() => {
    void load();
    return () => {
      sequence.current += 1;
    };
  }, [load]);
  useEffect(() => {
    setSelected(null);
    setCreating(false);
    setDirty(false);
    setPrintDocument(null);
  }, [project._id]);
  useEffect(() => {
    if (!printDocument) return undefined;
    document.body.classList.add("report-print-mode");
    return () => document.body.classList.remove("report-print-mode");
  }, [printDocument]);
  useEffect(() => {
    const block = (event) => {
      if (dirty) {
        event.preventDefault();
        event.returnValue = "";
      }
    };
    window.addEventListener("beforeunload", block);
    return () => window.removeEventListener("beforeunload", block);
  }, [dirty]);

  const run = async (operation) => {
    setBusy(true);
    setError("");
    setNotice("");
    try {
      await operation();
    } catch (reason) {
      setError(message(reason));
    } finally {
      setBusy(false);
    }
  };
  const confirmLeave = async () =>
    !dirty ||
    Boolean(
      await ask({
        title: "Rời báo cáo chưa lưu?",
        description: "Nội dung chưa lưu sẽ không được giữ khi chuyển sang báo cáo khác.",
        confirmLabel: "Rời báo cáo",
      }),
    );
  const open = async (item) =>
    run(async () => {
      if (!(await confirmLeave())) return;
      const report = await testingRequest(`/bao-cao-cong-viec/${item._id}`);
      setSelected(report);
      setAiDraft(null);
      const mayEdit =
        can("workreport.write") &&
        ["DRAFT", "APPROVED"].includes(report.status) &&
        (report.owner_id === userId || report.editor_ids?.includes(userId));
      setPreviewDoc(
        mayEdit
          ? null
          : (await testingRequest(`/bao-cao-cong-viec/${report._id}/xem-truoc`)).content_doc,
      );
      setAiSections([]);
      setContent(report.content_doc);
      setDirty(false);
      setNote("");
      const [files, discussion] = await Promise.all([
        testingRequest(`/bao-cao-cong-viec/${item._id}/ban-xuat`),
        testingRequest(`/bao-cao-cong-viec/${item._id}/binh-luan`),
      ]);
      setExports(files);
      setComments(discussion);
      if (
        [report.owner_id, report.reviewer_id, ...(report.editor_ids || [])].includes(userId) ||
        can("workreport.manage")
      ) {
        setDeliveries(await testingRequest(`/bao-cao-cong-viec/${item._id}/nguoi-nhan`));
      } else {
        setDeliveries([]);
        if (["PUBLISHED", "ARCHIVED"].includes(report.status))
          await testingRequest(`/bao-cao-cong-viec/${item._id}/da-xem`, { method: "POST" });
      }
    });
  const save = useCallback(async () => {
    if (saveInFlight.current || !selected) return;
    saveInFlight.current = true;
    const reportId = selected._id;
    const editVersion = editSequence.current;
    try {
      const updated = await testingRequest(`/bao-cao-cong-viec/${reportId}`, {
        method: "PATCH",
        body: JSON.stringify({
          expected_revision: selected.revision,
          content_doc: content,
          reason: note,
        }),
      });
      setSelected((current) => (current?._id === reportId ? updated : current));
      if (editSequence.current === editVersion) setDirty(false);
    } finally {
      saveInFlight.current = false;
    }
  }, [selected, content, note]);
  useEffect(() => {
    if (!dirty || busy || selected?.status !== "DRAFT" || error) return undefined;
    const timeout = window.setTimeout(() => {
      void save().catch((reason) => setError(message(reason)));
    }, 1500);
    return () => window.clearTimeout(timeout);
  }, [dirty, busy, selected?.status, content, save, error]);
  const action = (value) =>
    run(async () => {
      if (dirty) {
        setError("Hãy lưu nội dung trước khi chuyển trạng thái.");
        return;
      }
      const updated = await testingRequest(`/bao-cao-cong-viec/${selected._id}/chuyen-trang-thai`, {
        method: "POST",
        body: JSON.stringify({
          action: value,
          expected_revision: selected.revision,
          note,
          idempotency_key: key(),
        }),
      });
      setSelected(updated);
      setContent(updated.content_doc);
      setNotice("Đã cập nhật báo cáo.");
      await load();
    });
  const uploadImages = async (files) => {
    const nodes = [];
    try {
      for (const file of files) {
        const body = new FormData();
        body.append("file", file);
        const asset = await testingRequest(`${root}/anh`, { method: "POST", body });
        nodes.push({
          type: "image",
          attrs: {
            asset_id: asset._id,
            src: `/api/kiem-thu/du-an/${project._id}/bao-cao-cong-viec/anh/${asset._id}`,
            alt: file.name,
            width_cm: 14,
          },
        });
      }
    } catch (reason) {
      setError(message(reason));
    }
    return nodes;
  };
  const submitCreate = (schedule = false) =>
    run(async () => {
      const startAt = reportDateTime(`${start}T00:00`, settings.timezone);
      const endDay = new Date(`${end}T00:00:00Z`);
      endDay.setUTCDate(endDay.getUTCDate() + 1);
      const endAt = reportDateTime(`${endDay.toISOString().slice(0, 10)}T00:00`, settings.timezone);
      const report = {
        title,
        kind,
        owner_id: owner || userId,
        editor_ids: editorIds,
        reviewer_id: reviewer,
        recipients: recipientIds.map((id) => ({
          user_id: id,
          access: recipientAccess,
          can_download: allowDownload,
          acknowledgment_required: true,
        })),
        period: {
          start_at: startAt,
          end_at: endAt,
          timezone: settings.timezone,
        },
        template_version_id: templateId,
        output_language: language,
        subject_ids: kind === "PERSONAL" ? [owner || userId] : subjectIds,
        due_at: dueAt ? reportDateTime(dueAt, settings.timezone) : null,
        idempotency_key: operationKey.current,
      };
      if (schedule) {
        await testingRequest(`${root}/lich`, {
          method: "POST",
          body: JSON.stringify({
            name: title,
            report,
            cadence,
            interval: Number(scheduleInterval),
            first_run_at: reportDateTime(firstRun, settings.timezone),
            due_hours_after: Number(dueHours),
            formats: ["docx", "pdf"],
            idempotency_key: operationKey.current,
          }),
        });
      } else {
        const created = await testingRequest(root, {
          method: "POST",
          body: JSON.stringify(report),
        });
        setSelected(created);
        setContent(created.content_doc);
        setDirty(false);
      }
      operationKey.current = key();
      setCreating(false);
      await load();
    });
  const exportFile = (format) =>
    run(async () => {
      const job = await testingRequest(`/bao-cao-cong-viec/${selected._id}/xuat`, {
        method: "POST",
        body: JSON.stringify({
          expected_revision: selected.revision,
          format,
          idempotency_key: key(),
        }),
      });
      setExports((current) => [job, ...current.filter((item) => item._id !== job._id)]);
      setNotice(
        job.status === "READY"
          ? "Bản xuất đã sẵn sàng."
          : "Đã yêu cầu xuất tệp. Bạn có thể làm việc khác và kiểm tra lại tại Bản xuất.",
      );
    });
  const download = (file) =>
    run(async () => {
      const response = await authenticatedFetch(
        `${API_URL}/kiem-thu/ban-xuat-bao-cao/${file._id}/tai-xuong`,
      );
      if (!response.ok) throw new Error("Không thể tải tệp. Kiểm tra quyền tải hoặc thử lại.");
      const url = URL.createObjectURL(await response.blob());
      const link = document.createElement("a");
      link.href = url;
      link.download = `${selected.title}.${file.format}`;
      link.click();
      setTimeout(() => URL.revokeObjectURL(url), 1000);
    });
  const openPrintPreview = () =>
    run(async () => {
      const result = await testingRequest(`/bao-cao-cong-viec/${selected._id}/xem-truoc`);
      if (result.revision !== selected.revision)
        throw new Error("Báo cáo đã thay đổi. Hãy tải lại trước khi in.");
      setPrintDocument(result.content_doc);
    });
  const tabs = [
    { id: "mine", label: "Báo cáo của tôi" },
    { id: "inbox", label: "Đã nhận" },
    ...(can("workreport.manage")
      ? [
          { id: "templates", label: "Mẫu báo cáo" },
          { id: "assignments", label: "Phân công" },
          { id: "schedules", label: "Lịch báo cáo" },
          { id: "settings", label: "Cấu hình" },
        ]
      : []),
  ];
  const choices = (list) =>
    list.map((item) => (
      <option key={memberId(item)} value={memberId(item)}>
        {memberName(memberId(item))}
      </option>
    ));
  const reportOwnerId = owner || userId;
  const eligibleReviewers = members.filter(
    (item) =>
      item.status === "ACTIVE" &&
      item.report_capabilities?.includes("workreport.review") &&
      ![userId, reportOwnerId, ...editorIds].includes(memberId(item)),
  );
  const availableKinds = ["PERSONAL", "TEAM", "PROJECT"].filter(
    (item) =>
      settings?.allowed_kinds?.includes(item) && (can("workreport.manage") || item === "PERSONAL"),
  );

  return (
    <div className="min-w-0 space-y-4">
      {dialog}
      {error && <ErrorState message={error} />}
      {notice && (
        <p role="status" className="text-sm text-ink-muted">
          {notice}
        </p>
      )}
      <SegmentedTabs
        label="Báo cáo công việc"
        value={tab}
        onChange={async (value) => {
          if (await confirmLeave()) {
            setTab(value);
            setReportPage(0);
            setSelected(null);
            setDirty(false);
            setCreating(false);
          }
        }}
        tabs={tabs}
      />
      {loading && !settings ? (
        <LoadingState />
      ) : (
        settings && (
          <>
            {tab === "assignments" && can("workreport.manage") && (
              <ReportAssignmentsPanel project={project} members={members} />
            )}
            {tab === "settings" && (
              <Panel title="Báo cáo trong dự án">
                <div className="space-y-4 p-4">
                  <label className="flex items-center gap-2">
                    <input
                      type="checkbox"
                      checked={settings.enabled}
                      onChange={(event) =>
                        setSettings({ ...settings, enabled: event.target.checked })
                      }
                    />
                    Bật báo cáo công việc
                  </label>
                  <div className="grid gap-4 md:grid-cols-2">
                    <label className="block text-sm">
                      Múi giờ của dự án
                      <input
                        className="apple-input mt-1"
                        value={settings.timezone}
                        onChange={(event) =>
                          setSettings({ ...settings, timezone: event.target.value })
                        }
                      />
                    </label>
                    <label className="block text-sm">
                      Nhắc trước hạn (giờ)
                      <input
                        className="apple-input mt-1"
                        type="number"
                        min="0"
                        max="720"
                        value={settings.reminder_hours_before ?? ""}
                        onChange={(event) =>
                          setSettings({
                            ...settings,
                            reminder_hours_before:
                              event.target.value === "" ? 0 : Number(event.target.value),
                          })
                        }
                      />
                    </label>
                  </div>
                  <fieldset>
                    <legend className="mb-2 text-sm font-medium">Loại báo cáo được phép</legend>
                    <div className="flex flex-wrap gap-x-6 gap-y-2">
                      {["PERSONAL", "TEAM", "PROJECT"].map((item) => (
                        <label key={item} className="flex items-center gap-2 text-sm">
                          <input
                            type="checkbox"
                            checked={settings.allowed_kinds.includes(item)}
                            onChange={(event) =>
                              setSettings({
                                ...settings,
                                allowed_kinds: event.target.checked
                                  ? [...settings.allowed_kinds, item]
                                  : settings.allowed_kinds.filter((value) => value !== item),
                              })
                            }
                          />
                          {labels[item]}
                        </label>
                      ))}
                    </div>
                  </fieldset>
                  <button
                    className="apple-button"
                    disabled={busy}
                    onClick={() =>
                      run(async () => {
                        setSettings(
                          normalizeSettings(
                            await testingRequest(`${root}/cau-hinh`, {
                              method: "PUT",
                              body: JSON.stringify({
                                expected_revision: settings.revision,
                                enabled: settings.enabled,
                                timezone: settings.timezone,
                                allowed_kinds: settings.allowed_kinds,
                                reminder_hours_before: settings.reminder_hours_before,
                              }),
                            }),
                          ),
                        );
                        setNotice("Đã lưu cấu hình báo cáo.");
                      })
                    }
                  >
                    Lưu cấu hình
                  </button>
                </div>
              </Panel>
            )}
            {tab === "templates" && (
              <Panel title="Mẫu báo cáo">
                <div className="space-y-4 p-4">
                  <ul className="divide-y divide-border">
                    {!templates.length && (
                      <li className="py-2 text-sm text-ink-muted">
                        Chưa có mẫu báo cáo. Nhập mẫu Word hoặc tạo mẫu mới bên dưới.
                      </li>
                    )}
                    {templates.map((item) => (
                      <li key={item._id} className="py-2">
                        {item.name}{" "}
                        <span className="text-sm text-ink-muted">· {labels[item.kind]}</span>
                        {!templates.some(
                          (other) =>
                            other.template_id === item.template_id && other.version > item.version,
                        ) && (
                          <button
                            className="secondary-button ml-3"
                            disabled={busy}
                            onClick={() => {
                              setEditingTemplate(item);
                              setTitle(item.name);
                              setKind(item.kind);
                              setTemplateDoc(item.content_doc);
                              setTemplatePreview(null);
                            }}
                          >
                            Sửa thành phiên bản mới
                          </button>
                        )}
                      </li>
                    ))}
                  </ul>
                  <label className="block text-sm">
                    Nhập mẫu Word
                    <input
                      className="apple-input mt-1 max-w-full"
                      type="file"
                      accept=".docx"
                      disabled={busy}
                      onChange={(event) => {
                        const file = event.target.files?.[0];
                        if (!file) return;
                        void run(async () => {
                          const form = new FormData();
                          form.append("file", file);
                          const preview = await testingRequest(`${root}/mau/xem-truoc`, {
                            method: "POST",
                            body: form,
                          });
                          setTemplatePreview(preview);
                          setTemplateDoc(preview.content_doc);
                          setAcceptTemplateWarnings(false);
                          if (!title) setTitle(file.name.replace(/\.docx$/i, ""));
                        });
                      }}
                    />
                  </label>
                  {templatePreview && (
                    <div className="space-y-2 text-sm">
                      <p>
                        Đã phân tích {templatePreview.filename}. Hãy đối chiếu nội dung trước khi
                        lưu mẫu.
                      </p>
                      {templatePreview.warnings.length > 0 && (
                        <>
                          <ul className="list-disc pl-5">
                            {templatePreview.warnings.map((warning) => (
                              <li key={warning}>
                                {{
                                  IMAGES_REQUIRE_REINSERTION:
                                    "Ảnh trong phần nội dung cần được chèn lại trước khi dùng mẫu.",
                                  TEXTBOX_LAYOUT_REQUIRES_REVIEW:
                                    "Bố cục hộp văn bản cần đối chiếu với tệp gốc.",
                                  MULTIPLE_SECTIONS_NORMALIZED_TO_A4:
                                    "Các section được chuẩn hóa về khổ A4.",
                                  EXTERNAL_REFERENCES_NOT_FETCHED:
                                    "Tài nguyên liên kết ngoài không được tự tải.",
                                  LIST_NUMBERING_REQUIRES_REVIEW:
                                    "Cần đối chiếu lại thứ tự và kiểu đánh số danh sách.",
                                }[warning] || "Có thành phần cần đối chiếu với bản gốc."}
                              </li>
                            ))}
                          </ul>
                          <label className="flex items-center gap-2">
                            <input
                              type="checkbox"
                              checked={acceptTemplateWarnings}
                              onChange={(event) => setAcceptTemplateWarnings(event.target.checked)}
                            />
                            Đã đối chiếu và chấp nhận các điều chỉnh của mẫu
                          </label>
                        </>
                      )}
                    </div>
                  )}
                  <label className="block text-sm">
                    Tên mẫu
                    <input
                      className="apple-input mt-1"
                      value={title}
                      onChange={(event) => setTitle(event.target.value)}
                    />
                  </label>
                  <select
                    aria-label="Loại mẫu"
                    className="apple-input"
                    value={kind}
                    onChange={(event) => setKind(event.target.value)}
                  >
                    {["PERSONAL", "TEAM", "PROJECT"].map((item) => (
                      <option key={item} value={item}>
                        {labels[item]}
                      </option>
                    ))}
                  </select>
                  <div className="flex flex-wrap gap-2">
                    <select
                      aria-label="Trường dữ liệu trong mẫu"
                      className="apple-input !w-auto"
                      value={dataField}
                      onChange={(event) => setDataField(event.target.value)}
                    >
                      {[
                        ["report.title", "Tên báo cáo"],
                        ["project.name", "Tên dự án"],
                        ["owner.name", "Người phụ trách"],
                        ["period.start", "Bắt đầu kỳ"],
                        ["period.end", "Kết thúc kỳ"],
                        ["snapshot.captured_at", "Thời điểm chốt số liệu"],
                        ["metrics.work_items_total", "Số công việc"],
                        [
                          "metrics.work_items_completed_at_capture",
                          "Công việc hoàn thành khi chốt",
                        ],
                        ["metrics.work_items_changed_in_period", "Công việc thay đổi trong kỳ"],
                      ].map(([value, label]) => (
                        <option key={value} value={value}>
                          {label}
                        </option>
                      ))}
                    </select>
                    <button
                      className="secondary-button"
                      onClick={() =>
                        setTemplateDoc((current) => ({
                          type: "doc",
                          content: [
                            ...(current.content || []),
                            {
                              type: "paragraph",
                              content: [{ type: "text", text: `{{${dataField}}}` }],
                            },
                          ],
                        }))
                      }
                    >
                      Thêm trường vào mẫu
                    </button>
                  </div>
                  <DocumentEditor
                    documentProfile="formal-report"
                    value={templateDoc}
                    onImageFiles={uploadImages}
                    onChange={setTemplateDoc}
                    label="Nội dung mẫu"
                  />
                  <button
                    className="apple-button"
                    disabled={
                      busy ||
                      !title.trim() ||
                      (templatePreview?.warnings.length > 0 && !acceptTemplateWarnings)
                    }
                    onClick={() =>
                      run(async () => {
                        await testingRequest(`${root}/mau`, {
                          method: "POST",
                          body: JSON.stringify({
                            name: title,
                            kind,
                            content_doc: templateDoc,
                            ...(editingTemplate
                              ? {
                                  template_id: editingTemplate.template_id,
                                  expected_revision: editingTemplate.revision,
                                }
                              : {}),
                            ...(templatePreview
                              ? {
                                  import_preview_id: templatePreview._id,
                                  accepted_warnings: acceptTemplateWarnings
                                    ? templatePreview.warnings
                                    : [],
                                }
                              : {}),
                          }),
                        });
                        setTitle("");
                        setTemplateDoc(blank);
                        setEditingTemplate(null);
                        setTemplatePreview(null);
                        setAcceptTemplateWarnings(false);
                        await load();
                      })
                    }
                  >
                    {editingTemplate ? "Lưu phiên bản mẫu mới" : "Lưu mẫu mới"}
                  </button>
                  {editingTemplate && (
                    <button
                      className="secondary-button ml-2"
                      onClick={() => {
                        setEditingTemplate(null);
                        setTemplateDoc(blank);
                        setTitle("");
                      }}
                    >
                      Hủy sửa mẫu
                    </button>
                  )}
                </div>
              </Panel>
            )}
            {tab === "schedules" && !creating && (
              <Panel title="Lịch báo cáo">
                <div className="p-4">
                  <button
                    className="apple-button mb-4"
                    disabled={!settings.enabled || !availableKinds.length || busy}
                    onClick={() => {
                      setCreating(true);
                      operationKey.current = key();
                    }}
                  >
                    Tạo lịch
                  </button>
                  <div className="overflow-x-auto">
                    <table className="w-full text-left text-sm">
                      <thead>
                        <tr>
                          <th className="p-3">Tên</th>
                          <th className="p-3">Chu kỳ</th>
                          <th className="p-3">Lần tiếp theo</th>
                          <th className="p-3">Trạng thái</th>
                          <th className="p-3">Thao tác</th>
                        </tr>
                      </thead>
                      <tbody>
                        {schedules.map((item) => (
                          <tr key={item._id} className="border-t border-border">
                            <td className="p-3">{item.name}</td>
                            <td className="p-3">
                              {item.cadence === "ONCE"
                                ? "Một lần"
                                : `${item.interval} ${{ HOUR: "giờ", DAY: "ngày", WEEK: "tuần", MONTH: "tháng", QUARTER: "quý", YEAR: "năm" }[item.cadence]}`}
                            </td>
                            <td className="p-3">{date(item.next_run_at)}</td>
                            <td className="p-3">
                              {item.last_error
                                ? "Cần xử lý"
                                : item.enabled
                                  ? "Đang bật"
                                  : "Tạm dừng"}
                              {item.last_error && (
                                <p className="mt-1 text-xs text-ink-muted">
                                  {errors[item.last_error] ||
                                    "Kiểm tra thành viên, mẫu và cấu hình trước khi bật lại."}
                                </p>
                              )}
                            </td>
                            <td className="p-3">
                              <button
                                className="secondary-button"
                                disabled={busy}
                                onClick={() =>
                                  run(async () => {
                                    await testingRequest(`/lich-bao-cao/${item._id}`, {
                                      method: "PATCH",
                                      body: JSON.stringify({
                                        expected_revision: item.revision,
                                        enabled: !item.enabled,
                                      }),
                                    });
                                    await load();
                                  })
                                }
                              >
                                {item.enabled ? "Tạm dừng" : "Bật lại"}
                              </button>
                              <button
                                className="icon-button ml-2 h-9 w-9"
                                aria-label={`Lịch sử ${item.name}`}
                                disabled={busy}
                                onClick={() =>
                                  run(async () =>
                                    setScheduleHistory({
                                      name: item.name,
                                      rows: await testingRequest(
                                        `/lich-bao-cao/${item._id}/luot-chay`,
                                      ),
                                    }),
                                  )
                                }
                              >
                                <Eye size={17} />
                              </button>
                            </td>
                          </tr>
                        ))}
                      </tbody>
                    </table>
                  </div>
                  {!schedules.length && (
                    <p className="text-sm text-ink-muted">Chưa có lịch báo cáo.</p>
                  )}
                  {scheduleHistory && (
                    <div className="mt-4 border-t border-border pt-4">
                      <div className="mb-3 flex items-center justify-between gap-3">
                        <h3 className="font-medium">Lịch sử: {scheduleHistory.name}</h3>
                        <button
                          className="secondary-button"
                          onClick={() => setScheduleHistory(null)}
                        >
                          Đóng
                        </button>
                      </div>
                      {scheduleHistory.rows.length ? (
                        <ul className="divide-y divide-border">
                          {scheduleHistory.rows.map((entry) => (
                            <li
                              key={entry._id}
                              className="flex flex-wrap items-center justify-between gap-3 py-3 text-sm"
                            >
                              <span>{date(entry.scheduled_at)}</span>
                              <span>
                                {entry.status === "DRAFT_CREATED"
                                  ? "Đã tạo bản nháp"
                                  : entry.status === "BLOCKED"
                                    ? "Cần xử lý"
                                    : "Đã ghi nhận"}
                              </span>
                              {entry.skipped_count > 0 && (
                                <span>Đã bỏ qua {entry.skipped_count} kỳ trước</span>
                              )}
                              {entry.report_id && (
                                <button
                                  className="secondary-button"
                                  onClick={() => {
                                    setTab("mine");
                                    setScheduleHistory(null);
                                    open({ _id: entry.report_id });
                                  }}
                                >
                                  Mở báo cáo
                                </button>
                              )}
                            </li>
                          ))}
                        </ul>
                      ) : (
                        <p className="text-sm text-ink-muted">
                          Lịch chưa đến thời điểm tạo báo cáo.
                        </p>
                      )}
                    </div>
                  )}
                </div>
              </Panel>
            )}
            {creating && (
              <Panel title={tab === "schedules" ? "Tạo lịch báo cáo" : "Tạo báo cáo"}>
                <p className="px-4 pt-4 text-sm text-ink-muted">
                  Thời gian theo múi giờ của dự án.
                </p>
                <div className="grid grid-cols-2 gap-4 p-4">
                  <label className="col-span-2 text-sm">
                    Tên báo cáo
                    <input
                      className="apple-input mt-1"
                      value={title}
                      onChange={(event) => setTitle(event.target.value)}
                    />
                  </label>
                  <label className="text-sm">
                    Loại
                    <select
                      className="apple-input mt-1"
                      value={kind}
                      onChange={(event) => {
                        setKind(event.target.value);
                        setTemplateId("");
                      }}
                    >
                      {availableKinds.map((item) => (
                        <option key={item} value={item}>
                          {labels[item]}
                        </option>
                      ))}
                    </select>
                  </label>
                  <label className="text-sm">
                    Mẫu
                    <select
                      className="apple-input mt-1"
                      value={templateId}
                      onChange={(event) => setTemplateId(event.target.value)}
                    >
                      <option value="">Chọn mẫu</option>
                      {templates
                        .filter((item) => item.kind === kind)
                        .map((item) => (
                          <option key={item._id} value={item._id}>
                            {item.name}
                          </option>
                        ))}
                    </select>
                  </label>
                  <label className="text-sm">
                    Từ ngày
                    <input
                      className="apple-input mt-1"
                      type="date"
                      value={start}
                      onChange={(event) => setStart(event.target.value)}
                    />
                  </label>
                  <label className="text-sm">
                    Đến hết ngày
                    <input
                      className="apple-input mt-1"
                      type="date"
                      value={end}
                      onChange={(event) => setEnd(event.target.value)}
                    />
                  </label>
                  {can("workreport.manage") && (
                    <label className="text-sm">
                      Người viết
                      <select
                        className="apple-input mt-1"
                        value={owner}
                        onChange={(event) => {
                          setOwner(event.target.value);
                          if (
                            [event.target.value || userId, userId, ...editorIds].includes(reviewer)
                          )
                            setReviewer("");
                        }}
                      >
                        <option value="">Bản thân</option>
                        {choices(
                          members.filter(
                            (item) =>
                              item.status === "ACTIVE" &&
                              item.report_capabilities?.includes("workreport.write"),
                          ),
                        )}
                      </select>
                    </label>
                  )}
                  <label className="text-sm">
                    Người duyệt
                    <select
                      className="apple-input mt-1"
                      value={reviewer}
                      onChange={(event) => setReviewer(event.target.value)}
                    >
                      <option value="">Chọn người duyệt</option>
                      {choices(eligibleReviewers)}
                    </select>
                    <span className="mt-1 block text-xs text-ink-muted">
                      Người duyệt phải khác người tạo, người viết và người cùng soạn.
                    </span>
                  </label>
                  <label className="text-sm">
                    Hạn nộp
                    <input
                      type="datetime-local"
                      className="apple-input mt-1"
                      value={dueAt}
                      onChange={(event) => setDueAt(event.target.value)}
                    />
                  </label>
                  {can("workreport.manage") && (
                    <fieldset className="col-span-2">
                      <legend className="mb-2 text-sm font-medium">Người cùng soạn</legend>
                      <div className="grid max-h-40 grid-cols-3 gap-2 overflow-y-auto">
                        {members
                          .filter(
                            (item) =>
                              item.status === "ACTIVE" &&
                              item.report_capabilities?.includes("workreport.write"),
                          )
                          .map((item) => (
                            <label key={memberId(item)} className="flex items-center gap-2 text-sm">
                              <input
                                type="checkbox"
                                checked={editorIds.includes(memberId(item))}
                                onChange={(event) => {
                                  const id = memberId(item);
                                  setEditorIds((current) =>
                                    event.target.checked
                                      ? [...current, id]
                                      : current.filter((value) => value !== id),
                                  );
                                  if (event.target.checked && reviewer === id) setReviewer("");
                                }}
                              />
                              {memberName(memberId(item))}
                            </label>
                          ))}
                        {!members.some(
                          (item) =>
                            item.status === "ACTIVE" &&
                            item.report_capabilities?.includes("workreport.write"),
                        ) && (
                          <p className="col-span-full text-sm text-ink-muted">
                            Không có thành viên đang hoạt động được cấp quyền viết báo cáo.
                          </p>
                        )}
                      </div>
                    </fieldset>
                  )}
                  {kind === "TEAM" && (
                    <fieldset className="col-span-2">
                      <legend className="mb-2 text-sm font-medium">Thành viên được tổng hợp</legend>
                      <div className="grid max-h-40 grid-cols-3 gap-2 overflow-y-auto">
                        {members.map((item) => (
                          <label key={memberId(item)} className="flex items-center gap-2 text-sm">
                            <input
                              type="checkbox"
                              checked={subjectIds.includes(memberId(item))}
                              onChange={(event) =>
                                setSubjectIds((current) =>
                                  event.target.checked
                                    ? [...current, memberId(item)]
                                    : current.filter((id) => id !== memberId(item)),
                                )
                              }
                            />
                            {memberName(memberId(item))}
                          </label>
                        ))}
                        {!members.length && (
                          <p className="col-span-full text-sm text-ink-muted">
                            Chưa có thành viên trong dự án để tổng hợp.
                          </p>
                        )}
                      </div>
                    </fieldset>
                  )}
                  <label className="text-sm">
                    Ngôn ngữ nội dung
                    <select
                      className="apple-input mt-1"
                      value={language}
                      onChange={(event) => setLanguage(event.target.value)}
                    >
                      <option value="">Chọn ngôn ngữ</option>
                      {summaryLanguageOptions(user?.locale || project.locale)
                        .filter((item) => item.value !== "auto")
                        .map((item) => (
                          <option key={item.value} value={item.value}>
                            {item.label}
                          </option>
                        ))}
                    </select>
                  </label>
                  <fieldset className="col-span-2">
                    <legend className="mb-2 text-sm font-medium">Người nhận</legend>
                    <div className="grid max-h-48 grid-cols-3 gap-2 overflow-y-auto">
                      {members.map((item) => (
                        <label key={memberId(item)} className="flex items-center gap-2 text-sm">
                          <input
                            type="checkbox"
                            checked={recipientIds.includes(memberId(item))}
                            onChange={(event) =>
                              setRecipientIds((current) =>
                                event.target.checked
                                  ? [...current, memberId(item)]
                                  : current.filter((id) => id !== memberId(item)),
                              )
                            }
                          />
                          {memberName(memberId(item))}
                        </label>
                      ))}
                      {!members.length && (
                        <p className="col-span-full text-sm text-ink-muted">
                          Chưa có thành viên trong dự án để nhận báo cáo.
                        </p>
                      )}
                    </div>
                  </fieldset>
                  <label className="text-sm">
                    Quyền người nhận
                    <select
                      className="apple-input mt-1"
                      value={recipientAccess}
                      onChange={(event) => setRecipientAccess(event.target.value)}
                    >
                      <option value="VIEW">Chỉ xem</option>
                      <option value="COMMENT">Xem và nhận xét</option>
                    </select>
                  </label>
                  <label className="flex items-center gap-2 text-sm">
                    <input
                      type="checkbox"
                      checked={allowDownload}
                      onChange={(event) => setAllowDownload(event.target.checked)}
                    />
                    Cho tải tệp
                  </label>
                  {tab === "schedules" && (
                    <>
                      <label className="text-sm">
                        Chu kỳ
                        <select
                          className="apple-input mt-1"
                          value={cadence}
                          onChange={(event) => setCadence(event.target.value)}
                        >
                          {[
                            ["ONCE", "Một lần"],
                            ["HOUR", "Hằng giờ"],
                            ["DAY", "Hằng ngày"],
                            ["WEEK", "Hằng tuần"],
                            ["MONTH", "Hằng tháng"],
                            ["QUARTER", "Hằng quý"],
                            ["YEAR", "Hằng năm"],
                          ].map(([id, text]) => (
                            <option key={id} value={id}>
                              {text}
                            </option>
                          ))}
                        </select>
                      </label>
                      <label className="text-sm">
                        Số chu kỳ giữa hai lần tạo
                        <input
                          className="apple-input mt-1"
                          type="number"
                          min="1"
                          max="365"
                          value={scheduleInterval}
                          onChange={(event) => setScheduleInterval(event.target.value)}
                        />
                      </label>
                      <label className="text-sm">
                        Hạn nộp sau khi tạo (giờ)
                        <input
                          className="apple-input mt-1"
                          type="number"
                          min="1"
                          max="8760"
                          value={dueHours}
                          onChange={(event) => setDueHours(event.target.value)}
                        />
                      </label>
                      <label className="text-sm">
                        Lần tạo đầu tiên
                        <input
                          className="apple-input mt-1"
                          type="datetime-local"
                          value={firstRun}
                          onChange={(event) => setFirstRun(event.target.value)}
                        />
                      </label>
                    </>
                  )}
                  <div className="col-span-2 flex gap-2">
                    <button
                      className="apple-button"
                      disabled={
                        busy ||
                        !title.trim() ||
                        !templateId ||
                        !reviewer ||
                        !language.trim() ||
                        (tab === "schedules" && !firstRun)
                      }
                      onClick={() => submitCreate(tab === "schedules")}
                    >
                      {busy ? "Đang lưu…" : tab === "schedules" ? "Tạo lịch" : "Tạo bản nháp"}
                    </button>
                    <button
                      className="secondary-button"
                      disabled={busy}
                      onClick={() => setCreating(false)}
                    >
                      Hủy
                    </button>
                  </div>
                </div>
              </Panel>
            )}
            {["mine", "inbox"].includes(tab) && !selected && !creating && (
              <Panel title={tab === "inbox" ? "Báo cáo đã nhận" : "Báo cáo công việc"}>
                <div className="flex justify-between gap-3 p-4">
                  {can("workreport.write") && tab === "mine" && (
                    <button
                      className="apple-button inline-flex items-center gap-2"
                      disabled={!settings.enabled || !availableKinds.length || busy}
                      onClick={() => {
                        if (!availableKinds.includes(kind))
                          setKind(availableKinds[0] || "PERSONAL");
                        setCreating(true);
                        operationKey.current = key();
                      }}
                    >
                      <Plus size={16} />
                      Tạo báo cáo
                    </button>
                  )}
                  <button
                    className="icon-button ml-auto inline-flex h-10 w-10 shrink-0 items-center justify-center"
                    aria-label="Tải lại báo cáo"
                    disabled={busy}
                    onClick={load}
                  >
                    <RefreshCw size={17} />
                  </button>
                </div>
                {!settings.enabled && (
                  <p className="px-4 pb-4 text-sm text-ink-muted">
                    Dự án chưa bật báo cáo công việc. Các báo cáo cũ vẫn được lưu.
                  </p>
                )}
                {settings.enabled &&
                  !availableKinds.length &&
                  !reports.length &&
                  tab === "mine" && (
                    <p className="px-4 pb-4 text-sm text-ink-muted">
                      {settings.allowed_kinds.length
                        ? "Bạn chưa được cấp quyền tạo các loại báo cáo đang bật."
                        : "Dự án chưa bật loại báo cáo nào."}
                    </p>
                  )}
                <form
                  className="flex flex-wrap items-center gap-3 border-t border-border p-4"
                  onSubmit={(event) => {
                    event.preventDefault();
                    setReportPage(0);
                    setActiveSearch(reportSearch);
                  }}
                >
                  <input
                    aria-label="Tìm báo cáo"
                    placeholder="Tìm tên báo cáo"
                    className="apple-input !w-auto min-w-64 flex-1"
                    value={reportSearch}
                    onChange={(event) => setReportSearch(event.target.value)}
                  />
                  <select
                    aria-label="Trạng thái báo cáo"
                    className="apple-input !w-auto"
                    value={reportStatus}
                    onChange={(event) => {
                      setReportPage(0);
                      setReportStatus(event.target.value);
                    }}
                  >
                    <option value="">Tất cả trạng thái</option>
                    {["DRAFT", "IN_REVIEW", "APPROVED", "PUBLISHED", "ARCHIVED"].map((value) => (
                      <option key={value} value={value}>
                        {labels[value]}
                      </option>
                    ))}
                  </select>
                  <button className="secondary-button" type="submit" disabled={busy}>
                    Tìm
                  </button>
                </form>
                <div className="overflow-x-auto">
                  <table className="w-full text-left text-sm">
                    <thead>
                      <tr className="border-y border-border">
                        <th className="px-4 py-3">Báo cáo</th>
                        <th className="px-4 py-3">Kỳ báo cáo</th>
                        <th className="px-4 py-3">Phụ trách</th>
                        <th className="px-4 py-3">Trạng thái</th>
                        <th className="px-4 py-3">Cập nhật</th>
                        <th className="px-4 py-3">Thao tác</th>
                      </tr>
                    </thead>
                    <tbody>
                      {reports.map((item) => (
                        <tr key={item._id} className="border-b border-border">
                          <td className="max-w-80 px-4 py-3">
                            <button
                              className="text-left font-medium text-brand"
                              onClick={() => open(item)}
                            >
                              {item.title}
                            </button>
                            <p className="mt-1 text-xs text-ink-muted">{labels[item.kind]}</p>
                          </td>
                          <td className="px-4 py-3">
                            {date(item.period.start_at)}
                            <br />
                            {date(item.period.end_at)}
                          </td>
                          <td className="px-4 py-3">
                            {item.owner_label || memberName(item.owner_id)}
                          </td>
                          <td className="px-4 py-3">{labels[item.status]}</td>
                          <td className="px-4 py-3">{date(item.updated_at)}</td>
                          <td className="px-4 py-3">
                            <button
                              className="icon-button h-9 w-9"
                              aria-label={`Mở ${item.title}`}
                              disabled={busy}
                              onClick={() => open(item)}
                            >
                              <Eye size={17} />
                            </button>
                          </td>
                        </tr>
                      ))}
                    </tbody>
                  </table>
                </div>
                {!reports.length && (
                  <p className="p-4 text-sm text-ink-muted">Chưa có báo cáo trong danh sách này.</p>
                )}
                {(reportPage > 0 || reports.length === 50) && (
                  <div className="flex items-center justify-end gap-3 border-t border-border p-4">
                    <button
                      className="secondary-button"
                      disabled={loading || reportPage === 0}
                      onClick={() => setReportPage((value) => value - 1)}
                    >
                      Trước
                    </button>
                    <span className="text-sm">Trang {reportPage + 1}</span>
                    <button
                      className="secondary-button"
                      disabled={loading || reports.length < 50}
                      onClick={() => setReportPage((value) => value + 1)}
                    >
                      Sau
                    </button>
                  </div>
                )}
              </Panel>
            )}
            {selected && (
              <>
                <div className="flex flex-wrap items-center justify-between gap-3">
                  <button
                    className="secondary-button inline-flex items-center gap-2"
                    onClick={async () => {
                      if (await confirmLeave()) {
                        setSelected(null);
                        setDirty(false);
                      }
                    }}
                  >
                    <ArrowLeft size={16} />
                    Danh sách
                  </button>
                  <div className="flex flex-wrap items-center justify-end gap-3">
                    <div className="text-sm">
                      {labels[selected.status]} · {dirty ? "Chưa lưu" : "Đã lưu"}
                    </div>
                    <button
                      type="button"
                      className="secondary-button inline-flex items-center gap-2"
                      disabled={busy}
                      onClick={openPrintPreview}
                    >
                      <Printer size={16} aria-hidden="true" />
                      In báo cáo
                    </button>
                  </div>
                </div>
                <Panel title={selected.title}>
                  <div className="space-y-4 p-5">
                    <div className="space-y-4 border-b border-border pb-4">
                      <dl className="grid grid-cols-2 gap-x-8 gap-y-4 text-sm md:grid-cols-3 xl:grid-cols-5">
                        <div className="min-w-0">
                          <dt className="text-ink-muted">Loại báo cáo</dt>
                          <dd className="mt-1 font-medium">{labels[selected.kind] || "Báo cáo"}</dd>
                        </div>
                        <div className="min-w-0">
                          <dt className="text-ink-muted">Kỳ báo cáo</dt>
                          <dd className="mt-1 font-medium">
                            {date(selected.period?.start_at)} – {date(selected.period?.end_at)}
                          </dd>
                        </div>
                        <div className="min-w-0">
                          <dt className="text-ink-muted">Người thực hiện</dt>
                          <dd
                            className="mt-1 truncate font-medium"
                            title={memberName(selected.owner_id)}
                          >
                            {selected.owner_name || memberName(selected.owner_id)}
                          </dd>
                        </div>
                        <div className="min-w-0">
                          <dt className="text-ink-muted">Người xác nhận</dt>
                          <dd
                            className="mt-1 truncate font-medium"
                            title={selected.reviewer_name || memberName(selected.reviewer_id)}
                          >
                            {selected.reviewer_id
                              ? selected.reviewer_name || memberName(selected.reviewer_id)
                              : "Chưa phân công"}
                          </dd>
                        </div>
                        <div className="min-w-0">
                          <dt className="text-ink-muted">Hạn báo cáo</dt>
                          <dd className="mt-1 font-medium">{date(selected.due_at)}</dd>
                        </div>
                      </dl>
                    </div>
                    <div className="space-y-4">
                      {editable && (
                        <div className="flex justify-end">
                          <button
                            className="secondary-button"
                            disabled={busy || dirty}
                            onClick={() =>
                              run(async () => {
                                if (previewDoc) {
                                  setPreviewDoc(null);
                                  return;
                                }
                                const result = await testingRequest(
                                  `/bao-cao-cong-viec/${selected._id}/xem-truoc`,
                                );
                                if (result.revision !== selected.revision)
                                  throw new Error(
                                    "Báo cáo đã thay đổi. Hãy tải lại trước khi xem.",
                                  );
                                setPreviewDoc(result.content_doc);
                              })
                            }
                          >
                            {previewDoc ? "Trở lại nội dung soạn" : "Xem trước nội dung đã điền"}
                          </button>
                        </div>
                      )}
                      <DocumentEditor
                        documentProfile="formal-report"
                        key={`${selected._id}-${Boolean(previewDoc)}`}
                        value={previewDoc || content}
                        ignoreUnfocusedUpdates
                        onImageFiles={uploadImages}
                        onChange={(value) => {
                          setContent(value);
                          editSequence.current += 1;
                          setDirty(true);
                        }}
                        label="Nội dung báo cáo"
                        readOnly={!editable || Boolean(previewDoc)}
                        minHeight="min-h-72"
                      />
                      {can("workreport.ai") &&
                        [
                          selected.owner_id,
                          selected.reviewer_id,
                          ...(selected.editor_ids || []),
                        ].includes(userId) && (
                          <div className="space-y-3 rounded-control border border-border p-3">
                            <ContentOriginBadge
                              origin="ai_suggested"
                              aiLabel="Trợ lý soạn báo cáo"
                            />
                            <div className="flex flex-wrap gap-2">
                              <select
                                aria-label="Tác vụ AI cho báo cáo"
                                className="apple-input !w-auto"
                                value={aiMode}
                                onChange={(event) => setAiMode(event.target.value)}
                              >
                                <option value="DRAFT">Đề xuất nội dung</option>
                                <option value="REVIEW">Rà soát báo cáo</option>
                                <option value="SUMMARY">Tóm tắt điều hành</option>
                                <option value="TRANSLATE">Dịch nội dung</option>
                              </select>
                              <select
                                aria-label="Ngôn ngữ đầu ra AI"
                                className="apple-input !w-auto"
                                value={language}
                                onChange={(event) => setLanguage(event.target.value)}
                              >
                                <option value="">Chọn ngôn ngữ</option>
                                {summaryLanguageOptions(user?.locale || project.locale)
                                  .filter((item) => item.value !== "auto")
                                  .map((item) => (
                                    <option key={item.value} value={item.value}>
                                      {item.label}
                                    </option>
                                  ))}
                              </select>
                              <button
                                className="secondary-button"
                                disabled={busy || dirty || !language}
                                onClick={() =>
                                  run(async () => {
                                    const signature = JSON.stringify([
                                      selected._id,
                                      selected.revision,
                                      aiMode,
                                      note,
                                      language,
                                    ]);
                                    if (aiRequest.current?.signature !== signature)
                                      aiRequest.current = { signature, id: key() };
                                    setAiSections([]);
                                    setAiDraft(
                                      await testingRequest(
                                        `/bao-cao-cong-viec/${selected._id}/ai/de-xuat`,
                                        {
                                          method: "POST",
                                          body: JSON.stringify({
                                            expected_revision: selected.revision,
                                            mode: aiMode,
                                            instruction: note,
                                            output_language: language,
                                            idempotency_key: aiRequest.current.id,
                                          }),
                                        },
                                      ),
                                    );
                                  })
                                }
                              >
                                Chạy AI
                              </button>
                            </div>
                            {aiDraft && (
                              <div className="space-y-3">
                                {aiDraft.result?.status !== "SUCCESS" ? (
                                  <div className="space-y-2">
                                    <p className="text-sm text-ink-muted">
                                      {aiDraft.status === "RUNNING"
                                        ? "AI đang xử lý yêu cầu này."
                                        : "AI chưa tạo được đề xuất có căn cứ. Bạn có thể tiếp tục soạn báo cáo."}
                                    </p>
                                    {aiDraft.status === "RUNNING" ? (
                                      <button
                                        className="secondary-button"
                                        disabled={busy}
                                        onClick={() =>
                                          run(async () =>
                                            setAiDraft(
                                              await testingRequest(
                                                `/bao-cao-cong-viec/${selected._id}/ai/de-xuat/${aiDraft._id}`,
                                              ),
                                            ),
                                          )
                                        }
                                      >
                                        Kiểm tra kết quả AI
                                      </button>
                                    ) : (
                                      <button
                                        className="secondary-button"
                                        onClick={() => {
                                          aiRequest.current = null;
                                          setAiDraft(null);
                                        }}
                                      >
                                        Chuẩn bị thử lại
                                      </button>
                                    )}
                                  </div>
                                ) : (
                                  <>
                                    {aiDraft.result.suggestions?.[0]?.sections?.map(
                                      (section, index) => (
                                        <div key={index} className="space-y-2">
                                          <h4 className="font-medium">{section.title}</h4>
                                          <p className="whitespace-pre-wrap text-sm">
                                            {section.text}
                                          </p>
                                          {editable && aiDraft.mode !== "REVIEW" && (
                                            <label className="flex items-center gap-2 text-sm">
                                              <input
                                                type="checkbox"
                                                checked={aiSections.includes(index)}
                                                onChange={(event) =>
                                                  setAiSections((current) =>
                                                    event.target.checked
                                                      ? [...current, index]
                                                      : current.filter((item) => item !== index),
                                                  )
                                                }
                                              />
                                              Chọn mục này
                                            </label>
                                          )}
                                        </div>
                                      ),
                                    )}
                                    {editable && aiDraft.mode !== "REVIEW" && (
                                      <button
                                        className="secondary-button"
                                        disabled={
                                          busy ||
                                          dirty ||
                                          !aiSections.length ||
                                          aiDraft.source_revision !== selected.revision
                                        }
                                        onClick={() =>
                                          run(async () => {
                                            const updated = await testingRequest(
                                              `/bao-cao-cong-viec/${selected._id}/ai/ap-dung`,
                                              {
                                                method: "POST",
                                                body: JSON.stringify({
                                                  expected_revision: selected.revision,
                                                  proposal_id: aiDraft._id,
                                                  section_indices: aiSections,
                                                  idempotency_key: `apply-${aiDraft._id}-${[...aiSections].sort((a, b) => a - b).join("-")}`,
                                                }),
                                              },
                                            );
                                            setSelected(updated);
                                            setContent(updated.content_doc);
                                            setDirty(false);
                                            setAiSections([]);
                                            setNotice("Đã thêm các mục đã chọn vào bản nháp.");
                                          })
                                        }
                                      >
                                        Thêm các mục đã chọn
                                      </button>
                                    )}
                                    {aiDraft.result.suggestions?.[0]?.missing_information?.map(
                                      (item, index) => (
                                        <p className="text-sm" key={`missing-${index}`}>
                                          {item}
                                        </p>
                                      ),
                                    )}
                                    {aiDraft.result.suggestions?.[0]?.inconsistencies?.map(
                                      (item, index) => (
                                        <p className="text-sm" key={`issue-${index}`}>
                                          {item}
                                        </p>
                                      ),
                                    )}
                                  </>
                                )}
                              </div>
                            )}
                          </div>
                        )}
                      {canProvideChangeReason && (
                        <label className="block text-sm">
                          Ghi chú hoặc lý do thay đổi
                          <textarea
                            className="apple-input mt-1"
                            value={note}
                            onChange={(event) => setNote(event.target.value)}
                          />
                        </label>
                      )}
                      <div className="flex flex-wrap items-center gap-2">
                        {editable && (
                          <button
                            className="apple-button inline-flex items-center gap-2"
                            disabled={busy || !dirty}
                            onClick={() => run(save)}
                          >
                            <Save size={16} />
                            Lưu bản nháp
                          </button>
                        )}
                        {selected.status === "DRAFT" && editable && (
                          <button
                            className="secondary-button"
                            disabled={busy || dirty}
                            onClick={() => action("SUBMIT")}
                          >
                            Gửi rà soát
                          </button>
                        )}
                        {selected.reviewer_id === userId && selected.status === "IN_REVIEW" && (
                          <>
                            <button
                              className="apple-button"
                              disabled={busy}
                              onClick={() => action("APPROVE")}
                            >
                              Duyệt
                            </button>
                            <button
                              className="secondary-button"
                              disabled={busy || !note.trim()}
                              onClick={() => action("REQUEST_CHANGES")}
                            >
                              Yêu cầu chỉnh sửa
                            </button>
                          </>
                        )}
                        {selected.reviewer_id === userId && selected.status === "APPROVED" && (
                          <button
                            className="apple-button"
                            disabled={busy || dirty}
                            onClick={() => action("PUBLISH")}
                          >
                            Phát hành và gửi
                          </button>
                        )}
                        {["PUBLISHED", "ARCHIVED"].includes(selected.status) && assignedAuthor && (
                          <button
                            className="secondary-button"
                            disabled={busy || !note.trim()}
                            onClick={() => action("NEW_VERSION")}
                          >
                            Tạo phiên bản sửa
                          </button>
                        )}
                        {[
                          selected.owner_id,
                          selected.reviewer_id,
                          ...(selected.editor_ids || []),
                        ].includes(userId) &&
                          ["docx", "pdf"].map((format) => (
                            <button
                              key={format}
                              className="secondary-button"
                              disabled={busy || dirty}
                              onClick={() => exportFile(format)}
                            >
                              Xuất {format.toUpperCase()}
                            </button>
                          ))}
                      </div>
                    </div>
                  </div>
                </Panel>
                <details className="rounded-panel border border-border bg-surface p-4">
                  <summary className="cursor-pointer font-medium">Số liệu và nguồn báo cáo</summary>
                  {editable && selected.status === "DRAFT" && (
                    <button
                      className="secondary-button mt-3"
                      disabled={busy || dirty}
                      onClick={() =>
                        run(async () => {
                          const updated = await testingRequest(
                            `/bao-cao-cong-viec/${selected._id}`,
                            {
                              method: "PATCH",
                              body: JSON.stringify({
                                expected_revision: selected.revision,
                                refresh_snapshot: true,
                                reason: "Cập nhật số liệu theo yêu cầu người soạn",
                              }),
                            },
                          );
                          setSelected(updated);
                          setPreviewDoc(null);
                          setAiDraft(null);
                          setNotice("Đã chốt lại số liệu từ dữ liệu hiện tại.");
                        })
                      }
                    >
                      Cập nhật số liệu
                    </button>
                  )}
                  <p className="mt-3 text-sm text-ink-muted">
                    Dữ liệu chốt lúc {date(selected.snapshot.captured_at)}. Số giờ làm không được
                    suy ra từ lần cập nhật công việc.
                  </p>
                  <div className="mt-3 grid grid-cols-3 gap-4 text-sm">
                    <p>
                      Công việc: <strong>{selected.snapshot.metrics.work_items_total}</strong>
                    </p>
                    <p>
                      Đã hoàn thành khi chốt:{" "}
                      <strong>{selected.snapshot.metrics.work_items_completed_at_capture}</strong>
                    </p>
                    <p>
                      Thay đổi trong kỳ:{" "}
                      <strong>{selected.snapshot.metrics.work_items_changed_in_period}</strong>
                    </p>
                  </div>
                  <ul className="mt-3 divide-y divide-border">
                    {selected.snapshot.work_items.map((item) => (
                      <li key={item._id} className="py-2 text-sm">
                        {item.title} · {valueLabel(item.status)}
                      </li>
                    ))}
                  </ul>
                </details>
                <section
                  aria-labelledby="report-exports-heading"
                  className="space-y-3 rounded-xl border border-border bg-white p-4 sm:p-5"
                >
                  <div className="flex flex-wrap items-center justify-between gap-3">
                    <h3 className="font-semibold" id="report-exports-heading">
                      Tệp báo cáo
                    </h3>
                    <button
                      className="secondary-button"
                      disabled={busy}
                      onClick={() =>
                        run(async () =>
                          setExports(
                            await testingRequest(`/bao-cao-cong-viec/${selected._id}/ban-xuat`),
                          ),
                        )
                      }
                    >
                      Cập nhật trạng thái tệp
                    </button>
                  </div>
                  <div className="divide-y divide-border">
                    {exports.map((item) => (
                      <div
                        key={item._id}
                        className="flex items-center justify-between gap-3 text-sm"
                      >
                        <span>
                          {item.format.toUpperCase()} ·{" "}
                          {labels[item.status] || valueLabel(item.status)}
                          {item.error_code &&
                            ` · ${errors[item.error_code] || "Xuất tệp thất bại"}`}
                        </span>
                        {item.status === "FAILED" && (
                          <button
                            className="secondary-button"
                            disabled={busy}
                            onClick={() =>
                              run(async () => {
                                await testingRequest(`/ban-xuat-bao-cao/${item._id}/thu-lai`, {
                                  method: "POST",
                                  body: JSON.stringify({
                                    expected_generation: item.dispatch_generation || 0,
                                  }),
                                });
                                setExports(
                                  await testingRequest(
                                    `/bao-cao-cong-viec/${selected._id}/ban-xuat`,
                                  ),
                                );
                              })
                            }
                          >
                            Thử lại
                          </button>
                        )}
                        {item.status === "READY" &&
                          (selected.current_access?.can_download ||
                            (can("workreport.write") &&
                              [
                                selected.owner_id,
                                selected.reviewer_id,
                                ...(selected.editor_ids || []),
                              ].includes(userId))) && (
                            <button
                              className="icon-button h-9 w-9"
                              aria-label={`Tải ${item.format}`}
                              disabled={busy}
                              onClick={() => download(item)}
                            >
                              <Download size={17} />
                            </button>
                          )}
                      </div>
                    ))}
                    {!exports.length && (
                      <p className="py-2 text-sm text-ink-muted">
                        Chưa có tệp xuất cho phiên bản này.
                      </p>
                    )}
                  </div>
                </section>
                {deliveries.length > 0 && (
                  <section
                    aria-labelledby="report-recipients-heading"
                    className="space-y-3 rounded-xl border border-border bg-white p-4 sm:p-5"
                  >
                    <h3 className="font-semibold" id="report-recipients-heading">
                      Người nhận
                    </h3>
                    <div className="divide-y divide-border">
                      {deliveries.map((item) => (
                        <div
                          key={item._id}
                          className="flex flex-wrap items-center justify-between gap-3 py-3 text-sm"
                        >
                          <span>{item.user_label || memberName(item.user_id)}</span>
                          <span>{labels[item.status] || valueLabel(item.status)}</span>
                          <span>{date(item.first_viewed_at || item.received_at)}</span>
                          {(selected.owner_id === userId || can("workreport.manage")) && (
                            <div className="flex flex-wrap items-center gap-3">
                              <select
                                aria-label={`Quyền của ${memberName(item.user_id)}`}
                                className="apple-input !w-auto"
                                disabled={busy || Boolean(item.revoked_at)}
                                value={item.access}
                                onChange={(event) =>
                                  run(async () => {
                                    await testingRequest(
                                      `/bao-cao-cong-viec/${selected._id}/nguoi-nhan`,
                                      {
                                        method: "PATCH",
                                        body: JSON.stringify({
                                          user_id: item.user_id,
                                          expected_revision: item.revision,
                                          access: event.target.value,
                                          can_download: item.can_download,
                                          acknowledgment_required: item.acknowledgment_required,
                                        }),
                                      },
                                    );
                                    setDeliveries(
                                      await testingRequest(
                                        `/bao-cao-cong-viec/${selected._id}/nguoi-nhan`,
                                      ),
                                    );
                                  })
                                }
                              >
                                <option value="VIEW">Chỉ xem</option>
                                <option value="COMMENT">Xem và nhận xét</option>
                              </select>
                              <label className="flex items-center gap-2">
                                <input
                                  type="checkbox"
                                  checked={item.can_download}
                                  disabled={busy || Boolean(item.revoked_at)}
                                  onChange={(event) =>
                                    run(async () => {
                                      await testingRequest(
                                        `/bao-cao-cong-viec/${selected._id}/nguoi-nhan`,
                                        {
                                          method: "PATCH",
                                          body: JSON.stringify({
                                            user_id: item.user_id,
                                            expected_revision: item.revision,
                                            access: item.access,
                                            can_download: event.target.checked,
                                            acknowledgment_required: item.acknowledgment_required,
                                          }),
                                        },
                                      );
                                      setDeliveries(
                                        await testingRequest(
                                          `/bao-cao-cong-viec/${selected._id}/nguoi-nhan`,
                                        ),
                                      );
                                    })
                                  }
                                />
                                Cho tải tệp
                              </label>
                              <button
                                className="secondary-button"
                                disabled={busy}
                                onClick={() =>
                                  run(async () => {
                                    await testingRequest(
                                      `/bao-cao-cong-viec/${selected._id}/nguoi-nhan`,
                                      {
                                        method: "PATCH",
                                        body: JSON.stringify({
                                          user_id: item.user_id,
                                          expected_revision: item.revision,
                                          access: item.access,
                                          can_download: item.can_download,
                                          acknowledgment_required: item.acknowledgment_required,
                                          revoked: !item.revoked_at,
                                        }),
                                      },
                                    );
                                    setDeliveries(
                                      await testingRequest(
                                        `/bao-cao-cong-viec/${selected._id}/nguoi-nhan`,
                                      ),
                                    );
                                  })
                                }
                              >
                                {item.revoked_at ? "Cấp lại quyền" : "Thu hồi"}
                              </button>
                            </div>
                          )}
                        </div>
                      ))}
                    </div>
                  </section>
                )}
                {(comments.length > 0 || mayComment) && (
                  <section
                    aria-labelledby="report-comments-heading"
                    className="space-y-4 rounded-xl border border-border bg-white p-4 sm:p-5"
                  >
                    <h3 className="font-semibold" id="report-comments-heading">
                      Trao đổi
                    </h3>
                    <div className="space-y-4">
                      {comments.map((item) => (
                        <div key={item._id} className="border-b border-border pb-3">
                          <p className="text-sm font-medium">
                            {item.author_label || memberName(item.created_by)}{" "}
                            <span className="font-normal text-ink-muted">
                              · {date(item.created_at)}
                            </span>
                          </p>
                          <p className="mt-1 whitespace-pre-wrap text-sm">{item.body}</p>
                          {item.parent_id && (
                            <p className="mt-1 text-xs text-ink-muted">
                              Trả lời:{" "}
                              {comments
                                .find((parent) => parent._id === item.parent_id)
                                ?.body.slice(0, 100) || "Nhận xét trước đó"}
                            </p>
                          )}
                          <div className="mt-2 flex items-center gap-3">
                            {item.resolved && (
                              <span className="text-xs text-ink-muted">Đã giải quyết</span>
                            )}
                            {mayComment && (
                              <button
                                className="text-sm text-brand"
                                onClick={() => setReplyTo(item)}
                              >
                                Trả lời
                              </button>
                            )}
                            {[item.created_by, selected.owner_id, selected.reviewer_id].includes(
                              userId,
                            ) && (
                              <button
                                className="text-sm text-brand"
                                disabled={busy}
                                onClick={() =>
                                  run(async () => {
                                    const updated = await testingRequest(
                                      `/bao-cao-cong-viec/${selected._id}/binh-luan/${item._id}`,
                                      {
                                        method: "PATCH",
                                        body: JSON.stringify({
                                          expected_revision: item.revision,
                                          resolved: !item.resolved,
                                        }),
                                      },
                                    );
                                    setComments((current) =>
                                      current.map((entry) =>
                                        entry._id === updated._id ? updated : entry,
                                      ),
                                    );
                                  })
                                }
                              >
                                {item.resolved ? "Mở lại nhận xét" : "Đánh dấu đã giải quyết"}
                              </button>
                            )}
                          </div>
                        </div>
                      ))}
                      {mayComment && (
                        <>
                          {replyTo && (
                            <p className="text-sm">
                              Trả lời {memberName(replyTo.created_by)}{" "}
                              <button className="ml-2 text-brand" onClick={() => setReplyTo(null)}>
                                Hủy trả lời
                              </button>
                            </p>
                          )}
                          <textarea
                            aria-label="Nội dung nhận xét"
                            className="apple-input"
                            placeholder="Viết nhận xét về báo cáo"
                            value={comment}
                            onChange={(event) => setComment(event.target.value)}
                          />
                          <button
                            className="secondary-button"
                            disabled={busy || !comment.trim()}
                            onClick={() =>
                              run(async () => {
                                const result = await testingRequest(
                                  `/bao-cao-cong-viec/${selected._id}/binh-luan`,
                                  {
                                    method: "POST",
                                    body: JSON.stringify({
                                      body: comment,
                                      parent_id: replyTo?._id || null,
                                      idempotency_key: key(),
                                    }),
                                  },
                                );
                                setComments((current) => [result, ...current]);
                                setComment("");
                                setReplyTo(null);
                              })
                            }
                          >
                            Gửi nhận xét
                          </button>
                        </>
                      )}
                      {tab === "inbox" && (
                        <button
                          className="secondary-button ml-2"
                          disabled={busy}
                          onClick={() =>
                            run(async () => {
                              await testingRequest(`/bao-cao-cong-viec/${selected._id}/xac-nhan`, {
                                method: "POST",
                              });
                              setNotice("Đã xác nhận nhận báo cáo.");
                            })
                          }
                        >
                          Xác nhận đã nhận
                        </button>
                      )}
                    </div>
                  </section>
                )}
              </>
            )}
          </>
        )
      )}
      {printDocument && selected && (
        <section
          id="report-print-view"
          className="report-print-view"
          aria-label="Bản xem trước để in"
        >
          <div className="report-print-controls flex items-center justify-between gap-3 border-b border-border pb-3">
            <span className="text-sm text-ink-muted">Bản xem trước khi in</span>
            <div className="flex gap-2">
              <button
                type="button"
                className="secondary-button inline-flex items-center gap-2"
                onClick={() => window.print()}
              >
                <Printer size={16} aria-hidden="true" />
                In
              </button>
              <button
                type="button"
                className="secondary-button inline-flex items-center gap-2"
                onClick={() => setPrintDocument(null)}
              >
                <X size={16} aria-hidden="true" />
                Đóng
              </button>
            </div>
          </div>
          <header className="report-print-header">
            <div className="report-print-logo-cell">
              <Image src="/brand/veriq-logo.png" alt="Logo Veriq" width={76} height={76} priority />
            </div>
            <div className="report-print-title-cell">
              <h1>BÁO CÁO TIẾN ĐỘ</h1>
            </div>
          </header>
          <DocumentEditor
            documentProfile="formal-report"
            key={`print-${selected._id}-${selected.revision}`}
            value={printDocument}
            readOnly
            label="Bản in báo cáo"
          />
        </section>
      )}
    </div>
  );
}
