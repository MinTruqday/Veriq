"use client";

import Link from "next/link";
import { useCallback, useEffect, useMemo, useState } from "react";
import {
  ArrowRight,
  BookOpen,
  ClipboardCheck,
  FileBarChart2,
  FileText,
  Flag,
  GitBranch,
  PlayCircle,
  RefreshCw,
  TestTube2,
} from "lucide-react";
import { Panel, WorkspacePage } from "../../components/WorkspacePrimitives";
import { messageOf, valueLabel } from "../../lib/testing";
import { testingApi } from "../../services/testing.service";
import { PROJECT_SECTION_SLUGS, projectRoute } from "../../routes";

const STAGE_STATUS = {
  complete: new Set([
    "APPROVED",
    "BASELINED",
    "READY",
    "COMPLETED",
    "CLOSED",
    "PUBLISHED",
    "ARCHIVED",
  ]),
  attention: new Set([
    "DRAFT",
    "IN_REVIEW",
    "PENDING",
    "PROCESSING",
    "QUEUED",
    "RUNNING",
    "IN_PROGRESS",
    "AWAITING_INPUT",
    "AWAITING_AUTHORIZATION",
    "NEEDS_UPDATE",
    "DEGRADED",
  ]),
  blocked: new Set(["FAILED", "PARSE_FAILED", "BLOCKED", "REJECTED"]),
};

const STAGES = [
  {
    id: "documents",
    title: "Tài liệu",
    permission: "requirement_document.read",
    permissions: ["requirement.read"],
    icon: BookOpen,
    route: (projectId) => projectRoute(projectId, PROJECT_SECTION_SLUGS.requirements),
  },
  {
    id: "requirements",
    title: "Requirement",
    permission: "requirement.read",
    icon: FileText,
    route: (projectId) => projectRoute(projectId, PROJECT_SECTION_SLUGS.requirements),
  },
  {
    id: "plans",
    title: "Kế hoạch kiểm thử",
    permission: "testplan.read",
    icon: ClipboardCheck,
    route: (projectId) => projectRoute(projectId, PROJECT_SECTION_SLUGS.testPlans),
  },
  {
    id: "scenarios",
    title: "Kịch bản kiểm thử",
    permission: "testscenario.read",
    permissions: ["testcase.read"],
    icon: GitBranch,
    route: (projectId) => `${projectRoute(projectId, PROJECT_SECTION_SLUGS.testCases)}/kich-ban`,
  },
  {
    id: "cases",
    title: "Ca kiểm thử",
    permission: "testcase.read",
    icon: TestTube2,
    route: (projectId) => projectRoute(projectId, PROJECT_SECTION_SLUGS.testCases),
  },
  {
    id: "runs",
    title: "Lần chạy kiểm thử",
    permission: "testrun.read",
    icon: PlayCircle,
    route: (projectId) => projectRoute(projectId, PROJECT_SECTION_SLUGS.testRuns),
  },
  {
    id: "reports",
    title: "Báo cáo hoàn tất kiểm thử",
    permission: "testcompletion.read",
    icon: FileBarChart2,
    route: (projectId) =>
      `${projectRoute(projectId, PROJECT_SECTION_SLUGS.reports)}?tab=reports&testReport=completion`,
  },
  {
    id: "releases",
    title: "Bản phát hành",
    permission: "release.read",
    icon: Flag,
    route: (projectId) => projectRoute(projectId, PROJECT_SECTION_SLUGS.releases),
  },
];

function rowsOf(value) {
  if (Array.isArray(value)) return value;
  return Array.isArray(value?.items) ? value.items : [];
}

async function loadAllPages(fetchPage, query, maximumPages = 20) {
  const first = await fetchPage({ ...query, page: 1 });
  if (Array.isArray(first)) return { items: first, truncated: false };
  const items = rowsOf(first);
  const totalPages = Math.max(1, Number(first?.total_pages) || 1);
  const lastPage = Math.min(totalPages, maximumPages);
  for (let page = 2; page <= lastPage; page += 1) {
    const next = await fetchPage({ ...query, page });
    items.push(...rowsOf(next));
  }
  return { items, truncated: totalPages > maximumPages };
}

function sourceDocumentIds(record) {
  const values = new Set([
    ...(Array.isArray(record?.source_document_ids) ? record.source_document_ids : []),
    ...(Array.isArray(record?.document_ids) ? record.document_ids : []),
  ]);
  const refs = [
    ...(Array.isArray(record?.source_refs) ? record.source_refs : []),
    ...(Array.isArray(record?.current_version?.source_refs)
      ? record.current_version.source_refs
      : []),
  ];
  for (const ref of refs) {
    const documentId =
      ref?.requirement_document_id ||
      (ref?.artifact_type === "REQUIREMENT_DOCUMENT" ? ref?.artifact_id : null);
    if (documentId) values.add(String(documentId));
  }
  return values;
}

