export function hasNavigationPermission(item, permissions) {
  if (!item) return false;
  const granted = Array.isArray(permissions) ? permissions : [];
  return (
    (!item.permission || granted.includes(item.permission)) &&
    (Array.isArray(item.permissions) ? item.permissions : []).every((permission) =>
      granted.includes(permission),
    ) &&
    (!Array.isArray(item.anyPermission) ||
      item.anyPermission.some((permission) => granted.includes(permission)))
  );
}

export function hasNavigationRole(item, user) {
  return (
    (!item?.requireAdmin || user?.system_role === "ADMIN") && (!item?.requireAuth || Boolean(user))
  );
}

export function canSeeNavigationItem(item, user, permissions) {
  return hasNavigationRole(item, user) && hasNavigationPermission(item, permissions);
}

export function navigationItemForPath(groups, pathname, additionalItems = []) {
  const groupRoutes = groups
    .filter((group) => group.href)
    .map((group) => {
      const defaultItem = group.items.find((item) => item.id === group.defaultActiveItemId);
      return defaultItem ? { ...defaultItem, href: group.href } : null;
    })
    .filter(Boolean);
  const item =
    [...groups.flatMap((group) => group.items), ...groupRoutes, ...additionalItems]
      .filter(
        (candidate) =>
          candidate.href &&
          (pathname === candidate.href || pathname.startsWith(`${candidate.href}/`)),
      )
      .sort((left, right) => right.href.length - left.href.length)[0] || null;

  if (item?.id === "project" && pathname !== item.href) return null;
  return item;
}

export function canOpenNavigationPath(groups, pathname, permissions, additionalItems = []) {
  const item = navigationItemForPath(groups, pathname, additionalItems);
  return { item, allowed: item ? hasNavigationPermission(item, permissions) : false };
}

export function canOpenRoleRestrictedPath(groups, pathname, user) {
  const item = navigationItemForPath(groups, pathname);
  return { item, allowed: item ? hasNavigationRole(item, user) : false };
}

export function projectSearchRouteItem(projectId) {
  if (!projectId) return null;
  return {
    id: "project-search",
    href: `/du-an/${encodeURIComponent(projectId)}/tim-kiem`,
    permission: "knowledge.read",
  };
}

export function legacyProjectRouteItems(projectId, { projectTasksSlug, testDesignSlug } = {}) {
  if (!projectId || !projectTasksSlug || !testDesignSlug) return [];
  const root = `/du-an/${encodeURIComponent(projectId)}`;
  return [
    {
      id: "legacy-project-tasks",
      href: `${root}/${projectTasksSlug}`,
      permission: "project.read",
    },
    {
      id: "legacy-test-design",
      href: `${root}/${testDesignSlug}`,
      permission: "testcase.read",
    },
  ];
}

export function canRenderProtectedRoute({
  requireAuth,
  isLoading,
  user,
  projectId,
  projectAccessReady,
  routeDenied,
}) {
  if (requireAuth && (isLoading || !user)) return false;
  if (projectId && !projectAccessReady) return false;
  if (routeDenied) return false;
  return true;
}
