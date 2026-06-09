# 演出雷达 (Show Radar) — 产品需求文档 (PRD)

| 项 | 内容 |
|---|---|
| 产品名 | 演出雷达 / Show Radar（应用显示名 "Show Trace"） |
| 平台 | iOS（SwiftUI，部署目标 iOS 17.0） |
| 文档版本 | v1.0 |
| 文档定位 | 完整构建规格，供**设计 AI** 与 **coding AI** 直接对接 |
| 后端 | 已有 FastAPI 只读/触发服务（本文档第 7 节给出完整 API 契约） |
| 视觉基线 | 沿用现有设计系统（第 5 节 design tokens），`design_handoff_show_radar/` 为参考稿 |

> 阅读顺序建议：设计 AI 重点看第 4、5、6 节；coding AI 重点看第 5、6、7、8 节。第 9 节是所有人都要先扫一遍的全局约束。

---

## 1. 产品概述

### 1.1 一句话定位

一个**个人专属**的演出情报雷达：后台持续从多个票务平台抓取演出/展览/活动，用 LLM 按"我的兴趣"打分和分类，App 只负责把**当前最值得关注、且还没过期**的演出清晰地呈现给我，并让我用自然语言持续校准它的口味。

### 1.2 背景与问题

演出信息散落在大麦、秀动、摩天轮等多个平台，靠人工刷很容易错过开票或漏掉感兴趣的演出。后端已经解决了"抓取 + 抽取 + 打分"，但缺一个**信息消费端**：把累积的全量素材，按我的兴趣浓缩成每天看一眼就够的清单。

### 1.3 目标用户

单一用户（产品所有者本人）。这是个人工具，**不做多用户、不做账号体系**。所有"我的偏好/订阅"都是全局单例。

### 1.4 核心使用场景

1. **每天早上扫一眼**：打开 App → 当日摘要，看今天后端为我筛出的高分演出，有想买的直接点进购票页。
2. **主动找演出**：去全部演出，搜索/按分类筛，浏览所有未过期演出。
3. **校准口味**：发现推荐不准 → 偏好管理，用一句话告诉它"多推荐 livehouse""不想看亲子剧"，或直接增删关注艺人/城市/数据源。
4. **运维自查**：去设置看采集是否正常跑、配置服务器连接。

### 1.5 设计原则

- **消费优先**：App 是只读消费端 + 偏好校准端，不做内容创作、不做详情页。
- **零废操作**：界面上每一个看起来能点的元素都必须有真实反馈；没有后端支撑的功能不放假按钮（这是硬性要求，见第 9.6 节）。
- **当前有效**：默认只展示"未过期"的演出，过期信息自动隐藏。
- **后端是事实源**：分类、兴趣分、决策都由后端给出，App 不自行推断业务逻辑，只做展示与轻量本地筛选。

---

## 2. 范围

### 2.1 本期范围（4 个 Tab）

| Tab | 名称 | 一句话 |
|---|---|---|
| 1 | 当日摘要 | 今日筛出的高分、未过期演出 feed |
| 2 | 全部演出 | 所有未过期演出 + 搜索 + 筛选 |
| 3 | 偏好管理 | 自然语言调偏好 + 管理艺人/城市/数据源 |
| 4 | 设置 | 外观 / 采集记录 / 连接 / 版本 |

### 2.2 相对当前实现的变更

- **5 Tab → 4 Tab**：现有「订阅范围」与「偏好管理」两个 Tab **合并为一个「偏好管理」**。
- 移除旧的独立「摘要(Digest)」Tab；摘要能力并入「当日摘要」。
- 「当日摘要」由"keep 列表 + digest 计数"的临时实现，改为后端**每日结构化快照 feed**（已实现，见 6.1 / 7.2）。

### 2.3 不在范围内（Out of Scope）

- 多用户 / 登录 / 云账号
- 演出详情页（点卡片直接跳第三方购票网页）
- 头图 / 真实海报图（用分类 icon 代替）
- 推送通知（本期不做；不放任何"通知开关"假 UI）
- 评论、收藏夹、日历集成、分享
- 后端抓取/打分逻辑的修改（属于后端项目，本 PRD 只消费其产物）

