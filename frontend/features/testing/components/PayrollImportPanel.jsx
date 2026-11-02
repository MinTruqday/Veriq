"use client";

import { useCallback, useEffect, useRef, useState } from "react";
import { platformApi } from "@/features/authentication/services/platform.service";
import { projectTestingApi } from "../services/testing.projects";
import FilePicker from "./FilePicker";
import { ErrorState, LoadingState, Panel } from "./WorkspacePrimitives";
import { messageOf } from "../lib/testing";

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

const payrollErrorLabels = {
  PAYROLL_EMPLOYEE_REQUIRED: "Thiếu mã nhân viên hoặc email",
  PAYROLL_EMPLOYEE_NOT_FOUND: "Không tìm thấy tài khoản",
  HOURLY_COST_INVALID: "Đơn giá không hợp lệ",
  PAYROLL_CURRENCY_INVALID: "Mã tiền tệ không hợp lệ",
  PAYROLL_DATE_INVALID: "Ngày hiệu lực không hợp lệ",
  PAYROLL_PERIOD_INVALID: "Thời hạn không hợp lệ",
};

const overviewLabels = {
  FORECAST_ONLY: "Dự toán tham khảo",
  MISSING_EFFORT_ESTIMATE: "Chưa nhập giờ công dự kiến",
  MISSING_EFFORT_ALLOCATION: "Chưa phân bổ giờ công cho thành viên",
  EFFORT_ALLOCATION_MISMATCH: "Tổng giờ phân bổ chưa khớp kế hoạch",
  MISSING_PLAN_START_DATE: "Chưa có ngày bắt đầu kế hoạch",
  MISSING_LABOR_RATES: "Thiếu đơn giá còn hiệu lực",
  SCHEDULE_REQUIRED: "Chưa có lịch kế hoạch",
  CAPACITY_NOT_DECLARED: "Chưa khai báo công suất cho kỳ này",
  CAPACITY_PERIOD_NOT_COVERING_SCHEDULE:
    "Kỳ công suất không bao phủ toàn bộ lịch Test Plan; chưa áp dụng mức trần",
  AMBIGUOUS_CAPACITY_PERIOD: "Có nhiều kỳ công suất cùng áp dụng",
  PROJECT_LIMITS_PARTIALLY_DECLARED: "Đã khai báo mức trần cho một phần nhân sự",
  PROJECT_LIMIT_NOT_DECLARED: "Chưa khai báo mức trần dự án cho nhân sự",
  CAPACITY_DECLARED: "Đã khai báo công suất",
  AVAILABLE: "Có thể nhận việc",
  LIMITED: "Khả dụng có giới hạn",
  UNAVAILABLE: "Không khả dụng",
  NOT_RECORDED: "Chưa khai báo",
  QA: "QA",
  TESTER: "Tester",
  BA: "BA",
  DEVELOPER: "Nhà phát triển",
  VIEWER: "Người xem",
  ALLOCATED_PERSON_NOT_ACTIVE_PROJECT_MEMBER:
    "Có người được phân bổ không còn là thành viên đang hoạt động của dự án.",
  PERSON_AVAILABILITY_MISSING_OR_RESTRICTED:
    "Có người chưa khai báo khả dụng hoặc đang bị giới hạn khả dụng.",
  CONFIRMED_SKILL_OR_EXPERIENCE_EVIDENCE_MISSING:
    "Có hồ sơ chưa có kỹ năng hoặc kinh nghiệm được xác nhận.",
  ALLOCATED_HOURS_EXCEED_DECLARED_CAPACITY:
    "Tổng giờ phân bổ vượt công suất đã khai báo cho kỳ kế hoạch.",
  CURRENT_TEST_RUN_LOAD_EXISTS: "Một số thành viên đang tham gia các đợt kiểm thử đang diễn ra.",
  PLAN_ACTIVITY_WITHOUT_RESPONSIBLE_PERSON:
    "Có hoạt động trong Test Plan chưa có người thực hiện được chỉ định.",
  PLAN_ACTIVITY_WITHOUT_ACCOUNTABLE_PERSON:
    "Có hoạt động trong Test Plan chưa có người chịu trách nhiệm cuối cùng.",
  RESPONSIBILITY_ASSIGNED_TO_INACTIVE_OR_NONMEMBER:
    "Ma trận trách nhiệm có người không còn là thành viên đang hoạt động của dự án.",
  RESPONSIBILITY_PERSON_WITHOUT_PLAN_EFFORT_ALLOCATION:
    "Có người trong ma trận trách nhiệm nhưng chưa được phân bổ giờ trong kế hoạch.",
  PLAN_OBJECTIVE_NOT_DECLARED: "Chưa nêu mục tiêu kiểm thử.",
  PLAN_INCLUDED_SCOPE_NOT_DECLARED: "Chưa xác định phạm vi kiểm thử bao gồm.",
  PLAN_ENVIRONMENT_NOT_DECLARED: "Chưa xác định môi trường kiểm thử.",
  PLAN_ENTRY_OR_EXIT_CRITERIA_INCOMPLETE: "Chưa khai báo đủ điều kiện bắt đầu và kết thúc.",
  PLAN_TEST_DATA_SOURCE_NOT_DECLARED: "Chưa nêu nguồn dữ liệu kiểm thử.",
  PLAN_DEFECT_PROCESS_INCOMPLETE: "Quy trình xử lý lỗi chưa được khai báo đầy đủ.",
  NO_ACTIVE_QA_IN_PLAN_ALLOCATIONS: "Chưa có QA đang hoạt động trong phân bổ nguồn lực.",
  NO_ACTIVE_TESTER_IN_PLAN_ALLOCATIONS: "Chưa có Tester đang hoạt động trong phân bổ nguồn lực.",
  AVAILABILITY_NOT_CONFIRMED: "Chưa xác nhận khả dụng",
  NOT_ACTIVE_PROJECT_MEMBER: "Không còn là thành viên đang hoạt động của dự án",
  CAPACITY_NOT_DECLARED_FOR_MEMBER: "Chưa khai báo công suất cho người này",
  PLANNED_HOURS_EXCEED_AVAILABLE_CAPACITY: "Giờ của vị trí vượt công suất đã khai báo",
  MAX_CONCURRENT_PROJECTS_REACHED: "Đã chạm mức dự án tối đa trong kỳ công suất",
  NO_CONFIRMED_SKILL_OR_EXPERIENCE: "Chưa có kỹ năng hoặc kinh nghiệm được xác nhận",
};

