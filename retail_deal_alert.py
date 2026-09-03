#!/usr/bin/env python3
"""
Retail Deal Alert (Walmart / Target / Lowe's / Menards)
----------------------------------------------------------
Walmart, Target, Lowe's, and Menards don't offer public deal feeds and
actively block scrapers, so this watches Slickdeals instead - a
deal-aggregator site with public RSS search feeds, filtered to those
four retailers. When a new matching deal posts, you get a push
notification straight to your phone via ntfy.sh (free, no signup).

GETTING ALERTS ON YOUR PHONE
------------------------------
1. Install the "ntfy" app (App Store or Google Play).
2. In the app, tap "+" and subscribe to a topic name only you know,
   e.g. "kadens-retail-deals-8f2x" (topics aren't private - anyone who
   knows the exact name can see posts to it, so make it hard to guess).
3. Set NTFY_TOPIC below to that name.
"""

import json
import re
import xml.etree.ElementTree as ET
from pathlib import Path

import requests

# ============== CONFIG - EDIT THIS ==============

NTFY_TOPIC = "deal-alert1"  # your ntfy topic name

STORES = ["walmart", "target", "lowes", "menards"]

# Optional: only alert on deals whose titles also mention one of these
KEYWORD_FILTER = []  # e.g. ["clearance", "tool", "electronics"]

# ============== END CONFIG ==============

SEEN_FILE = Path(__file__).parent / "seen_deals.json"
SLICKDEALS_RSS = "https://slickdeals.net/newsearch.php"


def load_seen():
    if SEEN_FILE.exists():
        return set(json.loads(SEEN_FILE.read_text()))
    return set()


def save_seen(seen_ids):
    SEEN_FILE.write_text(json.dumps(list(seen_ids)))


def fetch_deals(store):
    params = {"rss": "1", "q": store, "sort": "newest"}
    resp = requests.get(SLICKDEALS_RSS, params=params, timeout=15,
                         headers={"User-Agent": "Mozilla/5.0"})
    resp.raise_for_status()

    root = ET.fromstring(resp.content)
    deals = []
    for item in root.findall(".//item"):
        title_el = item.find("title")
        link_el = item.find("link")
        if title_el is None or link_el is None:
            continue
        title = (title_el.text or "").strip()
        link = (link_el.text or "").strip()

        if KEYWORD_FILTER and not any(k.lower() in title.lower() for k in KEYWORD_FILTER):
            continue

        deal_id = re.sub(r"\D", "", link) or link
        deals.append({"id": f"{store}:{deal_id}", "title": title, "link": link, "store": store})
    return deals


def notify_phone(title, message, link):
    try:
        requests.post(
            f"https://ntfy.sh/{NTFY_TOPIC}",
            data=message.encode("utf-8"),
            headers={"Title": title, "Click": link, "Tags": "moneybag"},
            timeout=10,
        )
    except Exception as e:
        print(f"[phone notify failed: {e}]")


def main():
    seen = load_seen()
    new_seen = set(seen)

    for store in STORES:
        try:
            deals = fetch_deals(store)
        except Exception as e:
            print(f"Error fetching '{store}': {e}")
            continue

        for deal in deals:
            if deal["id"] in seen:
                continue
            new_seen.add(deal["id"])

            title = f"New {deal['store'].title()} deal"
            print(f"{title}: {deal['title']}\n{deal['link']}\n")
            notify_phone(title, deal["title"], deal["link"])

    save_seen(new_seen)


if __name__ == "__main__":
    main()
