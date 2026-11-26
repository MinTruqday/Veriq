# UI regression report

## Scope

This checkpoint covers frontend lint/build, Docker frontend rebuild and startup, HTTP health, and a read-only browser review of the public home page. It does not claim complete functional or visual acceptance.

## Results

| Check | Result | Evidence / limitation |
|---|---|---|
| Current frontend quality run | PASS | `pnpm format:check`, `pnpm lint`, and production `pnpm build` passed on 2026-11-26. Build requires `NEXT_PUBLIC_API_URL` and `INTERNAL_API_URL`; without them Next config exits before compilation. |
| Latest Docker rebuild and health | PASS | `docker compose up -d --build --wait frontend` rebuilt after the Test Case responsive breakpoint change; Docker ran formatting, lint and production build, then reported the frontend healthy. |
| Current project list and dashboard browser review | PASS (partial) | Authenticated local app displayed the API-backed project cards and the `Thư viện` dashboard with sparse-data and empty states. Browser viewport was narrow; no project mutation was performed. |
| Test Case split view after container rebuild | PASS (visual/data) | On a project with two real cases, query-backed selection showed repository list, detail content, history tab and pagination. At the available ~1270px viewport the content stayed readable after moving secondary details and four-column metadata to the 2xl breakpoint. Create/edit/review were not submitted. |
| Test Run list and historical detail | PASS (partial) | Real completed runs showed plan, build, environment and recorded-case progress; a completed run detail displayed persisted results. Result entry, evidence, active-run transition and defect creation were not exercised. |
| Defect board empty state | PASS (partial) | On a project with no defects, the Kanban/List controls, filters and empty state rendered. No defect was created and no status transition was attempted. |
| Project documents grid/list | PASS (partial) | Docker format check, lint and production build passed. The authenticated `/tai-lieu` route rendered the card/list controls and real empty state at the available narrow viewport; the selected project's collection had no documents, so card actions were not exercised. |
| Test report summary | BLOCKED BY API RESPONSE | The selected plan's report summary returned `Không thể hoàn tất yêu cầu`; chart metrics and export could not be reviewed. No report was saved or exported. |
| Working-tree preservation | PASS | Existing uncommitted frontend, backend and documentation changes were retained. |
| Route/navigation inventory | IN PROGRESS | Reviewed `frontend/features/testing/routes.js`, `navigation.js`, App Router files and feature page inventory. Nested route behavior still needs runtime confirmation. |
| Whitespace/conflict check | PASS | `git diff --check` completed without output. |
| Frontend lint | PASS | `pnpm lint` completed successfully. |
| Frontend format check | PASS | `pnpm format:check` passed after formatting `WorkspacePrimitives.jsx`. |
| Production build | PASS | `NEXT_PUBLIC_API_URL=http://127.0.0.1:8000 INTERNAL_API_URL=http://127.0.0.1:8000 pnpm build` compiled and generated 14 static routes plus the dynamic project route. |
| Docker frontend image | PASS | `docker compose build frontend` completed; image `veriq-frontend:latest` was used to recreate the frontend service. |
| Docker runtime | PASS | `docker compose up -d --wait frontend`; frontend healthy, ports 3000 and 8000 returned HTTP 200, and startup logs reported ready. |
| Public home page | PASS | Opened the Docker-served page in browser and reviewed rendered content and screenshot. Text describes actual requirement and test workflows; no generic slogan was observed. |
| Project route access guard | PASS | Direct navigation to `/du-an` redirected to `/dang-nhap?next=%2Fdu-an`; login form rendered with email, password, password visibility, recovery link and submit control. |
| Shared page title style | PASS | `PageHeader` on `/dieu-khoan` was visually reviewed at the available ~1270×715 viewport after updating the shared style to 24px. The production build includes the update. Authenticated workspace visual review remains NOT VERIFIED. |
| Dashboard refactor build | PASS | Docker frontend build included the dashboard layout and permission-gating changes; format, lint and Next.js production build passed. |
| Dashboard browser acceptance | BLOCKED | `/du-an/[projectId]` redirects without a session. No test session was available, and the native browser surface was unavailable while the Mac was locked; no dashboard interaction or role-based render is claimed. |
| Requirements workspace batch | PASS (build/runtime) | Current compact 30/70 split and distinct detail tabs passed Docker format, lint and production build; frontend is healthy and frontend/gateway returned HTTP 200. Authenticated review remains BLOCKED. |
| Project list alignment | NOT RUN | Source comparison confirms Grid/List, filters, progress and activity. Removed duplicate project key from grid cards; authenticated visual review remains NOT RUN. |
| Standalone test run creation | PASS (build/runtime) | UI exposes existing nullable plan contract and direct case/suite selection; Docker build passed. Authenticated workflow verification is BLOCKED. |
| Test Plan / Cycle integration | PASS (build/runtime) | Plan/cycle mode tabs, collapsible cycle groups including unassigned plans, and cycle result distribution from existing summary data passed Docker build; authenticated workflow verification is BLOCKED. |
| Browser visual checks at requested sizes | PARTIAL | The available in-app browser viewport was visually reviewed. 1280, 1440, 1920 and narrow viewport matrix remains NOT VERIFIED. |
| Functional API-backed workflows | NOT VERIFIED | Requires usable development session/data; no business data was modified. |
| Permission regression | NOT VERIFIED | Static permission gates are preserved in the reviewed code, but roles were not exercised end to end. |

## Known verification gaps

- Verify project creation/invitations and dashboard metrics with permitted accounts.
- Verify requirement import/version/impact/review, case creation and version flows, plan/period/run execution, defect creation/retest, report export, document/knowledge actions, settings and platform account controls.
- Check loading, empty, error, disabled and access-denied states, keyboard focus, long Vietnamese content and responsive overflow.

## Existing issues

No new business issue is asserted from this source-only checkpoint. Any API or business behavior discovered during runtime verification should be documented separately with reproduction evidence and must not be silently changed as part of UI work.
