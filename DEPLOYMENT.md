# 云端部署说明

Phase 4 的目标不是一上来解决所有反爬平台，而是先让稳定源在云端每天自动跑起来：

- API 服务可以公网访问，并用 `API_TOKEN` 保护 `/api/*`。
- SQLite、raw 抓取内容、digest 文件放在持久化目录。
- 每天自动触发一次 worker。
- 第一版云端只启用稳定源：秀动、摩天轮。
- 大麦默认关闭，后续作为 BrowserSource 单独处理。

当前支持两条路线：

1. Render：适合快速展示和验证 API。
2. 阿里云 ECS：适合你想拥有完整服务器控制权，后续尝试 Chrome / Computer Use / Codex 等能力。

---

## 1. 项目里的部署相关文件

- `render.yaml`：Render Blueprint，包含 API Web Service 和每日 cron trigger。
- `config.cloud.yaml`：云端首次初始化订阅用配置，默认 `damai.enabled: false`。
- `scripts/trigger_cloud_run.py`：定时任务 helper，通过 `POST /api/runs` 触发 worker。
- `.env.example`：环境变量模板。
- `app/auth.py`：API token 鉴权。
- `app/paths.py`：云端持久化路径配置。

---

## 2. 环境变量

### 2.1 必填

```env
API_TOKEN=<一段足够长的随机 token>
DEEPSEEK_API_KEY=<DeepSeek API key>
SHOW_TRACE_CONFIG_PATH=config.cloud.yaml
```

### 2.2 持久化目录

Render 推荐：

```env
SHOW_TRACE_DATA_DIR=/var/data/show-trace-tool
```

阿里云 ECS 推荐：

```env
SHOW_TRACE_DATA_DIR=/srv/show-trace-tool/data
```

如果设置了 `SHOW_TRACE_DATA_DIR`，默认会把这些内容放进去：

- SQLite：`events.db`
- 原始抓取文件：`raw/`
- 每日摘要：`digests/`

也可以分别覆盖：

```env
SHOW_TRACE_DB_PATH=
SHOW_TRACE_DIGEST_DIR=
SHOW_TRACE_RAW_DIR=
```

### 2.3 可选通知配置

```env
FEISHU_WEBHOOK_URL=
FEISHU_APP_ID=
FEISHU_APP_SECRET=
FEISHU_RECEIVE_ID=
FEISHU_RECEIVE_ID_TYPE=chat_id
```

### 2.4 可选禁用 source

即使数据库订阅里启用了某个 source，也可以通过环境变量强制禁用：

```env
SHOW_TRACE_DISABLED_SOURCES=damai
```

---

## 3. Render 部署路线

Render 适合快速把 API 跑到公网，验证作品展示链路。

### 3.1 为什么 Render cron 不是直接跑 worker

这个项目当前使用 SQLite 和本地 digest 文件。它们需要持久化目录。

Render cron job 不能挂载 web service 的同一块持久磁盘，所以 cron job 不直接运行 `main.py`。正确做法是：

```text
Render cron job -> 调用 POST /api/runs -> web service 内部运行 pipeline -> 写入 web service 持久磁盘
```

### 3.2 创建步骤

1. 在 Render 创建 Blueprint。
2. 选择本仓库。
3. 使用根目录的 `render.yaml`。
4. 给 web service 填环境变量：

   ```env
   API_TOKEN=<同一份 token>
   DEEPSEEK_API_KEY=<DeepSeek API key>
   SHOW_TRACE_DATA_DIR=/var/data/show-trace-tool
   SHOW_TRACE_CONFIG_PATH=config.cloud.yaml
   ```

5. 可选填写飞书通知变量。
6. 等 web service URL 生成后，给 cron job 填：

   ```env
   API_TOKEN=<同一份 token>
   SHOW_TRACE_API_BASE_URL=https://<your-render-service>.onrender.com
   SHOW_TRACE_RUN_FIXTURE=false
   SHOW_TRACE_RUN_NOTIFY=true
   ```

### 3.3 Render 验证

健康检查：

```bash
curl https://<your-render-service>.onrender.com/health
```

无 token 访问 `/api/*` 应该失败：

```bash
curl -i https://<your-render-service>.onrender.com/api/subscriptions
```

带 token 访问订阅：

```bash
curl -H "Authorization: Bearer $API_TOKEN" \
  https://<your-render-service>.onrender.com/api/subscriptions
```

手动触发一次云端采集：

