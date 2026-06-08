// 演出雷达 — Card family screens (Direction B = card-light, C = card-dark)
// Themed entirely by the passed `t` token object.

(function () {
const { SF, ICONS, ScoreBadge, SourceTag, Poster, Screen, BigHeader } = window;
const R = () => window.RADAR;

// pill
function Pill({ t, children, on, accent }) {
  return (
    <span style={{
      fontFamily: SF, fontSize: 13, fontWeight: on ? 650 : 540,
      padding: '7px 13px', borderRadius: 999, whiteSpace: 'nowrap',
      background: on ? (accent || t.text) : t.card,
      color: on ? (accent ? t.accentText : t.bg) : t.text2,
      border: on ? 'none' : `1px solid ${t.sep}`,
    }}>{children}</span>
  );
}

function MetaRow({ t, icon, children, strong }) {
  return (
    <div style={{ display: 'flex', alignItems: 'center', gap: 8, color: strong ? t.text : t.text2, fontFamily: SF, fontSize: 14 }}>
      <span style={{ color: t.text3, display: 'flex', flexShrink: 0 }}>{ICONS[icon]({ size: 17, c: t.text3 })}</span>
      <span style={{ overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap' }}>{children}</span>
    </div>
  );
}

// ── Compact event card (list rows) ───────────────────────────
function EventCard({ ev, t }) {
  return (
    <div style={{
      display: 'flex', gap: 13, padding: 12, background: t.card,
      borderRadius: t.radius, boxShadow: t.shadow,
      border: t.dark ? `0.5px solid ${t.sep}` : 'none',
    }}>
      <Poster ev={ev} t={t} w={66} h={84} radius={11} label={false} />
      <div style={{ flex: 1, minWidth: 0, display: 'flex', flexDirection: 'column', gap: 6 }}>
        <div style={{ display: 'flex', justifyContent: 'space-between', gap: 8 }}>
          <span style={{ fontFamily: SF, fontSize: 11, fontWeight: 650, color: t.accent, letterSpacing: 0.2 }}>{ev.cat}</span>
          <ScoreBadge score={ev.score} t={t} />
        </div>
        <div style={{
          fontFamily: SF, fontSize: 15, fontWeight: 670, color: t.text, lineHeight: 1.25,
          letterSpacing: -0.2, display: '-webkit-box', WebkitLineClamp: 2, WebkitBoxOrient: 'vertical', overflow: 'hidden',
        }}>{ev.title}</div>
        <div style={{ marginTop: 'auto', display: 'flex', flexDirection: 'column', gap: 3 }}>
          <MetaRow t={t} icon="cal">{ev.date}</MetaRow>
          <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', gap: 8 }}>
            <span style={{ fontFamily: SF, fontSize: 14, fontWeight: 700, color: t.text }}>{ev.price}</span>
            <SourceTag source={ev.source} t={t} />
          </div>
        </div>
      </div>
    </div>
  );
}

function SectionLabel({ t, children, right }) {
  return (
    <div style={{ display: 'flex', alignItems: 'baseline', justifyContent: 'space-between', padding: '20px 20px 9px' }}>
      <span style={{ fontFamily: SF, fontSize: 19, fontWeight: 740, color: t.text, letterSpacing: -0.3 }}>{children}</span>
      {right && <span style={{ fontFamily: SF, fontSize: 13, fontWeight: 600, color: t.accent }}>{right}</span>}
    </div>
  );
}

// ── 1. TODAY ─────────────────────────────────────────────────
function TodayCard({ t }) {
  const d = R().today, picks = R().topPicks, keeps = R().events.filter(e => e.score.decision === 'keep');
  return (
    <Screen t={t} active="当日摘要">
      <BigHeader t={t} kicker={`${d.date.replaceAll('-', '.')} ${d.weekday}`} title="今日雷达"
        right={<div style={{ position: 'relative', display: 'flex' }}>{ICONS.bell({ size: 23, c: t.text2 })}
          <span style={{ position: 'absolute', top: -2, right: -2, width: 8, height: 8, borderRadius: 999, background: t.accent, border: `1.5px solid ${t.bg}` }} /></div>} />

      {/* summary banner */}
      <div style={{ margin: '6px 20px 0', padding: 16, borderRadius: t.radius, background: t.dark ? 'linear-gradient(135deg,#2A1411,#1A1816)' : 'linear-gradient(135deg,#FBE9E4,#FFFFFF)', border: t.dark ? `0.5px solid ${t.sep}` : 'none' }}>
        <div style={{ display: 'flex', alignItems: 'baseline', gap: 7 }}>
          <span style={{ fontFamily: SF, fontSize: 38, fontWeight: 800, color: t.accent, letterSpacing: -1 }}>{d.newCount}</span>
          <span style={{ fontFamily: SF, fontSize: 16, fontWeight: 600, color: t.text }}>条新演出</span>
        </div>
        <div style={{ fontFamily: SF, fontSize: 13.5, color: t.text2, marginTop: 2 }}>
          其中 <b style={{ color: t.text }}>{d.keepCount}</b> 条按你的口味值得关注 · 来自 {d.sources.join(' / ')}
        </div>
      </div>

      <SectionLabel t={t}>⚡ 最近就开始</SectionLabel>
      <div style={{ display: 'flex', gap: 13, overflowX: 'auto', padding: '0 20px 4px' }}>
        {picks.map(ev => (
          <div key={ev.id} style={{ width: 210, flexShrink: 0, background: t.card, borderRadius: t.radius, overflow: 'hidden', boxShadow: t.shadow, border: t.dark ? `0.5px solid ${t.sep}` : 'none' }}>
            <Poster ev={ev} t={t} h={112} radius={0} />
            <div style={{ padding: '11px 12px 13px' }}>
              <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: 6 }}>
                <span style={{ fontFamily: SF, fontSize: 11, fontWeight: 650, color: t.accent }}>{ev.cat}</span>
                <ScoreBadge score={ev.score} t={t} />
              </div>
              <div style={{ fontFamily: SF, fontSize: 14.5, fontWeight: 700, color: t.text, lineHeight: 1.25, height: 36, display: '-webkit-box', WebkitLineClamp: 2, WebkitBoxOrient: 'vertical', overflow: 'hidden', letterSpacing: -0.2 }}>{ev.title}</div>
              <div style={{ marginTop: 8, display: 'flex', alignItems: 'center', gap: 6, color: t.text2, fontFamily: SF, fontSize: 12.5 }}>
                {ICONS.cal({ size: 14, c: t.text3 })}{ev.date.split(' ')[0]}
              </div>
            </div>
          </div>
        ))}
      </div>

      <SectionLabel t={t} right="全部 ›">为你关注</SectionLabel>
      <div style={{ display: 'flex', flexDirection: 'column', gap: 11, padding: '0 20px' }}>
        {keeps.slice(0, 4).map(ev => <EventCard key={ev.id} ev={ev} t={t} />)}
      </div>
    </Screen>
  );
}

// ── 2. ALL EVENTS ────────────────────────────────────────────
function AllCard({ t }) {
  const evs = R().events;
  const types = [['全部', true], ['演唱会', false], ['音乐会', false], ['话剧', false], ['体育', false], ['Livehouse', false]];
  return (
    <Screen t={t} active="全部演出">
      <BigHeader t={t} title="全部演出" search />
      <div style={{ display: 'flex', gap: 8, overflowX: 'auto', padding: '14px 20px 4px' }}>
        {types.map(([l, on]) => <Pill key={l} t={t} on={on} accent={on ? t.accent : null}>{l}</Pill>)}
      </div>
      <div style={{ display: 'flex', gap: 8, padding: '8px 20px 4px', alignItems: 'center' }}>
        <span style={{ fontFamily: SF, fontSize: 12.5, color: t.text2 }}>口味</span>
        <Pill t={t} on>关注</Pill><Pill t={t}>待定</Pill><Pill t={t}>已过滤</Pill>
        <span style={{ marginLeft: 'auto', fontFamily: SF, fontSize: 12.5, color: t.text2 }}>{evs.length} 场 · 按日期</span>
      </div>
      <div style={{ display: 'flex', flexDirection: 'column', gap: 11, padding: '10px 20px 0' }}>
        {evs.slice(0, 7).map(ev => <EventCard key={ev.id} ev={ev} t={t} />)}
      </div>
    </Screen>
  );
}

// ── 3. DETAIL ────────────────────────────────────────────────
function DetailCard({ t }) {
  const ev = R().events[0]; // 周杰伦
  const sc = ev.score, meta = R().decisionMeta[sc.decision], c = t[sc.decision];
  return (
    <div style={{ position: 'absolute', inset: 0, background: t.bg, overflow: 'hidden' }}>
      <div style={{ position: 'absolute', inset: 0, overflowY: 'auto', paddingBottom: 96 }}>
        {/* hero poster */}
        <div style={{ position: 'relative' }}>
          <Poster ev={ev} t={t} h={252} radius={0} label={false} />
          <div style={{ position: 'absolute', inset: 0, background: t.dark ? 'linear-gradient(180deg,rgba(0,0,0,0.05) 30%,rgba(12,11,10,0.97))' : 'linear-gradient(180deg,rgba(255,255,255,0) 30%,rgba(244,241,238,0.97))' }} />
          {/* placeholder hint */}
          <div style={{ position: 'absolute', top: 112, left: 0, right: 0, textAlign: 'center', fontFamily: 'ui-monospace, "SF Mono", Menlo, monospace', fontSize: 11, letterSpacing: 0.4, color: t.dark ? 'rgba(255,255,255,0.42)' : 'rgba(40,28,20,0.42)' }}>主视觉 / poster</div>
          {/* nav pills */}
          <div style={{ position: 'absolute', top: 58, left: 16, right: 16, display: 'flex', justifyContent: 'space-between' }}>
            {[ICONS.chev({ size: 21, c: t.text }), ICONS.bell({ size: 20, c: t.text })].map((g, i) => (
              <div key={i} style={{ width: 38, height: 38, borderRadius: 999, background: t.dark ? 'rgba(40,36,32,0.7)' : 'rgba(255,255,255,0.8)', backdropFilter: 'blur(12px)', display: 'flex', alignItems: 'center', justifyContent: 'center', transform: i === 0 ? 'translateX(-1px)' : 'none' }}>{g}</div>
            ))}
          </div>
          {/* title block */}
          <div style={{ position: 'absolute', left: 20, right: 20, bottom: 14 }}>
            <div style={{ display: 'flex', gap: 8, marginBottom: 9 }}>
              <span style={{ fontFamily: SF, fontSize: 11.5, fontWeight: 700, color: t.accentText, background: t.accent, padding: '4px 9px', borderRadius: 999 }}>{ev.cat}</span>
              <span style={{ fontFamily: SF, fontSize: 11.5, fontWeight: 650, color: t.text, background: t.card, padding: '4px 9px', borderRadius: 999, border: `0.5px solid ${t.sep}` }}>{ev.status}</span>
            </div>
            <h1 style={{ margin: 0, fontFamily: SF, fontSize: 25, fontWeight: 800, color: t.text, lineHeight: 1.18, letterSpacing: -0.4 }}>{ev.title}</h1>
            {ev.artist && <div style={{ marginTop: 6, fontFamily: SF, fontSize: 15, fontWeight: 600, color: t.text2 }}>{ev.artist}</div>}
          </div>
        </div>

        <div style={{ padding: '4px 20px 0', display: 'flex', flexDirection: 'column', gap: 14 }}>
          {/* AI score card */}
          <div style={{ background: c.bg, borderRadius: t.radius, padding: 15 }}>
            <div style={{ display: 'flex', alignItems: 'center', gap: 9 }}>
              <div style={{ width: 42, height: 42, borderRadius: 999, background: c.fg, color: t.dark ? '#1A0E0B' : '#fff', display: 'flex', flexDirection: 'column', alignItems: 'center', justifyContent: 'center', flexShrink: 0 }}>
                <span style={{ fontFamily: SF, fontSize: 16, fontWeight: 800, lineHeight: 1 }}>{sc.match}</span>
              </div>
              <div style={{ flex: 1 }}>
                <div style={{ fontFamily: SF, fontSize: 15, fontWeight: 750, color: c.fg }}>雷达评分 · {meta.label}</div>
                <div style={{ fontFamily: SF, fontSize: 12.5, color: t.text2, marginTop: 1 }}>不确定度 {sc.uncertainty} · 分类 {sc.cat}</div>
              </div>
            </div>
            <div style={{ marginTop: 11, fontFamily: SF, fontSize: 13.5, color: t.text, lineHeight: 1.5 }}>{sc.reason}</div>
          </div>

          {/* facts */}
          <div style={{ background: t.card, borderRadius: t.radius, padding: '5px 15px', boxShadow: t.shadow, border: t.dark ? `0.5px solid ${t.sep}` : 'none' }}>
            {[['cal', '演出日期', ev.date], ['pin', '场馆', `${ev.city} · ${ev.venue}`], ['ticket', '票价', ev.price], ['clock', '开票', ev.onSale]].map(([ic, k, v], i, arr) => (
              <div key={k} style={{ display: 'flex', alignItems: 'center', gap: 11, padding: '12px 0', borderBottom: i < arr.length - 1 ? `0.5px solid ${t.sep}` : 'none' }}>
                {ICONS[ic]({ size: 19, c: t.text3 })}
                <span style={{ fontFamily: SF, fontSize: 13.5, color: t.text2, width: 60, flexShrink: 0 }}>{k}</span>
                <span style={{ fontFamily: SF, fontSize: 14.5, fontWeight: 600, color: t.text, textAlign: 'right', flex: 1 }}>{v}</span>
              </div>
            ))}
          </div>

          {/* discovered via */}
          <div style={{ display: 'flex', alignItems: 'center', gap: 8, padding: '0 4px' }}>
            {ICONS.search({ size: 16, c: t.text3 })}
            <span style={{ fontFamily: SF, fontSize: 13, color: t.text2 }}>在 <SourceTag source={ev.source} t={t} plain /> {ev.via} 发现</span>
          </div>
        </div>
      </div>

      {/* sticky CTA */}
      <div style={{ position: 'absolute', left: 0, right: 0, bottom: 0, padding: '12px 20px 30px', background: t.barBg, backdropFilter: 'blur(20px)', borderTop: `0.5px solid ${t.sep}`, display: 'flex', gap: 11, alignItems: 'center' }}>
        <div>
          <div style={{ fontFamily: SF, fontSize: 11, color: t.text2 }}>票价</div>
          <div style={{ fontFamily: SF, fontSize: 17, fontWeight: 800, color: t.text }}>{ev.price}</div>
        </div>
        <button style={{ flex: 1, height: 50, border: 'none', borderRadius: 14, background: t.accent, color: t.accentText, fontFamily: SF, fontSize: 16.5, fontWeight: 700, display: 'flex', alignItems: 'center', justifyContent: 'center', gap: 7 }}>
          {ICONS.ticket({ size: 19, c: t.accentText })}去大麦购票
        </button>
      </div>
    </div>
  );
}

// ── 4. SUBSCRIPTIONS ─────────────────────────────────────────
function SubsCard({ t }) {
  const s = R().subscription;
  return (
    <Screen t={t} active="订阅范围">
      <BigHeader t={t} title="我的订阅" right={<div style={{ width: 34, height: 34, borderRadius: 999, background: t.card, display: 'flex', alignItems: 'center', justifyContent: 'center', boxShadow: t.shadow }}>{ICONS.plus({ size: 21, c: t.accent })}</div>} />

      <SectionLabel t={t}>关注的艺人</SectionLabel>
      <div style={{ display: 'flex', flexWrap: 'wrap', gap: 9, padding: '0 20px' }}>
        {s.artists.map(a => (
          <span key={a} style={{ display: 'inline-flex', alignItems: 'center', gap: 7, background: t.card, borderRadius: 999, padding: '8px 13px 8px 9px', boxShadow: t.shadow, border: t.dark ? `0.5px solid ${t.sep}` : 'none' }}>
            <span style={{ width: 24, height: 24, borderRadius: 999, background: t.accent, color: t.accentText, fontFamily: SF, fontSize: 12, fontWeight: 700, display: 'flex', alignItems: 'center', justifyContent: 'center' }}>{a[0]}</span>
            <span style={{ fontFamily: SF, fontSize: 14.5, fontWeight: 650, color: t.text }}>{a}</span>
          </span>
        ))}
        <span style={{ display: 'inline-flex', alignItems: 'center', gap: 5, border: `1.5px dashed ${t.hair}`, borderRadius: 999, padding: '8px 14px', color: t.text2, fontFamily: SF, fontSize: 14, fontWeight: 600 }}>{ICONS.plus({ size: 16, c: t.text2 })}添加</span>
      </div>

      <SectionLabel t={t}>本地 · {s.local.city}</SectionLabel>
      <div style={{ padding: '0 20px' }}>
        <div style={{ background: t.card, borderRadius: t.radius, padding: 15, boxShadow: t.shadow, border: t.dark ? `0.5px solid ${t.sep}` : 'none' }}>
          <div style={{ fontFamily: SF, fontSize: 13, color: t.text2, marginBottom: 10 }}>在 {s.local.city} 追踪这些关键词的演出</div>
          <div style={{ display: 'flex', flexWrap: 'wrap', gap: 8 }}>
            {s.local.keywords.map(k => <Pill key={k} t={t} on accent={t.accent}>{k}</Pill>)}
            <span style={{ display: 'inline-flex', alignItems: 'center', gap: 4, color: t.text2, fontFamily: SF, fontSize: 13, fontWeight: 600, padding: '7px 11px', border: `1.5px dashed ${t.hair}`, borderRadius: 999 }}>{ICONS.plus({ size: 15, c: t.text2 })}关键词</span>
          </div>
        </div>
      </div>

      <SectionLabel t={t}>数据源</SectionLabel>
      <div style={{ padding: '0 20px' }}>
        <div style={{ background: t.card, borderRadius: t.radius, boxShadow: t.shadow, overflow: 'hidden', border: t.dark ? `0.5px solid ${t.sep}` : 'none' }}>
          {Object.entries(s.sources).map(([k, v], i, arr) => (
            <div key={k} style={{ display: 'flex', alignItems: 'center', gap: 12, padding: '13px 15px', borderBottom: i < arr.length - 1 ? `0.5px solid ${t.sep}` : 'none' }}>
              <SourceTag source={v.label} t={t} />
              <div style={{ flex: 1 }}>
                <div style={{ fontFamily: SF, fontSize: 15, fontWeight: 650, color: t.text }}>{v.label}</div>
                <div style={{ fontFamily: SF, fontSize: 12, color: t.text2 }}>{v.note}</div>
              </div>
              <Toggle on={v.enabled} t={t} />
            </div>
          ))}
        </div>
      </div>
    </Screen>
  );
}

function Toggle({ on, t }) {
  return (
    <div style={{ width: 50, height: 30, borderRadius: 999, background: on ? t.accent : (t.dark ? 'rgba(255,255,255,0.16)' : 'rgba(120,120,128,0.28)'), position: 'relative', flexShrink: 0, transition: 'background .2s' }}>
      <div style={{ position: 'absolute', top: 2, left: on ? 22 : 2, width: 26, height: 26, borderRadius: 999, background: '#fff', boxShadow: '0 1px 3px rgba(0,0,0,0.25)' }} />
    </div>
  );
}

// ── 5. PREFERENCES ───────────────────────────────────────────
function PrefsCard({ t }) {
  const p = R().profile;
  return (
    <Screen t={t} active="偏好管理">
      <BigHeader t={t} title="兴趣偏好" />

      {/* NL feedback */}
      <div style={{ padding: '8px 20px 0' }}>
        <div style={{ background: t.dark ? 'linear-gradient(135deg,#2A1411,#1A1816)' : 'linear-gradient(135deg,#FBE9E4,#FFF)', borderRadius: t.radius, padding: 16, border: t.dark ? `0.5px solid ${t.sep}` : 'none' }}>
          <div style={{ display: 'flex', alignItems: 'center', gap: 7, marginBottom: 9 }}>
            {ICONS.bolt({ size: 18, c: t.accent })}
            <span style={{ fontFamily: SF, fontSize: 15, fontWeight: 740, color: t.text }}>用大白话调教推荐</span>
          </div>
          <div style={{ background: t.card, borderRadius: 12, padding: '11px 13px', fontFamily: SF, fontSize: 14, color: t.text, lineHeight: 1.5, border: `0.5px solid ${t.sep}` }}>
            “多推点爵士现场，<span style={{ color: t.text3 }}>别再给我亲子类了</span>”
          </div>
          <div style={{ display: 'flex', justifyContent: 'flex-end', marginTop: 10 }}>
            <button style={{ border: 'none', background: t.accent, color: t.accentText, fontFamily: SF, fontSize: 14, fontWeight: 700, padding: '9px 18px', borderRadius: 999 }}>更新偏好</button>
          </div>
        </div>
      </div>

      <SectionLabel t={t}>想看的品类</SectionLabel>
      <div style={{ display: 'flex', flexWrap: 'wrap', gap: 8, padding: '0 20px' }}>
        {p.include_categories.map(c => (
          <span key={c} style={{ display: 'inline-flex', alignItems: 'center', gap: 5, background: t.keep.bg, color: t.keep.fg, fontFamily: SF, fontSize: 14, fontWeight: 650, padding: '8px 13px', borderRadius: 999 }}>{ICONS.check({ size: 15, c: t.keep.fg })}{c}</span>
        ))}
      </div>

      <SectionLabel t={t}>不想看的品类</SectionLabel>
      <div style={{ display: 'flex', flexWrap: 'wrap', gap: 8, padding: '0 20px' }}>
        {p.exclude_categories.map(c => (
          <span key={c} style={{ display: 'inline-flex', alignItems: 'center', gap: 5, background: t.filter.bg, color: t.filter.fg, fontFamily: SF, fontSize: 14, fontWeight: 650, padding: '8px 13px', borderRadius: 999, textDecoration: 'line-through', textDecorationColor: t.text3 }}>{c}</span>
        ))}
      </div>

      <SectionLabel t={t}>排序偏好 & 信号</SectionLabel>
      <div style={{ padding: '0 20px', display: 'flex', flexDirection: 'column', gap: 10 }}>
        <div style={{ background: t.card, borderRadius: t.radius, padding: 15, boxShadow: t.shadow, border: t.dark ? `0.5px solid ${t.sep}` : 'none' }}>
          {p.ranking_preferences.map((r, i) => (
            <div key={r} style={{ display: 'flex', gap: 8, alignItems: 'center', paddingTop: i ? 9 : 0 }}>
              <span style={{ color: t.accent, fontFamily: SF, fontWeight: 800 }}>{i + 1}</span>
              <span style={{ fontFamily: SF, fontSize: 14, color: t.text }}>{r}</span>
            </div>
          ))}
        </div>
        <div style={{ display: 'flex', flexWrap: 'wrap', gap: 7 }}>
          {p.positive_signals.map(s => <span key={s} style={{ fontFamily: SF, fontSize: 13, fontWeight: 600, color: t.keep.fg, background: t.keep.bg, padding: '6px 11px', borderRadius: 8 }}>＋ {s}</span>)}
          {p.negative_signals.map(s => <span key={s} style={{ fontFamily: SF, fontSize: 13, fontWeight: 600, color: t.text2, background: t.filter.bg, padding: '6px 11px', borderRadius: 8 }}>－ {s}</span>)}
        </div>
      </div>
    </Screen>
  );
}

// ── 6. RUNS ──────────────────────────────────────────────────
const RUN_STATUS = {
  success: ['成功', '#16997A'], partial_success: ['部分成功', '#C9882E'], failed: ['失败', '#D14343'],
};
function RunsCard({ t }) {
  const runs = R().runs;
  return (
    <Screen t={t} active="设置">
      <BigHeader t={t} title="采集记录" />
      {/* stat strip */}
      <div style={{ display: 'flex', gap: 11, padding: '8px 20px 0' }}>
        {[['今日新增', '8', t.accent], ['本周采集', '253', t.text], ['已通知', '14', t.text]].map(([k, v, c]) => (
          <div key={k} style={{ flex: 1, background: t.card, borderRadius: t.radius, padding: '13px 14px', boxShadow: t.shadow, border: t.dark ? `0.5px solid ${t.sep}` : 'none' }}>
            <div style={{ fontFamily: SF, fontSize: 26, fontWeight: 800, color: c, letterSpacing: -0.5 }}>{v}</div>
            <div style={{ fontFamily: SF, fontSize: 12, color: t.text2, marginTop: 1 }}>{k}</div>
          </div>
        ))}
      </div>

      <SectionLabel t={t}>运行历史</SectionLabel>
      <div style={{ padding: '0 20px', display: 'flex', flexDirection: 'column', gap: 10 }}>
        {runs.map(r => {
          const [lbl, col] = RUN_STATUS[r.status];
          return (
            <div key={r.id} style={{ background: t.card, borderRadius: t.radius, padding: 14, boxShadow: t.shadow, border: t.dark ? `0.5px solid ${t.sep}` : 'none' }}>
              <div style={{ display: 'flex', alignItems: 'center', gap: 9 }}>
                <span style={{ width: 9, height: 9, borderRadius: 999, background: col, flexShrink: 0 }} />
                <span style={{ fontFamily: SF, fontSize: 14.5, fontWeight: 700, color: t.text }}>{r.date} {r.time}</span>
                <span style={{ fontFamily: SF, fontSize: 11.5, fontWeight: 650, color: col, background: t.dark ? 'rgba(255,255,255,0.06)' : 'rgba(0,0,0,0.04)', padding: '2px 8px', borderRadius: 999 }}>{lbl}</span>
                <span style={{ marginLeft: 'auto', fontFamily: SF, fontSize: 11.5, color: t.text3, fontWeight: 600, textTransform: 'uppercase', letterSpacing: 0.3 }}>{r.trigger}</span>
              </div>
              <div style={{ display: 'flex', gap: 16, marginTop: 11 }}>
                {[['抓取', r.raw], ['抽取', r.extracted], ['新增', r.fresh], ['通知', r.notified]].map(([k, v]) => (
                  <div key={k}><span style={{ fontFamily: SF, fontSize: 16, fontWeight: 750, color: k === '新增' && v > 0 ? t.accent : t.text }}>{v}</span><span style={{ fontFamily: SF, fontSize: 11.5, color: t.text2, marginLeft: 4 }}>{k}</span></div>
                ))}
              </div>
              {r.err && <div style={{ marginTop: 10, fontFamily: 'ui-monospace, SF Mono, monospace', fontSize: 11.5, color: RUN_STATUS.failed[1], background: t.dark ? 'rgba(209,67,67,0.1)' : 'rgba(209,67,67,0.07)', padding: '7px 9px', borderRadius: 8 }}>⚠ {r.err}</div>}
            </div>
          );
        })}
      </div>
    </Screen>
  );
}

// ── 7. SETTINGS ──────────────────────────────────────────────
function SettingsRow({ t, icon, title, sub, right, last, accentIcon }) {
  return (
    <div>
      <div style={{ display: 'flex', alignItems: 'center', gap: 12, padding: '13px 15px' }}>
        {icon && <span style={{ display: 'flex', flexShrink: 0, color: accentIcon ? t.accent : t.text3 }}>{ICONS[icon]({ size: 19, c: accentIcon ? t.accent : t.text3 })}</span>}
        <div style={{ flex: 1, minWidth: 0 }}>
          <div style={{ fontFamily: SF, fontSize: 15.5, fontWeight: 600, color: t.text }}>{title}</div>
          {sub && <div style={{ fontFamily: SF, fontSize: 12, color: t.text2, marginTop: 1 }}>{sub}</div>}
        </div>
        <div style={{ display: 'flex', alignItems: 'center', gap: 7, flexShrink: 0 }}>{right}</div>
      </div>
      {!last && <div style={{ height: 0.5, background: t.sep, marginLeft: icon ? 46 : 15 }} />}
    </div>
  );
}
function ThemeSeg({ t }) {
  const items = ['跟随系统', '浅色', '深色'];
  const on = t.dark ? '深色' : '浅色';
  return (
    <div style={{ background: t.dark ? 'rgba(255,255,255,0.08)' : 'rgba(118,118,128,0.12)', borderRadius: 9, padding: 2, display: 'flex' }}>
      {items.map(l => (
        <span key={l} style={{ padding: '5px 11px', borderRadius: 7, fontFamily: SF, fontSize: 12.5, fontWeight: l === on ? 650 : 540, color: t.text, background: l === on ? t.card : 'transparent', boxShadow: l === on ? '0 1px 2px rgba(0,0,0,0.18)' : 'none' }}>{l}</span>
      ))}
    </div>
  );
}
function SettingsCard({ t }) {
  const last = R().runs[0]; // today 10:00 success
  const [lbl, col] = RUN_STATUS[last.status];
  const chev = ICONS.chev({ size: 16, c: t.text3 });
  const Card = ({ children }) => <div style={{ margin: '0 20px', background: t.card, borderRadius: t.radius, overflow: 'hidden', boxShadow: t.shadow, border: t.dark ? `0.5px solid ${t.sep}` : 'none' }}>{children}</div>;
  return (
    <Screen t={t} active="设置">
      <BigHeader t={t} title="设置" />

      {/* account / profile */}
      <div style={{ padding: '6px 20px 0' }}>
        <div style={{ display: 'flex', alignItems: 'center', gap: 13, background: t.card, borderRadius: t.radius, padding: 15, boxShadow: t.shadow, border: t.dark ? `0.5px solid ${t.sep}` : 'none' }}>
          <div style={{ width: 46, height: 46, borderRadius: 999, background: t.accent, color: t.accentText, fontFamily: SF, fontSize: 18, fontWeight: 800, display: 'flex', alignItems: 'center', justifyContent: 'center', flexShrink: 0 }}>沪</div>
          <div style={{ flex: 1 }}>
            <div style={{ fontFamily: SF, fontSize: 17, fontWeight: 740, color: t.text }}>上海 · 我的雷达</div>
            <div style={{ fontFamily: SF, fontSize: 12.5, color: t.text2, marginTop: 1 }}>4 位关注艺人 · 2 个数据源开启</div>
          </div>
          {chev}
        </div>
      </div>

      <SectionLabel t={t}>外观</SectionLabel>
      <Card><SettingsRow t={t} icon="prefs" title="主题" right={<ThemeSeg t={t} />} last /></Card>

      <SectionLabel t={t}>通知</SectionLabel>
      <Card>
        <SettingsRow t={t} icon="bell" title="开票提醒" sub="即将开票的演出提前推送" right={<Toggle on t={t} />} />
        <SettingsRow t={t} icon="today" title="每日摘要推送" sub="每天 09:00 · 仅「关注」级" right={<Toggle on t={t} />} />
        <SettingsRow t={t} icon="ticket" title="价格变动提醒" sub="关注的演出降价时通知" right={<Toggle on={false} t={t} />} last />
      </Card>

      <SectionLabel t={t}>数据采集</SectionLabel>
      <Card>
        <SettingsRow t={t} icon="runs" title="采集记录" accentIcon
          sub={`最近一次 ${last.date} ${last.time}`}
          right={<><span style={{ display: 'inline-flex', alignItems: 'center', gap: 5, fontFamily: SF, fontSize: 12, fontWeight: 600, color: col }}><span style={{ width: 7, height: 7, borderRadius: 999, background: col }} />{lbl}</span>{chev}</>} />
        <SettingsRow t={t} icon="clock" title="采集频率" right={<><span style={{ fontFamily: SF, fontSize: 14, color: t.text2 }}>每日 2 次</span>{chev}</>} />
        <SettingsRow t={t} icon="subs" title="管理数据源" sub="大麦 / 秀动 已开启 · 摩天轮 关闭" right={chev} last />
      </Card>

      <SectionLabel t={t}>关于</SectionLabel>
      <Card>
        <SettingsRow t={t} title="给个反馈" right={chev} />
        <SettingsRow t={t} title="隐私与数据" right={chev} />
        <SettingsRow t={t} title="版本" right={<span style={{ fontFamily: SF, fontSize: 14, color: t.text3 }}>1.0.3 (42)</span>} last />
      </Card>
    </Screen>
  );
}

window.CardScreens = { TodayCard, AllCard, DetailCard, SubsCard, PrefsCard, RunsCard, SettingsCard };
})();