function requirementVersionIds(record) {
  const currentVersion = record?.current_version || {};
  return new Set(
    [
      ...(record?.requirement_version_ids || []),
      ...(record?.source_requirement_version_ids || []),
      ...(currentVersion.requirement_version_ids || []),
      ...(currentVersion.source_requirement_version_ids || []),
      ...(Array.isArray(record?.basis_refs)
        ? record.basis_refs
            .filter((item) => item?.artifact_type === "REQUIREMENT_VERSION")
            .flatMap((item) => [item.artifact_version_id, item.artifact_id])
            .filter(Boolean)
        : []),
    ].map(String),
  );
}

function testCaseVersionIds(record) {
  return new Set(
    [
      ...(record?.test_case_version_ids || []),
      ...(record?.approved_snapshot?.test_case_version_ids || []),
    ].map(String),
  );
}

function statusOf(record) {
  return String(record?.current_version?.status || record?.status || "").toUpperCase();
}

function stagePresentation(items, truncated, emptyLabel = "Chưa có dữ liệu") {
  if (!items.length) {
    return { count: "0", detail: emptyLabel, tone: "empty", statuses: [] };
  }
  const counts = new Map();
  for (const item of items) {
    const status = statusOf(item) || "UNSPECIFIED";
    counts.set(status, (counts.get(status) || 0) + 1);
  }
  const blocked = [...counts.keys()].some((status) => STAGE_STATUS.blocked.has(status));
  const allComplete = [...counts.keys()].every((status) => STAGE_STATUS.complete.has(status));
  const attention = [...counts.keys()].some((status) => STAGE_STATUS.attention.has(status));
  const tone = blocked ? "blocked" : allComplete ? "complete" : attention ? "attention" : "active";
  const statuses = [...counts.entries()]
    .sort((left, right) => right[1] - left[1])
    .slice(0, 2)
    .map(([status, count]) => `${count} ${valueLabel(status)}`);
  return {
    count: `${items.length}${truncated ? "+" : ""}`,
    detail: truncated
      ? `Ít nhất ${items.length} mục`
      : statuses.join(" · ") || `${items.length} mục`,
    tone,
    statuses,
  };
}

function scopeItems(data, documentId, releaseId) {
  const all = data;
  const documentReqs = all.requirements.filter((item) => sourceDocumentIds(item).has(documentId));
  const documentReqVersionIds = new Set(
    documentReqs
      .flatMap((item) => [item.current_version_id, item.current_version?._id])
      .filter(Boolean),
  );
  const releasePlans = all.plans.filter(
    (item) => item.release_id === releaseId || item.approved_snapshot?.release_id === releaseId,
  );
  const releaseReqVersionIds = new Set(
    releasePlans
      .flatMap(
        (item) =>
          item.requirement_version_ids || item.approved_snapshot?.requirement_version_ids || [],
      )
      .map(String),
  );
  const releaseCaseVersionIds = new Set(
    releasePlans.flatMap((item) => [...testCaseVersionIds(item)]),
  );

  const filterByScope = (items, documentMatcher, releaseMatcher) =>
    items.filter((item) => {
      const documentMatch = !documentId || documentMatcher(item);
      const releaseMatch = !releaseId || releaseMatcher(item);
      return documentMatch && releaseMatch;
    });

  const requirements = filterByScope(
    all.requirements,
    (item) => sourceDocumentIds(item).has(documentId),
    (item) => releaseReqVersionIds.has(String(item.current_version_id || "")),
  );
  const plans = filterByScope(
    all.plans,
    (item) =>
      (item.requirement_version_ids || []).some((id) => documentReqVersionIds.has(String(id))),
    (item) => item.release_id === releaseId || item.approved_snapshot?.release_id === releaseId,
  );
  const scenarios = filterByScope(
    all.scenarios,
    (item) =>
      (item.requirement_version_ids || []).some((id) => documentReqVersionIds.has(String(id))),
    (item) =>
      (item.requirement_version_ids || []).some((id) => releaseReqVersionIds.has(String(id))),
  );
  const cases = filterByScope(
    all.cases,
    (item) => [...requirementVersionIds(item)].some((id) => documentReqVersionIds.has(id)),
    (item) =>
      releaseCaseVersionIds.has(String(item.current_version_id || "")) ||
      [...requirementVersionIds(item)].some((id) => releaseReqVersionIds.has(id)),
  );
  const caseVersionSet = new Set(cases.map((item) => String(item.current_version_id || "")));
  const planIds = new Set(plans.map((item) => String(item._id)));
  const runs = filterByScope(
    all.runs,
    (item) =>
      planIds.has(String(item.test_plan_id || "")) ||
      [...testCaseVersionIds(item)].some((id) => caseVersionSet.has(id)),
    (item) =>
      item.release_id === releaseId ||
      planIds.has(String(item.test_plan_id || "")) ||
      [...testCaseVersionIds(item)].some((id) => releaseCaseVersionIds.has(id)),
  );
  const runIds = new Set(runs.map((item) => String(item._id)));
  const reports = filterByScope(
    all.reports,
    (item) =>
      planIds.has(String(item.test_plan_id || "")) ||
      (item.completed_run_ids || item.run_ids || []).some((id) => runIds.has(String(id))),
    (item) =>
      item.release_id === releaseId ||
      planIds.has(String(item.test_plan_id || "")) ||
      (item.completed_run_ids || item.run_ids || []).some((id) => runIds.has(String(id))),
  );
  const releaseIds = new Set(
    [
      ...(documentId ? plans.map((item) => item.release_id).filter(Boolean) : []),
      ...(releaseId ? [releaseId] : []),
    ].map(String),
  );
  const releases = releaseId
    ? all.releases.filter((item) => String(item._id) === String(releaseId))
    : documentId
      ? all.releases.filter((item) => releaseIds.has(String(item._id)))
      : all.releases;
  const documents = documentId
    ? all.documents.filter((item) => String(item._id) === String(documentId))
    : all.documents;
  return { documents, requirements, plans, scenarios, cases, runs, reports, releases };
}

