#!/usr/bin/env python3
"""Generic ecommerce candidate scorer.

This script uses only generic scoring. It does not contain category-specific
rules. It helps rank user-provided candidates based on must-have terms, avoid
terms, budget, review risks, and general fit signals.
"""

from __future__ import annotations

import argparse
import json
import re
from dataclasses import dataclass, asdict
from pathlib import Path
from typing import Any


POSITIVE_SIGNALS = [
    "耐用", "稳定", "好用", "方便", "轻便", "不重", "安静", "低噪音", "易清洗",
    "省空间", "小巧", "安全", "正品", "质保", "保修", "退换", "旗舰店",
    "做工好", "材质好", "性价比", "清晰", "可调", "兼容"
]

RISK_SIGNALS = [
    "容易坏", "坏了", "不耐用", "异味", "刺鼻", "掉色", "变形", "尺寸不准",
    "虚标", "假货", "客服差", "退货难", "不安全", "漏电", "噪音大",
    "太重", "难清洗", "不好用", "不稳", "不兼容", "智商税"
]


@dataclass
class CandidateScore:
    rank: int
    name: str
    score: float
    verdict: str
    fit_points: list[str]
    risks: list[str]
    price: Any = None
    url: str | None = None


def text_of(candidate: dict[str, Any]) -> str:
    parts: list[str] = []
    for key in ("name", "title", "specs", "review_summary", "notes", "shop", "brand"):
        value = candidate.get(key)
        if isinstance(value, list):
            parts.extend(map(str, value))
        elif value is not None:
            parts.append(str(value))
    return " ".join(parts)


def contains_any(text: str, keywords: list[str]) -> list[str]:
    hits = []
    seen = set()
    for kw in keywords:
        if re.search(re.escape(kw), text, re.IGNORECASE):
            key = kw.lower()
            if key not in seen:
                seen.add(key)
                hits.append(kw)
    return hits


def parse_terms(value: str | None) -> list[str]:
    if not value:
        return []
    return [x.strip() for x in re.split(r"[,，、\s]+", value) if x.strip()]


def score_candidate(candidate: dict[str, Any], must_terms: list[str], avoid_terms: list[str], budget: float | None) -> CandidateScore:
    blob = text_of(candidate)

    must_hits = contains_any(blob, must_terms)
    avoid_hits = contains_any(blob, avoid_terms)
    positive_hits = contains_any(blob, POSITIVE_SIGNALS)
    risk_hits = contains_any(blob, RISK_SIGNALS)

    score = 50.0

    if must_terms:
        score += (len(must_hits) / max(len(must_terms), 1)) * 25
        missing = [term for term in must_terms if term not in must_hits]
        if missing:
            score -= min(len(missing) * 8, 24)
    else:
        score += min(len(positive_hits) * 3, 18)

    score += min(len(positive_hits) * 2, 12)
    score -= min(len(risk_hits) * 8, 32)
    score -= min(len(avoid_hits) * 12, 36)

    price = candidate.get("price")
    if isinstance(price, (int, float)) and budget is not None:
        if price <= budget:
            score += 8
        elif price <= budget * 1.15:
            score += 2
        else:
            score -= 12

    if candidate.get("url"):
        score += 2
    if candidate.get("review_summary"):
        score += 3
    if candidate.get("specs"):
        score += 3

    score = max(0, min(100, score))

    if score >= 85:
        verdict = "直接买"
    elif score >= 75:
        verdict = "备选"
    elif score >= 60:
        verdict = "谨慎考虑"
    else:
        verdict = "不推荐"

    fit_points = must_hits + positive_hits
    if not fit_points:
        fit_points = ["信息不足，需要补充规格、评价或使用场景"]
    risks = risk_hits + avoid_hits
    if not risks:
        risks = ["未发现明显风险词；仍需查看近期差评"]

    return CandidateScore(
        rank=0,
        name=str(candidate.get("name") or candidate.get("title") or "未命名候选"),
        score=round(score, 1),
        verdict=verdict,
        fit_points=fit_points[:8],
        risks=risks[:8],
        price=price,
        url=candidate.get("url"),
    )


def render_markdown(scores: list[CandidateScore]) -> str:
    lines = ["| 排名 | 候选 | 分数 | 适合点 | 风险 | 结论 |", "|---:|---|---:|---|---|---|"]
    for item in scores:
        lines.append(
            f"| {item.rank} | {item.name} | {item.score} | {'、'.join(item.fit_points)} | {'、'.join(item.risks)} | {item.verdict} |"
        )
    return "\n".join(lines)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Evaluate generic shopping candidates.")
    parser.add_argument("--input", required=True, help="Path to candidates JSON array.")
    parser.add_argument("--must", default="", help="Comma/space separated must-have terms.")
    parser.add_argument("--avoid", default="", help="Comma/space separated avoid terms.")
    parser.add_argument("--budget", type=float, default=None, help="Optional maximum budget.")
    parser.add_argument("--format", choices=["json", "markdown"], default="markdown")
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    data = json.loads(Path(args.input).read_text(encoding="utf-8"))
    if not isinstance(data, list):
        raise ValueError("Input must be a JSON array of candidate objects.")
    must_terms = parse_terms(args.must)
    avoid_terms = parse_terms(args.avoid)
    scores = [score_candidate(x, must_terms, avoid_terms, args.budget) for x in data]
    scores.sort(key=lambda x: x.score, reverse=True)
    for idx, item in enumerate(scores, start=1):
        item.rank = idx
    if args.format == "json":
        print(json.dumps([asdict(x) for x in scores], ensure_ascii=False, indent=2))
    else:
        print(render_markdown(scores))


if __name__ == "__main__":
    main()
