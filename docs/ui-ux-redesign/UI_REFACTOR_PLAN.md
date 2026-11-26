# Veriq UI/UX refactor plan

## Scope and guardrails

Refactor the active frontend routes and their related forms, panels, tabs, dialogs, and shared components. Preserve existing routes, API contracts, data, permission checks, validation, lifecycle rules, calculations, and Veriq branding. Do not treat legacy routes or backend APIs as active UI without confirming their current route/navigation use.

## Work sequence

| Phase | Cluster | Dependencies | Current state |
|---|---|---|---|
| 0 | Route, navigation, shared component and working-tree inventory | None | IN PROGRESS |
| 1 | App shell, navigation, page headers, tokens and shared controls | Phase 0 | IN PROGRESS; existing local changes present |
| 2 | Projects and project dashboard | Shared foundation | IN PROGRESS |
| 3 | Requirements, source documents, versions, impact and traceability | Shared foundation | IN PROGRESS |
| 4 | Test plans, periods and releases | Projects, cases | IN PROGRESS |
| 5 | Test analysis, cases, suites, scenarios and datasets | Requirements | IN PROGRESS |
| 6 | Test runs, execution, defects and retest | Plans, cases | IN PROGRESS |
| 7 | Reports, audit, documents and knowledge | Execution and requirements | IN PROGRESS |
| 8 | Project settings, platform operations, account, auth and notifications | Shared foundation | IN PROGRESS |
| 9 | Route-by-route responsive and regression review | Phases 1–8 | NOT VERIFIED |

## Design principles

- Reuse `frontend/app/globals.css` tokens and existing workspace primitives.
- Choose a layout based on the task: project grid/list, split view for repositories, document workspace for reading/editing, execution workspace for runs, compact table for dense administration, and grouped settings for configuration.
- Keep primary actions visible, preserve loading/empty/error/disabled states, and support keyboard focus and narrow screens.
- Use real API data only. Keep permission gates and all business logic intact.
- A module is not VERIFIED until its linked routes and meaningful actions have been exercised; source changes or a successful build alone are not visual or functional verification.

## Current constraints

The working tree contains pre-existing uncommitted frontend and backend changes. Treat them as user work and preserve them. The current task only changes frontend presentation and UI documentation. Runtime visual evidence and authenticated end-to-end checks remain outstanding unless a usable session is available.
