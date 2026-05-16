# 架构

> 这是《演出活动监控-需求与Roadmap.md》第二、三节的精简版。完整背景看根目录那份文档。

## 系统本质：一条数据管道

```
原始信息 → 抓取 → 结构化 → 去重 / 匹配 → 存储 → 通知
```

每个阶段独立，阶段之间用「存储」解耦：上游落盘，下游读盘。改下游不必重跑上游。

## 两个业务维度（驱动 config.yaml 设计）

| 维度 | 配置块 | 城市 | 含义 |
|---|---|---|---|
| 关注艺人 | `artists` | 不限 | 跟踪指定艺人的演唱会，全国巡演都监控 |
| 本地发现 | `local.keywords` + `local.city` | 限定 | 不限艺人，按关键词找本地的演唱会、展览、音乐节、活动 |

抓取层（`sources.*`）刻意把 `city` 作为 `fetch_raw(query, city=...)` 的可选参数，
而不是 Source 的实例属性 —— 同一个 Source 实例两个维度都能用，由 main.py 决定怎么传。

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

## 决策不做：详情页跟进

LLM 只抽搜索页能见到的字段，`on_sale_time` 经常是 `null` 也接受。digest 里的 `purchase_url` 是大麦详情页直链，对某条事件感兴趣时 cmd+click 即可去原平台看完整信息（开票时间、座位图、实时余票等）。

实验过 main.py 自动抓详情页 + LLM 二次抽取，但弃用，原因：
- `detail.damai.cn` 用 patchright + profile cookies 会被服务端 500，要走 `requests` 无 cookie 路径
- LLM 重抽时 title/venue 微差导致 `events.id` 漂移（同事件入两条）
- 用户对感兴趣事件会自己去原平台决策购买，自动补全的 ROI 低

定位上：**digest 是"发现层"，原平台是"决策层"**，不要让 LLM 模糊这两层。