---

## 3. 信息架构与导航

- 底部 `TabView`，4 个 Tab，常驻。
- 默认选中 **当日摘要**。
- 各 Tab 内部用 `NavigationStack`；二级页面（如采集记录详情）用 push，模态选择类用 sheet。
- 全局应用外观模式（跟随系统/浅/深），见 6.4.1。

```
TabBar
├─ 当日摘要   (calendar.badge.clock)
├─ 全部演出   (list.bullet)
├─ 偏好管理   (slider.horizontal.3)
└─ 设置       (gearshape)
```

---

## 4. 核心数据模型与枚举

> 字段名以**后端 JSON（snake_case）**为准；括号内为 iOS 模型驼峰名。所有列表接口返回 `{ items, total, limit, offset }` 包裹。

### 4.1 ShowEvent（演出）

| JSON 字段 | 类型 | 说明 |
|---|---|---|
| `id` | string | 主键 |
| `type` | enum | `concert` / `exhibition` / `activity`（原始类型，粗粒度） |
| `title` | string | 演出名称 |
| `artist` | string? | 演出人/艺人 |
| `city` | string? | 城市 |
| `venue` | string? | 场馆 |
| `event_date` | string? | 演出日期（字符串，可能为空=日期待定） |
| `on_sale_time` | string? | 开票时间 |
| `price_info` | string? | 价格信息（已是展示文案，如"180-1280元"） |
| `purchase_url` | string? | **购票链接（卡片点击跳转目标）** |
| `source` | string? | 平台 slug：`damai` / `showstart` / `motianlun` |
| `source_url` | string? | 来源页 |
| `raw_ref` | string? | 原始引用 |
| `discovered_via` | string? | 发现途径 |
| `status` | string? | 事件状态（如 `rumored`/已确认等，后端维护） |
| `interest_decision` | enum? | **`keep` / `maybe` / `filter`**（LLM 决策） |
| `interest_match_score` | int? | **兴趣分**（LLM 打分，越高越推荐） |
| `interest_category` | string? | **细分类目**（见 4.4，展示与筛选用这个） |
| `interest_reason` | string? | 入选理由（LLM 生成） |
| `interest_uncertainty` | string? | 不确定性说明 |
| `interest_scored_at` | string? | 打分时间 |

### 4.2 Digest / 当日摘要快照（`GET /api/digests/today`）

| 字段 | 类型 | 说明 |
|---|---|---|
| `date` | string | 快照日期 |
| `generated_at` | string? | 快照生成时间 |
| `events` | ShowEvent[] | **结构化演出列表，按兴趣分降序**（App feed 直接渲染） |
| `event_count` | int? | 演出数（= `events` 长度） |
| `markdown` | string? | 旧版摘要正文（存在时附带，用于"查看完整摘要"） |
| `path` | string? | 文件路径（内部） |

### 4.3 Subscription（订阅配置，全局单例）

```json
{
  "artists": ["五月天", "周杰伦"],
  "local": { "city": "上海", "keywords": ["livehouse", "脱口秀"] },
  "sources": { "damai": {"enabled": true}, "showstart": {"enabled": true}, "motianlun": {"enabled": false} }
}
```

> **城市字段（Q4 决策）**：`subscription.local.city` 与 `profile.city` 在 App 层视为**同一个城市**，只呈现/编辑一处。`subscription.local.city` 为唯一可写来源，后端在保存订阅时同步 `profile.city`。

### 4.4 PreferenceProfile（兴趣画像，全局单例）

```json
{
  "city": "上海",
  "include_categories": ["演唱会", "音乐会"],
  "exclude_categories": ["亲子"],
  "ranking_preferences": ["优先 livehouse", "票价 500 以内优先"],
  "positive_signals": ["独立音乐", "爵士"],
  "negative_signals": ["大型晚会"]
}
```

### 4.5 RunItem（采集运行记录）

