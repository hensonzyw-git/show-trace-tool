"""秀动抓取器（SSR HTML + requests，无反爬）。

秀动主打 Livehouse / 独立音乐 / 小型现场，是大麦覆盖不到的那块互补
（大麦弱 Livehouse）。技术上比大麦简单得多：
- /event/list 是 SSR 静态 HTML（105KB 含完整演出列表），requests 直接抓
- 实测 curl 不带 cookie / 不带 referer 也能正常返回 200
- 按 cityCode 过滤城市（上海=21，北京=10，通过 Playwright 模拟点击观察）

刻意不实现 keyword 搜索 —— 秀动没有按 keyword 全站搜索的接口，按 city
+ 风格浏览是它的主路径。"按艺人搜全国" 维度对秀动不适用：fetch_raw
在 city=None 或未配置时返回空 raw，让 main.py 自然跳过 LLM 抽取，
节省 fetch + token。
"""

from urllib.parse import urlencode

import requests

from sources.base import Source


class ShowstartSource(Source):
    name = "showstart"

    # SSR + 无反爬，间隔短一点即可（保护 IP 不过频）
    fetch_interval_range = (1.0, 3.0)

    LIST_URL = "https://www.showstart.com/event/list"

    # 秀动的 cityCode 映射 —— 通过 Playwright 点击"上海"观察 URL 变化得到。
    # 只列用户关心的城市；其他城市 fetch_raw 会返回空 raw（main 跳过）。
    CITY_CODES = {
        "上海": 21,
        "北京": 10,
    }

    HEADERS = {
        "User-Agent": (
            "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
            "AppleWebKit/537.36 (KHTML, like Gecko) "
            "Chrome/122.0.0.0 Safari/537.36"
        ),
        "Accept-Language": "zh-CN,zh;q=0.9,en;q=0.8",
    }

    def fetch_raw(self, query: str, city: str | None = None) -> tuple[str, str]:
        """按 city 列出该城市的所有演出。query 参数当前忽略（秀动无 keyword 搜索）。

        city=None 或 city not in CITY_CODES → 返回 (url, "")，让 main 跳过抽取。
        同 city 的多次 task 复用同一份 raw（cache by city）。
        """
        code = self.CITY_CODES.get(city) if city else None
        if code is None:
            return (self.LIST_URL, "")

        return self._cached_fetch(
            key=("city", city),
            fetcher=lambda: self._do_fetch(code),
        )

    def _do_fetch(self, city_code: int) -> tuple[str, str]:
        params: dict[str, int] = {"pageNo": 1, "pageSize": 50, "cityCode": city_code}
        url = f"{self.LIST_URL}?{urlencode(params)}"
        resp = requests.get(url, headers=self.HEADERS, timeout=20)
        resp.raise_for_status()
        resp.encoding = resp.apparent_encoding or "utf-8"
        return resp.url, resp.text

    def discovered_via(self, query: str, city: str | None) -> str:
        """秀动按 city 浏览，不按 keyword 搜，discovered_via 反映这点。"""
        return f"秀动 App · {city or '?'} 演出列表"
