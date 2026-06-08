# Handoff: 演出雷达 (Show Radar) — iOS App UI · 方向 B（卡片）

## Overview
**演出雷达 / Show Radar** is a personal "show-tracking" iOS app. It aggregates live-performance
listings (concerts, classical/music, theatre, sports, Livehouse) from multiple Chinese ticketing
platforms (大麦 Damai, 秀动 Showstart, 摩天轮 Motianlun), scores each event against the user's
interest profile (keep / maybe / filter + a 0–100 match score), and surfaces a daily digest so the
user never misses an on-sale.

The single most important product idea: **one place that aggregates shows across multiple
platforms**, ranked by the user's taste.

This UI is the **frontend** for an existing Python backend (FastAPI). The data shapes below mirror
that backend's API (`/api/events`, `/api/digests/today`, `/api/subscriptions`, `/api/preferences`,
`/api/runs`) so the app can be wired to it directly.

## About the Design Files
The files in this bundle are **design references created in HTML/React+Babel** — prototypes that
show the intended look and behavior. They are **not production code to copy directly**.

Your task is to **recreate these designs in the target codebase's environment**. This is an iOS app,
so the natural target is **SwiftUI** (or UIKit). If you are instead building a cross-platform / web
client, use that stack's idioms. Either way: reproduce the layout, tokens, and component specs below
pixel-faithfully using the platform's native primitives — do not embed the HTML.

The prototype is rendered inside a simulated iPhone bezel (402×874 logical px, Dynamic Island, home
indicator). In a real app these are provided by the device + safe-area insets — drop the bezel and
respect `safeAreaInsets` instead of the hardcoded `paddingTop: 60` / `paddingBottom: 22` used here.

## Fidelity
**High-fidelity (hifi).** Final colors, typography, spacing, and component states are specified.
Recreate the UI pixel-faithfully. Two complete themes are provided — **Light** and **Dark** — and the
app must support switching between them (the user explicitly requested a light/dark toggle).

The only placeholders are **event poster images**: they are drawn as diagonally-striped blocks tinted
by category, labelled `主视觉 / poster` in monospace. In production, load the real event artwork
(the backend stores a `purchase_url`; poster scraping/import is a backend concern). Until artwork
exists, keep the striped placeholder as the graceful fallback.

---

## Design Tokens

### Fonts
- **UI**: system font — iOS: SF Pro (`-apple-system, "SF Pro Text", system-ui`). On web use the system
  stack; do **not** substitute Inter/Roboto.
- **Mono** (placeholder captions, error logs): `ui-monospace, "SF Mono", Menlo, monospace`.

### Color — Light theme (`card-light`)
| Token | Value | Use |
|---|---|---|
| `accent` | `#E0533D` | primary coral — CTAs, active tab, highlights |
| `accentText` | `#FFFFFF` | text/icon on accent |
| `bg` | `#F4F1EE` | screen background (warm off-white) |
| `bg2` | `#EDE8E3` | deeper background |
| `card` | `#FFFFFF` | card / surface |
| `card2` | `#F4F1EC` | inset field / chip surface |
| `text` | `#1C1715` | primary text |
| `text2` | `rgba(28,23,21,0.56)` | secondary text |
| `text3` | `rgba(28,23,21,0.34)` | tertiary text / icons |
| `sep` | `rgba(28,23,21,0.07)` | hairline separators |
| `hair` | `rgba(28,23,21,0.08)` | dashed "add" borders |
| `barBg` | `rgba(255,255,255,0.82)` | tab bar / sticky bar (over 20px blur) |
| `tabIdle` | `rgba(28,23,21,0.4)` | inactive tab |
| `shadow` | `0 1px 3px rgba(60,40,30,0.06), 0 8px 24px rgba(60,40,30,0.05)` | card elevation |

