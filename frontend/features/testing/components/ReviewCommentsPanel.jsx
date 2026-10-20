"use client";

import { useCallback, useEffect, useState } from "react";
import { docText, formatDate, messageOf, textDoc } from "../lib/testing";
import { testingApi } from "../services/testing.service";
import { ErrorState, Panel, StatusPill } from "./WorkspacePrimitives";

export default function ReviewCommentsPanel({
  projectId,
  artifactType,
  artifactId,
  title,
  permissions = [],
  currentUserId,
}) {
  const [items, setItems] = useState([]);
  const [body, setBody] = useState("");
  const [status, setStatus] = useState("OPEN");
  const [error, setError] = useState("");
  const [saving, setSaving] = useState(false);
  const canRead = permissions.includes("comment.read");
  const canCreate = permissions.includes("comment.create");
  const canModerate = permissions.includes("comment.moderate");
  const canUpdateOwn = permissions.includes("comment.update_own");
  const load = useCallback(async () => {
    if (!artifactId || !canRead) return;
    try {
      const query = new URLSearchParams({
        artifact_type: artifactType,
        artifact_id: artifactId,
        status,
      });
      setItems(await testingApi.listReviewComments(projectId, query.toString()));
      setError("");
    } catch (reason) {
      setError(messageOf(reason));
    }
  }, [artifactId, artifactType, canRead, projectId, status]);
  useEffect(() => {
    if (!canRead) return undefined;
    void load();
  }, [canRead, load]);
  const create = async (event) => {
    event.preventDefault();
    const value = body.trim();
    if (!value) return;
    setSaving(true);
    try {
      await testingApi.createReviewComment(projectId, {
        artifact_type: artifactType,
        artifact_id: artifactId,
        body_doc: textDoc(value),
      });
      setBody("");
      setStatus("OPEN");
      await load();
    } catch (reason) {
      setError(messageOf(reason));
    } finally {
      setSaving(false);
    }
  };
  const transition = async (item) => {
    try {
      if (item.status === "OPEN") await testingApi.resolveReviewComment(item._id);
      else await testingApi.reopenReviewComment(item._id);
      await load();
    } catch (reason) {
      setError(messageOf(reason));
    }
  };
  if (!canRead || !artifactId) return null;
  return (
    <Panel title={title || "Nhận xét rà soát"}>
      <div className="space-y-4 p-5">
        {error && <ErrorState message={error} />}
        <label className="grid max-w-xs gap-1 text-xs font-semibold text-ink-muted">
          Trạng thái nhận xét
          <select
            className="apple-input"
            value={status}
            onChange={(event) => setStatus(event.target.value)}
          >
            <option value="OPEN">Đang mở</option>
            <option value="RESOLVED">Đã xử lý</option>
          </select>
        </label>
        {items.length ? (
          <ul className="divide-y divide-border rounded-xl border border-border">
            {items.map((item) => (
              <li className="space-y-3 p-4" key={item._id}>
                <div className="flex flex-wrap items-center justify-between gap-3">
                  <div className="flex flex-wrap items-center gap-2">
                    <StatusPill value={item.status} />
                    <span className="text-[11px] text-ink-faint">
                      {formatDate(item.created_at)}
                    </span>
                  </div>
                  {(canModerate || (canUpdateOwn && item.author_id === currentUserId)) && (
                    <button
                      className="secondary-button"
                      type="button"
                      onClick={() => transition(item)}
                    >
                      {item.status === "OPEN" ? "Đánh dấu đã xử lý" : "Mở lại"}
                    </button>
                  )}
                </div>
                <p className="whitespace-pre-wrap text-[13px] leading-6">
                  {docText(item.body_doc) || "Nhận xét không có nội dung"}
                </p>
              </li>
            ))}
          </ul>
        ) : (
          <p className="text-[13px] text-ink-muted">Chưa có nhận xét rà soát</p>
        )}
        {canCreate && (
          <form className="flex flex-col gap-3 sm:flex-row" onSubmit={create}>
            <textarea
              aria-label="Nội dung nhận xét"
              className="apple-input min-h-24 flex-1"
              required
              value={body}
              onChange={(event) => setBody(event.target.value)}
              placeholder="Nhập nhận xét có thể kiểm chứng"
            />
            <button className="apple-button self-end" type="submit" disabled={saving}>
              {saving ? "Đang lưu" : "Thêm nhận xét"}
            </button>
          </form>
        )}
      </div>
    </Panel>
  );
}
