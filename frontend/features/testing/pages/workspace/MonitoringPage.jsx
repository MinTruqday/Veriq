"use client";
import { useDateTimeOptions } from "../../hooks/useDateTimeOptions";
import { useCallback, useEffect, useRef, useState } from "react";
import DataTable from "../../components/DataTable";
import ExitCriteriaPanel from "../../components/ExitCriteriaPanel";
import PlanVsActualPanel from "../../components/PlanVsActualPanel";
import QualityGateBadge from "../../components/QualityGateBadge";
import TestControlActionPanel from "../../components/TestControlActionPanel";
import TestProgressBoard from "../../components/TestProgressBoard";
import SegmentedTabs from "@/shared/components/navigation/SegmentedTabs";
import {
  ErrorState,
  InitialLoadState,
  Panel,
  ProjectCrumb,
  WorkspacePage,
  useActionDialog,
} from "../../components/WorkspacePrimitives";
import {
  formatCalendarDate as formatCalendarDateValue,
  formatDate as formatDateValue,
  messageOf,
  valueLabel,
} from "../../lib/testing";
import { testingApi } from "../../services/testing.service";

const controlTypes = [
  "PAUSE_EXECUTION",
  "RESUME_EXECUTION",
  "REQUEST_RETEST",
  "CREATE_ADDITIONAL_TEST_SCOPE",
  "REQUEST_NEW_BUILD",
  "BLOCK_RELEASE",
  "ACCEPT_RISK",
  "ESCALATE_DEFECT",
  "REPRIORITIZE_REGRESSION",
  "EXTEND_TEST_WINDOW",
];

function displayDeviationValue(value) {
  if (typeof value === "string" && /^\d{4}-\d{2}-\d{2}(?:T.*)?$/.test(value)) {
    return formatCalendarDateValue(value);
  }
  return value ?? "—";
}

const decisionLabels = {
  APPROVE_RELEASE: "Phê duyệt phát hành",
  BLOCK_RELEASE: "Chặn phát hành",
  ACCEPT_RISK: "Chấp nhận rủi ro",
};

const controlTypeLabels = {
  PAUSE_EXECUTION: "Tạm dừng thực thi",
  RESUME_EXECUTION: "Tiếp tục thực thi",
  REQUEST_RETEST: "Yêu cầu kiểm thử lại",
  CREATE_ADDITIONAL_TEST_SCOPE: "Bổ sung phạm vi kiểm thử",
  REQUEST_NEW_BUILD: "Yêu cầu bản dựng mới",
  BLOCK_RELEASE: "Chặn phát hành",
  ACCEPT_RISK: "Chấp nhận rủi ro",
  ESCALATE_DEFECT: "Báo cáo lỗi lên cấp cao hơn",
  REPRIORITIZE_REGRESSION: "Điều chỉnh ưu tiên hồi quy",
  EXTEND_TEST_WINDOW: "Gia hạn thời gian kiểm thử",
};

