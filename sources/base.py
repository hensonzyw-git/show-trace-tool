"""Source 抽象基类：每个抓取平台实现一个子类。

三个职责：
- fetch_raw(query, city)      : 拿到原始内容（HTML/JSON 文本）和实际请求 URL
- discovered_via(query, city) : 给 digest 渲染用的"用户视角在哪发现"字符串
- raw_path(...)               : 决定原始内容落盘的文件名

class attr `fetch_interval_range` 告诉 main.py 此源两次 fetch 之间随机
间隔范围（秒）。基类默认保守（6-12s），反爬轻的源可以 override 成更短。

city 是可选的 —— 调用方按"维度"决定是否传：
- 艺人维度（artists）→ city=None，全国都看
- 本地维度（local）  → city=指定城市
不支持当前 city 的 source 应在 fetch_raw 里返回空字符串 raw，让 main 自然跳过。
"""

from abc import ABC, abstractmethod
from datetime import datetime
from pathlib import Path


class Source(ABC):
    name: str  # 子类设置，作为 raw 文件名前缀和事件来源标识

    # 两次 fetch 之间的随机间隔范围（秒）。子类按反爬强度 override。
    fetch_interval_range: tuple[float, float] = (6.0, 12.0)

    @abstractmethod
    def fetch_raw(self, query: str, city: str | None = None) -> tuple[str, str]:
        """返回 (实际请求 URL, 原始内容文本)。

        城市未支持或当前查询不适用时，返回 (url, "")，main 会跳过 LLM 抽取。
        """
        ...

    def discovered_via(self, query: str, city: str | None) -> str:
        """用户视角的"在哪发现"字符串，digest 渲染用。子类按各自交互模型 override。

        默认通用版："<source.name> · 搜「{query}」（{city}）"
        """
        city_part = f"（{city}）" if city else "（全国）"
        return f"{self.name} · 搜「{query}」{city_part}"

    def raw_path(self, raw_dir: Path, query: str, fetched_at: datetime) -> Path:
        stamp = fetched_at.strftime("%Y%m%dT%H%M")
        safe_query = query.replace("/", "_").replace(" ", "_")
        return raw_dir / f"{self.name}_{stamp}_{safe_query}.html"
