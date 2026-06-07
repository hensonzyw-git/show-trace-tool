// 演出雷达 — real event data distilled from the show-trace codebase
// (data/local_inbox 2026-06-05 + digests). Today is 2026-06-05 (Fri).

window.RADAR = (function () {
  const TODAY = '2026-06-05';

  // ── Interest profile (app/preferences.py shape) ──────────────
  const profile = {
    city: '上海',
    include_categories: ['演唱会', '音乐会', '体育比赛'],
    exclude_categories: ['亲子'],
    ranking_preferences: ['未来三个月优先', '票价 ≤ 1000 优先'],
    positive_signals: ['爵士现场', '周杰伦'],
    negative_signals: ['商场快闪活动'],
  };

  // ── Subscription (config + db) ───────────────────────────────
  const subscription = {
    artists: ['周杰伦', '欧阳娜娜', '郎朗', '陈佩斯'],
    local: { city: '上海', keywords: ['演唱会', '音乐会', '体育赛事', '话剧'] },
    sources: {
      damai: { label: '大麦', enabled: true, note: '需 Chrome + 登录态' },
      showstart: { label: '秀动', enabled: true, note: 'Livehouse / 巡演' },
      motianlun: { label: '摩天轮', enabled: false, note: '二手 / 转票' },
    },
  };

  // ── Events (curated real rows) ───────────────────────────────
  // decision: keep | maybe | filter ; match 0-100
  const events = [
    {
      id: '999001', type: 'concert', cat: '演唱会',
      title: '周杰伦嘉年华世界巡回演唱会 2026 上海站',
      artist: '周杰伦', city: '上海', venue: '上海体育场',
      date: '2026.06.20 – 06.22', dateSort: '2026-06-20',
      onSale: '已开票 · 05.22', status: '售票中',
      price: '¥380 – 2580', source: '大麦', via: '搜「周杰伦」· 全国',
      hot: true,
      score: { decision: 'keep', match: 96, cat: '演唱会', uncertainty: 'low',
        reason: '命中订阅艺人「周杰伦」+ 关注品类 演唱会' },
    },
    {
      id: '1046342', type: 'concert', cat: '演唱会',
      title: '2026 欧阳娜娜「Playlist 嘉年华」演唱会 · 上海站',
      artist: '欧阳娜娜', city: '上海', venue: '上海世博文化公园 · 音乐之林',
      date: '2026.06.13 周六 18:30', dateSort: '2026-06-13',
      onSale: '已开票', status: '售票中',
      price: '¥380 – 980', source: '大麦', via: '搜「欧阳娜娜」· 全国',
      score: { decision: 'keep', match: 89, cat: '演唱会', uncertainty: 'low',
        reason: '命中订阅艺人 + 关注品类 演唱会' },
    },
    {
      id: '1053305', type: 'concert', cat: '音乐会',
      title: '郎朗 · 琴动中国钢琴独奏音乐会 · 上海站',
      artist: '郎朗', city: '上海', venue: '前滩 31 演艺中心 · 大剧场',
      date: '2026.08.27 周四 19:45', dateSort: '2026-08-27',
      onSale: '已开票', status: '售票中',
      price: '¥380 – 2680', source: '大麦', via: '搜「音乐会」· 上海',
      score: { decision: 'keep', match: 90, cat: '音乐会', uncertainty: 'low',
        reason: '命中订阅艺人 + 关注品类 音乐会' },
    },
    {
      id: '1055410', type: 'concert', cat: '音乐会',
      title: '当代投影 · 古典到爵士｜朱蟒三重奏音乐会',
      artist: null, city: '上海', venue: '林肯爵士乐上海中心',
      date: '2026.06.17 – 07.23', dateSort: '2026-06-17',
      onSale: '已开票', status: '售票中',
      price: '¥158 – 2388', source: '大麦', via: '搜「演唱会」· 上海',
      score: { decision: 'keep', match: 83, cat: '音乐会', uncertainty: 'medium',
        reason: '命中正向信号「爵士现场」' },
    },
    {
      id: '1052827', type: 'concert', cat: 'Livehouse',
      title: '【抉择呈现】澳大利亚前卫金属乐队 PLINI 2026 巡演上海站',
      artist: 'PLINI', city: '上海', venue: 'MAO Livehouse 上海',
      date: '2026.07.21 周二 19:30', dateSort: '2026-07-21',
      onSale: '已开票', status: '售票中',
      price: '¥260 – 320', source: '秀动', via: '搜「演唱会」· 上海',
      score: { decision: 'maybe', match: 54, cat: 'Livehouse', uncertainty: 'high',
        reason: '弱相关：Livehouse 巡演，未命中明确品类' },
    },
    {
      id: '1044435', type: 'concert', cat: '演唱会',
      title: '付辛博 2026「辛生万物」全国巡回演唱会 — 上海站',
      artist: '付辛博', city: '上海', venue: '徐家汇体育公园 · 上海体育馆',
      date: '2026.07.11 周六 19:00', dateSort: '2026-07-11',
      onSale: '已开票', status: '售票中',
      price: '¥580 – 1180', source: '大麦', via: '搜「演唱会」· 上海',
      score: { decision: 'maybe', match: 61, cat: '演唱会', uncertainty: 'medium',
        reason: '命中品类 演唱会，但票价偏高、非订阅艺人' },
    },
    {
      id: '1056095', type: 'concert', cat: '音乐会',
      title: '夏夜风琴声 — 管风琴室内乐音乐会 丨 上海夏季音乐节',
      artist: '上海交响乐团', city: '上海', venue: '捷豹上海交响音乐厅 · 演艺厅',
      date: '2026.07.16 周四 19:45', dateSort: '2026-07-16',
      onSale: '已开票', status: '售票中',
      price: '¥100 – 300', source: '大麦', via: '搜「音乐会」· 上海',
      score: { decision: 'keep', match: 80, cat: '音乐会', uncertainty: 'medium',
        reason: '命中关注品类 音乐会 + 票价友好' },
    },
    {
      id: '1043928', type: 'activity', cat: '话剧',
      title: '大道文化出品 · 陈佩斯主演话剧《惊梦》',
      artist: '陈佩斯', city: '上海', venue: '上海大剧院 · 大剧场',
      date: '2026.07.02 – 07.05', dateSort: '2026-07-02',
      onSale: '已开票', status: '售票中',
      price: '¥280 – 1080', source: '大麦', via: '搜「话剧」· 上海',
      score: { decision: 'keep', match: 78, cat: '话剧', uncertainty: 'medium',
        reason: '命中订阅艺人「陈佩斯」' },
    },
    {
      id: '1052714', type: 'activity', cat: '话剧',
      title: '话剧《青蛇》',
      artist: null, city: '上海', venue: '上海文化广场 · 主剧场',
      date: '2026.06.25 – 06.28', dateSort: '2026-06-25',
      onSale: '已开票', status: '售票中',
      price: '¥80 – 880', source: '大麦', via: '搜「话剧」· 上海',
      score: { decision: 'maybe', match: 50, cat: '话剧', uncertainty: 'high',
        reason: '未命中明确关注或排除品类' },
    },
    {
      id: '1052566', type: 'activity', cat: '体育',
      title: '2026 国际板式网球巡回赛金级赛事上海站',
      artist: null, city: '上海', venue: '江湾国际板式网球中心',
      date: '2026.06.10 – 06.14', dateSort: '2026-06-10',
      onSale: '已开票', status: '售票中',
      price: '¥299 – 1299', source: '大麦', via: '搜「体育赛事」· 上海',
      score: { decision: 'keep', match: 81, cat: '体育比赛', uncertainty: 'medium',
        reason: '命中关注品类 体育比赛' },
    },
    {
      id: '1027050', type: 'activity', cat: '体育',
      title: '2026 中国足球协会杯 · 上海泽天主场赛事',
      artist: null, city: '上海', venue: '源深体育中心体育场',
      date: '2026.06.20 周六 19:30', dateSort: '2026-06-20',
      onSale: '已开票', status: '售票中',
      price: '¥59.9 – 79.9', source: '大麦', via: '搜「体育赛事」· 上海',
      score: { decision: 'keep', match: 76, cat: '体育比赛', uncertainty: 'medium',
        reason: '命中关注品类 体育比赛 + 票价友好' },
    },
    {
      id: '1040909', type: 'concert', cat: '亲子',
      title: '互动亲子音乐会《动物狂欢节》',
      artist: null, city: '上海', venue: '保利上海城市剧院',
      date: '2026.07.19 周日 10:30', dateSort: '2026-07-19',
      onSale: '已开票', status: '售票中',
      price: '¥60 – 80', source: '大麦', via: '搜「音乐会」· 上海',
      score: { decision: 'filter', match: 15, cat: '亲子', uncertainty: 'low',
        reason: '命中排除品类 亲子' },
    },
    {
      id: '1056001', type: 'activity', cat: '话剧',
      title: '俄罗斯芭蕾国家剧院芭蕾舞剧《天鹅湖》',
      artist: null, city: '上海', venue: '久事 · 上海商城剧院',
      date: '2026.10.06 – 10.07', dateSort: '2026-10-06',
      onSale: '即将开票 · 06.10 10:00', status: '即将开票',
      price: '¥180 – 880', source: '大麦', via: '搜「话剧」· 上海',
      score: { decision: 'maybe', match: 48, cat: '话剧', uncertainty: 'high',
        reason: '未命中明确关注或排除品类' },
    },
    {
      id: '1046329', type: 'concert', cat: 'Livehouse',
      title: 'Summer Shape 2026 夏日速写 · 上海站',
      artist: null, city: '上海', venue: '育音堂小镇 C 厅 YUYINTOWN CUBE',
      date: '2026.06.11 周四 20:00', dateSort: '2026-06-11',
      onSale: '已开票', status: '售票中',
      price: '¥79 – 99', source: '秀动', via: '搜「演唱会」· 上海',
      score: { decision: 'maybe', match: 52, cat: 'Livehouse', uncertainty: 'high',
        reason: 'Livehouse 拼盘，弱相关' },
    },
    {
      id: '1041955', type: 'concert', cat: '音乐会',
      title: '黄诗扶「入梦」音乐幕剧',
      artist: '黄诗扶', city: '上海', venue: '前滩 31 演艺中心 · 大剧场',
      date: '2026.06.19 – 06.20', dateSort: '2026-06-19',
      onSale: '已开票', status: '售票中',
      price: '¥180 – 880', source: '大麦', via: '搜「演唱会」· 上海',
      score: { decision: 'maybe', match: 57, cat: '音乐会', uncertainty: 'medium',
        reason: '弱相关：音乐幕剧，未命中订阅艺人' },
    },
    {
      id: '1051915', type: 'activity', cat: '话剧',
      title: '邹静之编剧 · 张国立导演领衔 · 原创音乐话剧《情歌》',
      artist: '张国立', city: '上海', venue: '上海文化广场',
      date: '2026.07.24 – 07.26', dateSort: '2026-07-24',
      onSale: '即将开票 · 06.09 12:00', status: '即将开票',
      price: '¥80 – 1280', source: '大麦', via: '搜「话剧」· 上海',
      score: { decision: 'maybe', match: 55, cat: '话剧', uncertainty: 'medium',
        reason: '未命中明确关注品类' },
    },
  ];

  // ── Worker runs (db.list_runs shape) ─────────────────────────
  const runs = [
    { id: 41, date: '2026-06-05', time: '10:00', trigger: 'cron', status: 'success',
      raw: 12, extracted: 47, fresh: 5, notified: 5 },
    { id: 40, date: '2026-06-05', time: '00:00', trigger: 'local-sync', status: 'success',
      raw: 0, extracted: 50, fresh: 8, notified: 0 },
    { id: 39, date: '2026-06-04', time: '10:00', trigger: 'cron', status: 'partial_success',
      raw: 9, extracted: 31, fresh: 3, notified: 3, err: 'damai | 演唱会：登录态过期' },
    { id: 38, date: '2026-06-03', time: '21:40', trigger: 'api', status: 'success',
      raw: 12, extracted: 44, fresh: 2, notified: 2 },
    { id: 37, date: '2026-06-03', time: '10:00', trigger: 'cron', status: 'success',
      raw: 11, extracted: 40, fresh: 4, notified: 4 },
    { id: 36, date: '2026-06-02', time: '10:00', trigger: 'cron', status: 'failed',
      raw: 0, extracted: 0, fresh: 0, notified: 0, err: 'pipeline：没有启用任何 source' },
  ];

  // ── Derived: today's digest ──────────────────────────────────
  const keep = events.filter(e => e.score.decision === 'keep');
  const soon = [...events]
    .filter(e => e.score.decision !== 'filter')
    .sort((a, b) => a.dateSort.localeCompare(b.dateSort));

  return {
    TODAY, profile, subscription, events, runs,
    today: {
      date: TODAY, weekday: '周五',
      newCount: 8, keepCount: keep.length,
      sources: ['大麦', '秀动'],
    },
    topPicks: soon.slice(0, 3),
    decisionMeta: {
      keep:   { label: '关注', zh: '保留' },
      maybe:  { label: '待定', zh: '也许' },
      filter: { label: '已过滤', zh: '过滤' },
    },
  };
})();
