#!/usr/bin/env python3
"""
episodes.json を元に、Podcast用RSS (feed.xml) を自動生成するスクリプト。

使い方:
    python generate_feed.py

入力: episodes.json (同じディレクトリに配置)
出力: docs/feed.xml
"""

import json
import os
from datetime import datetime, timezone
from email.utils import format_datetime
from xml.sax.saxutils import escape

INPUT_JSON = "episodes.json"
OUTPUT_DIR = "docs"
OUTPUT_FILE = os.path.join(OUTPUT_DIR, "feed.xml")


def parse_date(date_str: str) -> str:
    """'YYYY-MM-DD' を RFC 2822 形式 (RSSのpubDateに必要な形式) に変換する"""
    dt = datetime.strptime(date_str, "%Y-%m-%d").replace(tzinfo=timezone.utc)
    return format_datetime(dt)


def duration_to_seconds(duration: str) -> str:
    """'HH:MM:SS' をそのまま返す (iTunes:duration は HH:MM:SS or 秒数どちらも可)"""
    return duration


def build_feed(data: dict) -> str:
    podcast = data["podcast"]
    episodes = data["episodes"]

    base_url = f"https://{podcast['github_username']}.github.io/{podcast['repo_name']}"
    feed_url = f"{base_url}/feed.xml"

    now_rfc2822 = format_datetime(datetime.now(timezone.utc))

    items_xml = []
    for ep in episodes:
        audio_url = f"{base_url}/episodes/{ep['filename']}"
        pub_date = parse_date(ep["pub_date"])
        item = f"""    <item>
      <title>{escape(ep['title'])}</title>
      <description>{escape(ep['description'])}</description>
      <enclosure url="{escape(audio_url)}" length="{ep['file_size_bytes']}" type="audio/mpeg"/>
      <guid isPermaLink="false">{escape(ep['filename'])}</guid>
      <pubDate>{pub_date}</pubDate>
      <itunes:duration>{escape(duration_to_seconds(ep['duration']))}</itunes:duration>
      <itunes:explicit>false</itunes:explicit>
    </item>"""
        items_xml.append(item)

    items_block = "\n".join(items_xml)

    image_block = ""
    if podcast.get("image_url"):
        image_block = f"""    <itunes:image href="{escape(podcast['image_url'])}"/>
    <image>
      <url>{escape(podcast['image_url'])}</url>
      <title>{escape(podcast['title'])}</title>
      <link>{escape(feed_url)}</link>
    </image>"""

    feed = f"""<?xml version="1.0" encoding="UTF-8"?>
<rss version="2.0"
     xmlns:itunes="http://www.itunes.com/dtds/podcast-1.0.dtd"
     xmlns:atom="http://www.w3.org/2005/Atom">
  <channel>
    <title>{escape(podcast['title'])}</title>
    <link>{escape(feed_url)}</link>
    <description>{escape(podcast['description'])}</description>
    <language>{escape(podcast['language'])}</language>
    <itunes:author>{escape(podcast['author'])}</itunes:author>
    <itunes:owner>
      <itunes:name>{escape(podcast['author'])}</itunes:name>
      <itunes:email>{escape(podcast['email'])}</itunes:email>
    </itunes:owner>
    <itunes:explicit>false</itunes:explicit>
    <atom:link href="{escape(feed_url)}" rel="self" type="application/rss+xml"/>
    <lastBuildDate>{now_rfc2822}</lastBuildDate>
{image_block}
{items_block}
  </channel>
</rss>
"""
    return feed


def main():
    with open(INPUT_JSON, "r", encoding="utf-8") as f:
        data = json.load(f)

    os.makedirs(OUTPUT_DIR, exist_ok=True)

    feed_xml = build_feed(data)

    with open(OUTPUT_FILE, "w", encoding="utf-8") as f:
        f.write(feed_xml)

    print(f"Generated: {OUTPUT_FILE}")
    print(f"Episodes: {len(data['episodes'])}")


if __name__ == "__main__":
    main()
