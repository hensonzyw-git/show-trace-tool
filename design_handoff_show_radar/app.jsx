// 演出雷达 — assemble the 3 directions on a design canvas
const { useState } = React;

const tSys = radarTheme('system');
const tB = radarTheme('card-light');
const tC = radarTheme('card-dark');

function Frame({ children }) {
  // sit the device inside the artboard
  return (
    <div style={{ display: 'flex', justifyContent: 'center' }}>
      <IOSDevice>{children}</IOSDevice>
    </div>
  );
}

const W = 402, H = 874;

function buildSection(id, title, subtitle, scr, t) {
  const items = [
    ['today', '今日 · Feed', scr.today],
    ['all', '全部演出', scr.all],
    ['detail', '演出详情', scr.detail],
    ['subs', '订阅', scr.subs],
    ['prefs', '兴趣偏好', scr.prefs],
    ['runs', '采集记录', scr.runs],
  ];
  return (
    <DCSection id={id} title={title} subtitle={subtitle}>
      {items.map(([k, label, El]) => (
        <DCArtboard key={k} id={`${id}-${k}`} label={label} width={W} height={H}>
          <Frame><El t={t} /></Frame>
        </DCArtboard>
      ))}
    </DCSection>
  );
}

function App() {
  const S = window.SysScreens, C = window.CardScreens;
  const sysScr = { today: S.TodaySys, all: S.AllSys, detail: S.DetailSys, subs: S.SubsSys, prefs: S.PrefsSys, runs: S.RunsSys };
  const cardScr = { today: C.TodayCard, all: C.AllCard, detail: C.DetailCard, subs: C.SubsCard, prefs: C.PrefsCard, runs: C.RunsCard };
  return (
    <DesignCanvas>
      {buildSection('a', '方向 A · 系统原生（浅色）', 'iOS 分组列表，最像 Apple 自家 App，主色克制', sysScr, tSys)}
      {buildSection('b', '方向 B · 卡片杂志（浅色）', '卡片流 + 海报占位，标题更大、珊瑚红更自信', cardScr, tB)}
      {buildSection('c', '方向 C · 夜场（深色）', 'B 的卡片语言换成深色夜间氛围，适合晚上刷演出', cardScr, tC)}
    </DesignCanvas>
  );
}

ReactDOM.createRoot(document.getElementById('root')).render(<App />);
