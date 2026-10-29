"use client";
import { useCallback, useEffect, useState } from "react";
import DataTable from "./DataTable";
import FormalReviewPanel from "./FormalReviewPanel";
import QualityGateBadge from "./QualityGateBadge";
import { ErrorState, Metric, Panel, StatusPill, useActionDialog } from "./WorkspacePrimitives";
import { formatDate, messageOf, valueLabel } from "../lib/testing";
import { testingApi } from "../services/testing.service";
import { StructuredValueView } from "./StructuredValueEditor";
import ContentOriginBadge from "@/shared/components/common/ContentOriginBadge";

function lines(value) {
  return String(value || "")
    .split("\n")
    .map((item) => item.trim())
    .filter(Boolean);
}

function forecastText(value) {
  if (!value) return "";
  if (typeof value === "string") return value;
  return [
    value.expected_completion_at
      ? `Dự kiến hoàn tất ${formatDate(value.expected_completion_at)}`
      : "",
    value.confidence === null || value.confidence === undefined
      ? ""
      : `Độ tin cậy dự báo ${Math.round(value.confidence * 100)}%`,
    ...(value.assumptions || []),
  ]
    .filter(Boolean)
    .join("\n");
}

export default function TestStatusReportPanel({ project }) {
  const { ask, dialog } = useActionDialog();
  const [reports, setReports] = useState([]);
  const [snapshots, setSnapshots] = useState([]);
  const [builds, setBuilds] = useState([]);
  const [selected, setSelected] = useState(null);
  const [comparison, setComparison] = useState(null);
  const [narrativeResult, setNarrativeResult] = useState(null);
  const [error, setError] = useState("");
  const [narrativeLoading, setNarrativeLoading] = useState(false);
  const [narrativeTimedOut, setNarrativeTimedOut] = useState(false);
  const can = (permission) => project.current_permissions?.includes(permission);
  const load = useCallback(async () => {
    try {
      const permissions = new Set(project.current_permissions || []);
      const [reportValues, snapshotValues, buildValues] = await Promise.all([
        testingApi.listTestStatusReports(project._id),
        permissions.has("testmonitor.read")
          ? testingApi.listMonitoringSnapshots(project._id)
          : Promise.resolve([]),
        permissions.has("build.read") ? testingApi.listBuilds(project._id) : Promise.resolve([]),
      ]);
      setReports(reportValues);
      setSnapshots(snapshotValues);
      setBuilds(buildValues);
      setSelected(
        (current) =>
          reportValues.find((item) => item._id === current?._id) || reportValues[0] || null,
      );
      setError("");
    } catch (reason) {
      setError(messageOf(reason));
    }
  }, [project._id, project.current_permissions]);
  useEffect(() => {
    void load();
  }, [load]);

  useEffect(() => {
    if (!selected?._id) {
      setNarrativeResult(null);
      setNarrativeLoading(false);
      return undefined;
    }
    let active = true;
    let timer;
    let attempts = 0;
    setNarrativeResult(null);
    setNarrativeLoading(true);
    setNarrativeTimedOut(false);
    const refreshNarrative = async () => {
      try {
        const value = await testingApi.getTestStatusReportNarrative(selected._id);
        if (!active) return;
        if (value) {
          setNarrativeResult(value);
          setNarrativeLoading(false);
          return;
        }
      } catch (reason) {
        if (active) setError(messageOf(reason));
      }
      attempts += 1;
      if (active && attempts < 20) {
        timer = setTimeout(refreshNarrative, 3000);
      } else if (active) {
        setNarrativeLoading(false);
        setNarrativeTimedOut(true);
      }
    };
    void refreshNarrative();
    return () => {
      active = false;
      clearTimeout(timer);
    };
  }, [selected?._id, selected?.revision]);

  const run = async (operation, { retainDialog = false } = {}) => {
    try {
      const value = await operation();
      setComparison(null);
      setNarrativeResult(null);
      await load();
      if (value?._id) setSelected(value);
    } catch (reason) {
      const message = messageOf(reason);
      setError(message);
      if (retainDialog) throw new Error(message);
    }
  };

  const create = async () => {
    const today = new Date();
    const end = today.toISOString().slice(0, 16);
    const startDate = new Date(today.getTime() - 7 * 86400000);
    await ask({
      title: "Tạo báo cáo từ mốc giám sát",
      confirmLabel: "Tạo báo cáo",
      fields: [
        {
          name: "snapshot_id",
          label: "Mốc giám sát",
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
        {
          name: "start_at",
          label: "Bắt đầu kỳ báo cáo",
          required: true,
          type: "datetime-local",
          initialValue: startDate.toISOString().slice(0, 16),
        },
        {
          name: "end_at",
          label: "Kết thúc kỳ báo cáo",
          required: true,
          type: "datetime-local",
          initialValue: end,
        },
        { name: "executive_summary", label: "Tóm tắt điều hành", multiline: true },
        { name: "expected_completion_at", label: "Dự kiến hoàn tất", type: "datetime-local" },
        {
          name: "forecast_confidence",
          label: "Độ tin cậy dự báo (%)",
          type: "number",
          min: 0,
          max: 100,
          step: 1,
        },
        {
          name: "forecast_assumptions",
          label: "Giả định dự báo mỗi dòng một mục",
          multiline: true,
        },
        { name: "distribution", label: "Danh sách phân phối mỗi dòng một người", multiline: true },
        { name: "evidence_refs", label: "Mã bằng chứng mỗi dòng một mã", multiline: true },
      ],
      onConfirm: (answer) =>
        run(
          () =>
            testingApi.generateTestStatusReport(project._id, {
              idempotency_key: crypto.randomUUID(),
              snapshot_id: answer.snapshot_id,
              build_id: answer.build_id,
              reporting_period: {
                start_at: new Date(answer.start_at).toISOString(),
                end_at: new Date(answer.end_at).toISOString(),
              },
              executive_summary: answer.executive_summary,
              forecast: {
                expected_completion_at: answer.expected_completion_at
                  ? new Date(answer.expected_completion_at).toISOString()
                  : null,
                confidence:
                  answer.forecast_confidence === ""
                    ? null
                    : Number(answer.forecast_confidence) / 100,
                assumptions: lines(answer.forecast_assumptions),
              },
              distribution: lines(answer.distribution),
              evidence_refs: lines(answer.evidence_refs),
            }),
          { retainDialog: true },
        ),
    });
  };

  const edit = async () => {
    if (!selected) return;
    await ask({
      title: "Chỉnh sửa nội dung báo cáo",
      confirmLabel: "Lưu nội dung",
      fields: [
        {
          name: "executive_summary",
          label: "Tóm tắt điều hành",
          multiline: true,
          initialValue: selected.executive_summary,
        },
        {
          name: "risk_explanation",
          label: "Diễn giải rủi ro",
          multiline: true,
          initialValue: selected.risk_explanation,
        },
        {
          name: "expected_completion_at",
          label: "Dự kiến hoàn tất",
          type: "datetime-local",
          initialValue: selected.forecast?.expected_completion_at?.slice(0, 16),
        },
        {
          name: "forecast_confidence",
          label: "Độ tin cậy dự báo (%)",
          type: "number",
          min: 0,
          max: 100,
          step: 1,
          initialValue:
            selected.forecast?.confidence == null
              ? ""
              : Math.round(selected.forecast.confidence * 100),
        },
        {
          name: "forecast_assumptions",
          label: "Giả định dự báo mỗi dòng một mục",
          multiline: true,
          initialValue: (selected.forecast?.assumptions || []).join("\n"),
        },
        {
          name: "recommendation_narrative",
          label: "Diễn giải khuyến nghị",
          multiline: true,
          initialValue: selected.recommendation_narrative,
        },
        {
          name: "distribution",
          label: "Danh sách phân phối mỗi dòng một người",
          multiline: true,
          initialValue: (selected.distribution || []).join("\n"),
        },
      ],
      onConfirm: (answer) =>
        run(
          () =>
            testingApi.updateTestStatusReport(selected._id, {
              expected_revision: selected.revision,
              executive_summary: answer.executive_summary,
              risk_explanation: answer.risk_explanation,
              forecast: {
                expected_completion_at: answer.expected_completion_at
                  ? new Date(answer.expected_completion_at).toISOString()
                  : null,
                confidence:
                  answer.forecast_confidence === ""
                    ? null
                    : Number(answer.forecast_confidence) / 100,
                assumptions: lines(answer.forecast_assumptions),
              },
              recommendation_narrative: answer.recommendation_narrative,
              distribution: lines(answer.distribution),
            }),
          { retainDialog: true },
        ),
    });
  };

  const attachEvidence = async () => {
    if (!selected) return;
    await ask({
      title: "Gắn bằng chứng",
      confirmLabel: "Gắn bằng chứng",
      fields: [
        {
          name: "evidence_refs",
          label: "Mã bằng chứng mỗi dòng một mã",
          required: true,
          multiline: true,
        },
      ],
      onConfirm: (answer) =>
        run(
          () =>
            testingApi.attachTestStatusReportEvidence(selected._id, {
              expected_revision: selected.revision,
              evidence_refs: lines(answer.evidence_refs),
            }),
          { retainDialog: true },
        ),
    });
  };

  const transition = async (action, title) => {
    await ask({
      title,
      confirmLabel: title,
      fields: [{ name: "note", label: "Ghi chú", multiline: true }],
      onConfirm: (answer) =>
        run(
          () =>
            testingApi[action](selected._id, {
              expected_revision: selected.revision,
              note: answer.note,
            }),
          { retainDialog: true },
        ),
    });
  };

  const compare = async () => {
    const candidates = reports.filter((item) => item._id !== selected?._id);
    const answer = await ask({
      title: "So sánh báo cáo",
      confirmLabel: "So sánh",
      fields: [
        {
          name: "other_report_id",
          label: "Báo cáo đối chiếu",
          required: true,
          options: candidates.map((item) => ({
            value: item._id,
            label: `Lần ${item.sequence} · ${formatDate(item.created_at)}`,
          })),
        },
      ],
    });
    if (!answer) return;
    try {
      setComparison(
        await testingApi.compareTestStatusReports(selected._id, answer.other_report_id),
      );
    } catch (reason) {
      setError(messageOf(reason));
    }
  };

  return (
    <Panel
      title="Báo cáo trạng thái kiểm thử"
      actions={
        can("teststatusreport.create") && can("testmonitor.read") && can("build.read") ? (
          <button
            className="apple-button"
            type="button"
            disabled={!snapshots.length || !builds.length}
            onClick={create}
          >
            Tạo báo cáo
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
      <div className="grid border-t border-border/70 xl:grid-cols-[320px_minmax(0,1fr)]">
        <div className="border-r border-border/70">
          <DataTable
            items={reports}
            empty="Chưa có báo cáo trạng thái"
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
                      setComparison(null);
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
            <p className="text-sm text-ink-muted">Chọn hoặc tạo báo cáo trạng thái</p>
          ) : (
            <div className="space-y-5">
              <div className="flex flex-wrap items-center gap-2">
                <StatusPill value={selected.status} />
                <QualityGateBadge status={selected.snapshot_basis?.quality_gate_status} />
                {selected.status === "DRAFT" && can("teststatusreport.update") && (
                  <button className="secondary-button" type="button" onClick={edit}>
                    Chỉnh sửa
                  </button>
                )}
                {selected.status === "DRAFT" && can("teststatusreport.update") && (
                  <button className="secondary-button" type="button" onClick={attachEvidence}>
                    Gắn bằng chứng
                  </button>
                )}
                {selected.status === "DRAFT" && can("teststatusreport.submit_review") && (
                  <button
                    className="secondary-button"
                    type="button"
                    onClick={() => transition("submitTestStatusReport", "Gửi rà soát")}
                  >
                    Gửi rà soát
                  </button>
                )}
                {selected.status === "IN_REVIEW" && can("teststatusreport.review") && (
                  <button
                    className="secondary-button"
                    type="button"
                    onClick={() =>
                      transition("requestTestStatusReportChanges", "Yêu cầu chỉnh sửa")
                    }
                  >
                    Yêu cầu chỉnh sửa
                  </button>
                )}
                {selected.status === "IN_REVIEW" && can("teststatusreport.approve") && (
                  <button
                    className="apple-button"
                    type="button"
                    onClick={() => transition("approveTestStatusReport", "Phê duyệt")}
                  >
                    Phê duyệt
                  </button>
                )}
                {selected.status === "APPROVED" && can("teststatusreport.publish") && (
                  <button
                    className="apple-button"
                    type="button"
                    onClick={() => transition("publishTestStatusReport", "Phát hành")}
                  >
                    Phát hành
                  </button>
                )}
                {selected.status === "PUBLISHED" && can("teststatusreport.archive") && (
                  <button
                    className="secondary-button"
                    type="button"
                    onClick={() => transition("archiveTestStatusReport", "Lưu trữ")}
                  >
                    Lưu trữ
                  </button>
                )}
                {reports.length > 1 && (
                  <button className="secondary-button" type="button" onClick={compare}>
                    So sánh
                  </button>
                )}
                {can("report.export") &&
                  [
                    { format: "pdf", label: "Xuất PDF" },
                    { format: "docx", label: "Xuất DOCX" },
                    { format: "csv", label: "Xuất CSV" },
                  ].map((item) => (
                    <button
                      className="secondary-button"
                      type="button"
                      key={item.format}
                      onClick={() =>
                        testingApi
                          .exportTestStatusReport(selected._id, item.format)
                          .catch((reason) => setError(messageOf(reason)))
                      }
                    >
                      {item.label}
                    </button>
                  ))}
              </div>
              {narrativeLoading && !narrativeResult && (
                <p className="text-sm text-ink-muted" role="status">
                  Báo cáo đã được tạo; đang chờ AI tạo phần diễn giải.
                </p>
              )}
              {narrativeTimedOut && !narrativeResult && (
                <p className="text-sm text-ink-muted" role="status">
                  Chưa nhận được kết quả tự động. Báo cáo gốc vẫn được giữ nguyên; kiểm tra trạng
                  thái xử lý AI.
                </p>
              )}
              {narrativeResult?.suggestions?.[0] && (
                <Panel title="Diễn giải được tạo tự động">
                  <div className="space-y-4 text-sm">
                    <div className="rounded-control border border-violet-300 bg-violet-50/60 p-3">
                      <ContentOriginBadge origin="ai_generated" />
                      <p className="mt-2 text-violet-950">
                        Phần này do AI đề xuất riêng; không thay đổi số liệu hoặc nội dung người
                        dùng đã nhập.
                      </p>
                    </div>
                    {narrativeResult.stale && (
                      <p className="text-amber-700" role="status">
                        Báo cáo đã đổi sau khi AI tạo phần diễn giải; kết quả này thuộc phiên bản
                        trước và không được dùng làm nội dung hiện hành.
                      </p>
                    )}
                    {[
                      ["Tóm tắt điều hành", narrativeResult.suggestions[0].executive_summary],
                      ["Diễn giải rủi ro", narrativeResult.suggestions[0].risk_explanation],
                      ["Dự báo", forecastText(narrativeResult.suggestions[0].forecast)],
                      [
                        "Diễn giải khuyến nghị",
                        narrativeResult.suggestions[0].recommendation_narrative,
                      ],
                    ].map(([label, value]) => (
                      <div key={label}>
                        <p className="field-label">{label}</p>
                        <p className="mt-1 whitespace-pre-wrap">{value || "Chưa có nội dung"}</p>
                      </div>
                    ))}
                    <p className="text-xs text-ink-muted">
                      Kết quả được tạo từ sự kiện tạo báo cáo; không thay đổi số liệu hoặc nội dung
                      báo cáo gốc.
                    </p>
                  </div>
                </Panel>
              )}
              {narrativeResult && !narrativeResult.suggestions?.[0] && (
                <p className="text-sm text-ink-muted" role="status">
                  Lượt AI tự động chưa tạo được phần diễn giải: {valueLabel(narrativeResult.status)}
                </p>
              )}
              <div className="grid grid-cols-2 gap-3 lg:grid-cols-4">
                <Metric
                  label="Thực thi"
                  value={`${selected.snapshot_basis?.metrics?.execution_percent ?? 0}%`}
                />
                <Metric
                  label="Tỷ lệ đạt"
                  value={`${selected.snapshot_basis?.metrics?.pass_rate ?? 0}%`}
                />
                <Metric
                  label="Độ phủ yêu cầu"
                  value={`${selected.snapshot_basis?.metrics?.requirement_coverage ?? 0}%`}
                />
                <Metric
                  label="Độ phủ điều kiện kiểm thử"
                  value={`${selected.snapshot_basis?.metrics?.test_condition_coverage ?? 0}%`}
                />
              </div>
              <div className="grid gap-4 md:grid-cols-2">
                {[
                  ["Tóm tắt điều hành", selected.executive_summary],
                  ["Tiến độ", selected.progress_summary],
                  ["Độ phủ", selected.coverage_summary],
                  ["Lỗi", selected.defect_summary],
                  ["Diễn giải rủi ro", selected.risk_explanation],
                  ["Dự báo", forecastText(selected.forecast)],
                  ["Khuyến nghị", valueLabel(selected.recommendation)],
                  ["Diễn giải khuyến nghị", selected.recommendation_narrative],
                ].map(([label, value]) => (
                  <div key={label}>
                    <p className="field-label">{label}</p>
                    <p className="mt-2 whitespace-pre-wrap text-sm text-ink">
                      {value || "Chưa ghi nhận"}
                    </p>
                  </div>
                ))}
              </div>
              <DataTable
                items={(selected.control_actions || []).map((item, index) => ({
                  ...item,
                  _id: item._id || `action-${index}`,
                }))}
                empty="Không có hành động kiểm soát"
                columns={[
                  { key: "title", label: "Hành động kiểm soát" },
                  { key: "owner_id", label: "Người phụ trách" },
                  {
                    key: "status",
                    label: "Trạng thái",
                    render: (item) => <StatusPill value={item.status} />,
                  },
                ]}
              />
              {comparison && (
                <Panel title="Kết quả so sánh">
                  <DataTable
                    items={(comparison.changes || []).map((item) => ({ ...item, _id: item.field }))}
                    empty="Hai báo cáo không khác nhau"
                    columns={[
                      { key: "field", label: "Trường" },
                      {
                        key: "from",
                        label: "Báo cáo hiện tại",
                        render: (item) => <StructuredValueView value={item.from} />,
                      },
                      {
                        key: "to",
                        label: "Báo cáo đối chiếu",
                        render: (item) => <StructuredValueView value={item.to} />,
                      },
                    ]}
                  />
                </Panel>
              )}
              <details className="text-xs text-ink-muted">
                <summary className="cursor-pointer">Chi tiết kỹ thuật</summary>
                <p className="mt-1 break-all">Mốc giám sát: {selected.snapshot_id}</p>
                <p className="break-all">
                  Mã đối chiếu dữ liệu: {selected.snapshot_source_fingerprint}
                </p>
              </details>
              {can("reviewsession.read") && (
                <FormalReviewPanel
                  project={project}
                  artifactType="STATUS_REPORT"
                  artifactId={selected._id}
                  artifactVersionId={selected._id}
                  reviewType="STATUS_REPORT"
                />
              )}
            </div>
          )}
        </div>
      </div>
    </Panel>
  );
}