### Color — Dark theme (`card-dark`)
| Token | Value |
|---|---|
| `accent` | `#FF6F57` (brighter coral) |
| `accentText` | `#1A0E0B` |
| `bg` | `#0C0B0A` |
| `bg2` | `#161412` |
| `card` | `#1A1816` |
| `card2` | `#231F1C` |
| `text` | `#F5F1EE` |
| `text2` | `rgba(245,241,238,0.62)` |
| `text3` | `rgba(245,241,238,0.36)` |
| `sep` | `rgba(255,255,255,0.08)` |
| `hair` | `rgba(255,255,255,0.10)` |
| `barBg` | `rgba(18,16,14,0.82)` |
| `tabIdle` | `rgba(245,241,238,0.42)` |
| `shadow` | `0 1px 2px rgba(0,0,0,0.4)` |
| card border (dark only) | `0.5px solid sep` (cards get a hairline border instead of shadow) |

### Interest-decision colors (the keep/maybe/filter badge)
| Decision | Label (zh) | Light fg / bg | Dark fg / bg |
|---|---|---|---|
| `keep` | 关注 | `#C0432F` / `rgba(224,83,61,0.10)` | `#FF8A72` / `rgba(255,111,87,0.16)` |
| `maybe` | 待定 | `#9A6B17` / `rgba(201,136,46,0.12)` | `#E8C06B` / `rgba(232,192,107,0.14)` |
| `filter` | 已过滤 | `rgba(28,23,21,0.4)` / `rgba(28,23,21,0.05)` | `rgba(245,241,238,0.4)` / `rgba(255,255,255,0.06)` |

### Source-tag dot colors (per platform)
`大麦 #E0533D` · `秀动 #2F6DF0` · `摩天轮 #16997A`

### Run-status colors
`success #16997A` · `partial_success #C9882E` · `failed #D14343`

### Poster placeholder hue (oklch chroma ~0.06, by category)
演唱会 `12°` · 音乐会 `268°` · Livehouse `320°` · 话剧 `32°` · 体育 `152°` · 亲子 `200°` · 展览 `92°`
(Light: `oklch(90% .06 H)`→`oklch(82% .07 H)` 18px diagonal stripes; Dark: `22%`→`16%`.)

### Radius
- Cards / surfaces: **18px**
- Pills / chips / toggles: **999px** (full)
- Poster thumbnails: 10–12px; CTA buttons: 14px
- Inset search/text field: 11–12px

### Spacing
- Screen horizontal padding: **20px**
- Header top padding (status-bar safe): **60px** → replace with safe-area top inset
- Content bottom padding (clears tab bar): **92px**; tab bar pad: top 9 / bottom 22 → use safe-area bottom inset
- Card internal padding: **12px**; gap between stacked cards: **11px**
- Section label block: `padding: 20px 20px 9px`
- Inter-chip gap: 8px

### Typography scale (size / weight / tracking)
| Role | px | weight | tracking / line |
|---|---|---|---|
| Large title (screen header) | 32 | 760 | -0.6 / 1.05 |
| Header kicker (date, accent) | 13 | 650 | +0.3 |
| Section label | 19 | 740 | -0.3 |
| Detail title (h1) | 25 | 800 | -0.4 / 1.18 |
| Card title (2-line clamp) | 15 | 670 | -0.2 / 1.25 |
| Top-pick card title (2-line) | 14.5 | 700 | -0.2 |
| Body / meta rows | 14 | 400–600 | — |
| Price (card / detail) | 14 / 17 | 700 / 800 | — |
| Score badge | 11.5 (big 13) | 650 | -0.2 |
| Source tag | 11.5 | 600 | — |
| Tab label | 10.5 | 510 idle / 650 active | — |
| Summary big number | 38 | 800 | -1 |

---

## Screens / Views

There are **6 screens** under a 5-item bottom tab bar: **当日摘要 (Today digest)** · **全部演出 (All)** ·
**订阅范围 (Subscription scope)** · **偏好管理 (Preferences)** · **设置 (Settings)**. The **演出详情 (Detail)**
screen is pushed on top of 当日摘要 / 全部演出 (not a tab), and **采集记录 (Collection log / Runs)** is a
pushed sub-screen reached from **设置 › 采集记录** (not a tab).

