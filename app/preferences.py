"""Interest profile helpers.

This module is intentionally model-agnostic. The first version uses simple
keyword rules so the API and storage flow are testable; an LLM parser can later
replace ``parse_preference_feedback`` without changing the API shape.
"""

from __future__ import annotations

import json
import os
import re
from typing import Any

from db import ensure_interest_profile, save_interest_profile

CATEGORY_ALIASES = {
    "体育比赛": ["体育", "比赛", "足球", "篮球", "网球", "赛车", "f1", "F1"],
    "演唱会": ["演唱会", "巡演", "live", "Live", "LIVE"],
    "音乐会": ["音乐会", "交响", "古典", "爵士", "室内乐", "音乐节"],
    "话剧": ["话剧", "舞台剧", "剧场", "戏剧"],
    "展览": ["展览", "艺术展", "博物馆", "美术馆"],
    "曲艺杂谈": ["曲艺", "相声", "评书", "杂谈", "脱口秀"],
    "亲子": ["亲子", "儿童", "家庭"],
    "儿童剧": ["儿童剧", "童话剧"],
}

NEGATIVE_MARKERS = [
    "不要",
    "不想",
    "不感兴趣",
    "少推荐",
    "屏蔽",
    "过滤",
    "排除",
    "暂不",
    "先不要",
]
POSITIVE_MARKERS = ["要", "想看", "关注", "多推荐", "保留", "优先", "看看", "需要"]
LOWER_PRIORITY_MARKERS = ["降低", "下调", "减少", "少推荐", "少一点", "低优先级"]
ARTIST_ADD_PATTERN = re.compile(r"(?:增加|添加|新增|关注)\s*(?:艺人|歌手|乐队)?\s*([\w\u4e00-\u9fff·・.\- ]+)")
ALLOWED_DECISIONS = {"keep", "maybe", "filter"}
ALLOWED_UNCERTAINTY = {"low", "medium", "high"}
LLM_MODEL = os.environ.get("SHOW_TRACE_PREFERENCES_MODEL", "deepseek-chat")
LLM_BATCH_SIZE = 30

FEEDBACK_PROMPT = """你是一个个人活动推荐系统的偏好解析器。
用户会用自然语言描述想看或不想看的活动类型。请把反馈合并进当前结构化偏好。

要求：
- 只输出 JSON object。
- 不要删除未被用户明确否定的偏好。
- 用户说"不要/不想/屏蔽/过滤/暂不/先不要"时，相关类别进入 exclude_categories。
- 用户说"想看/关注/多推荐/保留/优先/需要"时，相关类别进入 include_categories。
- 用户说"降低/下调/减少 X 优先级"时，不要排除 X；把 "降低X优先级" 写入 ranking_preferences。
- 用户说"增加/添加/关注 艺人/歌手/乐队 X"时，把艺人名写入 updates.artists，不要写入 profile。
- 对无法归入明确类别但有偏好含义的短语，放入 positive_signals 或 negative_signals。
- 保持列表去重。

当前偏好：
{profile_json}

用户反馈：
{feedback}

输出格式：
{{
  "profile": {{
    "city": "上海",
    "include_categories": ["体育比赛"],
    "exclude_categories": ["亲子"],
    "ranking_preferences": ["未来三个月优先"],
    "negative_signals": ["低质量商场活动"],
    "positive_signals": ["爵士现场"]
  }},
  "updates": {{
    "include_categories": [],
    "exclude_categories": [],
    "ranking_preferences": [],
    "artists": [],
    "positive_signals": [],
    "negative_signals": []
  }}
}}
"""

SCORING_PROMPT = """你是一个个人活动推荐系统的偏好分类器，请输出 json。
请根据用户当前偏好，为每条活动输出是否推荐。

决策规则：
- decision 只能是 keep、maybe、filter。
- keep：明确符合 include_categories 或 positive_signals。
- filter：明确符合 exclude_categories 或 negative_signals。
- maybe：不确定、信息不足、或弱相关。
- match_score 是 0-100 的整数。
- reason 用一句简短中文解释。
- interest_category 使用最贴近的中文类别，例如 体育比赛、演唱会、音乐会、话剧、展览、亲子、曲艺杂谈、其他。
- 不要因为字段缺失而编造事实。

当前偏好：
{profile_json}

活动列表：
{events_json}

输出格式：
{{
  "scores": [
    {{
      "index": 0,
      "decision": "keep",
      "match_score": 85,
      "interest_category": "体育比赛",
      "reason": "命中关注品类：体育比赛",
      "uncertainty": "medium"
    }}
  ]
}}
"""


