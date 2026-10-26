#!/usr/bin/env python3
"""Live wire: rewrite the healthsucks.com section of README.md daily.

Fetches the site's sitemap, takes the newest article pages, reads their
real <title>s, and re-renders the block between the LIVE markers. If the
site is unreachable the README is left untouched (exit 0) so a bad day
on the blog never breaks the profile.
"""

import re
import sys
import urllib.request
import xml.etree.ElementTree as ET
from datetime import date

SITEMAP = "https://www.healthsucks.com/sitemap.xml"
SITE = "https://www.healthsucks.com"
README_PATH = "README.md"
START, END = "<!-- LIVE:START -->", "<!-- LIVE:END -->"
NOT_POSTS = {"", "category", "topic", "about", "contact", "privacy-policy", "terms"}
NS = {"sm": "http://www.sitemaps.org/schemas/sitemap/0.9"}


def fetch(url):
    req = urllib.request.Request(url, headers={"User-Agent": "profile-livewire/1.0"})
    with urllib.request.urlopen(req, timeout=20) as r:
        return r.read().decode("utf-8", "replace")


def post_urls():
    root = ET.fromstring(fetch(SITEMAP))
    posts = []
    for url in root.findall("sm:url", NS):
        loc = url.findtext("sm:loc", default="", namespaces=NS).strip()
        prio = url.findtext("sm:priority", default="", namespaces=NS).strip()
        slug = loc.rstrip("/").rsplit("/", 1)[-1] if loc != SITE else ""
        if prio == "0.8" and slug not in NOT_POSTS and loc.startswith(SITE):
            posts.append(loc)
    return posts


def page_title(url):
    html = fetch(url)
    m = re.search(r"<title>(.*?)</title>", html, re.S | re.I)
    if not m:
        return None
    title = re.sub(r"\s+", " ", m.group(1)).strip()
    return re.sub(r"\s*\|\s*HealthSucks\s*$", "", title)


def render(items):
    lines = "\n".join(f"- [{t}]({u})" for t, u in items)
    today = date.today().strftime("%d %b %Y")
    return f"""{START}
### 📡 Live wire — latest on healthsucks.com

*This section rewrites itself every morning. No human touches it.*

{lines}

*Last synced: {today} · [healthsucks.com]({SITE}) — health advice that admits when it's guessing.*
{END}"""


def main():
    try:
        urls = post_urls()[:3]
        items = []
        for u in urls:
            t = page_title(u)
            if t:
                items.append((t, u))
        if not items:
            print("livewire: no items fetched, leaving README unchanged")
            return
    except Exception as e:  # never fail the profile over a fetch error
        print(f"livewire: fetch failed ({e}), leaving README unchanged")
        return

    with open(README_PATH) as f:
        readme = f.read()
    i, j = readme.index(START), readme.index(END) + len(END)
    with open(README_PATH, "w") as f:
        f.write(readme[:i] + render(items) + readme[j:])
    print(f"livewire: updated with {len(items)} posts")


if __name__ == "__main__":
    main()
