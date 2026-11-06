"use client";
import { useCallback, useEffect, useRef, useState } from "react";
import { Power, RotateCcw } from "lucide-react";
import DataTable from "./DataTable";
import {
  ErrorState,
  LoadingState,
  Panel,
  StatusPill,
  useActionDialog,
} from "./WorkspacePrimitives";
import { formatDate, messageOf } from "../lib/testing";
import { testingApi } from "../services/testing.service";
import { operationForRetry } from "../lib/executionRecovery.logic.mjs";

export default function WebhookPanel({ project }) {
  const { ask, dialog } = useActionDialog();
  const [subscriptions, setSubscriptions] = useState([]);
  const [deliveries, setDeliveries] = useState([]);
  const [error, setError] = useState("");
  const [notice, setNotice] = useState("");
  const [loading, setLoading] = useState(true);
  const hasLoaded = useRef(false);
  const replayOperation = useRef(null);
  const loadGeneration = useRef(0);
  const canRead = project.current_permissions?.includes("webhook.project.read");
  const canManage = project.current_permissions?.includes("webhook.project.manage");
  const canReplay = project.current_permissions?.includes("webhook.project.replay");
  const load = useCallback(async () => {
    const requestGeneration = ++loadGeneration.current;
    if (!canRead) {
      setSubscriptions([]);
      setDeliveries([]);
      setLoading(false);
      return false;
    }
    if (!hasLoaded.current) setLoading(true);
    try {
      const [subscriptionValues, deliveryValues] = await Promise.all([
        testingApi.listWebhookSubscriptions(project._id),
        testingApi.listWebhookDeliveries(project._id),
      ]);
      if (requestGeneration !== loadGeneration.current) return;
      setSubscriptions(subscriptionValues);
      setDeliveries(deliveryValues);
      setError("");
      hasLoaded.current = true;
      return true;
    } catch (reason) {
      if (requestGeneration === loadGeneration.current) setError(messageOf(reason));
      return false;
    } finally {
      if (requestGeneration === loadGeneration.current) setLoading(false);
    }
  }, [canRead, loadGeneration, project._id]);
  useEffect(() => {
    setSubscriptions([]);
    setDeliveries([]);
    setError("");
    hasLoaded.current = false;
    void load();
    return () => {
      loadGeneration.current += 1;
    };
  }, [load, loadGeneration]);
  const create = async () =>
    ask({
      title: "Tạo đăng ký webhook",
      confirmLabel: "Tạo đăng ký",
      description: "Dùng điểm cuối và thông tin xác thực đã được cấp trên nền tảng.",
      fields: [
        { name: "name", label: "Tên đăng ký", required: true, autoFocus: true },
        {
          name: "endpointReference",
          label: "Tham chiếu điểm cuối",
          required: true,
          placeholder: "Nhập tham chiếu điểm cuối đã được cấp",
        },
        {
          name: "secretReference",
          label: "Tham chiếu thông tin xác thực",
          required: true,
          placeholder: "Nhập tham chiếu thông tin xác thực đã được cấp",
        },
        {
          name: "events",
          label: "Sự kiện cần nhận, mỗi dòng một sự kiện",
          required: true,
          multiline: true,
          placeholder: "Nhập sự kiện được hệ thống hỗ trợ",
        },
      ],
      onConfirm: async (answer) => {
        setError("");
        setNotice("");
        await testingApi
          .createWebhookSubscription(project._id, {
            name: answer.name.trim(),
            endpoint_reference: answer.endpointReference.trim(),
            secret_reference: answer.secretReference.trim(),
            events: answer.events
              .split("\n")
              .map((value) => value.trim())
              .filter(Boolean),
            enabled: true,
          })
          .catch((reason) => {
            throw new Error(messageOf(reason));
          });
        const refreshed = await load();
        setNotice(
          refreshed
            ? "Đã tạo đăng ký webhook."
            : "Đăng ký đã được tạo, nhưng chưa tải lại được danh sách.",
        );
      },
    });
  if (!canRead) return null;
  return (
    <Panel
      title="Webhook dự án"
      actions={
        <div className="flex flex-wrap items-center gap-2">
          <button
            aria-label={loading ? "Đang tải webhook" : "Tải lại webhook"}
            className="icon-button h-10 w-10"
            disabled={loading}
            onClick={() => void load()}
            title={loading ? "Đang tải webhook" : "Tải lại webhook"}
            type="button"
          >
            <RotateCcw aria-hidden="true" size={16} />
          </button>
          {canManage && (
            <button className="apple-button" type="button" onClick={create}>
              Tạo webhook
            </button>
          )}
        </div>
      }
    >
      {error && <ErrorState message={error} />}
      {error && (
        <div className="px-5 pt-3">
          <button
            className="secondary-button"
            type="button"
            disabled={loading}
            onClick={() => void load()}
          >
            Thử tải lại
          </button>
        </div>
      )}
      {notice && (
        <p className="px-5 pt-3 text-sm text-ink-muted" role="status">
          {notice}
        </p>
      )}
      <div className="space-y-5 p-5">
        {loading && !hasLoaded.current ? (
          <LoadingState />
        ) : (
          <>
            <section className="space-y-3 rounded-xl border border-border bg-white p-4 sm:p-5">
              <div className="flex flex-wrap items-center justify-between gap-2">
                <h3 className="text-sm font-semibold text-ink">Đăng ký webhook</h3>
                <span className="text-xs text-ink-muted">{subscriptions.length} đăng ký</span>
              </div>
              <DataTable
                items={subscriptions}
                empty="Chưa có đăng ký webhook"
                columns={[
                  { key: "name", label: "Tên" },
                  {
                    key: "events",
                    label: "Sự kiện",
                    render: (item) => (
                      <details>
                        <summary className="cursor-pointer">{item.events.length} sự kiện</summary>
                        <ul className="mt-2 grid gap-1 text-xs text-ink-muted">
                          {item.events.map((event) => (
                            <li key={event}>{event}</li>
                          ))}
                        </ul>
                      </details>
                    ),
                  },
                  {
                    key: "references",
                    label: "Cấu hình kết nối",
                    render: (item) => (
                      <span className="text-sm">
                        {item.endpoint_reference ? "Điểm cuối đã cấu hình" : "Thiếu điểm cuối"}
                        <br />
                        {item.secret_reference
                          ? "Thông tin xác thực đã lưu an toàn"
                          : "Thiếu thông tin xác thực"}
                      </span>
                    ),
                  },
                  {
                    key: "enabled",
                    label: "Trạng thái",
                    render: (item) => <StatusPill value={item.enabled ? "ACTIVE" : "DISABLED"} />,
                  },
                  {
                    key: "actions",
                    label: "Thao tác",
                    hideWhenEmpty: true,
                    render: (item) =>
                      canManage ? (
                        <button
                          aria-label={`${item.enabled ? "Vô hiệu hóa" : "Kích hoạt"} đăng ký ${item.event_type || item._id}`}
                          className="icon-button h-9 w-9"
                          title={item.enabled ? "Vô hiệu hóa đăng ký" : "Kích hoạt đăng ký"}
                          type="button"
                          onClick={async () => {
                            try {
                              await testingApi.updateWebhookSubscription(project._id, item._id, {
                                expected_revision: item.revision,
                                enabled: !item.enabled,
                              });
                              await load();
                            } catch (reason) {
                              setError(messageOf(reason));
                            }
                          }}
                        >
                          <Power aria-hidden="true" size={16} />
                        </button>
                      ) : null,
                  },
                ]}
              />
            </section>
            <section className="space-y-3 rounded-xl border border-border bg-white p-4 sm:p-5">
              <div className="flex flex-wrap items-center justify-between gap-2">
                <h3 className="text-sm font-semibold text-ink">Lịch sử gửi</h3>
                <span className="text-xs text-ink-muted">{deliveries.length} lần gửi</span>
              </div>
              <DataTable
                items={deliveries}
                empty="Chưa có lần gửi webhook"
                columns={[
                  { key: "event_type", label: "Sự kiện" },
                  {
                    key: "status",
                    label: "Trạng thái",
                    render: (item) => <StatusPill value={item.status} />,
                  },
                  {
                    key: "details",
                    label: "Thông tin gửi",
                    render: (item) => (
                      <details>
                        <summary className="cursor-pointer">
                          {item.error_code
                            ? "Xem chi tiết"
                            : item.response_status
                              ? "Đã có phản hồi"
                              : "Chưa có phản hồi"}
                        </summary>
                        <dl className="mt-2 grid gap-1 text-xs text-ink-muted">
                          {item.response_status != null && (
                            <div>
                              <dt>Phản hồi từ dịch vụ</dt>
                              <dd>{item.response_status}</dd>
                            </div>
                          )}
                          {item.error_code && (
                            <div>
                              <dt>Thông tin lỗi</dt>
                              <dd>{item.error_code}</dd>
                            </div>
                          )}
                        </dl>
                      </details>
                    ),
                  },
                  {
                    key: "created_at",
                    label: "Thời điểm",
                    render: (item) => formatDate(item.created_at),
                  },
                  {
                    key: "actions",
                    label: "Thao tác",
                    hideWhenEmpty: true,
                    render: (item) =>
                      canReplay && item.status === "FAILED" ? (
                        <button
                          aria-label={`Phát lại lần gửi ${item.event_type || item._id}`}
                          className="icon-button h-9 w-9"
                          title="Phát lại"
                          type="button"
                          onClick={async () => {
                            await ask({
                              title: "Phát lại lần giao móc gọi",
                              description: `${item.event_type} ${item.error_code || ""}`,
                              confirmLabel: "Đưa vào hàng đợi",
                              fields: [
                                {
                                  name: "reason",
                                  label: "Lý do phát lại",
                                  required: true,
                                  multiline: true,
                                },
                              ],
                              onConfirm: async (answer) => {
                                const payload = {
                                  reason: answer.reason.trim(),
                                };
                                const signature = `${item._id}:${payload.reason}`;
                                replayOperation.current = operationForRetry(
                                  replayOperation.current,
                                  signature,
                                  crypto.randomUUID(),
                                );
                                try {
                                  await testingApi.replayWebhookDelivery(project._id, item._id, {
                                    idempotency_key: replayOperation.current.idempotencyKey,
                                    reason: payload.reason,
                                  });
                                  replayOperation.current = null;
                                  await load();
                                } catch (reason) {
                                  throw new Error(messageOf(reason));
                                }
                              },
                            });
                          }}
                        >
                          <RotateCcw aria-hidden="true" size={16} />
                        </button>
                      ) : null,
                  },
                ]}
              />
            </section>
          </>
        )}
      </div>
      {dialog}
    </Panel>
  );
}
