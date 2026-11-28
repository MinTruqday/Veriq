"use client";

import { useCallback, useEffect, useRef, useState } from "react";
import Link from "next/link";
import {
  BookOpen,
  ClipboardCheck,
  FileText,
  GitBranch,
  RefreshCw,
  TestTube2,
  X,
} from "lucide-react";
import { useAuth } from "@/features/authentication/contexts/AuthContext";
import {
  agentAuthorizationGuidance,
  canResumeAIRun,
  agentCheckpointView,
  aiRunProgress,
  aiRunErrorMessage,
  latestAgentUncertainties,
  agentSourceExtractionGaps,
} from "../lib/aiRun.logic.mjs";
import { formatDate, messageOf, valueLabel } from "../lib/testing";
import { preferredSummaryLocale } from "../lib/summaryLanguage";
import { testingApi } from "../services/testing.service";
import { ErrorState, LoadingState, Panel, StatusPill } from "./WorkspacePrimitives";
import ContentOriginBadge from "../../../shared/components/common/ContentOriginBadge";
import { useDateTimeOptions } from "../hooks/useDateTimeOptions";
import SearchField from "@/shared/components/ui/SearchField";

const activeStatuses = new Set(["QUEUED", "RUNNING", "VERIFYING"]);

const documentWorkflowStageLabels = {
  test_plan: "Kế hoạch kiểm thử",
  test_scenarios: "Kịch bản kiểm thử",
  test_cases: "Ca kiểm thử",
};

const documentWorkflowStatusLabels = {
  COMPLETED: "Đã hoàn tất",
  DRAFT_CREATED: "Đã tạo bản nháp",
  PROPOSED: "Có đề xuất để xem",
  PARTIAL_OR_BLOCKED: "Mới hoàn tất một phần hoặc đang bị chặn",
  BLOCKED: "Đang bị chặn",
  NOT_STARTED: "Chưa thực hiện",
  IN_PROGRESS: "Đang thực hiện",
};

function documentWorkflowResult(run) {
  if (run?.intent !== "process_ingested_requirement_document") return null;
  const observations = Array.isArray(run?.result?.observations) ? run.result.observations : [];
  return (
    observations
      .filter(
        (item) =>
          item?.tool_name === "process_ingested_requirement_document" &&
          item?.status === "COMPLETED" &&
          item?.result?.workflow_stages &&
          typeof item.result.workflow_stages === "object",
      )
      .map((item) => item.result)
      .at(-1) || null
  );
}

function documentWorkflowStageHref(projectId, stage) {
  const base = `/du-an/${encodeURIComponent(projectId)}`;
  if (stage === "requirements") return `${base}/yeu-cau`;
  if (stage === "test_scenarios") return `${base}/ca-kiem-thu/kich-ban`;
  if (stage === "test_cases") return `${base}/ca-kiem-thu`;
  return "";
}

const documentWorkflowIcons = {
  document: BookOpen,
  requirements: FileText,
  test_plan: ClipboardCheck,
  test_scenarios: GitBranch,
  test_cases: TestTube2,
};

function documentWorkflowTreeStages(projectId, workflow) {
  const requirementIds = Array.isArray(workflow.requirement_ids) ? workflow.requirement_ids : [];
  const stages = [
    {
      key: "document",
      label: "Tài liệu nguồn",
      status: "COMPLETED",
      detail: workflow.source_document_title || "Đã nhập và xử lý tài liệu",
      href: workflow.source_document_id
        ? `/du-an/${encodeURIComponent(projectId)}/tai-lieu/${encodeURIComponent(workflow.source_document_id)}`
        : documentWorkflowStageHref(projectId, "requirements"),
    },
    {
      key: "requirements",
      label: "Requirement",
      status: requirementIds.length ? "DRAFT_CREATED" : "PARTIAL_OR_BLOCKED",
      detail: requirementIds.length
        ? `${requirementIds.length} Requirement từ lượt AI này`
        : "Chưa tạo được Requirement",
      href: requirementIds.length
        ? `/du-an/${encodeURIComponent(projectId)}/yeu-cau/${encodeURIComponent(requirementIds[0])}`
        : documentWorkflowStageHref(projectId, "requirements"),
    },
    ...Object.entries(documentWorkflowStageLabels).map(([key, label]) => ({
      key,
      label,
      ...(workflow.workflow_stages?.[key] || {}),
      href: documentWorkflowStageHref(projectId, key),
    })),
  ];
  return stages.map((stage) => ({ ...stage, Icon: documentWorkflowIcons[stage.key] }));
}

function agentOriginLabel(run) {
  const providedLabel = String(run?.trigger_label || run?.trigger_display_name || "").trim();
  const userRequested =
    run?.trigger === "MANUAL" ||
    run?.constraints?.user_requested === true ||
    run?.user_requested === true;
  if (userRequested && providedLabel) return providedLabel;
  if (run?.trigger === "MANUAL") return "Theo yêu cầu người dùng";
  if (run?.trigger === "DOCUMENT_INGESTED" && userRequested) {
    return "Theo yêu cầu xử lý tài liệu";
  }
  return "Hoạt động AI trước đây";
}

function aiRunTitle(run) {
  if (run?.intent === "process_ingested_requirement_document") {
    return "Xử lý tài liệu yêu cầu";
  }
  const internalCode = /\b[A-Z][A-Z0-9]*(?:_+[A-Z0-9]+)+\b/;
  const summary = [
    run?.display_name,
    run?.title,
    run?.result?.summary,
    run?.result?.message,
    run?.objective,
  ]
    .map((value) => String(value || "").trim())
    .find((value) => value && !internalCode.test(value));
  if (summary) return summary;
  if (run?.trigger === "MANUAL") return "Yêu cầu xử lý AI";
  if (run?.trigger === "DOCUMENT_INGESTED" && run?.constraints?.user_requested === true) {
    return "Rà soát tài liệu theo yêu cầu";
  }
  return "Hoạt động AI";
}

function sourceFactSummary(fact) {
  const sourceType = fact?.artifact_type ? valueLabel(fact.artifact_type) : "Tài liệu nguồn";
  const pages = Array.isArray(fact?.source_page_numbers) ? fact.source_page_numbers : [];
  return pages.length
    ? `${sourceType} · Trang ${pages.join(", ")}`
    : `${sourceType} · Đoạn trích đã xác minh`;
}

function displayEvidenceQuote(quote) {
  return String(quote || "").replace(/\\r\\n|\\n|\\r/g, "\n");
}

function sourceFactHref(projectId, fact) {
  const artifactId = fact?.artifact_id;
  if (!artifactId) return "";
  if (fact.artifact_type === "requirement_version") {
    return `/du-an/${encodeURIComponent(projectId)}/yeu-cau/${encodeURIComponent(artifactId)}`;
  }
  if (fact.artifact_type === "test_case_version") {
    return `/du-an/${encodeURIComponent(projectId)}/ca-kiem-thu?case=${encodeURIComponent(artifactId)}`;
  }
  return "";
}

function evidenceReferencesInSummary(summary) {
  const references = new Set();
  const pattern = /\[([^\]]+)\]|\((?:Nguồn|Source)\s*:\s*([A-Z][A-Z0-9_-]*-[A-Za-z0-9_-]{8,})\)/gi;
  let match;
  while ((match = pattern.exec(String(summary || ""))) !== null) {
    const values = match[1] ? match[1].split(",") : [match[2]];
    values
      .map((reference) => reference.trim())
      .filter(Boolean)
      .forEach((reference) => {
        references.add(reference);
      });
  }
  return references;
}

