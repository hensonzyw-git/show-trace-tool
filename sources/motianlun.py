"""摩天轮票务抓取器（JSON API，无反爬）。

摩天轮 motianlun.cn 是 SPA，但所有数据走干净的 JSON API
（/mtl_recommendapi/* 和 /showapi/*）。一次调首页 floor API 就能拿
70+ 条事件，覆盖演唱会 / 话剧歌剧 / 舞蹈芭蕾 / 曲艺脱口秀 / Livehouse /
展览市集 / 体育赛事 / 儿童亲子 等多品类 —— 跟大麦 / 秀动互补很强
（"展览市集"和"话剧歌剧"是大麦较弱的，"曲艺脱口秀"两个都不强）。

技术上比秀动还简单：
- 直接 requests 调 JSON API，不需要 cookie / token / 浏览器
- 数据已经结构化，没有 HTML 解析问题
- LLM 只负责把摩天轮的字段标准化到 events schema（如 showType
  "VocalConcert" → type "concert"），而不是从乱糟糟 HTML 抽信息

实现：fetch_raw 把 JSON parse 后转成"每事件一段紧凑文本"，用 `---` 分段，
让 LLM 标准化字段输出。这跟其他 source 的 raw=HTML 形式保持流水线一致。
"""

import ast
from typing import Any
from urllib.parse import urlencode

import requests

from sources.base import Source


class MotianlunSource(Source):
    name = "motianlun"

    # JSON API + 无反爬，间隔短一点即可（保护 IP 不过频）
    fetch_interval_range = (1.0, 3.0)

    FLOOR_URL = "https://www.motianlun.cn/mtl_recommendapi/pub/home/v1/static_floor"
    SHOW_DETAIL_URL_TEMPLATE = "https://www.motianlun.cn/show_detail?showId={show_id}"

    # cityId 是中国行政区划码（省 2 位 + 市 2 位），通过 /showapi/site_city
    # 或 Playwright 切换城市观察 URL。MVP 只放用户关心的城市。
    CITY_IDS = {
        "上海": 3101,
        "北京": 1101,
    }

    HEADERS = {
        "User-Agent": (
            "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
            "AppleWebKit/537.36 (KHTML, like Gecko) "
            "Chrome/122.0.0.0 Safari/537.36"
        ),
        "Accept": "application/json",
        "Accept-Language": "zh-CN,zh;q=0.9,en;q=0.8",
    }

    def fetch_raw(self, query: str, city: str | None = None) -> tuple[str, str]:
        """按 city 拉 floor API，转成紧凑文本给 LLM。

        query 当前忽略（摩天轮 floor 是按 city 给推荐，无 keyword 搜索）。
        city 未配置时返回空 raw 让 main 跳过。
        """
        cid = self.CITY_IDS.get(city) if city else None
        if cid is None:
            return (self.FLOOR_URL, "")

        params = {"cityId": cid, "src": "web"}
        url = f"{self.FLOOR_URL}?{urlencode(params)}"
        resp = requests.get(url, headers=self.HEADERS, timeout=20)
        resp.raise_for_status()

        data = resp.json()
        text = self._format_floor(data.get("data") or [])
        return resp.url, text

    def _format_floor(self, sections: list[dict[str, Any]]) -> str:
        """从 floor JSON 抽出真实事件 item，按 id 去重，转成 LLM 友好文本。

        section/room 类型很多（CATEGORY/BANNER/ORDER/SHOW_TAG/DISCOUNT_SHOW），
        只取后两种（真演出）。
        """
        seen: set[str] = set()
        blocks: list[str] = []
        for section in sections:
            for room in section.get("rooms") or []:
                if room.get("type") not in ("SHOW_TAG", "DISCOUNT_SHOW"):
                    continue
                for item in room.get("items") or []:
                    iid = item.get("id")
                    if not iid or iid in seen:
                        continue
                    seen.add(iid)
                    blocks.append(self._format_item(item))
        return "\n---\n".join(blocks)

    def _format_item(self, item: dict[str, Any]) -> str:
        show_id = item.get("id")
        price = self._parse_price(item.get("priceInfo"))
        detail_url = self.SHOW_DETAIL_URL_TEMPLATE.format(show_id=show_id)
        return (
            f"标题: {item.get('title') or ''}\n"
            f"showType (摩天轮内部代码): {item.get('showType') or item.get('type') or ''}\n"
            f"城市: {item.get('cityName') or ''}\n"
            f"场馆: {item.get('venueName') or ''}\n"
            f"开始日期: {item.get('showBeginDate') or ''}\n"
            f"结束日期: {item.get('showEndDate') or ''}\n"
            f"票价: {price or ''}\n"
            f"详情链接: {detail_url}"
        )

    @staticmethod
    def _parse_price(price_info: Any) -> str | None:
        """priceInfo 在 JSON 里是 Python dict 字符串（用单引号），需要 literal_eval。"""
        if not price_info:
            return None
        if isinstance(price_info, dict):
            pi: Any = price_info
        elif isinstance(price_info, str):
            try:
                pi = ast.literal_eval(price_info)
            except (ValueError, SyntaxError):
                return price_info
        else:
            return None
        if not isinstance(pi, dict):
            return str(pi)
        prefix = pi.get("prefix") or ""
        yuan = pi.get("yuanNum") or "?"
        suffix = pi.get("suffix") or "元"
        return f"{prefix}{yuan}{suffix}"

    def discovered_via(self, query: str, city: str | None) -> str:
        return f"摩天轮 App · {city or '?'} 推荐演出"