| 字段 | 类型 | 说明 |
|---|---|---|
| `id` | int | 运行 id |
| `trigger` | string | 触发方式（`api`/`cli`/`cron`…） |
| `fixture` | bool | 是否 fixture 测试运行 |
| `notify` | bool | 是否触发通知 |
| `started_at` | string | 开始时间（服务器本地时间，无时区，见 9.5） |
| `finished_at` | string? | 结束时间，运行中为 null |
| `status` | enum | `success` / `partial_success` / `failed` / `running` / `skipped` |
| `total_raw_captures` | int | 抓取条数 |
| `total_extracted_events` | int | 抽取条数 |
| `new_events` | int | 新增条数 |
| `notified_events` | int | 通知条数 |
| `error_summary` | string? | 错误摘要 |

### 4.6 受控枚举（前后端必须一致的单一事实源）

- **细分类目 `interest_category`**（卡片展示 + 筛选用）：
  `体育比赛`、`演唱会`、`音乐会`、`话剧`、`展览`、`曲艺杂谈`、`亲子`、`儿童剧`、`其他`；当评分缺失时按 `type` 兜底（concert→演唱会 / exhibition→展览 / activity→活动）。
- **兴趣决策 `interest_decision`**：`keep`(关注) / `maybe`(待观察) / `filter`(已过滤)。
- **原始类型 `type`**：`concert` / `exhibition` / `activity`。
- **平台 `source`**：`damai`(大麦) / `showstart`(秀动) / `motianlun`(摩天轮)。
- **运行状态 `status`**：见 4.5。

---

## 5. 设计系统（Design Tokens）

> 沿用现有 `SharedViews.swift` 的 token，设计 AI 在此基线上细化，**不要新造一套颜色变量**。颜色支持浅/深双色。

### 5.1 颜色

| Token | 浅色 | 深色 | 用途 |
|---|---|---|---|
| `showRadarAccent` | `#E0533D`（橙红 rgb 224,83,61） | 同 | 主强调色：选中态、分数、关键数字、品牌 |
| `showRadarScreenBackground` | `#F4F1EE`（rgb 244,241,238） | `#0C0B0A`（rgb 12,11,10） | 页面底色 |
| `showRadarCardBackground` | `#FFFFFF` | `#1A1816`（rgb 26,24,22） | 卡片/控件底色 |

> 设计注意：深色下 `screenBackground` 与 `cardBackground` 对比偏弱，设计 AI 应确保卡片在深色下有足够分层（描边/阴影/微提亮）。

### 5.2 卡片样式（统一规范）

- 圆角 `18`
- 描边 `Color.primary.opacity(0.06)`，线宽 `0.5`
- 阴影 `black.opacity(0.05)`，半径 `16`，y 偏移 `8`
- 内边距约 `12–16`

### 5.3 分类 Icon（SF Symbols，无头图，每类一个）

| 类目 | SF Symbol |
|---|---|
| 演唱会 | `music.mic` |
| 音乐会 | `music.note` |
| 话剧 / 儿童剧 | `theatermasks.fill` |
| 展览 | `photo.fill` |
| 体育比赛 | `sportscourt.fill` |
| 亲子 | `person.2.fill` |
| 曲艺杂谈 | `mic.fill` |
| 其他/兜底 | `ticket.fill` |

> 每个分类同时有一套渐变占位（`EventCategory.posterColors`），用于卡片左侧色块，体现类目区分。

### 5.4 平台标签与配色

| 平台 | 标签 | 圆点色 |
|---|---|---|
| damai | 大麦 | accent |
| showstart | 秀动 | blue |
| motianlun | 摩天轮 | teal |
| 其他/空 | 原值或"未知" | secondary |

### 5.5 状态色

- 运行状态：`success`→绿，`partial_success`/`running`/`skipped`→橙，`failed`→红。
- 兴趣决策徽章：`keep`→accent（带 star.fill），`filter`→secondary，`maybe`→橙。

---

## 6. 逐屏规格

> 每屏统一三态要求：**加载态**（首次拉取显示 ProgressView）、**空态**（无数据的友好文案）、**错误态**（可重试）。各屏的"数据来源"列出对应 API（详见第 7 节）。

