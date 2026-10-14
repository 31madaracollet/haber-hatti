#!/usr/bin/env python3
"""
Hat — haber akışı derleyici.

Tüm RSS kaynaklarını sunucu tarafında çeker (CORS engeli yok), ayrıştırır ve
depo köküne feed.json yazar. Statik sayfa bu dosyayı kendi origin'inden okur.
"""
import json
import re
import html
import sys
import urllib.request
import urllib.error
import urllib.parse
from datetime import datetime, timezone
from email.utils import parsedate_to_datetime
from concurrent.futures import ThreadPoolExecutor
import xml.etree.ElementTree as ET

UA = "Mozilla/5.0 (compatible; HatFeedBot/1.0; +https://github.com/31madaracollet/haber-hatti)"
TIMEOUT = 20
MAX_WORKERS = 12


def gn(path=""):
    return "https://news.google.com/rss" + path + "?hl=tr&gl=TR&ceid=TR:tr"


SECTIONS = {
    "akis": [
        gn(), gn("/headlines/section/topic/WORLD"),
        gn("/headlines/section/topic/BUSINESS"),
        gn("/headlines/section/topic/TECHNOLOGY"),
        gn("/headlines/section/topic/SPORTS"),
        gn("/headlines/section/topic/SCIENCE"),
        "https://www.ntv.com.tr/son-dakika.rss",
        "https://www.hurriyet.com.tr/rss/anasayfa",
        "https://feeds.bbci.co.uk/turkce/rss.xml",
        "https://www.trthaber.com/sondakika_articles.rss",
        "https://www.cumhuriyet.com.tr/rss/son_dakika.xml",
        "https://feeds.bbci.co.uk/news/world/rss.xml",
        "https://www.aljazeera.com/xml/rss/all.xml",
        "https://www.theguardian.com/world/rss",
        "https://rss.dw.com/rdf/rss-tur-all",
        "https://techcrunch.com/feed/",
    ],
    "gundem": [
        gn(),
        "https://www.ntv.com.tr/son-dakika.rss",
        "https://www.hurriyet.com.tr/rss/gundem",
        "https://www.trthaber.com/sondakika_articles.rss",
        "https://www.cumhuriyet.com.tr/rss/son_dakika.xml",
        "https://feeds.bbci.co.uk/turkce/rss.xml",
        "https://www.haberturk.com/rss",
        "https://www.aa.com.tr/tr/rss/default?cat=guncel",
    ],
    "dunya": [
        gn("/headlines/section/topic/WORLD"),
        "https://feeds.bbci.co.uk/news/world/rss.xml",
        "https://www.aljazeera.com/xml/rss/all.xml",
        "https://www.theguardian.com/world/rss",
        "https://rss.nytimes.com/services/xml/rss/nyt/World.xml",
        "https://rss.dw.com/rdf/rss-tur-all",
        "https://tr.euronews.com/rss",
    ],
    "ekonomi": [
        gn("/headlines/section/topic/BUSINESS"),
        "https://www.ntv.com.tr/ekonomi.rss",
        "https://www.hurriyet.com.tr/rss/ekonomi",
        "https://www.bloomberght.com/rss",
        "https://www.aa.com.tr/tr/rss/default?cat=ekonomi",
        "https://www.theguardian.com/uk/business/rss",
    ],
    "teknoloji": [
        gn("/headlines/section/topic/TECHNOLOGY"),
        "https://www.ntv.com.tr/teknoloji.rss",
        "https://www.hurriyet.com.tr/rss/teknoloji",
        "https://techcrunch.com/feed/",
        "https://www.theverge.com/rss/index.xml",
        "https://feeds.arstechnica.com/arstechnica/index",
        "https://hnrss.org/frontpage",
    ],
    "spor": [
        gn("/headlines/section/topic/SPORTS"),
        "https://www.ntv.com.tr/spor.rss",
        "https://www.hurriyet.com.tr/rss/spor",
        "https://www.espn.com/espn/rss/news",
    ],
    "bilim": [
        gn("/headlines/section/topic/SCIENCE"),
        gn("/headlines/section/topic/HEALTH"),
        "https://www.sciencedaily.com/rss/all.xml",
        "https://phys.org/rss-feed/",
    ],
    "kultur": [
        gn("/headlines/section/topic/ENTERTAINMENT"),
        "https://www.hurriyet.com.tr/rss/kultur-sanat",
        "https://www.ntv.com.tr/kultur-sanat.rss",
        "https://www.theguardian.com/culture/rss",
    ],
}