### Bottom Tab Bar (global)
- 5 equal-width items, each = 25px icon over a 10px label (nowrap), vertical stack, 3px gap.
- Active item uses `accent` for both icon + label (weight 650); idle uses `tabIdle` (weight 510).
- Bar background `barBg` with `backdrop-filter: blur(20px) saturate(180%)`, top hairline `0.5px sep`.
- Tabs (label / icon): 当日摘要=calendar w/ dot · 全部演出=list · 订阅范围=star outline ·
  偏好管理=sliders · 设置=gear.

### 1. 今日 (Today / Feed)
- **Purpose**: the daily digest — what's new today, what starts soonest, what matches the user's taste.
- **Layout** (vertical scroll):
  1. **Header**: kicker = date `2026.06.05 周五` (accent); large title `今日雷达`; trailing bell icon
     with an accent notification dot (8px, bordered with `bg`).
  2. **Summary banner**: full-width card (radius 18), gradient bg
     (light `linear-gradient(135deg,#FBE9E4,#FFFFFF)`, dark `linear-gradient(135deg,#2A1411,#1A1816)`).
     Big accent number `8` (38px/800) + `条新演出`, sub-line `其中 8 条按你的口味值得关注 · 来自 大麦 / 秀动`.
  3. **⚡ 最近就开始** section label, then a **horizontal scroller** of "top pick" cards (width 210,
     poster height 112 flush to card top; body: category (accent 11px) + score badge row, 2-line title,
     date row with calendar icon).
  4. **为你关注** section label with `全部 ›` accent link, then a vertical stack of **EventCards** (the
     `keep`-decision events).
- **Content**: real data — picks sorted by soonest date (板式网球 06.10, Summer Shape 06.11, 欧阳娜娜 06.13);
  "为你关注" = 周杰伦, 欧阳娜娜, 郎朗, 朱蟒三重奏音乐会, etc.

### 2. 全部 (All Events)
- **Purpose**: browse/filter the full event list.
- **Layout**:
  1. Header large title `全部演出` + an inset **search field** (38px, radius 11, magnifier + placeholder
     `搜索演出、艺人、场馆`).
  2. **Category filter row** (horizontal pills): `全部`(active, accent fill) `演唱会` `音乐会` `话剧` `体育` `Livehouse`.
  3. **Taste filter row**: label `口味` + pills `关注`(active) `待定` `已过滤`; right-aligned count `16 场 · 按日期`.
  4. Vertical stack of **EventCards**.

### 3. 演出详情 (Event Detail) — pushed screen
- **Purpose**: full detail + purchase CTA + why-it-was-ranked.
- **Layout**:
  1. **Hero**: poster placeholder (height 252) with a bottom scrim gradient fading into `bg`; a centered
     monospace `主视觉 / poster` hint at y≈112. Two floating round 38px glass nav buttons (back chevron,
     bell) at top. Title block pinned to hero bottom: category pill (accent fill) + status pill (`售票中`),
     then h1 title (25/800), then artist (15/600 text2).
  2. **Radar score card**: bg = decision color `bg`; left = 42px circle filled with decision `fg`
     showing the match score (`96`); right = `雷达评分 · 关注` (decision fg) + `不确定度 low · 分类 演唱会`;
     below = the reason sentence (`命中订阅艺人「周杰伦」+ 关注品类 演唱会`).
  3. **Facts card**: 4 rows (icon + label + right-aligned value), separated by hairlines:
     日期 / 场馆(city · venue) / 票价 / 开票.
  4. **Discovered-via** line: `在 [大麦●] 搜「周杰伦」· 全国 发现`.
  5. **Sticky bottom bar** (`barBg` + blur, top hairline): left = `票价` label + value; right = full
     accent CTA button (50px, radius 14) `[ticket] 去大麦购票`. (System-style variant folds price into
     the button: `去大麦购票 · ¥380 – 2580`.)
- **Content**: defaults to event[0] = 周杰伦嘉年华世界巡回演唱会 2026 上海站.

