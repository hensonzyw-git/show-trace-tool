# 代码 Review — 演出活动监控

## 处理状态（2026-06-05 已修复）

| 项 | 状态 | 落点 |
|---|---|---|
| H1 SQLite 并发 | ✅ | `db.py` 加 `apply_pragmas`（WAL + busy_timeout）；`app/database.py` 共用；移除读路径 `init_db`；`app/api.py` lifespan 启动时建表 |
| H2 运行互斥 | ✅ | `app/pipeline.py` `_run_lock`，并发触发返回 `status="skipped"` |
| H3 通知语义 | ✅ | 文案统一改「待通知事件」（markdown / feishu / feishu_app / macos） |
| M1 排除逻辑 | ✅ | `_score_event_with_rules` 增加 `category in exclude_categories` 判断 |
| M2 重复评分 | ✅ | pipeline / import 仅对新增（或未评分）事件评分 |
| M3 macOS 通知 | ✅ | `MacosNotifier` 非 darwin 静默跳过 |
| M4 依赖 | ✅ | `requirements.txt` 锁版本；浏览器栈拆到 `requirements-local.txt`；damai 改懒加载 |
| M5 测试 | ✅ | `tests/` 33 个用例（pytest），覆盖日期归一 / 规则评分 / 抽取 / 通知卡片 |
| L1 token 比较 | ✅ | `hmac.compare_digest`，失败统一 401 |
| L3 连接层 | ✅ | 两处 `_conn` 共用 `apply_pragmas` |
| L4 抽取防御 | ✅ | 过滤非 dict 的 LLM 返回项 |
| L5 截断日志 | ✅ | `html_to_text` 超限时打印提示 |
| L6 飞书卡片 | ✅ | 抽到 `notifiers/feishu_card.py` 共用 |
| **L2 event_id 归一** | ⏸ 暂缓 | 改哈希算法会让现有 DB 全部 event_id 失配 → 旧事件被当新事件重发一遍。建议配合一次性迁移脚本再做，不宜直接改 |

验证：`pytest` 33 passed；`app.api` 等 13 个模块导入通过（缺 patchright 时 `DamaiSource=None`、SOURCE_REGISTRY 自动只含云端源）；WAL 生效；auth 三种情形（valid/wrong/missing）行为正确。

---

Review 范围：根目录与 `app/`、`sources/`、`notifiers/`、`scripts/` 全部业务代码（约 3100 行，排除 `venv/`）。整体质量很好——管道分层清晰、接口（Source / Notifier）抽象得当、`paths.py` 用环境变量做云端覆盖、原始/结构化分离、无 key 时优雅降级、docstring 详尽。下面按严重度列出问题，每条附定位和建议。

---

## 高优先级（云端稳定性 / 正确性）

### H1. SQLite 没有并发保护，且长任务跑在请求线程里

`db.py::_conn()` 和 `app/database.py::_conn()` 都是裸 `sqlite3.connect`，没有 `WAL`、没有 `busy_timeout`。同时：

- `POST /api/runs`（`app/api.py:185`）直接 `return run_pipeline(...)` —— 同步路由，FastAPI 在线程池里跑。`run_pipeline` 含 `time.sleep(6~12s)` 间隔 + 多次 LLM 调用，单次可阻塞数分钟（cron 端 `trigger_cloud_run.py` 给了 900s 超时正说明这点）。
- 与此同时 `list_events`（`app/database.py:43`）每次请求都调 `init_db()`，而 `init_db()` 会执行 `executescript(SCHEMA)` + `PRAGMA` +（可能）`ALTER`——这是一次 DDL 写事务，**每个 `/api/events` 读请求都在写锁**。

云端 web 进程 + cron 同时打同一个 DB 文件时，几乎必然出现 `database is locked`。

**建议**：在 `_conn()` 里统一开 `PRAGMA journal_mode=WAL; PRAGMA busy_timeout=5000;`；`init_db()` 改成进程启动时跑一次（FastAPI startup event / `main.py` 入口），读路径不要再调；把 `run_pipeline` 放进 `BackgroundTasks` 或独立 worker，请求只返回 run_id。

### H2. `run_pipeline` 没有互斥，可并发重入

cron 触发与手动 `POST /api/runs` 可同时启动两次采集 → 重复抓取、重复通知、加剧 H1 的锁竞争。

**建议**：加运行锁——简单做法是开跑前检查 `runs` 表是否有 `status='running'` 且未超时的记录；或用文件锁 / DB 应用锁。

### H3. 通知范围与"新事件"语义不符

`_run_pipeline_body`（`pipeline.py:223`）和 `import_events`（`api.py:233`）通知的都是 `get_unnotified_events()`——**全历史所有 `notified_at IS NULL` 的事件**，不是本次新增的。但 Markdown / 飞书标题写的是「共 N 条新事件」。

后果：某次用 `notify=False` 跑过后，那批未通知事件会在下一次通知时被一起倒出来；计数也对不上（N 其实是"累计未通知数"而非"本次新增"）。