export default function MonitoringPage({ project }) {
  const dateTimeOptions = useDateTimeOptions(project);
  const formatDate = (value) => formatDateValue(value, dateTimeOptions);
  const formatCalendarDate = (value) => formatCalendarDateValue(value, dateTimeOptions);
  const { ask, dialog } = useActionDialog();
  const [plans, setPlans] = useState([]);
  const [members, setMembers] = useState([]);
  const [snapshots, setSnapshots] = useState([]);
  const [actions, setActions] = useState([]);
  const [gate, setGate] = useState(null);
  const [decisions, setDecisions] = useState([]);
  const [selectedPlanId, setSelectedPlanId] = useState("");
  const [selectedSnapshot, setSelectedSnapshot] = useState(null);
  const [activeView, setActiveView] = useState("overview");
  const [error, setError] = useState("");
  const [initialLoading, setInitialLoading] = useState(true);
  const [initialLoadFailed, setInitialLoadFailed] = useState(false);
  const initialDataLoaded = useRef(false);
  const loadedProjectId = useRef(project._id);
  const can = (permission) => project.current_permissions?.includes(permission);
  const memberName = (userId) => {
    const member = members.find((item) => item.user_id === userId);
    return member?.identity?.label || member?.full_name || member?.email || "Thành viên dự án";
  };
  const load = useCallback(async () => {
    if (loadedProjectId.current !== project._id) {
      loadedProjectId.current = project._id;
      initialDataLoaded.current = false;
      setInitialLoading(true);
    }
    try {
      const permissions = new Set(project.current_permissions || []);
      const [planValues, memberValues, snapshotValues, actionValues, decisionValues] =
        await Promise.all([
          permissions.has("testplan.read")
            ? testingApi.listPlans(project._id, { status: "APPROVED" })
            : Promise.resolve([]),
          permissions.has("project.members.read")
            ? testingApi.listMembers(project._id)
            : Promise.resolve([]),
          permissions.has("testmonitor.read")
            ? testingApi.listMonitoringSnapshots(
                project._id,
                selectedPlanId ? { test_plan_id: selectedPlanId } : {},
              )
            : Promise.resolve([]),
          permissions.has("testmonitor.read")
            ? testingApi.listControlActions(project._id)
            : Promise.resolve([]),
          permissions.has("qualitygate.read")
            ? testingApi.listQualityDecisions(project._id)
            : Promise.resolve([]),
        ]);
      setPlans(planValues);
      setMembers(memberValues);
      setSnapshots(snapshotValues);
      setActions(actionValues);
      setDecisions(decisionValues);
      setSelectedPlanId((current) => current || planValues[0]?._id || "");
      setSelectedSnapshot(
        (current) =>
          snapshotValues.find((item) => item._id === current?._id) || snapshotValues[0] || null,
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
  }, [project._id, project.current_permissions, selectedPlanId]);
  useEffect(() => {
    void load();
  }, [load]);
  useEffect(() => {
    if (!selectedSnapshot?._id || !project.current_permissions?.includes("qualitygate.read")) {
      setGate(null);
      return;
    }
    let active = true;
    testingApi
      .getQualityGate(selectedSnapshot._id)
      .then((value) => {
        if (active) setGate(value);
      })
      .catch((reason) => {
        if (active) setError(messageOf(reason));
      });
    return () => {
      active = false;
    };
  }, [project.current_permissions, selectedSnapshot?._id]);
  if (initialLoading || initialLoadFailed)
    return (
      <InitialLoadState
        title="Giám sát kiểm thử"
        projectId={project._id}
        loading={initialLoading}
        error={error}
        onRetry={() => void load()}
      />
    );
  const createSnapshot = async () => {
    if (!selectedPlanId) return;
    await ask({
      title: "Lưu mốc giám sát",
      confirmLabel: "Lưu mốc giám sát",
      fields: [
        { name: "actual_effort", label: "Nỗ lực thực tế theo giờ", type: "number" },
        {
          name: "expected_completion",
          label: "Thời điểm dự kiến hoàn thành",
          type: "datetime-local",
        },
      ],
      onConfirm: async (answer) => {
        try {
          const value = await testingApi.createMonitoringSnapshot(project._id, {
            test_plan_id: selectedPlanId,
            actual_effort: answer.actual_effort === "" ? null : Number(answer.actual_effort),
            expected_completion: answer.expected_completion || null,
            risks: [],
            blockers: [],
          });
          setSelectedSnapshot(value);
          await load();
        } catch (reason) {
          throw new Error(messageOf(reason));
        }
      },
    });
  };
  const createAction = async () => {
    if (!selectedSnapshot) return;
    await ask({
      title: "Tạo hành động kiểm soát",
      confirmLabel: "Tạo hành động",
      fields: [
        {
          name: "type",
          label: "Loại",
          required: true,
          options: controlTypes.map((value) => ({ value, label: controlTypeLabels[value] })),
        },
        { name: "title", label: "Nội dung", required: true },
        { name: "description", label: "Mô tả", multiline: true },
        {
          name: "owner_id",
          label: "Người phụ trách",
          required: true,
          options: members.map((item) => ({
            value: item.user_id,
            label: item.identity?.label || item.full_name || item.email || "Thành viên dự án",
          })),
        },
        { name: "due_at", label: "Hạn xử lý", required: true, type: "datetime-local" },
        {
          name: "priority",
          label: "Ưu tiên theo quy ước dự án",
          required: true,
          maxLength: 100,
        },
        { name: "decision_reason", label: "Lý do quyết định", required: true, multiline: true },
      ],
      onConfirm: async (answer) => {
        try {
          await testingApi.createControlAction(project._id, {
            ...answer,
            snapshot_id: selectedSnapshot._id,
            evidence_refs: [selectedSnapshot._id],
          });
          await load();
        } catch (reason) {
          throw new Error(messageOf(reason));
        }
      },
    });
  };
  const createDecision = async (decision) => {
    if (!selectedSnapshot) return;
    const fields = [{ name: "reason", label: "Lý do quyết định", required: true, multiline: true }];
    if (
      decision === "APPROVE_RELEASE" &&
      ["FAIL", "MANUAL_REQUIRED"].includes(gate?.overall_status)
    )
      fields.push({
        name: "override_reason",
        label: "Lý do ghi đè cổng chất lượng",
        required: true,
        multiline: true,
      });
    if (decision === "ACCEPT_RISK")
      fields.push(
        { name: "risks", label: "Mã rủi ro hoặc lỗi", required: true, multiline: true },
        {
          name: "owner_id",
          label: "Người chịu trách nhiệm",
          required: true,
          options: members.map((item) => ({
            value: item.user_id,
            label: item.identity?.label || item.full_name || item.email || "Thành viên dự án",
          })),
        },
        { name: "expiry_at", label: "Ngày hết hạn", required: true, type: "datetime-local" },
      );
    await ask({
      title: decisionLabels[decision],
      confirmLabel: "Ghi nhận quyết định",
      fields,
      onConfirm: async (answer) => {
        try {
          await testingApi.createQualityDecision(selectedSnapshot._id, {
            idempotency_key: crypto.randomUUID(),
            decision,
            reason: answer.reason,
            override_reason: answer.override_reason || null,
            risk_acceptance:
              decision === "ACCEPT_RISK"
                ? {
                    risks: answer.risks
                      .split(/[\n,]/)
                      .map((value) => value.trim())
                      .filter(Boolean),
                    owner_id: answer.owner_id,
                    expiry_at: answer.expiry_at,
                  }
                : null,
            evidence_refs: [selectedSnapshot._id, gate?._id].filter(Boolean),
          });
          await load();
        } catch (reason) {
          throw new Error(messageOf(reason));
        }
      },
    });
  };
  const exportGate = async () => {
    if (!selectedSnapshot) return;
    try {
      const value = await testingApi.exportQualityGate(selectedSnapshot._id);
      const url = URL.createObjectURL(
        new Blob([JSON.stringify(value, null, 2)], { type: "application/json" }),
      );
      const link = document.createElement("a");
      link.href = url;
      link.download = `ket-qua-cong-phat-hanh-${new Date(selectedSnapshot.snapshot_at).toISOString().slice(0, 10)}.json`;
      link.click();
      URL.revokeObjectURL(url);
    } catch (reason) {
      setError(messageOf(reason));
    }
  };
  const monitorTabs = [
    { id: "overview", label: "Tổng quan" },
    ...(can("qualitygate.read")
      ? [{ id: "release", label: "Điều kiện và quyết định phát hành" }]
      : []),
    ...(can("testmonitor.read") ? [{ id: "actions", label: "Hành động kiểm soát" }] : []),
  ];
  const visibleView = monitorTabs.some((item) => item.id === activeView)
    ? activeView
    : monitorTabs[0].id;
  const canApproveRelease =
    can("qualitygate.decide") &&
    Boolean(gate?.overall_status) &&
    gate.overall_status !== "INSUFFICIENT_DATA" &&
    (!["FAIL", "MANUAL_REQUIRED"].includes(gate.overall_status) ||
      project.settings?.allow_quality_gate_override === true);
  return (
    <WorkspacePage
      title="Giám sát kiểm thử"
      actions={
        <>
          <ProjectCrumb projectId={project._id} />
          {can("testmonitor.snapshot.create") && (
            <button
              className="apple-button"
              type="button"
              disabled={!selectedPlanId}
              onClick={createSnapshot}
            >
              Lưu mốc giám sát
            </button>
          )}
        </>
      }
    >
      {dialog}
      {error && <ErrorState message={error} />}
      <Panel title="Phạm vi giám sát">
        <div className="grid gap-4 p-5 md:grid-cols-2">
          {can("testplan.read") && (
            <label className="field-label">
              Kế hoạch đã phê duyệt
              <select
                className="apple-input mt-2"
                value={selectedPlanId}
                onChange={(event) => {
                  setSelectedPlanId(event.target.value);
                  setSelectedSnapshot(null);
                }}
              >
                <option value="">Chọn kế hoạch</option>
                {plans.map((item) => (
                  <option key={item._id} value={item._id}>
                    {item.name}
                  </option>
                ))}
              </select>
            </label>
          )}
          <label className="field-label">
            Mốc giám sát
            <select
              className="apple-input mt-2"
              value={selectedSnapshot?._id || ""}
              onChange={(event) =>
                setSelectedSnapshot(
                  snapshots.find((item) => item._id === event.target.value) || null,
                )
              }
            >
              <option value="">Chọn mốc giám sát</option>
              {snapshots.map((item) => (
                <option key={item._id} value={item._id}>
                  {formatDate(item.snapshot_at)}
                </option>
              ))}
            </select>
          </label>
        </div>
      </Panel>
      {selectedSnapshot ? (
        <>
          <Panel title="Thông tin mốc giám sát">
            <div className="grid gap-x-6 gap-y-4 p-5 text-sm sm:grid-cols-2 xl:grid-cols-4">
              <div className="min-w-0">
                <p className="field-label">Kế hoạch</p>
                <p className="mt-2 break-words">
                  {plans.find((item) => item._id === selectedSnapshot.test_plan_id)?.name ||
                    "Kế hoạch kiểm thử"}
                </p>
              </div>
              <div>
                <p className="field-label">Thời điểm ghi nhận</p>
                <p className="mt-2">{formatDate(selectedSnapshot.snapshot_at)}</p>
              </div>
              <div>
                <p className="field-label">Phiên bản kế hoạch</p>
                <p className="mt-2">{selectedSnapshot.plan_revision}</p>
              </div>
              <div>
                <p className="field-label">Kết quả điều kiện phát hành</p>
                <div className="mt-2">
                  <QualityGateBadge
                    status={
                      selectedSnapshot.effective_quality_gate_status ||
                      selectedSnapshot.quality_gate_status
                    }
                  />
                </div>
              </div>
            </div>
          </Panel>
          <TestProgressBoard metrics={selectedSnapshot.metrics} />
          <SegmentedTabs
            label="Nội dung giám sát"
            value={visibleView}
            onChange={setActiveView}
            tabs={monitorTabs}
          />
          {visibleView === "overview" && (
            <div className="grid items-start gap-4 xl:grid-cols-2">
              <Panel title="Kế hoạch và thực tế">
                <PlanVsActualPanel snapshot={selectedSnapshot} />
              </Panel>
              <Panel title="Sai lệch và thay đổi cần rà soát">
                <DataTable
                  items={[
                    ...(selectedSnapshot.deviations || []),
                    ...(selectedSnapshot.blockers || []).map((item) => ({
                      type: "BLOCKER",
                      actual: item.title || "Có lỗi đang chặn phát hành",
                    })),
                  ]}
                  empty="Không có sai lệch hoặc trở ngại"
                  columns={[
                    { key: "type", label: "Loại", render: (item) => valueLabel(item.type) },
                    {
                      key: "planned",
                      label: "Kế hoạch",
                      render: (item) => displayDeviationValue(item.planned),
                    },
                    {
                      key: "actual",
                      label: "Thực tế",
                      render: (item) => displayDeviationValue(item.actual),
                    },
                    { key: "unit", label: "Đơn vị" },
                  ]}
                />
                <dl className="grid grid-cols-3 divide-x divide-border border-t border-border">
                  {[
                    ["Yêu cầu đã thay đổi", selectedSnapshot.metrics?.changed_requirements],
                    ["Ca kiểm thử lỗi thời", selectedSnapshot.metrics?.stale_testcases],
                    ["Đang chờ rà soát", selectedSnapshot.metrics?.impact_pending],
                  ].map(([label, value]) => (
                    <div className="min-w-0 px-3 py-3" key={label}>
                      <dt className="break-words text-xs leading-5 text-ink-muted">{label}</dt>
                      <dd className="mt-1 text-lg font-semibold text-ink">
                        {value ?? "Chưa có dữ liệu"}
                      </dd>
                    </div>
                  ))}
                </dl>
              </Panel>
            </div>
          )}
          {visibleView === "release" && (
            <div className="space-y-4">
              {can("qualitygate.read") && (
                <Panel
                  title="Điều kiện phát hành"
                  actions={
                    <QualityGateBadge
                      status={
                        selectedSnapshot.effective_quality_gate_status ||
                        selectedSnapshot.quality_gate_status
                      }
                    />
                  }
                >
                  <ExitCriteriaPanel
                    snapshot={selectedSnapshot}
                    canOverride={can("testmonitor.exit_criteria.override")}
                    onOverride={async (criterion) => {
                      await ask({
                        title: "Ghi nhận ngoại lệ điều kiện phát hành",
                        confirmLabel: "Ghi nhận",
                        fields: [
                          {
                            name: "status",
                            label: "Kết quả",
                            required: true,
                            options: ["PASS", "FAIL"].map((value) => ({
                              value,
                              label: value === "PASS" ? "Đạt" : "Không đạt",
                            })),
                          },
                          { name: "reason", label: "Lý do", required: true, multiline: true },
                        ],
                        onConfirm: async (answer) => {
                          try {
                            const value = await testingApi.overrideMonitoringCriterion(
                              selectedSnapshot._id,
                              {
                                expected_revision: selectedSnapshot.revision,
                                criterion_id: criterion.criterion_id,
                                ...answer,
                                evidence_refs: [],
                              },
                            );
                            setSelectedSnapshot(value);
                            await load();
                          } catch (reason) {
                            throw new Error(messageOf(reason));
                          }
                        },
                      });
                    }}
                  />
                </Panel>
              )}
              <Panel
                title="Quyết định phát hành"
                actions={
                  <div className="flex flex-wrap gap-2">
                    {can("qualitygate.read") && (
                      <button className="secondary-button" type="button" onClick={exportGate}>
                        Xuất bằng chứng
                      </button>
                    )}
                    {can("qualitygate.decide") && (
                      <>
                        <button
                          className="secondary-button"
                          type="button"
                          onClick={() => createDecision("BLOCK_RELEASE")}
                        >
                          Chặn phát hành
                        </button>
                        {canApproveRelease && (
                          <button
                            className="apple-button"
                            type="button"
                            onClick={() => createDecision("APPROVE_RELEASE")}
                          >
                            Phê duyệt phát hành
                          </button>
                        )}
                      </>
                    )}
                    {can("qualitygate.accept_risk") && (
                      <button
                        className="secondary-button"
                        type="button"
                        onClick={() => createDecision("ACCEPT_RISK")}
                      >
                        Chấp nhận rủi ro
                      </button>
                    )}
                  </div>
                }
              >
                <div className="space-y-5 p-5">
                  {can("qualitygate.decide") && gate?.overall_status === "INSUFFICIENT_DATA" && (
                    <p className="rounded-control border border-border bg-surface-quiet px-4 py-3 text-sm leading-6 text-ink-muted">
                      Chưa đủ dữ liệu để phê duyệt phát hành. Hoàn tất các lượt kiểm thử còn thiếu
                      rồi ghi nhận mốc mới.
                    </p>
                  )}
                  {can("qualitygate.decide") &&
                    ["FAIL", "MANUAL_REQUIRED"].includes(gate?.overall_status) &&
                    project.settings?.allow_quality_gate_override !== true && (
                      <p className="rounded-control border border-border bg-surface-quiet px-4 py-3 text-sm leading-6 text-ink-muted">
                        Điều kiện phát hành chưa đạt và dự án không cho phép ghi đè. Cần xử lý tiêu
                        chí chưa đạt trước khi phê duyệt.
                      </p>
                    )}
                  {can("qualitygate.read") && (
                    <DataTable
                      items={gate?.rules || []}
                      empty="Chưa có điều kiện phát hành"
                      getRowKey={(item) => item.criterion_id}
                      columns={[
                        { key: "criterion", label: "Tiêu chí" },
                        {
                          key: "status",
                          label: "Kết quả",
                          render: (item) => <QualityGateBadge status={item.status} />,
                        },
                        { key: "actual", label: "Thực tế" },
                        { key: "threshold", label: "Ngưỡng" },
                      ]}
                    />
                  )}
                  {can("qualitygate.read") && (
                    <DataTable
                      items={decisions.filter((item) => item.snapshot_id === selectedSnapshot._id)}
                      empty="Chưa có quyết định phát hành"
                      columns={[
                        {
                          key: "decision",
                          label: "Quyết định",
                          render: (item) => decisionLabels[item.decision] || item.decision,
                        },
                        { key: "reason", label: "Lý do" },
                        {
                          key: "decided_by",
                          label: "Người quyết định",
                          render: (item) => memberName(item.decided_by),
                        },
                        {
                          key: "decided_at",
                          label: "Thời điểm",
                          render: (item) => formatDate(item.decided_at),
                        },
                      ]}
                    />
                  )}
                </div>
              </Panel>
            </div>
          )}
          {visibleView === "actions" && can("testmonitor.read") && (
            <Panel title="Hành động kiểm soát">
              <TestControlActionPanel
                items={actions.filter((item) => item.snapshot_id === selectedSnapshot._id)}
                members={members}
                typeLabel={(item) =>
                  controlTypeLabels[item.action_type] || valueLabel(item.action_type || item.type)
                }
                canCreate={can("testmonitor.control.create")}
                canUpdate={can("testmonitor.control.update")}
                onCreate={createAction}
                onUpdate={async (item, status) => {
                  try {
                    await testingApi.updateControlAction(item._id, {
                      expected_revision: item.revision,
                      status,
                    });
                    await load();
                  } catch (reason) {
                    setError(messageOf(reason));
                  }
                }}
              />
            </Panel>
          )}
        </>
      ) : (
        <Panel title="Mốc giám sát">
          <p className="p-5 text-sm leading-6 text-ink-muted">
            {!can("testplan.read")
              ? "Bạn chưa được cấp quyền xem kế hoạch kiểm thử."
              : plans.length === 0
                ? "Chưa có kế hoạch kiểm thử được phê duyệt để theo dõi."
                : snapshots.length === 0
                  ? "Chưa có mốc giám sát cho kế hoạch này. Chọn kế hoạch ở phía trên để bắt đầu theo dõi."
                  : "Chọn một mốc giám sát ở phía trên để xem tiến độ và quyết định liên quan."}
          </p>
        </Panel>
      )}
    </WorkspacePage>
  );
}
