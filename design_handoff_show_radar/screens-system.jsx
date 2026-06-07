// 演出雷达 — System family screens (Direction A = iOS native grouped lists)
// Light, restrained, Apple-Settings flavour. Themed by `t` (system).

(function () {
const { SF, ICONS, ScoreBadge, SourceTag, Poster, Screen, BigHeader } = window;
const R = () => window.RADAR;
const GR = 18; // grouped inset radius

function Group({ t, header, footer, children }) {
  return (
    <div style={{ padding: '0 16px' }}>
      {header && <div style={{ fontFamily: SF, fontSize: 13, color: t.text2, padding: '18px 14px 7px', letterSpacing: -0.08 }}>{header}</div>}
      <div style={{ background: t.card, borderRadius: GR, overflow: 'hidden' }}>{children}</div>
      {footer && <div style={{ fontFamily: SF, fontSize: 12.5, color: t.text2, padding: '7px 14px 0', lineHeight: 1.4 }}>{footer}</div>}
    </div>
  );
}
function Sep({ t, inset = 16 }) { return <div style={{ height: 0.5, background: t.sep, marginLeft: inset }} />; }

// event row (system)
function Row({ ev, t, last }) {
  return (
    <div>
      <div style={{ display: 'flex', alignItems: 'center', gap: 12, padding: '10px 14px' }}>
        <Poster ev={ev} t={t} w={46} h={46} radius={10} label={false} />
        <div style={{ flex: 1, minWidth: 0 }}>
          <div style={{ fontFamily: SF, fontSize: 15.5, fontWeight: 600, color: t.text, letterSpacing: -0.3, lineHeight: 1.25, display: '-webkit-box', WebkitLineClamp: 1, WebkitBoxOrient: 'vertical', overflow: 'hidden' }}>{ev.title}</div>
          <div style={{ fontFamily: SF, fontSize: 13, color: t.text2, marginTop: 2, overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap' }}>{ev.date.split(' ')[0]} · {ev.venue}</div>
          <div style={{ display: 'flex', alignItems: 'center', gap: 8, marginTop: 5 }}>
            <span style={{ fontFamily: SF, fontSize: 13, fontWeight: 700, color: t.text }}>{ev.price}</span>
            <SourceTag source={ev.source} t={t} />
          </div>
        </div>
        <div style={{ display: 'flex', flexDirection: 'column', alignItems: 'flex-end', gap: 6 }}>
          <ScoreBadge score={ev.score} t={t} />
          {ICONS.chev({ size: 15, c: t.text3 })}
        </div>
      </div>
      {!last && <Sep t={t} inset={72} />}
    </div>
  );
}

// ── 1. TODAY ─────────────────────────────────────────────────
function TodaySys({ t }) {
  const d = R().today, picks = R().topPicks, keeps = R().events.filter(e => e.score.decision === 'keep');
  return (
    <Screen t={t} active="今日">
      <BigHeader t={t} kicker={`${d.date.replaceAll('-', '.')} ${d.weekday}`} title="今日雷达"
        right={<div style={{ position: 'relative', display: 'flex' }}>{ICONS.bell({ size: 23, c: t.accent })}<span style={{ position: 'absolute', top: -2, right: -2, width: 8, height: 8, borderRadius: 999, background: t.accent, border: `1.5px solid ${t.bg}` }} /></div>} />

      {/* summary */}
      <div style={{ padding: '4px 16px 0' }}>
        <div style={{ background: t.card, borderRadius: GR, padding: '15px 17px', display: 'flex', alignItems: 'center', gap: 14 }}>
          <div style={{ textAlign: 'center' }}>
            <div style={{ fontFamily: SF, fontSize: 34, fontWeight: 800, color: t.accent, lineHeight: 1, letterSpacing: -1 }}>{d.newCount}</div>
            <div style={{ fontFamily: SF, fontSize: 11, color: t.text2 }}>新演出</div>
          </div>
          <div style={{ width: 0.5, alignSelf: 'stretch', background: t.sep }} />
          <div style={{ fontFamily: SF, fontSize: 13.5, color: t.text2, lineHeight: 1.5 }}>
            <b style={{ color: t.text }}>{d.keepCount}</b> 条值得关注，已为你按口味排序。<br />来自 {d.sources.join(' / ')} · 今早 10:00 采集
          </div>
        </div>
      </div>

      <Group t={t} header="⚡ 最近就开始">
        {picks.map((ev, i) => <Row key={ev.id} ev={ev} t={t} last={i === picks.length - 1} />)}
      </Group>
      <Group t={t} header="为你关注" footer={`共 ${keeps.length} 条命中订阅艺人或关注品类`}>
        {keeps.slice(0, 4).map((ev, i, a) => <Row key={ev.id} ev={ev} t={t} last={i === a.length - 1} />)}
      </Group>
    </Screen>
  );
}

// ── 2. ALL ───────────────────────────────────────────────────
function Segmented({ t, items }) {
  return (
    <div style={{ margin: '12px 16px 0', background: t.dark ? 'rgba(255,255,255,0.08)' : 'rgba(118,118,128,0.12)', borderRadius: 9, padding: 2, display: 'flex' }}>
      {items.map(([l, on]) => (
        <div key={l} style={{ flex: 1, textAlign: 'center', padding: '6px 0', borderRadius: 7, background: on ? t.card : 'transparent', boxShadow: on ? '0 1px 3px rgba(0,0,0,0.12)' : 'none', fontFamily: SF, fontSize: 13.5, fontWeight: on ? 650 : 540, color: t.text }}>{l}</div>
      ))}
    </div>
  );
}
function AllSys({ t }) {
  const evs = R().events;
  return (
    <Screen t={t} active="全部">
      <BigHeader t={t} title="全部演出" search />
      <Segmented t={t} items={[['关注', true], ['待定', false], ['已过滤', false], ['全部', false]]} />
      <div style={{ display: 'flex', gap: 8, overflowX: 'auto', padding: '12px 16px 2px' }}>
        {['演唱会', '音乐会', '话剧', '体育', 'Livehouse'].map((c, i) => (
          <span key={c} style={{ fontFamily: SF, fontSize: 13, fontWeight: i === 0 ? 650 : 540, padding: '6px 12px', borderRadius: 999, background: i === 0 ? t.accent : t.card, color: i === 0 ? t.accentText : t.text2, whiteSpace: 'nowrap' }}>{c}</span>
        ))}
      </div>
      <Group t={t} header={`${evs.length} 场 · 按日期`}>
        {evs.slice(0, 7).map((ev, i, a) => <Row key={ev.id} ev={ev} t={t} last={i === a.length - 1} />)}
      </Group>
    </Screen>
  );
}

// ── 3. DETAIL ────────────────────────────────────────────────
function DetailSys({ t }) {
  const ev = R().events[0];
  const sc = ev.score, meta = R().decisionMeta[sc.decision], c = t[sc.decision];
  return (
    <div style={{ position: 'absolute', inset: 0, background: t.bg, overflow: 'hidden' }}>
      {/* nav */}
      <div style={{ position: 'absolute', top: 0, left: 0, right: 0, zIndex: 30, paddingTop: 54, paddingBottom: 9, background: t.barBg, backdropFilter: 'blur(20px)', borderBottom: `0.5px solid ${t.sep}`, display: 'flex', alignItems: 'center', padding: '54px 14px 9px' }}>
        <span style={{ display: 'flex', alignItems: 'center', color: t.accent, fontFamily: SF, fontSize: 16 }}>{ICONS.chev({ size: 20, c: t.accent })}<span style={{ marginLeft: -2 }}>今日</span></span>
        <span style={{ flex: 1, textAlign: 'center', fontFamily: SF, fontSize: 16, fontWeight: 650, color: t.text, paddingRight: 36, overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap' }}>演出详情</span>
      </div>
      <div style={{ position: 'absolute', inset: 0, overflowY: 'auto', paddingTop: 96, paddingBottom: 96 }}>
        {/* hero card */}
        <div style={{ padding: '0 16px' }}>
          <div style={{ background: t.card, borderRadius: GR, overflow: 'hidden' }}>
            <Poster ev={ev} t={t} h={170} radius={0} />
            <div style={{ padding: 16 }}>
              <div style={{ display: 'flex', gap: 7, marginBottom: 9 }}>
                <span style={{ fontFamily: SF, fontSize: 11.5, fontWeight: 700, color: t.accentText, background: t.accent, padding: '3px 9px', borderRadius: 999 }}>{ev.cat}</span>
                <span style={{ fontFamily: SF, fontSize: 11.5, fontWeight: 600, color: t.text2, background: t.card2, padding: '3px 9px', borderRadius: 999 }}>{ev.status}</span>
              </div>
              <h1 style={{ margin: 0, fontFamily: SF, fontSize: 21, fontWeight: 780, color: t.text, lineHeight: 1.22, letterSpacing: -0.4 }}>{ev.title}</h1>
              {ev.artist && <div style={{ marginTop: 6, fontFamily: SF, fontSize: 14.5, fontWeight: 600, color: t.text2 }}>{ev.artist}</div>}
            </div>
          </div>
        </div>

        {/* AI score */}
        <Group t={t} header="雷达评分">
          <div style={{ display: 'flex', alignItems: 'center', gap: 12, padding: '13px 14px' }}>
            <div style={{ width: 44, height: 44, borderRadius: 999, background: c.bg, color: c.fg, fontFamily: SF, fontSize: 17, fontWeight: 800, display: 'flex', alignItems: 'center', justifyContent: 'center', flexShrink: 0 }}>{sc.match}</div>
            <div style={{ flex: 1 }}>
              <div style={{ fontFamily: SF, fontSize: 15.5, fontWeight: 700, color: t.text }}>{meta.label} · 分类 {sc.cat}</div>
              <div style={{ fontFamily: SF, fontSize: 13, color: t.text2, marginTop: 2 }}>{sc.reason}</div>
            </div>
          </div>
        </Group>

        {/* facts */}
        <Group t={t}>
          {[['cal', '日期', ev.date], ['pin', '场馆', `${ev.city} · ${ev.venue}`], ['ticket', '票价', ev.price], ['clock', '开票', ev.onSale]].map(([ic, k, v], i, a) => (
            <div key={k}>
              <div style={{ display: 'flex', alignItems: 'center', gap: 11, padding: '12px 14px' }}>
                {ICONS[ic]({ size: 19, c: t.accent })}
                <span style={{ fontFamily: SF, fontSize: 15, color: t.text, width: 52, flexShrink: 0 }}>{k}</span>
                <span style={{ fontFamily: SF, fontSize: 14.5, fontWeight: 600, color: t.text2, textAlign: 'right', flex: 1 }}>{v}</span>
              </div>
              {i < a.length - 1 && <Sep t={t} inset={45} />}
            </div>
          ))}
        </Group>
        <Group t={t} footer={`在 ${ev.source} ${ev.via} 发现 · 来源 ID ${ev.id}`}>
          <div style={{ display: 'flex', alignItems: 'center', gap: 10, padding: '12px 14px' }}>
            {ICONS.search({ size: 18, c: t.text3 })}
            <span style={{ fontFamily: SF, fontSize: 15, color: t.text }}>在哪发现的</span>
            <span style={{ marginLeft: 'auto' }}><SourceTag source={ev.source} t={t} /></span>
          </div>
        </Group>
      </div>
      {/* CTA */}
      <div style={{ position: 'absolute', left: 0, right: 0, bottom: 0, padding: '12px 16px 30px', background: t.barBg, backdropFilter: 'blur(20px)', borderTop: `0.5px solid ${t.sep}` }}>
        <button style={{ width: '100%', height: 50, border: 'none', borderRadius: 14, background: t.accent, color: t.accentText, fontFamily: SF, fontSize: 16.5, fontWeight: 700, display: 'flex', alignItems: 'center', justifyContent: 'center', gap: 7 }}>{ICONS.ticket({ size: 19, c: t.accentText })}去大麦购票 · {ev.price}</button>
      </div>
    </div>
  );
}

// ── 4. SUBSCRIPTIONS ─────────────────────────────────────────
function Toggle({ on, t }) {
  return (
    <div style={{ width: 50, height: 30, borderRadius: 999, background: on ? t.accent : 'rgba(120,120,128,0.28)', position: 'relative', flexShrink: 0 }}>
      <div style={{ position: 'absolute', top: 2, left: on ? 22 : 2, width: 26, height: 26, borderRadius: 999, background: '#fff', boxShadow: '0 1px 3px rgba(0,0,0,0.25)' }} />
    </div>
  );
}
function SubsSys({ t }) {
  const s = R().subscription;
  return (
    <Screen t={t} active="订阅">
      <BigHeader t={t} title="我的订阅" right={ICONS.plus({ size: 25, c: t.accent })} />
      <Group t={t} header="关注的艺人">
        {s.artists.map((a, i, arr) => (
          <div key={a}>
            <div style={{ display: 'flex', alignItems: 'center', gap: 12, padding: '11px 14px' }}>
              <span style={{ width: 30, height: 30, borderRadius: 999, background: t.accent, color: t.accentText, fontFamily: SF, fontSize: 14, fontWeight: 700, display: 'flex', alignItems: 'center', justifyContent: 'center' }}>{a[0]}</span>
              <span style={{ flex: 1, fontFamily: SF, fontSize: 16, fontWeight: 500, color: t.text }}>{a}</span>
              <span style={{ fontFamily: SF, fontSize: 13, color: t.text2 }}>全国</span>
              {ICONS.chev({ size: 15, c: t.text3 })}
            </div>
            {i < arr.length - 1 && <Sep t={t} inset={56} />}
          </div>
        ))}
      </Group>
      <Group t={t} header={`本地 · ${s.local.city}`} footer="在所在城市追踪这些关键词的演出 / 展览 / 活动">
        <div style={{ padding: '12px 14px', display: 'flex', flexWrap: 'wrap', gap: 8 }}>
          {s.local.keywords.map(k => <span key={k} style={{ fontFamily: SF, fontSize: 14, fontWeight: 600, color: t.accent, background: t.keep.bg, padding: '6px 12px', borderRadius: 999 }}>{k}</span>)}
          <span style={{ fontFamily: SF, fontSize: 14, fontWeight: 600, color: t.text2, padding: '6px 12px', borderRadius: 999, border: `1.5px dashed ${t.hair}` }}>＋ 关键词</span>
        </div>
      </Group>
      <Group t={t} header="数据源">
        {Object.entries(s.sources).map(([k, v], i, arr) => (
          <div key={k}>
            <div style={{ display: 'flex', alignItems: 'center', gap: 12, padding: '11px 14px' }}>
              <span style={{ width: 9, height: 9, borderRadius: 999, background: { '大麦': '#E0533D', '秀动': '#2F6DF0', '摩天轮': '#16997A' }[v.label] }} />
              <div style={{ flex: 1 }}>
                <div style={{ fontFamily: SF, fontSize: 16, color: t.text }}>{v.label}</div>
                <div style={{ fontFamily: SF, fontSize: 12, color: t.text2 }}>{v.note}</div>
              </div>
              <Toggle on={v.enabled} t={t} />
            </div>
            {i < arr.length - 1 && <Sep t={t} inset={35} />}
          </div>
        ))}
      </Group>
    </Screen>
  );
}

// ── 5. PREFERENCES ───────────────────────────────────────────
function PrefsSys({ t }) {
  const p = R().profile;
  return (
    <Screen t={t} active="偏好">
      <BigHeader t={t} title="兴趣偏好" />
      <Group t={t} header="用大白话调教推荐" footer="自然语言反馈会合并进结构化偏好，不会删除你没否定的项目。">
        <div style={{ padding: 14 }}>
          <div style={{ background: t.card2, borderRadius: 12, padding: '11px 13px', fontFamily: SF, fontSize: 14.5, color: t.text, lineHeight: 1.5 }}>多推点爵士现场，<span style={{ color: t.text3 }}>别再给我亲子类了</span></div>
          <div style={{ display: 'flex', justifyContent: 'flex-end', marginTop: 11 }}>
            <button style={{ border: 'none', background: t.accent, color: t.accentText, fontFamily: SF, fontSize: 14.5, fontWeight: 650, padding: '8px 18px', borderRadius: 999 }}>更新偏好</button>
          </div>
        </div>
      </Group>
      <Group t={t} header="想看的品类">
        <div style={{ padding: '12px 14px', display: 'flex', flexWrap: 'wrap', gap: 8 }}>
          {p.include_categories.map(c => <span key={c} style={{ display: 'inline-flex', alignItems: 'center', gap: 5, fontFamily: SF, fontSize: 14, fontWeight: 600, color: t.keep.fg, background: t.keep.bg, padding: '6px 12px', borderRadius: 999 }}>{ICONS.check({ size: 14, c: t.keep.fg })}{c}</span>)}
        </div>
      </Group>
      <Group t={t} header="不想看的品类">
        <div style={{ padding: '12px 14px', display: 'flex', flexWrap: 'wrap', gap: 8 }}>
          {p.exclude_categories.map(c => <span key={c} style={{ fontFamily: SF, fontSize: 14, fontWeight: 600, color: t.text2, background: t.filter.bg, padding: '6px 12px', borderRadius: 999, textDecoration: 'line-through', textDecorationColor: t.text3 }}>{c}</span>)}
        </div>
      </Group>
      <Group t={t} header="排序偏好">
        {p.ranking_preferences.map((r, i, a) => (
          <div key={r}><div style={{ display: 'flex', gap: 10, alignItems: 'center', padding: '11px 14px' }}><span style={{ color: t.accent, fontFamily: SF, fontWeight: 800, fontSize: 15 }}>{i + 1}</span><span style={{ fontFamily: SF, fontSize: 15, color: t.text }}>{r}</span></div>{i < a.length - 1 && <Sep t={t} inset={40} />}</div>
        ))}
      </Group>
      <Group t={t} header="信号">
        <div style={{ padding: '12px 14px', display: 'flex', flexWrap: 'wrap', gap: 7 }}>
          {p.positive_signals.map(s => <span key={s} style={{ fontFamily: SF, fontSize: 13, fontWeight: 600, color: t.keep.fg, background: t.keep.bg, padding: '6px 11px', borderRadius: 8 }}>＋ {s}</span>)}
          {p.negative_signals.map(s => <span key={s} style={{ fontFamily: SF, fontSize: 13, fontWeight: 600, color: t.text2, background: t.filter.bg, padding: '6px 11px', borderRadius: 8 }}>－ {s}</span>)}
        </div>
      </Group>
    </Screen>
  );
}

// ── 6. RUNS ──────────────────────────────────────────────────
const RS = { success: ['成功', '#16997A'], partial_success: ['部分成功', '#C9882E'], failed: ['失败', '#D14343'] };
function RunsSys({ t }) {
  const runs = R().runs;
  return (
    <Screen t={t} active="记录">
      <BigHeader t={t} title="采集记录" />
      <Group t={t} header="本周概览">
        <div style={{ display: 'flex', padding: '14px 6px' }}>
          {[['8', '今日新增', t.accent], ['253', '本周采集', t.text], ['14', '已通知', t.text]].map(([v, k, c], i) => (
            <React.Fragment key={k}>
              {i > 0 && <div style={{ width: 0.5, background: t.sep }} />}
              <div style={{ flex: 1, textAlign: 'center' }}>
                <div style={{ fontFamily: SF, fontSize: 26, fontWeight: 800, color: c, letterSpacing: -0.5 }}>{v}</div>
                <div style={{ fontFamily: SF, fontSize: 12, color: t.text2, marginTop: 1 }}>{k}</div>
              </div>
            </React.Fragment>
          ))}
        </div>
      </Group>
      <Group t={t} header="运行历史">
        {runs.map((r, i, a) => {
          const [lbl, col] = RS[r.status];
          return (
            <div key={r.id}>
              <div style={{ padding: '12px 14px' }}>
                <div style={{ display: 'flex', alignItems: 'center', gap: 9 }}>
                  <span style={{ width: 9, height: 9, borderRadius: 999, background: col }} />
                  <span style={{ fontFamily: SF, fontSize: 15, fontWeight: 600, color: t.text }}>{r.date} {r.time}</span>
                  <span style={{ fontFamily: SF, fontSize: 11.5, fontWeight: 650, color: col }}>{lbl}</span>
                  <span style={{ marginLeft: 'auto', fontFamily: SF, fontSize: 11, color: t.text3, fontWeight: 600, textTransform: 'uppercase' }}>{r.trigger}</span>
                </div>
                <div style={{ display: 'flex', gap: 15, marginTop: 8, paddingLeft: 18 }}>
                  {[['抓取', r.raw], ['抽取', r.extracted], ['新增', r.fresh], ['通知', r.notified]].map(([k, v]) => (
                    <div key={k}><span style={{ fontFamily: SF, fontSize: 15, fontWeight: 700, color: k === '新增' && v > 0 ? t.accent : t.text }}>{v}</span><span style={{ fontFamily: SF, fontSize: 11, color: t.text2, marginLeft: 3 }}>{k}</span></div>
                  ))}
                </div>
                {r.err && <div style={{ marginTop: 9, marginLeft: 18, fontFamily: 'ui-monospace, SF Mono, monospace', fontSize: 11, color: RS.failed[1] }}>⚠ {r.err}</div>}
              </div>
              {i < a.length - 1 && <Sep t={t} inset={14} />}
            </div>
          );
        })}
      </Group>
    </Screen>
  );
}

window.SysScreens = { TodaySys, AllSys, DetailSys, SubsSys, PrefsSys, RunsSys };
})();
