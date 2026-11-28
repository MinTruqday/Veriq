"use client";

import { useCallback, useEffect, useMemo, useState } from "react";
import Link from "next/link";
import { RefreshCw } from "lucide-react";
import DataTable from "../../../components/DataTable";
import {
  ErrorState,
  LoadingState,
  Panel,
  StatusPill,
} from "../../../components/WorkspacePrimitives";
import { testingApi } from "../../../services/testing.service";
import { messageOf, valueLabel } from "../../../lib/testing";

function linkStatusLabel(link) {
  if (link.obsolete) return "Cần kiểm tra lại";
  return (
    {
      CONFIRMED: "Đã xác nhận",
      SUGGESTED: "Chờ rà soát",
      REJECTED: "Đã từ chối",
      REVOKED: "Đã thu hồi",
    }[link.status] || valueLabel(link.status)
  );
}

const relationshipLabels = {
  verifies: "Xác minh",
  covers: "Bao phủ",
  derived_from: "Phát sinh từ",
  relates_to: "Có liên quan",
};

export default function RequirementTracePanel({
  projectId,
  requirement,
  current,
  canReadCoverage,
}) {
  const [matrix, setMatrix] = useState(null);
  const [coverage, setCoverage] = useState(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");
  const load = useCallback(async () => {
    if (!current?._id) return;
    setLoading(true);
    setError("");
    setCoverage(null);
    try {
      const results = await Promise.allSettled([
        testingApi.traceability(projectId, { requirement_version_id: current._id }),
        canReadCoverage ? testingApi.coverage(projectId) : Promise.resolve(null),
      ]);
      if (results[0].status === "rejected") throw results[0].reason;
      setMatrix(results[0].value);
      setCoverage(results[1].status === "fulfilled" ? results[1].value : null);
    } catch (reason) {
      setError(messageOf(reason));
    } finally {
      setLoading(false);
    }
  }, [canReadCoverage, current?._id, projectId]);

  useEffect(() => {
    setMatrix(null);
    void load();
  }, [load]);

  const rows = useMemo(() => {
    if (!matrix || !current) return [];
    const criteria = new Map((current.acceptance_criteria || []).map((item) => [item._id, item]));
    const cases = new Map((matrix.test_cases || []).map((item) => [item._id, item]));
    const versions = new Map((matrix.test_case_versions || []).map((item) => [item._id, item]));
    const links = (matrix.trace_links || []).filter(
      (item) => item.target_type === "test_case_version",
    );
    const bySource = new Map();
    for (const link of links) {
      const group = bySource.get(link.source_id) || [];
      group.push(link);
      bySource.set(link.source_id, group);
    }
    const sourceRows = [
      {
        _id: current._id,
        source_id: current._id,
        label: `${requirement.requirement_key} · Phiên bản ${current.version}`,
        kind: "Yêu cầu",
      },
      ...(current.acceptance_criteria || []).map((item) => ({
        _id: item._id,
        source_id: item._id,
        label: `${item.key || "Tiêu chí chấp nhận"} · ${item.text || item.plain_text || ""}`,
        kind: "Tiêu chí chấp nhận",
      })),
    ];
    return sourceRows.flatMap((source) => {
      const sourceLinks = bySource.get(source.source_id) || [];
      if (!sourceLinks.length) return [{ ...source, link: null }];
      return sourceLinks.map((link) => {
        const testVersion = versions.get(link.target_id);
        const testCase = testVersion ? cases.get(testVersion.test_case_id) : null;
        const criterion = criteria.get(link.source_id);
        return {
          ...source,
          _id: `${source._id}:${link._id}`,
          link,
          testVersion,
          testCase,
          sourceLabel: criterion
            ? `${criterion.key || source.kind} · ${criterion.text || criterion.plain_text || ""}`
            : source.label,
        };
      });
    });
  }, [current, matrix, requirement?.requirement_key]);

  const linkedCount = (matrix?.trace_links || []).filter(
    (item) => item.target_type === "test_case_version",
  ).length;
  const confirmedCount = (matrix?.trace_links || []).filter(
    (item) =>
      item.target_type === "test_case_version" && item.status === "CONFIRMED" && !item.obsolete,
  ).length;
  const reviewCount = (matrix?.trace_links || []).filter(
    (item) => item.target_type === "test_case_version" && item.status === "SUGGESTED",
  ).length;

  return (
    <Panel
      title="Truy vết yêu cầu"
      description={`${requirement?.requirement_key || "Yêu cầu"} · Phiên bản ${current?.version ?? "—"}`}
      actions={
        <button
          aria-label="Tải lại liên kết truy vết"
          className="icon-button h-9 w-9"
          disabled={loading}
          onClick={() => void load()}
          title="Tải lại liên kết truy vết"
          type="button"
        >
          <RefreshCw aria-hidden="true" className="size-4" />
        </button>
      }
    >
      <div className="space-y-4 p-4 sm:p-5">
        {error && <ErrorState message={error} />}
        {loading ? (
          <LoadingState label="Đang tải liên kết truy vết" />
        ) : matrix ? (
          <>
            <dl className="grid gap-3 sm:grid-cols-3">
              <div className="rounded-control border border-border bg-surface-quiet p-3">
                <dt className="text-xs text-ink-muted">Liên kết ca kiểm thử</dt>
                <dd className="mt-1 text-lg font-semibold">{linkedCount}</dd>
              </div>
              <div className="rounded-control border border-border bg-surface-quiet p-3">
                <dt className="text-xs text-ink-muted">Đã xác nhận</dt>
                <dd className="mt-1 text-lg font-semibold">{confirmedCount}</dd>
              </div>
              <div className="rounded-control border border-border bg-surface-quiet p-3">
                <dt className="text-xs text-ink-muted">Chờ rà soát</dt>
                <dd className="mt-1 text-lg font-semibold">{reviewCount}</dd>
              </div>
            </dl>
            <DataTable
              items={rows}
              empty="Chưa có tiêu chí chấp nhận hoặc liên kết truy vết"
              columns={[
                {
                  key: "source",
                  label: "Yêu cầu / tiêu chí",
                  render: (item) => (
                    <div className="min-w-0">
                      <p className="text-xs font-medium text-ink-muted">{item.kind}</p>
                      <p className="mt-1 break-words text-sm">{item.sourceLabel || item.label}</p>
                    </div>
                  ),
                  mobileRender: (item) => `${item.kind} · ${item.sourceLabel || item.label}`,
                },
                {
                  key: "test_case",
                  label: "Ca kiểm thử",
                  render: (item) =>
                    item.testCase ? (
                      <Link
                        className="font-medium text-brand hover:underline"
                        href={`/du-an/${projectId}/ca-kiem-thu?case=${encodeURIComponent(item.testCase._id)}`}
                      >
                        {item.testVersion?.test_case_key ||
                          item.testCase.test_case_key ||
                          "Ca kiểm thử"}
                        {item.testVersion?.version ? ` · v${item.testVersion.version}` : ""}
                        {item.testVersion?.title ? ` · ${item.testVersion.title}` : ""}
                      </Link>
                    ) : item.link ? (
                      item.link.target_label || "Ca kiểm thử không còn khả dụng"
                    ) : (
                      <span className="text-ink-faint">Chưa có liên kết</span>
                    ),
                },
                {
                  key: "relationship",
                  label: "Quan hệ",
                  render: (item) =>
                    item.link
                      ? relationshipLabels[item.link.link_type] || valueLabel(item.link.link_type)
                      : "—",
                },
                {
                  key: "status",
                  label: "Trạng thái",
                  render: (item) =>
                    item.link ? (
                      <StatusPill value={linkStatusLabel(item.link)} wrap />
                    ) : (
                      "Chưa liên kết"
                    ),
                },
                {
                  key: "execution",
                  label: "Kết quả gần nhất",
                  render: (item) => {
                    const execution = item.testVersion
                      ? coverage?.latest_execution?.[item.testVersion._id]
                      : null;
                    return execution ? <StatusPill value={execution.status} /> : "Chưa chạy";
                  },
                },
                {
                  key: "evidence",
                  label: "Bằng chứng",
                  render: (item) => {
                    const evidence = (item.link?.evidence || []).filter((entry) => entry.text);
                    return evidence.length ? (
                      <details>
                        <summary className="cursor-pointer text-sm">
                          Xem {evidence.length} mục
                        </summary>
                        <ul className="mt-2 list-disc space-y-1 pl-4 text-xs text-ink-muted">
                          {evidence.map((entry, index) => (
                            <li key={`${entry.text}-${index}`}>{entry.text}</li>
                          ))}
                        </ul>
                      </details>
                    ) : (
                      "—"
                    );
                  },
                },
              ]}
            />
            {!linkedCount && (
              <p className="text-xs text-ink-muted">
                Chỉ hiển thị liên kết có trong dữ liệu dự án; hệ thống không tự suy luận quan hệ
              </p>
            )}
          </>
        ) : null}
      </div>
    </Panel>
  );
}
