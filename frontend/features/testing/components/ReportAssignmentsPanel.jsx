"use client";

import { useEffect, useState } from "react";
import { Users } from "lucide-react";
import { testingApi } from "../services/testing.service";
import { ErrorState, LoadingState, Panel } from "./WorkspacePrimitives";

const statuses = {
  DRAFT: "Bản nháp",
  IN_REVIEW: "Đang rà soát",
  APPROVED: "Đã duyệt",
  PUBLISHED: "Đã phát hành",
  ARCHIVED: "Lưu trữ",
};

export default function ReportAssignmentsPanel({ project, members }) {
  const [rows, setRows] = useState([]);
  const [page, setPage] = useState(0);
  const [editing, setEditing] = useState(null);
  const [people, setPeople] = useState(null);
  const [reason, setReason] = useState("");
  const [error, setError] = useState("");
  const [notice, setNotice] = useState("");
  const [loading, setLoading] = useState(true);
  const [busy, setBusy] = useState(false);
  const [refresh, setRefresh] = useState(0);
  const id = (member) => member.user_id || member._id;
  const name = (value) => {
    const member = members.find((item) => id(item) === value);
    return (
      member?.user_label || member?.display_name || member?.name || member?.email || "Thành viên"
    );
  };
  const writers = members.filter((item) =>
    ["BA", "QA", "TESTER", "DEVELOPER"].includes(item.project_role),
  );
  useEffect(() => {
    let active = true;
    setLoading(true);
    testingApi
      .listReportAssignments(project._id, page * 50)
      .then((items) => {
        if (active) setRows(items);
      })
      .catch((failure) => {
        if (active) setError(failure.message || "Không thể tải phân công báo cáo.");
      })
      .finally(() => {
        if (active) setLoading(false);
      });
    return () => {
      active = false;
    };
  }, [project._id, page, refresh]);
  async function save(event) {
    event.preventDefault();
    setBusy(true);
    setError("");
    try {
      await testingApi.updateReportAssignments(editing._id, {
        expected_revision: editing.revision,
        participants: people,
        reason: reason.trim(),
      });
      setEditing(null);
      setPeople(null);
      setNotice("Đã lưu phân công. Báo cáo được đưa về bản nháp để rà soát lại.");
      setRefresh((value) => value + 1);
    } catch (failure) {
      setError(
        failure.code === "REPORT_REVISION_CONFLICT"
          ? "Báo cáo đã thay đổi. Đóng biểu mẫu và tải lại danh sách trước khi phân công."
          : failure.code === "REPORT_REVIEWER_MUST_BE_INDEPENDENT"
            ? "Người duyệt phải khác người tạo, người đã sửa nội dung và người cùng soạn."
            : failure.message || "Không thể lưu phân công. Các lựa chọn của bạn được giữ lại.",
      );
    } finally {
      setBusy(false);
    }
  }
  return (
    <Panel title="Phân công báo cáo">
      <div className="space-y-4 p-4">
        {error && <ErrorState message={error} />}
        {notice && (
          <p role="status" className="text-sm text-ink-muted">
            {notice}
          </p>
        )}
        {editing && people ? (
          <form onSubmit={save} className="space-y-4">
            <h3 className="font-medium">{editing.title}</h3>
            <div className="grid grid-cols-2 gap-4">
              <label className="text-sm">
                Người viết
                <select
                  className="apple-input mt-1"
                  required
                  value={people.owner_id}
                  onChange={(event) => setPeople({ ...people, owner_id: event.target.value })}
                >
                  <option value="">Chọn người viết</option>
                  {writers.map((member) => (
                    <option key={id(member)} value={id(member)}>
                      {name(id(member))}
                    </option>
                  ))}
                </select>
              </label>
              <label className="text-sm">
                Người duyệt
                <select
                  className="apple-input mt-1"
                  required
                  value={people.reviewer_id}
                  onChange={(event) => setPeople({ ...people, reviewer_id: event.target.value })}
                >
                  <option value="">Chọn người duyệt</option>
                  {members
                    .filter(
                      (member) =>
                        ["BA", "QA"].includes(member.project_role) &&
                        ![people.owner_id, ...people.editor_ids].includes(id(member)),
                    )
                    .map((member) => (
                      <option key={id(member)} value={id(member)}>
                        {name(id(member))}
                      </option>
                    ))}
                </select>
              </label>
            </div>
            <fieldset>
              <legend className="mb-2 text-sm font-medium">Người cùng soạn</legend>
              <div className="grid max-h-48 grid-cols-3 gap-3 overflow-y-auto">
                {writers
                  .filter((member) => id(member) !== people.owner_id)
                  .map((member) => (
                    <label key={id(member)} className="flex items-center gap-2 text-sm">
                      <input
                        type="checkbox"
                        checked={people.editor_ids.includes(id(member))}
                        onChange={(event) =>
                          setPeople({
                            ...people,
                            editor_ids: event.target.checked
                              ? [...people.editor_ids, id(member)]
                              : people.editor_ids.filter((value) => value !== id(member)),
                          })
                        }
                      />
                      {name(id(member))}
                    </label>
                  ))}
              </div>
            </fieldset>
            <p className="text-sm text-ink-muted">
              Người nhận:{" "}
              {people.recipients.map((recipient) => name(recipient.user_id)).join(", ") ||
                "Chưa phân công"}
            </p>
            <label className="block text-sm">
              Lý do thay đổi
              <textarea
                className="apple-input mt-1"
                required
                maxLength={3000}
                value={reason}
                onChange={(event) => setReason(event.target.value)}
              />
            </label>
            <div className="flex gap-3">
              <button className="apple-button" type="submit" disabled={busy || !reason.trim()}>
                Lưu phân công
              </button>
              <button
                className="secondary-button"
                type="button"
                disabled={busy}
                onClick={() => {
                  setEditing(null);
                  setPeople(null);
                }}
              >
                Đóng
              </button>
            </div>
          </form>
        ) : loading ? (
          <LoadingState />
        ) : (
          <>
            <div className="overflow-x-auto">
              <table className="w-full text-left text-sm">
                <thead>
                  <tr className="border-b border-border">
                    <th className="px-3 py-3">Báo cáo</th>
                    <th className="px-3 py-3">Người viết</th>
                    <th className="px-3 py-3">Người duyệt</th>
                    <th className="px-3 py-3">Trạng thái</th>
                    <th className="px-3 py-3">Thao tác</th>
                  </tr>
                </thead>
                <tbody>
                  {rows.map((row) => (
                    <tr key={row._id} className="border-b border-border">
                      <td className="max-w-80 break-words px-3 py-3">{row.title}</td>
                      <td className="px-3 py-3">{name(row.owner_id)}</td>
                      <td className="px-3 py-3">{name(row.reviewer_id)}</td>
                      <td className="px-3 py-3">{statuses[row.status]}</td>
                      <td className="px-3 py-3">
                        {["DRAFT", "IN_REVIEW", "APPROVED"].includes(row.status) && (
                          <button
                            className="icon-button h-9 w-9"
                            title="Phân công"
                            aria-label={`Phân công ${row.title}`}
                            onClick={() => {
                              setEditing(row);
                              setPeople({
                                owner_id: row.owner_id,
                                editor_ids: row.editor_ids || [],
                                reviewer_id: row.reviewer_id,
                                recipients: row.recipients || [],
                              });
                              setReason("");
                              setError("");
                              setNotice("");
                            }}
                          >
                            <Users size={17} />
                          </button>
                        )}
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
            {!rows.length && (
              <p className="text-sm text-ink-muted">Chưa có báo cáo để phân công.</p>
            )}
            <div className="flex justify-end gap-3">
              <button
                className="secondary-button"
                disabled={page === 0}
                onClick={() => setPage((value) => value - 1)}
              >
                Trước
              </button>
              <span className="self-center text-sm">Trang {page + 1}</span>
              <button
                className="secondary-button"
                disabled={rows.length < 50}
                onClick={() => setPage((value) => value + 1)}
              >
                Sau
              </button>
            </div>
          </>
        )}
      </div>
    </Panel>
  );
}
