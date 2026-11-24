"use client";
import { useCallback, useEffect, useRef, useState } from "react";
import {
  Eye,
  KeyRound,
  LockKeyhole,
  MailCheck,
  Pencil,
  Shield,
  ShieldOff,
  Trash2,
  UnlockKeyhole,
  UserCheck,
  UserRoundX,
} from "lucide-react";
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
import { messageOf, valueLabel } from "../lib/testing";
import SearchField from "@/shared/components/ui/SearchField";
import { Modal, ModalContent, ModalHeader, ModalTitle } from "@/shared/components/ui/Modal";

export default function PlatformUsersPanel() {
  const { ask, dialog } = useActionDialog();
  const [users, setUsers] = useState([]);
  const [query, setQuery] = useState("");
  const [selectedId, setSelectedId] = useState("");
  const [detail, setDetail] = useState(null);
  const [memberships, setMemberships] = useState([]);
  const [loading, setLoading] = useState(true);
  const [detailLoading, setDetailLoading] = useState(false);
  const [error, setError] = useState("");
  const [accountActionInFlight, setAccountActionInFlight] = useState(false);
  const [page, setPage] = useState(1);
  const pageSize = 20;
  const usersRequestId = useRef(0);
  const detailRequestId = useRef(0);
  const accountActionInFlightRef = useRef(false);

  const loadUsers = useCallback(async (search = "") => {
    const requestId = ++usersRequestId.current;
    setLoading(true);
    setError("");
    setPage(1);
    try {
      const result = await platformApi.listUsers(search);
      if (requestId === usersRequestId.current) setUsers(Array.isArray(result) ? result : []);
    } catch (reason) {
      if (requestId === usersRequestId.current) setError(messageOf(reason));
    } finally {
      if (requestId === usersRequestId.current) setLoading(false);
    }
  }, []);

  const loadDetail = useCallback(async (id) => {
    const requestId = ++detailRequestId.current;
    if (!id) {
      setDetail(null);
      setMemberships([]);
      setDetailLoading(false);
      return;
    }
    setDetail(null);
    setMemberships([]);
    setDetailLoading(true);
    setError("");
    try {
      const [user, projectMemberships] = await Promise.all([
        platformApi.getUser(id),
        platformApi.listMemberships(id),
      ]);
      if (requestId !== detailRequestId.current) return;
      setDetail(user);
      setMemberships(Array.isArray(projectMemberships) ? projectMemberships : []);
    } catch (reason) {
      if (requestId === detailRequestId.current) setError(messageOf(reason));
    } finally {
      if (requestId === detailRequestId.current) setDetailLoading(false);
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

  const runAccountAction = async (action) => {
    if (accountActionInFlightRef.current) return;
    accountActionInFlightRef.current = true;
    setAccountActionInFlight(true);
    try {
      await action();
    } finally {
      accountActionInFlightRef.current = false;
      setAccountActionInFlight(false);
    }
  };

  const mutate = (title, description, confirmLabel, action) =>
    runAccountAction(async () => {
      const reason = await reasonFor(title, description, confirmLabel);
      if (!reason) return;
      setError("");
      try {
        await action(reason);
        await Promise.all([loadUsers(query), loadDetail(selectedId)]);
      } catch (value) {
        setError(messageOf(value));
      }
    });

  return (
    <div className="space-y-5">
      {error && !selectedId && <ErrorState message={error} />}
      <Panel
        title="Tài khoản hệ thống"
        actions={
          <div className="flex flex-wrap gap-2">
            <button
              className="apple-button"
              type="button"
              disabled={accountActionInFlight}
              onClick={() =>
                void runAccountAction(async () => {
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
                })
              }
            >
              Tạo tài khoản
            </button>
            <button
              className="secondary-button"
              type="button"
              disabled={accountActionInFlight}
              onClick={() =>
                void runAccountAction(async () => {
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
                })
              }
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
              <SearchField
                ariaLabel="Tìm tài khoản"
                className="w-full sm:w-72"
                onChange={(event) => setQuery(event.target.value)}
                placeholder="Email, họ tên hoặc tên đăng nhập"
                value={query}
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
                minWidth: 64,
                render: (item) => (
                  <button
                    aria-label={`Xem chi tiết tài khoản ${item.full_name || item.email}`}
                    className="icon-button h-9 w-9"
                    title="Xem chi tiết tài khoản"
                    type="button"
                    onClick={() => {
                      setSelectedId(item._id);
                    }}
                  >
                    <Eye aria-hidden="true" size={17} />
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

      <Modal
        isOpen={Boolean(selectedId)}
        onClose={() => setSelectedId("")}
        ariaLabel="Chi tiết tài khoản"
        className="max-w-5xl"
      >
        <ModalHeader>
          <ModalTitle>{detail ? `Chi tiết ${detail.email}` : "Đang tải tài khoản"}</ModalTitle>
        </ModalHeader>
        {detailLoading ? (
          <ModalContent>
            <LoadingState />
          </ModalContent>
        ) : error && !detail ? (
          <ModalContent>
            <ErrorState message={error} />
          </ModalContent>
        ) : detail ? (
          <ModalContent>
            {error && <ErrorState message={error} />}
            <div className="grid gap-4 md:grid-cols-2 xl:grid-cols-4">
              <div>
                <p className="field-label">Email</p>
                <p className="break-all">{detail.email}</p>
              </div>
              <div>
                <p className="field-label">Họ tên</p>
                <p>{detail.full_name || "-"}</p>
              </div>
              <div>
                <p className="field-label">Vai trò hệ thống</p>
                <p>{valueLabel(detail.system_role)}</p>
              </div>
              <div>
                <p className="field-label">Trạng thái</p>
                <p>{valueLabel(detail.account_status)}</p>
              </div>
            </div>

            <div
              className="flex flex-wrap items-center gap-2 border-y border-border py-4"
              aria-label="Thao tác tài khoản"
            >
              <button
                className="icon-button h-9 w-9"
                type="button"
                aria-label="Sửa hồ sơ"
                title="Sửa hồ sơ"
                disabled={accountActionInFlight}
                onClick={() =>
                  void runAccountAction(async () => {
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
                  })
                }
              >
                <Pencil aria-hidden="true" size={16} />
              </button>

              {detail.account_status === "ACTIVE" ? (
                <>
                  <button
                    className="icon-button h-9 w-9"
                    type="button"
                    aria-label="Khóa tài khoản"
                    title="Khóa tài khoản"
                    disabled={accountActionInFlight}
                    onClick={() =>
                      mutate(
                        "Khóa tài khoản",
                        "Tài khoản sẽ mất quyền truy cập ngay lập tức",
                        "Khóa",
                        (reason) => platformApi.lockUser(detail._id, reason),
                      )
                    }
                  >
                    <LockKeyhole aria-hidden="true" size={16} />
                  </button>
                  <button
                    className="icon-button h-9 w-9"
                    type="button"
                    aria-label="Vô hiệu hóa tài khoản"
                    title="Vô hiệu hóa tài khoản"
                    disabled={accountActionInFlight}
                    onClick={() =>
                      mutate(
                        "Vô hiệu hóa tài khoản",
                        "Tài khoản sẽ không thể đăng nhập",
                        "Vô hiệu hóa",
                        (reason) => platformApi.disableUser(detail._id, reason),
                      )
                    }
                  >
                    <UserRoundX aria-hidden="true" size={16} />
                  </button>
                </>
              ) : (
                <button
                  className="icon-button h-9 w-9"
                  type="button"
                  aria-label={
                    detail.account_status === "LOCKED" ? "Mở khóa tài khoản" : "Kích hoạt tài khoản"
                  }
                  title={
                    detail.account_status === "LOCKED" ? "Mở khóa tài khoản" : "Kích hoạt tài khoản"
                  }
                  disabled={accountActionInFlight}
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
                  {detail.account_status === "LOCKED" ? (
                    <UnlockKeyhole aria-hidden="true" size={16} />
                  ) : (
                    <UserCheck aria-hidden="true" size={16} />
                  )}
                </button>
              )}

              <button
                className="icon-button h-9 w-9"
                type="button"
                aria-label="Buộc đặt lại mật khẩu"
                title="Buộc đặt lại mật khẩu"
                disabled={accountActionInFlight}
                onClick={() =>
                  mutate(
                    "Buộc đặt lại mật khẩu",
                    "Quy trình khôi phục mật khẩu sẽ được gửi",
                    "Khởi tạo",
                    (reason) => platformApi.forcePasswordReset(detail._id, reason),
                  )
                }
              >
                <KeyRound aria-hidden="true" size={16} />
              </button>
              <button
                className="icon-button h-9 w-9"
                type="button"
                aria-label="Gửi lại quy trình kích hoạt"
                title="Gửi lại quy trình kích hoạt"
                disabled={accountActionInFlight}
                onClick={() =>
                  mutate(
                    "Gửi lại quy trình kích hoạt",
                    "Hệ thống sẽ gửi lại hướng dẫn kích hoạt",
                    "Gửi",
                    (reason) => platformApi.resendVerification(detail._id, reason),
                  )
                }
              >
                <MailCheck aria-hidden="true" size={16} />
              </button>
              <button
                className="icon-button h-9 w-9"
                type="button"
                aria-label={
                  detail.system_role === "ADMIN" ? "Hạ quyền quản trị" : "Cấp quyền quản trị"
                }
                title={detail.system_role === "ADMIN" ? "Hạ quyền quản trị" : "Cấp quyền quản trị"}
                disabled={accountActionInFlight}
                onClick={() =>
                  mutate(
                    detail.system_role === "ADMIN" ? "Hạ quyền quản trị" : "Cấp quyền quản trị",
                    "Thay đổi vai trò hệ thống của tài khoản",
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
                {detail.system_role === "ADMIN" ? (
                  <ShieldOff aria-hidden="true" size={16} />
                ) : (
                  <Shield aria-hidden="true" size={16} />
                )}
              </button>
              <button
                className="icon-button h-9 w-9 text-danger"
                type="button"
                aria-label="Xóa và ẩn danh tài khoản"
                title="Xóa và ẩn danh tài khoản"
                disabled={accountActionInFlight}
                onClick={() =>
                  void runAccountAction(async () => {
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
                  })
                }
              >
                <Trash2 aria-hidden="true" size={16} />
              </button>
            </div>

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
                  { key: "status", label: "Trạng thái", render: (item) => valueLabel(item.status) },
                ]}
              />
            </Panel>
          </ModalContent>
        ) : null}
      </Modal>
      {dialog}
    </div>
  );
}
