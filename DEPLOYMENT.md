# Cloud Deployment

Phase 4 goal: run the stable sources in the cloud first, while keeping browser-heavy
sources optional.

Recommended first deployment target: Render.

Why this shape:

- The API is a FastAPI web service.
- SQLite and generated digests need persistent storage.
- Render cron jobs cannot attach the same persistent disk as the web service, so
  the cron job should trigger the web API. The web service then runs the pipeline
  and writes to its own disk-backed `data/` directory.
- The first cloud config disables `damai`, because it needs a real Chrome profile
  and is more sensitive to cloud IP / captcha risk.

## Files

- `render.yaml` — Render Blueprint for the API web service and daily cron trigger.
- `config.cloud.yaml` — default cloud seed config with `damai.enabled: false`.
- `scripts/trigger_cloud_run.py` — cron helper that calls `POST /api/runs`.
- `.env.example` — cloud environment variable reference.

## Required Environment Variables

Set these on the Render web service:

```env
API_TOKEN=<long random token>
DEEPSEEK_API_KEY=<deepseek key>
SHOW_TRACE_DATA_DIR=/var/data/show-trace-tool
SHOW_TRACE_CONFIG_PATH=config.cloud.yaml
```

Optional notification variables:

```env
FEISHU_WEBHOOK_URL=
FEISHU_APP_ID=
FEISHU_APP_SECRET=
FEISHU_RECEIVE_ID=
FEISHU_RECEIVE_ID_TYPE=chat_id
```

Set these on the Render cron job:

```env
API_TOKEN=<same token as web service>
SHOW_TRACE_API_BASE_URL=https://<your-render-service>.onrender.com
SHOW_TRACE_RUN_FIXTURE=false
SHOW_TRACE_RUN_NOTIFY=true
```

## Render Setup

1. Create a Render Blueprint from this repository.
2. Use `render.yaml`.
3. Fill prompted secrets:
   - `API_TOKEN`
   - `DEEPSEEK_API_KEY`
   - optional Feishu values
   - `SHOW_TRACE_API_BASE_URL` for the cron job after the web service URL exists
4. Confirm the web service has a persistent disk mounted at:

   ```text
   /var/data/show-trace-tool
   ```

5. Open:

   ```text
   https://<your-render-service>.onrender.com/health
   ```

6. Test a protected endpoint:

   ```bash
   curl -H "Authorization: Bearer $API_TOKEN" \
     https://<your-render-service>.onrender.com/api/subscriptions
   ```

7. Trigger one cloud run:

   ```bash
   curl -X POST https://<your-render-service>.onrender.com/api/runs \
     -H "Authorization: Bearer $API_TOKEN" \
     -H "Content-Type: application/json" \
     -d '{"fixture": false, "notify": true}'
   ```

8. Check run records:

   ```bash
   curl -H "Authorization: Bearer $API_TOKEN" \
     https://<your-render-service>.onrender.com/api/runs
   ```

## Stable-Source First Policy

The first cloud deployment should use:

- `showstart`: enabled
- `motianlun`: enabled
- `damai`: disabled

That is encoded in `config.cloud.yaml`. After the database is initialized, update
the subscription through `PUT /api/subscriptions`.

If a cloud run must force-disable a source regardless of DB config, set:

```env
SHOW_TRACE_DISABLED_SOURCES=damai
```

## Notes From Official Render Docs

- Web services are publicly reachable and must bind to `0.0.0.0` on `$PORT`.
- Cron schedules use UTC.
- Cron jobs can run periodic commands, but they cannot attach persistent disks.
- Persistent disks can be attached to paid web services, private services, and
  background workers.

## Next Phase 4 Verification

After deploying:

1. Confirm `/health` is public.
2. Confirm `/api/*` rejects requests without `Authorization`.
3. Confirm `GET /api/subscriptions` shows only stable sources enabled.
4. Trigger `POST /api/runs`.
5. Confirm `GET /api/runs` shows a `success` or `partial_success` run.
6. Confirm `GET /api/digests/today` returns the generated digest.
