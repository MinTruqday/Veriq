"use client";
import { useCallback, useEffect, useState } from "react";
import { platformApi } from "@/features/authentication/services/platform.service";
import DataTable from "./DataTable";
import {
  ErrorState,
  LoadingState,
  Panel,
  StatusPill,
  useActionDialog,
} from "./WorkspacePrimitives";
import { Pagination } from "@/shared/components/ui/Pagination";
import { formatDate, messageOf, valueLabel } from "../lib/testing";

export default function PlatformUsersPanel() {
  const { ask, dialog } = useActionDialog();
  const [users, setUsers] = useState([]);
  const [query, setQuery] = useState("");
  const [selectedId, setSelectedId] = useState("");
  const [detail, setDetail] = useState(null);
  const [sessions, setSessions] = useState([]);
  const [memberships, setMemberships] = useState([]);
  const [audit, setAudit] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");
  const [page, setPage] = useState(1);
  const pageSize = 20;

  const loadUsers = useCallback(async (search = "") => {
    setLoading(true);
    setError("");
    setPage(1);
    try {
      setUsers(await platformApi.listUsers(search));
    } catch (reason) {
      setError(messageOf(reason));
    } finally {
      setLoading(false);
    }
  }, []);

  const loadDetail = useCallback(async (id) => {
    if (!id) return;
    setError("");
    try {
      const [user, activeSessions, projectMemberships, events] = await Promise.all([
        platformApi.getUser(id),
        platformApi.listSessions(id),
        platformApi.listMemberships(id),
        platformApi.listUserAudit(id),
      ]);
      setDetail(user);
      setSessions(activeSessions);
      setMemberships(projectMemberships);
      setAudit(events);
    } catch (reason) {
      setError(messageOf(reason));
    }
  }, []);

  useEffect(() => {
    void loadUsers();
  }, [loadUsers]);

  useEffect(() => {
    void loadDetail(selectedId);
  }, [loadDetail, selectedId]);

  const reasonFor = async (title, description, confirmLabel) => {
    const result = await ask({
      title,
      description,
      confirmLabel,
      fields: [
        {
          name: "reason",
          label: "Lý do",
          required: true,
          multiline: true,
          autoFocus: true,
        },
      ],
    });
    return result?.reason || "";
  };

  const mutate = async (title, description, confirmLabel, action) => {
    const reason = await reasonFor(title, description, confirmLabel);
    if (!reason) return;
    setError("");
    try {
      await action(reason);
      await Promise.all([loadUsers(query), loadDetail(selectedId)]);
    } catch (value) {
      setError(messageOf(value));
    }
  };

  return (
    <div className="space-y-5">
      {error && <ErrorState message={error} />}
      <Panel
        title="Tài khoản hệ thống"
        actions={
          <div className="flex flex-wrap gap-2">
            <button
              className="apple-button"
              type="button"
              onClick={async () => {
                const answer = await ask({
                  title: "Tạo tài khoản hệ thống",
                  description: "Người dùng sẽ nhận quy trình đặt mật khẩu riêng",
                  confirmLabel: "Tạo và gửi lời mời",
                  fields: [
                    { name: "email", label: "Email", required: true, autoFocus: true },
                    { name: "full_name", label: "Họ tên", required: true },
                    { name: "slug", label: "Tên đăng nhập", required: true },
                    { name: "reason", label: "Lý do", required: true, multiline: true },
                  ],
                });
                if (!answer) return;
                try {
                  await platformApi.createUser(answer);
                  await loadUsers(query);
                } catch (reason) {
                  setError(messageOf(reason));
                }
              }}
            >
              Tạo tài khoản
            </button>
            <button
              className="secondary-button"
              type="button"
              onClick={async () => {
                const answer = await ask({
                  title: "Thao tác tài khoản hàng loạt",
                  description: "Nhập mỗi mã tài khoản trên một dòng hoặc phân tách bằng dấu phẩy",
                  confirmLabel: "Tạo bản xem trước",
                  fields: [
                    {
                      name: "action",
                      label: "Thao tác",
                      required: true,
                      options: [
                        { value: "DISABLE", label: "Vô hiệu hóa" },
                        { value: "INVITE", label: "Gửi lại lời mời" },
                        { value: "REVOKE_SESSIONS", label: "Thu hồi phiên" },
                      ],
                    },
                    { name: "user_ids", label: "Mã tài khoản", required: true, multiline: true },
                    { name: "reason", label: "Lý do", required: true, multiline: true },
                  ],
                });
                if (!answer) return;
                try {
                  const userIds = answer.user_ids
                    .split(/[\s,]+/)
                    .map((value) => value.trim())
                    .filter(Boolean);
                  const preview = await platformApi.previewBulkUsers(
                    answer.action,
                    userIds,
                    answer.reason,
                  );
                  const confirmation = await ask({
                    title: "Xác nhận thao tác hàng loạt",
                    description: `${preview.user_ids.length} tài khoản hợp lệ và ${preview.missing_user_ids.length} mã không tồn tại`,
                    confirmLabel: "Thực hiện",
                    danger: answer.action === "DISABLE",
                  });
                  if (!confirmation) return;
                  await platformApi.confirmBulkUsers(preview._id);
                  await loadUsers(query);
                } catch (reason) {
                  setError(messageOf(reason));
                }
              }}
            >
              Thao tác hàng loạt
            </button>
            <form
              className="flex min-w-0 flex-wrap gap-2 sm:flex-nowrap"
              onSubmit={(event) => {
                event.preventDefault();
                void loadUsers(query);
              }}
            >
              <input
                className="apple-input min-w-0 w-full sm:w-72"
                aria-label="Tìm tài khoản"
                value={query}
                onChange={(event) => setQuery(event.target.value)}
                placeholder="Email tên hoặc tên đăng nhập"
              />
              <button className="secondary-button shrink-0" type="submit">
                Tìm
              </button>
            </form>
          </div>
        }
      >
        {loading ? (
          <div className="p-5">
            <LoadingState />
          </div>
        ) : (
          <DataTable
            items={users.slice((page - 1) * pageSize, page * pageSize)}
            empty="Không có tài khoản phù hợp"
            columns={[
              { key: "email", label: "Email" },
              { key: "full_name", label: "Tên" },
              {
                key: "system_role",
                label: "Vai trò hệ thống",
                render: (item) => valueLabel(item.system_role),
              },
              {
                key: "is_active",
                label: "Trạng thái",
                render: (item) => <StatusPill value={item.is_active ? "ACTIVE" : "DISABLED"} />,
              },
              {
                key: "open",
                label: "Thao tác",
                render: (item) => (
                  <button
                    className="secondary-button"
                    type="button"
                    onClick={() => setSelectedId(item._id)}
                  >
                    Xem chi tiết
                  </button>
                ),
              },
            ]}
          />
        )}
        {!loading && (
          <Pagination page={page} pageSize={pageSize} total={users.length} onChange={setPage} />
        )}
      </Panel>

      {detail && (
        <>
          <Panel title={`Chi tiết ${detail.email}`}>
            <div className="grid gap-4 p-5 md:grid-cols-2 xl:grid-cols-4">
              <div>
                <p className="field-label">Tên</p>
                <p>{detail.full_name}</p>
              </div>
              <div>
                <p className="field-label">Vai trò hệ thống</p>
                <p>{valueLabel(detail.system_role)}</p>
              </div>
              <div>
                <p className="field-label">Trạng thái</p>
                <p>{valueLabel(detail.account_status)}</p>
              </div>
              <div>
                <p className="field-label">Phiên đang hoạt động</p>
                <p>{detail.active_session_count}</p>
              </div>
            </div>
            <details className="border-t border-border">
              <summary className="cursor-pointer px-5 py-4 text-[13px] font-semibold text-ink">
                Thao tác tài khoản
              </summary>
              <div className="grid gap-2 border-t border-border p-5 sm:grid-cols-2 xl:grid-cols-3">
                <button
                  className="secondary-button"
                  type="button"
                  onClick={async () => {
                    const answer = await ask({
                      title: "Cập nhật hồ sơ tài khoản",
                      confirmLabel: "Lưu",
                      fields: [
                        {
                          name: "full_name",
                          label: "Họ tên",
                          required: true,
                          initialValue: detail.full_name,
                        },
                        {
                          name: "slug",
                          label: "Tên đăng nhập",
                          required: true,
                          initialValue: detail.slug,
                        },
                        { name: "reason", label: "Lý do", required: true, multiline: true },
                      ],
                    });
                    if (!answer) return;
                    try {
                      await platformApi.updateProfile(detail._id, answer);
                      await Promise.all([loadUsers(query), loadDetail(detail._id)]);
                    } catch (reason) {
                      setError(messageOf(reason));
                    }
                  }}
                >
                  Sửa hồ sơ
                </button>
                {detail.account_status === "ACTIVE" ? (
                  <>
                    <button
                      className="secondary-button"
                      type="button"
                      onClick={() =>
                        mutate(
                          "Khóa tài khoản",
                          "Tài khoản sẽ mất quyền truy cập ngay lập tức",
                          "Khóa",
                          (reason) => platformApi.lockUser(detail._id, reason),
                        )
                      }
                    >
                      Khóa
                    </button>
                    <button
                      className="secondary-button"
                      type="button"
                      onClick={() =>
                        mutate(
                          "Vô hiệu hóa tài khoản",
                          "Toàn bộ phiên đăng nhập sẽ bị thu hồi",
                          "Vô hiệu hóa",
                          (reason) => platformApi.disableUser(detail._id, reason),
                        )
                      }
                    >
                      Vô hiệu hóa
                    </button>
                  </>
                ) : (
                  <button
                    className="secondary-button"
                    type="button"
                    onClick={() =>
                      mutate(
                        detail.account_status === "LOCKED"
                          ? "Mở khóa tài khoản"
                          : "Kích hoạt tài khoản",
                        "Tài khoản sẽ được phép đăng nhập trở lại",
                        detail.account_status === "LOCKED" ? "Mở khóa" : "Kích hoạt",
                        (reason) =>
                          detail.account_status === "LOCKED"
                            ? platformApi.unlockUser(detail._id, reason)
                            : platformApi.enableUser(detail._id, reason),
                      )
                    }
                  >
                    {detail.account_status === "LOCKED" ? "Mở khóa" : "Kích hoạt"}
                  </button>
                )}
                <button
                  className="secondary-button"
                  type="button"
                  onClick={() =>
                    mutate(
                      "Buộc đặt lại mật khẩu",
                      "Toàn bộ phiên cũ sẽ bị thu hồi và quy trình khôi phục sẽ được gửi",
                      "Khởi tạo",
                      (reason) => platformApi.forcePasswordReset(detail._id, reason),
                    )
                  }
                >
                  Buộc đặt lại mật khẩu
                </button>
                <button
                  className="secondary-button"
                  type="button"
                  onClick={() =>
                    mutate(
                      "Gửi lại quy trình kích hoạt",
                      "Hệ thống sẽ gửi lại hướng dẫn kích hoạt và đặt mật khẩu",
                      "Gửi",
                      (reason) => platformApi.resendVerification(detail._id, reason),
                    )
                  }
                >
                  Gửi lại kích hoạt
                </button>
                <button
                  className="secondary-button"
                  type="button"
                  onClick={() =>
                    mutate(
                      "Đặt lại passkey",
                      "Toàn bộ passkey và phiên đăng nhập của tài khoản sẽ bị thu hồi",
                      "Đặt lại",
                      (reason) => platformApi.resetPasskeys(detail._id, reason),
                    )
                  }
                >
                  Đặt lại passkey
                </button>
                <button
                  className="secondary-button"
                  type="button"
                  onClick={() =>
                    mutate(
                      detail.system_role === "ADMIN" ? "Hạ quyền quản trị" : "Cấp quyền quản trị",
                      "Thay đổi có hiệu lực sau khi toàn bộ phiên hiện tại bị thu hồi",
                      "Xác nhận",
                      (reason) =>
                        platformApi.updateSystemRole(
                          detail._id,
                          detail.system_role === "ADMIN" ? "USER" : "ADMIN",
                          reason,
                        ),
                    )
                  }
                >
                  {detail.system_role === "ADMIN" ? "Hạ xuống người dùng" : "Cấp quyền quản trị"}
                </button>
                <button
                  className="secondary-button"
                  type="button"
                  onClick={async () => {
                    const reason = await reasonFor(
                      "Thu hồi toàn bộ phiên",
                      "Tài khoản sẽ phải đăng nhập lại trên mọi thiết bị",
                      "Thu hồi",
                    );
                    if (!reason) return;
                    try {
                      await platformApi.revokeAllSessions(detail._id);
                      await loadDetail(detail._id);
                    } catch (value) {
                      setError(messageOf(value));
                    }
                  }}
                >
                  Thu hồi mọi phiên
                </button>
                <button
                  className="danger-button"
                  type="button"
                  onClick={async () => {
                    const answer = await ask({
                      title: "Ẩn danh và xóa tài khoản",
                      description: `Nhập chính xác ${detail.email} để xác nhận`,
                      confirmLabel: "Xóa tài khoản",
                      danger: true,
                      fields: [
                        { name: "confirmation", label: "Email xác nhận", required: true },
                        { name: "reason", label: "Lý do", required: true, multiline: true },
                      ],
                    });
                    if (!answer) return;
                    try {
                      await platformApi.deleteUser(detail._id, answer.confirmation, answer.reason);
                      setSelectedId("");
                      setDetail(null);
                      await loadUsers(query);
                    } catch (reason) {
                      setError(messageOf(reason));
                    }
                  }}
                >
                  Xóa và ẩn danh
                </button>
              </div>
            </details>
          </Panel>

          <Panel title="Phiên đăng nhập">
            <DataTable
              items={sessions}
              empty="Không có phiên đăng nhập"
              columns={[
                { key: "_id", label: "Mã phiên" },
                { key: "ip", label: "Địa chỉ IP" },
                {
                  key: "created_at",
                  label: "Thời điểm tạo",
                  render: (item) => formatDate(item.created_at),
                },
                {
                  key: "revoke",
                  label: "Thao tác",
                  render: (item) => (
                    <button
                      className="secondary-button"
                      type="button"
                      disabled={Boolean(item.revoked_at)}
                      onClick={async () => {
                        setError("");
                        try {
                          await platformApi.revokeSession(detail._id, item._id);
                          await loadDetail(detail._id);
                        } catch (reason) {
                          setError(messageOf(reason));
                        }
                      }}
                    >
                      {item.revoked_at ? "Đã thu hồi" : "Thu hồi"}
                    </button>
                  ),
                },
              ]}
            />
          </Panel>

          <div className="grid gap-5 xl:grid-cols-2">
            <Panel title="Thành viên dự án">
              <DataTable
                items={memberships}
                empty="Không có thành viên dự án"
                columns={[
                  { key: "project_id", label: "Dự án" },
                  {
                    key: "project_role",
                    label: "Vai trò",
                    render: (item) => valueLabel(item.project_role),
                  },
                  {
                    key: "status",
                    label: "Trạng thái",
                    render: (item) => valueLabel(item.status),
                  },
                ]}
              />
            </Panel>
            <Panel title="Nhật ký bảo mật">
              <DataTable
                items={audit}
                empty="Không có sự kiện"
                columns={[
                  {
                    key: "action",
                    label: "Sự kiện",
                    render: (item) => valueLabel(item.action),
                  },
                  {
                    key: "timestamp",
                    label: "Thời điểm",
                    render: (item) => formatDate(item.timestamp),
                  },
                ]}
              />
            </Panel>
          </div>
        </>
      )}
      {dialog}
    </div>
  );
}
