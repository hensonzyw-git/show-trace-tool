# Handoff — Show Radar

Start here after `AGENTS.md`.

## Read First

1. `CLAUDE.md`
2. `PROJECT_STATE.md`
3. `PRD-演出雷达.md`
4. `docs/DECISIONS.md`
5. Current `git status -sb` and diff

## Before Editing

- Reconcile the request with the current PRD and actual code.
- If a design handoff conflicts with implemented capability, prefer the PRD and real product boundary.
- Keep changes narrow; do not invent endpoints, tabs, or unsupported UI.

## Verification

- Backend: `./venv/bin/pytest`
- iOS: backend tests are not enough. Use an Xcode/iOS build when Swift changes are made, or state clearly if the user will build manually.

## Closeout

When the user asks to wrap up:

1. Update `PROJECT_STATE.md`.
2. Record new decisions in `docs/DECISIONS.md`.
3. Record milestones in `docs/PROJECT_LOG.md`.
4. Commit and push if requested.
5. Deploy/update server only when the request includes that scope.
