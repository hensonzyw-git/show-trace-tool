# AGENTS.md — Codex working agreement (Show Radar)

Read `CLAUDE.md` for the full project agreement, then `PROJECT_STATE.md` for the current
cross-machine handoff. This file mirrors the non-negotiables so Codex sees them too.

## Non-negotiables

- Backend is the single source of truth; the app does not infer business logic.
- No detail-page scraping; no push-notification UI; iOS is exactly 4 tabs (当日摘要 / 全部演出 / 偏好管理 / 设置).
- **Do not fix a bug by deleting the feature.** Fix the cause; preserve existing behavior unless the task explicitly asks to remove it.
- Make the smallest change that satisfies the task; don't touch unrelated files; don't invent UI / endpoints.

## Checks

- Backend: `./venv/bin/pytest` (keep green).
- iOS changes need a real build: `xcodebuild -scheme ShowTrace -destination 'platform=iOS Simulator,name=iPhone 15' build test` — backend tests don't cover Swift.

Full context: `CLAUDE.md`, `PROJECT_STATE.md`, `README.md`, `ARCHITECTURE.md`,
`PRD-演出雷达.md`, `docs/DECISIONS.md`, `docs/HANDOFF.md`.

## Closeout

When wrapping up work, update `PROJECT_STATE.md`; record durable choices in
`docs/DECISIONS.md`; record milestones in `docs/PROJECT_LOG.md`; and keep
`docs/HANDOFF.md` accurate for the next machine/agent.
