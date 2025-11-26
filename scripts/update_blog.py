import os
import re
import sys
import json
import requests
from datetime import datetime, timezone
from dateutil import parser as dateparser

README_PATH = "README.md"
START_MARK = "<!-- recent-blog-posts start -->"
END_MARK = "<!-- recent-blog-posts end -->"

DEVTO_USERNAME = "vaibhavg"   # your username
MAX_POSTS = 6
TIMEOUT = 20

session = requests.Session()
session.headers.update({
    "User-Agent": "Mozilla/5.0 (compatible; GitHubAction; +https://github.com/vaibhavg)",
    "Accept-Language": "en",
})


def normalize_date(dt):
    if not dt:
        return None
    if dt.tzinfo is None:
        return dt.replace(tzinfo=timezone.utc)
    return dt.astimezone(timezone.utc)


def safe_get(url, timeout=TIMEOUT):
    try:
        r = session.get(url, timeout=timeout)
        r.raise_for_status()
        return r
    except Exception:
        return None


def fetch_devto_posts():
    url = f"https://dev.to/api/articles?username={DEVTO_USERNAME}"
    resp = safe_get(url)
    if not resp:
        return []

    try:
        data = resp.json()
    except:
        return []

    posts = []
    for item in data:
        published = item.get("published_at") or item.get("created_at")
        try:
            dt_raw = dateparser.parse(published)
        except:
            dt_raw = None
        dt = normalize_date(dt_raw)

        posts.append({
            "title": item.get("title") or "",
            "url": item.get("url") or "",
            "cover_image": item.get("cover_image") or item.get("social_image") or "",
            "date": dt,
            "date_str": dt.strftime("%Y-%m-%d") if dt else (published or ""),
        })
    return posts


def render_markdown_grid(posts):
    items = posts[:MAX_POSTS]

    # Make even number for 2-column grid
    if len(items) % 2 == 1:
        items.append({"title": "", "url": "", "cover_image": "", "date_str": ""})

    def cell_html(p):
        if not p.get("title"):
            return "<td></td>"
        img_html = (
            f'<img src="{p["cover_image"]}" alt="cover" '
            f'style="width:280px; max-width:100%; border-radius:8px;" />'
            if p.get("cover_image") else ""
        )
        title_html = f'<a href="{p["url"]}">{p["title"]}</a>'
        meta_html = p.get("date_str", "")
        return (
            f"<td valign='top' style='padding:8px;'>"
            f"{img_html}"
            f"<div style='margin-top:6px; font-weight:600;'>{title_html}</div>"
            f"<div style='color:#666;'>{meta_html}</div>"
            f"</td>"
        )

    rows = []
    for i in range(0, len(items), 2):
        rows.append(f"<tr>{cell_html(items[i])}{cell_html(items[i+1])}</tr>")

    html = []
    html.append("")
    html.append("### Recent Articles")
    html.append("")
    html.append("<table>")
    for r in rows:
        html.append(r)
    html.append("</table>")
    html.append("")
    html.append("_Auto-updated daily from dev.to_")
    html.append("")

    return "\n".join(html)


def update_readme_section(new_content):
    if not os.path.exists(README_PATH):
        print("README.md not found.", file=sys.stderr)
        sys.exit(1)

    with open(README_PATH, "r", encoding="utf-8") as f:
        readme = f.read()

    if START_MARK not in readme or END_MARK not in readme:
        print("Markers not found in README.md.", file=sys.stderr)
        sys.exit(1)

    pattern = re.compile(
        re.escape(START_MARK) + r"(.*?)" + re.escape(END_MARK),
        re.DOTALL
    )

    updated = pattern.sub(
        START_MARK + "\n" + new_content + "\n" + END_MARK,
        readme
    )

    if updated != readme:
        with open(README_PATH, "w", encoding="utf-8") as f:
            f.write(updated)
        print("README.md updated.")
    else:
        print("README.md already up to date.")


def main():
    devto = fetch_devto_posts()

    def sort_key(p): return p["date"] or datetime.min.replace(tzinfo=timezone.utc)

    devto.sort(key=sort_key, reverse=True)
    latest = devto[:MAX_POSTS]

    md = render_markdown_grid(latest)
    update_readme_section(md)


if __name__ == "__main__":
    main()