```bash
curl -X POST https://<your-render-service>.onrender.com/api/runs \
  -H "Authorization: Bearer $API_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"fixture": false, "notify": true}'
```

查看运行记录：

```bash
curl -H "Authorization: Bearer $API_TOKEN" \
  https://<your-render-service>.onrender.com/api/runs
```

查看今日摘要：

```bash
curl -H "Authorization: Bearer $API_TOKEN" \
  https://<your-render-service>.onrender.com/api/digests/today
```

---

## 4. 阿里云 ECS 部署路线

可以使用阿里云服务器。对这个项目，我更推荐 **ECS**，而不是轻量应用服务器。

原因：

- 你后续可能需要装 Chrome / Playwright / Patchright / Codex / Computer Use 相关能力。
- ECS 对系统、网络、安全组、磁盘、进程管理的控制权更完整。
- 作为求职 demo，ECS + systemd + Nginx + cron 的部署链路更像真实工程。

轻量应用服务器也能跑当前稳定源，但更适合博客、小型网站、开发测试。如果只是今天想省事、低成本跑 FastAPI 和稳定源，也可以用轻量应用服务器；如果你想为后续困难源留余地，选 ECS。

### 4.1 建议购买配置

第一版建议：

- 地域：华东 2（上海）或华东 1（杭州）
- 系统：Ubuntu 22.04 LTS 或 Ubuntu 24.04 LTS
- 规格：2 vCPU / 2 GB 起步
- 系统盘：40 GB 起步
- 公网带宽：3-5 Mbps 起步
- 计费：先按量付费或短周期包月，确认稳定后再长期购买

如果后续要跑浏览器自动化，2 GB 内存可能偏紧，建议升到 4 GB。

### 4.2 安全组

最低开放：

- `22/tcp`：SSH，仅允许你的常用 IP 更安全
- `80/tcp`：HTTP
- `443/tcp`：HTTPS

不建议直接长期暴露 `8000/tcp`。生产访问建议走 Nginx 反代到本机 `127.0.0.1:8000`。

如果 `curl http://<server-ip>/health` 在服务器本机正常，但公网访问为空响应或失败，优先检查阿里云安全组是否已经添加 `80/tcp` 入方向规则。

### 4.3 服务器初始化

登录服务器：

```bash
ssh root@<server-ip>
```

安装基础依赖。Ubuntu 24.04 默认 Python 是 3.12，这个项目可以直接用系统 `python3` 创建虚拟环境：

```bash
apt update
apt install -y git python3 python3-venv python3-pip nginx sqlite3 cron
```

创建目录：

```bash
mkdir -p /srv/show-trace-tool
cd /srv/show-trace-tool
```

拉代码：

```bash
git clone https://github.com/hensonzyw-git/show-trace-tool.git .
```

创建虚拟环境：

```bash
python3 -m venv venv
./venv/bin/pip install -r requirements.txt
```

创建 `.env`：

```bash
cp .env.example .env
nano .env
```

至少填写：

```env
API_TOKEN=<一段足够长的随机 token>
DEEPSEEK_API_KEY=<DeepSeek API key>
SHOW_TRACE_DATA_DIR=/srv/show-trace-tool/data
SHOW_TRACE_CONFIG_PATH=config.cloud.yaml
SHOW_TRACE_DISABLED_SOURCES=damai
```

### 4.4 测试本机运行

启动 API：

```bash
./venv/bin/uvicorn app.api:app --host 127.0.0.1 --port 8000
```

另开一个 SSH 窗口测试：

```bash
curl http://127.0.0.1:8000/health
curl -H "Authorization: Bearer $API_TOKEN" \
  http://127.0.0.1:8000/api/subscriptions
```

触发一次采集：

```bash
curl -X POST http://127.0.0.1:8000/api/runs \
  -H "Authorization: Bearer $API_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"fixture": false, "notify": true}'
```

### 4.5 systemd 托管 API

创建服务文件：

```bash
nano /etc/systemd/system/show-trace-tool.service
```

内容：

```ini
[Unit]
Description=Show Trace Tool API
After=network.target

[Service]
WorkingDirectory=/srv/show-trace-tool
EnvironmentFile=/srv/show-trace-tool/.env
ExecStart=/srv/show-trace-tool/venv/bin/uvicorn app.api:app --host 127.0.0.1 --port 8000
Restart=always
RestartSec=5

[Install]
WantedBy=multi-user.target
```

启动：

```bash
systemctl daemon-reload
systemctl enable --now show-trace-tool
systemctl status show-trace-tool
```

