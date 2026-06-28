# CLAUDE.md — Show Radar working agreement

Project memory for Claude Code / Codex when working in this repo. Both the CLI agents and the
`loop/` review loop read this. Keep it short and current.

## What this is

A single-user personal live-event radar: backend collects events from ticketing platforms, an LLM
(DeepSeek) normalizes them into structured records, scores them by taste, and a SwiftUI iOS app shows
the day's worth-a-look events. It's a **discovery layer** — purchases happen back on the source
platforms. Daily batch, single-user, not a commercial scraper.

Deeper context: `README.md`, `ARCHITECTURE.md`, `PRD-演出雷达.md`, `DEPLOYMENT.md`.

## Product boundaries (NON-NEGOTIABLE — treat violations as blockers)

- **Backend is the single source of truth.** The app does not infer business logic.
- **No detail-page scraping.** Cards link back to the platform; missing fields stay `null`.
- **No push notifications** → never add notification toggles or other UI without a real backend behind it.
- **iOS is exactly 4 tabs**: 当日摘要 / 全部演出 / 偏好管理 / 设置. Do not invent tabs, screens, or features.
- **Don't fix a bug by deleting the feature.** Fix the cause; preserve existing behavior unless the task explicitly says to remove it.
- **Collection may be unstable; everything downstream must not.** Extract / store / summarize / client stay stable.
- **Hard sources (大麦)** go through assisted-local capture + import API — never the cloud main path.

## Conventions

- Backend: Python · FastAPI · SQLite. LLM: DeepSeek (`deepseek-chat`).
- Event dedup id: `sha256("type|artist-or-title|date|venue")[:16]`.
- iOS: SwiftUI; real-device build/verification is manual by design.
- Make the smallest change that satisfies the task; don't touch unrelated files.

## Checks (must stay green)

- Backend: `./venv/bin/pytest`
- iOS changes: a green backend test means nothing for Swift — build with
  `xcodebuild -scheme ShowTrace -destination 'platform=iOS Simulator,name=iPhone 15' build test`.

## Automated review loop

`loop/` runs Codex-implements → gates → Claude-review → Codex-arbitrate. Match the gate to the change
(set `BUILD_CMD` for iOS tasks). See `loop/README.md`.

## Working style (Henson)

- Be concise and direct; minimal preamble.
- For non-trivial product / technical / strategic decisions, reason from first principles: break the
  problem to fundamentals, separate known vs assumed, then build up. Skip this for simple factual asks.
- If a task lacks the context to reason from first principles, ask one focused question and surface
  assumptions explicitly rather than guessing silently.
- Web search: prefer English sources by default; use Chinese for China A-share topics.
- Generated docs default to Markdown unless asked otherwise.
