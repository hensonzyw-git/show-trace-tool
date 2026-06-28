# Decisions — Show Radar

This is the durable decision record for cross-machine continuation. Keep this concise and link to `PRD-演出雷达.md` or `CLAUDE.md` for full context.

## D1 — Discovery Layer, Not Purchase Or Detail Completion

Show Radar helps the user discover events worth attention. Purchase, full detail completion, and anti-bot-heavy detail scraping stay on original platforms.

## D2 — Backend Is The Source Of Truth

The iOS app should not infer business logic that belongs in backend scoring, filtering, subscription, or summary semantics.

## D3 — Daily Summaries Must Be Frozen Snapshots

Daily summary output should persist the event payload as-of summary time instead of rereading mutable event rows later. This preserves the meaning of "today's summary" after rescoring or data changes.

## D4 — Product Surface Is Four Real Tabs

The supported iOS tabs are 当日摘要 / 全部演出 / 偏好管理 / 设置. Do not preserve mockup-only tabs, fake screens, or unsupported Settings controls.

## D5 — No Fake Notification Surface

Do not add push notification toggles or notification UI unless backend and delivery behavior actually exist.

## D6 — Hard Sources Use Assisted Local Capture

Sources with strong anti-bot behavior, especially 大麦, should use assisted-local capture/RPA plus import API rather than the cloud main crawler path.

## D7 — Do Not Fix Bugs By Deleting Features

Preserve existing intended behavior unless the user explicitly asks to remove it. Fix the cause.
