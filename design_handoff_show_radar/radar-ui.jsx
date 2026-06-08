// 演出雷达 — shared theme tokens + atoms (used by all 3 directions)
// Loaded after React/Babel. Exports to window.

const ACCENT = '#E0533D';      // coral (chosen accent)
const ACCENT_DK = '#FF6F57';   // brighter coral for dark

function radarTheme(kind) {
  // kind: 'system' | 'card-light' | 'card-dark'
  if (kind === 'card-dark') {
    return {
      kind, dark: true, accent: ACCENT_DK, accentText: '#1A0E0B',
      bg: '#0C0B0A', bg2: '#161412',
      card: '#1A1816', card2: '#231F1C',
      text: '#F5F1EE', text2: 'rgba(245,241,238,0.62)', text3: 'rgba(245,241,238,0.36)',
      sep: 'rgba(255,255,255,0.08)', hair: 'rgba(255,255,255,0.10)',
      keep:   { fg: '#FF8A72', bg: 'rgba(255,111,87,0.16)' },
      maybe:  { fg: '#E8C06B', bg: 'rgba(232,192,107,0.14)' },
      filter: { fg: 'rgba(245,241,238,0.4)', bg: 'rgba(255,255,255,0.06)' },
      barBg: 'rgba(18,16,14,0.82)', tabIdle: 'rgba(245,241,238,0.42)',
      shadow: '0 1px 2px rgba(0,0,0,0.4)', radius: 18,
    };
  }
  if (kind === 'card-light') {
    return {
      kind, dark: false, accent: ACCENT, accentText: '#fff',
      bg: '#F4F1EE', bg2: '#EDE8E3',
      card: '#FFFFFF', card2: '#F4F1EC',
      text: '#1C1715', text2: 'rgba(28,23,21,0.56)', text3: 'rgba(28,23,21,0.34)',
      sep: 'rgba(28,23,21,0.07)', hair: 'rgba(28,23,21,0.08)',
      keep:   { fg: '#C0432F', bg: 'rgba(224,83,61,0.10)' },
      maybe:  { fg: '#9A6B17', bg: 'rgba(201,136,46,0.12)' },
      filter: { fg: 'rgba(28,23,21,0.4)', bg: 'rgba(28,23,21,0.05)' },
      barBg: 'rgba(255,255,255,0.82)', tabIdle: 'rgba(28,23,21,0.4)',
      shadow: '0 1px 3px rgba(60,40,30,0.06), 0 8px 24px rgba(60,40,30,0.05)', radius: 18,
    };
  }
  // system (iOS native, light)
  return {
    kind: 'system', dark: false, accent: ACCENT, accentText: '#fff',
    bg: '#F2F2F7', bg2: '#E9E9EE',
    card: '#FFFFFF', card2: '#F2F2F7',
    text: '#000000', text2: 'rgba(60,60,67,0.6)', text3: 'rgba(60,60,67,0.3)',
    sep: 'rgba(60,60,67,0.12)', hair: 'rgba(60,60,67,0.18)',
    keep:   { fg: '#C0432F', bg: 'rgba(224,83,61,0.12)' },
    maybe:  { fg: '#8A6D3B', bg: 'rgba(142,109,59,0.12)' },
    filter: { fg: 'rgba(60,60,67,0.5)', bg: 'rgba(120,120,128,0.12)' },
    barBg: 'rgba(249,249,249,0.84)', tabIdle: 'rgba(60,60,67,0.45)',
    shadow: 'none', radius: 26,
  };
}

const SF = '-apple-system, "SF Pro Text", system-ui, sans-serif';