function toneClasses(tone) {
  return {
    complete: "border-emerald-200 bg-emerald-50 text-emerald-900",
    attention: "border-amber-200 bg-amber-50 text-amber-950",
    blocked: "border-rose-200 bg-rose-50 text-rose-950",
    active: "border-violet-200 bg-violet-50 text-violet-950",
    empty: "border-border bg-surface-raised text-ink-muted",
  }[tone];
}

function WorkflowNode({ stage, projectId, compact = false }) {
  const Icon = stage.icon;
  const detail = stage.presentation.detail;
  return (
    <Link
      aria-label={`${stage.title}: ${stage.presentation.count} mục. Mở trang ${stage.title}.`}
      className={`relative z-10 flex min-w-0 items-center justify-between gap-3 rounded-xl border transition hover:border-violet-400 hover:shadow-sm focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-violet-500 ${compact ? "min-h-14 px-3 py-2" : "min-h-[84px] px-4 py-3"} ${toneClasses(stage.presentation.tone)}`}
      href={stage.route(projectId)}
    >
      <span className="flex min-w-0 items-start gap-3">
        <Icon
          aria-hidden="true"
          className="mt-0.5 shrink-0 text-violet-700"
          size={compact ? 16 : 19}
        />
        <span className="min-w-0">
          <span className="block text-sm font-semibold leading-5">{stage.title}</span>
          <span className="mt-1 line-clamp-1 block text-xs leading-4 text-ink-muted">{detail}</span>
        </span>
      </span>
      <span className="flex shrink-0 items-center gap-2">
        <span className="text-lg font-semibold tabular-nums">{stage.presentation.count}</span>
        <ArrowRight aria-hidden="true" className="text-violet-700" size={15} />
      </span>
    </Link>
  );
}

