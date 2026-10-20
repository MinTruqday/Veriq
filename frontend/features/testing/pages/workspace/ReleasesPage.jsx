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

export default function ReleasesPage({ project }) {
  const { ask, dialog } = useActionDialog();
  const [releases, setReleases] = useState([]);
  const [error, setError] = useState("");
  const [loading, setLoading] = useState(true);
  const can = (permission) => project.current_permissions?.includes(permission);
  const load = useCallback(async () => {
    setLoading(true);
    try {
      setReleases(await testingApi.listReleases(project._id));
      setError("");
    } catch (reason) {
      setError(messageOf(reason));
    } finally {
      setLoading(false);
    }
  }, [project._id]);
  useEffect(() => {
    void load();
  }, [load]);
  const createRelease = async () => {
    const value = await ask({
      title: "Tạo bản phát hành",
      confirmLabel: "Tạo bản phát hành",
      fields: [
        { name: "key", label: "Mã", required: true },
        { name: "name", label: "Tên", required: true },
        { name: "version", label: "Phiên bản", required: true },
        { name: "planned_start_at", label: "Bắt đầu dự kiến", type: "date" },
        { name: "planned_end_at", label: "Kết thúc dự kiến", type: "date" },
        { name: "notes", label: "Ghi chú", multiline: true },
      ],
      onConfirm: async (value) => {
        await testingApi.createRelease(project._id, {
          ...value,
          key: value.key.trim(),
          name: value.name.trim(),
          version: value.version.trim(),
          planned_start_at: value.planned_start_at || null,
          planned_end_at: value.planned_end_at || null,
          notes: value.notes.trim(),
        });
        await load();
      },
    });
  };
  const transition = async (release, action) => {
    const value = await ask({
      title: action === "activate" ? "Kích hoạt bản phát hành" : "Đóng bản phát hành",
      confirmLabel: action === "activate" ? "Kích hoạt" : "Đóng bản phát hành",
      fields: [{ name: "reason", label: "Lý do", multiline: true, required: true }],
    });
    if (!value) return;
    try {
      const payload = { expected_revision: release.revision, reason: value.reason.trim() };
      if (action === "activate") await testingApi.activateRelease(release._id, payload);
      else await testingApi.closeRelease(release._id, payload);
      await load();
    } catch (reason) {
      setError(messageOf(reason));
    }
  };
  if (loading)
    return (
      <WorkspacePage title="Bản phát hành">
        <LoadingState />
      </WorkspacePage>
    );
  return (
    <WorkspacePage
      title="Bản phát hành"
      actions={
        can("release.create") ? (
          <button className="apple-button" type="button" onClick={createRelease}>
            <Plus size={16} />
            Tạo bản phát hành
          </button>
        ) : null
      }
    >
      {error && <ErrorState message={error} />}
      {error && releases.length === 0 ? (
        <Panel title="Danh sách bản phát hành">
          <div className="space-y-3 p-5">
            <p className="text-sm text-ink-muted">Chưa thể xác định danh sách bản phát hành</p>
            <button className="secondary-button" type="button" onClick={() => void load()}>
              Tải lại
            </button>
          </div>
        </Panel>
      ) : (
        <Panel title="Danh sách bản phát hành">
          <DataTable
            items={releases}
            empty="Chưa có bản phát hành"
            columns={[
              { key: "key", label: "Mã" },
              { key: "name", label: "Tên" },
              { key: "version", label: "Phiên bản" },
              {
                key: "status",
                label: "Trạng thái",
                render: (item) => <StatusPill value={item.status} />,
              },
              {
                key: "planned_end_at",
                label: "Kết thúc dự kiến",
                render: (item) =>
                  item.planned_end_at ? formatDate(item.planned_end_at) : "Chưa đặt",
              },
              ...(can("release.manage") || can("release.close")
                ? [
                    {
                      key: "actions",
                      label: "Thao tác",
                      hideWhenEmpty: true,
                      render: (item) =>
                        item.status === "PLANNED" && can("release.manage") ? (
                          <button
                            className="secondary-button"
                            type="button"
                            onClick={() => transition(item, "activate")}
                          >
                            Kích hoạt
                          </button>
                        ) : item.status === "ACTIVE" && can("release.close") ? (
                          <button
                            className="secondary-button"
                            type="button"
                            onClick={() => transition(item, "close")}
                          >
                            Đóng phát hành
                          </button>
                        ) : null,
                    },
                  ]
                : []),
            ]}
          />
        </Panel>
      )}
      {dialog}
    </WorkspacePage>
  );
}