// ── Icons (geometric, 1.8 stroke) ────────────────────────────
function Ic({ d, size = 22, c = 'currentColor', sw = 1.8, fill = 'none', vb = 24 }) {
  return (
    <svg width={size} height={size} viewBox={`0 0 ${vb} ${vb}`} fill={fill}
      stroke={fill === 'none' ? c : 'none'} strokeWidth={sw}
      strokeLinecap="round" strokeLinejoin="round">{d}</svg>
  );
}
const ICONS = {
  today: (p) => <Ic {...p} d={<><rect x="3" y="4.5" width="18" height="16" rx="3"/><path d="M3 9h18M8 2.5v4M16 2.5v4"/><circle cx="8.5" cy="14" r="1.4" fill="currentColor" stroke="none"/></>} />,
  list: (p) => <Ic {...p} d={<><path d="M8 6h12M8 12h12M8 18h12"/><circle cx="3.5" cy="6" r="1.3" fill="currentColor" stroke="none"/><circle cx="3.5" cy="12" r="1.3" fill="currentColor" stroke="none"/><circle cx="3.5" cy="18" r="1.3" fill="currentColor" stroke="none"/></>} />,
  subs: (p) => <Ic {...p} d={<><path d="M12 4l2.2 4.6 5 .7-3.6 3.5.9 5L12 15.9 7.5 17.8l.9-5L4.8 9.3l5-.7z"/></>} />,
  prefs: (p) => <Ic {...p} d={<><path d="M5 7h14M5 12h14M5 17h14"/><circle cx="9" cy="7" r="2.2" fill="var(--ic-bg)"/><circle cx="15" cy="12" r="2.2" fill="var(--ic-bg)"/><circle cx="8" cy="17" r="2.2" fill="var(--ic-bg)"/></>} />,
  runs: (p) => <Ic {...p} d={<><path d="M4 19V5M4 19h16"/><path d="M8 16l3.5-4 3 2.5L20 8"/></>} />,
  settings: (p) => <Ic {...p} d={<><circle cx="12" cy="12" r="3.4"/><path d="M19.4 12.9a7.6 7.6 0 000-1.8l1.9-1.5-1.9-3.3-2.3.9a7.3 7.3 0 00-1.5-.9l-.3-2.4H10l-.3 2.4a7.3 7.3 0 00-1.5.9l-2.3-.9L4 9.6l1.9 1.5a7.6 7.6 0 000 1.8L4 14.4l1.9 3.3 2.3-.9c.5.4 1 .7 1.5.9l.3 2.4h4l.3-2.4c.5-.2 1-.5 1.5-.9l2.3.9 1.9-3.3z"/></>} />,
  cal: (p) => <Ic {...p} d={<><rect x="3.5" y="5" width="17" height="15" rx="2.5"/><path d="M3.5 9.5h17M8 3v4M16 3v4"/></>} />,
  pin: (p) => <Ic {...p} d={<><path d="M12 21c4-4.5 7-8 7-11a7 7 0 10-14 0c0 3 3 6.5 7 11z"/><circle cx="12" cy="10" r="2.4"/></>} />,
  ticket: (p) => <Ic {...p} d={<><path d="M4 8a2 2 0 012-2h12a2 2 0 012 2 2 2 0 000 4 2 2 0 00-2 2v0a2 2 0 01-2 2H6a2 2 0 01-2-2 2 2 0 000-4 2 2 0 002-2z"/><path d="M14 6v12" strokeDasharray="1.5 2.5"/></>} />,
  bell: (p) => <Ic {...p} d={<><path d="M6 9a6 6 0 1112 0c0 5 1.5 7 1.5 7H4.5S6 14 6 9z"/><path d="M10 20a2 2 0 004 0"/></>} />,
  search: (p) => <Ic {...p} d={<><circle cx="11" cy="11" r="6.5"/><path d="M20 20l-4-4"/></>} />,
  chev: (p) => <Ic {...p} vb={24} d={<path d="M9 5l7 7-7 7"/>} />,
  star: (p) => <Ic {...p} fill="currentColor" sw={0} d={<path d="M12 3l2.5 5.4 5.9.7-4.4 4 1.2 5.8L12 16l-5.2 2.9 1.2-5.8-4.4-4 5.9-.7z"/>} />,
  bolt: (p) => <Ic {...p} fill="currentColor" sw={0} d={<path d="M13 2L4 14h6l-1 8 9-12h-6z"/>} />,
  check: (p) => <Ic {...p} d={<path d="M5 12.5l4.5 4.5L19 7"/>} />,
  plus: (p) => <Ic {...p} d={<path d="M12 5v14M5 12h14"/>} />,
  clock: (p) => <Ic {...p} d={<><circle cx="12" cy="12" r="8.5"/><path d="M12 7.5V12l3 2"/></>} />,
  x: (p) => <Ic {...p} d={<path d="M6 6l12 12M18 6L6 18"/>} />,
};

// ── Score badge (keep / maybe / filter + match) ──────────────
function ScoreBadge({ score, t, big = false }) {
  const meta = window.RADAR.decisionMeta[score.decision];
  const c = t[score.decision];
  return (
    <span style={{
      display: 'inline-flex', alignItems: 'center', gap: 5,
      background: c.bg, color: c.fg,
      fontFamily: SF, fontWeight: 650, letterSpacing: -0.2,
      fontSize: big ? 13 : 11.5, padding: big ? '5px 10px' : '3px 8px',
      borderRadius: 999, lineHeight: 1, whiteSpace: 'nowrap',
    }}>
      {score.decision === 'keep' && ICONS.star({ size: big ? 13 : 11, c: c.fg })}
      {meta.label}
      <span style={{ opacity: 0.62, fontWeight: 600 }}>{score.match}</span>
    </span>
  );
}

// ── Source tag ───────────────────────────────────────────────
function SourceTag({ source, t, plain = false }) {
  const tint = { '大麦': '#E0533D', '秀动': '#2F6DF0', '摩天轮': '#16997A' }[source] || t.text2;
  if (plain) return <span style={{ color: t.text2, fontFamily: SF, fontSize: 12 }}>{source}</span>;
  return (
    <span style={{
      display: 'inline-flex', alignItems: 'center', gap: 5,
      fontFamily: SF, fontSize: 11.5, fontWeight: 600, color: t.text2,
    }}>
      <span style={{ width: 6, height: 6, borderRadius: 999, background: tint }} />
      {source}
    </span>
  );
}

