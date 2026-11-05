export function defectActionAccess(project, defect) {
  const membership = project.current_membership;
  const role = membership?.project_role;
  const active =
    membership?.status === "ACTIVE" &&
    project.status?.toLowerCase() !== "archived" &&
    (!project.administrative_status || project.administrative_status === "ACTIVE");
  const owned = Boolean(membership?.user_id && defect?.assignee === membership.user_id);
  const denied = project.settings?.permission_overrides?.[role]?.deny || [];
  const can = (permission) =>
    !denied.includes(permission) && project.current_permissions?.includes(permission);
  return {
    canEditTechnical: Boolean(
      active && role === "DEVELOPER" && owned && !denied.includes("defect.update"),
    ),
    canManageTrace: Boolean(
      active &&
        !denied.includes("defect.trace.manage") &&
        (role === "DEVELOPER" ? owned : role === "QA" && can("defect.trace.manage")),
    ),
    canAssign: Boolean(active && role === "QA" && can("defect.assign")),
    canTriage: Boolean(active && role === "QA" && can("defect.triage")),
    canRepair: Boolean(
      active && role === "DEVELOPER" && owned && !denied.includes("defect.transition.developer"),
    ),
    canRetest: Boolean(
      active && role === "TESTER" && can("defect.retest") && can("testrun.execute"),
    ),
  };
}
