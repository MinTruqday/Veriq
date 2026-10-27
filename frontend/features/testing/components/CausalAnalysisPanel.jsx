"use client";
import { useCallback, useEffect, useState } from "react";
import DataTable from "./DataTable";
import PreventiveActionTable from "./PreventiveActionTable";
import { ErrorState, Panel, StatusPill, useActionDialog } from "./WorkspacePrimitives";
import ContentOriginBadge from "../../../shared/components/common/ContentOriginBadge";
import { messageOf } from "../lib/testing";
import { testingApi } from "../services/testing.service";

const ROOT_CAUSE_CATEGORIES = [
  "REQUIREMENT",
  "DESIGN",
  "IMPLEMENTATION",
  "CONFIGURATION",
  "TEST_DATA",
  "TEST_CASE_GAP",
  "ENVIRONMENT",
  "INTEGRATION",
  "DEPLOYMENT",
  "PROCESS",
  "THIRD_PARTY",
  "UNKNOWN",
];
const lines = (value) =>
  String(value || "")
    .split("\n")
    .map((item) => item.trim())
    .filter(Boolean);
const EVENT_TRIGGER_LABELS = {
  DEFECT_RECORDED: "Khi ghi nhận lỗi",
  DEFECT_CHANGED: "Khi cập nhật nội dung lỗi",
};

