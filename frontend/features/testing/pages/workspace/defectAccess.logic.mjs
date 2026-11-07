export function defectActionAccess(project, defect) {
  const membership = project.current_membership;
  const active =
    membership?.status === "ACTIVE" &&
    project.status?.toLowerCase() !== "archived" &&
    (!project.administrative_status || project.administrative_status === "ACTIVE");
  const owned = Boolean(membership?.user_id && defect?.assignee === membership.user_id);
  const can = (permission) => project.current_permissions?.includes(permission);
  return {
    canEditTechnical: Boolean(active && owned && can("defect.update")),
    canManageTrace: Boolean(
      active && can("defect.trace.manage") && (owned || can("defect.triage")),
    ),
    canAssign: Boolean(active && can("defect.assign")),
    canTriage: Boolean(active && can("defect.triage")),
    canRepair: Boolean(active && owned && can("defect.transition.developer")),
    canRetest: Boolean(active && can("defect.retest") && can("testrun.execute")),
  };
}
