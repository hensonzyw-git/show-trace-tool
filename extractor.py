"""LLM 抽取：把原始 HTML 转纯文本后丢给 DeepSeek，按 events 表字段吐 JSON。

DeepSeek 兼容 OpenAI SDK，只是 base_url 不同。模型用 deepseek-chat（V3），
抽取任务用它足够；如果以后想试 reasoner（R1），改 model 字段即可。

extract_events 接受 description 参数描述"找什么"，由 caller 决定 prompt
context（艺人 vs 本地关键词），让 extractor 与"维度"解耦。

刻意不做详情页二次抽取 —— digest 里的 purchase_url 是大麦详情页直链，
用户对感兴趣事件会自己点过去看，不需要 LLM 在中间再加一层抽取。

无 API key 时不抛错，print 提示并返回空列表，便于在等 key 期间链路依然能跑通。
"""

import json
import os
import re
from typing import Any

from bs4 import BeautifulSoup

EXTRACT_PROMPT = """你是信息抽取助手。下面是从演出票务网站抓到的原始内容（已转纯文本），\
请从中识别 {description}，按字段输出 JSON。\
没有匹配项时返回 {{"events": []}}。

字段（找不到的字段填 null，不要瞎编；artist 对非艺人活动可以为 null）:
- type: "concert" | "exhibition" | "activity"
- title: 标题
- artist: 艺人（展览/活动可空）
- city: 城市
- venue: 场馆
- event_date: 举办日期 (YYYY-MM-DD，区间写成 "YYYY-MM-DD ~ YYYY-MM-DD")
- on_sale_time: 开票时间（搜索页通常没有，找不到就 null）
- price_info: 价格信息（字符串即可）
- purchase_url: 购票 / 详情页链接（在内容里以 `[link: https://detail.damai.cn/...]` 标记出现，给每个事件配最相关的那条）
- source_url: 来源页面 URL

输出格式必须是 {{"events": [ {{...}}, {{...}} ]}}，事件放在 events 数组里。

原始内容:
---
{content}
---
"""


def _resolve_detail_link(href: str) -> str | None:
    """如果 href 是某个已知 source 的演出详情链接，返回完整 URL；否则 None。

    每加一个 source 在这里加一条规则。LLM 看到 `[link: ...]` 标记后会
    把对应链接填进 purchase_url 字段。
    """
    # 大麦：//detail.damai.cn/item.htm?id=... 或 https://detail.damai.cn/...
    if "detail.damai.cn" in href:
        return ("https:" + href) if href.startswith("//") else href
    # 秀动：/event/<数字>（排除 /event/list 这种非详情页 URL）
    if re.match(r"^/event/\d", href):
        return "https://www.showstart.com" + href
    return None


def html_to_text(html: str, limit: int = 60_000) -> str:
    """剥掉 script/style/comment，转纯文本；超长则粗暴截断防止上下文爆。

    用 lxml 而不是内置 html.parser —— 大麦实测下 html.parser 容错弱，
    178KB HTML 只能 get_text 出 930 字（在某个标签上截了），lxml 没问题。

    给已知 source 的演出详情链接附加 `[link: URL]` 标记 —— BS4 get_text
    默认丢弃 href 属性，但 LLM 需要 detail URL 才能填进 purchase_url。
    """
    soup = BeautifulSoup(html, "lxml")
    for tag in soup(["script", "style", "noscript"]):
        tag.decompose()
    for a in soup.find_all("a", href=True):
        full = _resolve_detail_link(a["href"])
        if full:
            a.append(f" [link: {full}]")
    text = soup.get_text("\n", strip=True)
    return text[:limit]


def extract_events(
    html: str,
    description: str,
    source_url: str,
    source_name: str = "damai",
) -> list[dict[str, Any]]:
    api_key = os.environ.get("DEEPSEEK_API_KEY")
    if not api_key:
        print(
            "[extractor] DEEPSEEK_API_KEY 未设，跳过 LLM 抽取。\n"
            "           在 .env 里填上 key 后再次运行即可完整跑通。"
        )
        return []

    text = html_to_text(html)
    if not text.strip():
        print("[extractor] 原始内容转纯文本后为空，可能源站返回了纯 JS 壳。")
        return []

    # 延迟 import，让无 key 的早期阶段也能跑前面的步骤
    from openai import OpenAI

    client = OpenAI(api_key=api_key, base_url="https://api.deepseek.com")
    resp = client.chat.completions.create(
        model="deepseek-chat",
        messages=[
            {
                "role": "user",
                "content": EXTRACT_PROMPT.format(description=description, content=text),
            }
        ],
        response_format={"type": "json_object"},
        max_tokens=8192,
        temperature=0.0,
    )

    reply = resp.choices[0].message.content or ""
    try:
        payload = json.loads(reply)
    except json.JSONDecodeError:
        print(f"[extractor] LLM 返回无法解析为 JSON，前 200 字: {reply[:200]}")
        return []

    events = payload.get("events") if isinstance(payload, dict) else None
    if not isinstance(events, list):
        print(f"[extractor] LLM 返回的 events 字段不是数组: {type(events).__name__}")
        return []

    for e in events:
        e.setdefault("source", source_name)
        if not e.get("source_url"):
            e["source_url"] = source_url
        # 把协议相对 URL 补全 https，方便 digest 里直接渲染成可点击链接
        url = e.get("purchase_url")
        if url and url.startswith("//"):
            e["purchase_url"] = "https:" + url
    return events
