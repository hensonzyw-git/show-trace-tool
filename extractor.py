"""LLM 抽取：把原始 HTML 转纯文本后丢给 DeepSeek，按 events 表字段吐 JSON。

DeepSeek 兼容 OpenAI SDK，只是 base_url 不同。模型用 deepseek-chat（V3），
抽取任务用它足够；如果以后想试 reasoner（R1），改 model 字段即可。

无 API key 时不抛错，print 提示并返回空列表，便于在等 key 期间链路依然能跑通。
"""

import json
import os
from typing import Any

from bs4 import BeautifulSoup

EXTRACT_PROMPT = """你是信息抽取助手。下面是从演出票务网站抓到的原始内容（已转纯文本），\
请从中识别与艺人「{artist}」相关的演唱会 / 演出场次，按字段输出 JSON。\
没有任何场次时返回 {{"events": []}}。

字段（找不到的字段填 null，不要瞎编）:
- type: "concert" | "exhibition" | "activity"
- title: 标题
- artist: 艺人
- city: 城市
- venue: 场馆
- event_date: 举办日期 (YYYY-MM-DD，区间写成 "YYYY-MM-DD ~ YYYY-MM-DD")
- on_sale_time: 开票时间
- price_info: 价格信息（字符串即可）
- purchase_url: 购票链接
- source_url: 来源页面 URL

输出格式必须是 {{"events": [ {{...}}, {{...}} ]}}，事件放在 events 数组里。

原始内容:
---
{content}
---
"""


def html_to_text(html: str, limit: int = 60_000) -> str:
    """剥掉 script/style/comment，转纯文本；超长则粗暴截断防止上下文爆。"""
    soup = BeautifulSoup(html, "html.parser")
    for tag in soup(["script", "style", "noscript"]):
        tag.decompose()
    text = soup.get_text("\n", strip=True)
    return text[:limit]


def extract_events(html: str, artist: str, source_url: str) -> list[dict[str, Any]]:
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
                "content": EXTRACT_PROMPT.format(artist=artist, content=text),
            }
        ],
        response_format={"type": "json_object"},
        max_tokens=2048,
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
        e.setdefault("source", "damai")
        if not e.get("source_url"):
            e["source_url"] = source_url
    return events
