# 本机辅助采集流程

稳定源已经交给云端 ECS：

- 秀动
- 摩天轮

本机不再做每日全量自动抓取，也不再用 launchd 定时跑旧 worker。本机只负责困难源的辅助采集：

- 小红书：Chrome / Computer Use / 插件 / 人工接管
- 大麦：本机 Chrome profile / 人工接管
- 其他云端抓取失败的平台

## 当前原则

1. 本机不直接写云端数据库。
2. 本机不跑稳定源，避免和 ECS 重复。
3. 困难源先产出结构化 JSON，再调用云端导入 API。
4. 每次同步都走 `POST /api/events/import`，复用云端去重逻辑。

## 目录

本机辅助采集产物放在：

```text
data/local_inbox/
```

JSON 文件不进 Git。可以用日期和平台命名：

```text
data/local_inbox/2026-06-03-xiaohongshu.json
data/local_inbox/2026-06-03-damai.json
```

## JSON 格式

```json
{
  "trigger": "local-computer-use",
  "notify": false,
  "events": [
    {
      "type": "concert",
      "title": "示例演出",
      "artist": "周杰伦",
      "city": "上海",
      "venue": "示例场馆",
      "event_date": "2026-08-08",
      "on_sale_time": null,
      "price_info": "待确认",
      "purchase_url": "https://example.com",
      "source": "xiaohongshu",
      "source_url": "https://www.xiaohongshu.com",
      "raw_ref": "local://xiaohongshu/2026-06-03",
      "discovered_via": "小红书 · 本机 Chrome 搜索",
      "status": "rumored"
    }
  ]
}
```

必填字段：

- `type`: `concert` / `exhibition` / `activity`
- `title`
- `source`

建议尽量填写：

- `city`
- `venue`
- `event_date`
- `purchase_url`
- `discovered_via`

`discovered_via` 很重要，它保留“在哪看到”，方便之后回原平台人工确认。

## 同步到云端

本机 `.env` 需要包含：

```env
SHOW_TRACE_API_BASE_URL=http://<server-ip>
SHOW_TRACE_CLOUD_API_TOKEN=<cloud-api-token>
```

同步：

```bash
./venv/bin/python scripts/sync_local_events.py data/local_inbox/2026-06-03-xiaohongshu.json
```

导入后立即触发云端摘要 / 通知：

```bash
./venv/bin/python scripts/sync_local_events.py data/local_inbox/2026-06-03-xiaohongshu.json --notify
```

默认不通知，避免调试时打扰。稳定后可以决定是否让困难源同步后自动通知。

## 后续再自动化的边界

只有当某个困难源的本机流程满足这三个条件，才重新加本机自动化：

1. 单次运行有明确超时。
2. 失败不会阻塞其他来源。
3. 产出是标准 JSON，而不是直接写本机数据库。

在此之前，本机流程保持“辅助采集 + 手动同步”，更适合当前阶段。
