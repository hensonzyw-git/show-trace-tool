"""大麦网搜索抓取器（patchright + 持久化 Chrome profile）。

历史：
- 里程碑 0：Playwright headless 触发阿里 RGV587 滑块反爬
- 里程碑 0.5 / A：patchright 替换 Playwright 仍被反爬识别（webdriver
  信号绕过了，但 IP 行为模式、TLS 指纹等其他维度仍命中风控）
- 里程碑 0.5 / B（当前）：patchright + launch_persistent_context +
  channel="chrome"。用项目内独立 user_data_dir（.browser-profile/），
  通过 channel="chrome" 调用系统真实 Chrome 二进制——指纹更接近正常用户。
  首次需要 GUI 模式让用户手动浏览一下，建立真实的 cookie/history/指纹痕迹。

每天一次的低频访问对这套 profile 友好；如果哪天 profile 又被反爬识别，
重新跑一次 `python main.py --init-profile` 即可。
"""

from pathlib import Path
from urllib.parse import urlencode

from patchright.sync_api import sync_playwright

from sources.base import Source

PROFILE_DIR = Path(__file__).resolve().parent.parent / ".browser-profile"


class DamaiSource(Source):
    name = "damai"

    SEARCH_URL = "https://search.damai.cn/search.htm"

    def __init__(self, city: str | None = None, headless: bool = True):
        self.city = city
        self.headless = headless

    def _build_url(self, query: str) -> str:
        params: dict[str, str] = {"keyword": query}
        if self.city:
            params["cty"] = self.city
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

    def fetch_raw(self, query: str) -> tuple[str, str]:
        url = self._build_url(query)
        with sync_playwright() as p:
            ctx = self._launch(p, headless=self.headless)
            try:
                page = ctx.pages[0] if ctx.pages else ctx.new_page()
                page.goto(url, wait_until="domcontentloaded", timeout=30_000)
                try:
                    page.wait_for_load_state("networkidle", timeout=10_000)
                except Exception:
                    pass
                return page.url, page.content()
            finally:
                ctx.close()

    def init_profile(self, query: str) -> None:
        """开 GUI 模式让用户手动浏览一次，给 profile 建立真实使用痕迹。

        如果遇到滑块验证码，人工滑过最稳定。完成后回终端按 Enter。
        """
        url = self._build_url(query)
        with sync_playwright() as p:
            ctx = self._launch(p, headless=False)
            try:
                page = ctx.pages[0] if ctx.pages else ctx.new_page()
                page.goto(url, wait_until="domcontentloaded", timeout=30_000)
                print("\n[init-profile] Chrome 已打开大麦搜索页。请：")
                print("  1. 如果出现滑块验证码，手动滑过（人工最稳）")
                print("  2. 自然浏览 5~15 秒（点开一两个结果也好）")
                print("  3. 浏览完成后，回到这里按 Enter")
                input("\n  >> 完成后按 Enter 关闭浏览器并保存 profile: ")
            finally:
                ctx.close()
        print(f"\n[init-profile] Profile 已保存到 {PROFILE_DIR}")
