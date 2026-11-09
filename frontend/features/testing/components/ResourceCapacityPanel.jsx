"use client";

import { useCallback, useEffect, useRef, useState } from "react";
import { platformApi } from "@/features/authentication/services/platform.service";
import { projectTestingApi } from "../services/testing.projects";
import { ErrorState, Panel } from "./WorkspacePrimitives";
import { messageOf } from "../lib/testing";

function defaultPeriod() {
  const current = new Date();
  const start = new Date(current.getFullYear(), current.getMonth(), 1);
  const end = new Date(current.getFullYear(), current.getMonth() + 1, 0);
  const format = (date) =>
    `${date.getFullYear()}-${String(date.getMonth() + 1).padStart(2, "0")}-${String(date.getDate()).padStart(2, "0")}`;
  return { period_start: format(start), period_end: format(end) };
}

function calendarDate(value) {
  const match = /^(\d{4})-(\d{2})-(\d{2})/.exec(String(value || ""));
  return match ? `${match[3]}/${match[2]}/${match[1]}` : "—";
}

export default function ResourceCapacityPanel() {
  const [periods, setPeriods] = useState([]);
  const [users, setUsers] = useState([]);
  const [selectedPeriod, setSelectedPeriod] = useState("new");
  const [range, setRange] = useState(defaultPeriod);
  const [revision, setRevision] = useState(0);
  const [rows, setRows] = useState([]);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState("");
  const [saved, setSaved] = useState(false);
  const requestId = useRef(0);

  const load = useCallback(async (selection = "new") => {
    const currentRequest = ++requestId.current;
    setLoading(true);
    setError("");
    try {
      const [result, people] = await Promise.all([
        projectTestingApi.listCapacityPeriods(),
        platformApi.listUsers(),
      ]);
      if (currentRequest !== requestId.current) return;
      const availablePeriods = Array.isArray(result) ? result : [];
      setPeriods(availablePeriods);
      setUsers(Array.isArray(people) ? people.filter((item) => item.is_active) : []);
      const selected = availablePeriods.find((item) => item._id === selection);
      const period = selected || (selection !== "new" ? availablePeriods[0] : null);
      if (period) {
        setSelectedPeriod(period._id);
        setRange({ period_start: period.period_start, period_end: period.period_end });
        setRevision(period.revision || 0);
        setRows((period.entries || []).map((entry) => ({
          user_id: entry.user_id,
          available_hours: String(entry.available_hours ?? ""),
          max_concurrent_projects: entry.max_concurrent_projects == null ? "" : String(entry.max_concurrent_projects),
        })));
      } else {
        setSelectedPeriod("new");
        setRange(defaultPeriod());
        setRevision(0);
        setRows([]);
      }
    } catch (reason) {
      if (currentRequest === requestId.current) setError(messageOf(reason) || "Không thể tải công suất nhân sự");
    } finally {
      if (currentRequest === requestId.current) setLoading(false);
    }
  }, []);

  useEffect(() => {
    void load("new");
  }, [load]);

  const selectPeriod = (value) => {
    requestId.current += 1;
    setSelectedPeriod(value);
    setSaved(false);
    const period = periods.find((item) => item._id === value);
    setRange(period ? { period_start: period.period_start, period_end: period.period_end } : defaultPeriod());
    setRevision(period?.revision || 0);
    setRows((period?.entries || []).map((entry) => ({
      user_id: entry.user_id,
      available_hours: String(entry.available_hours ?? ""),
      max_concurrent_projects: entry.max_concurrent_projects == null ? "" : String(entry.max_concurrent_projects),
    })));
  };

  const updateRow = (index, key, value) => {
    setSaved(false);
    setRows((current) => current.map((row, rowIndex) => rowIndex === index ? { ...row, [key]: value } : row));
  };

  const save = async (event) => {
    event.preventDefault();
    setLoading(true);
    setError("");
    setSaved(false);
    try {
      const result = await projectTestingApi.updateCapacityPeriod({
        expected_revision: revision,
        ...range,
        entries: rows.map((row) => ({
          user_id: row.user_id,
          available_hours: Number(row.available_hours),
          max_concurrent_projects: row.max_concurrent_projects ? Number(row.max_concurrent_projects) : null,
        })),
      });
      setRevision(result.revision || revision + 1);
      setSelectedPeriod(result._id || selectedPeriod);
      setSaved(true);
      await load(result._id || selectedPeriod);
    } catch (reason) {
      setError(messageOf(reason) || "Không thể lưu công suất nhân sự");
    } finally {
      setLoading(false);
    }
  };

  return (
    <Panel title="Công suất và giới hạn phân công">
      <form className="space-y-4 p-4" onSubmit={save}>
        <p className="text-sm text-ink-muted">
          Khai báo giờ khả dụng và giới hạn số dự án đồng thời cho từng kỳ. AI dùng thông tin này để tránh đề xuất vượt quá công suất.
        </p>
        {error && <ErrorState message={error} />}
        {saved && <p className="text-sm text-success" role="status">Đã lưu công suất và giới hạn phân công.</p>}
        <div className="grid gap-3 md:grid-cols-3">
          <label className="field-label block">
            Kỳ công suất
            <select className="apple-input mt-2 w-full" value={selectedPeriod} disabled={loading} onChange={(event) => selectPeriod(event.target.value)}>
              <option value="new">Tạo kỳ mới</option>
              {periods.map((period) => <option key={period._id} value={period._id}>{calendarDate(period.period_start)} – {calendarDate(period.period_end)}</option>)}
            </select>
          </label>
          <label className="field-label block">
            Bắt đầu
            <input className="apple-input mt-2 w-full" type="date" required disabled={loading || selectedPeriod !== "new"} value={range.period_start} onChange={(event) => setRange((current) => ({ ...current, period_start: event.target.value }))} />
          </label>
          <label className="field-label block">
            Kết thúc
            <input className="apple-input mt-2 w-full" type="date" required disabled={loading || selectedPeriod !== "new"} value={range.period_end} onChange={(event) => setRange((current) => ({ ...current, period_end: event.target.value }))} />
          </label>
        </div>
        <div className="max-w-full overflow-x-auto">
          <table className="w-full min-w-[760px] text-left text-sm">
            <thead><tr><th className="p-2">Thành viên</th><th className="p-2">Giờ khả dụng</th><th className="p-2">Số dự án tối đa đồng thời</th><th className="p-2">Thao tác</th></tr></thead>
            <tbody>
              {rows.map((row, index) => (
                <tr className="border-t border-border align-top" key={`${row.user_id}-${index}`}>
                  <td className="min-w-64 p-2"><select className="apple-input w-full" required disabled={loading} value={row.user_id} onChange={(event) => updateRow(index, "user_id", event.target.value)}><option value="">Chọn thành viên</option>{users.map((person) => <option key={person._id} value={person._id}>{person.full_name || person.email} · {person.email}</option>)}</select></td>
                  <td className="min-w-40 p-2"><input className="apple-input w-full" type="number" min="0" step="0.25" required disabled={loading} value={row.available_hours} onChange={(event) => updateRow(index, "available_hours", event.target.value)} /></td>
                  <td className="min-w-48 p-2"><input className="apple-input w-full" type="number" min="1" step="1" disabled={loading} value={row.max_concurrent_projects} onChange={(event) => updateRow(index, "max_concurrent_projects", event.target.value)} /><span className="mt-1 block text-xs text-ink-muted">Để trống nếu chưa có giới hạn đã duyệt.</span></td>
                  <td className="p-2"><button className="apple-button-secondary" type="button" disabled={loading} onClick={() => setRows((current) => current.filter((_, rowIndex) => rowIndex !== index))}>Gỡ</button></td>
                </tr>
              ))}
            </tbody>
          </table>
          {!rows.length && <p className="py-4 text-sm text-ink-muted">Chưa có thành viên trong kỳ công suất này.</p>}
        </div>
        <div className="flex flex-wrap gap-2">
          <button className="apple-button-secondary" type="button" disabled={loading} onClick={() => setRows((current) => [...current, { user_id: "", available_hours: "", max_concurrent_projects: "" }])}>Thêm thành viên</button>
          <button className="apple-button" type="submit" disabled={loading || !rows.length}>{loading ? "Đang lưu" : "Lưu công suất"}</button>
        </div>
      </form>
    </Panel>
  );
}
