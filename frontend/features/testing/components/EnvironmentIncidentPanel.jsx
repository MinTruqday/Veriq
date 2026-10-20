"use client";
import { useCallback, useEffect, useState } from "react";
import DataTable from "./DataTable";
import { ErrorState, Panel, StatusPill, useActionDialog } from "./WorkspacePrimitives";
import { messageOf } from "../lib/testing";
import { testingApi } from "../services/testing.service";

export default function EnvironmentIncidentPanel({ project }) {
  const [items, setItems] = useState([]);
  const [environments, setEnvironments] = useState([]);
  const [builds, setBuilds] = useState([]);
  const [runs, setRuns] = useState([]);
  const [members, setMembers] = useState([]);
  const [error, setError] = useState("");
  const { ask, dialog } = useActionDialog();
  const can = (permission) => project.current_permissions?.includes(permission);
  const load = useCallback(async () => {
    try {
      const permissions = new Set(project.current_permissions || []);
      const [result, environmentValues, buildValues, runValues, memberValues] = await Promise.all([
        testingApi.listEnvironmentIncidents(project._id),
        permissions.has("environment.read")
          ? testingApi.listEnvironments(project._id)
          : Promise.resolve([]),
        permissions.has("build.read") ? testingApi.listBuilds(project._id) : Promise.resolve([]),
        permissions.has("testrun.read") ? testingApi.listRuns(project._id) : Promise.resolve([]),
        permissions.has("project.members.read")
          ? testingApi.listMembers(project._id)
          : Promise.resolve([]),
      ]);
      setItems(result.items || []);
      setEnvironments(environmentValues);
      setBuilds(buildValues);
      setRuns(runValues);
      setMembers(memberValues.filter((item) => item.status === "ACTIVE"));
    } catch (reason) {
      setError(messageOf(reason));
    }
  }, [project._id, project.current_permissions]);
  useEffect(() => {
    void load();
  }, [load]);
  const create = async () => {
    const answer = await ask({
      title: "Ghi nhận sự cố môi trường",
      confirmLabel: "Ghi nhận",
      fields: [
        {
          name: "environment_id",
          label: "Môi trường",
          required: true,
          options: [
            { value: "", label: "Chọn môi trường" },
            ...environments.map((item) => ({ value: item._id, label: item.name })),
          ],
        },
        ...(can("build.read")
          ? [
              {
                name: "build_id",
                label: "Bản dựng",
                options: [
                  { value: "", label: "Không gắn bản dựng" },
                  ...builds.map((item) => ({
                    value: item._id,
                    label: `${item.identifier} ${item.version}`,
                  })),
                ],
              },
            ]
          : []),
        {
          name: "severity",
          label: "Mức độ",
          options: ["BLOCKER", "CRITICAL", "MAJOR", "MINOR"].map((value) => ({
            value,
            label: value,
          })),
        },
        {
          name: "type",
          label: "Loại",
          options: [
            "UNAVAILABLE",
            "DEPLOYMENT_FAILURE",
            "TEST_DATA_FAILURE",
            "NETWORK",
            "DEPENDENCY",
            "CONFIGURATION",
            "CAPACITY",
            "CERTIFICATE",
            "ACCESS",
            "OTHER",
          ].map((value) => ({ value, label: value })),
        },
        { name: "description", label: "Mô tả", required: true, multiline: true },
        ...(can("testrun.read")
          ? [
              {
                name: "affected_run_ids",
                label: "Mã lần chạy bị ảnh hưởng, phân cách bằng dấu phẩy",
                initialValue: runs
                  .filter((item) => item.status === "IN_PROGRESS")
                  .map((item) => item._id)
                  .join(","),
              },
            ]
          : []),
        {
          name: "owner_id",
          label: "Phụ trách",
          required: true,
          options: [
            { value: "", label: "Chọn thành viên" },
            ...members.map((item) => ({
              value: item.user_id,
              label: item.user_label || item.email || item.user_id,
            })),
          ],
        },
      ],
    });
    if (!answer) return;
    try {
      await testingApi.createEnvironmentIncident(project._id, {
        ...answer,
        idempotency_key: crypto.randomUUID(),
        build_id: answer.build_id || null,
        observed_at: new Date().toISOString(),
        affected_run_ids: String(answer.affected_run_ids || "")
          .split(",")
          .map((item) => item.trim())
          .filter(Boolean),
        evidence_refs: [],
      });
      await load();
    } catch (reason) {
      setError(messageOf(reason));
    }
  };
  const transition = async (item, status) => {
    const answer = await ask({
      title: `Chuyển incident sang ${status}`,
      confirmLabel: "Chuyển",
      fields: [
        {
          name: "resolution",
          label: "Kết quả xử lý",
          required: ["RESOLVED", "CLOSED"].includes(status),
          multiline: true,
        },
      ],
    });
    if (!answer) return;
    try {
      await testingApi.transitionEnvironmentIncident(
        item._id,
        { expected_revision: item.revision, status, resolution: answer.resolution },
        status === "CLOSED",
      );
      await load();
    } catch (reason) {
      setError(messageOf(reason));
    }
  };
  return (
    <Panel
      title="Sự cố môi trường"
      actions={
        can("environmentincident.create") &&
        can("environment.read") &&
        can("project.members.read") ? (
          <button className="apple-button" type="button" onClick={create}>
            Ghi nhận incident
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
        empty="Chưa có sự cố môi trường"
        columns={[
          { key: "incident_key", label: "Mã" },
          {
            key: "severity",
            label: "Mức độ",
            render: (item) => <StatusPill value={item.severity} />,
          },
          { key: "type", label: "Loại" },
          { key: "description", label: "Mô tả" },
          {
            key: "status",
            label: "Trạng thái",
            render: (item) => <StatusPill value={item.status} />,
          },
          {
            key: "downtime",
            label: "Gián đoạn",
            render: (item) => (item.downtime === null ? "Đang tính" : `${item.downtime} giây`),
          },
          {
            key: "action",
            label: "Thao tác",
            render: (item) =>
              can("environmentincident.update") && item.status === "OPEN" ? (
                <button
                  className="secondary-button"
                  type="button"
                  onClick={() => transition(item, "INVESTIGATING")}
                >
                  Điều tra
                </button>
              ) : can("environmentincident.update") && item.status === "INVESTIGATING" ? (
                <button
                  className="secondary-button"
                  type="button"
                  onClick={() => transition(item, "MITIGATED")}
                >
                  Đã giảm thiểu
                </button>
              ) : can("environmentincident.update") && item.status === "MITIGATED" ? (
                <button
                  className="secondary-button"
                  type="button"
                  onClick={() => transition(item, "RESOLVED")}
                >
                  Xử lý xong
                </button>
              ) : can("environmentincident.close") && item.status === "RESOLVED" ? (
                <button
                  className="secondary-button"
                  type="button"
                  onClick={() => transition(item, "CLOSED")}
                >
                  Đóng
                </button>
              ) : null,
          },
        ]}
      />
    </Panel>
  );
}
