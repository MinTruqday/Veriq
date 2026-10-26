import DataTable from "../../../components/DataTable";
import { Panel } from "../../../components/WorkspacePrimitives";
import { messageOf, valueLabel } from "../../../lib/testing";
import { testingApi } from "../../../services/testing.service";
import ScenarioCreateModal from "./ScenarioCreateModal";
import { TEST_LEVELS, TEST_SCENARIO_CATEGORIES } from "./testDesign.model";

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
}) {
  return (
    <Panel
      title="Kịch bản"
      actions={
        can("testscenario.create") ? (
          <button className="secondary-button" type="button" onClick={() => setCreating(true)}>
            Tạo kịch bản
          </button>
        ) : null
      }
    >
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
          onSubmit={onSubmit}
        />
      )}
      <details className="border-b border-border p-4">
        <summary className="cursor-pointer text-sm font-medium">Tìm kiếm bộ lọc và sắp xếp</summary>
        <div className="mt-3 grid gap-3 sm:grid-cols-2 lg:grid-cols-5">
          <input
            aria-label="Tìm kịch bản"
            className="apple-input"
            placeholder="Tìm mã hoặc tên"
            value={filters.q}
            onChange={(event) => setFilters({ ...filters, q: event.target.value })}
          />
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
            <option value="updated_at">Cũ cập nhật</option>
            <option value="scenario_key">Mã tăng dần</option>
            <option value="title">Tên tăng dần</option>
          </select>
        </div>
      </details>
      <DataTable
        onSelect={async (item) => {
          if (item.status !== "draft" || !can("testscenario.update")) return;
          await ask({
            title: "Đổi tên kịch bản kiểm thử",
            description: item.scenario_key,
            confirmLabel: "Lưu tên",
            fields: [
              {
                name: "title",
                label: "Tên kịch bản",
                initialValue: item.title,
                required: true,
                autoFocus: true,
              },
            ],
            onConfirm: async (answer) => {
              if (answer.title === item.title) return;
              try {
                await testingApi.updateScenario(item._id, {
                  expected_revision: item.revision,
                  title: answer.title,
                });
                await reload();
              } catch (reason) {
                throw new Error(messageOf(reason));
              }
            },
          });
        }}
        items={scenarios}
        empty="Chưa có kịch bản"
        columns={[
          { key: "scenario_key", label: "Mã" },
          { key: "title", label: "Tên" },
          { key: "category", label: "Nhóm" },
          { key: "origin", label: "Nguồn" },
          {
            key: "actions",
            label: "Thao tác",
            hideWhenEmpty: true,
            render: (item) => (
              <span className="flex flex-wrap gap-2">
                {can("testscenario.clone") && (
                  <button
                    className="secondary-button"
                    type="button"
                    onClick={async (event) => {
                      event.stopPropagation();
                      try {
                        await testingApi.cloneScenario(item._id);
                        await reload();
                      } catch (reason) {
                        onError(messageOf(reason));
                      }
                    }}
                  >
                    Nhân bản
                  </button>
                )}
                {item.status !== "archived" && can("testscenario.archive") && (
                  <button
                    className="secondary-button"
                    type="button"
                    onClick={async (event) => {
                      event.stopPropagation();
                      await ask({
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
                      });
                    }}
                  >
                    Lưu trữ
                  </button>
                )}
              </span>
            ),
          },
        ]}
      />
    </Panel>
  );
}