### 6.1 Tab 1 · 当日摘要

**目的**：每天打开看一眼即可——后端从全量未过期素材中，按兴趣分挑出的当日高分清单。每日刷新；当日尚未生成时，展示前一日快照。**不保留历史摘要**（每天都是从全量重新筛，旧快照无保留价值）。

**数据来源**：
- 摘要元信息（日期 / 计数）：`GET /api/digests/today`（无当日则后端回退前一日；都没有则 404，按空态处理，**不可白屏**）。
- feed 卡片列表：见下方"后端依赖"。

**布局（自上而下）**：
1. **头部**：日期（如 `2026.06.10 周三`）+ 大标题"今日雷达"。
2. **概览条**：大数字 = 本次 feed 的演出数；副标题给出"今日新增 N 条 / 来源分布"等事实（措辞不得暗示无依据的包含关系）。点击概览条可查看完整摘要正文（Markdown，sheet 呈现）。
3. **Feed 列表**：演出卡片（见 6.4 卡片规范），按兴趣分降序、其次按日期升序。

**卡片字段**（本屏与"全部演出"完全一致）：分类（+icon/色块）、名称、日期、价格、平台、城市、演出人、兴趣决策徽章 + 兴趣分。**无头图。**

**交互**：
- 点击卡片 → 直接用 `purchase_url` 打开系统浏览器/SFSafariViewController 跳转购票页；**无详情页**。`purchase_url` 为空时，点击无跳转（卡片不可点或弱化）。
- 下拉刷新重新拉取。

**空/错误态**：
- 无 feed：空态"今日还没有筛选结果"。
- 摘要 404：按空态处理，feed 仍可独立展示（摘要缺失不致整屏报错）。
- 网络错误：错误态 + 重试。

**实现方式（已决策 Q1 = 快照，后端已实现）**：
当日摘要是**每日一次的冻结快照，不实时更新**；当日未生成前展示前一日快照；不保留更早的历史。
- `GET /api/digests/today` **已返回结构化 `events: ShowEvent[]`**（按兴趣分降序）+ `event_count` + `generated_at`，App 直接渲染这个列表，**不要再实时重排或用 `/api/events?interest_decision=keep` 顶替**。
- 快照由后端在每次采集运行结束时重建（`summary_YYYY-MM-DD.json`），当日缺失则返回最近一份（前一日）。都没有时返回 `404`，App 按空态处理（不可白屏）。
> coding AI：feed 直接接 `response.events`；排序已由后端固定，客户端只渲染。

### 6.2 Tab 2 · 全部演出

**目的**：浏览**所有未过期**演出，支持搜索与筛选。

**数据来源**：`GET /api/events?date_from=<今天>`（服务端已滤掉过期；类目/搜索仍在客户端做，故拉取较大窗口，如 `limit=200`）。

**"未过期"定义（已决策 Q3 = 服务端过滤）**：`event_date` 存在且 `< 今天` 视为过期；`event_date` 为空视为"待定"、保留。**由服务端过滤下发**——App 请求时带 `date_from=<今天>`，后端只返回未过期 + 待定的演出，客户端不再做日期过滤。

**布局（自上而下）**：
1. **头部**：大标题"全部演出" + 搜索框（真实 `TextField`，带清除按钮）。
2. **分类筛选**：横向 chip，取值来自受控类目（见 4.6）；`全部` 表示不筛。`体育`→匹配"体育比赛"，`曲艺`→匹配"曲艺杂谈"。
3. **是否过滤筛选**：按兴趣决策分段——`关注(keep)` / `待观察(maybe)` / `已过滤(filter)`。
4. **计数行**：当前筛选后的条数（如 "32 场 · 按日期"）。
5. **列表**：与当日摘要同款卡片。

**搜索逻辑**：对 `title / artist / venue / city` 做不区分大小写包含匹配（客户端）。

**交互**：卡片点击同 6.1（跳购票页）；下拉刷新。