def get_current_interest_profile() -> dict[str, Any]:
    return ensure_interest_profile()


def parse_preference_feedback(
    feedback: str,
    *,
    current_profile: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """Parse natural-language feedback into a structure-preserving update.

    The return shape mirrors the future LLM result: updated profile plus a
    compact summary of what changed. It errs on the side of visible, reversible
    edits instead of hidden inference.
    """
    profile = _profile_without_metadata(current_profile or ensure_interest_profile())
    if _llm_enabled():
        try:
            result = _parse_preference_feedback_with_llm(feedback, profile)
            structural_updates = _apply_structural_feedback(feedback, result["profile"])
            _merge_updates(result["updates"], structural_updates)
            saved = save_interest_profile(result["profile"])
            return {
                "profile": saved,
                "updates": result["updates"],
                "parser": f"llm:{LLM_MODEL}",
            }
        except Exception as e:
            print(f"[preferences] LLM feedback parse failed, fallback to rules: {e}")

    return _parse_preference_feedback_with_rules(feedback, profile)


def _parse_preference_feedback_with_rules(
    feedback: str,
    profile: dict[str, Any],
) -> dict[str, Any]:
    clauses = [part.strip() for part in re.split(r"[，,。；;\n]+", feedback) if part.strip()]

    added_include: list[str] = []
    added_exclude: list[str] = []
    added_ranking_preferences: list[str] = []
    added_artists: list[str] = []
    added_positive_signals: list[str] = []
    added_negative_signals: list[str] = []

    for clause in clauses:
        artists = _artists_in_text(clause)
        if artists:
            for artist in artists:
                _add_unique(added_artists, artist)
            continue

        categories = _categories_in_text(clause)
        is_lower_priority = bool(categories) and _has_any(clause, LOWER_PRIORITY_MARKERS) and "优先" in clause
        is_negative = _has_any(clause, NEGATIVE_MARKERS)
        is_positive = _has_any(clause, POSITIVE_MARKERS) or not is_negative

        if categories:
            if is_lower_priority:
                for category in categories:
                    preference = f"降低{category}优先级"
                    _add_unique(profile["ranking_preferences"], preference)
                    _add_unique(added_ranking_preferences, preference)
                continue
            if is_negative:
                for category in categories:
                    _add_unique(profile["exclude_categories"], category)
                    _remove_value(profile["include_categories"], category)
                    _add_unique(added_exclude, category)
            elif is_positive:
                for category in categories:
                    _add_unique(profile["include_categories"], category)
                    _remove_value(profile["exclude_categories"], category)
                    _add_unique(added_include, category)
            continue

        if is_negative:
            _add_unique(profile["negative_signals"], clause)
            _add_unique(added_negative_signals, clause)
        elif is_positive:
            _add_unique(profile["positive_signals"], clause)
            _add_unique(added_positive_signals, clause)

    saved = save_interest_profile(profile)
    return {
        "profile": saved,
        "updates": {
            "include_categories": added_include,
            "exclude_categories": added_exclude,
            "ranking_preferences": added_ranking_preferences,
            "artists": added_artists,
            "positive_signals": added_positive_signals,
            "negative_signals": added_negative_signals,
        },
        "parser": "rules-v1",
    }


def score_event_for_interest(
    event: dict[str, Any],
    profile: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """Return a keep/maybe/filter decision for one event."""
    return score_events_for_interest([event], profile)[0]


def score_events_for_interest(
    events: list[dict[str, Any]],
    profile: dict[str, Any] | None = None,
) -> list[dict[str, Any]]:
    """Score events in batches, preferring LLM classification with rules fallback."""
    profile = profile or ensure_interest_profile()
    if not events:
        return []
    if _llm_enabled():
        scores: list[dict[str, Any]] = []
        try:
            for start in range(0, len(events), LLM_BATCH_SIZE):
                chunk = events[start : start + LLM_BATCH_SIZE]
                scores.extend(_score_events_with_llm(chunk, profile))
            if len(scores) == len(events):
                return scores
        except Exception as e:
            print(f"[preferences] LLM event scoring failed, fallback to rules: {e}")

    return [_score_event_with_rules(event, profile) for event in events]


def _score_event_with_rules(
    event: dict[str, Any],
    profile: dict[str, Any],
) -> dict[str, Any]:
    category = infer_event_category(event)
    title = event.get("title") or ""
    exclude_categories = profile.get("exclude_categories") or []

    # Symmetric with the include branch below: filter if the inferred category
    # is excluded OR the title matches an excluded category's aliases. Without
    # the category check, a type-inferred category (e.g. 亲子) would slip through
    # whenever the title itself contains no alias word.
    if category in exclude_categories or _matches_any_category(title, exclude_categories):
        return {
            "decision": "filter",
            "match_score": 15,
            "interest_category": category,
            "reason": "命中排除品类",
            "uncertainty": "low",
        }

    if category in (profile.get("include_categories") or []):
        return {
            "decision": "keep",
            "match_score": 85,
            "interest_category": category,
            "reason": f"命中关注品类：{category}",
            "uncertainty": "medium",
        }

    if _matches_any_category(title, profile.get("include_categories") or []):
        return {
            "decision": "keep",
            "match_score": 78,
            "interest_category": category,
            "reason": "标题命中关注信号",
            "uncertainty": "medium",
        }

    return {
        "decision": "maybe",
        "match_score": 45,
        "interest_category": category,
        "reason": "未命中明确关注或排除品类",
        "uncertainty": "high",
    }


def _parse_preference_feedback_with_llm(
    feedback: str,
    profile: dict[str, Any],
) -> dict[str, Any]:
    payload = _call_deepseek_json(
        FEEDBACK_PROMPT.format(
            profile_json=json.dumps(profile, ensure_ascii=False, indent=2),
            feedback=feedback,
        ),
        max_tokens=2000,
    )
    next_profile = _normalize_profile(payload.get("profile") or profile)
    updates = _normalize_updates(payload.get("updates") or {})
    return {"profile": next_profile, "updates": updates}


def _score_events_with_llm(
    events: list[dict[str, Any]],
    profile: dict[str, Any],
) -> list[dict[str, Any]]:
    compact_events = [_compact_event(event, idx) for idx, event in enumerate(events)]
    payload = _call_deepseek_json(
        SCORING_PROMPT.format(
            profile_json=json.dumps(_profile_without_metadata(profile), ensure_ascii=False, indent=2),
            events_json=json.dumps(compact_events, ensure_ascii=False, indent=2),
        ),
        max_tokens=4000,
    )
    raw_scores = payload.get("scores")
    if not isinstance(raw_scores, list):
        raise ValueError("scores is not a list")

    scores_by_index: dict[int, dict[str, Any]] = {}
    for raw in raw_scores:
        if not isinstance(raw, dict):
            continue
        try:
            idx = int(raw.get("index"))
        except (TypeError, ValueError):
            continue
        if 0 <= idx < len(events):
            scores_by_index[idx] = _normalize_score(raw)

    return [
        scores_by_index.get(idx) or _score_event_with_rules(event, profile)
        for idx, event in enumerate(events)
    ]


def _call_deepseek_json(prompt: str, *, max_tokens: int) -> dict[str, Any]:
    api_key = os.environ.get("DEEPSEEK_API_KEY")
    if not api_key:
        raise RuntimeError("DEEPSEEK_API_KEY is missing")

    from openai import OpenAI

    client = OpenAI(
        api_key=api_key,
        base_url=os.environ.get("DEEPSEEK_BASE_URL", "https://api.deepseek.com"),
        timeout=float(os.environ.get("SHOW_TRACE_PREFERENCES_TIMEOUT", "30")),
    )
    resp = client.chat.completions.create(
        model=LLM_MODEL,
        messages=[{"role": "user", "content": prompt}],
        response_format={"type": "json_object"},
        max_tokens=max_tokens,
        temperature=0.0,
    )
    reply = resp.choices[0].message.content or ""
    payload = json.loads(reply)
    if not isinstance(payload, dict):
        raise ValueError("LLM response is not an object")
    return payload


def _llm_enabled() -> bool:
    return (
        os.environ.get("SHOW_TRACE_PREFERENCES_LLM", "1").lower()
        not in {"0", "false", "no"}
        and bool(os.environ.get("DEEPSEEK_API_KEY"))
    )


def infer_event_category(event: dict[str, Any]) -> str:
    title = event.get("title") or ""
    event_type = event.get("type") or ""

    for category, aliases in CATEGORY_ALIASES.items():
        if any(alias in title for alias in aliases):
            return category

    if event_type == "concert":
        return "演唱会"
    if event_type == "exhibition":
        return "展览"
    if event_type == "activity":
        return "活动"
    return "其他"


def _profile_without_metadata(profile: dict[str, Any]) -> dict[str, Any]:
    return {
        "city": profile.get("city") or "上海",
        "include_categories": list(profile.get("include_categories") or []),
        "exclude_categories": list(profile.get("exclude_categories") or []),
        "ranking_preferences": list(profile.get("ranking_preferences") or []),
        "negative_signals": list(profile.get("negative_signals") or []),
        "positive_signals": list(profile.get("positive_signals") or []),
    }


def _normalize_profile(profile: dict[str, Any]) -> dict[str, Any]:
    current = _profile_without_metadata(profile)
    return {
        "city": str(current.get("city") or "上海"),
        "include_categories": _unique_strings(current.get("include_categories")),
        "exclude_categories": _unique_strings(current.get("exclude_categories")),
        "ranking_preferences": _unique_strings(current.get("ranking_preferences")),
        "negative_signals": _unique_strings(current.get("negative_signals")),
        "positive_signals": _unique_strings(current.get("positive_signals")),
    }


def _normalize_updates(updates: dict[str, Any]) -> dict[str, list[str]]:
    return {
        "include_categories": _unique_strings(updates.get("include_categories")),
        "exclude_categories": _unique_strings(updates.get("exclude_categories")),
        "ranking_preferences": _unique_strings(updates.get("ranking_preferences")),
        "artists": _unique_strings(updates.get("artists")),
        "positive_signals": _unique_strings(updates.get("positive_signals")),
        "negative_signals": _unique_strings(updates.get("negative_signals")),
    }


def _apply_structural_feedback(feedback: str, profile: dict[str, Any]) -> dict[str, list[str]]:
    updates = {
        "ranking_preferences": [],
        "artists": [],
    }
    clauses = [part.strip() for part in re.split(r"[，,。；;\n]+", feedback) if part.strip()]
    for clause in clauses:
        for artist in _artists_in_text(clause):
            _add_unique(updates["artists"], artist)

        categories = _categories_in_text(clause)
        if categories and _has_any(clause, LOWER_PRIORITY_MARKERS) and "优先" in clause:
            for category in categories:
                preference = f"降低{category}优先级"
                _add_unique(profile["ranking_preferences"], preference)
                _add_unique(updates["ranking_preferences"], preference)
    return updates


def _merge_updates(target: dict[str, list[str]], source: dict[str, list[str]]) -> None:
    for key, values in source.items():
        existing = target.setdefault(key, [])
        for value in values:
            _add_unique(existing, value)


def _normalize_score(raw: dict[str, Any]) -> dict[str, Any]:
    decision = str(raw.get("decision") or "maybe")
    if decision not in ALLOWED_DECISIONS:
        decision = "maybe"
    try:
        match_score = int(raw.get("match_score"))
    except (TypeError, ValueError):
        match_score = 45
    match_score = max(0, min(100, match_score))

    uncertainty = str(raw.get("uncertainty") or "medium")
    if uncertainty not in ALLOWED_UNCERTAINTY:
        uncertainty = "medium"

    return {
        "decision": decision,
        "match_score": match_score,
        "interest_category": str(raw.get("interest_category") or "其他"),
        "reason": str(raw.get("reason") or "LLM 未提供理由"),
        "uncertainty": uncertainty,
    }


def _compact_event(event: dict[str, Any], idx: int) -> dict[str, Any]:
    return {
        "index": idx,
        "type": event.get("type"),
        "title": event.get("title"),
        "artist": event.get("artist"),
        "city": event.get("city"),
        "venue": event.get("venue"),
        "event_date": event.get("event_date"),
        "price_info": event.get("price_info"),
        "source": event.get("source"),
        "discovered_via": event.get("discovered_via"),
    }


def _unique_strings(values: Any) -> list[str]:
    if not isinstance(values, list):
        return []
    result: list[str] = []
    for value in values:
        text = str(value).strip()
        if text and text not in result:
            result.append(text)
    return result


def _categories_in_text(text: str) -> list[str]:
    found: list[str] = []
    for category, aliases in CATEGORY_ALIASES.items():
        if category in text or any(alias in text for alias in aliases):
            _add_unique(found, category)
    return found


def _matches_any_category(text: str, categories: list[str]) -> bool:
    for category in categories:
        aliases = CATEGORY_ALIASES.get(category, [category])
        if category in text or any(alias in text for alias in aliases):
            return True
    return False


def _artists_in_text(text: str) -> list[str]:
    found: list[str] = []
    for match in ARTIST_ADD_PATTERN.finditer(text):
        artist = match.group(1).strip(" ，,。；;")
        if artist:
            _add_unique(found, artist)
    return found


def _has_any(text: str, markers: list[str]) -> bool:
    return any(marker in text for marker in markers)


def _add_unique(values: list[str], value: str) -> None:
    if value not in values:
        values.append(value)


def _remove_value(values: list[str], value: str) -> None:
    while value in values:
        values.remove(value)
