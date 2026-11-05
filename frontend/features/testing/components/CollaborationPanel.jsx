"use client";
import { useCallback, useEffect, useRef, useState } from "react";
import { ErrorState, Panel, useActionDialog } from "./WorkspacePrimitives";
import { testingApi } from "../services/testing.service";
import { messageOf } from "../lib/testing";

export default function CollaborationPanel({ project, artifactType, artifactId, onResolved }) {
  const { ask, dialog } = useActionDialog();
  const clientId = useRef(`workspace-${crypto.randomUUID()}`);
  const [presence, setPresence] = useState([]);
  const [conflicts, setConflicts] = useState([]);
  const [error, setError] = useState("");
  const canPresence = project.current_permissions?.includes("collaboration.presence.read");
  const canResolve = project.current_permissions?.includes("collaboration.conflict.resolve");
  const refresh = useCallback(async () => {
    if (!canPresence || !artifactId) return;
    try {
      await testingApi.updateCollaborationPresence(project._id, {
        artifact_type: artifactType,
        artifact_id: artifactId,
        client_id: clientId.current,
      });
      const [active, conflictValues] = await Promise.all([
        testingApi.listCollaborationPresence(project._id, artifactType, artifactId),
        canResolve ? testingApi.listCollaborationConflicts(project._id) : Promise.resolve([]),
      ]);
      setPresence(active);
      setConflicts(
        conflictValues.filter(
          (item) =>
            item.artifact_type === artifactType &&
            item.artifact_id === artifactId &&
            item.status === "OPEN",
        ),
      );
      setError("");
    } catch (reason) {
      setError(messageOf(reason));
    }
  }, [artifactId, artifactType, canPresence, canResolve, project._id]);
  useEffect(() => {
    void refresh();
    const timer = window.setInterval(() => void refresh(), 20000);
    return () => window.clearInterval(timer);
  }, [refresh]);
  const resolve = async (conflict) => {
    const answer = await ask({
      title: "Giải quyết xung đột chỉnh sửa",
      description: "Bản nháp đã được cập nhật ở nơi khác. Chọn nội dung cần được giữ lại.",
      confirmLabel: "Xác nhận phương án",
      fields: [
        {
          name: "resolution",
          label: "Phương án",
          required: true,
          initialValue: "KEEP_CURRENT",
          options: [
            { value: "KEEP_CURRENT", label: "Giữ nội dung hiện tại" },
            { value: "APPLY_INCOMING", label: "Áp dụng nội dung đang chờ" },
          ],
        },
        { name: "reason", label: "Lý do", required: true, multiline: true },
      ],
    });
    if (!answer) return;
    try {
      await testingApi.resolveCollaborationConflict(project._id, conflict._id, {
        expected_revision: conflict.current_revision,
        resolution: answer.resolution,
        reason: answer.reason.trim(),
      });
      await onResolved?.();
      await refresh();
    } catch (reason) {
      setError(messageOf(reason));
    }
  };
  if (!canPresence || !artifactId) return null;
  return (
    <Panel title="Cộng tác trên bản nháp">
      <div className="space-y-4 p-5">
        {error && <ErrorState message={error} />}
        <div>
          <p className="field-label">Đang mở bản nháp</p>
          <div className="mt-2 flex flex-wrap gap-2">
            {presence.map((item) => (
              <span className="rounded-full border border-border px-3 py-1 text-xs" key={item._id}>
                {item.user_email}
              </span>
            ))}
          </div>
        </div>
        {conflicts.length > 0 && (
          <div className="space-y-2 border-t border-border pt-4">
            <p className="font-medium">Xung đột cần rà soát</p>
            {conflicts.map((item) => (
              <div
                className="flex flex-wrap items-center justify-between gap-3 rounded-xl border border-border p-3"
                key={item._id}
              >
                <p className="text-sm">Nội dung đã thay đổi kể từ lần mở bản nháp này.</p>
                <button className="secondary-button" type="button" onClick={() => resolve(item)}>
                  Giải quyết xung đột
                </button>
              </div>
            ))}
          </div>
        )}
      </div>
      {dialog}
    </Panel>
  );
}
