#!/usr/bin/env python3
"""Send a daily Zhubei weather and international news briefing to Discord."""

from __future__ import annotations

import argparse
import html
import json
import os
import sys
import textwrap
import urllib.error
import urllib.parse
import urllib.request
import xml.etree.ElementTree as ET
from dataclasses import dataclass
from datetime import datetime, timedelta
from email.utils import parsedate_to_datetime
from zoneinfo import ZoneInfo


TAIPEI_TZ = ZoneInfo("Asia/Taipei")
LOCATION_NAME = "新竹縣竹北市"
ZHUBEI_LATITUDE = 24.8383
ZHUBEI_LONGITUDE = 121.0078
DISCORD_LIMIT = 1900

DEFAULT_NEWS_FEEDS = [
    ("紐約時報 World", "https://rss.nytimes.com/services/xml/rss/nyt/World.xml"),
    ("CNN World", "https://rss.cnn.com/rss/cnn_world.rss"),
    ("CNN Latest", "https://rss.cnn.com/rss/cnn_latest.rss"),
    (
        "CNN via Google News",
        "https://news.google.com/rss/search?q=site%3Acnn.com%2Fworld%20international%20news&hl=en-US&gl=US&ceid=US:en",
    ),
]

DEFAULT_TECH_FEEDS = [
    ("紐約時報 Technology", "https://rss.nytimes.com/services/xml/rss/nyt/Technology.xml"),
    ("CNN Tech", "https://news.google.com/rss/search?q=site%3Acnn.com%2Fbusiness%2Ftech%20technology&hl=en-US&gl=US&ceid=US:en"),
]

WEATHER_CODES = {
    0: "晴朗",
    1: "大致晴朗",
    2: "局部多雲",
    3: "陰天",
    45: "有霧",
    48: "霧淞",
    51: "毛毛雨",
    53: "毛毛雨",
    55: "毛毛雨",
    61: "小雨",
    63: "中雨",
    65: "大雨",
    66: "凍雨",
    67: "凍雨",
    71: "降雪",
    73: "降雪",
    75: "降雪",
    77: "雪粒",
    80: "短暫陣雨",
    81: "陣雨",
    82: "強陣雨",
    85: "陣雪",
    86: "強陣雪",
    95: "雷雨",
    96: "雷雨伴隨冰雹",
    99: "強雷雨伴隨冰雹",
}


@dataclass(frozen=True)
class NewsItem:
    source: str
    title: str
    summary: str
    link: str
    published: datetime | None


def fetch_text(url: str, timeout: int = 20) -> str:
    request = urllib.request.Request(
        url,
        headers={
            "User-Agent": "daily-discord-briefing/1.0 (+https://github.com/)",
            "Accept": "application/rss+xml, application/xml, text/xml, application/json, */*",
        },
    )
    with urllib.request.urlopen(request, timeout=timeout) as response:
        return response.read().decode(response.headers.get_content_charset() or "utf-8", errors="replace")


def post_discord(webhook_url: str, content: str) -> None:
    payload = json.dumps({"content": content}).encode("utf-8")
    request = urllib.request.Request(
        webhook_url,
        data=payload,
        headers={"Content-Type": "application/json", "User-Agent": "daily-discord-briefing/1.0"},
        method="POST",
    )
    with urllib.request.urlopen(request, timeout=20) as response:
        if response.status >= 300:
            raise RuntimeError(f"Discord webhook returned HTTP {response.status}")


