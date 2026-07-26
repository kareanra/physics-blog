import os
import time
import urllib.request
import xml.etree.ElementTree as ET
from datetime import datetime, timedelta, timezone
from email.utils import parsedate_to_datetime

from newsletter_common import db
from newsletter_common.email import send as send_email

FEED_URL = os.environ["FEED_URL"]
API_BASE_URL = os.environ["API_BASE_URL"]
LOOKBACK_DAYS = int(os.environ.get("LOOKBACK_DAYS", "7"))
SEND_INTERVAL_SECONDS = float(os.environ.get("SEND_INTERVAL_SECONDS", "0.2"))


def _fetch_feed_items() -> list[dict]:
    with urllib.request.urlopen(FEED_URL, timeout=15) as resp:
        raw = resp.read()

    root = ET.fromstring(raw)
    items = []
    for item in root.findall("./channel/item"):
        link = (item.findtext("link") or "").strip()
        title = (item.findtext("title") or "").strip()
        description = (item.findtext("description") or "").strip()
        pub_date_raw = item.findtext("pubDate")
        if not link or not title or not pub_date_raw:
            continue
        try:
            pub_date = parsedate_to_datetime(pub_date_raw)
        except (TypeError, ValueError):
            continue
        if pub_date.tzinfo is None:
            pub_date = pub_date.replace(tzinfo=timezone.utc)
        items.append({"link": link, "title": title, "description": description, "pub_date": pub_date})
    return items


def _render_digest(items: list[dict]) -> tuple[str, str, str]:
    count = len(items)
    subject = f"{count} new post{'s' if count != 1 else ''} on Computational Physics Notes"

    text_parts = ["New posts this week:\n"]
    html_parts = ["<p>New posts this week:</p><ul>"]
    for item in items:
        text_parts.append(f"- {item['title']}\n  {item['link']}\n")
        html_parts.append(
            f'<li><a href="{item["link"]}">{item["title"]}</a>'
            f'<br>{item["description"]}</li>'
        )
    html_parts.append("</ul>")

    return subject, "\n".join(text_parts), "".join(html_parts)


def handler(_event, _context):
    items = _fetch_feed_items()

    cutoff = datetime.now(timezone.utc) - timedelta(days=LOOKBACK_DAYS)
    sent_links = db.get_sent_links()
    new_items = [i for i in items if i["pub_date"] >= cutoff and i["link"] not in sent_links]

    if not new_items:
        print("No new posts in the lookback window; skipping digest send.")
        return {"sent": 0, "recipients": 0}

    subject, text_body, html_body = _render_digest(new_items)
    subscribers = db.list_confirmed_subscribers()

    sent_count = 0
    for sub in subscribers:
        unsubscribe_url = f"{API_BASE_URL}/unsubscribe?token={sub['unsubscribeToken']}"
        try:
            send_email(
                to_address=sub["email"],
                subject=subject,
                text_body=text_body,
                html_body=html_body,
                unsubscribe_url=unsubscribe_url,
            )
            sent_count += 1
        except Exception as exc:  # noqa: BLE001 - keep sending to the rest of the list
            print(f"Failed to send digest to {sub['email']}: {exc}")
        time.sleep(SEND_INTERVAL_SECONDS)

    db.add_sent_links({i["link"] for i in new_items})
    return {"sent": sent_count, "recipients": len(subscribers), "posts": [i["link"] for i in new_items]}
