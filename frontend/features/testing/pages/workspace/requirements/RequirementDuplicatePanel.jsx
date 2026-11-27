import { Panel } from "../../../components/WorkspacePrimitives";
import { valueLabel } from "../../../lib/testing";

export default function RequirementDuplicatePanel({ result }) {
  if (!result) return null;
  const candidates = result.candidates || [];

  return (
    <Panel
      title="Ứng viên yêu cầu trùng lặp"
      actions={
        <span className="text-[12px] text-ink-muted">
          {result.candidate_count ?? candidates.length} cặp cần đối chiếu
        </span>
      }
    >
      {candidates.length ? (
        <ol className="divide-y divide-border">
          {candidates.map((item, index) => {
            const score = Number(item.score);
            const scorePercent = Number.isFinite(score)
              ? Math.max(0, Math.min(100, Math.round(score * 100)))
              : null;
            const reasons = Array.isArray(item.reasons) ? item.reasons.filter(Boolean) : [];
            return (
              <li
                className="grid min-w-0 gap-3 p-4 sm:p-5"
                key={`${item.left_requirement_id}-${item.right_requirement_id}-${index}`}
              >
                <div className="grid min-w-0 gap-3 md:grid-cols-2">
                  <div className="min-w-0 rounded-control border border-border bg-surface-quiet/50 p-3">
                    <p className="text-[11px] font-semibold uppercase tracking-wide text-ink-muted">
                      Yêu cầu thứ nhất
                    </p>
                    <p className="mt-1 break-words text-sm font-medium text-ink">
                      {item.left_requirement_label || item.left_requirement_id || "Yêu cầu"}
                    </p>
                  </div>
                  <div className="min-w-0 rounded-control border border-border bg-surface-quiet/50 p-3">
                    <p className="text-[11px] font-semibold uppercase tracking-wide text-ink-muted">
                      Yêu cầu thứ hai
                    </p>
                    <p className="mt-1 break-words text-sm font-medium text-ink">
                      {item.right_requirement_label || item.right_requirement_id || "Yêu cầu"}
                    </p>
                  </div>
                </div>
                <div className="grid gap-3 sm:grid-cols-[minmax(0,1fr)_auto] sm:items-center">
                  <div className="min-w-0">
                    <div className="flex flex-wrap items-center gap-2">
                      <span className="rounded-full border border-border bg-surface px-2.5 py-1 text-xs font-medium text-ink">
                        {valueLabel(item.match_type)}
                      </span>
                      {scorePercent !== null && (
                        <span className="text-sm font-semibold tabular-nums text-ink">
                          {scorePercent}% khớp
                        </span>
                      )}
                    </div>
                    {scorePercent !== null && (
                      <div
                        aria-label={`Mức độ khớp ${scorePercent}%`}
                        aria-valuemax={100}
                        aria-valuemin={0}
                        aria-valuenow={scorePercent}
                        className="mt-2 h-1.5 overflow-hidden rounded-full bg-surface-quiet"
                        role="progressbar"
                      >
                        <div
                          className="h-full rounded-full bg-brand"
                          style={{ width: `${scorePercent}%` }}
                        />
                      </div>
                    )}
                  </div>
                  {reasons.length > 0 && (
                    <ul className="flex min-w-0 flex-wrap gap-1.5 text-xs text-ink-muted">
                      {reasons.map((reason) => (
                        <li
                          className="max-w-full break-words rounded-control border border-border px-2 py-1"
                          key={reason}
                        >
                          {reason}
                        </li>
                      ))}
                    </ul>
                  )}
                </div>
              </li>
            );
          })}
        </ol>
      ) : (
        <p className="p-5 text-sm text-ink-muted">
          Không phát hiện cặp yêu cầu vượt ngưỡng trùng lặp.
        </p>
      )}
    </Panel>
  );
}