**筛选与展示一致性（硬性）**：卡片显示的"分类"与"是否过滤"必须与筛选所用字段**同源**——即都基于 `interest_category`（缺失时按 `type` 兜底的同一套逻辑）与 `interest_decision`，不得出现"卡片显示 X 类但 X 筛选筛不到它"。

**空/错误态**：
- 搜索无结果："没有匹配「<词>」的演出"。
- 分类无结果："「<类目>」下暂无<决策>演出"。
- 网络错误：错误态 + 重试。

### 6.3 Tab 3 · 偏好管理（订阅 + 偏好二合一）

**目的**：用两种方式校准雷达——**自然语言**整体调教，**结构化字段**精确增删。

**数据来源（读）**：
- `GET /api/preferences` → PreferenceProfile（类目/信号/倾向）。
- `GET /api/subscriptions` → Subscription（艺人/城市/数据源）。

**数据来源（写）**：
- 自然语言：`POST /api/preferences/feedback`。
- 结构化：`PUT /api/subscriptions`（艺人、城市、数据源开关）。
- 类目/信号/倾向（profile 字段）：**已决策 Q2 = 只读展示 + 自然语言修改**，本期不提供结构化直接增删，也不需要后端新增 profile 写接口。

**布局（自上而下）**：
1. **自然语言输入框**（核心）：多行输入 + 发送。占位示例："多推荐 livehouse、不想看大型晚会"。发送后调用 feedback 接口，返回 `updates`（本次新增的 include/exclude/positive/negative）→ 就地高亮反馈"已更新：+独立音乐 / −亲子"，并刷新下方画像。可选 `rescore_existing` 触发存量重打分（返回 `rescored_events` 条数）。
   > ✅ Q6 = LLM 解析，**后端已实现**：`parse_preference_feedback` 已优先走 DeepSeek LLM（`parser: "llm:<model>"`），失败/未配置 key 时回退规则版（`parser: "rules-v1"`）。
   > - **启用条件**：后端环境变量 `DEEPSEEK_API_KEY` 已配置且 `SHOW_TRACE_PREFERENCES_LLM≠0`。未配 key 时自动降级为规则版（只认"多推荐/不想看/屏蔽"等标记词，复杂措辞会失效）。
   > - **UI 仍必须展示接口返回的 `updates`**（它到底改了哪些 include/exclude/positive/negative），让用户确认，而不是假定一定改对——这与底层是 LLM 还是规则无关。
   > - 演出**打分/分类**也是同一套 LLM 基建（DeepSeek，带规则回退），与偏好解析独立，别混淆。
2. **关注艺人**：`subscription.artists`，支持增/删，保存走 PUT。
3. **城市（已决策 Q4 = 单一城市）**：全 App **只有一个城市字段**。以 `subscription.local.city` 为唯一可写来源，可改、保存走 PUT；`profile.city` 视为派生/只读，后端需保持二者一致（PUT subscription 时同步 profile.city）。UI 上只呈现一个"城市"。
4. **数据源**：`subscription.sources` 各平台开关（大麦/秀动/摩天轮），toggle 保存走 PUT。
5. **画像展示（只读 + 自然语言可改）**：
   - 关注的演出范围 = `include_categories` + `positive_signals`
   - 不关注的演出范围 = `exclude_categories` + `negative_signals`
   - 倾向 = `ranking_preferences`

**交互细节**：
- 结构化项（艺人/城市/数据源）每次修改后乐观更新 + PUT 整个 subscription（接口是整体覆盖，注意提交完整对象）。
- feedback 发送中禁用输入，失败给出错误文案。

**空/错误态**：未配置连接时引导去设置；接口失败可重试。

### 6.4 卡片组件规范（当日摘要 & 全部演出共用）

单个演出卡片，自上而下/左右：
- 左侧：分类色块 + 分类 icon（无头图）。
- 顶行：分类名（accent）+ 兴趣决策徽章（含兴趣分）。
- 标题：`title`，最多 2 行。
- 元信息：日期（`event_date`，待定时显示"日期待定"）、价格（`price_info`，加粗）、平台标签（`source`→中文+圆点色）、城市/场馆（`city / venue`）、演出人（`artist`）。
- （可选）入选理由 `interest_reason`、发现途径 `discovered_via` 以弱文案展示。
- 整卡可点 → `purchase_url`。