NAMES = {
    "news.google.com": None,
    "www.ntv.com.tr": "NTV", "ntv.com.tr": "NTV",
    "www.hurriyet.com.tr": "Hürriyet",
    "www.trthaber.com": "TRT Haber",
    "www.cumhuriyet.com.tr": "Cumhuriyet",
    "www.haberturk.com": "Habertürk",
    "www.aa.com.tr": "Anadolu Ajansı",
    "feeds.bbci.co.uk": "BBC",
    "www.aljazeera.com": "Al Jazeera",
    "www.theguardian.com": "The Guardian",
    "rss.nytimes.com": "New York Times",
    "rss.dw.com": "DW",
    "tr.euronews.com": "Euronews",
    "www.bloomberght.com": "Bloomberg HT",
    "techcrunch.com": "TechCrunch",
    "www.theverge.com": "The Verge",
    "feeds.arstechnica.com": "Ars Technica",
    "hnrss.org": "Hacker News",
    "www.espn.com": "ESPN",
    "www.sciencedaily.com": "ScienceDaily",
    "phys.org": "Phys.org",
}

CAPS = {"akis": 200}
DEFAULT_CAP = 110


def label_of(url):
    m = re.match(r"https?://([^/]+)", url)
    host = m.group(1).lower() if m else url
    if host in NAMES:
        return NAMES[host] or host.replace("www.", "")
    return host.replace("www.", "")


def localname(tag):
    return tag.split("}")[-1].lower() if "}" in tag else tag.lower()


def find_first(elem, names):
    # localname() küçük harfe çevirir; karşılaştırmayı da küçük harfle yap.
    wanted = {n.lower() for n in names}
    for child in elem.iter():
        if localname(child.tag) in wanted:
            return child
    return None


def text_of(elem, names):
    node = find_first(elem, names)
    if node is not None and node.text and node.text.strip():
        return node.text.strip()
    return ""


def strip_tags(raw):
    if not raw:
        return ""
    s = re.sub(r"<[^>]*>", " ", raw)
    s = html.unescape(s)
    return re.sub(r"\s+", " ", s).strip()


def parse_date(value):
    if not value:
        return None
    value = value.strip()
    try:
        d = parsedate_to_datetime(value)
        return d if d.tzinfo else d.replace(tzinfo=timezone.utc)
    except (TypeError, ValueError, IndexError):
        pass
    try:
        return datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError:
        return None


def get_link(item):
    for el in item.iter():
        if localname(el.tag) != "link":
            continue
        rel = (el.get("rel") or "").lower()
        href = el.get("href")
        if href and rel in ("", "alternate"):
            return href
    for el in item.iter():
        if localname(el.tag) == "link" and el.text and el.text.strip():
            return el.text.strip()
    g = find_first(item, ["guid"])
    if g is not None and g.text and g.text.strip().startswith("http"):
        return g.text.strip()
    return ""


def get_image(item):
    for el in item.iter():
        ln = localname(el.tag)
        if ln not in ("content", "thumbnail", "enclosure", "image"):
            continue
        url = el.get("url")
        if not url:
            continue
        mime = (el.get("type") or "").lower()
        medium = (el.get("medium") or "").lower()
        if ln == "enclosure" and mime and not mime.startswith("image"):
            continue
        if ln == "thumbnail" or mime.startswith("image") or medium == "image":
            return url
    raw = text_of(item, ["description", "summary", "content", "encoded"])
    m = re.search(r"""<img[^>]+src=["']([^"']+)["']""", raw or "")
    if m and not re.search(r"pixel|spacer|1x1|blank\.|transparent", m.group(1), re.I):
        return m.group(1)
    return ""


def fetch(url):
    req = urllib.request.Request(url, headers={
        "User-Agent": UA,
        "Accept": "application/rss+xml, application/atom+xml, application/xml, text/xml, */*",
        "Accept-Encoding": "identity",
        "Accept-Language": "tr,en;q=0.8",
    })
    with urllib.request.urlopen(req, timeout=TIMEOUT) as resp:
        return resp.read()