function valueLabel(value) {
  return overviewLabels[value] || statusLabels[value] || String(value || "Chưa khai báo");
}

function displayAmount(value) {
  if (value == null || value === "") return "—";
  const amount = Number(value);
  return Number.isFinite(amount)
    ? amount.toLocaleString("vi-VN", { maximumFractionDigits: 4 })
    : "—";
}

function displayCalendarDate(value) {
  if (!value) return "—";
  const match = /^(\d{4})-(\d{2})-(\d{2})/.exec(String(value));
  if (match) return `${match[3]}/${match[2]}/${match[1]}`;
  const date = new Date(value);
  return Number.isNaN(date.getTime()) ? String(value) : date.toLocaleDateString("vi-VN");
}

function defaultCapacityPeriod() {
  const current = new Date();
  const start = new Date(current.getFullYear(), current.getMonth(), 1);
  const end = new Date(current.getFullYear(), current.getMonth() + 1, 0);
  const format = (date) =>
    `${date.getFullYear()}-${String(date.getMonth() + 1).padStart(2, "0")}-${String(date.getDate()).padStart(2, "0")}`;
  return { period_start: format(start), period_end: format(end) };
}

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
  const [commercialTermsDirty, setCommercialTermsDirty] = useState(false);
  const [financialProjectLoading, setFinancialProjectLoading] = useState(true);
  const [forecast, setForecast] = useState(null);
  const [forecastLoading, setForecastLoading] = useState(false);
  const forecastRequestId = useRef(0);
  const [capacityPeriods, setCapacityPeriods] = useState([]);
  const [capacityUsers, setCapacityUsers] = useState([]);
  const [selectedCapacityPeriod, setSelectedCapacityPeriod] = useState("new");
  const [capacityRange, setCapacityRange] = useState(defaultCapacityPeriod);
  const [capacityRevision, setCapacityRevision] = useState(0);
  const [capacityRows, setCapacityRows] = useState([]);
  const [capacityLoading, setCapacityLoading] = useState(false);
  const [capacityError, setCapacityError] = useState("");
  const [capacitySaved, setCapacitySaved] = useState(false);
  const capacityRequestId = useRef(0);
  const payrollHeadersRequestId = useRef(0);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState("");

  const loadRates = useCallback(async () => {
    setLoading(true);
    setError("");
    try {
      setRates(await projectTestingApi.listPayrollRates());
    } catch (reason) {
      setError(messageOf(reason) || "Không thể tải bảng đơn giá");
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    void loadRates();
  }, [loadRates]);

  const loadCapacity = useCallback(async (selection = "new") => {
    const requestId = ++capacityRequestId.current;
    setCapacityLoading(true);
    setCapacityError("");
    try {
      const [periods, users] = await Promise.all([
        projectTestingApi.listCapacityPeriods(),
        platformApi.listUsers(),
      ]);
      if (requestId !== capacityRequestId.current) return;
      const safePeriods = Array.isArray(periods) ? periods : [];
      const safeUsers = Array.isArray(users) ? users.filter((item) => item.is_active) : [];
      setCapacityPeriods(safePeriods);
      setCapacityUsers(safeUsers);
      const existing = safePeriods.find((item) => item._id === selection);
      if (existing) {
        setCapacityRange({
          period_start: existing.period_start,
          period_end: existing.period_end,
        });
        setCapacityRevision(existing.revision || 0);
        setCapacityRows(
          (existing.entries || []).map((entry) => ({
            user_id: entry.user_id,
            available_hours: String(entry.available_hours ?? ""),
            max_concurrent_projects:
              entry.max_concurrent_projects == null ? "" : String(entry.max_concurrent_projects),
          })),
        );
      } else if (selection === "new") {
        setCapacityRange(defaultCapacityPeriod());
        setCapacityRevision(0);
        setCapacityRows([]);
      } else if (safePeriods.length) {
        const first = safePeriods[0];
        setSelectedCapacityPeriod(first._id);
        setCapacityRange({ period_start: first.period_start, period_end: first.period_end });
        setCapacityRevision(first.revision || 0);
        setCapacityRows(
          (first.entries || []).map((entry) => ({
            user_id: entry.user_id,
            available_hours: String(entry.available_hours ?? ""),
            max_concurrent_projects:
              entry.max_concurrent_projects == null ? "" : String(entry.max_concurrent_projects),
          })),
        );
      }
    } catch (reason) {
      if (requestId === capacityRequestId.current) {
        setCapacityError(messageOf(reason) || "Không thể tải công suất nhân sự");
      }
    } finally {
      if (requestId === capacityRequestId.current) setCapacityLoading(false);
    }
  }, []);

  useEffect(() => {
    void loadCapacity(selectedCapacityPeriod);
  }, [loadCapacity, selectedCapacityPeriod]);

  const selectCapacityPeriod = (value) => {
    capacityRequestId.current += 1;
    setSelectedCapacityPeriod(value);
    setCapacitySaved(false);
    const period = capacityPeriods.find((item) => item._id === value);
    if (!period) {
      setCapacityRange(defaultCapacityPeriod());
      setCapacityRevision(0);
      setCapacityRows([]);
      return;
    }
    setCapacityRange({ period_start: period.period_start, period_end: period.period_end });
    setCapacityRevision(period.revision || 0);
    setCapacityRows(
      (period.entries || []).map((entry) => ({
        user_id: entry.user_id,
        available_hours: String(entry.available_hours ?? ""),
        max_concurrent_projects:
          entry.max_concurrent_projects == null ? "" : String(entry.max_concurrent_projects),
      })),
    );
  };

  const updateCapacityRow = (index, key, value) => {
    setCapacitySaved(false);
    setCapacityRows((current) =>
      current.map((row, rowIndex) => (rowIndex === index ? { ...row, [key]: value } : row)),
    );
  };

  const updateCommercialTerms = (changes) => {
    forecastRequestId.current += 1;
    setForecastLoading(false);
    setForecast(null);
    setCommercialTermsDirty(true);
    setCommercialTerms((current) => ({ ...current, ...changes }));
  };

  const saveCapacity = async (event) => {
    event.preventDefault();
    setCapacityLoading(true);
    setCapacityError("");
    setCapacitySaved(false);
    try {
      const entries = capacityRows.map((row) => ({
        user_id: row.user_id,
        available_hours: Number(row.available_hours),
        max_concurrent_projects: row.max_concurrent_projects
          ? Number(row.max_concurrent_projects)
          : null,
      }));
      const saved = await projectTestingApi.updateCapacityPeriod({
        expected_revision: capacityRevision,
        ...capacityRange,
        entries,
      });
      setCapacityRevision(saved.revision || capacityRevision + 1);
      setSelectedCapacityPeriod(saved._id || selectedCapacityPeriod);
      setCapacitySaved(true);
      await loadCapacity(saved._id || selectedCapacityPeriod);
    } catch (reason) {
      setCapacityError(messageOf(reason) || "Không thể lưu công suất nhân sự");
    } finally {
      setCapacityLoading(false);
    }
  };

  useEffect(() => {
    projectTestingApi
      .listFinancialProjects()
      .then((items) => {
        setProjects(items);
        setFinanceProjectId((current) => current || items[0]?._id || "");
      })
      .catch((reason) => setError(messageOf(reason) || "Không thể tải dự án"));
  }, []);

  useEffect(() => {
    let current = true;
    if (!financeProjectId) {
      setFinancialProjectLoading(false);
      return () => {
        current = false;
      };
    }
    setFinancialProjectLoading(true);
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
        setCommercialTermsDirty(false);
        setFinancePlans(plans);
        setSelectedFinancialPlanId((selected) =>
          plans.some((item) => item._id === selected) ? selected : "",
        );
        setForecast(null);
      })
      .catch((reason) => {
        if (current) setError(messageOf(reason) || "Không thể tải dữ liệu dự toán");
      })
      .finally(() => {
        if (current) setFinancialProjectLoading(false);
      });
    return () => {
      current = false;
    };
  }, [financeProjectId]);

  const selectFile = async (nextFile) => {
    const requestId = ++payrollHeadersRequestId.current;
    setFile(nextFile);
    setPreview(null);
    setHeaders([]);
    if (!nextFile) {
      setLoading(false);
      return;
    }
    setLoading(true);
    setError("");
    try {
      const values = await projectTestingApi.readPayrollHeaders(nextFile);
      if (requestId !== payrollHeadersRequestId.current) return;
      if (!Array.isArray(values) || !values.length) {
        throw new Error(
          "Không tìm thấy hàng tiêu đề trong tệp. Hãy kiểm tra nội dung hoặc định dạng tệp.",
        );
      }
      setHeaders(values);
      setMapping(
        Object.fromEntries(columns.map(([key]) => [key, values.includes(key) ? key : ""])),
      );
    } catch (reason) {
      if (requestId === payrollHeadersRequestId.current) {
        setError(messageOf(reason) || "Không thể đọc tiêu đề bảng lương");
      }
    } finally {
      if (requestId === payrollHeadersRequestId.current) setLoading(false);
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
      setError(messageOf(reason) || "Không thể tạo bản xem trước");
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
      payrollHeadersRequestId.current += 1;
      setFile(null);
      await loadRates();
    } catch (reason) {
      setError(messageOf(reason) || "Không thể áp dụng bảng đơn giá");
    } finally {
      setLoading(false);
    }
  };

  const saveCommercialTerms = async (event) => {
    event.preventDefault();
    const contractPriceValue = String(commercialTerms.contract_price ?? "");
    const contractPrice = Number(contractPriceValue);
    const decimalPlaces = contractPriceValue.split(".")[1]?.length || 0;
    if (!Number.isFinite(contractPrice) || contractPrice <= 0 || decimalPlaces > 4) {
      setError("Nhập giá khách hàng lớn hơn 0 và tối đa 4 chữ số thập phân.");
      return;
    }
    setLoading(true);
    setError("");
    try {
      const saved = await projectTestingApi.setProjectCommercialTerms(financeProjectId, {
        ...commercialTerms,
        contract_price: String(commercialTerms.contract_price),
      });
      setCommercialTerms((current) => ({ ...current, expected_revision: saved.revision }));
      setCommercialTermsDirty(false);
    } catch (reason) {
      setError(messageOf(reason) || "Không thể lưu giá hợp đồng");
    } finally {
      setLoading(false);
    }
  };

  const loadForecast = async () => {
    if (
      !financeProjectId ||
      !selectedFinancialPlanId ||
      !commercialTerms.expected_revision ||
      commercialTermsDirty
    ) {
      return;
    }
    const requestId = ++forecastRequestId.current;
    const requestedProjectId = financeProjectId;
    const requestedPlanId = selectedFinancialPlanId;
    setForecastLoading(true);
    setError("");
    try {
      const result = await projectTestingApi.forecastPlanLaborCost(
        requestedProjectId,
        requestedPlanId,
      );
      if (requestId === forecastRequestId.current) setForecast(result);
    } catch (reason) {
      if (requestId === forecastRequestId.current) {
        setError(messageOf(reason) || "Không thể tính dự toán nhân công");
      }
    } finally {
      if (requestId === forecastRequestId.current) setForecastLoading(false);
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
                disabled={financialProjectLoading || loading || forecastLoading}
                onChange={(event) => {
                  forecastRequestId.current += 1;
                  setForecastLoading(false);
                  setForecast(null);
                  setError("");
                  setCommercialTermsDirty(false);
                  setCommercialTerms({
                    expected_revision: 0,
                    contract_price: "",
                    currency: "VND",
                    tax_included: true,
                    scope_note: "",
                  });
                  setFinancePlans([]);
                  setSelectedFinancialPlanId("");
                  setFinancialProjectLoading(true);
                  setFinanceProjectId(event.target.value);
                }}
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
                  disabled={financialProjectLoading || loading || forecastLoading}
                  value={commercialTerms.contract_price}
                  onChange={(event) =>
                    updateCommercialTerms({ contract_price: event.target.value })
                  }
                />
                {commercialTerms.contract_price !== "" && (
                  <span className="mt-1 block text-sm font-medium text-ink">
                    {displayAmount(commercialTerms.contract_price)} {commercialTerms.currency}
                  </span>
                )}
              </label>
              <label className="field-label">
                Tiền tệ
                <input
                  className="apple-input mt-2 w-full uppercase"
                  minLength={3}
                  maxLength={3}
                  required
                  disabled={financialProjectLoading || loading || forecastLoading}
                  value={commercialTerms.currency}
                  onChange={(event) =>
                    updateCommercialTerms({ currency: event.target.value.toUpperCase() })
                  }
                />
              </label>
              <label className="field-label flex items-center gap-2 sm:col-span-2">
                <input
                  type="checkbox"
                  checked={commercialTerms.tax_included}
                  disabled={financialProjectLoading || loading || forecastLoading}
                  onChange={(event) =>
                    updateCommercialTerms({ tax_included: event.target.checked })
                  }
                />{" "}
                Giá đã bao gồm thuế
              </label>
              <label className="field-label sm:col-span-2">
                Phạm vi/ghi chú giá
                <textarea
                  className="apple-input mt-2 min-h-20 w-full"
                  value={commercialTerms.scope_note}
                  disabled={financialProjectLoading || loading || forecastLoading}
                  onChange={(event) => updateCommercialTerms({ scope_note: event.target.value })}
                />
              </label>
              <button
                className="apple-button sm:col-span-2"
                type="submit"
                disabled={
                  financialProjectLoading || loading || forecastLoading || !financeProjectId
                }
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
                  disabled={financialProjectLoading || loading || forecastLoading}
                  onChange={(event) => {
                    forecastRequestId.current += 1;
                    setForecastLoading(false);
                    setForecast(null);
                    setSelectedFinancialPlanId(event.target.value);
                  }}
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
                disabled={
                  financialProjectLoading ||
                  loading ||
                  forecastLoading ||
                  !selectedFinancialPlanId ||
                  !commercialTerms.expected_revision ||
                  commercialTermsDirty
                }
                onClick={() => void loadForecast()}
              >
                {forecastLoading ? "Đang tính…" : "Tính dự toán"}
              </button>
            </div>
            {commercialTermsDirty || !commercialTerms.expected_revision ? (
              <p className="text-sm text-ink-muted">
                Lưu giá khách hàng của dự án trước khi tính dự toán.
              </p>
            ) : null}
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
                      Giá khách hàng: {displayAmount(forecast.customer_price)} {forecast.currency}
                    </p>
                    <p>
                      Nhân công dự kiến: {displayAmount(forecast.estimated_labor_cost)}{" "}
                      {forecast.currency}
                    </p>
                    <p>
                      Chênh lệch trước chi phí khác: {displayAmount(forecast.variance)}{" "}
                      {forecast.currency}
                    </p>
                    <p>Số giờ: {displayAmount(forecast.planned_effort_hours)}</p>
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
                {forecast.resource_overview && (
                  <section className="mt-4 border-t border-border pt-4">
                    <h3 className="font-medium">Nguồn lực và bối cảnh kế hoạch</h3>
                    <div className="mt-3 grid gap-2 text-ink-muted sm:grid-cols-2 lg:grid-cols-4">
                      <p>
                        Người được phân bổ:{" "}
                        {forecast.resource_overview.people_summary.planned_people}
                      </p>
                      <p>
                        Thành viên dự án đang hoạt động:{" "}
                        {forecast.resource_overview.people_summary.active_project_members}
                      </p>
                      <p>
                        Hồ sơ chưa có dẫn chứng xác nhận:{" "}
                        {
                          forecast.resource_overview.people_summary
                            .without_confirmed_profile_evidence
                        }
                      </p>
                      <p>
                        Rủi ro đang mở: {forecast.resource_overview.plan_context.open_risk_count}
                        {forecast.resource_overview.plan_context.risk_exposure_total
                          ? ` · mức phơi nhiễm ${displayAmount(forecast.resource_overview.plan_context.risk_exposure_total)}`
                          : ""}
                      </p>
                      <p>
                        Mốc kế hoạch đang mở:{" "}
                        {forecast.resource_overview.plan_context.open_milestone_count} /{" "}
                        {forecast.resource_overview.plan_context.milestone_count}
                      </p>
                      <p>
                        Phụ thuộc / bên liên quan:{" "}
                        {forecast.resource_overview.plan_context.dependency_count} /{" "}
                        {forecast.resource_overview.plan_context.stakeholder_count}
                      </p>
                      <p>
                        Thời lượng kế hoạch:{" "}
                        {forecast.resource_overview.plan_context.schedule_duration_days == null
                          ? "Chưa xác định"
                          : `${forecast.resource_overview.plan_context.schedule_duration_days} ngày`}
                      </p>
                      <p>
                        Yêu cầu trong phạm vi:{" "}
                        {forecast.resource_overview.plan_context.requirement_version_count}
                      </p>
                      <p>
                        Ca kiểm thử trong phạm vi:{" "}
                        {forecast.resource_overview.plan_context.test_case_version_count}
                      </p>
                      <p>
                        Bộ kiểm thử trong phạm vi:{" "}
                        {forecast.resource_overview.plan_context.test_suite_count}
                      </p>
                      <p>
                        Môi trường:{" "}
                        {forecast.resource_overview.plan_context.environment || "Chưa chọn"}
                      </p>
                      <p>
                        Cấp kiểm thử:{" "}
                        {forecast.resource_overview.plan_context.test_level || "Chưa chọn"}
                      </p>
                      <p>
                        Phiên bản phát hành:{" "}
                        {forecast.resource_overview.plan_context.release || "Chưa chọn"}
                      </p>
                      <p>
                        Thời gian:{" "}
                        {displayCalendarDate(
                          forecast.resource_overview.plan_context.planned_start_at,
                        )}{" "}
                        –{" "}
                        {displayCalendarDate(
                          forecast.resource_overview.plan_context.planned_end_at,
                        )}
                      </p>
                      <p>
                        Phạm vi bao gồm / loại trừ:{" "}
                        {forecast.resource_overview.plan_context.scope_in_count} /{" "}
                        {forecast.resource_overview.plan_context.scope_out_count}
                      </p>
                      <p>
                        Điều kiện bắt đầu / kết thúc:{" "}
                        {forecast.resource_overview.plan_context.entry_criteria_count} /{" "}
                        {forecast.resource_overview.plan_context.exit_criteria_count}
                      </p>
                      <p className="sm:col-span-2 lg:col-span-4">
                        Hoạt động có người thực hiện / người chịu trách nhiệm cuối:{" "}
                        {forecast.resource_overview.plan_context.responsibility_activity_count -
                          forecast.resource_overview.plan_context
                            .activities_without_responsible_person}{" "}
                        / {forecast.resource_overview.plan_context.accountable_activity_count}
                      </p>
                      <p className="sm:col-span-2 lg:col-span-4">
                        Loại kiểm thử:{" "}
                        {forecast.resource_overview.plan_context.test_types
                          .map(valueLabel)
                          .join(", ") || "Chưa xác định"}
                      </p>
                      {forecast.resource_overview.plan_context.test_approach && (
                        <p className="sm:col-span-2 lg:col-span-4">
                          Cách tiếp cận: {forecast.resource_overview.plan_context.test_approach}
                        </p>
                      )}
                      {forecast.resource_overview.plan_context.objective && (
                        <p className="sm:col-span-2 lg:col-span-4">
                          Mục tiêu: {forecast.resource_overview.plan_context.objective}
                        </p>
                      )}
                      {forecast.commercial_scope_note && (
                        <p className="sm:col-span-2 lg:col-span-4">
                          Ghi chú phạm vi và giá khách hàng: {forecast.commercial_scope_note}
                        </p>
                      )}
                      <p>
                        Công suất theo lịch:{" "}
                        {valueLabel(forecast.resource_overview.capacity.status)}
                      </p>
                      <p>
                        Giờ được phân bổ / công suất đã khai báo:{" "}
                        {displayAmount(forecast.resource_overview.capacity.allocated_hours)}
                        {forecast.resource_overview.capacity.declared_available_hours == null
                          ? " / chưa có dữ liệu"
                          : ` / ${displayAmount(forecast.resource_overview.capacity.declared_available_hours)}`}
                      </p>
                    </div>
                    <div className="mt-3 rounded-control border border-border p-3">
                      <h4 className="font-medium">Độ phủ đội ngũ và trách nhiệm</h4>
                      <div className="mt-2 grid gap-2 text-sm text-ink-muted sm:grid-cols-2 lg:grid-cols-4">
                        <p>
                          QA được phân bổ:{" "}
                          {forecast.resource_overview.team_coverage.role_member_counts.QA}
                        </p>
                        <p>
                          Tester được phân bổ:{" "}
                          {forecast.resource_overview.team_coverage.role_member_counts.TESTER}
                        </p>
                        <p>
                          Người trong ma trận trách nhiệm:{" "}
                          {forecast.resource_overview.team_coverage.responsibility_user_count}
                        </p>
                        <p>
                          Người chịu trách nhiệm cuối:{" "}
                          {forecast.resource_overview.team_coverage.accountable_user_count}
                        </p>
                        <p className="sm:col-span-2 lg:col-span-4">
                          Người trong ma trận nhưng chưa có phân bổ giờ trong kế hoạch:{" "}
                          {
                            forecast.resource_overview.team_coverage
                              .responsibility_assignments_outside_plan_allocations
                          }
                        </p>
                      </div>
                    </div>
                    <details className="mt-3 rounded-control border border-border p-3">
                      <summary className="cursor-pointer font-medium">
                        Mức đầy đủ của Test Plan
                      </summary>
                      <div className="mt-3 grid gap-2 text-sm text-ink-muted sm:grid-cols-2 lg:grid-cols-3">
                        <p>
                          Mục tiêu:{" "}
                          {forecast.resource_overview.plan_context.plan_completeness
                            .objective_declared
                            ? "Đã nêu"
                            : "Chưa nêu"}
                        </p>
                        <p>
                          Nguồn dữ liệu kiểm thử:{" "}
                          {
                            forecast.resource_overview.plan_context.plan_completeness
                              .test_data_sources_count
                          }
                        </p>
                        <p>
                          Chuẩn bị dữ liệu:{" "}
                          {forecast.resource_overview.plan_context.plan_completeness
                            .test_data_preparation_declared
                            ? "Đã nêu"
                            : "Chưa nêu"}
                        </p>
                        <p>
                          Quy trình xử lý lỗi:{" "}
                          {
                            forecast.resource_overview.plan_context.plan_completeness
                              .defect_process_fields_completed
                          }{" "}
                          / 5 nội dung
                        </p>
                        <p>
                          Tần suất báo cáo:{" "}
                          {forecast.resource_overview.plan_context.plan_completeness
                            .communication_frequency_declared
                            ? "Đã nêu"
                            : "Chưa nêu"}
                        </p>
                        <p>
                          Mục tiêu chất lượng / chỉ số theo dõi:{" "}
                          {
                            forecast.resource_overview.plan_context.plan_completeness
                              .quality_target_count
                          }{" "}
                          /{" "}
                          {
                            forecast.resource_overview.plan_context.plan_completeness
                              .monitoring_metric_count
                          }
                        </p>
                        <p>
                          Giả định / ràng buộc:{" "}
                          {
                            forecast.resource_overview.plan_context.plan_completeness
                              .assumption_count
                          }{" "}
                          /{" "}
                          {
                            forecast.resource_overview.plan_context.plan_completeness
                              .constraint_count
                          }
                        </p>
                        <p>
                          Hoạt động có người thực hiện:{" "}
                          {
                            forecast.resource_overview.plan_context.plan_completeness
                              .responsible_activity_count
                          }{" "}
                          /{" "}
                          {
                            forecast.resource_overview.plan_context.plan_completeness
                              .responsibility_activity_count
                          }
                        </p>
                        <p>
                          Hoạt động có người chịu trách nhiệm cuối:{" "}
                          {
                            forecast.resource_overview.plan_context.plan_completeness
                              .accountable_activity_count
                          }{" "}
                          /{" "}
                          {
                            forecast.resource_overview.plan_context.plan_completeness
                              .responsibility_activity_count
                          }
                        </p>
                      </div>
                      {!!forecast.resource_overview.plan_context.scope_in.length && (
                        <div className="mt-3 text-sm">
                          <p className="font-medium">Trong phạm vi</p>
                          <ul className="mt-1 list-inside list-disc text-ink-muted">
                            {forecast.resource_overview.plan_context.scope_in.map((item, index) => (
                              <li key={`${index}-${item}`}>{item}</li>
                            ))}
                          </ul>
                        </div>
                      )}
                      {!!forecast.resource_overview.plan_context.scope_out.length && (
                        <div className="mt-3 text-sm">
                          <p className="font-medium">Ngoài phạm vi</p>
                          <ul className="mt-1 list-inside list-disc text-ink-muted">
                            {forecast.resource_overview.plan_context.scope_out.map(
                              (item, index) => (
                                <li key={`${index}-${item}`}>{item}</li>
                              ),
                            )}
                          </ul>
                        </div>
                      )}
                    </details>
                    {forecast.resource_overview.capacity.hours_covered === false && (
                      <p className="mt-2 text-danger">
                        Tổng giờ phân bổ vượt công suất đã khai báo cho kỳ kế hoạch.
                      </p>
                    )}
                    {forecast.resource_overview.warnings.length > 0 && (
                      <ul className="mt-3 list-inside list-disc space-y-1 text-ink-muted">
                        {forecast.resource_overview.warnings.map((warning) => (
                          <li key={warning}>{valueLabel(warning)}</li>
                        ))}
                      </ul>
                    )}
                    {forecast.resource_overview.people.length > 0 && (
                      <div className="mt-3 overflow-x-auto rounded-control border border-border">
                        <table className="w-full min-w-[760px] text-left">
                          <thead className="bg-surface-muted text-xs text-ink-muted">
                            <tr>
                              <th className="p-2 font-medium">Người được phân bổ</th>
                              <th className="p-2 font-medium">Vai trò</th>
                              <th className="p-2 font-medium">Kỹ năng / kinh nghiệm xác nhận</th>
                              <th className="p-2 font-medium">Khả dụng</th>
                              <th className="p-2 font-medium">Giờ kế hoạch</th>
                              <th className="p-2 font-medium">Tải đang chạy</th>
                            </tr>
                          </thead>
                          <tbody>
                            {forecast.resource_overview.people.map((person) => (
                              <tr key={person.user_id} className="border-t border-border">
                                <td className="p-2">{person.label}</td>
                                <td className="p-2">
                                  {person.roles.map(valueLabel).join(", ") ||
                                    "Chưa có vai trò đang hoạt động"}
                                </td>
                                <td className="p-2">
                                  {person.confirmed_skills.length ||
                                  person.confirmed_experience_count ? (
                                    <details>
                                      <summary className="cursor-pointer">
                                        {person.confirmed_skill_count} kỹ năng ·{" "}
                                        {person.confirmed_experience_count} kinh nghiệm
                                      </summary>
                                      <div className="mt-1 space-y-1 text-xs text-ink-muted">
                                        {!!person.confirmed_skills.length && (
                                          <p>Kỹ năng: {person.confirmed_skills.join(", ")}</p>
                                        )}
                                        {person.confirmed_experiences.map((experience, index) => (
                                          <p key={`${person.user_id}-${index}`}>
                                            {experience.title}
                                            {experience.domain ? ` · ${experience.domain}` : ""}
                                            {experience.technologies.length
                                              ? ` · ${experience.technologies.join(", ")}`
                                              : ""}
                                          </p>
                                        ))}
                                      </div>
                                    </details>
                                  ) : (
                                    "Chưa có dữ liệu xác nhận"
                                  )}
                                </td>
                                <td className="p-2">{valueLabel(person.availability)}</td>
                                <td className="p-2">{displayAmount(person.planned_hours)}</td>
                                <td className="p-2">
                                  {person.active_test_case_count_across_projects} ca ·{" "}
                                  {person.active_test_run_count_across_projects} lượt chạy ·{" "}
                                  {person.active_project_count} dự án có lượt chạy mở
                                </td>
                              </tr>
                            ))}
                          </tbody>
                        </table>
                      </div>
                    )}
                    {forecast.resource_overview.staffing_options && (
                      <div className="mt-4 rounded-control border border-border p-3">
                        <h4 className="font-medium">So sánh phương án nhân sự</h4>
                        <p className="mt-1 text-sm text-ink-muted">
                          Mỗi dòng giữ nguyên số giờ của một vị trí và thay tối đa một người trong
                          đội hiện tại. Đơn giá cho biết tác động ngân sách; kỹ năng, kinh nghiệm,
                          khả dụng và tải việc được trình bày riêng để người phụ trách cân nhắc.
                        </p>
                        <p className="mt-1 text-sm text-ink-muted">
                          {forecast.resource_overview.staffing_options.project_limit_configured
                            ? "Mức trần được hiển thị trong từng phương án và kiểm tra khi lưu phân bổ Test Plan."
                            : `${valueLabel(forecast.resource_overview.staffing_options.project_limit_status)}; hệ thống không tự đặt giới hạn.`}
                        </p>
                        {forecast.resource_overview.staffing_options.slots.length ? (
                          <div className="mt-3 space-y-3">
                            {forecast.resource_overview.staffing_options.slots.map((slot) => (
                              <details
                                key={slot.current_user_id}
                                className="rounded-control border border-border p-3"
                              >
                                <summary className="cursor-pointer font-medium">
                                  {slot.current_label} ·{" "}
                                  {slot.current_roles.map(valueLabel).join(", ") ||
                                    "Chưa rõ vai trò"}{" "}
                                  · {displayAmount(slot.planned_hours)} giờ
                                </summary>
                                <div className="mt-3 overflow-x-auto">
                                  <table className="w-full min-w-[1050px] text-left text-sm">
                                    <thead className="bg-surface-muted text-xs text-ink-muted">
                                      <tr>
                                        <th className="p-2 font-medium">Người</th>
                                        <th className="p-2 font-medium">Vai trò</th>
                                        <th className="p-2 font-medium">Kỹ năng / kinh nghiệm</th>
                                        <th className="p-2 font-medium">Khả dụng · tải</th>
                                        <th className="p-2 font-medium">Đơn giá/giờ</th>
                                        <th className="p-2 font-medium">
                                          Chi phí đội sau thay đổi
                                        </th>
                                        <th className="p-2 font-medium">Chênh lệch</th>
                                      </tr>
                                    </thead>
                                    <tbody>
                                      {slot.candidates.map((candidate) => (
                                        <tr
                                          key={candidate.user_id}
                                          className="border-t border-border align-top"
                                        >
                                          <td className="p-2">
                                            {candidate.label}
                                            {candidate.is_current_assignee && (
                                              <span className="ml-1 text-ink-muted">
                                                (hiện tại)
                                              </span>
                                            )}
                                          </td>
                                          <td className="p-2">
                                            {candidate.roles.map(valueLabel).join(", ") || "—"}
                                          </td>
                                          <td className="max-w-64 p-2">
                                            {candidate.confirmed_skills.join(", ") ||
                                              "Chưa có kỹ năng"}
                                            {candidate.confirmed_experiences.length > 0 && (
                                              <span className="block text-ink-muted">
                                                {candidate.confirmed_experiences.join(", ")}
                                              </span>
                                            )}
                                          </td>
                                          <td className="p-2">
                                            {valueLabel(candidate.availability)} ·{" "}
                                            {candidate.active_test_case_count} ca ·{" "}
                                            {candidate.active_test_run_count} lượt ·{" "}
                                            {candidate.active_project_count} dự án có lượt chạy mở
                                            {candidate.max_concurrent_projects != null && (
                                              <span className="block text-ink-muted">
                                                Mức tối đa: {candidate.max_concurrent_projects} dự
                                                án
                                                {candidate.project_limit_reached
                                                  ? " · Đã chạm mức"
                                                  : " · Còn trong mức"}
                                              </span>
                                            )}
                                            {candidate.declared_available_hours != null && (
                                              <span className="block text-ink-muted">
                                                Công suất:{" "}
                                                {displayAmount(candidate.declared_available_hours)}{" "}
                                                giờ
                                              </span>
                                            )}
                                          </td>
                                          <td className="p-2">
                                            {candidate.hourly_cost == null
                                              ? "Thiếu đơn giá"
                                              : `${displayAmount(candidate.hourly_cost)} ${candidate.currency}`}
                                          </td>
                                          <td className="p-2">
                                            {candidate.estimated_team_labor_cost == null
                                              ? "Chưa đủ đơn giá đội"
                                              : `${displayAmount(candidate.estimated_team_labor_cost)} ${forecast.resource_overview.staffing_options.currency}`}
                                          </td>
                                          <td className="p-2">
                                            {candidate.cost_change_from_current == null
                                              ? "Chưa tính được"
                                              : `${Number(candidate.cost_change_from_current) > 0 ? "+" : ""}${displayAmount(candidate.cost_change_from_current)} ${forecast.resource_overview.staffing_options.currency}`}
                                            {!!candidate.review_factors.length && (
                                              <span className="block text-ink-muted">
                                                {candidate.review_factors
                                                  .map(valueLabel)
                                                  .join("; ")}
                                              </span>
                                            )}
                                          </td>
                                        </tr>
                                      ))}
                                    </tbody>
                                  </table>
                                </div>
                              </details>
                            ))}
                          </div>
                        ) : (
                          <p className="mt-2 text-sm text-ink-muted">
                            Chưa có phân bổ nhân sự trong Test Plan để so sánh.
                          </p>
                        )}
                        <ul className="mt-3 list-disc space-y-1 pl-5 text-xs text-ink-muted">
                          {forecast.resource_overview.staffing_options.limitations.map((item) => (
                            <li key={item}>{item}</li>
                          ))}
                        </ul>
                      </div>
                    )}
                    <p className="mt-3 text-xs text-ink-muted">
                      Đánh giá nguồn lực dựa trên vai trò, năng lực có xác nhận, khả dụng, tải và
                      công suất. Đơn giá dùng để so sánh tác động ngân sách giữa các phương án,
                      không phải thước đo năng lực; người phụ trách tự chọn và cập nhật phân công
                      trong Test Plan.
                    </p>
                  </section>
                )}
              </div>
            )}
          </div>
        )}
      </Panel>
      <Panel title="Công suất và giới hạn phân công">
        <form className="space-y-4 p-4" onSubmit={saveCapacity}>
          <p className="text-sm text-ink-muted">
            Chỉ Admin được quản lý. Mức tối đa để trống nghĩa là chưa cấu hình giới hạn cho nhân
            viên. AI chỉ áp dụng giới hạn khi các kỳ công suất liền nhau bao phủ toàn bộ lịch Test
            Plan; kỳ giao nhau bị từ chối để tránh dùng hai mức trần cùng lúc.
          </p>
          {capacityError && <ErrorState message={capacityError} />}
          {capacitySaved && (
            <p className="text-sm text-success" role="status">
              Đã lưu công suất và giới hạn phân công.
            </p>
          )}
          <div className="grid gap-3 md:grid-cols-3">
            <label className="field-label block">
              Kỳ công suất
              <select
                className="apple-input mt-2 w-full"
                value={selectedCapacityPeriod}
                disabled={capacityLoading}
                onChange={(event) => selectCapacityPeriod(event.target.value)}
              >
                <option value="new">Tạo kỳ mới</option>
                {capacityPeriods.map((period) => (
                  <option key={period._id} value={period._id}>
                    {displayCalendarDate(period.period_start)} –{" "}
                    {displayCalendarDate(period.period_end)}
                  </option>
                ))}
              </select>
            </label>
            <label className="field-label block">
              Bắt đầu
              <input
                className="apple-input mt-2 w-full"
                type="date"
                required
                disabled={capacityLoading || selectedCapacityPeriod !== "new"}
                value={capacityRange.period_start}
                onChange={(event) =>
                  setCapacityRange((current) => ({ ...current, period_start: event.target.value }))
                }
              />
            </label>
            <label className="field-label block">
              Kết thúc
              <input
                className="apple-input mt-2 w-full"
                type="date"
                required
                disabled={capacityLoading || selectedCapacityPeriod !== "new"}
                value={capacityRange.period_end}
                onChange={(event) =>
                  setCapacityRange((current) => ({ ...current, period_end: event.target.value }))
                }
              />
            </label>
          </div>
          <div className="max-w-full overflow-x-auto">
            <table className="w-full min-w-[760px] text-left text-sm">
              <thead>
                <tr>
                  <th className="p-2">Nhân viên</th>
                  <th className="p-2">Giờ khả dụng</th>
                  <th className="p-2">Số dự án tối đa đồng thời</th>
                  <th className="p-2">Thao tác</th>
                </tr>
              </thead>
              <tbody>
                {capacityRows.map((row, index) => (
                  <tr className="border-t border-border align-top" key={`${row.user_id}-${index}`}>
                    <td className="min-w-64 p-2">
                      <select
                        className="apple-input w-full"
                        required
                        disabled={capacityLoading}
                        value={row.user_id}
                        onChange={(event) =>
                          updateCapacityRow(index, "user_id", event.target.value)
                        }
                      >
                        <option value="">Chọn nhân viên</option>
                        {capacityUsers.map((person) => (
                          <option key={person._id} value={person._id}>
                            {person.full_name || person.email} · {person.email}
                          </option>
                        ))}
                      </select>
                    </td>
                    <td className="min-w-40 p-2">
                      <input
                        className="apple-input w-full"
                        type="number"
                        min="0"
                        step="0.25"
                        required
                        disabled={capacityLoading}
                        value={row.available_hours}
                        onChange={(event) =>
                          updateCapacityRow(index, "available_hours", event.target.value)
                        }
                      />
                    </td>
                    <td className="min-w-48 p-2">
                      <input
                        className="apple-input w-full"
                        type="number"
                        min="1"
                        step="1"
                        disabled={capacityLoading}
                        value={row.max_concurrent_projects}
                        onChange={(event) =>
                          updateCapacityRow(index, "max_concurrent_projects", event.target.value)
                        }
                      />
                      <span className="mt-1 block text-xs text-ink-muted">
                        Để trống nếu chưa có giới hạn đã duyệt.
                      </span>
                    </td>
                    <td className="p-2">
                      <button
                        className="apple-button-secondary"
                        type="button"
                        disabled={capacityLoading}
                        onClick={() =>
                          setCapacityRows((current) =>
                            current.filter((_, rowIndex) => rowIndex !== index),
                          )
                        }
                      >
                        Gỡ
                      </button>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
            {!capacityRows.length && (
              <p className="py-4 text-sm text-ink-muted">
                Chưa có nhân viên trong kỳ công suất này.
              </p>
            )}
          </div>
          <div className="flex flex-wrap gap-2">
            <button
              className="apple-button-secondary"
              type="button"
              disabled={capacityLoading}
              onClick={() =>
                setCapacityRows((current) => [
                  ...current,
                  {
                    user_id: "",
                    available_hours: "",
                    max_concurrent_projects: "",
                  },
                ])
              }
            >
              Thêm nhân viên
            </button>
            <button
              className="apple-button"
              type="submit"
              disabled={capacityLoading || !capacityRows.length}
            >
              {capacityLoading ? "Đang lưu" : "Lưu công suất"}
            </button>
          </div>
        </form>
      </Panel>
      <Panel title="Bảng đơn giá nhân công">
        <div className="min-w-0 space-y-4 p-4">
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
          <form className="min-w-0 space-y-4" onSubmit={runPreview}>
            <FilePicker
              accept=".csv,.xlsx"
              ariaLabel="Chọn bảng CSV hoặc XLSX"
              className="w-full min-w-0 max-w-full"
              disabled={loading}
              fileName={file?.name || ""}
              label="Chọn bảng CSV hoặc XLSX"
              stacked
              onChange={(event) => void selectFile(event.target.files?.[0] || null)}
            />
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
            <button
              className="apple-button"
              type={headers.length ? "submit" : "button"}
              onClick={headers.length ? undefined : () => void selectFile(file)}
              disabled={!file || loading}
            >
              {loading ? "Đang xử lý" : headers.length ? "Xem trước dữ liệu" : "Đọc lại tiêu đề"}
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
                    <td className="p-2">{displayAmount(row.hourly_cost)}</td>
                    <td className="p-2">{row.currency || "—"}</td>
                    <td className="p-2">
                      {displayCalendarDate(row.valid_from)} –{" "}
                      {row.valid_until ? displayCalendarDate(row.valid_until) : "Không thời hạn"}
                    </td>
                    <td className="p-2">
                      {payrollErrorLabels[row.error_code] ||
                        (row.error_code ? "Cần kiểm tra dữ liệu dòng này" : null) ||
                        statusLabels[row.status] ||
                        "Cần kiểm tra dữ liệu dòng này"}
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
                    <td className="p-2">{displayAmount(rate.hourly_cost)}</td>
                    <td className="p-2">{rate.currency}</td>
                    <td className="p-2">
                      {displayCalendarDate(rate.valid_from)} –{" "}
                      {rate.valid_until ? displayCalendarDate(rate.valid_until) : "Không thời hạn"}
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
