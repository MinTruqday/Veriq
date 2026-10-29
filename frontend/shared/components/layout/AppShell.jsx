"use client";
import Link from "next/link";
import Image from "next/image";
import { useCallback, useEffect, useMemo, useRef, useState } from "react";
import { usePathname, useRouter, useSearchParams } from "next/navigation";
import {
  Bell,
  ChevronDown,
  ChevronRight,
  Menu,
  PanelLeftClose,
  PanelLeftOpen,
  Search,
  X,
} from "lucide-react";
import { useAuth } from "@/features/authentication/contexts/AuthContext";
import { testingApi } from "@/features/testing/services/testing.service";
import { useAnnouncements } from "@/shared/contexts/AnnouncementContext";
import { PROJECTS_ROUTE, PROJECT_SECTION_SLUGS } from "@/features/testing/routes";
import {
  canOpenRoleRestrictedPath,
  canRenderProtectedRoute,
  legacyProjectRouteItems,
  projectSearchRouteItem,
} from "./navigationAccess.mjs";
import {
  availableNavigation,
  hasNavigationPermission,
  navigationGroupsFor,
  navigationItemForPath,
  projectIdFromPath,
  testCaseSubsectionItems,
} from "./navigation";

function activeNavigationGroup(groups, pathname) {
  return groups
    .filter(
      (group) =>
        group.href === pathname ||
        (group.href && pathname.startsWith(`${group.href}/`)) ||
        group.items.some((item) => pathname === item.href || pathname.startsWith(`${item.href}/`)),
    )
    .sort(
      (left, right) =>
        Math.max(right.href?.length || 0, ...right.items.map((item) => item.href.length)) -
        Math.max(left.href?.length || 0, ...left.items.map((item) => item.href.length)),
    )[0];
}

function initialNavigationGroups(groups, pathname) {
  const activeGroup = activeNavigationGroup(groups, pathname);
  return Object.fromEntries(
    groups.map((group) => [group.label, group.label !== activeGroup?.label]),
  );
}