export default function CausalAnalysisPanel({ project }) {
  const [items, setItems] = useState([]);
  const [defects, setDefects] = useState([]);
  const [members, setMembers] = useState([]);
  const [candidates, setCandidates] = useState([]);
  const [selected, setSelected] = useState(null);
  const [hypothesisResult, setHypothesisResult] = useState(null);
  const [error, setError] = useState("");
  const { ask, dialog } = useActionDialog();
  const can = (permission) => project.current_permissions?.includes(permission);
  const load = useCallback(async () => {
    try {
      const [result, candidateValues, defectValues, memberValues] = await Promise.all([
        testingApi.listCausalAnalyses(project._id),
        testingApi.listCausalAnalysisCandidates(project._id),
        project.current_permissions?.includes("defect.read")
          ? testingApi.listDefects(project._id)
          : Promise.resolve([]),
        project.current_permissions?.includes("project.members.read")
          ? testingApi.listMembers(project._id)
          : Promise.resolve([]),
      ]);
      setItems(result.items || []);
      setCandidates(candidateValues.items || []);
      setDefects(defectValues);
      setMembers(memberValues.filter((item) => item.status === "ACTIVE"));
      if (selected?._id) {
        const [analysis, resultValue] = await Promise.all([
          testingApi.getCausalAnalysis(selected._id),
          testingApi.getLatestCausalHypothesisResult(selected._id),
        ]);
        setSelected(analysis);
        setHypothesisResult(resultValue || null);
      }
      setError("");
    } catch (reason) {
      setError(messageOf(reason));
    }
  }, [project._id, project.current_permissions, selected?._id]);
  useEffect(() => {
    void load();
  }, [load]);
  const memberOptions = members.map((item) => ({
    value: item.user_id,
    label: item.user_label || item.email || item.user_id,
  }));
  const refreshSelected = async () => {
    const [analysis, resultValue] = await Promise.all([
      testingApi.getCausalAnalysis(selected._id),
      testingApi.getLatestCausalHypothesisResult(selected._id),
    ]);
    setSelected(analysis);
    setHypothesisResult(resultValue || null);
  };
  const hypotheses = hypothesisResult?.suggestions || [];
  useEffect(() => {
    if (!selected?._id || hypothesisResult?._id) return undefined;
    let active = true;
    let attempts = 0;
    const timer = window.setInterval(async () => {
      attempts += 1;
      if (attempts > 12) {
        window.clearInterval(timer);
        return;
      }
      try {
        const value = await testingApi.getLatestCausalHypothesisResult(selected._id);
        if (active && value?._id) {
          setHypothesisResult(value);
          window.clearInterval(timer);
        }
      } catch (reason) {
        if (active) setError(messageOf(reason));
      }
    }, 5000);
    return () => {
      active = false;
      window.clearInterval(timer);
    };
  }, [hypothesisResult?._id, selected?._id]);
  const create = async () => {
    const eligible = defects.filter(
      (item) => ["blocker", "critical"].includes(item.severity) || item.status === "REOPENED",
    );
    const answer = await ask({
      title: "Tạo phân tích nguyên nhân",
      confirmLabel: "Tạo",
      fields: [
        {
          name: "defect_ids",
          label: "Mã lỗi cách nhau bởi dấu phẩy",
          required: true,
          initialValue: eligible.map((item) => item._id).join(","),
        },
        { name: "problem_statement", label: "Mô tả vấn đề", required: true, multiline: true },
        { name: "evidence", label: "Bằng chứng", required: true, multiline: true },
        {
          name: "owner_id",
          label: "Phụ trách",
          required: true,
          options: [{ value: "", label: "Chọn thành viên" }, ...memberOptions],
        },
      ],
    });
    if (!answer) return;
    try {
      const value = await testingApi.createCausalAnalysis(project._id, {
        idempotency_key: crypto.randomUUID(),
        defect_ids: answer.defect_ids
          .split(",")
          .map((item) => item.trim())
          .filter(Boolean),
        problem_statement: answer.problem_statement,
        evidence_refs: [answer.evidence],
        owner_id: answer.owner_id,
      });
      setHypothesisResult(null);
      setSelected(value);
      await load();
    } catch (reason) {
      setError(messageOf(reason));
    }
  };
  const editAnalysis = async () => {
    const answer = await ask({
      title: "Cập nhật phân tích",
      confirmLabel: "Lưu",
      fields: [
        {
          name: "problem_statement",
          label: "Mô tả vấn đề",
          required: true,
          multiline: true,
          initialValue: selected.problem_statement,
        },
        {
          name: "evidence_refs",
          label: "Bằng chứng mỗi dòng một mã",
          required: true,
          multiline: true,
          initialValue: (selected.evidence_refs || []).join("\n"),
        },
        {
          name: "owner_id",
          label: "Phụ trách",
          required: true,
          options: [{ value: "", label: "Chọn thành viên" }, ...memberOptions],
          initialValue: selected.owner_id,
        },
      ],
    });
    if (!answer) return;
    try {
      setSelected(
        await testingApi.updateCausalAnalysis(selected._id, {
          expected_revision: selected.revision,
          problem_statement: answer.problem_statement,
          evidence_refs: lines(answer.evidence_refs),
          owner_id: answer.owner_id,
        }),
      );
      setError("");
    } catch (reason) {
      setError(messageOf(reason));
    }
  };
  const linkDefects = async () => {
    const answer = await ask({
      title: "Liên kết lỗi",
      confirmLabel: "Liên kết",
      fields: [
        {
          name: "defect_ids",
          label: "Mã lỗi cách nhau bởi dấu phẩy",
          required: true,
          initialValue: selected.defect_ids?.join(",") || "",
        },
      ],
    });
    if (!answer) return;
    try {
      setSelected(
        await testingApi.linkCausalAnalysisDefects(selected._id, {
          expected_revision: selected.revision,
          defect_ids: answer.defect_ids
            .split(",")
            .map((item) => item.trim())
            .filter(Boolean),
        }),
      );
    } catch (reason) {
      setError(messageOf(reason));
    }
  };
  const addFiveWhy = async () => {
    const answer = await ask({
      title: "Thêm câu trả lời năm câu hỏi tại sao",
      confirmLabel: "Thêm",
      fields: [
        {
          name: "why",
          label: `Lý do thứ ${(selected.five_whys?.length || 0) + 1}`,
          required: true,
          multiline: true,
        },
      ],
    });
    if (!answer) return;
    try {
      setSelected(
        await testingApi.addCausalFiveWhy(selected._id, {
          expected_revision: selected.revision,
          why: answer.why,
        }),
      );
    } catch (reason) {
      setError(messageOf(reason));
    }
  };
  const recordRootCause = async () => {
    const rootCause = selected.root_causes?.[0] || {};
    const answer = await ask({
      title: "Ghi nhận nguyên nhân gốc",
      confirmLabel: "Ghi nhận",
      fields: [
        {
          name: "category",
          label: "Nhóm nguyên nhân",
          options: ROOT_CAUSE_CATEGORIES.map((value) => ({ value, label: value })),
          initialValue: rootCause.category || "UNKNOWN",
        },
        {
          name: "detail",
          label: "Nguyên nhân",
          required: true,
          multiline: true,
          initialValue: rootCause.detail || "",
        },
        {
          name: "contributing_factors",
          label: "Yếu tố đóng góp mỗi dòng một mục",
          multiline: true,
          initialValue: (selected.contributing_factors || []).join("\n"),
        },
        {
          name: "evidence_refs",
          label: "Bằng chứng mỗi dòng một mã",
          required: true,
          multiline: true,
          initialValue: (rootCause.evidence_refs || selected.evidence_refs || []).join("\n"),
        },
      ],
    });
    if (!answer) return;
    try {
      setSelected(
        await testingApi.recordCausalRootCause(selected._id, {
          expected_revision: selected.revision,
          category: answer.category,
          detail: answer.detail,
          contributing_factors: lines(answer.contributing_factors),
          evidence_refs: lines(answer.evidence_refs),
        }),
      );
    } catch (reason) {
      setError(messageOf(reason));
    }
  };
  const addAction = async (actionType) => {
    const answer = await ask({
      title: actionType === "CORRECTIVE" ? "Thêm hành động khắc phục" : "Thêm hành động phòng ngừa",
      confirmLabel: "Thêm",
      fields: [
        { name: "title", label: "Tên hành động", required: true },
        { name: "description", label: "Mô tả", required: true, multiline: true },
        { name: "due_at", label: "Hạn", required: true, type: "datetime-local" },
        { name: "evidence_refs", label: "Bằng chứng mỗi dòng một mã", multiline: true },
      ],
    });
    if (!answer) return;
    try {
      const payload = {
        title: answer.title,
        description: answer.description,
        due_at: new Date(answer.due_at).toISOString(),
        evidence_refs: lines(answer.evidence_refs),
      };
      await (actionType === "CORRECTIVE"
        ? testingApi.createCorrectiveAction(selected._id, payload)
        : testingApi.createPreventiveAction(selected._id, payload));
      await refreshSelected();
    } catch (reason) {
      setError(messageOf(reason));
    }
  };
  const submitReview = async () => {
    const answer = await ask({
      title: "Gửi phân tích để rà soát",
      confirmLabel: "Gửi",
      fields: [{ name: "note", label: "Ghi chú", required: true, multiline: true }],
    });
    if (!answer) return;
    try {
      setSelected(
        await testingApi.submitCausalAnalysis(selected._id, {
          expected_revision: selected.revision,
          note: answer.note,
        }),
      );
    } catch (reason) {
      setError(messageOf(reason));
    }
  };
  const decideReview = async () => {
    const answer = await ask({
      title: "Phê duyệt phân tích nguyên nhân",
      confirmLabel: "Ghi nhận",
      fields: [
        {
          name: "decision",
          label: "Quyết định",
          options: [
            { value: "APPROVE", label: "Phê duyệt" },
            { value: "REQUEST_CHANGES", label: "Yêu cầu chỉnh sửa" },
          ],
        },
        { name: "note", label: "Ghi chú", required: true, multiline: true },
      ],
    });
    if (!answer) return;
    try {
      setSelected(
        await testingApi.approveCausalAnalysis(selected._id, {
          expected_revision: selected.revision,
          ...answer,
        }),
      );
    } catch (reason) {
      setError(messageOf(reason));
    }
  };
  const reviewEffectiveness = async () => {
    const answer = await ask({
      title: "Đánh giá hiệu lực hành động khắc phục và phòng ngừa",
      confirmLabel: "Ghi nhận",
      fields: [
        {
          name: "decision",
          label: "Kết quả",
          options: [
            { value: "EFFECTIVE", label: "Có hiệu lực" },
            { value: "INEFFECTIVE", label: "Chưa có hiệu lực" },
          ],
        },
        { name: "result", label: "Kết quả kiểm chứng", required: true, multiline: true },
        {
          name: "evidence_refs",
          label: "Bằng chứng mỗi dòng một mã",
          required: true,
          multiline: true,
        },
        {
          name: "reviewed_at",
          label: "Thời điểm đánh giá",
          required: true,
          type: "datetime-local",
        },
      ],
    });
    if (!answer) return;
    try {
      setSelected(
        await testingApi.reviewCausalEffectiveness(selected._id, {
          expected_revision: selected.revision,
          decision: answer.decision,
          result: answer.result,
          evidence_refs: lines(answer.evidence_refs),
          reviewed_at: new Date(answer.reviewed_at).toISOString(),
        }),
      );
    } catch (reason) {
      setError(messageOf(reason));
    }
  };
  const closeAnalysis = async () => {
    const answer = await ask({
      title: "Đóng phân tích nguyên nhân",
      confirmLabel: "Đóng",
      fields: [{ name: "note", label: "Kết luận", required: true, multiline: true }],
    });
    if (!answer) return;
    try {
      setSelected(
        await testingApi.closeCausalAnalysis(selected._id, {
          expected_revision: selected.revision,
          note: answer.note,
        }),
      );
    } catch (reason) {
      setError(messageOf(reason));
    }
  };
  return (
    <Panel
      title="Phân tích nguyên nhân và hành động khắc phục"
      actions={
        can("causalanalysis.create") && can("defect.read") && can("project.members.read") ? (
          <button className="apple-button" type="button" onClick={create}>
            Tạo phân tích
          </button>
        ) : null
      }
    >
      {dialog}
      <p className="px-5 pt-4 text-sm text-ink-muted">
        Khi lỗi được ghi nhận, luồng AI tự động có thể tạo giả thuyết dựa trên bằng chứng. Màn hình
        này chỉ đọc kết quả; giả thuyết không tự trở thành nguyên nhân gốc đã xác nhận.
      </p>
      {error && (
        <div className="p-4">
          <ErrorState message={error} />
        </div>
      )}
      {candidates.length > 0 && (
        <DataTable
          items={candidates}
          columns={[
            {
              key: "problem_statement",
              label: "Vấn đề cần phân tích",
              render: (item) => (
                <div className="grid justify-items-start gap-2">
                  <ContentOriginBadge origin="ai_suggested" />
                  <span>{item.problem_statement}</span>
                </div>
              ),
            },
            { key: "defect_ids", label: "Lỗi", render: (item) => item.defect_ids.join(", ") },
            { key: "reason_codes", label: "Lý do", render: (item) => item.reason_codes.join(", ") },
          ]}
        />
      )}
      {items.length > 0 && (
        <DataTable
          items={items}
          columns={[
            { key: "problem_statement", label: "Vấn đề" },
            { key: "defect_ids", label: "Lỗi", render: (item) => item.defect_ids?.length || 0 },
            {
              key: "status",
              label: "Trạng thái",
              render: (item) => <StatusPill value={item.status} />,
            },
            {
              key: "action",
              label: "Thao tác",
              render: (item) => (
                <button
                  className="secondary-button"
                  type="button"
                  onClick={async () => {
                    try {
                      setSelected(await testingApi.getCausalAnalysis(item._id));
                      setHypothesisResult(
                        await testingApi.getLatestCausalHypothesisResult(item._id),
                      );
                    } catch (reason) {
                      setError(messageOf(reason));
                    }
                  }}
                >
                  Mở
                </button>
              ),
            },
          ]}
        />
      )}
      {candidates.length === 0 && items.length === 0 && (
        <p className="px-5 py-8 text-center text-sm text-ink-muted">
          Chưa có phân tích nguyên nhân
        </p>
      )}
      {selected && (
        <div className="space-y-4 border-t border-border p-5">
          <div className="flex flex-wrap justify-between gap-3">
            <div>
              <p className="font-semibold">{selected.problem_statement}</p>
              <p className="text-sm text-ink-muted">
                {selected.analysis_key} · <StatusPill value={selected.status} />
              </p>
            </div>
            <div className="flex flex-wrap gap-2">
              {selected.status === "DRAFT" && can("causalanalysis.update") && (
                <>
                  <button className="secondary-button" type="button" onClick={editAnalysis}>
                    Cập nhật
                  </button>
                  {can("defect.read") && (
                    <button className="secondary-button" type="button" onClick={linkDefects}>
                      Liên kết lỗi
                    </button>
                  )}
                  {(selected.five_whys?.length || 0) < 5 && (
                    <button className="secondary-button" type="button" onClick={addFiveWhy}>
                      Thêm năm câu hỏi tại sao
                    </button>
                  )}
                  <button className="secondary-button" type="button" onClick={recordRootCause}>
                    Ghi nhận nguyên nhân
                  </button>
                  <button className="apple-button" type="button" onClick={submitReview}>
                    Gửi rà soát
                  </button>
                </>
              )}
              {selected.status === "IN_REVIEW" && can("causalanalysis.approve") && (
                <button className="apple-button" type="button" onClick={decideReview}>
                  Ra quyết định
                </button>
              )}
              {["APPROVED", "ACTION_IN_PROGRESS"].includes(selected.status) &&
                can("preventionaction.manage") && (
                  <>
                    <button
                      className="secondary-button"
                      type="button"
                      onClick={() => addAction("CORRECTIVE")}
                    >
                      Thêm hành động khắc phục
                    </button>
                    <button
                      className="secondary-button"
                      type="button"
                      onClick={() => addAction("PREVENTIVE")}
                    >
                      Thêm hành động phòng ngừa
                    </button>
                  </>
                )}
              {selected.status === "ACTION_IN_PROGRESS" && can("causalanalysis.update") && (
                <button className="apple-button" type="button" onClick={reviewEffectiveness}>
                  Đánh giá hiệu lực
                </button>
              )}
              {selected.status === "EFFECTIVENESS_REVIEW" && can("causalanalysis.approve") && (
                <button className="apple-button" type="button" onClick={closeAnalysis}>
                  Đóng phân tích
                </button>
              )}
            </div>
          </div>
          {selected.source_event_id && (
            <section className="grid gap-1 rounded-control border border-border bg-surface-quiet p-3 text-sm">
              <p className="font-medium text-ink">Nguồn tự động hóa</p>
              <p className="text-ink-muted">
                {EVENT_TRIGGER_LABELS[selected.source_event_trigger] || "Sự kiện dự án"} · phiên bản
                lỗi {selected.source_event_revision}
              </p>
              <p className="break-all text-xs text-ink-muted">
                Mã sự kiện: {selected.source_event_id}
              </p>
              {selected.source_automation_run_id && (
                <p className="break-all text-xs text-ink-muted">
                  Mã lượt AI: {selected.source_automation_run_id}
                </p>
              )}
            </section>
          )}
          <DataTable
            items={(selected.five_whys || []).map((why, index) => ({ sequence: index + 1, why }))}
            empty="Chưa ghi nhận năm câu hỏi tại sao"
            columns={[
              { key: "sequence", label: "Lần" },
              { key: "why", label: "Lý do" },
            ]}
          />
          <DataTable
            items={selected.root_causes || []}
            empty="Chưa ghi nhận nguyên nhân"
            columns={[
              { key: "category", label: "Nhóm" },
              { key: "detail", label: "Nguyên nhân" },
            ]}
          />
          {hypotheses.length > 0 && (
            <DataTable
              items={hypotheses}
              empty="Chưa có giả thuyết"
              columns={[
                { key: "root_cause_category", label: "Nhóm" },
                {
                  key: "hypothesis",
                  label: "Giả thuyết",
                  render: (item) => (
                    <div className="grid justify-items-start gap-2">
                      <ContentOriginBadge origin="ai_suggested" />
                      <span>{item.hypothesis}</span>
                    </div>
                  ),
                },
                { key: "confidence", label: "Tin cậy" },
              ]}
            />
          )}
          {selected.status === "DRAFT" && !hypothesisResult && (
            <p className="text-sm text-ink-muted" role="status">
              Chưa có kết quả giả thuyết tự động cho phân tích này. Kết quả sẽ xuất hiện nếu một
              lượt AI theo sự kiện tạo được.
            </p>
          )}
          <PreventiveActionTable
            items={selected.actions}
            canManage={can("preventionaction.manage")}
            onAssign={async (item) => {
              const answer = await ask({
                title: "Phân công hành động",
                confirmLabel: "Phân công",
                fields: [
                  {
                    name: "owner_id",
                    label: "Phụ trách",
                    required: true,
                    options: [{ value: "", label: "Chọn thành viên" }, ...memberOptions],
                    initialValue: item.owner_id || "",
                  },
                ],
              });
              if (answer) {
                try {
                  await testingApi.assignPreventionAction(item._id, {
                    expected_revision: item.revision,
                    owner_id: answer.owner_id,
                  });
                  await refreshSelected();
                } catch (reason) {
                  setError(messageOf(reason));
                }
              }
            }}
            onAdvance={async (item, status) => {
              const answer = await ask({
                title: `Chuyển hành động sang ${status}`,
                confirmLabel: "Chuyển",
                fields: [
                  {
                    name: "result",
                    label: "Kết quả",
                    required: !["IN_PROGRESS"].includes(status),
                    multiline: true,
                  },
                ],
              });
              if (answer) {
                try {
                  await testingApi.updatePreventionAction(item._id, {
                    expected_revision: item.revision,
                    status,
                    result: answer.result || "Đang thực hiện",
                  });
                  await refreshSelected();
                } catch (reason) {
                  setError(messageOf(reason));
                }
              }
            }}
          />
        </div>
      )}
    </Panel>
  );
}