### 4. 订阅 (Subscriptions)
- **Purpose**: manage who/what is tracked and which platforms are on.
- **Layout**:
  1. Header `我的订阅` + trailing `＋` add button (round card or accent glyph).
  2. **关注的艺人** section: wrap of artist chips (24px circle avatar = first char on accent, + name) +
     a dashed `＋ 添加` chip. Artists: 周杰伦, 欧阳娜娜, 郎朗, 陈佩斯.
  3. **本地 · 上海** section: a card explaining `在 上海 追踪这些关键词的演出`, then keyword pills
     (`演唱会` `音乐会` `体育赛事` `话剧`, accent-tinted) + dashed `＋ 关键词`.
  4. **数据源** section: list card, one row per source = colored dot + name + note + **toggle**.
     大麦 (on, `需 Chrome + 登录态`), 秀动 (on, `Livehouse / 巡演`), 摩天轮 (off, `二手 / 转票`).
     Toggle: 50×30 pill, accent when on, 26px white knob.

### 5. 偏好 (Preferences)
- **Purpose**: tune the recommendation taste profile.
- **Layout**:
  1. Header `兴趣偏好`.
  2. **大白话调教推荐** card (gradient like the Today banner): bolt icon + heading, an inset example
     input bubble `"多推点爵士现场，别再给我亲子类了"`, right-aligned accent `更新偏好` button.
     (This maps to `POST /api/preferences/feedback` — free-text → profile merge.)
  3. **想看的品类** section: keep-colored chips with a check glyph (`演唱会` `音乐会` `体育比赛`).
  4. **不想看的品类** section: filter-colored chips, strikethrough (`亲子`).
  5. **排序偏好 & 信号**: a numbered list card (`未来三个月优先`, `票价 ≤ 1000 优先`), then signal chips —
     positive `＋ 爵士现场` `＋ 周杰伦` (keep color), negative `－ 商场快闪活动` (muted).

### 6. 设置 (Settings)
- **Purpose**: app-level configuration + the entry point to backend transparency (采集记录).
- **Layout**:
  1. Header `设置`.
  2. **Account card**: 46px accent avatar (`沪`) + `上海 · 我的雷达` + sub `4 位关注艺人 · 2 个数据源开启`, chevron.
  3. **外观** section: single row `主题` with an inline **segmented control** (`跟随系统` / `浅色` / `深色`);
     selected segment reflects the active theme.
  4. **通知** section: rows with toggles — `开票提醒` (on, `即将开票的演出提前推送`), `每日摘要推送`
     (on, `每天 09:00 · 仅「关注」级`), `价格变动提醒` (off, `关注的演出降价时通知`).
  5. **数据采集** section: `采集记录` row (accent icon, sub = last-run time, right = status dot+label
     `成功` + chevron → pushes the Runs screen), `采集频率` (`每日 2 次`, chevron), `管理数据源`
     (`大麦 / 秀动 已开启 · 摩天轮 关闭`, chevron → 订阅范围).
  6. **关于** section: `给个反馈`, `隐私与数据`, `版本 1.0.3 (42)`.
- Settings rows: icon (19px, text3 — accent only for 采集记录) + title (15.5/600) + optional sub (12/text2)
  + right accessory; hairline separators inset 46px (with icon) / 15px (without).

### 6b. 采集记录 (Collection Log / Runs) — pushed from 设置
- **Purpose**: transparency into the daily scraper — what ran, what it found, what failed.
- **Layout**:
  1. Header `采集记录` (keeps the 设置 tab active).
  2. **Stat strip**: 3 cards — `今日新增 8` (accent), `本周采集 253`, `已通知 14`.
  3. **运行历史** list of run cards. Each: status dot + `date time` + status pill (`成功`/`部分成功`/`失败`)
     + right-aligned uppercase trigger (`CRON` / `API` / `LOCAL-SYNC`). Stat row: 抓取/抽取/新增/通知
     (新增 highlighted accent when >0). Failed/partial runs show a mono error line in a red-tinted box.

---

