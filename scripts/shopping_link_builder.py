#!/usr/bin/env python3
"""Build shopping search and item entry links for Chinese ecommerce platforms.

The script does not scrape platforms and does not verify product data. It creates
search or item-page entry URLs for the assistant to include in a shopping decision.
"""

from __future__ import annotations

import argparse
import json
import re
from dataclasses import dataclass, asdict
from typing import Iterable
from urllib.parse import quote_plus, urlparse, parse_qs


SUPPORTED_PLATFORMS = {"taobao", "tmall", "jd", "pdd", "xiaohongshu"}


@dataclass
class ShoppingLinks:
    platform: str
    query: str | None = None
    item_id: str | None = None
    search_url: str | None = None
    mobile_search_url: str | None = None
    app_search_deeplink: str | None = None
    item_url: str | None = None
    mobile_item_url: str | None = None
    app_item_deeplink: str | None = None
    note: str = "搜索入口不代表已核验商品；商品页链接优先，最终下单前仍需用户确认规格和售后。"


def normalize_terms(values: Iterable[str] | None) -> list[str]:
    terms: list[str] = []
    for value in values or []:
        value = str(value).strip()
        if value and value not in terms:
            terms.append(value)
    return terms


def build_query(query: str, must: Iterable[str] | None = None, avoid: Iterable[str] | None = None) -> str:
    terms = []
    terms.extend(str(query).split())
    terms.extend(normalize_terms(must))
    seen = set()
    clean = []
    for term in terms:
        if term and term not in seen:
            seen.add(term)
            clean.append(term)
    return " ".join(clean)


def build_search_links(platform: str, query: str) -> ShoppingLinks:
    platform = platform.lower()
    if platform not in SUPPORTED_PLATFORMS:
        raise ValueError(f"Unsupported platform: {platform}")
    encoded = quote_plus(query)

    if platform in {"taobao", "tmall"}:
        return ShoppingLinks(
            platform=platform,
            query=query,
            search_url=f"https://s.taobao.com/search?q={encoded}",
            mobile_search_url=f"https://h5.m.taobao.com/search.htm?q={encoded}",
            app_search_deeplink=f"taobao://s.taobao.com/search?q={encoded}",
        )
    if platform == "jd":
        return ShoppingLinks(
            platform=platform,
            query=query,
            search_url=f"https://search.jd.com/Search?keyword={encoded}",
            mobile_search_url=f"https://so.m.jd.com/ware/search.action?keyword={encoded}",
            app_search_deeplink=None,
        )
    if platform == "pdd":
        return ShoppingLinks(
            platform=platform,
            query=query,
            search_url=f"https://mobile.yangkeduo.com/search_result.html?search_key={encoded}",
            mobile_search_url=f"https://mobile.yangkeduo.com/search_result.html?search_key={encoded}",
            app_search_deeplink=None,
        )
    if platform == "xiaohongshu":
        return ShoppingLinks(
            platform=platform,
            query=query,
            search_url=f"https://www.xiaohongshu.com/search_result?keyword={encoded}",
            mobile_search_url=f"https://www.xiaohongshu.com/search_result?keyword={encoded}",
            app_search_deeplink=None,
        )
    raise AssertionError("unreachable")


def extract_item_id(value: str) -> str | None:
    value = value.strip()
    if re.fullmatch(r"[A-Za-z0-9_-]{4,40}", value):
        return value
    parsed = urlparse(value)
    params = parse_qs(parsed.query)
    for key in ("id", "itemId", "item_id", "sku", "skuId", "goods_id", "goodsId"):
        if key in params and params[key]:
            return params[key][0]
    match = re.search(r"(?:id|itemId|item_id|sku|skuId|goods_id|goodsId)[=/]([A-Za-z0-9_-]{4,40})", value)
    if match:
        return match.group(1)
    return None


def build_item_links(platform: str, item_id_or_url: str) -> ShoppingLinks:
    platform = platform.lower()
    if platform not in SUPPORTED_PLATFORMS:
        raise ValueError(f"Unsupported platform: {platform}")
    item_id = extract_item_id(item_id_or_url)
    if not item_id:
        raise ValueError("Could not extract an item id from the input.")

    if platform in {"taobao", "tmall"}:
        return ShoppingLinks(
            platform=platform,
            item_id=item_id,
            item_url=f"https://item.taobao.com/item.htm?id={item_id}",
            mobile_item_url=f"https://h5.m.taobao.com/awp/core/detail.htm?id={item_id}",
            app_item_deeplink=f"taobao://item.taobao.com/item.htm?id={item_id}",
        )
    if platform == "jd":
        return ShoppingLinks(
            platform=platform,
            item_id=item_id,
            item_url=f"https://item.jd.com/{item_id}.html",
            mobile_item_url=f"https://item.m.jd.com/product/{item_id}.html",
        )
    if platform == "pdd":
        return ShoppingLinks(
            platform=platform,
            item_id=item_id,
            item_url=f"https://mobile.yangkeduo.com/goods.html?goods_id={item_id}",
            mobile_item_url=f"https://mobile.yangkeduo.com/goods.html?goods_id={item_id}",
        )
    if platform == "xiaohongshu":
        return ShoppingLinks(
            platform=platform,
            item_id=item_id,
            item_url=f"https://www.xiaohongshu.com/search_result?keyword={quote_plus(item_id)}",
            mobile_item_url=f"https://www.xiaohongshu.com/search_result?keyword={quote_plus(item_id)}",
        )
    raise AssertionError("unreachable")


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Build shopping search or item links.")
    sub = parser.add_subparsers(dest="command", required=True)

    search = sub.add_parser("search", help="Build search entry links.")
    search.add_argument("--platform", default="taobao", choices=sorted(SUPPORTED_PLATFORMS))
    search.add_argument("--query", required=True, help="Natural-language query or keywords.")
    search.add_argument("--must", nargs="*", default=[], help="Must-have terms to add.")
    search.add_argument("--avoid", nargs="*", default=[], help="Avoid terms to return in metadata.")

    item = sub.add_parser("item", help="Build item-page entry links.")
    item.add_argument("--platform", default="taobao", choices=sorted(SUPPORTED_PLATFORMS))
    item.add_argument("--item-id", required=True, help="Item id or URL containing an item id.")

    return parser.parse_args()


def main() -> None:
    args = parse_args()
    if args.command == "search":
        query = build_query(args.query, args.must, args.avoid)
        payload = asdict(build_search_links(args.platform, query))
        payload["avoid_terms"] = normalize_terms(args.avoid)
        print(json.dumps(payload, ensure_ascii=False, indent=2))
    elif args.command == "item":
        print(json.dumps(asdict(build_item_links(args.platform, args.item_id)), ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