function WorkflowTree({ project, data, scope, compact = false }) {
  const permissions = new Set(project.current_permissions || []);
  const visibleStages = STAGES.filter(
    (stage) =>
      permissions.has(stage.permission) &&
      (stage.permissions || []).every((permission) => permissions.has(permission)),
  );
  const scoped = scopeItems(data, scope.documentId, scope.releaseId);
  const stageRows = visibleStages.map((stage) => ({
    ...stage,
    presentation: stagePresentation(scoped[stage.id] || [], Boolean(data.truncated?.[stage.id])),
  }));
  if (!stageRows.length) {
    return (
      <p className="p-4 text-sm text-ink-muted">Bạn chưa có quyền xem các chặng của quy trình.</p>
    );
  }
  return (
    <div
      aria-label="Cây quy trình kiểm thử của dự án"
      className={`mx-auto w-full ${compact ? "max-w-3xl px-4 pb-4 pt-2 sm:px-5" : "max-w-4xl px-3 pb-4 pt-3 sm:px-5"}`}
      role="group"
    >
      <ol aria-label="Các chặng quy trình" className="relative grid gap-0">
        {stageRows.map((stage, index) => (
          <li className={`relative min-w-0 ${compact ? "pb-2 pl-8" : "pb-3 pl-10"}`} key={stage.id}>
            {index < stageRows.length - 1 && (
              <span
                aria-hidden="true"
                className="absolute bottom-[-1px] left-[7px] top-4 w-0.5 bg-violet-300"
              />
            )}
            <span
              aria-hidden="true"
              className="absolute left-0 top-[9px] h-4 w-4 rounded-full border-[3px] border-violet-600 bg-white"
            />
            <span
              aria-hidden="true"
              className="absolute left-[7px] top-4 h-0.5 w-5 bg-violet-400"
            />
            <WorkflowNode compact={compact} projectId={project._id} stage={stage} />
          </li>
        ))}
      </ol>
    </div>
  );
}

function emptyData() {
  return {
    documents: [],
    requirements: [],
    plans: [],
    scenarios: [],
    cases: [],
    runs: [],
    reports: [],
    releases: [],
    truncated: {},
  };
}

export function ProjectWorkflowSummary({ project }) {
  return <ProjectWorkflowSurface project={project} compact />;
}

export default function ProjectWorkflowPage({ project }) {
  return <ProjectWorkflowSurface project={project} />;
}

