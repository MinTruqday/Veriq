"use client";

import { useCallback, useEffect, useRef, useState } from "react";
import CompletionReportEditor from "../../components/CompletionReportEditor";
import DataTable from "../../components/DataTable";
import FormalReviewPanel from "../../components/FormalReviewPanel";
import LessonsLearnedPanel from "../../components/LessonsLearnedPanel";
import QualityGateBadge from "../../components/QualityGateBadge";
import ResidualRiskPanel from "../../components/ResidualRiskPanel";
import TestwareHandoverPanel from "../../components/TestwareHandoverPanel";
import { StructuredValueView } from "../../components/StructuredValueEditor";
import {
  ErrorState,
  LoadingState,
  Metric,
  Panel,
  StatusPill,
  useActionDialog,
} from "../../components/WorkspacePrimitives";
import { formatDate, messageOf, valueLabel } from "../../lib/testing";
import { testingApi } from "../../services/testing.service";
import ContentOriginBadge from "@/shared/components/common/ContentOriginBadge";

function lines(value, category) {
  return String(value || "")
    .split("\n")
    .map((item) => item.trim())
    .filter(Boolean)
    .map((observation) => ({
      category,
      observation,
      impact: "",
      recommendation: "",
      evidence_refs: [],
      owner_id: null,
      convert_to_improvement: false,
    }));
}