## Interactions & Behavior
The prototype is static, but the intended behavior:
- **Tab bar**: switches between the 5 top-level screens; preserve scroll position per tab.
- **EventCard / row tap** → push **演出详情** for that event.
- **Detail back button** → pop. **去大麦购票** → open `purchase_url` (in-app Safari / `SFSafariViewController`).
- **Bell (Today header / Detail)** → set/clear an **on-sale reminder** for events with a future `on_sale_time`.
- **Filter pills (全部)**: tapping toggles a single active category + a single active taste filter; list
  re-queries (`GET /api/events?type=…&interest_decision=…`).
- **Search field** → search screen (out of scope for this handoff; not designed).
- **Subscription toggles / chips**: editing pushes `PUT /api/subscriptions`. Adding artist/keyword via
  the dashed chips.
- **Settings**: 主题 segmented sets the theme override; 采集记录 row → push Runs screen; 管理数据源 → 订阅范围;
  notification toggles persist locally / to the backend.
- **更新偏好** → `POST /api/preferences/feedback` with the typed text; on success, re-score visible events
  and refresh decision badges.
- **Theme**: support Light + Dark; follow the system appearance by default with a manual override.
- **Transitions**: standard iOS push/pop for detail; subtle fade/slide-up for cards is acceptable. Respect
  reduced-motion. No infinite/decorative animation.

## State Management
- `theme`: `'light' | 'dark'` (default = system).
- `activeTab`: one of `当日摘要 / 全部演出 / 订阅范围 / 偏好管理 / 设置`.
- `events`: list from `GET /api/events` (filterable). Each carries an embedded `score`.
- `filters`: `{ category, decision, city, type, date_from, date_to }`.
- `digest`: `GET /api/digests/today` (today's new count + top picks).
- `subscription`: `GET/PUT /api/subscriptions`.
- `profile`: `GET /api/preferences`; mutated via `POST /api/preferences/feedback`.
- `runs`: `GET /api/runs`.
- `reminders`: per-event on-sale reminder set (local notifications).

## Data Model (matches the backend)
Event fields used by the UI:
`id, type('concert'|'exhibition'|'activity'), cat(display category), title, artist?, city, venue,
date(display string), dateSort(ISO), onSale(display), status('售票中'|'即将开票'|'待定'…), price(display),
source('大麦'|'秀动'|'摩天轮'), via(discovered-via short text), url(purchase_url)`, plus
`score: { decision('keep'|'maybe'|'filter'), match(0–100), cat, reason, uncertainty('low'|'medium'|'high') }`.
See `data.js` for a fully-populated, real example set (16 Shanghai events + profile + subscription + runs).

## Assets
- **No bitmap assets.** All icons are inline geometric SVGs (1.8px stroke) — see `ICONS` in `radar-ui.jsx`;
  reimplement with SF Symbols on iOS (calendar, list.bullet, star, slider.horizontal.3, chart.line.uptrend,
  mappin, ticket, bell, magnifyingglass, chevron.right, checkmark, plus, clock, bolt.fill, gearshape).
- **Event posters** are placeholders (striped, category-tinted) — replace with real artwork when available.

## Files (in this bundle)
| File | Role |
|---|---|
| `演出雷达 · 方向B.html` | **The chosen design** — Direction B, every screen paired Light + Dark. Open this. |
| `data.js` | Real event/profile/subscription/run data + the exact data shapes. |
| `radar-ui.jsx` | **Design system**: `radarTheme()` token sets, icon set, ScoreBadge, SourceTag, Poster, TabBar, headers. Read this first for tokens. |
| `screens-card.jsx` | The 6 Direction-B screens (themed by the token object). |
| `app-b.jsx` | Mounts the 6 screens in Light+Dark pairs on the review canvas. |
| `ios-frame.jsx` | Simulated iPhone bezel/status bar — **scaffold only, do not port**. |
| `design-canvas.jsx` | Review canvas wrapper — **scaffold only, do not port**. |
| `演出雷达.html` | (Reference only) the earlier 3-direction exploration incl. the iOS-native list variant (A) and dark (C). |

> Start at `radar-ui.jsx` (tokens + atoms) and `screens-card.jsx` (composition). The two `*-frame` /
> `canvas` files are presentation scaffolding from the design tool and should not be reproduced in the app.
