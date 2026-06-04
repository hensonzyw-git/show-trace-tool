# 架构

> 这是《演出活动监控-需求与Roadmap.md》第二、三节的精简版。完整背景看根目录那份文档。

## 系统本质：一条数据管道

```
原始信息 → 抓取 → 结构化 → 去重 / 匹配 → 存储 → 通知
```

每个阶段独立，阶段之间用「存储」解耦：上游落盘，下游读盘。改下游不必重跑上游。

Phase 4 上云后，这条管道拆成两类入口：

```
云端稳定源        → 抓取 / LLM 抽取 → POST/内部写入 → events 表
本机困难源辅助抓取 → 本机结构化 JSON  → POST /api/events/import → events 表
```

稳定源（秀动 / 摩天轮）在 ECS 上定时跑。困难源（小红书 / 大麦等）优先留在本机，用真实 Chrome、Computer Use、人工接管或插件能力获取信息，再把标准化事件同步到云端。iOS App 和摘要读取只看云端 API，不关心事件来自哪种入口。

下一阶段增加一层"喜好过滤"，但不改变上游采集事实：

```
events 表事实数据 → LLM 喜好分类 / 打分 → digest / iOS 推荐视图
                         ↑
                  iOS 自然语言反馈
```

原则：

- 采集层尽量客观，覆盖用户明确关注的上海活动品类。
- 偏好层不直接删除事件，只输出 `keep` / `maybe` / `filter`、分数和理由。
- iOS 用自然语言收集反馈，后端把反馈沉淀成结构化 `interest_profile`。
- digest 和 iOS 默认展示高匹配事件；`GET /api/events?interest_decision=keep|maybe|filter` 由服务端完成分层查询，同时保留过滤统计，方便用户继续校准。

## 两个业务维度（驱动 config.yaml 设计）

| 维度 | 配置块 | 城市 | 含义 |
|---|---|---|---|
| 关注艺人 | `artists` | 不限 | 跟踪指定艺人的演唱会，全国巡演都监控 |
| 本地发现 | `local.keywords` + `local.city` | 限定 | 不限艺人，按关键词找本地的演唱会、展览、音乐节、活动 |

抓取层（`sources.*`）刻意把 `city` 作为 `fetch_raw(query, city=...)` 的可选参数，
而不是 Source 的实例属性 —— 同一个 Source 实例两个维度都能用，由 `app/pipeline.py` 决定怎么传。

## 已锁定的决策（改起来贵的部分）

1. **统一数据模型** —— 所有事件流经同一个 `events` 表结构（里程碑 1 在 `db.py` 中落地）。
2. **原始 / 结构化切分** —— 抓取只把原始内容落到 `data/raw/`，抽取从原始内容产出结构化事件，两步分开存。
3. **两个接口**
   - `sources/base.py::Source` —— 每个抓取平台实现一个子类
   - `notifiers/base.py::Notifier` —— 每个通知渠道实现一个子类（里程碑 1 加）
   - **接口按「将来 N 个」设计，MVP 只实现 1 个**。不写插件注册、抽象工厂。
4. **技术栈**
   - Python 3.11
   - `requests` + `BeautifulSoup` 处理简单页面；以后再用 `Playwright` 处理 JS 渲染 / 登录态
   - **SQLite** 做结构化存储（里程碑 1 加）
   - **Claude (Anthropic API)** 做 LLM 抽取，避免写一堆易碎的 CSS selector

## 现在不纠结的（改起来便宜的部分）

通知渠道、调度方式、某个源用 requests 还是 Playwright、SQLite 换不换数据库 —— 都是「换一个适配器」或「加一个文件」的事，跟架构无关。

## 多源：每个源独立 Source 子类 + SOURCE_REGISTRY 注册

`app/pipeline.py::SOURCE_REGISTRY` 注册所有 source 类。加新源 3 步：
1. `sources/<name>.py` 实现 Source 子类（`fetch_raw` + 通常 `discovered_via`）
2. SOURCE_REGISTRY 加一行 `"<name>": <Class>`
3. 订阅配置里设置 `sources.<name>.enabled: true`（首次会从 `config.yaml` 初始化）

每个 source 自带两个 class attr / method 反映"此源代价模型"：
- `fetch_interval_range`: 此源两次 fetch 之间的随机间隔范围（秒）。反爬强弱差异巨大：大麦 6-12s，秀动 1-3s
- `discovered_via(query, city)`: 给 digest 渲染用的"用户视角在哪发现"字符串。每个源按自己的交互模型 override（搜索式 / 浏览式）

`app/pipeline.py` 嵌套 loop：每个 source 跑所有 task；interval 用各源自己的 range。`_run_one` 在 `raw == ""` 时优雅跳过，给"此源不支持当前查询"留口子。

当前接入的源：

| Source | 反爬 | 主打覆盖 | 抓取技术 |
|---|---|---|---|
| 大麦 (damai) | 重（阿里 RGV587 滑块） | 商业演出、演唱会、展览 | patchright + 持久化 Chrome profile |
| 秀动 (showstart) | 无 | Livehouse、独立音乐、小型现场 | requests + cityCode 直接拉 SSR HTML |
| 摩天轮 (motianlun) | 无 | 话剧歌剧、舞蹈芭蕾、曲艺脱口秀、展览市集、儿童亲子、体育赛事 | requests 直接调 JSON API（floor 推荐 70+ 条/次）|

源之间互补很强（大麦商演 / 秀动 Livehouse / 摩天轮 话剧+脱口秀+展览）。`events.id` 哈希让多源抓到同一事件自然去重，实测一次跑 107 抽到、78 入库（29 条跨源去重）。

## 本机困难源导入

困难源不强行实现为云端 Source。它们先产出标准事件 JSON，再调用：

```
POST /api/events/import
```

导入接口复用 `db.upsert_event()`，所以去重规则和云端 worker 完全一致。导入也会写入 `runs` 表，`trigger` 通常用 `local-sync`、`local-computer-use` 或具体平台名，方便未来在 iOS App 或 API 中追溯来源。

这条入口适合：

- 小红书：用本机 Chrome / Computer Use / 插件搜索，整理成结构化事件。
- 大麦：云端禁用，保留本机 profile 和人工接管能力。
- 手动补录：用户在任意平台看到活动，也可以构造成 JSON 上传。

## 决策不做：详情页跟进

LLM 只抽搜索页能见到的字段，`on_sale_time` 经常是 `null` 也接受。digest 里的 `purchase_url` 是大麦详情页直链，对某条事件感兴趣时 cmd+click 即可去原平台看完整信息（开票时间、座位图、实时余票等）。

实验过 main.py 自动抓详情页 + LLM 二次抽取，但弃用，原因：
- `detail.damai.cn` 用 patchright + profile cookies 会被服务端 500，要走 `requests` 无 cookie 路径
- LLM 重抽时 title/venue 微差导致 `events.id` 漂移（同事件入两条）
- 用户对感兴趣事件会自己去原平台决策购买，自动补全的 ROI 低

定位上：**digest 是"发现层"，原平台是"决策层"**，不要让 LLM 模糊这两层。