function proposalSummaryParts(summary, evidenceReferences) {
  const referenceNumbers = new Map();
  const referenceEntries = new Map();
  evidenceReferences.forEach((item) => {
    [
      item.reference,
      item.fact?.source_fact_id,
      item.fact?.artifact_id,
      item.fact?.artifact_version_id,
    ]
      .filter(Boolean)
      .forEach((reference) => {
        if (!referenceNumbers.has(reference)) referenceNumbers.set(reference, item.number);
        if (!referenceEntries.has(reference)) referenceEntries.set(reference, item);
      });
  });
  const parts = [];
  const markerPattern =
    /\[([^\]]+)\]|\((Nguồn|Source)\s*:\s*([A-Z][A-Z0-9_-]*-[A-Za-z0-9_-]{8,})\)/gi;
  let lastIndex = 0;
  let match;
  while ((match = markerPattern.exec(String(summary || ""))) !== null) {
    if (match[2]) {
      const language = match[2].toLocaleLowerCase() === "source" ? "en" : "vi";
      const reference = match[3];
      const number = referenceNumbers.get(reference);
      const item = referenceEntries.get(reference);
      if (match.index > lastIndex) parts.push(String(summary || "").slice(lastIndex, match.index));
      if (!number || !item) {
        parts.push(language === "en" ? "(Unverified source)" : "(Nguồn chưa đối chiếu)");
      } else {
        const href = sourceFactHref(item.projectId, item.fact);
        const label = language === "en" ? `Source ${number}` : `Nguồn ${number}`;
        const citation = href ? (
          <Link
            className="font-medium text-brand underline-offset-2 hover:underline"
            href={href}
            key={`inline-source-${match.index}`}
          >
            {label}
          </Link>
        ) : (
          <span className="font-medium text-brand" key={`inline-source-${match.index}`}>
            {label}
          </span>
        );
        parts.push("(", citation, ")");
      }
      lastIndex = markerPattern.lastIndex;
      continue;
    }
    const references = match[1].split(",").map((reference) => reference.trim());
    const hasInternalReference = references.some((reference) => referenceNumbers.has(reference));
    const looksLikeInternalReference = references.some((reference) =>
      /^[A-Z0-9_-]{8,}$/.test(reference),
    );
    if (!hasInternalReference && !looksLikeInternalReference) continue;
    if (match.index > lastIndex) parts.push(String(summary || "").slice(lastIndex, match.index));
    if (!hasInternalReference) {
      parts.push(
        <span className="text-ink-muted" key={`unresolved-${match.index}`}>
          [Căn cứ chưa đối chiếu]
        </span>,
      );
    } else {
      const citations = references.map((reference, index) => {
        const item = referenceEntries.get(reference);
        if (!item) {
          return (
            <span className="text-ink-muted" key={`${match.index}-missing-${index}`}>
              Nguồn chưa tải được
            </span>
          );
        }
        const label = `Nguồn ${referenceNumbers.get(reference)}`;
        const href = sourceFactHref(item.projectId, item.fact);
        return href ? (
          <Link
            className="font-medium text-brand underline-offset-2 hover:underline"
            href={href}
            key={`${match.index}-${reference}`}
          >
            {label}
          </Link>
        ) : (
          <span className="font-medium text-brand" key={`${match.index}-${reference}`}>
            {label}
          </span>
        );
      });
      parts.push(
        <span className="inline-flex flex-wrap gap-x-1" key={`citation-${match.index}`}>
          [{citations.map((citation, index) => (index ? [", ", citation] : citation))}]
        </span>,
      );
    }
    lastIndex = markerPattern.lastIndex;
  }
  if (lastIndex < String(summary || "").length) parts.push(String(summary || "").slice(lastIndex));
  return parts.length ? parts : [String(summary || "")];
}

function isOlderRunSnapshot(incoming, current) {
  if (!incoming || !current) return false;
  const incomingRevision = Number(incoming.revision);
  const currentRevision = Number(current.revision);
  if (!Number.isFinite(incomingRevision) || !Number.isFinite(currentRevision)) return false;
  return (
    incomingRevision < currentRevision ||
    (incomingRevision === currentRevision && incoming.status !== current.status)
  );
}