function NavigationList({ onNavigate, projectPermissions, planningMethod, collapsed = false }) {
  const pathname = usePathname();
  const { user } = useAuth();
  const groups = useMemo(
    () =>
      availableNavigation(navigationGroupsFor(pathname, planningMethod), user, projectPermissions),
    [pathname, planningMethod, projectPermissions, user],
  );
  const [collapsedGroups, setCollapsedGroups] = useState(() =>
    initialNavigationGroups(groups, pathname),
  );
  useEffect(() => {
    const activeGroup = activeNavigationGroup(groups, pathname);
    if (!activeGroup) return;
    setCollapsedGroups((current) =>
      Object.fromEntries(
        groups.map((group) => [
          group.label,
          group.label === activeGroup.label ? false : (current[group.label] ?? true),
        ]),
      ),
    );
  }, [groups, pathname]);
  return (
    <div className={collapsed ? "flex flex-col gap-2" : "flex flex-col gap-3"}>
      {groups.map((group) => (
        <div key={group.label}>
          {!collapsed && (
            <button
              type="button"
              className="mb-1 flex min-h-8 w-full items-center justify-between gap-2 rounded-control px-3 text-left text-[12px] font-semibold text-ink-faint transition hover:bg-surface-quiet hover:text-ink-muted"
              aria-expanded={!collapsedGroups[group.label]}
              onClick={() =>
                setCollapsedGroups((current) => ({
                  ...current,
                  [group.label]: !current[group.label],
                }))
              }
            >
              <span>{group.label}</span>
              <ChevronDown
                aria-hidden="true"
                size={15}
                className={`shrink-0 transition-transform ${collapsedGroups[group.label] ? "-rotate-90" : ""}`}
              />
            </button>
          )}
          <div
            className={`space-y-1 ${!collapsed && collapsedGroups[group.label] ? "hidden" : ""}`}
          >
            {group.items.map((item) => {
              const active =
                pathname === item.href ||
                (!["dashboard", "projects"].includes(item.id) &&
                  pathname.startsWith(`${item.href}/`)) ||
                (group.defaultActiveItemId === item.id && pathname === group.href);
              return (
                <Link
                  key={item.id}
                  href={item.href}
                  onClick={onNavigate}
                  aria-current={
                    pathname === item.href ||
                    (group.defaultActiveItemId === item.id && pathname === group.href)
                      ? "page"
                      : active
                        ? "location"
                        : undefined
                  }
                  aria-label={collapsed ? item.label : undefined}
                  title={collapsed ? item.label : undefined}
                  className={`flex min-h-9 items-center rounded-control text-[14px] font-medium transition duration-150 ${
                    collapsed ? "justify-center px-2" : "gap-3 px-3"
                  } ${
                    active
                      ? "bg-brand-soft text-brand"
                      : "text-ink-muted hover:bg-surface-quiet hover:text-ink"
                  }`}
                >
                  <item.icon aria-hidden="true" size={18} strokeWidth={1.75} />
                  {!collapsed && <span>{item.label}</span>}
                </Link>
              );
            })}
          </div>
        </div>
      ))}
    </div>
  );
}
export default function AppShell({ children, requireAuth }) {
  const pathname = usePathname();
  const router = useRouter();
  const searchParams = useSearchParams();
  const routeQuery = searchParams.get("q") || "";
  const projectId = projectIdFromPath(pathname);
  const { user, isLoading, authError, refreshUser, logoutState } = useAuth();
  const { unreadCount } = useAnnouncements();
  const [mobileOpen, setMobileOpen] = useState(false);
  const [accountOpen, setAccountOpen] = useState(false);
  const [searchQuery, setSearchQuery] = useState(routeQuery);
  const [projectPermissions, setProjectPermissions] = useState(null);
  const [permissionsProjectId, setPermissionsProjectId] = useState(null);
  const [planningMethod, setPlanningMethod] = useState(null);
  const [projectContext, setProjectContext] = useState(null);
  const [projectContextError, setProjectContextError] = useState("");
  const projectContextRequest = useRef(0);
  const [sidebarCollapsed, setSidebarCollapsed] = useState(false);
  const [aiStream, setAiStream] = useState(null);
  const aiStreamDismissal = useRef(null);
  const accountRef = useRef(null);
  const mobileTriggerRef = useRef(null);
  const mobileDrawerRef = useRef(null);
  const redirectFromProject = useCallback(() => {
    router.replace(PROJECTS_ROUTE);
    window.setTimeout(() => {
      if (window.location.pathname.startsWith(`${PROJECTS_ROUTE}/`)) {
        window.location.replace(PROJECTS_ROUTE);
      }
    }, 1200);
  }, [router]);
  useEffect(() => {
    const updateAiStream = (event) => {
      const value = event.detail;
      if (!value?.id) return;
      if (aiStreamDismissal.current) window.clearTimeout(aiStreamDismissal.current);
      setAiStream(value);
      if (value.status === "complete") {
        aiStreamDismissal.current = window.setTimeout(() => setAiStream(null), 4000);
      }
    };
    window.addEventListener("veriq-ai-stream", updateAiStream);
    return () => {
      window.removeEventListener("veriq-ai-stream", updateAiStream);
      if (aiStreamDismissal.current) window.clearTimeout(aiStreamDismissal.current);
    };
  }, []);
  useEffect(() => {
    setSearchQuery(routeQuery);
  }, [routeQuery]);
  useEffect(() => {
    setMobileOpen(false);
    setAccountOpen(false);
  }, [pathname]);
  const refreshProjectContext = useCallback(
    async (id, hideUntilVerified = false) => {
      const requestId = ++projectContextRequest.current;
      setProjectContextError("");
      if (hideUntilVerified) {
        setProjectPermissions(null);
        setPermissionsProjectId(null);
      }
      try {
        const project = await testingApi.getProject(id);
        if (requestId !== projectContextRequest.current) return;
        setProjectPermissions(project?.current_permissions || []);
        setPermissionsProjectId(id);
        setPlanningMethod(project ? project.planning_method || "SCRUM" : null);
        setProjectContext(project || null);
      } catch (error) {
        if (error?.status === 403 || error?.status === 404) {
          if (requestId === projectContextRequest.current) {
            setPlanningMethod(null);
            setProjectContext(null);
            setProjectPermissions([]);
            setPermissionsProjectId(id);
          }
          redirectFromProject();
          return;
        }
        if (requestId !== projectContextRequest.current) return;
        setPlanningMethod(null);
        setProjectContext(null);
        setProjectPermissions(null);
        setPermissionsProjectId(null);
        setProjectContextError("Không thể tải quyền và thông tin dự án. Hãy thử lại.");
      }
    },
    [redirectFromProject],
  );
  useEffect(() => {
    if (!projectId || !user) {
      projectContextRequest.current += 1;
      setProjectPermissions(null);
      setPermissionsProjectId(null);
      setPlanningMethod(null);
      setProjectContext(null);
      setProjectContextError("");
      return;
    }
    setProjectPermissions(null);
    setPermissionsProjectId(null);
    setPlanningMethod(null);
    setProjectContext(null);
    void refreshProjectContext(projectId);
    return () => {
      projectContextRequest.current += 1;
    };
  }, [projectId, refreshProjectContext, user]);
  useEffect(() => {
    const refreshAfterDeniedAction = (event) => {
      if (event.detail?.projectId === projectId && user) {
        const permission = event.detail?.permission;
        if (typeof permission !== "string") {
          setProjectPermissions([]);
          setPermissionsProjectId(projectId);
          setProjectContext(null);
          redirectFromProject();
          return;
        }
        if (typeof permission === "string") {
          setProjectPermissions(
            (current) =>
              current?.filter((grantedPermission) => grantedPermission !== permission) ?? null,
          );
        }
        void refreshProjectContext(projectId, true);
      }
    };
    window.addEventListener("veriq-project-access-denied", refreshAfterDeniedAction);
    return () =>
      window.removeEventListener("veriq-project-access-denied", refreshAfterDeniedAction);
  }, [projectId, redirectFromProject, refreshProjectContext, user]);
  useEffect(() => {
    if (requireAuth && !isLoading && !user && !authError) {
      const query = searchParams.toString();
      const returnPath = `${pathname}${query ? `?${query}` : ""}`;
      router.replace(`/dang-nhap?next=${encodeURIComponent(returnPath)}`);
    }
  }, [authError, isLoading, pathname, requireAuth, router, searchParams, user]);
  useEffect(() => {
    const close = (event) => {
      if (accountRef.current && !accountRef.current.contains(event.target)) setAccountOpen(false);
    };
    const escape = (event) => {
      if (event.key === "Escape") {
        setMobileOpen(false);
        setAccountOpen(false);
      }
    };
    document.addEventListener("mousedown", close);
    document.addEventListener("keydown", escape);
    return () => {
      document.removeEventListener("mousedown", close);
      document.removeEventListener("keydown", escape);
    };
  }, []);
  useEffect(() => {
    if (!mobileOpen) return undefined;
    const previousOverflow = document.body.style.overflow;
    document.body.style.overflow = "hidden";
    const drawer = mobileDrawerRef.current;
    const trigger = mobileTriggerRef.current;
    const focusableSelector =
      'button:not([disabled]), a[href], input:not([disabled]), select:not([disabled]), textarea:not([disabled]), [tabindex]:not([tabindex="-1"])';
    const frame = requestAnimationFrame(() => {
      drawer?.querySelector('[data-mobile-nav-close="true"]')?.focus();
    });
    const trapFocus = (event) => {
      if (event.key !== "Tab" || !drawer) return;
      const focusable = Array.from(drawer.querySelectorAll(focusableSelector)).filter(
        (element) =>
          element.getClientRects().length > 0 && !element.closest('[aria-hidden="true"], [inert]'),
      );
      if (!focusable.length) {
        event.preventDefault();
        drawer.focus();
        return;
      }
      const first = focusable[0];
      const last = focusable[focusable.length - 1];
      if (event.shiftKey && document.activeElement === first) {
        event.preventDefault();
        last.focus();
      } else if (!event.shiftKey && document.activeElement === last) {
        event.preventDefault();
        first.focus();
      }
    };
    document.addEventListener("keydown", trapFocus);
    return () => {
      cancelAnimationFrame(frame);
      document.removeEventListener("keydown", trapFocus);
      document.body.style.overflow = previousOverflow;
      trigger?.focus();
    };
  }, [mobileOpen]);
  const currentProjectPermissions = permissionsProjectId === projectId ? projectPermissions : null;
  const currentPlanningMethod = permissionsProjectId === projectId ? planningMethod : null;
  const currentProjectContext = permissionsProjectId === projectId ? projectContext : null;
  const projectAccessReady =
    !projectId || (permissionsProjectId === projectId && Array.isArray(currentProjectPermissions));
  const projectRouteItem = projectId
    ? navigationItemForPath(navigationGroupsFor(pathname, currentPlanningMethod), pathname, [
        ...testCaseSubsectionItems(projectId),
        ...legacyProjectRouteItems(projectId, {
          projectTasksSlug: PROJECT_SECTION_SLUGS.projectTasks,
          testDesignSlug: PROJECT_SECTION_SLUGS.testDesign,
        }),
        projectSearchRouteItem(projectId),
      ])
    : null;
  const projectRouteDenied =
    projectAccessReady &&
    (!projectRouteItem || !hasNavigationPermission(projectRouteItem, currentProjectPermissions));
  const globalRoleAccess = projectId
    ? null
    : canOpenRoleRestrictedPath(navigationGroupsFor(pathname), pathname, user);
  const globalRouteRequiresAuth = Boolean(globalRoleAccess?.item?.requireAuth && !user);
  const globalRouteDenied = Boolean(
    !isLoading &&
      globalRoleAccess?.item &&
      !globalRoleAccess.allowed &&
      !(globalRouteRequiresAuth && authError),
  );
  const routeDenied = projectId ? projectRouteDenied : globalRouteDenied;
  useEffect(() => {
    if (!projectRouteDenied || !projectId) return;
    const destination = currentProjectPermissions?.includes("project.read")
      ? `/du-an/${projectId}`
      : "/du-an";
    if (pathname !== destination) router.replace(destination);
  }, [currentProjectPermissions, pathname, projectId, projectRouteDenied, router]);
  useEffect(() => {
    if (projectId || isLoading || !globalRouteDenied) return;
    if (globalRouteRequiresAuth) {
      const query = searchParams.toString();
      const returnPath = `${pathname}${query ? `?${query}` : ""}`;
      router.replace(`/dang-nhap?next=${encodeURIComponent(returnPath)}`);
      return;
    }
    router.replace("/du-an");
  }, [
    globalRouteDenied,
    globalRouteRequiresAuth,
    isLoading,
    pathname,
    projectId,
    router,
    searchParams,
  ]);
  if (routeDenied) {
    if (!projectId) return null;
    return (
      <main
        id="main-content"
        className="flex min-h-[100dvh] items-center justify-center bg-canvas text-ink"
        aria-busy="true"
      >
        <p className="text-sm text-ink-muted" role="status">
          Đang chuyển về khu vực có thể truy cập.
        </p>
      </main>
    );
  }
  if (
    !canRenderProtectedRoute({
      requireAuth,
      isLoading,
      user,
      projectId,
      projectAccessReady,
      routeDenied,
    })
  ) {
    if (requireAuth && !isLoading && !user && authError) {
      return (
        <main className="flex min-h-[100dvh] items-center justify-center bg-canvas px-4 py-8">
          <section
            className="w-full max-w-md rounded-panel border border-border bg-surface p-6"
            role="alert"
          >
            <h1 className="text-lg font-semibold text-ink">Chưa xác minh được phiên</h1>
            <p className="mt-2 text-sm text-ink-muted">{authError}</p>
            <button
              className="primary-button mt-4"
              type="button"
              onClick={() => void refreshUser()}
            >
              Thử xác minh lại
            </button>
          </section>
        </main>
      );
    }
    return (
      <div className="mx-auto flex min-h-[100dvh] w-full max-w-[1280px] gap-8 px-6 py-10">
        <div className="hidden w-48 space-y-3 lg:block">
          <div className="skeleton h-7 w-24" />
          <div className="skeleton mt-10 h-10 w-full" />
          <div className="skeleton h-10 w-full" />
          <div className="skeleton h-10 w-4/5" />
        </div>
        <div className="flex-1 space-y-5">
          <div className="skeleton h-9 w-52" />
          <div className="skeleton h-4 w-80 max-w-full" />
          <div className="skeleton mt-10 h-56 w-full" />
        </div>
      </div>
    );
  }
  const initials = String(user?.full_name || user?.username || "D")
    .trim()
    .charAt(0)
    .toUpperCase();
  return (
    <div className="min-h-[100dvh] bg-canvas text-ink">
      {aiStream && (
        <div
          className="fixed inset-x-4 bottom-4 z-[70] ml-auto w-auto max-w-sm rounded-control border border-border bg-surface px-4 py-3 shadow-lg sm:inset-x-auto sm:bottom-5 sm:right-5"
          aria-live="polite"
        >
          <div className="flex min-w-0 items-start justify-between gap-3">
            <div className="min-w-0">
              <p className="text-sm font-semibold text-ink">
                {aiStream.status === "complete"
                  ? "Yêu cầu AI đã hoàn tất"
                  : aiStream.status === "failed"
                    ? "Không thể hoàn tất yêu cầu AI"
                    : "AI đang xử lý yêu cầu"}
              </p>
              {aiStream.status === "failed" && aiStream.message && (
                <p className="mt-1 break-words text-xs text-ink-muted">{aiStream.message}</p>
              )}
            </div>
            <button
              type="button"
              onClick={() => setAiStream(null)}
              className="-mr-1 -mt-1 flex h-8 w-8 shrink-0 items-center justify-center rounded-control text-ink-muted hover:bg-surface-quiet hover:text-ink"
              aria-label="Đóng thông báo AI"
            >
              <X size={16} aria-hidden="true" />
            </button>
          </div>
        </div>
      )}
      <a
        href="#main-content"
        className="fixed left-3 top-3 z-[60] -translate-y-20 rounded-control bg-brand px-4 py-2 text-[14px] font-semibold text-white transition focus:translate-y-0"
      >
        Bỏ qua điều hướng
      </a>
      <header
        className={`fixed inset-x-0 top-0 z-40 h-[68px] border-b border-border bg-surface/95 backdrop-blur-md transition-[left] duration-200 ${sidebarCollapsed ? "lg:left-[76px]" : "lg:left-[260px]"}`}
      >
        <div className="flex h-full items-center gap-3 px-4 md:px-6">
          <button
            type="button"
            ref={mobileTriggerRef}
            onClick={() => setMobileOpen(true)}
            className="flex h-11 w-11 shrink-0 items-center justify-center rounded-control text-ink-muted hover:bg-surface-quiet lg:hidden"
            aria-label="Mở điều hướng"
            aria-controls="mobile-navigation"
            aria-expanded={mobileOpen}
          >
            <Menu size={20} strokeWidth={1.75} />
          </button>
          <Link
            href={projectId ? `/du-an/${projectId}` : "/du-an"}
            className="flex shrink-0 items-center gap-2 lg:hidden"
          >
            <Image
              src="/brand/veriq-logo.png"
              alt="Veriq"
              width={32}
              height={32}
              className="h-8 w-8 rounded-lg object-cover"
              priority
              unoptimized
            />
            <span className="text-[15px] font-bold tracking-[-0.02em]">Veriq</span>
          </Link>
          {projectId && (
            <div className="hidden min-w-0 items-center gap-1 text-[13px] text-ink-muted lg:flex">
              <Link href="/du-an" className="shrink-0 hover:text-ink">
                Dự án
              </Link>
              <ChevronRight size={14} aria-hidden="true" />
              <Link
                href={`/du-an/${projectId}`}
                className="max-w-44 truncate font-medium text-ink hover:text-brand"
              >
                {currentProjectContext?.name || currentProjectContext?.project_name || projectId}
              </Link>
            </div>
          )}
          {projectId && currentProjectPermissions?.includes("knowledge.read") && (
            <form
              action={`/du-an/${projectId}/tim-kiem`}
              className="relative hidden min-w-0 w-full max-w-[520px] flex-1 md:block"
            >
              <button
                type="submit"
                aria-label="Thực hiện tìm kiếm"
                className="absolute left-0 top-0 flex h-10 w-10 items-center justify-center text-ink-faint hover:text-ink"
              >
                <Search aria-hidden="true" size={18} strokeWidth={1.75} />
              </button>
              <label htmlFor="workspace-search" className="sr-only">
                Tìm trong dữ liệu dự án
              </label>
              <input
                id="workspace-search"
                name="q"
                type="search"
                value={searchQuery}
                onChange={(event) => setSearchQuery(event.target.value)}
                className="h-10 w-full rounded-control border border-transparent bg-surface-quiet pl-10 pr-3 text-[14px] text-ink outline-none transition focus:border-brand focus:bg-surface focus:ring-2 focus:ring-brand-soft"
                placeholder="Tìm trong yêu cầu, kiểm thử hoặc lỗi"
              />
            </form>
          )}
          <div className="ml-auto flex items-center gap-2">
            {user ? (
              <>
                {projectId && currentProjectPermissions?.includes("knowledge.read") && (
                  <Link
                    href={`/du-an/${projectId}/tim-kiem`}
                    className="flex h-11 w-11 items-center justify-center rounded-control text-ink-muted hover:bg-surface-quiet hover:text-ink md:hidden"
                    aria-label="Tìm kiếm"
                  >
                    <Search size={19} strokeWidth={1.75} />
                  </Link>
                )}
                <Link
                  href="/thong-bao"
                  className="relative flex h-11 w-11 items-center justify-center rounded-control text-ink-muted hover:bg-surface-quiet hover:text-ink"
                  aria-label={unreadCount ? `Thông báo, ${unreadCount} chưa đọc` : "Thông báo"}
                >
                  <Bell size={19} strokeWidth={1.75} />
                  {unreadCount > 0 && (
                    <span className="absolute right-2.5 top-2.5 h-2 w-2 rounded-full bg-danger" />
                  )}
                </Link>
                <div className="relative" ref={accountRef}>
                  <button
                    type="button"
                    onClick={() => setAccountOpen((value) => !value)}
                    className="flex h-10 items-center gap-2 rounded-control px-1.5 pr-2 text-left hover:bg-surface-quiet"
                    aria-expanded={accountOpen}
                  >
                    <span className="flex h-8 w-8 items-center justify-center overflow-hidden rounded-full bg-brand text-[13px] font-semibold text-white">
                      {user.avatar_url ? (
                        <Image
                          src={user.avatar_url}
                          alt=""
                          width={32}
                          height={32}
                          className="h-full w-full object-cover"
                          unoptimized
                        />
                      ) : (
                        initials
                      )}
                    </span>
                    <span className="hidden max-w-36 truncate text-[13px] font-semibold md:block">
                      {user.full_name || user.username}
                    </span>
                  </button>
                  {accountOpen && (
                    <div
                      id="account-menu"
                      className="absolute right-0 top-12 w-60 rounded-panel border border-border bg-surface p-2 shadow-[0_18px_50px_rgba(48,47,42,0.12)]"
                    >
                      <div className="border-b border-border px-3 py-2.5">
                        <p className="truncate text-[14px] font-semibold text-ink">
                          {user.full_name || user.username}
                        </p>
                        <p className="truncate text-[12px] text-ink-muted">{user.email}</p>
                      </div>
                      <Link
                        href="/cai-dat"
                        onClick={() => setAccountOpen(false)}
                        className="mt-1 block rounded-control px-3 py-2 text-[14px] hover:bg-surface-quiet"
                      >
                        Cài đặt
                      </Link>
                      <button
                        type="button"
                        onClick={logoutState}
                        className="block w-full rounded-control px-3 py-2 text-left text-[14px] text-danger hover:bg-danger-soft"
                      >
                        Đăng xuất
                      </button>
                    </div>
                  )}
                </div>
              </>
            ) : (
              <>
                <Link
                  href="/dang-nhap"
                  className="hidden min-h-11 items-center whitespace-nowrap rounded-control px-3 py-2 text-[14px] font-semibold text-ink hover:bg-surface-quiet min-[380px]:flex"
                >
                  Đăng nhập
                </Link>
                <Link
                  href="/dang-nhap"
                  className="flex min-h-11 items-center whitespace-nowrap rounded-control bg-brand px-4 py-2 text-[14px] font-semibold text-white hover:bg-brand-hover"
                >
                  Đăng nhập
                </Link>
              </>
            )}
          </div>
        </div>
      </header>

      <aside
        className={`fixed inset-y-0 left-0 z-40 hidden border-r border-border bg-surface transition-[width] duration-200 lg:block ${sidebarCollapsed ? "w-[76px]" : "w-[260px]"}`}
      >
        <div
          className={`flex h-[68px] items-center border-b border-border ${sidebarCollapsed ? "justify-center px-3" : "justify-between px-5"}`}
        >
          <Link
            href="/"
            className="flex min-w-0 items-center gap-3 text-[19px] font-semibold tracking-[-0.035em] text-ink"
          >
            <Image
              src="/brand/veriq-logo.png"
              alt="Veriq"
              width={36}
              height={36}
              className="h-9 w-9 rounded-xl object-cover"
              priority
              unoptimized
            />
            {!sidebarCollapsed && <span>Veriq</span>}
          </Link>
          {!sidebarCollapsed && (
            <button
              type="button"
              onClick={() => setSidebarCollapsed(true)}
              className="flex h-9 w-9 items-center justify-center rounded-control text-ink-muted hover:bg-surface-quiet hover:text-ink"
              aria-label="Thu gọn điều hướng"
            >
              <PanelLeftClose size={18} aria-hidden="true" />
            </button>
          )}
        </div>
        {sidebarCollapsed && (
          <button
            type="button"
            onClick={() => setSidebarCollapsed(false)}
            className="mx-auto mt-3 flex h-9 w-9 items-center justify-center rounded-control text-ink-muted hover:bg-surface-quiet hover:text-ink"
            aria-label="Mở rộng điều hướng"
          >
            <PanelLeftOpen size={18} aria-hidden="true" />
          </button>
        )}
        <nav
          className={`h-[calc(100dvh-68px)] overflow-y-auto ${sidebarCollapsed ? "px-2 py-4" : "px-4 py-6"}`}
          aria-label="Điều hướng chính"
        >
          <NavigationList
            projectPermissions={currentProjectPermissions}
            planningMethod={currentPlanningMethod}
            collapsed={sidebarCollapsed}
          />
        </nav>
      </aside>

      {mobileOpen && (
        <div className="fixed inset-0 z-50 lg:hidden">
          <button
            type="button"
            aria-label="Đóng điều hướng"
            className="absolute inset-0 bg-ink/30"
            onClick={() => setMobileOpen(false)}
          />
          <aside
            id="mobile-navigation"
            ref={mobileDrawerRef}
            role="dialog"
            aria-modal="true"
            aria-label="Điều hướng chính"
            tabIndex={-1}
            className="relative h-full w-[min(88vw,320px)] overflow-y-auto bg-surface p-4 shadow-[20px_0_60px_rgba(32,32,30,0.16)] outline-none"
          >
            <div className="mb-6 flex h-11 items-center justify-between">
              <Link
                href="/"
                onClick={() => setMobileOpen(false)}
                className="flex items-center gap-3 text-[19px] font-semibold tracking-[-0.035em]"
              >
                <Image
                  src="/brand/veriq-logo.png"
                  alt="Veriq"
                  width={36}
                  height={36}
                  className="h-9 w-9 rounded-xl object-cover"
                  unoptimized
                />
                Veriq
              </Link>
              <button
                type="button"
                data-mobile-nav-close="true"
                onClick={() => setMobileOpen(false)}
                className="flex h-11 w-11 items-center justify-center rounded-control hover:bg-surface-quiet"
                aria-label="Đóng điều hướng"
              >
                <X size={20} strokeWidth={1.75} />
              </button>
            </div>
            <NavigationList
              onNavigate={() => setMobileOpen(false)}
              projectPermissions={currentProjectPermissions}
              planningMethod={currentPlanningMethod}
            />
          </aside>
        </div>
      )}

      <main
        id="main-content"
        tabIndex={-1}
        className={`min-h-[100dvh] min-w-0 pt-[68px] transition-[padding] duration-200 ${sidebarCollapsed ? "lg:pl-[76px]" : "lg:pl-[260px]"}`}
      >
        <div className="page-shell">
          {projectContextError ? (
            <section
              className="mx-auto max-w-xl rounded-panel border border-border bg-surface p-6"
              role="alert"
            >
              <h1 className="text-lg font-semibold text-ink">Không thể tải quyền dự án</h1>
              <p className="mt-2 break-words text-sm text-ink-muted">{projectContextError}</p>
              <button
                className="primary-button mt-4"
                type="button"
                onClick={() => void refreshProjectContext(projectId, true)}
              >
                Thử tải lại
              </button>
            </section>
          ) : !projectAccessReady ? (
            <div aria-busy="true" aria-label="Đang kiểm tra quyền truy cập" className="space-y-5">
              <div className="skeleton h-9 w-56 max-w-full" />
              <div className="skeleton h-4 w-80 max-w-full" />
              <div className="skeleton h-56 w-full" />
            </div>
          ) : routeDenied ? null : (
            children
          )}
        </div>
      </main>
    </div>
  );
}
