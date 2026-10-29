"use client";
import { useCallback, useEffect, useRef, useState } from "react";
import DataTable from "../../components/DataTable";
import ExitCriteriaPanel from "../../components/ExitCriteriaPanel";
import PlanVsActualPanel from "../../components/PlanVsActualPanel";
import QualityGateBadge from "../../components/QualityGateBadge";
import TestControlActionPanel from "../../components/TestControlActionPanel";
import TestProgressBoard from "../../components/TestProgressBoard";
import {
  ErrorState,
  InitialLoadState,
  Metric,
  Panel,
  ProjectCrumb,
  WorkspacePage,
  useActionDialog,
} from "../../components/WorkspacePrimitives";
import { messageOf, valueLabel } from "../../lib/testing";
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
  const { ask, dialog } = useActionDialog();
  const [plans, setPlans] = useState([]);
  const [members, setMembers] = useState([]);
  const [snapshots, setSnapshots] = useState([]);
  const [actions, setActions] = useState([]);
  const [gate, setGate] = useState(null);
  const [decisions, setDecisions] = useState([]);
  const [selectedPlanId, setSelectedPlanId] = useState("");
  const [selectedSnapshot, setSelectedSnapshot] = useState(null);
  const [error, setError] = useState("");
  const [initialLoading, setInitialLoading] = useState(true);
  const [initialLoadFailed, setInitialLoadFailed] = useState(false);
  const initialDataLoaded = useRef(false);
  const loadedProjectId = useRef(project._id);
  const can = (permission) => project.current_permissions?.includes(permission);
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
      title: "Tạo ảnh chụp giám sát",
      confirmLabel: "Tạo ảnh chụp",
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
          label: "Ưu tiên",
          required: true,
          options: ["CRITICAL", "HIGH", "MEDIUM", "LOW"].map((value) => ({
            value,
            label: valueLabel(value.toLowerCase()),
          })),
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
    if (decision === "APPROVE_RELEASE" && gate?.overall_status !== "PASS")
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
                  {new Date(item.snapshot_at).toLocaleString("vi-VN")}
                </option>
              ))}
            </select>
          </label>
        </div>
      </Panel>
      {selectedSnapshot ? (
        <>
          <Panel title="Thông tin mốc giám sát">
            <div className="grid gap-4 p-5 text-sm sm:grid-cols-2 lg:grid-cols-4">
              <div>
                <p className="field-label">Thời điểm ghi nhận</p>
                <p className="mt-2">
                  {new Date(selectedSnapshot.snapshot_at).toLocaleString("vi-VN")}
                </p>
              </div>
              <div>
                <p className="field-label">Phiên bản kế hoạch</p>
                <p className="mt-2">{selectedSnapshot.plan_revision}</p>
              </div>
              <div>
                <p className="field-label">Trạng thái cổng chất lượng</p>
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
          <Panel title="Kế hoạch và thực tế">
            <PlanVsActualPanel snapshot={selectedSnapshot} />
          </Panel>
          {can("qualitygate.read") && (
            <Panel
              title="Tiêu chí thoát"
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
                    title: "Ghi đè tiêu chí thoát",
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
            title="Quyết định chất lượng"
            actions={
              <div className="flex flex-wrap gap-2">
                <button className="secondary-button" type="button" onClick={exportGate}>
                  Xuất bằng chứng
                </button>
                {can("qualitygate.decide") && (
                  <>
                    <button
                      className="secondary-button"
                      type="button"
                      onClick={() => createDecision("BLOCK_RELEASE")}
                    >
                      Chặn phát hành
                    </button>
                    <button
                      className="apple-button"
                      type="button"
                      onClick={() => createDecision("APPROVE_RELEASE")}
                    >
                      Phê duyệt phát hành
                    </button>
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
              <div className="flex flex-wrap items-center justify-between gap-3 rounded-xl border border-border bg-surface-quiet p-4">
                <div>
                  <p className="field-label">Kết quả đánh giá</p>
                </div>
                <QualityGateBadge status={gate?.overall_status} />
              </div>
              <DataTable
                items={gate?.rules || []}
                empty="Mốc giám sát này chưa có tiêu chí phát hành"
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
              <DataTable
                items={decisions.filter((item) => item.snapshot_id === selectedSnapshot._id)}
                empty="Chưa có quyết định chất lượng"
                columns={[
                  {
                    key: "decision",
                    label: "Quyết định",
                    render: (item) => decisionLabels[item.decision] || item.decision,
                  },
                  { key: "reason", label: "Lý do" },
                  { key: "decided_by", label: "Người quyết định" },
                  {
                    key: "decided_at",
                    label: "Thời điểm",
                    render: (item) => new Date(item.decided_at).toLocaleString("vi-VN"),
                  },
                ]}
              />
            </div>
          </Panel>
          <Panel title="Sai lệch và trở ngại">
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
                { key: "type", label: "Loại" },
                { key: "planned", label: "Kế hoạch" },
                { key: "actual", label: "Thực tế" },
                { key: "unit", label: "Đơn vị" },
              ]}
            />
          </Panel>
          <Panel title="Việc cần rà soát sau thay đổi">
            <div className="grid gap-4 p-5 sm:grid-cols-2 xl:grid-cols-3">
              <Metric
                label="Yêu cầu đã thay đổi"
                value={selectedSnapshot.metrics?.changed_requirements || 0}
              />
              <Metric
                label="Ca kiểm thử lỗi thời"
                value={selectedSnapshot.metrics?.stale_testcases || 0}
              />
              <Metric
                label="Thay đổi đang chờ rà soát"
                value={selectedSnapshot.metrics?.impact_pending || 0}
              />
            </div>
          </Panel>
          {can("testmonitor.read") && (
            <Panel title="Hành động kiểm soát">
              <TestControlActionPanel
                items={actions.filter((item) => item.snapshot_id === selectedSnapshot._id)}
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
        <Panel title="Ảnh chụp giám sát">
          <p className="p-8 text-sm text-ink-muted">
            Chọn kế hoạch đã phê duyệt và tạo ảnh chụp đầu tiên
          </p>
        </Panel>
      )}
    </WorkspacePage>
  );
}
