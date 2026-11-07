import { useRef, useState } from "react";
import { Archive, Copy, Send, Check, RotateCcw } from "lucide-react";
import SearchField from "@/shared/components/ui/SearchField";
import { Panel, StatusPill } from "../../../components/WorkspacePrimitives";
import { messageOf, valueLabel } from "../../../lib/testing";
import { testingApi } from "../../../services/testing.service";
import ScenarioCreateModal from "./ScenarioCreateModal";
import {
  TEST_LEVELS,
  TEST_SCENARIO_CATEGORIES,
  scenarioPayload,
  scenarioFormFromRecord,
} from "./testDesign.model";

export default function ScenariosPanel({
  can,
  scenarios,
  filters,
  setFilters,
  isCreating,
  setCreating,
  saving,
  form,
  setForm,
  testConditions,
  onSubmit,
  ask,
  reload,
  onError,
  requirements = [],
  members = [],
  canReview = false,
  canEdit = () => can("testscenario.update"),
  canAssignOwner = true,
  canReadTestConditions = false,
}) {
  const [selected, setSelected] = useState(null);
  const [editForm, setEditForm] = useState(null);
  const [editError, setEditError] = useState("");
  const [savingEdit, setSavingEdit] = useState(false);
  const editInFlight = useRef(false);
  const transition = async (item, action, label) => {
    await ask({
      title: label,
      description: item.title,
      confirmLabel: label,
      fields: [{ name: "note", label: "Nhận xét", multiline: true }],
      onConfirm: async (answer) => {
        await testingApi.transitionScenario(item._id, action, {
          expected_revision: item.revision,
          review_note: answer.note || "",
        });
        await reload();
      },
    });
  };
  const openScenario = async (item) => {
    try {
      const record = await testingApi.getScenario(item._id);
      setEditError("");
      setEditForm(scenarioFormFromRecord(record));
      setSelected(record);
    } catch (reason) {
      onError(messageOf(reason));
    }
  };
  const scenarioActions = (item) => (
    <span className="flex shrink-0 items-center gap-1.5">
      {[
        ...(item.status === "draft" && canEdit(item) ? [["gui-ra-soat", "Gửi rà soát", Send]] : []),
        ...(item.status === "in_review" && canReview && can("testscenario.update")
          ? [
              ["phe-duyet", "Duyệt kịch bản", Check],
              ["yeu-cau-chinh-sua", "Yêu cầu chỉnh sửa", RotateCcw],
            ]
          : []),
      ].map(([action, label, Icon]) => (
        <button
          key={action}
          type="button"
          className="icon-button h-9 w-9"
          title={label}
          aria-label={`${label} ${item.title}`}
          onClick={() => void transition(item, action, label)}
        >
          <Icon aria-hidden="true" size={16} />
        </button>
      ))}
      {can("testscenario.clone") && (
        <button
          className="icon-button h-9 w-9"
          type="button"
          aria-label={`Nhân bản kịch bản ${item.title}`}
          title="Nhân bản kịch bản"
          onClick={async () => {
            try {
              await testingApi.cloneScenario(item._id);
              await reload();
            } catch (reason) {
              onError(messageOf(reason));
            }
          }}
        >
          <Copy aria-hidden="true" size={16} />
        </button>
      )}
      {item.status !== "archived" && can("testscenario.archive") && (
        <button
          className="icon-button h-9 w-9"
          type="button"
          aria-label={`Lưu trữ kịch bản ${item.title}`}
          title="Lưu trữ kịch bản"
          onClick={() =>
            void ask({
              title: "Lưu trữ kịch bản",
              description: item.title,
              confirmLabel: "Lưu trữ",
              danger: true,
              fields: [
                {
                  name: "reason",
                  label: "Lý do",
                  required: true,
                  multiline: true,
                  autoFocus: true,
                },
              ],
              onConfirm: async (answer) => {
                try {
                  await testingApi.archiveScenario(item._id, {
                    expected_revision: item.revision,
                    reason: answer.reason,
                  });
                  await reload();
                } catch (reason) {
                  throw new Error(messageOf(reason));
                }
              },
            })
          }
        >
          <Archive aria-hidden="true" size={16} />
        </button>
      )}
    </span>
  );
  return (
    <Panel title="Kịch bản">
      {can("testscenario.create") && (
        <ScenarioCreateModal
          isOpen={isCreating}
          onClose={() => {
            if (!saving) setCreating(false);
          }}
          saving={saving}
          form={form}
          setForm={setForm}
          testConditions={testConditions}
          requirements={requirements}
          members={members}
          canReadTestConditions={canReadTestConditions}
          onSubmit={onSubmit}
        />
      )}
      {selected && editForm && (
        <ScenarioCreateModal
          isOpen
          title={selected.title}
          form={editForm}
          setForm={setEditForm}
          onClose={() => {
            if (!savingEdit) setSelected(null);
          }}
          saving={savingEdit}
          readOnly={selected.status !== "draft" || !canEdit(selected)}
          canAssignOwner={canAssignOwner}
          testConditions={testConditions}
          requirements={requirements}
          members={members}
          canReadTestConditions={canReadTestConditions}
          onSubmit={async (event) => {
            event.preventDefault();
            if (editInFlight.current) return;
            editInFlight.current = true;
            setSavingEdit(true);
            setEditError("");
            try {
              await testingApi.updateScenario(selected._id, {
                ...scenarioPayload(editForm),
                expected_revision: selected.revision,
              });
              setSelected(null);
              await reload();
            } catch (reason) {
              setEditError(messageOf(reason));
            } finally {
              editInFlight.current = false;
              setSavingEdit(false);
            }
          }}
        >
          {editError && (
            <p role="alert" className="text-sm text-danger">
              {editError}
            </p>
          )}
          <div className="border-t border-border pt-3 text-sm">
            <p className="font-medium">Ca kiểm thử liên quan</p>
            {selected.test_cases?.length ? (
              <ul className="mt-2 space-y-1">
                {selected.test_cases.map((item) => (
                  <li key={item._id}>
                    {item.test_case_key} {item.title || item.current_version?.title}
                  </li>
                ))}
              </ul>
            ) : (
              <p className="mt-2 text-ink-muted">Chưa có ca kiểm thử liên kết.</p>
            )}
          </div>
        </ScenarioCreateModal>
      )}
      <div className="flex flex-wrap items-center justify-between gap-3 border-b border-border px-4 py-3">
        <p className="text-sm text-ink-muted">{scenarios.length} kịch bản trong danh sách</p>
        <div className="flex min-w-0 flex-1 flex-wrap items-center justify-end gap-2">
          <SearchField
            ariaLabel="Tìm kịch bản"
            className="min-w-[16rem] flex-1 xl:max-w-lg"
            onChange={(event) => setFilters({ ...filters, q: event.target.value })}
            placeholder="Tìm theo mã hoặc tên kịch bản"
            value={filters.q}
          />
          {can("testscenario.create") && (
            <button
              className="primary-button shrink-0"
              type="button"
              onClick={() => setCreating(true)}
            >
              Tạo kịch bản
            </button>
          )}
        </div>
      </div>
      <details className="border-b border-border px-4 py-3">
        <summary className="cursor-pointer text-sm font-medium">
          Lọc nhóm, rủi ro và trạng thái
        </summary>
        <div className="mt-3 grid gap-3 sm:grid-cols-2 xl:grid-cols-4">
          <select
            aria-label="Lọc nhóm kịch bản"
            className="apple-input"
            value={filters.category}
            onChange={(event) => setFilters({ ...filters, category: event.target.value })}
          >
            <option value="">Mọi nhóm</option>
            {TEST_SCENARIO_CATEGORIES.map((value) => (
              <option value={value} key={value}>
                {valueLabel(value)}
              </option>
            ))}
          </select>
          <select
            aria-label="Lọc rủi ro kịch bản"
            className="apple-input"
            value={filters.risk}
            onChange={(event) => setFilters({ ...filters, risk: event.target.value })}
          >
            <option value="">Mọi rủi ro</option>
            {TEST_LEVELS.map((value) => (
              <option value={value} key={value}>
                {valueLabel(value)}
              </option>
            ))}
          </select>
          <select
            aria-label="Lọc trạng thái kịch bản"
            className="apple-input"
            value={filters.status}
            onChange={(event) => setFilters({ ...filters, status: event.target.value })}
          >
            <option value="">Mọi trạng thái</option>
            {["draft", "in_review", "approved", "archived"].map((value) => (
              <option value={value} key={value}>
                {valueLabel(value)}
              </option>
            ))}
          </select>
          <select
            aria-label="Sắp xếp kịch bản"
            className="apple-input"
            value={filters.sort}
            onChange={(event) => setFilters({ ...filters, sort: event.target.value })}
          >
            <option value="-updated_at">Mới cập nhật</option>
            <option value="updated_at">Cập nhật cũ nhất</option>
            <option value="scenario_key">Mã tăng dần</option>
            <option value="title">Tên tăng dần</option>
          </select>
        </div>
      </details>
      {scenarios.length ? (
        <ul className="divide-y divide-border" aria-label="Danh sách kịch bản kiểm thử">
          {scenarios.map((item) => (
            <li className="flex min-w-0 items-start justify-between gap-4 px-4 py-4" key={item._id}>
              <button
                className="min-w-0 flex-1 text-left"
                type="button"
                aria-label={`Mở kịch bản ${item.scenario_key || item.title}`}
                onClick={() => void openScenario(item)}
              >
                <span className="flex flex-wrap items-center gap-x-3 gap-y-1">
                  <span className="font-mono text-xs text-ink-muted">{item.scenario_key}</span>
                  <StatusPill value={item.status} />
                </span>
                <span className="mt-2 block break-words font-medium text-ink [overflow-wrap:anywhere]">
                  {item.title}
                </span>
                <span className="mt-1 flex flex-wrap gap-x-4 gap-y-1 text-sm text-ink-muted">
                  {item.category && <span>{valueLabel(item.category)}</span>}
                  {item.priority && <span>Ưu tiên {valueLabel(item.priority)}</span>}
                  {item.risk && <span>Rủi ro {valueLabel(item.risk)}</span>}
                  {item.origin && <span>{valueLabel(item.origin)}</span>}
                </span>
              </button>
              {scenarioActions(item)}
            </li>
          ))}
        </ul>
      ) : (
        <div className="p-5 text-sm text-ink-muted">
          {filters.q || filters.category || filters.risk || filters.status
            ? "Không tìm thấy kịch bản phù hợp."
            : "Chưa có kịch bản kiểm thử."}
        </div>
      )}
    </Panel>
  );
}
