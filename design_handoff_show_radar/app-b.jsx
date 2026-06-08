// 演出雷达 — Direction B (chosen), polished. Light + dark paired per screen.
const tLight = radarTheme('card-light');
const tDark = radarTheme('card-dark');
const W = 402, H = 874;

function Frame({ children }) {
  return <div style={{ display: 'flex', justifyContent: 'center' }}><IOSDevice>{children}</IOSDevice></div>;
}

function PairSection({ id, title, subtitle, El }) {
  return (
    <DCSection id={id} title={title} subtitle={subtitle}>
      <DCArtboard id={`${id}-light`} label="浅色" width={W} height={H}><Frame><El t={tLight} /></Frame></DCArtboard>
      <DCArtboard id={`${id}-dark`} label="深色" width={W} height={H}><Frame><El t={tDark} /></Frame></DCArtboard>
    </DCSection>
  );
}

function App() {
  const C = window.CardScreens;
  return (
    <DesignCanvas>
      <PairSection id="today" title="今日 · Feed" subtitle="每日新增汇总 + ⚡最近就开始 + 为你关注" El={C.TodayCard} />
      <PairSection id="all" title="全部演出" subtitle="品类 / 口味筛选 · 按日期排序" El={C.AllCard} />
      <PairSection id="detail" title="演出详情" subtitle="雷达评分理由 · 场馆票价 · 去大麦购票" El={C.DetailCard} />
      <PairSection id="subs" title="订阅" subtitle="关注艺人 · 本地关键词 · 多平台数据源开关" El={C.SubsCard} />
      <PairSection id="prefs" title="兴趣偏好" subtitle="大白话调教推荐 · 想看 / 不想看品类 · 信号" El={C.PrefsCard} />
      <PairSection id="settings" title="设置" subtitle="外观主题 · 通知 · 数据采集 · 关于" El={C.SettingsCard} />
      <PairSection id="runs" title="采集记录（设置内）" subtitle="从「设置 › 采集记录」进入 · 每日统计与运行历史" El={C.RunsCard} />
    </DesignCanvas>
  );
}

ReactDOM.createRoot(document.getElementById('root')).render(<App />);