**建议**：明确语义二选一——要么只通知本次 `stats.new_event_ids`（pipeline 已经收集了），要么把文案从「新事件」改成「未通知事件」。

---

## 中优先级

### M1. 规则评分的"排除"逻辑不对称（漏过滤）

`preferences.py::_score_event_with_rules`：
- include 命中走的是**类别成员判断** `category in include_categories`（`:242`）
- exclude 只走**标题别名匹配** `_matches_any_category(title, exclude_categories)`（`:233`），从不检查 `category in exclude_categories`

于是一个靠 `type` 推断出类别（如 `亲子`）、但标题里没有别名词的事件，即使 `亲子` 在 `exclude_categories` 里也不会被 `filter`。

**建议**：排除分支补一条 `if category in exclude_categories: return filter`，与 include 对称。

### M2. LLM 评分重复且偏贵

每次 `run_pipeline` 对 `all_events`（含已入库的旧事件）全量重新评分（`pipeline.py:211`）；`import` 也整批评分；`/preferences/feedback` 默认 `rescore_existing` 最多重刷 500 条（`api.py:171`）。DeepSeek 便宜，但这是按运行次数线性增长的可省成本。

**建议**：pipeline 里只对新事件（`is_new`）评分，或对已评分事件跳过；feedback 重刷做成可选/异步。

### M3. macOS Notifier 进了云端通知链

`pipeline.py:228` 的通知循环包含 `MacosNotifier()`。云端是 Render Linux，`osascript` 不存在，虽然被 `except` 兜住，但每次跑都报一条失败日志。`import_events` 的通知链就没带 macos，二者不一致。

**建议**：按平台/配置门控 macos notifier，或像 import 那样不放进云端链路。

### M4. 依赖未锁版本，且云端镜像装了用不到的浏览器栈

`requirements.txt` 全是 `>=`，云端构建不可复现；同时 `playwright` + `patchright` 被装进云端镜像，但 `config.cloud.yaml` 已禁用 damai，这两个重依赖（还需 `playwright install` 下浏览器）在云端纯属浪费。注意 `pipeline.py:33` 在模块顶层 `from sources.damai import DamaiSource`，会在 import 期触发 `patchright` import——云端必须保证它装着，否则整个 API 起不来。

**建议**：锁版本（`pip freeze` 或 `pip-tools`）；把浏览器源依赖拆成可选 extra，或云端 requirements 分文件。

### M5. 零测试

多处 docstring 说"testable / 便于测试"，但仓库无任何测试。恰恰最该测的几块都很脆：`normalize_event_date` 的区间/跨年逻辑、`_score_event_with_rules` 规则、LLM 失败回退、`make_event_id` 稳定性。

**建议**：先给 `db.normalize_event_date`、`preferences` 规则路径、`extractor.html_to_text` 加单元测试（纯函数、不依赖网络/LLM，成本低收益高）。

---

## 低优先级 / 打磨

- **L1. Token 比较非常量时间**（`auth.py:25`）：`token != expected` 有时序侧信道，且 401/403 分流泄露"格式是否正确"。改用 `hmac.compare_digest`，失败统一返回 401。
- **L2. `make_event_id` 依赖 LLM 原样字符串**（`db.py:118`）：venue/title 抽取文字稍有漂移就会生成新 ID → 同一演出重复入库。可考虑对 title/venue 做更强归一（去空白/标点/全半角），或容忍重复。
- **L3. 两套 DB 连接层重复**：`db.py::_conn`（带 commit）与 `app/database.py::_conn`（只读）逻辑重复，WAL/busy_timeout 修复时要改两处。建议合并到一个 helper。
- **L4. `extractor.extract_events` 假设 events 元素是 dict**（`extractor.py:130`）：若 LLM 返回 `events:[null]` 或字符串，`.setdefault` 会抛。加一层 `isinstance(e, dict)` 过滤。
- **L5. `html_to_text` 60k 截断**（`extractor.py:62`）可能在大页面上静默丢事件；可记一条日志提示被截断。
- **L6. 飞书两个 notifier 的卡片渲染逻辑几乎重复**（`feishu.py` / `feishu_app.py` 的 lines 构造段）：抽成共享函数，少一处改两遍。

---

## 优点（值得保留）

架构决策很扎实：Source/Notifier 双接口 + `SOURCE_REGISTRY` 注册、原始落盘与结构化分离、`fetch_interval_range` / `discovered_via` 把"每个源的代价模型"内聚到源自身、`_cached_fetch` 处理同城重复抓取、`paths.py` 用环境变量适配云端、无 API key 时不崩而是返回空。这些都体现了清晰的工程判断，继续保持。

---

## 建议处理顺序

1. **H1 + H2**（SQLite WAL/busy_timeout、init_db 移到启动、pipeline 异步化 + 运行锁）——云端能否稳定跑的关键。
2. **H3**（通知语义）+ **M1**（排除逻辑）——直接影响用户看到的结果对不对。
3. **M3 / M4**——清理云端部署噪音与镜像。
4. **M5 + L 系列**——补测试与打磨。