### 6.5 Tab 4 · 设置

分区自上而下：

#### 6.5.1 外观
- 主题分段选择：**跟随系统 / 浅色 / 深色**，全宽自适应（不要固定宽度）。
- 选择即时生效（应用到根视图 `preferredColorScheme`），并持久化（UserDefaults）。

#### 6.5.2 数据采集 → 采集记录（push 二级页）
入口行展示最近一次运行状态摘要；点击进入「采集记录」页：
- **统计条**：`今日新增`（今日 runs 的 new_events 之和）、`近 7 天采集`（近 7 天 runs 的 extracted 之和）、`近 7 天通知`。
- **运行历史**：`GET /api/runs?limit=20` 列表，每条展示时间、trigger、状态圆点、抓取/抽取/新增/通知四项指标、错误摘要（有则红框）。
- 工具栏：刷新、手动触发一次采集（`POST /api/runs`，返回 `running` 时提示"已开始，稍后刷新"）。
> 统计的"今日/近 7 天"基于服务器时间字符串前缀比较，注意时区假设（9.5）。

#### 6.5.3 连接
- 服务器地址 `TextField` + API token `SecureField`。
- "使用服务器地址"快捷按钮（填入生产地址）。
- "测试连接"按钮：调一个轻量只读接口（如 `GET /api/events?limit=1`）验证，给出成功/失败文案。
- **token 存 Keychain**（已决策 Q5）；baseURL 可存 UserDefaults。

#### 6.5.4 关于
- 版本号：从 `Bundle.main` 读 `CFBundleShortVersionString (CFBundleVersion)`，**不写死**。

> 设置页**不得**出现无后端支撑的占位项（账户卡、反馈、隐私、写死的"采集频率"等一律不放）。

---

## 7. 后端 API 契约

**Base URL**：用户配置（生产示例 `http://8.153.84.10`，HTTP，见 9.2）。
**鉴权**：除 `/health` 外，所有接口需 `Authorization: Bearer <token>`；缺失/错误返回 `401`。
**列表包裹**：列表类返回 `{ items: [...], total, limit, offset }`。

### 7.1 GET /api/events — 演出列表
Query（均可选）：`city`、`type`(concert|exhibition|activity)、`source`、`interest_decision`(keep|maybe|filter)、`date_from`、`date_to`、`limit`(1–500，默认 100)、`offset`(默认 0)。
响应：`{ items: ShowEvent[], total, limit, offset }`，已按 `event_date`(空值靠后) 升序、`first_seen` 降序排序。
> 说明：**不支持按 `interest_category` 服务端筛选**，类目筛选需客户端做（见 9.4）。

### 7.2 GET /api/digests/today — 当日摘要（已含结构化 events）
响应：`{ date, generated_at, events: ShowEvent[], event_count, markdown?, path? }`。
- `events`：当日快照的演出列表，**已按兴趣分降序**，App 直接渲染。
- `markdown`/`path`：旧版 Markdown 摘要全文（存在时附带，用于"查看完整摘要"）。
- 无当日快照时返回最近一份（前一日）；快照与 markdown 都没有时返回 `404`（App 按空态处理，不可白屏）。

### 7.3 GET /api/digests?limit=14 — 历史摘要列表
`limit` 1–90，默认 14。响应：`{ items: Digest[], total, limit, offset:0 }`。
> 本期 App 不展示历史摘要列表（产品决策：不保留历史）；接口保留备用。

### 7.4 GET /api/subscriptions — 读订阅
响应：Subscription（见 4.3）。

### 7.5 PUT /api/subscriptions — 整体覆盖订阅
Body：`{ artists: string[], local: { city, keywords[] }, sources: { [slug]: { enabled } } }`。
响应：保存后的 Subscription。**整体覆盖语义**，提交需带完整对象。

### 7.6 GET /api/preferences — 读兴趣画像
响应：PreferenceProfile（见 4.4）。

