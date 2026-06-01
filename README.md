# 演出活动监控

本地部署的个人工具，每天自动抓取大麦 / 秀动 / 摩天轮三个平台的上海演出 + 关注艺人全国巡演信息，去重后生成 Markdown 摘要 + macOS 系统通知。

完整需求和架构见 [《演出活动监控-需求与Roadmap.md》](演出活动监控-需求与Roadmap.md) 和 [ARCHITECTURE.md](ARCHITECTURE.md)。

## 日常使用

```bash
# 手动跑一次（也是 launchd 调用的命令）
./venv/bin/python main.py

# 用 fixture（绕开抓取，验证 LLM 抽取链路）
./venv/bin/python main.py --fixture

# 给大麦养 Chrome profile（首次必跑、或被反爬后重养）
./venv/bin/python main.py --init-profile
```

跑完后看：
- `data/digests/digest_YYYY-MM-DD.md` —— Markdown 摘要（Top N + 按日期分组）
- macOS 通知中心 —— "X 条新事件" 提醒

## 本地 API（Phase 1）

服务端化第一步先提供只读 API，不改变现有每日采集流程：

```bash
./venv/bin/uvicorn app.api:app --reload
```

打开：
- `http://127.0.0.1:8000/health` —— 健康检查
- `http://127.0.0.1:8000/api/events` —— 事件列表
- `http://127.0.0.1:8000/api/digests/today` —— 今日 Markdown 摘要
- `http://127.0.0.1:8000/docs` —— OpenAPI 文档

## 自动化（launchd 每天 10:00 跑）

把 plist 模板装到用户 LaunchAgents：

```bash
# 一次性安装
cp "launchd/com.zhuyawei.show-trace-tool.plist" ~/Library/LaunchAgents/
launchctl load ~/Library/LaunchAgents/com.zhuyawei.show-trace-tool.plist

# 立即触发一次测试（不等到明早 10:00）
launchctl start com.zhuyawei.show-trace-tool

# 看跑的日志
tail -f data/launchd.log

# 卸载
launchctl unload ~/Library/LaunchAgents/com.zhuyawei.show-trace-tool.plist
rm ~/Library/LaunchAgents/com.zhuyawei.show-trace-tool.plist
```

第一次 launchd 触发时 macOS 可能弹"是否允许 Python 发送通知"，授权一次即可。

## 配置

`config.yaml`：

```yaml
artists:           # 关注艺人，全国巡演都监控
  - 周杰伦
local:             # 上海本地发现（不限艺人）
  city: 上海
  keywords:
    - 演唱会
    - 展览
    - 音乐节
sources:           # 启用的抓取源
  damai:
    enabled: true
  showstart:
    enabled: true
  motianlun:
    enabled: true
```

`.env`：

```
DEEPSEEK_API_KEY=sk-xxx

# 可选：飞书 webhook，配了就推 Top 5 到飞书群（手机也收到）
FEISHU_WEBHOOK_URL=https://open.feishu.cn/open-apis/bot/v2/hook/xxx
```

### 飞书推送（可选，两种方式任选）

**方式 A：群机器人 webhook（最简单，绑定一个群）**

1. 在飞书任意群右上角点 **设置 → 群机器人 → 添加机器人 → 自定义机器人**
2. 复制 webhook URL，填到 `.env::FEISHU_WEBHOOK_URL`

**方式 B：自建应用机器人（更灵活，能推到任意 chat/user/email）**

适合你在飞书开放平台已经有自建应用、配过 `im:message:send_as_bot` 权限的场景。

1. 在 [飞书开放平台](https://open.feishu.cn/) 拿你的 `app_id` / `app_secret`
2. 拿到目标 `receive_id`（chat_id / open_id / user_id 或邮箱）
3. 填到 `.env`：
   ```
   FEISHU_APP_ID=cli_xxx
   FEISHU_APP_SECRET=xxx
   FEISHU_RECEIVE_ID=oc_xxx 或邮箱
   FEISHU_RECEIVE_ID_TYPE=chat_id  # 或 open_id / email / user_id
   ```

两种方式都配的话两边都会推（不冲突）。每次跑 `main.py` 自动推 Top 5（按日期升序的今天及以后事件）。完整 digest 仍在本地 `data/digests/`。

## 项目结构

```
main.py                 编排：抓取 → LLM 抽取 → 入库去重 → 通知
config.yaml             艺人 / 城市 / 启用的源
.env                    DeepSeek API key（gitignore）
db.py                   SQLite schema + upsert / 查询
extractor.py            LLM 抽取（DeepSeek）
sources/
  base.py               Source 抽象基类 + fetch cache helper
  damai.py              大麦（patchright + 持久化 Chrome profile）
  showstart.py          秀动（requests + cityCode）
  motianlun.py          摩天轮（requests + JSON API）
notifiers/
  base.py               Notifier 抽象基类
  markdown.py           写 data/digests/digest_YYYY-MM-DD.md
  macos.py              macOS 原生系统通知
launchd/                launchd plist 模板
data/                   gitignore 的运行时数据：DB / raw / digests / log
  fixtures/             ←  这个不 ignore，是抽取链路的稳定参照样本
```
