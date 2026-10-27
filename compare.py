#!/usr/bin/env python3
"""Compare second-hand prices across OLX, Wallapop, Leboncoin, Custojusto and Facebook Marketplace.

Usage:
  python compare.py "iphone 13" --sources olx,wallapop --max-price 400
  python compare.py "sofa" --cheapest --limit 10
  python compare.py "ps5" --watch 300        # re-check every 5 minutes, print only new listings
"""
import argparse, os, sys, time
import requests

HOST = os.environ.get("RAPIDAPI_HOST", "classifieds-listings-api.p.rapidapi.com")
KEY = os.environ.get("RAPIDAPI_KEY")
BASE = "https://" + HOST
HEAD = {"X-RapidAPI-Key": KEY or "", "X-RapidAPI-Host": HOST}


def call(path, params):
    r = requests.get(BASE + path, headers=HEAD, params={k: v for k, v in params.items() if v not in (None, "")}, timeout=60)
    r.raise_for_status()
    body = r.json()
    if body.get("error"):
        sys.exit("API error: " + str(body["error"]))
    return body["data"]


def money(v, cur="EUR"):
    return "-" if v is None else f"{v:,.0f} {cur}"


def show_compare(data):
    print(f"{'source':<12}{'count':>6}{'min':>10}{'avg':>10}{'max':>10}")
    for src, s in sorted(data["bySource"].items(), key=lambda kv: kv[1].get("min") or 1e12):
        print(f"{src:<12}{s['count']:>6}{money(s['min']):>10}{money(s['avg']):>10}{money(s['max']):>10}")
    o = data["overall"]
    print(f"{'ALL':<12}{o['count']:>6}{money(o['min']):>10}{money(o['avg']):>10}{money(o['max']):>10}")
    for e in data.get("errors", []):
        print("  (source failed, partial result):", e)


def show_listings(rows, limit):
    for l in rows[:limit]:
        print(f"{money(l['price'], l.get('currency') or 'EUR'):>10}  [{l['source']}]  {l['title'][:70]}\n{'':>12}{l['url']}")


def main():
    p = argparse.ArgumentParser()
    p.add_argument("query")
    p.add_argument("--sources", default="")
    p.add_argument("--min-price")
    p.add_argument("--max-price")
    p.add_argument("--limit", type=int, default=20)
    p.add_argument("--cheapest", action="store_true", help="list the cheapest listings instead of per-source stats")
    p.add_argument("--watch", type=int, metavar="SECONDS", help="poll and print only new listings")
    a = p.parse_args()
    if not KEY:
        sys.exit("Set RAPIDAPI_KEY (see .env.example)")
    params = {"query": a.query, "sources": a.sources, "minPrice": a.min_price, "maxPrice": a.max_price, "limit": a.limit}
    seen = set()
    while True:
        if a.watch:
            data = call("/api/search/cheapest", params)
            fresh = [l for l in data["listings"] if l["id"] not in seen]
            seen.update(l["id"] for l in data["listings"])
            if fresh:
                print(time.strftime("%H:%M:%S"), f"{len(fresh)} new")
                show_listings(fresh, a.limit)
            time.sleep(a.watch)
        elif a.cheapest:
            show_listings(call("/api/search/cheapest", params)["listings"], a.limit)
            return
        else:
            show_compare(call("/api/search/compare", params))
            return


if __name__ == "__main__":
    main()