// ── Poster placeholder (striped, category-tinted) ────────────
const CAT_HUE = { '演唱会': 12, '音乐会': 268, 'Livehouse': 320, '话剧': 32, '体育': 152, '亲子': 200, '展览': 92 };
function Poster({ ev, t, w = '100%', h = 96, radius = 12, label = true }) {
  const hue = CAT_HUE[ev.cat] ?? 20;
  const a = t.dark ? 0.5 : 0.9, l1 = t.dark ? 22 : 90, l2 = t.dark ? 16 : 82;
  return (
    <div style={{
      width: w, height: h, borderRadius: radius, overflow: 'hidden',
      position: 'relative', flexShrink: 0,
      background: `repeating-linear-gradient(135deg, oklch(${l1}% 0.06 ${hue}) 0 9px, oklch(${l2}% 0.07 ${hue}) 9px 18px)`,
    }}>
      <div style={{ position: 'absolute', inset: 0, background: t.dark ? 'rgba(0,0,0,0.15)' : 'rgba(255,255,255,0.12)' }} />
      {label && (
        <span style={{
          position: 'absolute', left: 8, bottom: 7,
          fontFamily: 'ui-monospace, "SF Mono", Menlo, monospace',
          fontSize: 9.5, letterSpacing: 0.3,
          color: t.dark ? 'rgba(255,255,255,0.55)' : 'rgba(40,28,20,0.5)',
        }}>{ev.cat} · poster</span>
      )}
    </div>
  );
}

// ── Bottom tab bar ───────────────────────────────────────────
const TABS = [
  { id: '当日摘要', icon: 'today' },
  { id: '全部演出', icon: 'list' },
  { id: '订阅范围', icon: 'subs' },
  { id: '偏好管理', icon: 'prefs' },
  { id: '设置', icon: 'settings' },
];
function TabBar({ active, t }) {
  return (
    <div style={{
      position: 'absolute', left: 0, right: 0, bottom: 0, zIndex: 40,
      paddingBottom: 22, paddingTop: 9,
      background: t.barBg,
      backdropFilter: 'blur(20px) saturate(180%)', WebkitBackdropFilter: 'blur(20px) saturate(180%)',
      borderTop: `0.5px solid ${t.sep}`,
      display: 'flex', justifyContent: 'space-around',
    }}>
      {TABS.map(tab => {
        const on = tab.id === active;
        const col = on ? t.accent : t.tabIdle;
        return (
          <div key={tab.id} style={{ display: 'flex', flexDirection: 'column', alignItems: 'center', gap: 3, flex: 1 }}>
            <div style={{ '--ic-bg': t.barBg, color: col, display: 'flex' }}>
              {ICONS[tab.icon]({ size: 25, c: col })}
            </div>
            <span style={{ fontFamily: SF, fontSize: 10, fontWeight: on ? 650 : 510, color: col, letterSpacing: -0.2, whiteSpace: 'nowrap' }}>{tab.id}</span>
          </div>
        );
      })}
    </div>
  );
}

// ── Screen scaffold: status-bar-safe scroll area + tab bar ───
function Screen({ t, children, active, pad = true }) {
  return (
    <div style={{ position: 'absolute', inset: 0, background: t.bg, overflow: 'hidden' }}>
      <div style={{
        position: 'absolute', inset: 0, overflowY: 'auto',
        paddingBottom: 92, WebkitOverflowScrolling: 'touch',
      }}>
        {children}
      </div>
      <TabBar active={active} t={t} />
    </div>
  );
}

// ── Large-title header (status-bar safe) ─────────────────────
function BigHeader({ t, kicker, title, right, search }) {
  return (
    <div style={{ padding: '60px 20px 8px' }}>
      {kicker && (
        <div style={{ fontFamily: SF, fontSize: 13, fontWeight: 650, color: t.accent, letterSpacing: 0.3, marginBottom: 3 }}>{kicker}</div>
      )}
      <div style={{ display: 'flex', alignItems: 'flex-end', justifyContent: 'space-between', gap: 12 }}>
        <h1 style={{ margin: 0, fontFamily: SF, fontSize: 32, fontWeight: 760, letterSpacing: -0.6, color: t.text, lineHeight: 1.05 }}>{title}</h1>
        {right}
      </div>
      {search && (
        <div style={{
          marginTop: 14, height: 38, borderRadius: 11, background: t.dark ? 'rgba(255,255,255,0.07)' : 'rgba(118,118,128,0.12)',
          display: 'flex', alignItems: 'center', gap: 7, padding: '0 11px',
        }}>
          {ICONS.search({ size: 18, c: t.text3 })}
          <span style={{ fontFamily: SF, fontSize: 16, color: t.text3 }}>搜索演出、艺人、场馆</span>
        </div>
      )}
    </div>
  );
}

Object.assign(window, {
  radarTheme, SF, ICONS, ScoreBadge, SourceTag, Poster, TabBar, Screen, BigHeader, CAT_HUE,
});