def weather_summary() -> tuple[str, str]:
    params = urllib.parse.urlencode(
        {
            "latitude": ZHUBEI_LATITUDE,
            "longitude": ZHUBEI_LONGITUDE,
            "timezone": "Asia/Taipei",
            "daily": "weather_code,temperature_2m_max,temperature_2m_min,precipitation_probability_max",
            "forecast_days": 1,
        }
    )
    url = f"https://api.open-meteo.com/v1/forecast?{params}"
    data = json.loads(fetch_text(url))
    daily = data["daily"]

    code = int(daily["weather_code"][0])
    max_temp = round(float(daily["temperature_2m_max"][0]))
    min_temp = round(float(daily["temperature_2m_min"][0]))
    rain_chance = daily.get("precipitation_probability_max", [None])[0]
    condition = WEATHER_CODES.get(code, f"天氣代碼 {code}")

    if rain_chance is None:
        rain_text = "降雨機率未提供"
        note = "出門前可再看一次即時雷達。"
    else:
        rain_text = f"最高降雨機率 {round(float(rain_chance))}%"
        note = "建議帶傘。" if float(rain_chance) >= 50 else "通勤大致輕便，午後仍可留意雲量變化。"

    return f"{condition}，{min_temp}-{max_temp}°C，{rain_text}", note


def parse_datetime(value: str | None) -> datetime | None:
    if not value:
        return None
    try:
        parsed = parsedate_to_datetime(value)
        if parsed.tzinfo is None:
            parsed = parsed.replace(tzinfo=ZoneInfo("UTC"))
        return parsed.astimezone(TAIPEI_TZ)
    except (TypeError, ValueError):
        return None


def first_text(element: ET.Element, names: tuple[str, ...]) -> str:
    for name in names:
        found = element.find(name)
        if found is not None and found.text:
            return html.unescape(found.text.strip())
    for child in element:
        local_name = child.tag.rsplit("}", 1)[-1]
        if local_name in names and child.text:
            return html.unescape(child.text.strip())
    return ""


def first_link(element: ET.Element) -> str:
    direct = first_text(element, ("link", "id"))
    if direct:
        return direct
    for child in element:
        local_name = child.tag.rsplit("}", 1)[-1]
        if local_name == "link":
            href = child.attrib.get("href")
            if href:
                return href
    return ""


def clean_summary(value: str) -> str:
    text = html.unescape(value or "")
    text = " ".join(text.replace("<br>", " ").replace("<br/>", " ").split())
    while "<" in text and ">" in text:
        start = text.find("<")
        end = text.find(">", start)
        if end == -1:
            break
        text = f"{text[:start]} {text[end + 1:]}"
    return " ".join(text.split())


def translate_to_zh_tw(text: str) -> str:
    if not text:
        return ""

    query = urllib.parse.urlencode(
        {
            "client": "gtx",
            "sl": "auto",
            "tl": "zh-TW",
            "dt": "t",
            "q": text[:900],
        }
    )
    url = f"https://translate.googleapis.com/translate_a/single?{query}"
    try:
        data = json.loads(fetch_text(url, timeout=15))
        translated = "".join(part[0] for part in data[0] if part and part[0])
        return translated.strip() or text
    except (json.JSONDecodeError, KeyError, IndexError, TypeError, urllib.error.URLError, TimeoutError):
        return text


def parse_feed(source: str, url: str) -> list[NewsItem]:
    xml_text = fetch_text(url)
    root = ET.fromstring(xml_text)
    entries = root.findall(".//item") or root.findall(".//{http://www.w3.org/2005/Atom}entry")
    items: list[NewsItem] = []

    for entry in entries:
        title = first_text(entry, ("title",))
        summary = clean_summary(first_text(entry, ("description", "summary", "content")))
        link = first_link(entry)
        published = parse_datetime(first_text(entry, ("pubDate", "published", "updated")))
        if title and link:
            items.append(NewsItem(source=source, title=title, summary=summary, link=link, published=published))
    return items