### 7.7 POST /api/preferences/feedback — 自然语言改偏好
Body：
```json
{
  "feedback": "多推荐 livehouse，不想看亲子剧",   // 必填，1–2000 字
  "event_id": "可选，针对某条事件的反馈",
  "rescore_existing": true,                      // 可选，是否对存量事件重打分
  "rescore_limit": 500                           // 可选，0–500，默认 500
}
```
响应：
```json
{
  "profile": { /* 更新后的完整 PreferenceProfile */ },
  "updates": {
    "include_categories": ["演唱会"],
    "exclude_categories": ["亲子"],
    "positive_signals": ["独立音乐"],
    "negative_signals": []
  },
  "event_id": "...",
  "rescored_events": 128
}
```

### 7.8 POST /api/runs — 手动触发采集（异步）
返回 `202 Accepted`。Body：`{ fixture: bool, notify: bool }`。
响应（立即返回）：`{ run_id, id, status, ... }`，`status` 为 `running`（已受理，后台执行）或 `skipped`（已有运行在进行中）。真实结果通过 7.9 轮询。

### 7.9 GET /api/runs?limit=20&offset=0 — 运行历史
响应：`{ items: RunItem[], limit, offset }`。

### 7.10 其他
- `GET /health`：健康检查，无需鉴权。
- `POST /api/events/import`：后端/本地辅助导入用，**App 不调用**，本期忽略。

### 7.11 通用错误约定
- `401` 未授权（token 缺失/错误）→ App 引导去设置检查连接。
- `404` 资源不存在（如当日无摘要）→ 按空态处理。
- 网络/超时 → 错误态 + 重试；不得整屏白屏或卡死 loading。

---

## 8. 端到端数据流（给 coding AI）

```
后端 cron / 手动触发
  └─ 抓取(大麦/秀动/摩天轮) → 抽取 → LLM 打分&分类 → 落库(events + interest_scores) → 生成每日 digest

iOS App（只读消费 + 偏好写入）
  ├─ 当日摘要  ← GET /api/digests/today (+结构化 feed / 或 keep 实时查询)
  ├─ 全部演出  ← GET /api/events (+客户端 类目/搜索/未过期 过滤)
  ├─ 偏好管理  ← GET /api/preferences + GET /api/subscriptions
  │              → POST /api/preferences/feedback（自然语言）
  │              → PUT /api/subscriptions（艺人/城市/数据源）
  └─ 设置/采集记录 ← GET /api/runs ; → POST /api/runs（手动触发）
```

---

## 9. 全局非功能需求与约束

### 9.1 鉴权与配置
- 所有业务接口带 Bearer token；token 与 baseURL 存本机（建议 token 用 Keychain）。
- 未配置/连接失败时，各 Tab 给出引导而非崩溃或空白。

### 9.2 网络传输安全（ATS）
- 生产地址为 **HTTP**，Info.plist 已开 `NSAllowsArbitraryLoads`。后续若上 HTTPS 应收紧 ATS。

### 9.3 外观/主题
- 三态：跟随系统/浅/深，全局 `preferredColorScheme` 生效并持久化。
- 自定义动态颜色需正确响应深浅切换（基于 trait，强制深色时也要正确解析）。

### 9.4 客户端筛选与拉取窗口
- **"未过期"过滤走服务端**（`date_from=今天`，已决策 Q3），App 不再做日期过滤。
- 但 `/api/events` **不支持类目服务端筛选**，故"全部演出"的类目筛选与搜索仍是客户端过滤；需拉取足够大的窗口（如 `limit=200`），避免筛选后数据过少。

### 9.5 时区
- 后端 `started_at` 等为**服务器本地时间字符串、无时区**。"今日/近 7 天"统计按设备本地日期前缀比较，仅在设备与服务器同区时准确（单用户 CN 场景成立）。若后端改为带时区时间，需同步调整。

### 9.6 零废操作（硬性）
- 界面上任何带点击暗示（chevron、按钮样式、链接样式）的元素，必须有真实动作或真实数据。
- **没有后端接口支撑的功能不得放占位 UI**（如本期不做的推送通知开关、账户体系、写死的统计值）。这是历史上反复出现的问题，作为验收红线。

