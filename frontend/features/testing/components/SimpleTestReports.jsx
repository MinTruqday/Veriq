"use client";

import { useCallback, useEffect, useMemo, useState } from "react";
import { testingApi } from "../services/testing.service";
import { downloadTestingFile, testingRequest } from "../services/testing.transport";
import { ErrorState, Panel } from "./WorkspacePrimitives";
import { messageOf } from "../lib/testing";

const emptyForm = () => ({
  type: "PROGRESS",
  title: "",
  test_plan_id: "",
  start_at: "",
  end_at: "",
  summary: "",
  obstacles: "",
  next_steps: "",
  evaluation: "",
  remaining_risks: "",
  lessons: "",
});
const labels = {
  PASS: "Đạt",
  FAIL: "Thất bại",
  BLOCKED: "Bị chặn",
  SKIPPED: "Bỏ qua",
  NOT_APPLICABLE: "Không áp dụng",
  NOT_RUN: "Chưa ghi nhận trong kỳ",
};

export default function SimpleTestReports({ project }) {
  const permissions = useMemo(
    () => project.current_permissions || [],
    [project.current_permissions],
  );
  const can = (value) => permissions.includes(value);
  const [reports, setReports] = useState([]);
  const [plans, setPlans] = useState([]);
  const [form, setForm] = useState(emptyForm);
  const [editing, setEditing] = useState(false);
  const [preview, setPreview] = useState(null);
  const [selected, setSelected] = useState(null);
  const [error, setError] = useState("");
  const [busy, setBusy] = useState(false);
  const root = `/du-an/${project._id}/bao-cao-kiem-thu`;
  const load = useCallback(async () => {
    const [items, planItems] = await Promise.all([
      testingRequest(root),
      permissions.includes("testplan.read")
        ? testingApi.listPlans(project._id, { status: "APPROVED" })
        : Promise.resolve([]),
    ]);
    setReports(items);
    setPlans(planItems);
  }, [root, project._id, permissions]);
  useEffect(() => {
    load().catch((reason) => setError(messageOf(reason)));
  }, [load]);
  const change = (field, value) => {
    setForm((current) => ({ ...current, [field]: value }));
    setPreview(null);
  };
  const submit = async (event) => {
    event.preventDefault();
    setBusy(true);
    setError("");
    try {
      const payload = {
        ...form,
        start_at: new Date(form.start_at).toISOString(),
        end_at: new Date(form.end_at).toISOString(),
      };
      const value = await testingRequest(`${root}/xem-truoc`, {
        method: "POST",
        body: JSON.stringify(payload),
      });
      setPreview({
        value,
        payload: {
          ...payload,
          preview_hash: value.preview_hash,
          idempotency_key: crypto.randomUUID(),
        },
      });
    } catch (reason) {
      setError(messageOf(reason));
    } finally {
      setBusy(false);
    }
  };
  const save = async () => {
    setBusy(true);
    setError("");
    try {
      const saved = await testingRequest(root, {
        method: "POST",
        body: JSON.stringify(preview.payload),
      });
      await load();
      setSelected(saved);
      setPreview(null);
      setEditing(false);
    } catch (reason) {
      setError(messageOf(reason));
    } finally {
      setBusy(false);
    }
  };
  const displayed = preview?.value || selected;
  return (
    <div className="space-y-5">
      {error && <ErrorState message={error} />}
      {!editing && (can("teststatusreport.create") || can("testcompletion.create")) && (
        <button
          className="apple-button"
          type="button"
          onClick={() => {
            setForm({
              ...emptyForm(),
              type: can("teststatusreport.create") ? "PROGRESS" : "COMPLETION",
            });
            setPreview(null);
            setSelected(null);
            setEditing(true);
          }}
        >
          Tạo báo cáo
        </button>
      )}
      {editing && (
        <Panel title="Tạo báo cáo">
          <form className="space-y-4 p-5" onSubmit={submit}>
            <label className="field-label block">
              Loại báo cáo
              <select
                className="apple-input mt-2"
                value={form.type}
                onChange={(event) => change("type", event.target.value)}
              >
                {can("teststatusreport.create") && (
                  <option value="PROGRESS">Tiến độ kiểm thử</option>
                )}
                {can("testcompletion.create") && (
                  <option value="COMPLETION">Hoàn tất kiểm thử</option>
                )}
              </select>
            </label>
            <label className="field-label block">
              Tên báo cáo
              <input
                className="apple-input mt-2"
                required
                minLength={2}
                value={form.title}
                onChange={(event) => change("title", event.target.value)}
              />
            </label>
            <label className="field-label block">
              Kế hoạch kiểm thử
              <select
                className="apple-input mt-2"
                required
                value={form.test_plan_id}
                onChange={(event) => change("test_plan_id", event.target.value)}
              >
                <option value="">-</option>
                {plans.map((plan) => (
                  <option key={plan._id} value={plan._id}>
                    {plan.name}
                  </option>
                ))}
              </select>
            </label>
            <div className="grid gap-4 md:grid-cols-2">
              <label className="field-label block">
                Bắt đầu kỳ báo cáo
                <input
                  className="apple-input mt-2"
                  required
                  type="datetime-local"
                  value={form.start_at}
                  onChange={(event) => change("start_at", event.target.value)}
                />
              </label>
              <label className="field-label block">
                Kết thúc kỳ báo cáo
                <input
                  className="apple-input mt-2"
                  required
                  type="datetime-local"
                  value={form.end_at}
                  onChange={(event) => change("end_at", event.target.value)}
                />
              </label>
            </div>
            <label className="field-label block">
              Nhận xét
              <textarea
                className="apple-input mt-2"
                value={form.summary}
                onChange={(event) => change("summary", event.target.value)}
              />
            </label>
            {form.type === "COMPLETION" && (
              <label className="field-label block">
                Đánh giá mục tiêu và tiêu chí kết thúc
                <textarea
                  className="apple-input mt-2"
                  value={form.evaluation}
                  onChange={(event) => change("evaluation", event.target.value)}
                />
              </label>
            )}
            <details className="rounded-control border border-border p-4">
              <summary className="cursor-pointer">Tùy chọn</summary>
              <div className="mt-4 space-y-4">
                {[
                  ["obstacles", "Sai lệch, trở ngại và cách xử lý"],
                  ...(form.type === "PROGRESS"
                    ? [["next_steps", "Công việc kiểm thử tiếp theo"]]
                    : [
                        ["remaining_risks", "Rủi ro còn lại"],
                        ["lessons", "Bài học kinh nghiệm"],
                      ]),
                ].map(([field, label]) => (
                  <label key={field} className="field-label block">
                    {label}
                    <textarea
                      className="apple-input mt-2"
                      value={form[field]}
                      onChange={(event) => change(field, event.target.value)}
                    />
                  </label>
                ))}
              </div>
            </details>
            <div className="flex gap-2">
              <button
                type="button"
                className="secondary-button"
                onClick={() => {
                  setEditing(false);
                  setPreview(null);
                }}
              >
                Hủy
              </button>
              <button type="submit" className="apple-button" disabled={busy}>
                {busy ? "Đang tải…" : "Xem trước"}
              </button>
            </div>
          </form>
        </Panel>
      )}
      {displayed && (
        <Panel title={preview ? "Xem trước báo cáo" : displayed.title}>
          <div className="space-y-3 p-5">
            <p>
              {displayed.plan_name} · {new Date(displayed.start_at).toLocaleString("vi-VN")} –{" "}
              {new Date(displayed.end_at).toLocaleString("vi-VN")}
            </p>
            <p>Mục tiêu: {displayed.objective || "-"}</p>
            <p>Phạm vi: {displayed.scope_in?.join(", ") || "-"}</p>
            {!!displayed.scope_out?.length && (
              <p>Ngoài phạm vi: {displayed.scope_out.join(", ")}</p>
            )}
            {displayed.type === "COMPLETION" && (
              <p>Tiêu chí kết thúc: {displayed.exit_criteria?.join(", ") || "Chưa có"}</p>
            )}
            {!!displayed.environments?.length && (
              <p>Môi trường: {displayed.environments.join(", ")}</p>
            )}
            {!!displayed.builds?.length && <p>Bản dựng: {displayed.builds.join(", ")}</p>}
            {!!displayed.excluded_run_count && (
              <p>
                Có {displayed.excluded_run_count} lần chạy không thuộc phiên bản kế hoạch hiện tại,
                không được tính.
              </p>
            )}
            <p>Tổng số ca: {displayed.total}</p>
            <p>
              Tỷ lệ đạt (Đạt / (Đạt + Thất bại)):{" "}
              {displayed.pass_rate == null ? "Chưa đủ dữ liệu" : `${displayed.pass_rate}%`}
            </p>
            <ul className="grid gap-2 sm:grid-cols-2 md:grid-cols-3">
              {Object.entries(labels).map(([status, label]) => (
                <li key={status}>
                  {label}: {displayed.counts[status]}
                </li>
              ))}
            </ul>
            <p className="text-sm text-ink-muted">
              Mỗi ca được tính theo kết quả đã ghi nhận mới nhất trong kỳ; lịch sử từng lần chạy
              được giữ riêng.
            </p>
            {displayed.defects && (
              <p>
                Lỗi liên kết: {displayed.defects.total} · Đang mở tại thời điểm lập:{" "}
                {displayed.defects.open}
              </p>
            )}
            {[
              ["summary", "Nhận xét"],
              ["evaluation", "Đánh giá"],
              ["obstacles", "Trở ngại và cách xử lý"],
              ["next_steps", "Công việc tiếp theo"],
              ["remaining_risks", "Rủi ro còn lại"],
              ["lessons", "Bài học kinh nghiệm"],
            ].map(([key, label]) =>
              displayed[key] ? (
                <p key={key}>
                  {label}: {displayed[key]}
                </p>
              ) : null,
            )}
            {preview ? (
              <button className="apple-button" type="button" disabled={busy} onClick={save}>
                Lưu báo cáo
              </button>
            ) : (
              can("report.export") && (
                <div className="flex gap-2">
                  {["pdf", "docx"].map((format) => (
                    <button
                      className="secondary-button"
                      type="button"
                      key={format}
                      onClick={() =>
                        downloadTestingFile(
                          `${root}/${displayed._id}/xuat?format=${format}`,
                          `bao-cao.${format}`,
                        ).catch((reason) => setError(messageOf(reason)))
                      }
                    >
                      Xuất {format === "pdf" ? "PDF" : "Word"}
                    </button>
                  ))}
                </div>
              )
            )}
          </div>
        </Panel>
      )}
      {!editing && (
        <Panel title="Báo cáo đã lưu">
          <div className="divide-y divide-border">
            {reports.length ? (
              reports.map((report) => (
                <button
                  className="block w-full p-4 text-left hover:bg-surface-raised"
                  type="button"
                  key={report._id}
                  onClick={() => setSelected(report)}
                >
                  {report.title} · {report.type === "PROGRESS" ? "Tiến độ" : "Hoàn tất"} ·{" "}
                  {report.plan_name}
                </button>
              ))
            ) : (
              <p className="p-4">Chưa có báo cáo</p>
            )}
          </div>
        </Panel>
      )}
    </div>
  );
}