def collect_news(feeds: list[tuple[str, str]], source_keywords: tuple[str, ...]) -> tuple[list[NewsItem], list[str]]:
    errors: list[str] = []
    items: list[NewsItem] = []

    feed_env = os.getenv("NEWS_FEEDS", "") if feeds == DEFAULT_NEWS_FEEDS else os.getenv("TECH_NEWS_FEEDS", "")
    active_feeds = feeds
    if feed_env:
        active_feeds = []
        for chunk in feed_env.split(","):
            if "=" not in chunk:
                continue
            name, url = chunk.split("=", 1)
            active_feeds.append((name.strip(), url.strip()))

    for source, url in active_feeds:
        try:
            items.extend(parse_feed(source, url))
        except (ET.ParseError, urllib.error.URLError, TimeoutError, ValueError) as exc:
            errors.append(f"{source}: {exc}")

    today = datetime.now(TAIPEI_TZ).date()
    recent_cutoff = datetime.now(TAIPEI_TZ) - timedelta(hours=36)
    items.sort(key=lambda item: item.published or datetime.min.replace(tzinfo=TAIPEI_TZ), reverse=True)
    recent_items = [item for item in items if item.published is None or item.published >= recent_cutoff or item.published.date() == today]
    candidates = recent_items or items
    selected: list[NewsItem] = []
    seen_titles: set[str] = set()

    def add_item(item: NewsItem) -> bool:
        normalized = " ".join(item.title.lower().split())
        if normalized in seen_titles:
            return False
        seen_titles.add(normalized)
        selected.append(item)
        return True

    for source_keyword in source_keywords:
        for item in candidates:
            if source_keyword in item.source and add_item(item):
                break

    for item in candidates:
        if len(selected) == 3:
            break
        add_item(item)

    return selected, errors


def add_news_section(lines: list[str], title: str, news: list[NewsItem]) -> None:
    lines.extend(["", title])
    if news:
        for index, item in enumerate(news, start=1):
            published = f"（{item.published:%m/%d %H:%M}）" if item.published else ""
            summary_source = item.summary if item.summary and item.summary != item.title else item.title
            zh_summary = translate_to_zh_tw(summary_source)
            lines.append(f"{index}. [{item.source}]{published}")
            lines.append(f"   摘要：{zh_summary}")
            lines.append(f"   連結：{item.link}")
    else:
        lines.append("目前無法取得新聞內容，請稍後手動檢查。")


def build_message() -> str:
    now = datetime.now(TAIPEI_TZ)
    weather, weather_note = weather_summary()
    world_news, world_errors = collect_news(DEFAULT_NEWS_FEEDS, ("紐約時報", "CNN"))
    tech_news, tech_errors = collect_news(DEFAULT_TECH_FEEDS, ("紐約時報", "CNN"))

    lines = [
        f"**每日早報｜{now:%Y-%m-%d} 09:00 台北時間**",
        "",
        f"**{LOCATION_NAME}天氣**",
        f"- {weather}",
        f"- 提醒：{weather_note}",
    ]

    add_news_section(lines, "**今日國際頭條 Top 3**", world_news)
    add_news_section(lines, "**今日科技頭條 Top 3**", tech_news)

    news_errors = world_errors + tech_errors
    if news_errors:
        lines.extend(["", "**資料來源提醒**"])
        for error in news_errors[:5]:
            lines.append(f"- {error}")

    return "\n".join(lines)


def split_message(content: str) -> list[str]:
    chunks: list[str] = []
    current = ""
    for paragraph in content.split("\n\n"):
        candidate = f"{current}\n\n{paragraph}".strip()
        if len(candidate) <= DISCORD_LIMIT:
            current = candidate
        else:
            if current:
                chunks.append(current)
            current = textwrap.shorten(paragraph, width=DISCORD_LIMIT, placeholder="...")
    if current:
        chunks.append(current)
    return chunks


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--dry-run", action="store_true", help="Print the Discord message instead of sending it.")
    args = parser.parse_args()

    message = build_message()
    if args.dry_run:
        print(message)
        return 0

    webhook_url = os.getenv("DISCORD_WEBHOOK_URL")
    if not webhook_url:
        print("Missing DISCORD_WEBHOOK_URL secret.", file=sys.stderr)
        return 1

    for chunk in split_message(message):
        post_discord(webhook_url, chunk)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
