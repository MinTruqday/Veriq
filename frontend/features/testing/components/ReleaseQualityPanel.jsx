"use client";
import { useCallback, useEffect, useState } from "react";
import DataTable from "./DataTable";
import { ErrorState, Panel, StatusPill, useActionDialog } from "./WorkspacePrimitives";
import { messageOf } from "../lib/testing";
import { testingApi } from "../services/testing.service";
import { runReleaseQualityAction } from "./releaseQualityActions.mjs";

export default function ReleaseQualityPanel({ project }) {
  const [items, setItems] = useState([]);
  const [selected, setSelected] = useState(null);
  const [releases, setReleases] = useState([]);
  const [builds, setBuilds] = useState([]);
  const [measurements, setMeasurements] = useState([]);
  const [monitoring, setMonitoring] = useState([]);
  const [members, setMembers] = useState([]);
  const [error, setError] = useState("");
  const { ask, dialog } = useActionDialog();
  const can = (permission) => project.current_permissions?.includes(permission);
  const runAction = async (operation, onSuccess) => {
    setError("");
    const result = await runReleaseQualityAction(operation);
    if (!result.ok) {
      setError(messageOf(result.error));
      return;
    }
    await onSuccess?.(result.value);
  };
  const load = useCallback(async () => {
    try {
      const permissions = new Set(project.current_permissions || []);
      const [
        result,
        releaseValues,
        buildValues,
        measurementValues,
        monitoringValues,
        memberValues,
      ] = await Promise.all([
        testingApi.listQualityEvaluations(project._id),
        permissions.has("release.read")
          ? testingApi.listReleases(project._id)
          : Promise.resolve([]),
        permissions.has("build.read") ? testingApi.listBuilds(project._id) : Promise.resolve([]),
        permissions.has("measurement.read")
          ? testingApi.listMeasurementSnapshots(project._id)
          : Promise.resolve({ items: [] }),
        permissions.has("testmonitor.read")
          ? testingApi.listMonitoringSnapshots(project._id)
          : Promise.resolve([]),
        permissions.has("project.members.read")
          ? testingApi.listMembers(project._id)
          : Promise.resolve([]),
      ]);
      setItems(result.items || []);
      setReleases(releaseValues);
      setBuilds(buildValues);
      setMeasurements(measurementValues.items || []);
      setMonitoring(monitoringValues || []);
      setMembers(memberValues.filter((item) => item.status === "ACTIVE"));
      if (selected?._id) setSelected(await testingApi.getQualityEvaluation(selected._id));
    } catch (reason) {
      setError(messageOf(reason));
    }
  }, [project._id, project.current_permissions, selected?._id]);
  useEffect(() => {
    void load();
  }, [load]);
  const create = async () => {
    await ask({
      title: "Tạo đánh giá chất lượng bản phát hành",
      confirmLabel: "Tạo đánh giá",
      fields: [
        {
          name: "release_id",
          label: "Bản phát hành",
          required: true,
          options: [
            { value: "", label: "Chọn bản phát hành" },
            ...releases.map((item) => ({ value: item._id, label: `${item.key} ${item.name}` })),
          ],
        },
        {
          name: "build_id",
          label: "Bản dựng",
          required: true,
          options: [
            { value: "", label: "Chọn bản dựng" },
            ...builds.map((item) => ({
              value: item._id,
              label: `${item.identifier} ${item.version}`,
            })),
          ],
        },
        {
          name: "monitoring_snapshot_id",
          label: "Ảnh chụp giám sát",
          required: true,
          options: [
            { value: "", label: "Chọn ảnh chụp" },
            ...monitoring.map((item) => ({
              value: item._id,
              label: `${item.name || (item.created_at ? new Date(item.created_at).toLocaleString() : "Ảnh chụp giám sát")} · ${item.effective_quality_gate_status || item.quality_gate_status || "Chưa đánh giá"}`,
            })),
          ],
        },
        {
          name: "measurement_snapshot_refs",
          label: "Ảnh chụp đo lường liên quan",
          multiple: true,
          options: measurements.map((item) => ({
            value: item._id,
            label:
              item.name ||
              (item.created_at ? new Date(item.created_at).toLocaleString() : "Ảnh chụp đo lường"),
          })),
          initialValue: [],
        },
        {
          name: "rationale",
          label: "Lập luận dựa trên bằng chứng",
          required: true,
          multiline: true,
        },
      ],
      onConfirm: async (answer) => {
        try {
          const value = await testingApi.createQualityEvaluation(project._id, {
            ...answer,
            idempotency_key: crypto.randomUUID(),
            measurement_snapshot_refs: answer.measurement_snapshot_refs || [],
            critical_risks: [],
            evidence_refs: [],
          });
          setSelected(value);
          await load();
        } catch (reason) {
          throw new Error(messageOf(reason));
        }
      },
    });
  };
  const act = async (action, extra = {}) => {
    await ask({
      title: extra.title || "Xác nhận đánh giá",
      confirmLabel: extra.confirmLabel || "Xác nhận",
      fields: extra.fields || [{ name: "note", label: "Ghi chú", multiline: true }],
      onConfirm: async (answer) => {
        try {
          setSelected(
            await action(selected._id, {
              expected_revision: selected.revision,
              ...answer,
              ...extra.payload,
            }),
          );
          await load();
        } catch (reason) {
          throw new Error(messageOf(reason));
        }
      },
    });
  };
  const createWaiver = async () => {
    await ask({
      title: "Tạo miễn trừ có thời hạn",
      confirmLabel: "Tạo miễn trừ",
      fields: [
        { name: "criterion_or_metric", label: "Chỉ số hoặc tiêu chí", required: true },
        { name: "actual", label: "Giá trị thực tế", required: true },
        { name: "threshold", label: "Ngưỡng", required: true },
        { name: "reason", label: "Lý do", required: true, multiline: true },
        { name: "risk", label: "Rủi ro", required: true, multiline: true },
        {
          name: "owner_id",
          label: "Người chịu trách nhiệm",
          required: true,
          options: [
            { value: "", label: "Chọn thành viên" },
            ...members.map((item) => ({
              value: item.user_id,
              label: item.user_label || item.email || "Thành viên",
            })),
          ],
        },
        { name: "expiry_at", label: "Thời điểm hết hạn", required: true, type: "datetime-local" },
        {
          name: "evidence_refs",
          label: "Tham chiếu bằng chứng cách nhau bởi dấu phẩy",
          required: true,
        },
      ],
      onConfirm: async (answer) => {
        try {
          setSelected(
            await testingApi.createQualityWaiver(selected._id, {
              ...answer,
              expected_revision: selected.revision,
              actual: Number.isNaN(Number(answer.actual)) ? answer.actual : Number(answer.actual),
              threshold: Number.isNaN(Number(answer.threshold))
                ? answer.threshold
                : Number(answer.threshold),
              expiry_at: new Date(answer.expiry_at).toISOString(),
              evidence_refs: answer.evidence_refs
                .split(",")
                .map((item) => item.trim())
                .filter(Boolean),
            }),
          );
          await load();
        } catch (reason) {
          throw new Error(messageOf(reason));
        }
      },
    });
  };
  return (
    <Panel
      title="Chất lượng bản phát hành"
      actions={
        can("qualityevaluation.create") &&
        can("release.read") &&
        can("build.read") &&
        can("testmonitor.read") ? (
          <button className="apple-button" type="button" onClick={create}>
            Tạo đánh giá
          </button>
        ) : null
      }
    >
      {dialog}
      {error && (
        <div className="p-4">
          <ErrorState message={error} />
        </div>
      )}
      <DataTable
        items={items}
        empty="Chưa có đánh giá chất lượng"
        columns={[
          {
            key: "release_id",
            label: "Bản phát hành",
            render: (item) => {
              const release = releases.find((value) => value._id === item.release_id);
              return release
                ? `${release.key} ${release.name}`
                : "Bản phát hành không còn khả dụng";
            },
          },
          {
            key: "build_id",
            label: "Bản dựng",
            render: (item) => {
              const build = builds.find((value) => value._id === item.build_id);
              return build ? `${build.identifier} ${build.version}` : "Bản dựng không còn khả dụng";
            },
          },
          {
            key: "quality_gate_status",
            label: "Điều kiện phát hành",
            render: (item) => <StatusPill value={item.quality_gate_status} />,
          },
          {
            key: "recommendation",
            label: "Khuyến nghị",
            render: (item) => (
              <StatusPill value={item.system_recommendation || item.recommendation} />
            ),
          },
          {
            key: "status",
            label: "Trạng thái",
            render: (item) => <StatusPill value={item.status} />,
          },
          {
            key: "action",
            label: "Thao tác",
            render: (item) => (
              <button
                className="secondary-button"
                type="button"
                onClick={() =>
                  runAction(
                    () => testingApi.getQualityEvaluation(item._id),
                    (evaluation) => setSelected(evaluation),
                  )
                }
              >
                Mở
              </button>
            ),
          },
        ]}
      />
      {selected && (
        <div className="space-y-4 border-t border-border p-5">
          <div className="flex flex-wrap items-start justify-between gap-3">
            <div>
              <p className="font-semibold">
                {selected.system_recommendation || selected.recommendation}
              </p>
              <p className="mt-1 max-w-3xl whitespace-pre-wrap text-sm">{selected.rationale}</p>
            </div>
            <div className="flex flex-wrap gap-2">
              {["DRAFT", "IN_REVIEW"].includes(selected.status) &&
                can("qualityevaluation.create") && (
                  <button className="secondary-button" type="button" onClick={createWaiver}>
                    Tạo miễn trừ
                  </button>
                )}
              {selected.status === "DRAFT" && can("qualityevaluation.review") && (
                <button
                  className="secondary-button"
                  type="button"
                  onClick={() => act(testingApi.submitQualityEvaluation)}
                >
                  Gửi rà soát
                </button>
              )}
              {selected.status === "IN_REVIEW" && can("qualityevaluation.review") && (
                <button
                  className="secondary-button"
                  type="button"
                  onClick={() =>
                    act(testingApi.reviewQualityEvaluation, {
                      title: "Rà soát đánh giá",
                      fields: [
                        {
                          name: "decision",
                          label: "Quyết định",
                          options: ["ENDORSE", "REQUEST_CHANGES"].map((value) => ({
                            value,
                            label: value === "ENDORSE" ? "Đồng ý" : "Yêu cầu chỉnh sửa",
                          })),
                        },
                        { name: "note", label: "Ghi chú", multiline: true },
                      ],
                    })
                  }
                >
                  Rà soát
                </button>
              )}
              {selected.status === "IN_REVIEW" && can("qualityevaluation.approve") && (
                <button
                  className="apple-button"
                  type="button"
                  onClick={() => act(testingApi.approveQualityEvaluation)}
                >
                  Phê duyệt
                </button>
              )}
            </div>
          </div>
          <div className="grid gap-3 md:grid-cols-3">
            <div>
              <p className="field-label">Cổng chất lượng đầu ra</p>
              <StatusPill value={selected.quality_gate_status} />
            </div>
            <div>
              <p className="field-label">Lỗi chưa xử lý</p>
              <p>{selected.unresolved_defects?.length || 0}</p>
            </div>
            <div>
              <p className="field-label">Rủi ro nghiêm trọng</p>
              <p>{selected.critical_risks?.length || 0}</p>
            </div>
          </div>
          <DataTable
            items={selected.waivers || []}
            empty="Không có miễn trừ"
            columns={[
              {
                key: "criterion_or_metric",
                label: "Chỉ số hoặc tiêu chí",
                render: (item) => item.criterion_or_metric || item.metric_or_criterion,
              },
              { key: "risk", label: "Rủi ro" },
              { key: "expiry", label: "Hết hạn" },
              {
                key: "status",
                label: "Trạng thái",
                render: (item) => <StatusPill value={item.status} />,
              },
              {
                key: "action",
                label: "Thao tác",
                render: (item) =>
                  item.status === "PENDING" && can("qualityevaluation.waiver.approve") ? (
                    <div className="flex gap-2">
                      <button
                        className="secondary-button"
                        type="button"
                        onClick={() =>
                          runAction(
                            () =>
                              testingApi.decideQualityWaiver(selected._id, item.waiver_id, {
                                expected_revision: selected.revision,
                                decision: "APPROVE",
                                note: "Đã đánh giá rủi ro",
                              }),
                            async (evaluation) => {
                              setSelected(evaluation);
                              await load();
                            },
                          )
                        }
                      >
                        Duyệt
                      </button>
                      <button
                        className="secondary-button"
                        type="button"
                        onClick={async () => {
                          await ask({
                            title: "Từ chối miễn trừ",
                            confirmLabel: "Từ chối",
                            fields: [
                              { name: "note", label: "Lý do", required: true, multiline: true },
                            ],
                            onConfirm: async (answer) => {
                              try {
                                setSelected(
                                  await testingApi.decideQualityWaiver(
                                    selected._id,
                                    item.waiver_id,
                                    {
                                      expected_revision: selected.revision,
                                      decision: "REJECT",
                                      note: answer.note,
                                    },
                                  ),
                                );
                                await load();
                              } catch (reason) {
                                throw new Error(messageOf(reason));
                              }
                            },
                          });
                        }}
                      >
                        Từ chối
                      </button>
                    </div>
                  ) : null,
              },
            ]}
          />
        </div>
      )}
    </Panel>
  );
}
