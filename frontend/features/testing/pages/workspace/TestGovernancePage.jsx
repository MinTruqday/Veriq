"use client";
import { useCallback, useEffect, useRef, useState } from "react";
import DataTable from "../../components/DataTable";
import StrategyVersionHistory from "../../components/StrategyVersionHistory";
import TestStrategyEditor from "../../components/TestStrategyEditor";
import FormalReviewPanel from "../../components/FormalReviewPanel";
import {
  ErrorState,
  InitialLoadState,
  Panel,
  ProjectCrumb,
  StatusPill,
  WorkspacePage,
  useActionDialog,
} from "../../components/WorkspacePrimitives";
import { Modal, ModalHeader, ModalTitle } from "@/shared/components/ui/Modal";
import { messageOf, valueLabel } from "../../lib/testing";
import { testingApi } from "../../services/testing.service";

const strategyFindingLabels = {
  STRATEGY_OBJECTIVE_MISSING: "Bổ sung mục tiêu chiến lược.",
  STRATEGY_TEST_LEVEL_MISSING: "Chọn cấp kiểm thử.",
  STRATEGY_TEST_TYPE_MISSING: "Chọn loại kiểm thử.",
  STRATEGY_RISK_MODEL_MISSING: "Bổ sung mô hình đánh giá rủi ro.",
  STRATEGY_ENTRY_CRITERIA_MISSING: "Bổ sung điều kiện bắt đầu.",
  STRATEGY_EXIT_CRITERIA_MISSING: "Bổ sung điều kiện kết thúc.",
  STRATEGY_SUSPENSION_CRITERIA_MISSING: "Bổ sung điều kiện tạm dừng.",
  STRATEGY_RESUMPTION_CRITERIA_MISSING: "Bổ sung điều kiện tiếp tục.",
  STRATEGY_REPORTING_CADENCE_MISSING: "Bổ sung chu kỳ báo cáo.",
  STRATEGY_QUALITY_OBJECTIVE_MISSING: "Bổ sung mục tiêu chất lượng.",
};

