"use client";

import { useCallback, useEffect, useState } from "react";
import DataTable from "./DataTable";
import { Panel } from "./WorkspacePrimitives";
import { testingApi } from "../services/testing.service";
import { messageOf } from "../lib/testing";

export default function JUnitResultPanel({ project, runs, tests, can, onError }) {
  const [imports, setImports] = useState([]);
  const [runId, setRunId] = useState("");
  const [file, setFile] = useState(null);
  const [mappings, setMappings] = useState({});
  const load = useCallback(async () => {
    try {
      setImports(await testingApi.listJUnitResultImports(project._id));
    } catch (reason) {
      onError(messageOf(reason));
    }
  }, [onError, project._id]);
  useEffect(() => {
    void load();
  }, [load]);
  return (
    <Panel title="Nhập kết quả JUnit XML">
      {can("automation.create") && (
        <form
          className="mb-4 flex flex-wrap items-end gap-3"
          onSubmit={async (event) => {
            event.preventDefault();
            if (!file || !runId) return;
            try {
              await testingApi.importJUnitResult(project._id, runId, file);
              setFile(null);
              await load();
            } catch (reason) {
              onError(messageOf(reason));
            }
          }}
        >
          <label className="field-label">
            Test Run
            <select
              className="apple-input mt-2"
              value={runId}
              onChange={(event) => setRunId(event.target.value)}
              required
            >
              <option value="">Chọn Test Run</option>
              {runs.map((run) => (
                <option key={run._id} value={run._id}>
                  {run.name}
                </option>
              ))}
            </select>
          </label>
          <label className="field-label">
            Tệp JUnit XML
            <input
              className="apple-input mt-2"
              type="file"
              accept=".xml,text/xml,application/xml"
              onChange={(event) => setFile(event.target.files?.[0] || null)}
              required
            />
          </label>
          <button className="primary-button" type="submit">
            Nhập kết quả
          </button>
        </form>
      )}
      <p className="mb-3 text-sm text-ink-muted">
        Mỗi testcase cần property veriq_test_case_version_id để được liên kết an toàn với phiên bản
        Test Case
      </p>
      <DataTable
        items={imports}
        empty="Chưa có kết quả JUnit"
        columns={[
          { key: "test_run_id", label: "Test Run" },
          { key: "status", label: "Trạng thái" },
          {
            key: "mapped_test_case_version_ids",
            label: "Đã liên kết",
            render: (item) => item.mapped_test_case_version_ids?.length || 0,
          },
          { key: "unresolved", label: "Cần xử lý", render: (item) => item.unresolved?.length || 0 },
        ]}
      />
      {imports
        .filter((item) => item.unresolved?.length)
        .map((item) => {
          const run = runs.find((value) => value._id === item.test_run_id);
          const versions = new Set(run?.test_case_version_ids || []);
          const availableTests = tests.filter((test) => versions.has(test.current_version_id));
          return (
            <div className="mt-4 rounded-control border border-border p-4" key={item._id}>
              <p className="mb-3 text-sm font-medium">Các kết quả JUnit cần liên kết</p>
              <div className="space-y-3">
                {item.unresolved.map((row, index) => {
                  const key = `${item._id}:${index}`;
                  return (
                    <div className="grid gap-2 md:grid-cols-[1fr_1fr_auto]" key={key}>
                      <p className="self-center text-sm">
                        {row.classname ? `${row.classname} ` : ""}
                        {row.name || "Không có tên testcase"}
                      </p>
                      <select
                        aria-label={`Liên kết kết quả JUnit ${row.name || index + 1}`}
                        className="apple-input"
                        value={mappings[key] || ""}
                        onChange={(event) =>
                          setMappings((current) => ({ ...current, [key]: event.target.value }))
                        }
                      >
                        <option value="">Chọn phiên bản Test Case</option>
                        {availableTests.map((test) => (
                          <option key={test.current_version_id} value={test.current_version_id}>
                            {test.test_case_key} {test.current_version?.title || test.title}
                          </option>
                        ))}
                      </select>
                      {can("automation.create") && (
                        <button
                          className="secondary-button"
                          type="button"
                          disabled={!mappings[key]}
                          onClick={async () => {
                            try {
                              await testingApi.resolveJUnitResultMapping(item._id, {
                                expected_revision: item.revision,
                                unresolved_index: index,
                                test_case_version_id: mappings[key],
                              });
                              await load();
                            } catch (reason) {
                              onError(messageOf(reason));
                            }
                          }}
                        >
                          Liên kết
                        </button>
                      )}
                    </div>
                  );
                })}
              </div>
            </div>
          );
        })}
    </Panel>
  );
}
