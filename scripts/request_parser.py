#!/usr/bin/env python3
"""Lightweight parser for one-sentence Chinese shopping requests.

This parser is generic. It does not contain category-specific rules. It creates
a first-pass structured brief for ChatGPT to review and improve.
"""

from __future__ import annotations

import argparse
import json
import re
from typing import Any


POSITIVE_PATTERNS = [
    "便宜", "性价比", "耐用", "轻便", "好看", "安静", "低噪音",
    "易清洗", "好收纳", "小巧", "安全", "防水", "防泼水", "快",
    "省电", "适合送礼", "适合通勤", "适合宿舍", "适合租房",
    "长期用", "应急", "省空间", "舒服", "稳定", "方便"
]

NEGATIVE_PATTERNS = [
    "不要太贵", "不要太重", "不要太丑", "不要占地方", "不要智商税",
    "别太贵", "别太重", "别太丑", "别占地方", "不想要", "不接受",
    "避开", "不要"
]

PLATFORM_PATTERNS = {
    "taobao": ["淘宝", "天猫", "淘系"],
    "jd": ["京东"],
    "pdd": ["拼多多", "pdd", "PDD"],
    "xiaohongshu": ["小红书"],
}


def extract_budget(text: str) -> dict[str, Any] | None:
    patterns = [
        r"预算\s*(\d+(?:\.\d+)?)\s*(?:元|块|rmb|RMB)?\s*(?:以内|以下|内)?",
        r"(\d+(?:\.\d+)?)\s*(?:元|块|rmb|RMB)?\s*(?:以内|以下|内)",
        r"不超过\s*(\d+(?:\.\d+)?)\s*(?:元|块)?",
        r"控制在\s*(\d+(?:\.\d+)?)\s*(?:元|块)?",
    ]
    for pattern in patterns:
        match = re.search(pattern, text)
        if match:
            return {"max": float(match.group(1)), "currency": "CNY"}
    return None


def detect_platform(text: str) -> str:
    for platform, hints in PLATFORM_PATTERNS.items():
        if any(hint in text for hint in hints):
            return platform
    return "taobao"


def unique_in_order(items: list[str]) -> list[str]:
    seen = set()
    output = []
    for item in items:
        if item and item not in seen:
            seen.add(item)
            output.append(item)
    return output


def extract_preferences(text: str) -> tuple[list[str], list[str]]:
    positives = [p for p in POSITIVE_PATTERNS if p.lower() in text.lower()]
    negatives = [p for p in NEGATIVE_PATTERNS if p.lower() in text.lower()]

    # Convert common negative wording into useful positive preferences too.
    negative_to_positive = {
        "不要太贵": "价格合理",
        "别太贵": "价格合理",
        "不要太重": "轻便",
        "别太重": "轻便",
        "不要太丑": "外观可接受",
        "别太丑": "外观可接受",
        "不要占地方": "省空间",
        "别占地方": "省空间",
        "不要智商税": "实用",
    }
    for neg in negatives:
        if neg in negative_to_positive:
            positives.append(negative_to_positive[neg])

    return unique_in_order(positives), unique_in_order(negatives)


def extract_product_guess(text: str) -> str:
    cleaned = text
    cleaned = re.sub(r"预算\s*\d+(?:\.\d+)?\s*(?:元|块|rmb|RMB)?\s*(?:以内|以下|内)?", "", cleaned, flags=re.I)
    cleaned = re.sub(r"\d+(?:\.\d+)?\s*(?:元|块|rmb|RMB)?\s*(?:以内|以下|内)", "", cleaned, flags=re.I)
    cleaned = re.sub(r"不超过\s*\d+(?:\.\d+)?\s*(?:元|块)?", "", cleaned)
    cleaned = re.sub(r"控制在\s*\d+(?:\.\d+)?\s*(?:元|块)?", "", cleaned)
    cleaned = re.sub(r"我想买|想买|帮我买|给我推荐|推荐一个|推荐一款|求推荐|买一个|买个", "", cleaned)
    cleaned = cleaned.strip(" ，。,.")
    return cleaned[:80] or text[:80]


def parse_request(text: str) -> dict[str, Any]:
    positives, negatives = extract_preferences(text)
    return {
        "raw_request": text,
        "product_guess": extract_product_guess(text),
        "budget": extract_budget(text),
        "must_have_or_preferences": positives,
        "avoid_or_negative_constraints": negatives,
        "platform": detect_platform(text),
        "decision_goal": "best_fit",
        "assumptions_to_check": [
            "默认用户希望减少选择成本，而不是获得尽可能多的链接",
            "默认最终仍由用户确认颜色、规格、地址、售后和付款"
        ],
    }


def main() -> None:
    parser = argparse.ArgumentParser(description="Parse a generic Chinese shopping request.")
    parser.add_argument("text", help="User shopping request.")
    args = parser.parse_args()
    print(json.dumps(parse_request(args.text), ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