export default function AIRunPanel({
  project,
  compact = false,
  showPanelHeading = true,
  contextContent = null,
  onRunsStateChange,
  targetArtifactIds = [],
  targetArtifactLabels = {},
}) {
  const { user } = useAuth();
  const dateTimeOptions = useDateTimeOptions(project);
  const currentUserId = project.current_membership?.user_id;
  const permissions = project.current_permissions || [];
  const permissionKey = permissions.join("|");
  const canReadProjectRuns = permissions.includes("proposal.read");
  const canReadOwnAIRuns = permissions.includes("requirement.read");
  const canViewRun = (item) => canReadProjectRuns || item?.requester_user_id === currentUserId;
  const [recentRuns, setRecentRuns] = useState([]);
  const [agentCapabilities, setAgentCapabilities] = useState([]);
  const [run, setRun] = useState(null);
  const [checkpoints, setCheckpoints] = useState([]);
  const [dismissedProgressRunId, setDismissedProgressRunId] = useState(null);
  const [receipt, setReceipt] = useState(null);
  const [sourceFacts, setSourceFacts] = useState([]);
  const [toolEvidence, setToolEvidence] = useState([]);
  const [busy, setBusy] = useState(false);
  const [refreshingRuns, setRefreshingRuns] = useState(false);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");
  const [runsRefreshError, setRunsRefreshError] = useState("");
  const [detailRefreshError, setDetailRefreshError] = useState("");
  const [initialLoadAttempt, setInitialLoadAttempt] = useState(0);
  const [agentInstruction, setAgentInstruction] = useState("");
  const [runQuery, setRunQuery] = useState("");
  const [runStatusFilter, setRunStatusFilter] = useState("ALL");
  const [startingAgent, setStartingAgent] = useState(false);
  const [agentStartError, setAgentStartError] = useState("");
  const agentIdempotencyKey = useRef("");
  const agentIdempotencyFingerprint = useRef("");
  const detailRequestVersion = useRef(0);
  const runListRequestVersion = useRef(0);
  const selectedRunIdRef = useRef(null);
  const selectedRunSnapshotRef = useRef(null);

  useEffect(() => {
    let active = true;
    const listRequestVersion = ++runListRequestVersion.current;
    detailRequestVersion.current += 1;
    setLoading(true);
    setError("");
    setRunsRefreshError("");
    setDetailRefreshError("");
    setRecentRuns([]);
    setAgentCapabilities([]);
    onRunsStateChange?.({ runs: [], error: "", loading: true });
    setRun(null);
    selectedRunIdRef.current = null;
    selectedRunSnapshotRef.current = null;
    setCheckpoints([]);
    setReceipt(null);
    setSourceFacts([]);
    setToolEvidence([]);
    Promise.allSettled([
      canReadProjectRuns || canReadOwnAIRuns
        ? testingApi.listAIRuns(project._id)
        : Promise.resolve([]),
      testingApi.listAIRunCapabilities(project._id),
    ])
      .then((results) => {
        if (!active) return;
        const values = results.map((result) => (result.status === "fulfilled" ? result.value : []));
        if (listRequestVersion === runListRequestVersion.current) {
          setRecentRuns(values[0]);
          const runListError = results[0].status === "rejected" ? messageOf(results[0].reason) : "";
          onRunsStateChange?.({
            runs: values[0],
            error: runListError,
            loading: false,
          });
        }
        setAgentCapabilities(values[1]);
        setError(
          results
            .filter(
              (result, index) =>
                result.status === "rejected" && !(index === 1 && result.reason?.status === 403),
            )
            .map((result) => messageOf(result.reason))
            .filter(Boolean)
            .join(" · "),
        );
      })
      .finally(() => active && setLoading(false));
    return () => {
      active = false;
      if (listRequestVersion === runListRequestVersion.current) {
        runListRequestVersion.current += 1;
      }
    };
  }, [
    canReadOwnAIRuns,
    canReadProjectRuns,
    currentUserId,
    initialLoadAttempt,
    onRunsStateChange,
    project._id,
    permissionKey,
  ]);

  const refreshRuns = useCallback(async () => {
    if (!canReadProjectRuns && !canReadOwnAIRuns) return;
    const requestVersion = ++runListRequestVersion.current;
    const selectedRunId = selectedRunIdRef.current;
    const selectionVersion = detailRequestVersion.current;
    const items = await testingApi.listAIRuns(project._id);
    if (requestVersion !== runListRequestVersion.current) return;
    setRecentRuns(items);
    onRunsStateChange?.({ runs: items, error: "", loading: false });
    if (
      selectedRunId === selectedRunIdRef.current &&
      selectionVersion === detailRequestVersion.current
    ) {
    }
    setRunsRefreshError("");
  }, [canReadOwnAIRuns, canReadProjectRuns, onRunsStateChange, project._id]);

  const refreshRunList = async () => {
    if (refreshingRuns) return;
    setRefreshingRuns(true);
    try {
      await refreshRuns();
    } catch (reason) {
      setRunsRefreshError(messageOf(reason));
    } finally {
      setRefreshingRuns(false);
    }
  };

  const loadRun = async (runId) => {
    const requestVersion = ++detailRequestVersion.current;
    if (selectedRunIdRef.current !== runId) setDismissedProgressRunId(null);
    selectedRunIdRef.current = runId;
    selectedRunSnapshotRef.current = null;
    setSourceFacts([]);
    setToolEvidence([]);
    setDetailRefreshError("");
    if (run?.ai_run_id !== runId) {
      setRun(null);
      setCheckpoints([]);
      setReceipt(null);
    }
    let detail;
    try {
      detail = await testingApi.getAIRun(runId);
    } catch (reason) {
      if (requestVersion !== detailRequestVersion.current) return;
      throw reason;
    }
    if (requestVersion !== detailRequestVersion.current) return;
    selectedRunSnapshotRef.current = {
      revision: detail.run.revision,
      status: detail.run.status,
    };
    setRun(detail.run);
    setCheckpoints(detail.checkpoints || []);
    setReceipt(detail.receipt || null);
    try {
      const evidence = await testingApi.getAIRunEvidence(runId);
      if (requestVersion !== detailRequestVersion.current) return;
      setReceipt(evidence.receipt || detail.receipt || null);
      setSourceFacts(evidence.source_facts || []);
      setToolEvidence(evidence.tool_evidence || []);
    } catch (reason) {
      if (requestVersion === detailRequestVersion.current) {
        setDetailRefreshError(messageOf(reason));
      }
    }
  };

  useEffect(() => {
    if (!run || !activeStatuses.has(run.status)) {
      return undefined;
    }
    let active = true;
    let pending = false;
    const timer = window.setInterval(async () => {
      if (document.visibilityState !== "visible" || pending) return;
      pending = true;
      const requestVersion = detailRequestVersion.current;
      try {
        const detail = await testingApi.getAIRun(run.ai_run_id);
        if (!active || requestVersion !== detailRequestVersion.current) return;
        if (isOlderRunSnapshot(detail.run, selectedRunSnapshotRef.current)) return;
        let evidence = null;
        let evidenceError = "";
        if (!activeStatuses.has(detail.run.status)) {
          try {
            evidence = await testingApi.getAIRunEvidence(run.ai_run_id);
          } catch (reason) {
            evidenceError = messageOf(reason);
          }
        }
        if (
          !active ||
          requestVersion !== detailRequestVersion.current ||
          selectedRunIdRef.current !== run.ai_run_id ||
          isOlderRunSnapshot(detail.run, selectedRunSnapshotRef.current)
        ) {
          return;
        }
        selectedRunSnapshotRef.current = {
          revision: detail.run.revision,
          status: detail.run.status,
        };
        setDetailRefreshError(evidenceError);
        setRun(detail.run);
        setCheckpoints(detail.checkpoints || []);
        setReceipt(evidence?.receipt || detail.receipt || null);
        if (evidence) {
          setSourceFacts(evidence.source_facts || []);
          setToolEvidence(evidence.tool_evidence || []);
        } else if (evidenceError) {
          setSourceFacts([]);
          setToolEvidence([]);
        }
        if (!activeStatuses.has(detail.run.status)) {
          try {
            await refreshRuns();
          } catch (reason) {
            if (active) setRunsRefreshError(messageOf(reason));
          }
        }
      } catch (reason) {
        if (active) setDetailRefreshError(messageOf(reason));
      } finally {
        pending = false;
      }
    }, 2500);
    return () => {
      active = false;
      window.clearInterval(timer);
    };
  }, [run, refreshRuns]);

  const retry = async () => {
    if (!run) return;
    const runId = run.ai_run_id;
    const selectionVersion = detailRequestVersion.current;
    setBusy(true);
    setError("");
    try {
      try {
        await testingApi.resumeAIRun(runId, {
          expected_revision: run.revision,
        });
      } catch (reason) {
        if (selectionVersion === detailRequestVersion.current) {
          setError(messageOf(reason));
          try {
            await loadRun(runId);
          } catch (refreshReason) {
            setDetailRefreshError(messageOf(refreshReason));
          }
        }
        return;
      }
      try {
        await refreshRuns();
      } catch (reason) {
        setRunsRefreshError(messageOf(reason));
      }
      if (selectionVersion === detailRequestVersion.current) {
        try {
          await loadRun(runId);
          setDetailRefreshError("");
        } catch (reason) {
          setDetailRefreshError(messageOf(reason));
        }
      }
    } finally {
      setBusy(false);
    }
  };

  const cancel = async () => {
    if (!run) return;
    const runId = run.ai_run_id;
    const selectionVersion = detailRequestVersion.current;
    setBusy(true);
    setError("");
    try {
      try {
        await testingApi.cancelAIRun(runId, {
          expected_revision: run.revision,
        });
      } catch (reason) {
        if (selectionVersion === detailRequestVersion.current) {
          setError(messageOf(reason));
          try {
            await loadRun(runId);
          } catch (refreshReason) {
            setDetailRefreshError(messageOf(refreshReason));
          }
        }
        return;
      }
      try {
        await refreshRuns();
      } catch (reason) {
        setRunsRefreshError(messageOf(reason));
      }
      if (selectionVersion === detailRequestVersion.current) {
        try {
          await loadRun(runId);
        } catch (reason) {
          setDetailRefreshError(messageOf(reason));
        }
      }
    } finally {
      setBusy(false);
    }
  };

  const proposal = run?.result?.proposal;
  const sourceExtractionWarnings = (run?.result?.observations || []).flatMap((observation) =>
    observation?.tool_name === "process_ingested_requirement_document" &&
    Array.isArray(observation?.result?.source_extraction_warnings)
      ? observation.result.source_extraction_warnings
      : [],
  );
  const documentWorkflow = documentWorkflowResult(run);
  const documentWorkflowStages = documentWorkflow?.workflow_stages || null;
  const sourceFactsById = new Map(
    sourceFacts.flatMap((fact) =>
      [fact.source_fact_id, fact.artifact_id, fact.artifact_version_id]
        .filter(Boolean)
        .map((reference) => [reference, fact]),
    ),
  );
  const toolEvidenceById = new Map(toolEvidence.map((item) => [item.evidence_ref, item]));
  const agentCapabilityLabels = new Map(
    agentCapabilities
      .filter((item) => item?.name && item?.label)
      .map((item) => [item.name, item.label]),
  );
  const proposalEvidenceReferences = [];
  const evidenceNumbersByIdentity = new Map();
  (proposal?.evidence_refs || []).forEach((reference) => {
    const fact = sourceFactsById.get(reference) || null;
    const toolResult = toolEvidenceById.get(reference) || null;
    const identity = fact?.source_fact_id || reference;
    let number = evidenceNumbersByIdentity.get(identity);
    if (!number) {
      number = proposalEvidenceReferences.length + 1;
      evidenceNumbersByIdentity.set(identity, number);
      proposalEvidenceReferences.push({
        reference,
        number,
        fact,
        toolResult,
        projectId: project._id,
      });
    } else if (fact || toolResult) {
      const existing = proposalEvidenceReferences[number - 1];
      if (!existing.fact) existing.fact = fact;
      if (!existing.toolResult) existing.toolResult = toolResult;
    }
  });
  const summaryEvidenceReferences = evidenceReferencesInSummary(proposal?.summary);
  const citedProposalEvidenceReferences = proposalEvidenceReferences
    .filter((item) =>
      [
        item.reference,
        item.fact?.source_fact_id,
        item.fact?.artifact_id,
        item.fact?.artifact_version_id,
        item.toolResult?.artifact_id,
      ].some((reference) => reference && summaryEvidenceReferences.has(reference)),
    )
    .map((item, index) => ({ ...item, number: index + 1 }));
  const proposalEvidenceFactIds = new Set(
    proposalEvidenceReferences.map((item) => item.fact?.source_fact_id).filter(Boolean),
  );
  const unlinkedSourceFacts = sourceFacts.filter(
    (fact) => !proposalEvidenceFactIds.has(fact.source_fact_id),
  );
  const busyRun = run && activeStatuses.has(run.status);
  const accessibleRuns = recentRuns.filter(canViewRun);
  const availableRunStatuses = [
    ...new Set(accessibleRuns.map((item) => item.status).filter(Boolean)),
  ];
  const normalizedRunQuery = runQuery.trim().toLocaleLowerCase("vi");
  const visibleRuns = accessibleRuns.filter((item) => {
    const matchesStatus = runStatusFilter === "ALL" || item.status === runStatusFilter;
    const searchable = [
      aiRunTitle(item),
      item.display_name,
      item.trigger_label,
      item.trigger_display_name,
      item.objective,
      item.status ? valueLabel(item.status) : "",
    ]
      .filter(Boolean)
      .join(" ")
      .toLocaleLowerCase("vi");
    return matchesStatus && (!normalizedRunQuery || searchable.includes(normalizedRunQuery));
  });
  const canControlRun = run?.requester_user_id === currentUserId;
  const canResumeRun = canControlRun && canResumeAIRun(run, checkpoints, currentUserId);
  const canShowRunControls = (busyRun && canControlRun) || canResumeRun;
  const uncertainties = latestAgentUncertainties(checkpoints);
  const runProgress = aiRunProgress(run, checkpoints);
  const sourceExtractionGaps = agentSourceExtractionGaps(run);
  const authorizationGuidance = agentAuthorizationGuidance(run);
  const showCompactEmptyState = compact && !loading && !error && visibleRuns.length === 0;
  const showRecentActivity =
    accessibleRuns.length > 0 || showCompactEmptyState || (!compact && !loading && !error && !run);
  const canStartAgent = agentCapabilities.length > 0;
  const startAIRun = async () => {
    const instruction = agentInstruction.trim();
    if (!instruction || startingAgent) return;
    setStartingAgent(true);
    setAgentStartError("");
    try {
      const requestFingerprint = JSON.stringify({
        instruction,
        targetArtifactIds,
      });
      if (agentIdempotencyFingerprint.current !== requestFingerprint) {
        agentIdempotencyKey.current = `agent-${crypto.randomUUID()}`;
        agentIdempotencyFingerprint.current = requestFingerprint;
      }
      const started = await testingApi.createAIRun({
        project_id: project._id,
        objective: instruction,
        intent: "",
        target_artifact_ids: targetArtifactIds,
        evidence: [],
        output_language: preferredSummaryLocale(user?.locale, project.locale),
        idempotency_key: agentIdempotencyKey.current,
      });
      agentIdempotencyKey.current = "";
      agentIdempotencyFingerprint.current = "";
      setAgentInstruction("");
      try {
        await refreshRuns();
      } catch (reason) {
        setRunsRefreshError(messageOf(reason));
      }
      if (started?.ai_run_id) await loadRun(started.ai_run_id);
    } catch (reason) {
      setAgentStartError(messageOf(reason));
    } finally {
      setStartingAgent(false);
    }
  };

  const recentActivityHeading = (
    <div className="flex min-w-0 items-center justify-between gap-3">
      <h3 className="text-sm font-semibold text-ink">Hoạt động gần đây</h3>
      <button
        aria-label="Tải lại hoạt động AI"
        className="icon-button inline-flex h-8 w-8 shrink-0 items-center justify-center self-center"
        disabled={loading || refreshingRuns}
        onClick={() => void refreshRunList()}
        title="Tải lại hoạt động AI"
        type="button"
      >
        <RefreshCw aria-hidden="true" className={refreshingRuns ? "animate-spin" : ""} size={16} />
      </button>
    </div>
  );

  return (
    <Panel
      title={
        !showPanelHeading ? null : compact ? (
          <span className="flex w-full flex-wrap items-center justify-between gap-3">
            <span>Hoạt động AI</span>
            <Link
              className="text-sm font-medium text-brand hover:text-brand-hover"
              href={`/du-an/${encodeURIComponent(project._id)}/ra-soat-ai`}
            >
              Xem tất cả
            </Link>
          </span>
        ) : (
          "Hoạt động AI"
        )
      }
    >
      <div className={`grid gap-3 px-4 ${compact ? "pb-3 pt-3" : "pb-4 pt-3"}`}>
        {contextContent}
        {!compact && !loading && !error && !canStartAgent && (
          <section
            className="grid gap-1 rounded-control border border-border bg-surface p-4"
            role="status"
          >
            <h3 className="font-semibold text-ink">Chưa có thao tác AI khả dụng</h3>
            <p className="text-sm text-ink-muted">
              Hiện chưa có chức năng AI phù hợp với quyền truy cập của bạn trong dự án
            </p>
          </section>
        )}
        {!compact && canStartAgent && (
          <form
            className="grid gap-3"
            onSubmit={(event) => {
              event.preventDefault();
              void startAIRun();
            }}
          >
            <label className="grid gap-2 text-sm font-medium text-ink">
              Bạn cần AI hỗ trợ việc gì?
              <textarea
                className="apple-input min-h-24"
                maxLength={4000}
                value={agentInstruction}
                onChange={(event) => setAgentInstruction(event.target.value)}
                placeholder="Mô tả kết quả cần có. AI sẽ kiểm tra căn cứ và quyền hiện tại trước khi xử lý"
              />
            </label>
            {agentStartError && <ErrorState message={agentStartError} />}
            <button
              className="primary-button justify-self-start"
              type="submit"
              disabled={startingAgent || !agentInstruction.trim()}
            >
              {startingAgent ? "Đang bắt đầu…" : "Bắt đầu xử lý bằng AI"}
            </button>
          </form>
        )}
        {error && (
          <div className="grid gap-2">
            <ErrorState message={error} />
            <button
              className="secondary-button justify-self-start"
              type="button"
              disabled={loading}
              onClick={() => setInitialLoadAttempt((attempt) => attempt + 1)}
            >
              {loading ? "Đang tải lại…" : "Tải lại dữ liệu AI"}
            </button>
          </div>
        )}
        {runsRefreshError && (
          <div className="grid gap-2" role="status">
            <ErrorState message={`Chưa cập nhật được hoạt động AI: ${runsRefreshError}`} />
            <button
              className="secondary-button justify-self-start"
              type="button"
              disabled={busy}
              onClick={() => void refreshRunList()}
            >
              Tải lại hoạt động AI
            </button>
          </div>
        )}
        {loading &&
          visibleRuns.length === 0 &&
          (compact ? (
            <div className="grid gap-2 py-1" role="status" aria-label="Đang tải hoạt động AI">
              <span className="sr-only">Đang tải hoạt động AI</span>
              {[0, 1, 2].map((item) => (
                <div aria-hidden="true" className="skeleton h-[58px] w-full" key={item} />
              ))}
            </div>
          ) : (
            <LoadingState />
          ))}
        {canShowRunControls && (
          <div className="flex flex-wrap gap-2">
            {busyRun && canControlRun && (
              <button className="secondary-button" type="button" disabled={busy} onClick={cancel}>
                Dừng tác vụ AI
              </button>
            )}
            {canResumeRun && (
              <button className="secondary-button" type="button" disabled={busy} onClick={retry}>
                {run.status === "AWAITING_AUTHORIZATION"
                  ? authorizationGuidance.action
                  : "Tiếp tục từ điểm an toàn"}
              </button>
            )}
          </div>
        )}
        <div
          className={`grid min-w-0 gap-4 ${!compact && run ? "lg:grid-cols-[minmax(15rem,0.75fr)_minmax(0,1.6fr)] lg:items-start" : ""}`}
        >
          {showRecentActivity && visibleRuns.length > 0 && (
            <div
              className={`grid min-w-0 content-start gap-3 text-sm ${!compact && run ? "lg:sticky lg:top-44" : ""}`}
            >
              {recentActivityHeading}
              {!compact && (
                <div className="grid gap-3">
                  <SearchField
                    ariaLabel="Tìm hoạt động AI"
                    onChange={(event) => setRunQuery(event.target.value)}
                    placeholder="Tìm theo nội dung hoặc trạng thái"
                    value={runQuery}
                  />
                  {availableRunStatuses.length > 1 && (
                    <div aria-label="Lọc trạng thái hoạt động AI" className="flex flex-wrap gap-2">
                      <button
                        aria-pressed={runStatusFilter === "ALL"}
                        className={`rounded-full border px-3 py-1.5 text-xs font-medium ${runStatusFilter === "ALL" ? "border-brand bg-brand/5 text-ink" : "border-border text-ink-muted hover:bg-surface-quiet"}`}
                        onClick={() => setRunStatusFilter("ALL")}
                        type="button"
                      >
                        Tất cả ({accessibleRuns.length})
                      </button>
                      {availableRunStatuses.map((status) => {
                        const count = accessibleRuns.filter(
                          (item) => item.status === status,
                        ).length;
                        return (
                          <button
                            aria-pressed={runStatusFilter === status}
                            className={`rounded-full border px-3 py-1.5 text-xs font-medium ${runStatusFilter === status ? "border-brand bg-brand/5 text-ink" : "border-border text-ink-muted hover:bg-surface-quiet"}`}
                            key={status}
                            onClick={() => setRunStatusFilter(status)}
                            type="button"
                          >
                            {valueLabel(status)} ({count})
                          </button>
                        );
                      })}
                    </div>
                  )}
                </div>
              )}
              {visibleRuns.slice(0, compact ? 3 : 10).map((item) => (
                <button
                  className={`grid grid-cols-[minmax(0,1fr)_auto] items-start gap-3 rounded-control border p-3 text-left transition ${item.ai_run_id === run?.ai_run_id ? "border-brand/50 bg-brand-soft" : "border-border hover:bg-surface-quiet"}`}
                  key={item.ai_run_id}
                  type="button"
                  onClick={async () => {
                    try {
                      await loadRun(item.ai_run_id);
                      setError("");
                      setDetailRefreshError("");
                    } catch (reason) {
                      setDetailRefreshError(messageOf(reason));
                    }
                  }}
                >
                  <span className="min-w-0">
                    <span className="block truncate font-medium text-ink">{aiRunTitle(item)}</span>
                    <span className="block truncate text-xs text-ink-muted">
                      {compact
                        ? formatDate(item.created_at, dateTimeOptions)
                        : `${agentOriginLabel(item)}${item.created_at ? ` · ${formatDate(item.created_at, dateTimeOptions)}` : ""}`}
                    </span>
                  </span>
                  <StatusPill value={item.status} />
                </button>
              ))}
            </div>
          )}
          {showRecentActivity && visibleRuns.length === 0 && (
            <div className="grid gap-2 text-sm">
              {recentActivityHeading}
              {!compact && accessibleRuns.length > 0 ? (
                <div className="grid gap-3">
                  <SearchField
                    ariaLabel="Tìm hoạt động AI"
                    onChange={(event) => setRunQuery(event.target.value)}
                    placeholder="Tìm theo nội dung hoặc trạng thái"
                    value={runQuery}
                  />
                  <p className="text-ink-muted" role="status">
                    Không có hoạt động AI khớp với bộ lọc
                  </p>
                  <button
                    className="secondary-button justify-self-start"
                    onClick={() => {
                      setRunQuery("");
                      setRunStatusFilter("ALL");
                    }}
                    type="button"
                  >
                    Xóa bộ lọc
                  </button>
                </div>
              ) : (
                <p className="text-ink-muted" role="status">
                  Chưa có hoạt động gần đây
                </p>
              )}
            </div>
          )}
          {run && (
            <div className="grid gap-4 pt-2 text-sm">
              {detailRefreshError && (
                <div className="grid gap-2" role="status">
                  <ErrorState
                    message={`Thông tin hoạt động AI có thể đã cũ; chưa tải được dữ liệu mới nhất: ${detailRefreshError}`}
                  />
                  <button
                    className="secondary-button justify-self-start"
                    type="button"
                    disabled={busy}
                    onClick={async () => {
                      try {
                        await loadRun(run.ai_run_id);
                      } catch (reason) {
                        setDetailRefreshError(messageOf(reason));
                      }
                    }}
                  >
                    Tải lại hoạt động và căn cứ
                  </button>
                </div>
              )}
              {Array.isArray(run.target_artifact_ids) && (
                <section
                  aria-label="Phạm vi của lượt AI đang xem"
                  className="grid gap-2 rounded-control border border-border bg-surface p-4"
                >
                  <h3 className="font-semibold text-ink">Phạm vi của lượt này</h3>
                  {run.target_artifact_ids.length ? (
                    <ul className="grid gap-1 text-ink-muted">
                      {run.target_artifact_ids.map((artifactId, index) => (
                        <li className="break-words" key={`${artifactId}-${index}`}>
                          {targetArtifactLabels[artifactId] ||
                            "Yêu cầu đã chọn khi bắt đầu lượt này"}
                        </li>
                      ))}
                    </ul>
                  ) : (
                    <p className="text-ink-muted">Lượt này không giới hạn vào một yêu cầu cụ thể</p>
                  )}
                </section>
              )}
              {sourceExtractionGaps.length > 0 && (
                <section
                  aria-label="Phần tài liệu nguồn chưa trích xuất đầy đủ"
                  className="grid gap-3 rounded-control border border-warning/40 bg-warning/5 p-4"
                  role="status"
                >
                  <div>
                    <h3 className="font-semibold text-ink">Tài liệu chưa được đọc đầy đủ</h3>
                    <p className="mt-1 text-ink-muted">
                      Agent đã dừng trước khi tạo hoặc cập nhật dữ liệu vì còn phần nguồn chưa trích
                      xuất được. Hãy xử lý tài liệu được nêu dưới đây rồi tải lại nguồn; hệ thống
                      không xem phần chưa đọc là nội dung đã kiểm tra
                    </p>
                  </div>
                  <ul className="grid gap-2">
                    {sourceExtractionGaps.map((gap) => (
                      <li
                        className="grid min-w-0 gap-2 rounded-control border border-border bg-surface p-3"
                        key={gap.document_id}
                      >
                        <p className="font-medium text-ink">Tài liệu cần xử lý</p>
                        <p className="text-xs text-ink-muted">
                          Trạng thái {valueLabel(gap.index_status)}
                          {gap.page_count !== null ? ` · ${gap.page_count} trang` : ""}
                          {gap.unprocessed_block_count !== null
                            ? ` · ${gap.unprocessed_block_count} phần chưa đọc`
                            : ""}
                        </p>
                        {gap.unprocessed_blocks.length > 0 && (
                          <ul className="grid gap-1">
                            {gap.unprocessed_blocks.map((block, index) => (
                              <li
                                className="break-words text-sm text-ink-muted"
                                key={`${block.block_id}-${block.page_no}-${index}`}
                              >
                                {block.page_no !== null
                                  ? `Trang ${block.page_no}`
                                  : "Vị trí chưa rõ"}
                                {block.type ? ` · ${valueLabel(block.type)}` : ""}
                                {block.reason_code === "TABLE_TEXT_NOT_EXTRACTED"
                                  ? " · Chưa trích xuất được nội dung bảng"
                                  : block.reason_code === "PICTURE_TEXT_NOT_EXTRACTED"
                                    ? " · Chưa trích xuất được nội dung hình"
                                    : " · Nội dung chưa đọc đầy đủ"}
                              </li>
                            ))}
                          </ul>
                        )}
                        {gap.unprocessed_blocks_truncated && (
                          <p className="text-xs text-warning">
                            Danh sách vị trí đã được rút gọn; tổng số phần chưa đọc vẫn được giữ
                            nguyên
                          </p>
                        )}
                      </li>
                    ))}
                  </ul>
                </section>
              )}
              {run.status === "AWAITING_INPUT" && (
                <section
                  aria-live="polite"
                  className="grid gap-3 rounded-control border border-warning/40 bg-warning/5 p-4"
                  role="status"
                >
                  <div>
                    <h3 className="font-semibold text-ink">Cần bổ sung thông tin</h3>
                    <p className="mt-1 text-ink-muted">
                      AI đã tạm dừng vì dữ liệu hiện có chưa đủ căn cứ để tiếp tục an toàn
                    </p>
                    <p className="mt-1 text-ink-muted">
                      Hãy bổ sung thông tin vào yêu cầu hoặc tài liệu nguồn liên quan. Khi nguồn
                      được cập nhật, hãy bấm bắt đầu xử lý bằng AI để tiếp tục
                    </p>
                  </div>
                  {uncertainties.length > 0 ? (
                    <ul className="grid gap-3">
                      {uncertainties.map((item, index) => (
                        <li
                          className="grid gap-1 rounded-control border border-border bg-surface p-3"
                          key={`${item.code || "uncertainty"}-${index}`}
                        >
                          {item.reason && <p className="text-ink-muted">{item.reason}</p>}
                          {item.evidence_refs?.length > 0 && (
                            <div className="text-xs text-ink-muted">
                              <p>
                                Nguồn liên quan: {item.evidence_refs.length} trích dẫn đã xác minh
                              </p>
                            </div>
                          )}
                        </li>
                      ))}
                    </ul>
                  ) : (
                    <p className="text-sm text-ink-muted">
                      Tác vụ AI chưa ghi nhận chi tiết về nguồn cần bổ sung. Hãy mở yêu cầu hoặc tài
                      liệu liên quan
                    </p>
                  )}
                </section>
              )}
              {run.error_code && run.status !== "AWAITING_INPUT" && (
                <ErrorState message={aiRunErrorMessage(run.error_code)} />
              )}
              {run.status === "AWAITING_AUTHORIZATION" && (
                <section
                  aria-live="polite"
                  className="grid gap-2 rounded-control border border-warning/40 bg-warning/5 p-4"
                  role="status"
                >
                  <h3 className="font-semibold text-ink">Cần kiểm tra quyền thực hiện</h3>
                  <p className="text-ink-muted">{authorizationGuidance.message}</p>
                </section>
              )}
              {canControlRun &&
                run.error_code === "AI_RUN_ACTION_OUTCOME_UNCERTAIN" &&
                !canResumeRun && (
                  <p className="rounded-control border border-warning/40 bg-warning/5 p-3 text-sm text-ink-muted">
                    Chưa thể tiếp tục an toàn vì hệ thống chưa xác minh được trạng thái thao tác
                    trước. Cần đối soát kết quả để tránh chạy lặp hoặc ghi trùng dữ liệu
                  </p>
                )}
              {proposal?.summary && (
                <div>
                  <div className="flex flex-wrap items-center gap-2">
                    <h3 className="font-semibold text-ink">Kết quả xử lý</h3>
                    <ContentOriginBadge origin="ai_generated" />
                  </div>
                  <p className="mt-1 whitespace-pre-wrap text-ink-muted">
                    {proposalSummaryParts(proposal.summary, citedProposalEvidenceReferences)}
                  </p>
                </div>
              )}
              {sourceExtractionWarnings.length > 0 && (
                <section
                  aria-label="Cảnh báo về quá trình trích xuất tài liệu"
                  className="grid gap-2 rounded-control border border-warning/40 bg-warning/5 p-4"
                  role="status"
                >
                  <h3 className="font-semibold text-ink">Cần đối soát tài liệu nguồn</h3>
                  <ul className="grid gap-1 text-sm text-ink-muted">
                    {sourceExtractionWarnings.map((warning, index) => (
                      <li
                        key={`${warning.document_id || "source"}-${warning.reason_code || index}`}
                      >
                        {warning.message || valueLabel(warning.reason_code || "SOURCE_WARNING")}
                      </li>
                    ))}
                  </ul>
                </section>
              )}
              {documentWorkflowStages && (
                <section
                  aria-label="Cây tiến độ AI từ tài liệu đến ca kiểm thử"
                  className="grid gap-3 rounded-control border border-border bg-surface p-4"
                >
                  <div>
                    <h3 className="font-semibold text-ink">AI từ tài liệu đến ca kiểm thử</h3>
                    <p className="mt-1 text-ink-muted">
                      Cây này ghi nhận các nội dung được tạo từ tài liệu trong lượt AI hiện tại. Mở
                      từng mục để xem và rà soát nội dung
                    </p>
                  </div>
                  <ol className="relative grid gap-0">
                    {documentWorkflowTreeStages(project._id, documentWorkflow).map(
                      (stage, index, stages) => {
                        const Icon = stage.Icon;
                        const draftIds = Array.isArray(stage.draft_ids) ? stage.draft_ids : [];
                        const blockers = [
                          ...(Array.isArray(stage.warnings) ? stage.warnings : []),
                          ...(Array.isArray(stage.source_warnings) ? stage.source_warnings : []),
                        ]
                          .filter(Boolean)
                          .slice(0, 5);
                        const unresolvedQuestions = Array.isArray(stage.unresolved_questions)
                          ? stage.unresolved_questions.filter(Boolean).slice(0, 10)
                          : [];
                        const fieldEvidence = Array.isArray(stage.field_evidence)
                          ? stage.field_evidence.slice(0, 12)
                          : [];
                        const planSuggestion =
                          stage.key === "test_plan" && stage.suggestion ? stage.suggestion : null;
                        const stageStatus =
                          documentWorkflowStatusLabels[stage.status] ||
                          (stage.status ? valueLabel(stage.status) : "Chưa có trạng thái");
                        return (
                          <li className="relative min-w-0 pb-3 pl-9 last:pb-0" key={stage.key}>
                            {index < stages.length - 1 && (
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
                            <div className="grid min-w-0 gap-1 rounded-control border border-border bg-surface-quiet/40 p-3">
                              <div className="flex min-w-0 flex-wrap items-center justify-between gap-2">
                                <span className="flex min-w-0 items-center gap-2 font-medium text-ink">
                                  {Icon && (
                                    <Icon
                                      aria-hidden="true"
                                      className="shrink-0 text-violet-700"
                                      size={16}
                                    />
                                  )}
                                  {stage.href ? (
                                    <Link className="hover:text-brand" href={stage.href}>
                                      {stage.label}
                                    </Link>
                                  ) : (
                                    stage.label
                                  )}
                                </span>
                                <span className="text-xs text-ink-muted">{stageStatus}</span>
                              </div>
                              {stage.detail && (
                                <p className="break-words text-xs text-ink-muted">{stage.detail}</p>
                              )}
                              {planSuggestion && (
                                <div className="mt-2 grid gap-2 rounded-control border border-border bg-surface p-3 text-sm">
                                  <p className="font-medium text-ink">
                                    Đề xuất Test Plan · Chưa lưu
                                  </p>
                                  {planSuggestion.objective && (
                                    <p>
                                      <span className="font-medium">Mục tiêu:</span>{" "}
                                      {planSuggestion.objective}
                                    </p>
                                  )}
                                  {[
                                    ["scope_out", "Ngoài phạm vi"],
                                    ["entry_criteria", "Điều kiện bắt đầu"],
                                    ["exit_criteria", "Tiêu chí hoàn thành"],
                                    ["test_types", "Loại kiểm thử"],
                                  ].map(([field, label]) => {
                                    const values = Array.isArray(planSuggestion[field])
                                      ? planSuggestion[field].filter(Boolean)
                                      : [];
                                    if (!values.length) return null;
                                    return (
                                      <p key={field}>
                                        <span className="font-medium">{label}:</span>{" "}
                                        {values.join("; ")}
                                      </p>
                                    );
                                  })}
                                  {planSuggestion.test_level && (
                                    <p>
                                      <span className="font-medium">Cấp kiểm thử:</span>{" "}
                                      {valueLabel(planSuggestion.test_level)}
                                    </p>
                                  )}
                                  {Array.isArray(planSuggestion.risks) &&
                                    planSuggestion.risks.length > 0 && (
                                      <div>
                                        <p className="font-medium">Rủi ro có căn cứ</p>
                                        <ul className="mt-1 grid gap-1 text-ink-muted">
                                          {planSuggestion.risks.map((risk, riskIndex) => (
                                            <li key={`${stage.key}-risk-${riskIndex}`}>
                                              <span className="font-medium text-ink">
                                                {risk.title}
                                              </span>
                                              {risk.description ? `: ${risk.description}` : ""}
                                            </li>
                                          ))}
                                        </ul>
                                      </div>
                                    )}
                                </div>
                              )}
                              {stage.evaluation?.reason && (
                                <p className="text-xs text-ink-muted">{stage.evaluation.reason}</p>
                              )}
                              {stage.reason_code && (
                                <p className="text-xs text-warning">
                                  {valueLabel(stage.reason_code)}
                                </p>
                              )}
                              {draftIds.length > 0 && (
                                <p className="break-words text-xs text-ink-muted">
                                  {draftIds.length} bản nháp được tạo trong lượt này
                                </p>
                              )}
                              {blockers.length > 0 && (
                                <ul className="grid gap-1 text-xs text-warning">
                                  {blockers.map((warning, warningIndex) => (
                                    <li key={`${stage.key}-warning-${warningIndex}`}>
                                      {valueLabel(warning)}
                                    </li>
                                  ))}
                                </ul>
                              )}
                              {unresolvedQuestions.length > 0 && (
                                <div className="grid gap-1 text-xs">
                                  <p className="font-medium text-ink">Cần làm rõ</p>
                                  <ul className="grid gap-1 text-ink-muted">
                                    {unresolvedQuestions.map((question, questionIndex) => (
                                      <li key={`${stage.key}-question-${questionIndex}`}>
                                        {question}
                                      </li>
                                    ))}
                                  </ul>
                                </div>
                              )}
                              {fieldEvidence.length > 0 && (
                                <details className="text-xs">
                                  <summary className="cursor-pointer font-medium text-ink">
                                    Căn cứ cho đề xuất Test Plan
                                  </summary>
                                  <ul className="mt-2 grid gap-2 text-ink-muted">
                                    {fieldEvidence.map((item, evidenceIndex) => (
                                      <li key={`${stage.key}-evidence-${evidenceIndex}`}>
                                        <span className="font-medium text-ink">
                                          {valueLabel(item.field)}: {item.value}
                                        </span>
                                        {(item.evidence_quotes || [])
                                          .slice(0, 2)
                                          .map((quote, quoteIndex) => (
                                            <p
                                              className="mt-1 border-l-2 border-border pl-2"
                                              key={`${stage.key}-quote-${evidenceIndex}-${quoteIndex}`}
                                            >
                                              “{String(quote.quote || "").slice(0, 500)}”
                                            </p>
                                          ))}
                                      </li>
                                    ))}
                                  </ul>
                                </details>
                              )}
                              {stage.key === "requirements" &&
                                documentWorkflow.requirement_ids?.length > 0 && (
                                  <div className="flex flex-wrap gap-x-3 gap-y-1 text-xs">
                                    {documentWorkflow.requirement_ids.map((requirementId) => (
                                      <Link
                                        className="font-medium text-brand hover:underline"
                                        href={`/du-an/${encodeURIComponent(project._id)}/yeu-cau/${encodeURIComponent(requirementId)}`}
                                        key={requirementId}
                                      >
                                        Mở Requirement
                                      </Link>
                                    ))}
                                  </div>
                                )}
                            </div>
                          </li>
                        );
                      },
                    )}
                  </ol>
                  {Array.isArray(documentWorkflow.unresolved) &&
                    documentWorkflow.unresolved.length > 0 && (
                      <p className="text-sm text-ink-muted">
                        Còn {documentWorkflow.unresolved.length} nội dung cần rà soát hoặc bổ sung
                        trước khi hoàn tất quy trình
                      </p>
                    )}
                </section>
              )}
              {proposal?.evidence_refs?.length > 0 && (
                <div>
                  <h3 className="font-semibold text-ink">Căn cứ được trích dẫn trong kết quả</h3>
                  <p className="mt-1 text-ink-muted">
                    {citedProposalEvidenceReferences.length} căn cứ được trích dẫn trong câu trả lời
                  </p>
                  {citedProposalEvidenceReferences.length > 0 ? (
                    <ul className="mt-2 grid gap-1 text-sm text-ink-muted">
                      {citedProposalEvidenceReferences.map((item) => (
                        <li
                          className="grid min-w-0 gap-1 rounded-control border border-border bg-surface p-3"
                          key={`${item.reference}-${item.number}`}
                        >
                          <div className="flex flex-wrap items-center gap-2">
                            <span className="font-medium text-ink">Nguồn {item.number}</span>
                            {item.fact ? (
                              <>
                                <span>{sourceFactSummary(item.fact)}</span>
                                {sourceFactHref(item.projectId, item.fact) && (
                                  <Link
                                    className="text-brand hover:underline"
                                    href={sourceFactHref(item.projectId, item.fact)}
                                  >
                                    Mở nguồn
                                  </Link>
                                )}
                              </>
                            ) : item.toolResult ? (
                              <span>
                                Kết quả đã kiểm tra từ{" "}
                                {agentCapabilityLabels.get(item.toolResult.tool_name) ||
                                  "công cụ AI"}
                              </span>
                            ) : (
                              <span className="text-warning">
                                Chưa tải được trích dẫn để đối chiếu
                              </span>
                            )}
                          </div>
                          {item.fact?.quote && (
                            <blockquote className="break-words whitespace-pre-wrap border-l-2 border-accent/40 pl-3 text-ink-muted">
                              {displayEvidenceQuote(item.fact.quote)}
                            </blockquote>
                          )}
                          {item.toolResult?.text && (
                            <details className="rounded-control border border-border bg-surface-quiet p-3">
                              <summary className="cursor-pointer font-medium text-ink">
                                Mở kết quả đã kiểm tra
                              </summary>
                              <pre className="mt-3 max-h-80 overflow-auto whitespace-pre-wrap break-words text-xs text-ink-muted">
                                {item.toolResult.text}
                              </pre>
                            </details>
                          )}
                        </li>
                      ))}
                    </ul>
                  ) : (
                    <p className="mt-2 text-sm text-ink-muted">
                      Câu trả lời không trích dẫn nguồn cụ thể. Có thể xem nguồn được đối chiếu
                      trong phần truy vết bên dưới
                    </p>
                  )}
                </div>
              )}
              {(checkpoints.length > 0 || receipt || unlinkedSourceFacts.length > 0) && (
                <details className="rounded-control border border-border bg-surface-quiet p-4">
                  <summary className="cursor-pointer font-semibold text-ink">
                    Xem nguồn và quá trình tạo kết quả
                  </summary>
                  <div className="mt-4 grid gap-5">
                    {checkpoints.length > 0 && (
                      <div>
                        <h3 className="font-semibold text-ink">Các bước đã thực hiện</h3>
                        <ol className="mt-2 grid gap-2">
                          {checkpoints.map((checkpoint) => {
                            const item = agentCheckpointView(checkpoint, dateTimeOptions);
                            if (!item) return null;
                            return (
                              <li
                                className="grid min-w-0 gap-2 rounded-control border border-border bg-surface p-3"
                                key={checkpoint.checkpoint_id}
                              >
                                <div className="flex flex-wrap items-center justify-between gap-2">
                                  <span className="font-medium text-ink">
                                    {item.sequence > 0 ? `${item.sequence}. ` : ""}
                                    {item.phase}
                                  </span>
                                  <StatusPill value={item.status} />
                                </div>
                                <time
                                  className="text-xs text-ink-muted"
                                  dateTime={checkpoint.created_at || undefined}
                                >
                                  {item.createdAt}
                                </time>
                                {item.facts.length > 0 && (
                                  <ul className="grid gap-1 text-xs text-ink-muted">
                                    {item.facts.map((fact) => (
                                      <li key={fact}>{fact}</li>
                                    ))}
                                  </ul>
                                )}
                              </li>
                            );
                          })}
                        </ol>
                      </div>
                    )}
                    {receipt && (
                      <div>
                        <h3 className="font-semibold text-ink">Nguồn đã dùng</h3>
                        <p className="mt-1 text-ink-muted">
                          {receipt.source_fact_ids?.length || 0} nguồn được dùng để tạo kết quả này
                        </p>
                      </div>
                    )}
                    {unlinkedSourceFacts.length > 0 && (
                      <section aria-label="Trích dẫn nguồn đã kiểm chứng" className="grid gap-2">
                        <h3 className="font-semibold text-ink">Trích dẫn nguồn đã kiểm chứng</h3>
                        <ul className="grid gap-2">
                          {unlinkedSourceFacts.map((fact) => (
                            <li
                              className="min-w-0 rounded-control border border-border bg-surface p-3"
                              key={fact.source_fact_id}
                            >
                              <p className="break-words text-xs text-ink-muted">
                                {sourceFactSummary(fact)}
                              </p>
                              <blockquote className="mt-2 break-words whitespace-pre-wrap border-l-2 border-accent/40 pl-3 text-ink">
                                {displayEvidenceQuote(fact.quote)}
                              </blockquote>
                            </li>
                          ))}
                        </ul>
                      </section>
                    )}
                  </div>
                </details>
              )}
            </div>
          )}
        </div>
      </div>
      {run && dismissedProgressRunId !== run.ai_run_id && (
        <aside
          aria-label="Tiến độ xử lý AI"
          className="fixed bottom-5 right-4 z-[80] grid w-[min(380px,calc(100vw-2rem))] gap-2 rounded-panel border border-border bg-surface p-4 shadow-[0_12px_36px_rgba(32,32,30,0.16)] sm:right-6"
        >
          <div className="flex items-center justify-between gap-3">
            <span
              className={`min-w-0 flex-1 font-semibold ${runProgress.tone === "danger" ? "text-danger" : runProgress.tone === "success" ? "text-green-700" : "text-warning"}`}
            >
              {runProgress.label} • {runProgress.percent}%
            </span>
            <button
              aria-label="Ẩn tiến độ lượt AI"
              className="icon-button -my-2 -mr-2 h-10 w-10 shrink-0"
              onClick={() => setDismissedProgressRunId(run.ai_run_id)}
              title="Ẩn tiến độ lượt AI"
              type="button"
            >
              <X aria-hidden="true" size={16} />
            </button>
          </div>
          <div
            aria-label={`Tiến độ ${runProgress.label.toLowerCase()}`}
            aria-valuemax={100}
            aria-valuemin={0}
            aria-valuenow={runProgress.percent}
            aria-valuetext={`${runProgress.label} ${runProgress.percent}%`}
            className="h-2 overflow-hidden rounded-full bg-surface-quiet"
            role="progressbar"
          >
            <div
              className={`h-full rounded-full transition-[width] duration-500 ease-out ${runProgress.tone === "danger" ? "bg-danger" : runProgress.tone === "success" ? "bg-green-600" : "bg-warning"}`}
              style={{ width: `${runProgress.percent}%` }}
            />
          </div>
        </aside>
      )}
    </Panel>
  );
}
