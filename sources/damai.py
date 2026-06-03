"""大麦网搜索抓取器（patchright + 持久化 Chrome profile）。

city 不再作为 source 属性，而是 fetch_raw 的可选参数 —— 同一个 source
实例可同时服务两个维度：
- 艺人维度：fetch_raw(artist)           不带 cty，全国结果
- 本地维度：fetch_raw(keyword, city=…)  带 cty 过滤

历史：
- 里程碑 0：Playwright headless 触发阿里 RGV587 滑块反爬。
- 里程碑 0.5 / A：patchright 替换 Playwright 仍会被搜索接口风控。
- 里程碑 0.5 / B：账号态 profile 可以保存登录，但 headless 请求
  `searchajax.html` 仍会落到 `_____tmd_____/punish` / `newslidecaptcha`。
- 当前策略：大麦只作为本机 assisted source，优先接管用户日常 Chrome
  profile 中的可见标签页。不要用 headless 跑账号态，避免频繁触发风控。

刻意只暴露 fetch_raw（搜索页）—— 详情页跟进作为功能被否决（见
ARCHITECTURE.md 和 memory）。
"""

from pathlib import Path
from urllib.parse import urlencode

from patchright.sync_api import sync_playwright

from sources.base import Source

PROFILE_DIR = Path(__file__).resolve().parent.parent / ".browser-profile"


class DamaiSource(Source):
    name = "damai"
    # fetch_interval_range 用基类默认 (6.0, 12.0) —— 大麦反爬重需要保守间隔

    SEARCH_URL = "https://search.damai.cn/search.htm"

    def __init__(self, headless: bool = False):
        super().__init__()
        self.headless = headless

    # 不 override _cached_fetch 的 key 策略 —— 大麦每个 query 都是不同搜索，
    # 不需要 cache（即使按 (query, city) cache 也不会命中）。

    def discovered_via(self, query: str, city: str | None) -> str:
        city_part = f"（{city}）" if city else "（全国）"
        return f"大麦 App · 搜「{query}」{city_part}"

    def _build_url(self, query: str, city: str | None = None) -> str:
        params: dict[str, str] = {"keyword": query}
        if city:
            params["cty"] = city
        return f"{self.SEARCH_URL}?{urlencode(params)}"

    def _launch(self, p, headless: bool):
        PROFILE_DIR.mkdir(parents=True, exist_ok=True)
        return p.chromium.launch_persistent_context(
            user_data_dir=str(PROFILE_DIR),
            channel="chrome",
            headless=headless,
            viewport={"width": 1280, "height": 800},
            locale="zh-CN",
        )

    def fetch_raw(self, query: str, city: str | None = None) -> tuple[str, str]:
        if self.headless:
            raise RuntimeError(
                "DamaiSource no longer supports headless mode; use visible assisted browsing."
            )
        url = self._build_url(query, city)
        with sync_playwright() as p:
            ctx = self._launch(p, headless=self.headless)
            try:
                page = ctx.pages[0] if ctx.pages else ctx.new_page()
                punished = False

                def on_response(resp):
                    nonlocal punished
                    if (
                        "_____tmd_____/punish" in resp.url
                        or "newslidecaptcha" in resp.url
                    ):
                        punished = True

                page.on("response", on_response)
                page.goto(url, wait_until="domcontentloaded", timeout=30_000)
                # 显式等搜索结果列表出现 —— networkidle 在大麦 SPA 上偶尔会
                # 过早通过（polling/keep-alive 干扰 idle 判定）。selector 没
                # 等到不致命，可能本来就 0 条结果。
                try:
                    page.wait_for_selector(
                        ".search__itemlist .item__main, .search-noresult",
                        timeout=15_000,
                    )
                except Exception:
                    pass
                try:
                    page.wait_for_load_state("networkidle", timeout=8_000)
                except Exception:
                    pass
                page.wait_for_timeout(1500)  # 给最后的 reflow 一点 buffer
                html = page.content()
                if punished or "_____tmd_____/punish" in html or "newslidecaptcha" in html:
                    raise RuntimeError(
                        "Damai triggered anti-bot verification; switch to manual Computer Use collection."
                    )
                return page.url, html
            finally:
                ctx.close()

    def init_profile(self, query: str = "周杰伦") -> None:
        """Legacy helper: open a project-local Chrome profile for debugging.

        默认采集路径已经改为日常 Chrome + Codex Chrome Extension /
        Computer Use。这个方法只保留给隔离调试用，不建议登录长期账号。

        query 仅用于打开一个搜索页方便互动，不影响 profile 内容。
        如果遇到滑块验证码，人工滑过最稳定。完成后回终端按 Enter。
        """
        url = self._build_url(query)
        with sync_playwright() as p:
            ctx = self._launch(p, headless=False)
            try:
                page = ctx.pages[0] if ctx.pages else ctx.new_page()
                page.goto(url, wait_until="domcontentloaded", timeout=30_000)
                print("\n[init-profile] Chrome 已打开大麦搜索页。请：")
                print("  1. ★ 强烈推荐：点右上角【登录】，登录你的大麦账号 ★")
                print("     —— 登录态会进 profile，大幅降低反爬触发概率")
                print("  2. 如果出现滑块验证码，手动滑过（人工最稳）")
                print("  3. 自然浏览 5~15 秒（点开一两个结果也好）")
                print("  4. 浏览完成后，回到这里按 Enter")
                input("\n  >> 完成后按 Enter 关闭浏览器并保存 profile: ")
            finally:
                ctx.close()
        print(f"\n[init-profile] Profile 已保存到 {PROFILE_DIR}")