查看日志：

```bash
journalctl -u show-trace-tool -f
```

### 4.6 Nginx 反向代理

创建配置：

```bash
nano /etc/nginx/sites-available/show-trace-tool
```

内容：

```nginx
server {
    listen 80;
    server_name _;

    location / {
        proxy_pass http://127.0.0.1:8000;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
    }
}
```

启用：

```bash
ln -s /etc/nginx/sites-available/show-trace-tool /etc/nginx/sites-enabled/show-trace-tool
nginx -t
systemctl reload nginx
```

访问：

```bash
curl http://<server-ip>/health
curl -H "Authorization: Bearer $API_TOKEN" \
  http://<server-ip>/api/subscriptions
```

### 4.7 cron 定时任务

编辑 crontab：

```bash
crontab -e
```

每天 10:00 执行一次：

```cron
0 10 * * * cd /srv/show-trace-tool && set -a && . /srv/show-trace-tool/.env && set +a && SHOW_TRACE_API_BASE_URL=http://127.0.0.1 /srv/show-trace-tool/venv/bin/python scripts/trigger_cloud_run.py >> /srv/show-trace-tool/data/cron.log 2>&1
```

也可以先用 fixture 测试：

```cron
0 10 * * * cd /srv/show-trace-tool && set -a && . /srv/show-trace-tool/.env && set +a && SHOW_TRACE_API_BASE_URL=http://127.0.0.1 SHOW_TRACE_RUN_FIXTURE=true SHOW_TRACE_RUN_NOTIFY=false /srv/show-trace-tool/venv/bin/python scripts/trigger_cloud_run.py >> /srv/show-trace-tool/data/cron.log 2>&1
```

### 4.8 阿里云验证

1. `curl http://<server-ip>/health` 返回 `status=ok`。
2. 不带 token 请求 `/api/subscriptions` 返回 401。
3. 带 token 请求 `/api/subscriptions` 正常。
4. `POST /api/runs` 能触发一次稳定源采集。
5. `GET /api/runs` 能看到运行记录。
6. `GET /api/digests/today` 能看到云端生成的摘要。

---

## 5. 稳定源优先策略

第一版云端订阅建议：

- `showstart`: enabled
- `motianlun`: enabled
- `damai`: disabled

这已经写在 `config.cloud.yaml` 里。

大麦暂时不建议直接上云，原因：

- 需要真实 Chrome profile。
- 云服务器 IP 可能更容易触发风控。
- 滑块 / 验证码无法保证自动处理。

后续如果要尝试大麦或小红书，优先作为 BrowserSource / AssistedSource 单独做，不要让它们影响稳定源每日摘要。

---

## 6. 本机困难源同步到云端

云端 ECS 负责稳定源每日抓取。本机 Mac 负责困难源辅助抓取：

- 小红书：用 Chrome / Computer Use / 插件能力搜索和读取。
- 大麦：保留本机 Chrome profile、登录态和人工接管能力。
- 其他反爬失败的平台：先在本机完成信息获取。

本机脚本最终只需要产出标准事件 JSON，然后调用云端导入接口：

```bash
SHOW_TRACE_API_BASE_URL=http://<server-ip> \
API_TOKEN=<cloud-api-token> \
./venv/bin/python scripts/sync_local_events.py data/fixtures/local_import_events.json
```

云端接口：

```text
POST /api/events/import
```

行为：

- 使用同一套 `events.id` 去重规则。
- 新事件插入，重复事件只更新票价、开票时间、购买链接等易变字段。
- 写入 `runs` 表，方便追踪是云端自动采集还是本机同步。
- 默认 `notify=false`，需要导入后立即生成摘要 / 推送时再显式开启。

---

## 7. 官方文档依据

- [Render FastAPI 部署](https://render.com/docs/deploy-fastapi)：Web service 启动命令需要绑定 `0.0.0.0:$PORT`。
- [Render Cron Jobs](https://render.com/docs/cronjobs)：cron job 可定时运行命令，但不能挂载持久磁盘。
- [Render Persistent Disks](https://render.com/docs/disks)：持久磁盘可挂到 paid web service / private service / background worker。
- [阿里云 ECS](https://help.aliyun.com/product/25365.html/)：ECS 是 IaaS 云服务器，适合需要完整系统控制权的场景。
- [阿里云轻量应用服务器](https://help.aliyun.com/zh/simple-application-server/)：轻量应用服务器面向网站建设、开发测试、小型应用等轻量场景。