### 9.7 性能与健壮性
- 列表用 `LazyVStack`/`List` 懒加载。
- 单接口失败不应拖垮整屏（如当日摘要的 digest 失败不影响 feed 渲染）。
- 下拉刷新、加载/空/错误三态齐全。

### 9.8 可访问性与本地化
- 文案中文为主；尊重 Dynamic Type（分段控件等避免固定宽度导致截断）。
- 颜色对比满足可读性，尤其深色模式。

---

## 10. 决策记录（已拍板）

| 编号 | 问题 | 决策 |
|---|---|---|
| Q1 | 当日摘要快照 vs 实时 | **快照**：每日一次、不实时更新、当日未生成展示前一日、不留更早历史。 |
| Q2 | 画像是否结构化直接增删 | **否**：只读展示 + 自然语言修改即可，本期不加 profile 写接口。 |
| Q3 | 未过期过滤放哪 | **服务端**：请求带 `date_from=今天`，后端只下发未过期+待定。 |
| Q4 | 两处 city 如何处理 | **合并为一个城市**：以 `subscription.local.city` 为唯一来源，`profile.city` 派生同步。 |
| Q5 | token 存储 | **Keychain**。 |
| Q6 | 偏好 feedback 是否上 LLM | **LLM 解析，后端已实现**（DeepSeek + 规则回退）；只需配 `DEEPSEEK_API_KEY`。UI 仍要展示 `updates`。 |

## 11. 后端改动状态（本期前置依赖）

> 这些是支撑本 PRD 决策、需要在**后端**完成的改动。✅ 标记的已在本轮实现并通过测试；coding AI 做 iOS 端时按对应接口对接即可。

1. ✅ **当日摘要结构化**（Q1）：`GET /api/digests/today` 现返回结构化 `events: ShowEvent[]`（按兴趣分降序）+ `event_count` + `generated_at`，并保留 `markdown`。快照由 `app/summary.py` 生成、每次采集运行结束时重建当日快照（`summary_YYYY-MM-DD.json`）、当日缺失则取最近一份（前一日）。
2. ✅ **演出列表日期过滤下发**（Q3）：`GET /api/events?date_from=<今天>` 已按"未过期 + 待定（`event_date` 为空保留）"语义工作（`list_events`/`count_events` 已修）。
3. ✅ **城市单一来源同步**（Q4）：`PUT /api/subscriptions` 写入 `local.city` 时已同步 `profile.city`。
4. ✅ **偏好 feedback LLM**（Q6）：已是 DeepSeek LLM + 规则回退（无需新开发，配 `DEEPSEEK_API_KEY` 即启用）。

> 运维：`summary_*.json` 快照文件按日累积，读取永远取最新一份，旧文件可定期清理（非必须）。

---

## 附录 A · 现有代码资产对照（给 coding AI）

- 设计 token / 分类 / 来源 / 状态映射的单一事实源：`ios/ShowTraceApp/ShowTraceApp/Views/SharedViews.swift`（`EventCategory` / `EventSource` / `RunStatus` / `Color` 扩展）。
- 数据模型：`Models.swift`（`ShowEvent` / `Subscription` / `PreferenceProfile` / `RunItem` 等，CodingKeys 已映射 snake_case）。
- 网络层：`Services/APIClient.swift`；配置：`Services/AppSettings.swift`（baseURL/token/themeMode）。
- 现有视图：`TodayView`(当日摘要) / `EventsView`+`EventCard`(全部演出) / `SubscriptionView`+`PreferencesView`(待合并为偏好管理) / `SettingsView`+`RunsView`(设置) / `DigestView`(摘要正文)。
- 后端契约源码：`app/api.py`（端点）、`app/database.py`/`db.py`（数据形状）、`app/preferences.py`（类目/信号/打分）。

> 复用原则：新增映射（颜色/类目/来源/状态）一律加到 `SharedViews.swift` 的对应 enum，禁止在多个视图各写一份。
