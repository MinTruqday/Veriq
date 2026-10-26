"use client";
import { useCallback, useEffect, useRef, useState } from "react";
import DataTable from "./DataTable";
import { ErrorState, Panel, StatusPill, useActionDialog } from "./WorkspacePrimitives";
import { formatDate, messageOf } from "../lib/testing";
import { testingApi } from "../services/testing.service";
import { operationForRetry } from "../lib/executionRecovery.logic.mjs";

export default function WebhookPanel({ project }) {
  const { ask, dialog } = useActionDialog();
  const [subscriptions, setSubscriptions] = useState([]);
  const [deliveries, setDeliveries] = useState([]);
  const [error, setError] = useState("");
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
      return;
    }
    try {
      const [subscriptionValues, deliveryValues] = await Promise.all([
        testingApi.listWebhookSubscriptions(project._id),
        testingApi.listWebhookDeliveries(project._id),
      ]);
      if (requestGeneration !== loadGeneration.current) return;
      setSubscriptions(subscriptionValues);
      setDeliveries(deliveryValues);
      setError("");
    } catch (reason) {
      if (requestGeneration === loadGeneration.current) setError(messageOf(reason));
    }
  }, [canRead, loadGeneration, project._id]);
  useEffect(() => {
    setSubscriptions([]);
    setDeliveries([]);
    setError("");
    void load();
    return () => {
      loadGeneration.current += 1;
    };
  }, [load, loadGeneration]);
  const create = async () => {
    const answer = await ask({
      title: "Tạo đăng ký móc gọi",
      confirmLabel: "Tạo đăng ký",
      fields: [
        { name: "name", label: "Tên móc gọi", required: true, autoFocus: true },
        {
          name: "endpointReference",
          label: "Tham chiếu điểm cuối",
          required: true,
          initialValue: "endpoint://nen-tang/",
        },
        {
          name: "secretReference",
          label: "Tham chiếu bí mật",
          required: true,
          initialValue: "secret://nen-tang/",
        },
        {
          name: "events",
          label: "Mã sự kiện mỗi dòng một giá trị",
          required: true,
          multiline: true,
          initialValue: "DEFECT_CREATED",
        },
      ],
    });
    if (!answer) return;
    try {
      await testingApi.createWebhookSubscription(project._id, {
        name: answer.name.trim(),
        endpoint_reference: answer.endpointReference.trim(),
        secret_reference: answer.secretReference.trim(),
        events: answer.events
          .split("\n")
          .map((value) => value.trim())
          .filter(Boolean),
        enabled: true,
      });
      await load();
    } catch (reason) {
      setError(messageOf(reason));
    }
  };
  if (!canRead) return null;
  return (
    <Panel
      title="Móc gọi dự án"
      actions={
        canManage ? (
          <button className="apple-button" type="button" onClick={create}>
            Tạo đăng ký
          </button>
        ) : null
      }
    >
      {error && <ErrorState message={error} />}
      <div className="space-y-5 p-5">
        <DataTable
          items={subscriptions}
          empty="Chưa có đăng ký móc gọi"
          columns={[
            { key: "name", label: "Tên" },
            { key: "events", label: "Sự kiện", render: (item) => item.events.join(", ") },
            {
              key: "references",
              label: "Tham chiếu",
              render: (item) => `${item.endpoint_reference} · ${item.secret_reference}`,
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
                    className="secondary-button"
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
                    {item.enabled ? "Vô hiệu hóa" : "Kích hoạt"}
                  </button>
                ) : null,
            },
          ]}
        />
        <DataTable
          items={deliveries}
          empty="Chưa có lần giao móc gọi"
          columns={[
            { key: "event_type", label: "Sự kiện" },
            {
              key: "status",
              label: "Trạng thái",
              render: (item) => <StatusPill value={item.status} />,
            },
            { key: "response_status", label: "Mã phản hồi" },
            { key: "error_code", label: "Mã lỗi" },
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
                    className="secondary-button"
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
                    Phát lại
                  </button>
                ) : null,
            },
          ]}
        />
      </div>
      {dialog}
    </Panel>
  );
}
