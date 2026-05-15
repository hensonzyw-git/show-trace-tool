"""大麦网搜索抓取器（Playwright 版）。

大麦搜索是 SPA，requests 拿到的是空壳。MVP 直接用 Playwright headless
浏览器渲染拿真实 HTML —— 这是文档第三节预留的升级路径，提前到里程碑 0
是因为 requests 实测抽不到任何内容。

注意：Playwright 每次会启动 Chromium，首次调用约 3~6 秒，对每天跑一次
的工具完全可接受。后续如果要并发或复用 browser 实例再优化。
"""

from urllib.parse import urlencode

from playwright.sync_api import sync_playwright

from sources.base import Source


class DamaiSource(Source):
    name = "damai"

    SEARCH_URL = "https://search.damai.cn/search.htm"

    USER_AGENT = (
        "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/122.0.0.0 Safari/537.36"
    )

    def __init__(self, city: str | None = None):
        self.city = city

    def fetch_raw(self, query: str) -> tuple[str, str]:
        params: dict[str, str] = {"keyword": query}
        if self.city:
            params["cty"] = self.city
        url = f"{self.SEARCH_URL}?{urlencode(params)}"

        with sync_playwright() as p:
            browser = p.chromium.launch(headless=True)
            try:
                context = browser.new_context(
                    user_agent=self.USER_AGENT,
                    locale="zh-CN",
                )
                page = context.new_page()
                # networkidle 等到没有持续网络活动，SPA 内容此时已渲染完
                page.goto(url, wait_until="networkidle", timeout=30_000)
                html = page.content()
                final_url = page.url
                return final_url, html
            finally:
                browser.close()