def parse_feed(url, section):
    raw = fetch(url)
    root = ET.fromstring(raw)

    items = [e for e in root.iter() if localname(e.tag) == "item"]
    if not items:
        items = [e for e in root.iter() if localname(e.tag) == "entry"]

    is_google = "news.google.com" in url
    label = label_of(url)
    out = []

    for it in items[:40]:
        title = strip_tags(text_of(it, ["title"]))
        if not title:
            continue

        src_el = find_first(it, ["source"])
        source = ""
        if src_el is not None:
            source = strip_tags(src_el.text or "")
            if not source and src_el.get("url"):
                source = label_of(src_el.get("url"))
        if not source:
            source = label

        if source and title.endswith(" - " + source):
            title = title[: -(len(source) + 3)].strip()

        link = get_link(it)
        if not link:
            continue
        link = urllib.parse.urljoin(url, link) if link.startswith("/") else link
        if not link.startswith("http"):
            continue

        dt = parse_date(text_of(it, ["pubDate", "published", "updated", "date"]))
        if dt is None:
            dt = datetime.now(timezone.utc)

        summary = strip_tags(
            text_of(it, ["description", "summary", "content", "encoded"])
        )
        if is_google and source and summary.endswith(source):
            summary = summary[: -len(source)].strip(" ,-")
        if len(summary) > 300:
            summary = summary[:297].rstrip() + "…"

        image = get_image(it)
        if image and image.startswith("//"):
            image = "https:" + image
        if image and not image.startswith("http"):
            image = ""
        if image:
            image = urllib.parse.urljoin(url, image)

        out.append({
            "title": title,
            "link": link,
            "source": source,
            "date": dt.astimezone(timezone.utc).isoformat(),
            "image": image,
            "summary": summary,
        })

    return out


def key_of(item):
    t = re.sub(r"[^a-z0-9çğıöşü ]", "", item["title"].lower())
    return re.sub(r"\s+", " ", t).strip()[:90]


def fetch_section(section, feeds):
    items = []
    health = []
    with ThreadPoolExecutor(max_workers=MAX_WORKERS) as pool:
        futures = {pool.submit(parse_feed, f, section): f for f in feeds}
        for fut, feed_url in futures.items():
            name = label_of(feed_url)
            try:
                rows = fut.result()
            except Exception as exc:
                health.append({"name": name, "url": feed_url, "ok": False,
                               "error": type(exc).__name__})
                continue
            health.append({"name": name, "url": feed_url, "ok": True, "count": len(rows)})
            items.extend(rows)

    seen = {}
    unique = []
    for it in items:
        k = key_of(it)
        if not k:
            continue
        if k in seen:
            prev = seen[k]
            if not prev["image"] and it["image"]:
                prev["image"] = it["image"]
            if not prev["summary"] and it["summary"]:
                prev["summary"] = it["summary"]
            if it["date"] > prev["date"]:
                prev["date"] = it["date"]
            continue
        seen[k] = it
        unique.append(it)

    unique.sort(key=lambda x: x["date"], reverse=True)
    cap = CAPS.get(section, DEFAULT_CAP)
    return unique[:cap], health


def main():
    started = datetime.now(timezone.utc)
    payload = {
        "generatedAt": started.isoformat(),
        "sections": {},
        "health": {},
    }

    cache = {}
    for section, feeds in SECTIONS.items():
        rows, health = fetch_section(section, feeds)
        payload["sections"][section] = rows
        payload["health"][section] = {
            "ok": sum(1 for h in health if h["ok"]),
            "total": len(health),
            "sources": health,
        }
        cache[section] = rows
        print(f"  {section:<10} {len(rows):>4} haber   "
              f"{payload['health'][section]['ok']}/{len(health)} kaynak", flush=True)

    with open("feed.json", "w", encoding="utf-8") as fh:
        json.dump(payload, fh, ensure_ascii=False, separators=(",", ":"))

    elapsed = (datetime.now(timezone.utc) - started).total_seconds()
    total = sum(len(v) for v in payload["sections"].values())
    print(f"feed.json yazildi — {total} haber, {elapsed:.1f} sn")
    return 0


if __name__ == "__main__":
    import urllib.parse  # noqa: E402  (parse_feed içinde kullanılıyor)
    sys.exit(main())