export default function TestGovernancePage({ project }) {
  const { ask, dialog } = useActionDialog();
  const [items, setItems] = useState([]);
  const [selected, setSelected] = useState(null);
  const [editing, setEditing] = useState(false);
  const [query, setQuery] = useState("");
  const [status, setStatus] = useState("");
  const [error, setError] = useState("");
  const [validation, setValidation] = useState(null);
  const [comparison, setComparison] = useState(null);
  const [initialLoading, setInitialLoading] = useState(true);
  const [initialLoadFailed, setInitialLoadFailed] = useState(false);
  const initialDataLoaded = useRef(false);
  const loadedProjectId = useRef(project._id);
  const can = (permission) => project.current_permissions?.includes(permission);
  const load = useCallback(async () => {
    if (loadedProjectId.current !== project._id) {
      loadedProjectId.current = project._id;
      initialDataLoaded.current = false;
      setInitialLoading(true);
    }
    try {
      const result = await testingApi.listTestStrategies(project._id, {
        q: query,
        status,
        page_size: 200,
      });
      setItems(result.items || []);
      setSelected(
        (current) =>
          result.items?.find((item) => item._id === current?._id) ||
          current ||
          result.items?.[0] ||
          null,
      );
      initialDataLoaded.current = true;
      setInitialLoadFailed(false);
    } catch (reason) {
      setError(messageOf(reason));
      if (!initialDataLoaded.current) setInitialLoadFailed(true);
    } finally {
      setInitialLoading(false);
    }
  }, [project._id, query, status]);
  useEffect(() => {
    void load();
  }, [load]);
  if (initialLoading || initialLoadFailed)
    return (
      <InitialLoadState
        title="Chiến lược kiểm thử"
        projectId={project._id}
        loading={initialLoading}
        error={error}
        onRetry={() => void load()}
      />
    );
  const transition = async (title, confirmLabel, action, field = "note") => {
    if (!selected) return;
    await ask({
      title,
      confirmLabel,
      fields: [{ name: field, label: "Lý do hoặc ghi chú", required: true, multiline: true }],
      onConfirm: async (answer) => {
        try {
          await action(selected._id, {
            expected_revision: selected.revision,
            [field]: answer[field],
          });
          await load();
        } catch (reason) {
          throw new Error(messageOf(reason));
        }
      },
    });
  };
  const validateSelected = async () => {
    if (!selected) return;
    try {
      setValidation(await testingApi.validateTestStrategy(selected._id));
    } catch (reason) {
      setError(messageOf(reason));
    }
  };
  const compareSelected = async () => {
    if (!selected) return;
    const other = items.find(
      (item) => item.lineage_id === selected.lineage_id && item._id !== selected._id,
    );
    if (!other) {
      setComparison({ changed_fields: [], unavailable: true });
      return;
    }
    try {
      setComparison(await testingApi.compareTestStrategyVersions(selected._id, other._id));
    } catch (reason) {
      setError(messageOf(reason));
    }
  };
  return (
    <WorkspacePage
      title="Chiến lược kiểm thử"
      actions={
        <>
          <ProjectCrumb projectId={project._id} />
          {can("teststrategy.create") && (
            <button
              className="apple-button"
              type="button"
              onClick={() => {
                setSelected(null);
                setEditing(true);
              }}
            >
              Tạo chiến lược
            </button>
          )}
        </>
      }
    >
      {dialog}
      {error && <ErrorState message={error} />}
      <Panel title="Kho chiến lược kiểm thử">
        <form
          className="grid gap-3 p-5 sm:grid-cols-[1fr_220px_auto]"
          onSubmit={(event) => {
            event.preventDefault();
            void load();
          }}
        >
          <input
            className="apple-input"
            aria-label="Tìm chiến lược"
            value={query}
            onChange={(event) => setQuery(event.target.value)}
            placeholder="Tìm theo mã hoặc tên"
          />
          <select
            className="apple-input"
            aria-label="Lọc trạng thái"
            value={status}
            onChange={(event) => setStatus(event.target.value)}
          >
            <option value="">Tất cả trạng thái</option>
            {["DRAFT", "IN_REVIEW", "APPROVED", "SUPERSEDED", "ARCHIVED"].map((value) => (
              <option key={value} value={value}>
                {valueLabel(value)}
              </option>
            ))}
          </select>
          <button className="secondary-button" type="submit">
            Lọc
          </button>
        </form>
        <DataTable
          items={items}
          empty="Chưa có chiến lược kiểm thử"
          columns={[
            { key: "key", label: "Mã" },
            { key: "name", label: "Tên" },
            { key: "version", label: "Phiên bản" },
            { key: "created_by", label: "Người soạn" },
            {
              key: "status",
              label: "Trạng thái",
              render: (item) => <StatusPill value={item.status} />,
            },
            {
              key: "active",
              label: "Hiệu lực",
              render: (item) => (item.active_approved ? "Đang áp dụng" : ""),
            },
            {
              key: "actions",
              label: "Thao tác",
              render: (item) => (
                <button
                  className="secondary-button"
                  type="button"
                  onClick={() => setSelected(item)}
                >
                  Mở
                </button>
              ),
            },
          ]}
        />
      </Panel>
      {selected && (
        <Panel
          title={`${selected.key} phiên bản ${selected.version}`}
          actions={
            <div className="flex flex-wrap gap-2">
              {can("teststrategy.update") && ["DRAFT", "IN_REVIEW"].includes(selected.status) && (
                <button className="secondary-button" type="button" onClick={() => setEditing(true)}>
                  Chỉnh sửa
                </button>
              )}
              {can("teststrategy.review") && (
                <button
                  className="secondary-button"
                  type="button"
                  onClick={() => void validateSelected()}
                >
                  Kiểm tra đầy đủ
                </button>
              )}
              {can("teststrategy.submit_review") && selected.status === "DRAFT" && (
                <button
                  className="secondary-button"
                  type="button"
                  onClick={() =>
                    transition(
                      "Gửi chiến lược để rà soát",
                      "Gửi rà soát",
                      testingApi.submitTestStrategy,
                    )
                  }
                >
                  Gửi rà soát
                </button>
              )}
              {can("teststrategy.review") && selected.status === "IN_REVIEW" && (
                <button
                  className="secondary-button"
                  type="button"
                  onClick={() =>
                    transition(
                      "Ghi nhận rà soát chiến lược",
                      "Ghi nhận",
                      testingApi.reviewTestStrategy,
                    )
                  }
                >
                  Ghi nhận rà soát
                </button>
              )}
              {can("teststrategy.review") && selected.status === "IN_REVIEW" && (
                <button
                  className="secondary-button"
                  type="button"
                  onClick={() =>
                    transition(
                      "Yêu cầu chỉnh sửa chiến lược",
                      "Yêu cầu chỉnh sửa",
                      testingApi.requestTestStrategyChanges,
                    )
                  }
                >
                  Yêu cầu chỉnh sửa
                </button>
              )}
              {can("teststrategy.approve") && selected.status === "IN_REVIEW" && (
                <button
                  className="apple-button"
                  type="button"
                  onClick={() =>
                    transition("Phê duyệt chiến lược", "Phê duyệt", testingApi.approveTestStrategy)
                  }
                >
                  Phê duyệt
                </button>
              )}
              {can("teststrategy.version.create") &&
                ["APPROVED", "SUPERSEDED"].includes(selected.status) && (
                  <button
                    className="secondary-button"
                    type="button"
                    onClick={() =>
                      transition(
                        "Tạo phiên bản chiến lược mới",
                        "Tạo phiên bản",
                        testingApi.versionTestStrategy,
                        "change_reason",
                      )
                    }
                  >
                    Tạo phiên bản mới
                  </button>
                )}
              {can("teststrategy.version.read") && (
                <button
                  className="secondary-button"
                  type="button"
                  onClick={() => void compareSelected()}
                >
                  So sánh phiên bản
                </button>
              )}
              {can("teststrategy.archive") && ["DRAFT", "SUPERSEDED"].includes(selected.status) && (
                <button
                  className="secondary-button"
                  type="button"
                  onClick={() =>
                    transition("Lưu trữ chiến lược", "Lưu trữ", testingApi.archiveTestStrategy)
                  }
                >
                  Lưu trữ
                </button>
              )}
            </div>
          }
        >
          <div className="grid gap-5 p-5 md:grid-cols-2">
            <div>
              <p className="field-label">Mục tiêu</p>
              <p className="mt-2 whitespace-pre-wrap text-sm">{selected.objective}</p>
            </div>
            <div>
              <p className="field-label">Cách tiếp cận</p>
              <p className="mt-2 whitespace-pre-wrap text-sm">{selected.approach}</p>
            </div>
            <div>
              <p className="field-label">Cấp kiểm thử</p>
              <p className="mt-2 text-sm">
                {selected.test_levels?.map(valueLabel).join(" · ") || "Chưa khai báo"}
              </p>
            </div>
            <div>
              <p className="field-label">Loại kiểm thử</p>
              <p className="mt-2 text-sm">
                {selected.test_types?.map(valueLabel).join(" · ") || "Chưa khai báo"}
              </p>
            </div>
            <div>
              <p className="field-label">Công thức rủi ro</p>
              <p className="mt-2 text-sm">{selected.risk_model?.risk_exposure_formula}</p>
            </div>
            <div>
              <p className="field-label">Người rà soát được phân công</p>
              <p className="mt-2 text-sm">
                {selected.reviewer_ids?.join(" · ") || "Chưa phân công"}
              </p>
            </div>
          </div>
          <details className="px-5 pb-5 text-xs text-ink-muted">
            <summary className="cursor-pointer">Thông tin kiểm tra phiên bản</summary>
            <p className="mt-1 break-all">Mã đối chiếu: {selected.snapshot_hash || "Chưa có"}</p>
          </details>
          {validation && (
            <div className="border-t border-border p-5 text-sm">
              {validation.ready_for_review
                ? "Chiến lược đã đủ điều kiện rà soát"
                : validation.findings
                    .map(
                      (item) =>
                        strategyFindingLabels[item.code] ||
                        "Bổ sung thông tin còn thiếu cho chiến lược.",
                    )
                    .join(" ")}
            </div>
          )}
          {comparison && (
            <div className="border-t border-border p-5 text-sm">
              {comparison.unavailable
                ? "Chưa có phiên bản khác để so sánh"
                : comparison.changed_fields.length
                  ? `Trường thay đổi ${comparison.changed_fields.join(" · ")}`
                  : "Hai phiên bản không khác nội dung kiểm soát"}
            </div>
          )}
        </Panel>
      )}
      {selected && (
        <Panel title="Lịch sử phiên bản">
          <StrategyVersionHistory
            items={items}
            lineageId={selected.lineage_id}
            onSelect={setSelected}
          />
        </Panel>
      )}
      {selected && project.current_permissions?.includes("reviewsession.read") && (
        <FormalReviewPanel
          project={project}
          artifactType="TEST_STRATEGY"
          artifactId={selected._id}
          artifactVersionId={selected._id}
          reviewType="TEST_STRATEGY_REVIEW"
        />
      )}
      <Modal
        isOpen={editing}
        onClose={() => setEditing(false)}
        ariaLabel="Biên tập chiến lược kiểm thử"
        className="max-h-[94dvh] max-w-5xl overflow-y-auto"
      >
        <ModalHeader>
          <ModalTitle>{selected ? "Chỉnh sửa chiến lược" : "Tạo chiến lược"}</ModalTitle>
        </ModalHeader>
        <TestStrategyEditor
          strategy={selected}
          onCancel={() => setEditing(false)}
          onSave={async (payload) => {
            try {
              const value = selected
                ? await testingApi.updateTestStrategy(selected._id, payload)
                : await testingApi.createTestStrategy(project._id, payload);
              setSelected(value);
              setEditing(false);
              await load();
            } catch (reason) {
              setError(messageOf(reason));
              throw reason;
            }
          }}
        />
      </Modal>
    </WorkspacePage>
  );
}
