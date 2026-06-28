# Project State — Show Radar

Last updated: 2026-06-28

## Current Status

Show Radar is a single-user live-event discovery product. The backend collects and normalizes events, scores them against the user's preferences, freezes daily summaries, and serves a SwiftUI iOS app.

The product is intentionally a discovery layer. Event purchase and detail completion remain on source platforms.

## Source Of Truth

- Agent working agreement: `CLAUDE.md`
- Codex entrypoint: `AGENTS.md`
- Product/build spec: `PRD-演出雷达.md`
- Architecture: `ARCHITECTURE.md`
- Deployment: `DEPLOYMENT.md`
- Long-term decisions: `docs/DECISIONS.md`
- Milestone log: `docs/PROJECT_LOG.md`
- Next-agent handoff: `docs/HANDOFF.md`

## Current Product Boundaries

- Backend is the single source of truth.
- iOS has exactly four tabs: 当日摘要 / 全部演出 / 偏好管理 / 设置.
- No fake UI for unsupported features.
- No detail-page scraping; cards link back to source platforms.
- No push-notification UI unless a real backend exists.
- Hard sources such as 大麦 use assisted local capture plus import API, not the cloud main path.

## Next-Step Protocol

Before any code changes:

1. Read `AGENTS.md`, `CLAUDE.md`, and `PRD-演出雷达.md`.
2. Check `git status -sb` and current diff.
3. If backend behavior is involved, verify code paths and tests before documenting TODOs.
4. If iOS behavior is involved, remember backend tests do not validate Swift.

## Validation State

No tests were run for this context-sync update; this is documentation-only.