export default function CompletionPage({ project }) {
  const { ask, dialog } = useActionDialog();
  const [reports, setReports] = useState([]);
  const [snapshots, setSnapshots] = useState([]);
  const [builds, setBuilds] = useState([]);
  const [members, setMembers] = useState([]);
  const [selected, setSelected] = useState(null);
  const [editing, setEditing] = useState(false);
  const [narrativeDraft, setNarrativeDraft] = useState(null);
  const [lessonClusters, setLessonClusters] = useState(null);
  const [error, setError] = useState("");
  const [aiLoading, setAiLoading] = useState(false);
  const [aiTimedOut, setAiTimedOut] = useState(false);
  const [initialLoading, setInitialLoading] = useState(true);
  const [initialLoadFailed, setInitialLoadFailed] = useState(false);
  const initialDataLoaded = useRef(false);
  const can = (permission) => project.current_permissions?.includes(permission);
  const load = useCallback(async () => {
    if (!initialDataLoaded.current) setInitialLoading(true);
    try {
      const permissions = new Set(project.current_permissions || []);
      const [reportValues, snapshotValues, buildValues, memberValues] = await Promise.all([
        testingApi.listTestCompletionReports(project._id),
        permissions.has("testmonitor.read")
          ? testingApi.listMonitoringSnapshots(project._id)
          : Promise.resolve([]),
        permissions.has("build.read") ? testingApi.listBuilds(project._id) : Promise.resolve([]),
        permissions.has("project.members.read")
          ? testingApi.listMembers(project._id)
          : Promise.resolve([]),
      ]);
      setReports(reportValues);
      setSnapshots(snapshotValues);
      setBuilds(buildValues);
      setMembers(memberValues.filter((item) => item.status === "ACTIVE"));
      setSelected(
        (current) =>
          reportValues.find((item) => item._id === current?._id) || reportValues[0] || null,
      );
      setError("");
      initialDataLoaded.current = true;
      setInitialLoadFailed(false);
    } catch (reason) {
      setError(messageOf(reason));
      if (!initialDataLoaded.current) setInitialLoadFailed(true);
    } finally {
      setInitialLoading(false);
    }
  }, [project._id, project.current_permissions]);
  useEffect(() => {
    void load();
  }, [load]);

  useEffect(() => {
    if (!selected?._id) {
      setNarrativeDraft(null);
      setLessonClusters(null);
      setAiLoading(false);
      setAiTimedOut(false);
      return undefined;
    }
    let active = true;
    let timer;
    let attempts = 0;
    const lessonsExpected = Boolean(selected.lessons_learned?.length);
    setNarrativeDraft(null);
    setLessonClusters(null);
    setAiLoading(selected.status === "DRAFT");
    setAiTimedOut(false);
    const refresh = async () => {
      try {
        const [narrative, lessons] = await Promise.all([
          testingApi.getTestCompletionNarrative(selected._id),
          lessonsExpected
            ? testingApi.getTestCompletionLessonClusters(selected._id)
            : Promise.resolve(null),
        ]);
        if (!active) return;
        setNarrativeDraft(narrative);
        setLessonClusters(lessons);
        const narrativeReady = Boolean(narrative);
        const lessonsReady = !lessonsExpected || Boolean(lessons);
        if (narrativeReady && lessonsReady) {
          setAiLoading(false);
          return;
        }
      } catch (reason) {
        if (active) setError(messageOf(reason));
      }
      attempts += 1;
      if (active && selected.status === "DRAFT" && attempts < 20) {
        timer = setTimeout(refresh, 3000);
      } else if (active) {
        setAiLoading(false);
        setAiTimedOut(selected.status === "DRAFT");
      }
    };
    void refresh();
    return () => {
      active = false;
      clearTimeout(timer);
    };
  }, [selected?._id, selected?.revision, selected?.status, selected?.lessons_learned]);

  const run = async (operation) => {
    try {
      const value = await operation();
      await load();
      if (value?._id) setSelected(value);
      setEditing(false);
    } catch (reason) {
      setError(messageOf(reason));
    }
  };

  const runFromDialog = async (operation) => {
    try {
      const value = await operation();
      await load();
      if (value?._id) setSelected(value);
      setEditing(false);
    } catch (reason) {
      throw new Error(messageOf(reason));
    }
  };

  const create = async () => {
    await ask({
      title: "Tạo báo cáo hoàn tất kiểm thử",
      description:
        "Báo cáo cố định kế hoạch kiểm thử, bản phát hành, bản dựng và các lần chạy trong bản chụp số liệu giám sát.",
      confirmLabel: "Tạo báo cáo",
      fields: [
        {
          name: "snapshot_id",
          label: "Bản chụp số liệu giám sát",
          required: true,
          options: snapshots.map((item) => ({
            value: item._id,
            label: formatDate(item.snapshot_at),
          })),
        },
        {
          name: "build_id",
          label: "Bản dựng",
          required: true,
          options: builds.map((item) => ({
            value: item._id,
            label: `${item.identifier} · ${item.version}`,
          })),
        },
        { name: "worked", label: "Điều đã làm tốt mỗi dòng một nội dung", multiline: true },
        { name: "failed", label: "Điều chưa hiệu quả mỗi dòng một nội dung", multiline: true },
        { name: "blockers", label: "Trở ngại lặp lại mỗi dòng một nội dung", multiline: true },
      ],
      onConfirm: (answer) =>
        runFromDialog(() =>
          testingApi.createTestCompletionReport(project._id, {
            idempotency_key: crypto.randomUUID(),
            snapshot_id: answer.snapshot_id,
            build_id: answer.build_id,
            lessons_learned: [
              ...lines(answer.worked, "WORKED"),
              ...lines(answer.failed, "FAILED"),
              ...lines(answer.blockers, "BLOCKER"),
            ],
          }),
        ),
    });
  };

  const transition = async (method, title, extraFields = []) => {
    await ask({
      title,
      confirmLabel: title,
      fields: [...extraFields, { name: "note", label: "Ghi chú", required: true, multiline: true }],
      onConfirm: (answer) =>
        runFromDialog(() =>
          testingApi[method](selected._id, { expected_revision: selected.revision, ...answer }),
        ),
    });
  };

  const addResidualRisk = async () => {
    await ask({
      title: "Thêm rủi ro còn lại",
      confirmLabel: "Thêm rủi ro",
      fields: [
        { name: "title", label: "Tên rủi ro", required: true },
        { name: "description", label: "Mô tả", multiline: true },
        {
          name: "severity",
          label: "Mức độ",
          required: true,
          options: ["CRITICAL", "HIGH", "MEDIUM", "LOW"].map((value) => ({
            value,
            label: valueLabel(value),
          })),
          initialValue: "MEDIUM",
        },
        {
          name: "probability",
          label: "Xác suất",
          required: true,
          options: ["VERY_HIGH", "HIGH", "MEDIUM", "LOW", "VERY_LOW"].map((value) => ({
            value,
            label: valueLabel(value),
          })),
          initialValue: "MEDIUM",
        },
        {
          name: "impact",
          label: "Tác động",
          required: true,
          options: ["CRITICAL", "HIGH", "MEDIUM", "LOW"].map((value) => ({
            value,
            label: valueLabel(value),
          })),
          initialValue: "MEDIUM",
        },
        {
          name: "owner_id",
          label: "Người phụ trách",
          required: true,
          options: members.map((member) => ({
            value: member.user_id,
            label: member.user_label || member.user?.email || member.user_id,
          })),
        },
        { name: "expiry_at", label: "Ngày hết hạn", type: "datetime-local" },
      ],
      onConfirm: (answer) =>
        runFromDialog(() =>
          testingApi.addTestCompletionResidualRisk(selected._id, {
            expected_revision: selected.revision,
            risk: {
              risk_id: `RISK-${crypto.randomUUID()}`,
              title: answer.title,
              description: answer.description || "",
              severity: answer.severity,
              probability: answer.probability,
              impact: answer.impact,
              source_refs: [],
              owner_id: answer.owner_id,
              treatment: "PENDING",
              expiry_at: answer.expiry_at || null,
              status: "OPEN",
            },
          }),
        ),
    });
  };

  const addLesson = async () => {
    await ask({
      title: "Thêm bài học kinh nghiệm",
      confirmLabel: "Thêm bài học",
      fields: [
        {
          name: "category",
          label: "Nhóm",
          required: true,
          options: ["WORKED", "FAILED", "BLOCKER", "IMPROVEMENT", "OTHER"].map((value) => ({
            value,
            label: valueLabel(value),
          })),
          initialValue: "OTHER",
        },
        { name: "observation", label: "Quan sát", required: true, multiline: true },
        { name: "impact", label: "Tác động", multiline: true },
        { name: "recommendation", label: "Khuyến nghị", multiline: true },
        {
          name: "owner_id",
          label: "Người phụ trách",
          options: [
            { value: "", label: "Chưa giao" },
            ...members.map((member) => ({
              value: member.user_id,
              label: member.user_label || member.user?.email || member.user_id,
            })),
          ],
        },
      ],
      onConfirm: (answer) =>
        runFromDialog(() =>
          testingApi.addTestCompletionLesson(selected._id, {
            expected_revision: selected.revision,
            lesson: {
              category: answer.category,
              observation: answer.observation,
              impact: answer.impact || "",
              recommendation: answer.recommendation || "",
              evidence_refs: [],
              owner_id: answer.owner_id || null,
              convert_to_improvement: false,
            },
          }),
        ),
    });
  };

  const manageHandover = async () => {
    await ask({
      title: "Quản lý bàn giao tài sản kiểm thử",
      confirmLabel: "Lưu bàn giao",
      fields: [
        { name: "artifact_type", label: "Loại tài sản", required: true },
        { name: "artifact_id", label: "Tên hoặc mã tài sản", required: true },
        { name: "artifact_version_id", label: "Mã phiên bản (nếu có)" },
        { name: "handover_to", label: "Bàn giao cho", required: true },
        { name: "storage_location", label: "Vị trí lưu trữ", required: true },
        {
          name: "status",
          label: "Trạng thái",
          required: true,
          options: ["PENDING", "READY", "HANDED_OVER", "ACCEPTED"].map((value) => ({
            value,
            label: valueLabel(value),
          })),
          initialValue: "PENDING",
        },
        { name: "note", label: "Ghi chú", multiline: true },
      ],
      onConfirm: (answer) =>
        runFromDialog(() =>
          testingApi.manageTestCompletionHandover(selected._id, {
            expected_revision: selected.revision,
            item: {
              ...answer,
              artifact_version_id: answer.artifact_version_id || null,
              note: answer.note || "",
            },
          }),
        ),
    });
  };

  const exportReport = async (format) => {
    try {
      await testingApi.exportTestCompletionReport(selected._id, format);
      setError("");
    } catch (reason) {
      setError(messageOf(reason));
    }
  };

  return (
    <Panel
      title="Báo cáo hoàn tất kiểm thử"
      actions={
        can("testcompletion.create") && can("testmonitor.read") && can("build.read") ? (
          <button
            className="apple-button"
            type="button"
            disabled={!snapshots.length || !builds.length}
            onClick={create}
          >
            Tạo báo cáo hoàn tất
          </button>
        ) : null
      }
    >
      {dialog}
      {error && (
        <div className="p-5">
          <ErrorState message={error} />
        </div>
      )}
      {initialLoading ? (
        <div className="p-5">
          <LoadingState />
        </div>
      ) : initialLoadFailed ? (
        <div className="space-y-3 p-5">
          <ErrorState message={error || "Không thể tải báo cáo hoàn tất"} />
          <button className="secondary-button" type="button" onClick={() => void load()}>
            Tải lại
          </button>
        </div>
      ) : (
        <div className="grid border-t border-border/70 xl:grid-cols-[320px_minmax(0,1fr)]">
          <div className="border-r border-border/70">
            <DataTable
              items={reports}
              empty="Chưa có báo cáo hoàn tất"
              columns={[
                { key: "sequence", label: "Lần" },
                {
                  key: "created_at",
                  label: "Thời điểm",
                  render: (item) => (
                    <button
                      className="text-left text-accent"
                      type="button"
                      onClick={() => {
                        setSelected(item);
                      }}
                    >
                      {formatDate(item.created_at)}
                    </button>
                  ),
                },
                {
                  key: "status",
                  label: "Trạng thái",
                  render: (item) => <StatusPill value={item.status} />,
                },
              ]}
            />
          </div>
          <div className="min-w-0 p-5">
            {!selected ? (
              <p className="text-sm text-ink-muted">Chọn hoặc tạo báo cáo hoàn tất</p>
            ) : (
              <div className="space-y-7">
                <div className="flex flex-wrap items-center gap-2">
                  <StatusPill value={selected.status} />
                  <QualityGateBadge status={selected.quality_gate_status} />
                  {selected.status === "DRAFT" && can("testcompletion.update") && (
                    <button
                      className="secondary-button"
                      type="button"
                      onClick={() => setEditing(true)}
                    >
                      Chỉnh sửa
                    </button>
                  )}
                  {selected.status === "DRAFT" && can("testcompletion.risk.manage") && (
                    <button className="secondary-button" type="button" onClick={addResidualRisk}>
                      Thêm rủi ro
                    </button>
                  )}
                  {selected.status === "DRAFT" && can("testcompletion.lesson.create") && (
                    <button className="secondary-button" type="button" onClick={addLesson}>
                      Thêm bài học
                    </button>
                  )}
                  {selected.status === "DRAFT" && can("testcompletion.handover.manage") && (
                    <button className="secondary-button" type="button" onClick={manageHandover}>
                      Quản lý bàn giao
                    </button>
                  )}
                  {selected.status === "DRAFT" && can("testcompletion.submit_review") && (
                    <button
                      className="secondary-button"
                      type="button"
                      onClick={() => transition("submitTestCompletionReport", "Gửi rà soát")}
                    >
                      Gửi rà soát
                    </button>
                  )}
                  {selected.status === "IN_REVIEW" && can("testcompletion.review") && (
                    <button
                      className="secondary-button"
                      type="button"
                      onClick={() =>
                        transition("signOffTestCompletion", "Ký xác nhận", [
                          {
                            name: "decision",
                            label: "Quyết định",
                            required: true,
                            options: [
                              { value: "APPROVE", label: "Đồng ý" },
                              { value: "REJECT", label: "Không đồng ý" },
                            ],
                          },
                        ])
                      }
                    >
                      Ký xác nhận
                    </button>
                  )}
                  {selected.status === "IN_REVIEW" && can("testcompletion.review") && (
                    <button
                      className="secondary-button"
                      type="button"
                      onClick={() =>
                        transition("requestTestCompletionChanges", "Yêu cầu chỉnh sửa")
                      }
                    >
                      Yêu cầu chỉnh sửa
                    </button>
                  )}
                  {selected.status === "IN_REVIEW" && can("testcompletion.approve") && (
                    <button
                      className="apple-button"
                      type="button"
                      onClick={() => transition("approveTestCompletionReport", "Phê duyệt báo cáo")}
                    >
                      Phê duyệt
                    </button>
                  )}
                  {selected.status === "APPROVED" && can("testcompletion.close") && (
                    <button
                      className="apple-button"
                      type="button"
                      onClick={() => transition("closeTestCompletionReport", "Đóng báo cáo")}
                    >
                      Đóng báo cáo
                    </button>
                  )}
                  {can("report.export") && (
                    <>
                      <button
                        className="secondary-button"
                        type="button"
                        onClick={() => exportReport("pdf")}
                      >
                        Xuất PDF
                      </button>
                      <button
                        className="secondary-button"
                        type="button"
                        onClick={() => exportReport("docx")}
                      >
                        Xuất DOCX
                      </button>
                      <button
                        className="secondary-button"
                        type="button"
                        onClick={() => exportReport("csv")}
                      >
                        Xuất CSV
                      </button>
                    </>
                  )}
                </div>
                {aiLoading && !narrativeDraft && (
                  <p className="text-sm text-ink-muted" role="status">
                    Báo cáo vừa tạo; đang chờ lượt AI tự động xử lý.
                  </p>
                )}
                {aiTimedOut && !narrativeDraft && (
                  <p className="text-sm text-ink-muted" role="status">
                    Chưa nhận được kết quả tự động. Báo cáo gốc vẫn được giữ nguyên; xem trạng thái
                    lượt chạy trong Lịch sử AI.
                  </p>
                )}
                {narrativeDraft?.suggestions?.[0] && (
                  <Panel title="Diễn giải AI cho báo cáo hoàn tất">
                    <div className="space-y-4 text-sm">
                      <div className="rounded-control border border-violet-300 bg-violet-50/60 p-3">
                        <ContentOriginBadge origin="ai_generated" />
                        <p className="mt-2 text-violet-950">
                          Đây là nội dung AI đề xuất; số liệu và quyết định trong báo cáo gốc được
                          giữ riêng.
                        </p>
                      </div>
                      {[
                        ["Tóm tắt điều hành", "executive_summary"],
                        ["Tổng kết đóng kiểm thử", "closure_summary"],
                        ["Rủi ro còn lại", "residual_risk_summary"],
                        ["Cơ sở khuyến nghị", "recommendation_rationale"],
                      ].map(([label, key]) => (
                        <div key={key}>
                          <p className="field-label">{label}</p>
                          <p className="mt-1 whitespace-pre-wrap">
                            {narrativeDraft.suggestions[0][key]}
                          </p>
                        </div>
                      ))}
                      <p className="text-xs text-ink-muted">
                        Nội dung AI được lưu riêng, không sửa số liệu, quyết định hoặc báo cáo
                        nguồn. Kết quả của phiên bản cũ sẽ được đánh dấu khi báo cáo thay đổi.
                      </p>
                    </div>
                  </Panel>
                )}
                {narrativeDraft?.stale && (
                  <p className="text-sm text-amber-700" role="status">
                    Diễn giải thuộc phiên bản báo cáo trước; không dùng như nội dung hiện hành.
                  </p>
                )}
                {lessonClusters?.suggestions?.length > 0 && (
                  <Panel title="Nhóm bài học do AI đề xuất">
                    <div className="space-y-3">
                      <div className="rounded-control border border-violet-300 bg-violet-50/60 p-3">
                        <ContentOriginBadge origin="ai_generated" />
                      </div>
                      {lessonClusters.suggestions.map((item, index) => (
                        <article
                          className="rounded-xl border border-violet-200 bg-violet-50/30 p-3 text-sm"
                          key={`${item.theme}-${index}`}
                        >
                          <p className="font-semibold">{item.theme}</p>
                          <p className="mt-1">{item.summary}</p>
                          <p className="mt-2 text-xs text-ink-muted">
                            Nguồn {item.source_indices.map((value) => value + 1).join(", ")}
                          </p>
                        </article>
                      ))}
                      <p className="text-xs text-ink-muted">
                        Kết quả gom nhóm không thay thế các bài học nguồn và không tự tạo hành động
                        cải tiến
                      </p>
                    </div>
                  </Panel>
                )}
                <div className="grid grid-cols-2 gap-3 lg:grid-cols-4">
                  <Metric
                    label="Tiến độ thực thi"
                    value={`${selected.execution_summary?.execution_percent ?? 0}%`}
                  />
                  <Metric
                    label="Tỷ lệ đạt"
                    value={`${selected.execution_summary?.pass_rate ?? 0}%`}
                  />
                  <Metric
                    label="Độ phủ yêu cầu"
                    value={`${selected.coverage_summary?.requirement_coverage ?? 0}%`}
                  />
                  {selected.coverage_summary?.api_coverage !== null &&
                    selected.coverage_summary?.api_coverage !== undefined && (
                      <Metric
                        label="Độ phủ API"
                        value={`${selected.coverage_summary.api_coverage}%`}
                      />
                    )}
                  {selected.coverage_summary?.nfr_coverage !== null &&
                    selected.coverage_summary?.nfr_coverage !== undefined && (
                      <Metric
                        label="Độ phủ phi chức năng"
                        value={`${selected.coverage_summary.nfr_coverage}%`}
                      />
                    )}
                  <Metric
                    label="Lỗi nghiêm trọng chưa xử lý"
                    value={selected.defect_summary?.open_critical ?? 0}
                  />
                </div>
                <details className="rounded-xl border border-border p-4 text-sm">
                  <summary className="cursor-pointer font-medium">
                    Thông tin phạm vi báo cáo
                  </summary>
                  <div className="mt-3 grid gap-3 md:grid-cols-2 xl:grid-cols-3">
                    <p>
                      <span className="field-label">Kế hoạch kiểm thử</span>
                      <br />
                      {selected.test_plan_id ? "Đã ghi nhận" : "Chưa ghi nhận"}
                    </p>
                    <p>
                      <span className="field-label">Chiến lược kiểm thử</span>
                      <br />
                      {selected.strategy_version_id ? "Đã ghi nhận" : "Chưa ghi nhận"}
                    </p>
                    <p>
                      <span className="field-label">Bản phát hành</span>
                      <br />
                      {selected.release_id ? "Đã ghi nhận" : "Chưa ghi nhận"}
                    </p>
                    <p>
                      <span className="field-label">Bản dựng</span>
                      <br />
                      {selected.build_id ? "Đã ghi nhận" : "Chưa ghi nhận"}
                    </p>
                    <p>
                      <span className="field-label">Bản chụp số liệu giám sát</span>
                      <br />
                      {selected.monitoring_snapshot_id ? "Đã ghi nhận" : "Chưa ghi nhận"}
                    </p>
                    <p>
                      <span className="field-label">Khuyến nghị</span>
                      <br />
                      {valueLabel(selected.recommendation)}
                    </p>
                  </div>
                </details>
                {(selected.executive_summary ||
                  selected.closure_summary ||
                  selected.residual_risk_summary ||
                  selected.recommendation_rationale) && (
                  <div className="grid gap-4 md:grid-cols-2">
                    {[
                      ["Tóm tắt điều hành", selected.executive_summary],
                      ["Tổng kết đóng kiểm thử", selected.closure_summary],
                      ["Rủi ro còn lại", selected.residual_risk_summary],
                      ["Cơ sở khuyến nghị", selected.recommendation_rationale],
                    ].map(([label, value]) => (
                      <div key={label}>
                        <p className="field-label">{label}</p>
                        <p className="mt-2 whitespace-pre-wrap text-sm">
                          {value || "Chưa ghi nhận"}
                        </p>
                      </div>
                    ))}
                  </div>
                )}
                <div>
                  <h3 className="mb-3 font-semibold text-ink">Đánh giá điều kiện kết thúc</h3>
                  <DataTable
                    items={(selected.exit_criteria_evaluation || []).map((item, index) => ({
                      ...item,
                      _id: item.criterion_id || index,
                    }))}
                    empty="Không có tiêu chí thoát"
                    columns={[
                      { key: "criterion", label: "Tiêu chí" },
                      {
                        key: "actual",
                        label: "Thực tế",
                        render: (item) => <StructuredValueView value={item.actual} />,
                      },
                      {
                        key: "status",
                        label: "Kết quả",
                        render: (item) => <StatusPill value={item.status} />,
                      },
                    ]}
                  />
                </div>
                <div>
                  <h3 className="mb-3 font-semibold text-ink">Hạng mục chưa giải quyết</h3>
                  <DataTable
                    items={(selected.unresolved_items || []).map((item, index) =>
                      typeof item === "string"
                        ? { _id: index, type: "OTHER", title: item }
                        : { ...item, _id: item.defect_id || item.test_result_id || index },
                    )}
                    empty="Không có hạng mục chưa giải quyết"
                    columns={[
                      { key: "type", label: "Loại", render: (item) => valueLabel(item.type) },
                      {
                        key: "title",
                        label: "Nội dung",
                        render: (item) => item.title || item.reason,
                      },
                      {
                        key: "severity",
                        label: "Mức độ",
                        render: (item) => valueLabel(item.severity),
                      },
                    ]}
                  />
                </div>
                <ResidualRiskPanel
                  items={selected.residual_risks || []}
                  members={members}
                  onDecide={
                    can("testcompletion.review") && ["DRAFT", "IN_REVIEW"].includes(selected.status)
                      ? async (risk) => {
                          await ask({
                            title: "Ghi nhận xử lý rủi ro",
                            description: risk.title,
                            confirmLabel: "Ghi nhận",
                            fields: [
                              {
                                name: "acceptance",
                                label: "Cách xử lý",
                                required: true,
                                options: [
                                  { value: "ACCEPTED", label: "Chấp nhận" },
                                  { value: "MITIGATE", label: "Giảm thiểu" },
                                  { value: "TRANSFER", label: "Chuyển giao" },
                                  { value: "AVOID", label: "Tránh" },
                                ],
                              },
                              { name: "reason", label: "Lý do", required: true, multiline: true },
                            ],
                            onConfirm: (answer) =>
                              runFromDialog(() =>
                                testingApi.decideTestCompletionResidualRisk(
                                  selected._id,
                                  risk.risk_id,
                                  { expected_revision: selected.revision, ...answer },
                                ),
                              ),
                          });
                        }
                      : null
                  }
                />
                <LessonsLearnedPanel
                  lessons={selected.lessons_learned || []}
                  actions={selected.improvement_actions || []}
                  members={members}
                />
                <TestwareHandoverPanel
                  handover={selected.testware_handover}
                  archived={selected.archived_artifacts}
                  environments={selected.environment_closure}
                />
                <div>
                  <h3 className="mb-3 font-semibold text-ink">Xác nhận</h3>
                  <DataTable
                    items={(selected.sign_offs || []).map((item) => ({
                      ...item,
                      _id: item.user_id,
                    }))}
                    empty="Chưa có xác nhận"
                    columns={[
                      {
                        key: "user_id",
                        label: "Người xác nhận",
                        render: (item) =>
                          item.user_label ||
                          members.find((member) => member.user_id === item.user_id)?.user_label ||
                          members.find((member) => member.user_id === item.user_id)?.user?.email ||
                          "Không có tên hiển thị",
                      },
                      { key: "role", label: "Vai trò", render: (item) => valueLabel(item.role) },
                      {
                        key: "decision",
                        label: "Quyết định",
                        render: (item) => valueLabel(item.decision),
                      },
                      { key: "at", label: "Thời điểm", render: (item) => formatDate(item.at) },
                    ]}
                  />
                </div>
                {selected.approved_snapshot_hash && (
                  <details className="text-xs text-ink-muted">
                    <summary className="cursor-pointer">Mã kiểm tra bản đã duyệt</summary>
                    <p className="mt-1 break-all">{selected.approved_snapshot_hash}</p>
                  </details>
                )}
                {can("reviewsession.read") && (
                  <FormalReviewPanel
                    project={project}
                    artifactType="COMPLETION_REPORT"
                    artifactId={selected._id}
                    artifactVersionId={selected._id}
                    reviewType="COMPLETION_REPORT"
                  />
                )}
              </div>
            )}
          </div>
        </div>
      )}
      <CompletionReportEditor
        report={editing ? selected : null}
        members={members}
        onClose={() => setEditing(false)}
        onSave={(payload) =>
          run(() => testingApi.updateTestCompletionReport(selected._id, payload))
        }
      />
    </Panel>
  );
}
