"use client";
import Link from "next/link";
import AnchoredActionMenu from "./AnchoredActionMenu";
import { StatusPill } from "./WorkspacePrimitives";
import { PROJECT_SECTION_SLUGS, projectRoute } from "../routes";

export default function TestPlanCatalog({
  items,
  project,
  members,
  validation,
  progress = {},
  findingLabels,
  can,
  onOpen,
  onAction,
  formatDate,
}) {
  if (!items.length) {
    return (
      <div className="px-5 py-16 text-center text-sm text-ink-muted">
        Chưa có kế hoạch phù hợp với bộ lọc
      </div>
    );
  }

  return (
    <ol className="divide-y divide-border">
      {items.map((item, index) => {
        const identifier = item.plan_key || item.key || item.code || item._id;
        const owner = members.find((member) => member.user_id === item.owner_id);
        const liveProgress = progress[item._id];
        const hasProgress = Object.hasOwn(progress, item._id);
        const caseScope = item.approved_snapshot || item;
        const caseCount = Array.isArray(caseScope.test_case_version_ids)
          ? caseScope.test_case_version_ids.length
          : null;
        const dates = [item.schedule?.planned_start_at, item.schedule?.planned_end_at]
          .filter(Boolean)
          .map((date) => formatDate(date));
        const canApprove =
          item.status === "IN_REVIEW" &&
          (project.can_self_approve ||
            (item.created_by !== project.current_membership?.user_id &&
              !(item.content_author_ids || []).includes(project.current_membership?.user_id))) &&
          can("testplan.approve");
        const canReview =
          item.status === "IN_REVIEW" &&
          (project.can_self_approve ||
            (item.created_by !== project.current_membership?.user_id &&
              !(item.content_author_ids || []).includes(project.current_membership?.user_id)));
        const hasActions =
          (["DRAFT", "READY"].includes(item.status) && can("testplan.update")) ||
          can("testplan.read") ||
          (["DRAFT", "READY"].includes(item.status) && can("testplan.submit_review")) ||
          canApprove ||
          (item.status === "IN_REVIEW" && can("testplan.review")) ||
          can("testplan.create") ||
          (item.status !== "ARCHIVED" && can("testplan.archive"));
        const finding =
          validation?.planId === item._id && validation?.revision === item.revision
            ? validation
            : null;

        return (
          <li
            key={item._id}
            className="grid gap-4 px-5 py-5 lg:grid-cols-[4rem_minmax(0,1fr)_16rem_auto] lg:items-center"
          >
            <div className="hidden h-12 w-12 items-center justify-center rounded-full bg-surface-quiet font-mono text-xs text-ink-muted lg:flex">
              {String(index + 1).padStart(2, "0")}
            </div>
            <div className="min-w-0">
              <div className="flex flex-wrap items-center gap-x-3 gap-y-1">
                <span className="font-mono text-xs text-ink-muted">{identifier}</span>
                {item.status === "READY" ? (
                  <span className="text-xs text-ink-muted">Đã lưu, chưa duyệt</span>
                ) : (
                  <StatusPill value={item.status} />
                )}
              </div>
              <button
                className="mt-1 block max-w-full truncate text-left text-base font-semibold text-ink hover:text-brand"
                type="button"
                title={item.name || ""}
                onClick={() => onOpen(item._id)}
              >
                {item.name || "Kế hoạch chưa có tên"}
              </button>
              {finding && (
                <p
                  className={`mt-2 text-xs ${finding.ready_for_approval ? "text-success" : "text-warning"}`}
                  role="status"
                >
                  {finding.ready_for_approval
                    ? "Đủ điều kiện phê duyệt"
                    : finding.findings
                        .map(
                          (entry) => findingLabels[entry.code] || "Cần bổ sung thông tin kế hoạch",
                        )
                        .join(" · ")}
                </p>
              )}
              {item.status === "APPROVED" && can("testrun.read") && (
                <div className="mt-3 max-w-sm" aria-label={`Tiến độ ${item.name}`}>
                  <div className="flex items-center justify-between gap-3 text-xs">
                    <span className="text-ink-muted">Tiến độ</span>
                    <span className="font-medium text-ink">
                      {!hasProgress
                        ? "Đang tải"
                        : !liveProgress
                          ? "Không tải được"
                          : liveProgress.result_recorded_percent == null
                            ? "Chưa có kết quả"
                            : `${liveProgress.result_recorded}/${liveProgress.total} · ${liveProgress.result_recorded_percent}%`}
                    </span>
                  </div>
                  {liveProgress?.result_recorded_percent != null && (
                    <div
                      className="mt-1.5 h-1.5 overflow-hidden rounded-full bg-surface-quiet"
                      role="progressbar"
                      aria-label={`Ca đã có kết quả trong ${item.name}`}
                      aria-valuemin={0}
                      aria-valuemax={100}
                      aria-valuenow={liveProgress.result_recorded_percent}
                    >
                      <div
                        className="h-full rounded-full bg-brand"
                        style={{ width: `${Math.min(100, liveProgress.result_recorded_percent)}%` }}
                      />
                    </div>
                  )}
                </div>
              )}
            </div>
            <div className="grid grid-cols-2 gap-x-5 gap-y-2 text-sm lg:block lg:space-y-2">
              <div>
                <span className="block text-xs text-ink-muted">Chu kỳ</span>
                {item.test_period_snapshot?._id ? (
                  <Link
                    className="font-medium text-brand hover:underline"
                    href={projectRoute(
                      project._id,
                      PROJECT_SECTION_SLUGS.testPeriods,
                      item.test_period_snapshot._id,
                    )}
                  >
                    {item.test_period_snapshot.name || "Mở chu kỳ"}
                  </Link>
                ) : (
                  <span className="font-medium">-</span>
                )}
              </div>
              <div>
                <span className="block text-xs text-ink-muted">Thời gian dự kiến</span>
                <span className="font-medium">{dates.length ? dates.join(" – ") : "-"}</span>
              </div>
              <div>
                <span className="block text-xs text-ink-muted">Phụ trách kế hoạch</span>
                <span className="font-medium">
                  {owner?.user_label || owner?.user?.full_name || "Chưa phân công"}
                </span>
              </div>
              <div>
                <span className="block text-xs text-ink-muted">Ca kiểm thử trong phạm vi</span>
                <span className="font-medium">{caseCount ?? "-"}</span>
              </div>
            </div>
            <div className="flex items-center justify-end gap-2">
              <button className="secondary-button" type="button" onClick={() => onOpen(item._id)}>
                Mở kế hoạch
              </button>
              {hasActions && (
                <AnchoredActionMenu
                  label={`Thao tác kế hoạch ${item.name}`}
                  className="icon-button flex h-10 w-10 items-center justify-center"
                >
                  {["DRAFT", "READY"].includes(item.status) && can("testplan.update") && (
                    <button
                      className="w-full rounded-control px-3 py-2 text-left text-sm hover:bg-surface-quiet"
                      type="button"
                      onClick={() => onAction(item, "edit")}
                    >
                      Sửa kế hoạch
                    </button>
                  )}
                  {can("testplan.read") && (
                    <button
                      className="w-full rounded-control px-3 py-2 text-left text-sm hover:bg-surface-quiet"
                      type="button"
                      onClick={() => onAction(item, "validate")}
                    >
                      Kiểm tra kế hoạch
                    </button>
                  )}
                  {["DRAFT", "READY"].includes(item.status) && can("testplan.submit_review") && (
                    <button
                      className="w-full rounded-control px-3 py-2 text-left text-sm hover:bg-surface-quiet"
                      type="button"
                      onClick={() => onAction(item, "submit")}
                    >
                      {project.can_self_approve ? "Chốt kế hoạch" : "Gửi rà soát"}
                    </button>
                  )}
                  {canApprove && (
                    <button
                      className="w-full rounded-control px-3 py-2 text-left text-sm hover:bg-surface-quiet"
                      type="button"
                      onClick={() => onAction(item, "approve")}
                    >
                      Phê duyệt kế hoạch
                    </button>
                  )}
                  {canReview && can("testplan.review") && (
                    <button
                      className="w-full rounded-control px-3 py-2 text-left text-sm hover:bg-surface-quiet"
                      type="button"
                      onClick={() => onAction(item, "revise")}
                    >
                      Yêu cầu chỉnh sửa
                    </button>
                  )}
                  {can("testplan.create") && (
                    <button
                      className="w-full rounded-control px-3 py-2 text-left text-sm hover:bg-surface-quiet"
                      type="button"
                      onClick={() => onAction(item, "duplicate")}
                    >
                      Nhân bản kế hoạch
                    </button>
                  )}
                  {item.status !== "ARCHIVED" && can("testplan.archive") && (
                    <button
                      className="w-full rounded-control px-3 py-2 text-left text-sm text-danger hover:bg-danger-soft"
                      type="button"
                      onClick={() => onAction(item, "archive")}
                    >
                      Lưu trữ kế hoạch
                    </button>
                  )}
                </AnchoredActionMenu>
              )}
            </div>
          </li>
        );
      })}
    </ol>
  );
}
