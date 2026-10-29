"use client";

import { useCallback, useEffect, useState } from "react";
import { projectTestingApi } from "../services/testing.projects";
import { ErrorState, LoadingState, Panel } from "./WorkspacePrimitives";

const columns = [
  ["employee", "Mã nhân viên hoặc email"],
  ["hourly_cost", "Đơn giá theo giờ"],
  ["currency", "Tiền tệ"],
  ["valid_from", "Ngày bắt đầu hiệu lực"],
  ["valid_until", "Ngày kết thúc hiệu lực (không bắt buộc)"],
];

const statusLabels = {
  READY: "Sẵn sàng nhập",
  UNCHANGED: "Đã có, không thay đổi",
  DUPLICATE_IN_FILE: "Dòng trùng trong file",
  CONFLICT_IN_FILE: "Trùng mã và thời hạn nhưng dữ liệu khác",
  CONFLICT_EXISTING: "Trùng thời hạn với đơn giá hiện có",
  INVALID: "Dữ liệu lỗi",
};

export default function PayrollImportPanel() {
  const [file, setFile] = useState(null);
  const [headers, setHeaders] = useState([]);
  const [mapping, setMapping] = useState({
    employee: "employee",
    hourly_cost: "hourly_cost",
    currency: "currency",
    valid_from: "valid_from",
    valid_until: "valid_until",
  });
  const [preview, setPreview] = useState(null);
  const [skipRows, setSkipRows] = useState(() => new Set());
  const [rates, setRates] = useState([]);
  const [projects, setProjects] = useState([]);
  const [financeProjectId, setFinanceProjectId] = useState("");
  const [financePlans, setFinancePlans] = useState([]);
  const [selectedFinancialPlanId, setSelectedFinancialPlanId] = useState("");
  const [commercialTerms, setCommercialTerms] = useState({
    expected_revision: 0,
    contract_price: "",
    currency: "VND",
    tax_included: true,
    scope_note: "",
  });
  const [forecast, setForecast] = useState(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState("");

  const loadRates = useCallback(async () => {
    setLoading(true);
    setError("");
    try {
      setRates(await projectTestingApi.listPayrollRates());
    } catch (reason) {
      setError(reason.message || "Không thể tải bảng đơn giá");
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    void loadRates();
  }, [loadRates]);

  useEffect(() => {
    projectTestingApi
      .listFinancialProjects()
      .then((items) => {
        setProjects(items);
        setFinanceProjectId((current) => current || items[0]?._id || "");
      })
      .catch((reason) => setError(reason.message || "Không thể tải dự án"));
  }, []);

  useEffect(() => {
    if (!financeProjectId) return;
    let current = true;
    Promise.all([
      projectTestingApi.getProjectCommercialTerms(financeProjectId),
      projectTestingApi.listFinancialTestPlans(financeProjectId),
    ])
      .then(([terms, plans]) => {
        if (!current) return;
        setCommercialTerms({
          expected_revision: terms.revision || 0,
          contract_price: terms.contract_price || "",
          currency: terms.currency || "VND",
          tax_included: terms.tax_included ?? true,
          scope_note: terms.scope_note || "",
        });
        setFinancePlans(plans);
        setSelectedFinancialPlanId((selected) =>
          plans.some((item) => item._id === selected) ? selected : "",
        );
        setForecast(null);
      })
      .catch((reason) => {
        if (current) setError(reason.message || "Không thể tải dữ liệu dự toán");
      });
    return () => {
      current = false;
    };
  }, [financeProjectId]);

  const selectFile = async (nextFile) => {
    setFile(nextFile);
    setPreview(null);
    setHeaders([]);
    if (!nextFile) return;
    setLoading(true);
    setError("");
    try {
      const values = await projectTestingApi.readPayrollHeaders(nextFile);
      setHeaders(values);
      setMapping(
        Object.fromEntries(columns.map(([key]) => [key, values.includes(key) ? key : ""])),
      );
    } catch (reason) {
      setError(reason.message || "Không thể đọc tiêu đề bảng lương");
      setFile(null);
    } finally {
      setLoading(false);
    }
  };

  const runPreview = async (event) => {
    event.preventDefault();
    if (!file) return;
    setLoading(true);
    setError("");
    try {
      const result = await projectTestingApi.previewPayrollImport(file, {
        ...mapping,
        valid_until: mapping.valid_until || null,
      });
      setPreview(result);
      setSkipRows(
        new Set(
          (result.rows || [])
            .filter((row) =>
              [
                "INVALID",
                "CONFLICT_IN_FILE",
                "CONFLICT_EXISTING",
                "UNCHANGED",
                "DUPLICATE_IN_FILE",
              ].includes(row.status),
            )
            .map((row) => row.row_number),
        ),
      );
    } catch (reason) {
      setError(reason.message || "Không thể tạo bản xem trước");
    } finally {
      setLoading(false);
    }
  };

  const apply = async () => {
    if (!preview) return;
    setLoading(true);
    setError("");
    try {
      const resolutions = preview.rows
        .filter((row) => skipRows.has(row.row_number))
        .map((row) => ({ row_number: row.row_number, action: "SKIP" }));
      await projectTestingApi.applyPayrollImport(preview.preview_id, {
        expected_revision: preview.revision,
        resolutions,
      });
      setPreview(null);
      setFile(null);
      await loadRates();
    } catch (reason) {
      setError(reason.message || "Không thể áp dụng bảng đơn giá");
    } finally {
      setLoading(false);
    }
  };

  const saveCommercialTerms = async (event) => {
    event.preventDefault();
    setLoading(true);
    setError("");
    try {
      const saved = await projectTestingApi.setProjectCommercialTerms(financeProjectId, {
        ...commercialTerms,
        contract_price: String(commercialTerms.contract_price),
      });
      setCommercialTerms((current) => ({ ...current, expected_revision: saved.revision }));
    } catch (reason) {
      setError(reason.message || "Không thể lưu giá hợp đồng");
    } finally {
      setLoading(false);
    }
  };

  const loadForecast = async () => {
    if (!financeProjectId || !selectedFinancialPlanId) return;
    setLoading(true);
    setError("");
    try {
      setForecast(
        await projectTestingApi.forecastPlanLaborCost(financeProjectId, selectedFinancialPlanId),
      );
    } catch (reason) {
      setError(reason.message || "Không thể tính dự toán nhân công");
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="space-y-5">
      {error && <ErrorState message={error} />}
      <Panel title="Giá khách hàng và dự toán nhân công">
        {!projects.length ? (
          <p className="p-4 text-sm text-ink-muted">Chưa có dự án để lập dự toán.</p>
        ) : (
          <div className="space-y-4 p-4">
            <label className="field-label block">
              Dự án
              <select
                className="apple-input mt-2 w-full"
                value={financeProjectId}
                onChange={(event) => setFinanceProjectId(event.target.value)}
              >
                {projects.map((item) => (
                  <option key={item._id} value={item._id}>
                    {item.key} · {item.name}
                  </option>
                ))}
              </select>
            </label>
            <form className="grid gap-3 sm:grid-cols-2" onSubmit={saveCommercialTerms}>
              <label className="field-label">
                Giá khách hàng
                <input
                  className="apple-input mt-2 w-full"
                  type="number"
                  min="0.0001"
                  step="0.0001"
                  required
                  value={commercialTerms.contract_price}
                  onChange={(event) =>
                    setCommercialTerms((current) => ({
                      ...current,
                      contract_price: event.target.value,
                    }))
                  }
                />
              </label>
              <label className="field-label">
                Tiền tệ
                <input
                  className="apple-input mt-2 w-full uppercase"
                  minLength={3}
                  maxLength={3}
                  required
                  value={commercialTerms.currency}
                  onChange={(event) =>
                    setCommercialTerms((current) => ({
                      ...current,
                      currency: event.target.value.toUpperCase(),
                    }))
                  }
                />
              </label>
              <label className="field-label flex items-center gap-2 sm:col-span-2">
                <input
                  type="checkbox"
                  checked={commercialTerms.tax_included}
                  onChange={(event) =>
                    setCommercialTerms((current) => ({
                      ...current,
                      tax_included: event.target.checked,
                    }))
                  }
                />{" "}
                Giá đã bao gồm thuế
              </label>
              <label className="field-label sm:col-span-2">
                Phạm vi/ghi chú giá
                <textarea
                  className="apple-input mt-2 min-h-20 w-full"
                  value={commercialTerms.scope_note}
                  onChange={(event) =>
                    setCommercialTerms((current) => ({
                      ...current,
                      scope_note: event.target.value,
                    }))
                  }
                />
              </label>
              <button
                className="apple-button sm:col-span-2"
                type="submit"
                disabled={loading || !financeProjectId}
              >
                {loading ? "Đang lưu" : "Lưu giá khách hàng"}
              </button>
            </form>
            <div className="grid gap-3 sm:grid-cols-[minmax(0,1fr)_auto]">
              <label className="field-label">
                Test Plan dùng để lập dự toán
                <select
                  className="apple-input mt-2 w-full"
                  value={selectedFinancialPlanId}
                  onChange={(event) => setSelectedFinancialPlanId(event.target.value)}
                >
                  <option value="">Chọn Test Plan</option>
                  {financePlans.map((item) => (
                    <option key={item._id} value={item._id}>
                      {item.name} · {item.status}
                    </option>
                  ))}
                </select>
              </label>
              <button
                className="secondary-button self-end"
                type="button"
                disabled={loading || !selectedFinancialPlanId || !commercialTerms.contract_price}
                onClick={() => void loadForecast()}
              >
                Tính dự toán
              </button>
            </div>
            {forecast && (
              <div className="rounded-control border border-border p-4 text-sm">
                <p className="font-medium">
                  {forecast.status === "FORECAST_ONLY"
                    ? "Dự toán nhân công"
                    : "Chưa đủ dữ liệu để lập dự toán"}
                </p>
                {forecast.status === "FORECAST_ONLY" ? (
                  <div className="mt-2 grid gap-1 text-ink-muted sm:grid-cols-2">
                    <p>
                      Giá khách hàng: {forecast.customer_price} {forecast.currency}
                    </p>
                    <p>
                      Nhân công dự kiến: {forecast.estimated_labor_cost} {forecast.currency}
                    </p>
                    <p>
                      Chênh lệch trước chi phí khác: {forecast.variance} {forecast.currency}
                    </p>
                    <p>Số giờ: {forecast.planned_effort_hours}</p>
                    <p className="sm:col-span-2">
                      {forecast.comparison === "PRICE_BELOW_ESTIMATED_LABOR"
                        ? "Giá khách hàng thấp hơn riêng chi phí nhân công dự kiến."
                        : forecast.comparison === "PRICE_MATCHES_ESTIMATED_LABOR"
                          ? "Giá khách hàng bằng chi phí nhân công dự kiến."
                          : "Giá khách hàng cao hơn chi phí nhân công dự kiến."}{" "}
                      Đây chưa phải lợi nhuận hoặc giá thành thực tế.
                    </p>
                  </div>
                ) : (
                  <p className="mt-1 text-ink-muted">
                    Trạng thái: {valueLabel(forecast.status)}. Kiểm tra giờ phân bổ, ngày bắt đầu kế
                    hoạch và đơn giá còn hiệu lực.
                  </p>
                )}
              </div>
            )}
          </div>
        )}
      </Panel>
      <Panel title="Bảng đơn giá nhân công">
        <div className="space-y-4 p-4">
          <div className="flex min-w-0 flex-wrap items-center justify-between gap-3">
            <p className="min-w-0 max-w-3xl text-sm leading-5 text-ink-muted">
              Dùng mẫu CSV hoặc tệp CSV/XLSX có mã hoặc email nhân viên, đơn giá theo giờ, tiền tệ
              và thời hạn hiệu lực.
            </p>
            <button
              type="button"
              className="secondary-button shrink-0"
              onClick={() => void projectTestingApi.downloadPayrollTemplate()}
            >
              Tải mẫu CSV
            </button>
          </div>
          <form className="space-y-4" onSubmit={runPreview}>
            <label className="field-label block">
              Chọn bảng CSV hoặc XLSX
              <input
                className="peer sr-only"
                type="file"
                accept=".csv,.xlsx"
                onChange={(event) => void selectFile(event.target.files?.[0] || null)}
              />
              <span className="peer-focus-visible:ring-2 peer-focus-visible:ring-brand mt-2 flex min-h-12 min-w-0 items-center gap-3 rounded-control border border-border bg-surface px-3">
                <span className="secondary-button shrink-0">Chọn tệp</span>
                <span aria-live="polite" className="min-w-0 truncate text-sm text-ink-muted">
                  {file?.name || "Chưa chọn tệp"}
                </span>
              </span>
            </label>
            {headers.length > 0 && (
              <div className="grid min-w-0 gap-3 sm:grid-cols-2 lg:grid-cols-3">
                {columns.map(([key, label]) => (
                  <label className="field-label min-w-0" key={key}>
                    {label}
                    <select
                      className="apple-input mt-2 w-full min-w-0"
                      value={mapping[key] || ""}
                      required={key !== "valid_until"}
                      onChange={(event) =>
                        setMapping((current) => ({ ...current, [key]: event.target.value }))
                      }
                    >
                      <option value="">Không có cột</option>
                      {headers.map((header, index) => (
                        <option value={header} key={`${header}-${index}`}>
                          {header || `Cột ${index + 1}`}
                        </option>
                      ))}
                    </select>
                  </label>
                ))}
              </div>
            )}
            <button className="apple-button" type="submit" disabled={!file || loading}>
              {loading ? "Đang xử lý" : "Xem trước dữ liệu"}
            </button>
          </form>
        </div>
      </Panel>
      {preview && (
        <Panel title="Xem trước và xử lý dòng">
          <div className="max-w-full overflow-x-auto p-4 pt-0">
            <table className="w-full min-w-[760px] text-left text-sm">
              <thead>
                <tr>
                  <th className="p-2">Dòng</th>
                  <th className="p-2">Nhân viên</th>
                  <th className="p-2">Đơn giá</th>
                  <th className="p-2">Tiền tệ</th>
                  <th className="p-2">Hiệu lực</th>
                  <th className="p-2">Kết quả</th>
                  <th className="p-2">Bỏ qua</th>
                </tr>
              </thead>
              <tbody>
                {preview.rows.map((row) => (
                  <tr className="border-t border-border" key={row.row_number}>
                    <td className="p-2">{row.row_number}</td>
                    <td className="p-2">{row.user_id || row.employee_reference || "—"}</td>
                    <td className="p-2">{row.hourly_cost || "—"}</td>
                    <td className="p-2">{row.currency || "—"}</td>
                    <td className="p-2">
                      {row.valid_from || "—"} – {row.valid_until || "Không thời hạn"}
                    </td>
                    <td className="p-2">
                      {row.error_code || statusLabels[row.status] || row.status}
                    </td>
                    <td className="p-2">
                      <input
                        aria-label={`Bỏ qua dòng ${row.row_number}`}
                        type="checkbox"
                        disabled={row.status !== "READY"}
                        checked={skipRows.has(row.row_number)}
                        onChange={(event) =>
                          setSkipRows((current) => {
                            const next = new Set(current);
                            if (event.target.checked) next.add(row.row_number);
                            else next.delete(row.row_number);
                            return next;
                          })
                        }
                      />
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
          <button
            className="apple-button mt-4"
            type="button"
            disabled={loading}
            onClick={() => void apply()}
          >
            {loading ? "Đang lưu" : "Áp dụng các dòng hợp lệ"}
          </button>
        </Panel>
      )}
      <Panel title="Đơn giá đã nhập">
        {loading && !rates.length ? (
          <div className="p-4">
            <LoadingState />
          </div>
        ) : (
          <div className="max-w-full overflow-x-auto p-4 pt-0">
            <table className="w-full min-w-[640px] text-left text-sm">
              <thead>
                <tr>
                  <th className="p-2">Nhân viên</th>
                  <th className="p-2">Đơn giá/giờ</th>
                  <th className="p-2">Tiền tệ</th>
                  <th className="p-2">Thời hạn</th>
                </tr>
              </thead>
              <tbody>
                {rates.map((rate) => (
                  <tr className="border-t border-border" key={rate._id}>
                    <td className="p-2">
                      {rate.employee?.display_name || rate.employee?.email || rate.user_id}
                    </td>
                    <td className="p-2">{rate.hourly_cost}</td>
                    <td className="p-2">{rate.currency}</td>
                    <td className="p-2">
                      {rate.valid_from} – {rate.valid_until || "Không thời hạn"}
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
            {!rates.length && (
              <p className="pt-4 text-sm text-ink-muted">Chưa có đơn giá nào được nhập.</p>
            )}
          </div>
        )}
      </Panel>
    </div>
  );
}