function ProjectWorkflowSurface({ project, compact = false }) {
  const [data, setData] = useState(emptyData);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");
  const [reloadVersion, setReloadVersion] = useState(0);
  const [documentId, setDocumentId] = useState("");
  const [releaseId, setReleaseId] = useState("");
  const permissions = useMemo(
    () => new Set(project.current_permissions || []),
    [project.current_permissions],
  );
  const load = useCallback(
    async (isActive = () => true) => {
      setLoading(true);
      setError("");
      const can = (permission) => permissions.has(permission);
      const requests = [
        [
          "documents",
          can("requirement_document.read")
            ? testingApi.listRequirementDocuments(project._id, "limit=1000")
            : Promise.resolve([]),
        ],
        [
          "requirements",
          can("requirement.read")
            ? loadAllPages(
                (query) =>
                  testingApi.listRequirementPage(project._id, { ...query, page_size: 200 }),
                { page_size: 200 },
              )
            : Promise.resolve({ items: [] }),
        ],
        ["plans", can("testplan.read") ? testingApi.listPlans(project._id) : Promise.resolve([])],
        [
          "scenarios",
          can("testscenario.read")
            ? testingApi.listScenarios(project._id, { limit: 500 })
            : Promise.resolve([]),
        ],
        [
          "cases",
          can("testcase.read")
            ? loadAllPages(
                (query) => testingApi.listTestCasePage(project._id, { ...query, page_size: 500 }),
                { page_size: 500 },
              )
            : Promise.resolve({ items: [] }),
        ],
        [
          "runs",
          can("testrun.read")
            ? loadAllPages(
                (query) => testingApi.listRunPage(project._id, { ...query, page_size: 500 }),
                { page_size: 500 },
              )
            : Promise.resolve({ items: [] }),
        ],
        [
          "reports",
          can("testcompletion.read")
            ? testingApi.listTestCompletionReports(project._id, { limit: 500 })
            : Promise.resolve([]),
        ],
        [
          "releases",
          can("release.read") ? testingApi.listReleases(project._id) : Promise.resolve([]),
        ],
      ];
      const results = await Promise.allSettled(requests.map(([, request]) => request));
      if (!isActive()) return;
      const next = emptyData();
      const errors = [];
      results.forEach((result, index) => {
        const [key] = requests[index];
        if (result.status === "fulfilled") {
          const value = result.value;
          if (["requirements", "cases", "runs"].includes(key)) {
            next[key] = rowsOf(value);
            if (value?.truncated) next.truncated[key] = true;
          } else {
            next[key] = rowsOf(value);
            if (
              next[key].length >=
              ({ documents: 1000, scenarios: 500, reports: 500 }[key] || Infinity)
            ) {
              next.truncated[key] = true;
            }
          }
        } else if (result.reason?.status !== 403) {
          errors.push(messageOf(result.reason));
        }
      });
      setData(next);
      setError(errors[0] || "");
      setLoading(false);
    },
    [permissions, project._id],
  );

  useEffect(() => {
    let active = true;
    void load(() => active);
    return () => {
      active = false;
    };
  }, [load, reloadVersion]);

  const scope = { documentId, releaseId };
  const canReadDocuments = permissions.has("requirement_document.read");
  const canReadReleases = permissions.has("release.read");

  if (compact) {
    return (
      <Panel
        actions={
          <Link
            className="secondary-button inline-flex items-center gap-2"
            href={projectRoute(project._id, PROJECT_SECTION_SLUGS.workflow)}
          >
            Xem quy trình <ArrowRight aria-hidden="true" size={15} />
          </Link>
        }
        title="Quy trình kiểm thử"
        description="Theo dõi từ tài liệu nguồn đến bản phát hành. Chọn một chặng để mở trang nghiệp vụ."
      >
        {loading ? (
          <div className="p-4 text-sm text-ink-muted">Đang tải tiến độ quy trình…</div>
        ) : error ? (
          <div className="flex flex-wrap items-center justify-between gap-3 p-4">
            <p className="text-sm text-danger">{error}</p>
            <button
              className="secondary-button inline-flex items-center gap-2"
              onClick={() => setReloadVersion((current) => current + 1)}
              type="button"
            >
              <RefreshCw aria-hidden="true" size={15} /> Tải lại
            </button>
          </div>
        ) : (
          <WorkflowTree project={project} data={data} scope={scope} compact />
        )}
      </Panel>
    );
  }

  return (
    <WorkspacePage
      title="Quy trình kiểm thử"
      description="Theo dõi các chặng bằng trạng thái và dữ liệu đã lưu trong dự án. Bấm vào một chặng để mở trang tương ứng."
      actions={
        <button
          className="secondary-button inline-flex items-center gap-2"
          disabled={loading}
          onClick={() => setReloadVersion((current) => current + 1)}
          type="button"
        >
          <RefreshCw aria-hidden="true" size={15} /> Tải lại dữ liệu
        </button>
      }
    >
      <Panel title="Phạm vi theo dõi" description="Lọc cây theo nguồn tài liệu hoặc bản phát hành.">
        <div className="grid gap-3 p-4 sm:grid-cols-2 sm:p-5">
          {canReadDocuments && (
            <label className="min-w-0 space-y-1.5 text-sm font-medium text-ink">
              <span>Tài liệu nguồn</span>
              <select
                className="apple-input w-full"
                value={documentId}
                onChange={(event) => setDocumentId(event.target.value)}
              >
                <option value="">Toàn bộ tài liệu</option>
                {data.documents.map((item) => (
                  <option key={item._id} value={item._id}>
                    {item.title || item.filename || item._id}
                  </option>
                ))}
              </select>
            </label>
          )}
          {canReadReleases && (
            <label className="min-w-0 space-y-1.5 text-sm font-medium text-ink">
              <span>Bản phát hành</span>
              <select
                className="apple-input w-full"
                value={releaseId}
                onChange={(event) => setReleaseId(event.target.value)}
              >
                <option value="">Tất cả bản phát hành</option>
                {data.releases.map((item) => (
                  <option key={item._id} value={item._id}>
                    {[item.key, item.name, item.version].filter(Boolean).join(" · ") || item._id}
                  </option>
                ))}
              </select>
            </label>
          )}
          {!canReadDocuments && !canReadReleases && (
            <p className="text-sm text-ink-muted">
              Tài khoản hiện không có quyền lọc theo tài liệu hoặc bản phát hành.
            </p>
          )}
        </div>
      </Panel>
      {error && (
        <div className="flex flex-wrap items-center justify-between gap-3 rounded-xl border border-amber-200 bg-amber-50 p-4 text-sm text-amber-950">
          <span>Một số chặng chưa tải được: {error}</span>
          <button
            className="secondary-button inline-flex items-center gap-2"
            disabled={loading}
            onClick={() => setReloadVersion((current) => current + 1)}
            type="button"
          >
            <RefreshCw aria-hidden="true" size={15} /> Tải lại
          </button>
        </div>
      )}
      {loading ? (
        <Panel title="Tiến độ quy trình">
          <div className="p-5 text-sm text-ink-muted">Đang tải dữ liệu quy trình…</div>
        </Panel>
      ) : (
        <Panel title="Tiến độ quy trình">
          <WorkflowTree project={project} data={data} scope={scope} />
        </Panel>
      )}
      <p className="text-xs leading-5 text-ink-muted">
        Trạng thái và số lượng lấy từ dữ liệu hiện có. Chặng chưa có quan hệ truy vết phù hợp có thể
        không được tính khi lọc theo phạm vi.
      </p>
    </WorkspacePage>
  );
}
