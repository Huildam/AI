# pip install readability-lxml requests beautifulsoup4 python-dateutil

from __future__ import annotations
import re, requests, datetime as dt
from urllib.parse import urlparse
from bs4 import BeautifulSoup, Comment, Tag
from readability import Document
from dateutil import parser as dtparser    

HEADERS = {"User-Agent": "Mozilla/5.0"}

SITE_HINTS = {
    "n.news.naver.com":   "div#newsct_article, div.byline",
    "news.naver.com":     "div#newsct_article, div.byline",
    "v.daum.net":         "section#harmonyContainer",
    "www.businesspost.co.kr": "div#tab1",
    "www.yna.co.kr":      "div#articleWrap",
    "www.chosun.com":     "div#news_body_area",
    "www.hani.co.kr":     "div#contents-article",
    "www.news1.kr":       "div#articleBodyContent",
}


def fetch_html(url: str, timeout: int = 10) -> str:
    r = requests.get(url, headers=HEADERS, timeout=timeout)
    r.raise_for_status()
    r.encoding = r.apparent_encoding
    return r.text

def get_title(raw_html: str) -> str:
    soup = BeautifulSoup(raw_html, "lxml")
    t = (soup.find("meta", property="og:title")
         or soup.find(["h1", "h2"])
         or soup.title)
    return (t["content"] if t and t.has_attr("content")
            else t.get_text(" ", strip=True) if t else "")


def clean_dom(soup: BeautifulSoup) -> None:
    for tag in soup(["script", "style", "noscript",
                     "header", "footer", "nav",
                     "aside", "iframe"]):
        tag.decompose()
    for c in soup.find_all(string=lambda t: isinstance(t, Comment)):
        c.extract()

def tidy_text(txt: str) -> str:
    txt = re.sub(r"\r\n|\r", "\n", txt)
    txt = re.sub(r"\n{3,}", "\n\n", txt)
    txt = re.sub(r"[ \t]{2,}", " ", txt)
    return txt.strip()

def domain_hint(url: str) -> str | None:
    host = urlparse(url).netloc
    return next((sel for dom, sel in SITE_HINTS.items()
                 if host.endswith(dom)), None)

def collect_selector_text(soup: BeautifulSoup, chain: str) -> str:
    texts, seen = [], set()
    for sel in map(str.strip, chain.split(",")):
        for node in soup.select(sel):
            if id(node) in seen:
                continue
            seen.add(id(node))
            texts.append(node.get_text("\n", strip=True))
    return "\n\n".join(texts)

def largest_block(soup: BeautifulSoup) -> Tag | None:
    max_words, best = 0, None
    for tag in soup.find_all(["article", "section", "div"]):
        words = len(tag.get_text(" ", strip=True).split())
        if words > max_words:
            max_words, best = words, tag
    return best

def get_body(raw_html: str, url: str, css_hint: str | None) -> str:
    css_hint = css_hint or domain_hint(url)

    soup_full = BeautifulSoup(raw_html, "lxml")
    clean_dom(soup_full)

    if css_hint:
        txt = collect_selector_text(soup_full, css_hint)
        if len(txt.split()) >= 30:
            return tidy_text(txt)

    soup_read = BeautifulSoup(
        Document(str(soup_full)).summary(html_partial=True), "lxml")
    lb = largest_block(soup_read)
    if lb:
        txt = lb.get_text("\n", strip=True)
        if len(txt.split()) >= 50:
            return tidy_text(txt)


    lb = largest_block(soup_full)
    return tidy_text(lb.get_text("\n", strip=True)) if lb else ""


_DATE_PTRN = re.compile(r"\d{4}[./-]\d{2}[./-]\d{2}")

def _from_meta(soup: BeautifulSoup) -> str | None:
    meta = soup.select_one(
        "meta[property='article:published_time'],"
        "meta[property='og:article:published_time'],"
        "meta[name='pubdate'],"
        "meta[name='date'],"
        "meta[itemprop='datePublished']"
    )
    if meta and meta.get("content"):
        return meta["content"]

def _from_naver_span(soup: BeautifulSoup) -> str | None:
    sel = ("span.media_end_head_info_datestamp_time, "
           "em.media_end_head_info_datestamp_time, "
           "span.t11")
    span = soup.select_one(sel)
    if not span:
        return None


    if span.has_attr("data-date-time"):
        return span["data-date-time"]


    return span.get_text(" ", strip=True)


def _normalize_date(txt: str) -> str | None:
    m = _DATE_PTRN.search(txt)
    try:
        dtobj = dtparser.parse(txt if m else "")
    except (ValueError, OverflowError):
        return None
    return dtobj.isoformat(sep="T", timespec="seconds") if dtobj else None

def get_pubdate(raw_html: str, url: str) -> str | None:
    soup = BeautifulSoup(raw_html, "lxml")


    cand = _from_naver_span(soup) or _from_meta(soup)
    if not cand:
        match = _DATE_PTRN.search(soup.get_text(" ", strip=True))
        cand = match.group(0) if match else None

    return _normalize_date(cand) if cand else None

def news_bodyparser(url: str, hint: str | None = None):
    raw   = fetch_html(url)
    title = get_title(raw)
    body  = get_body(raw, url, hint)
    date  = get_pubdate(raw, url)

    return title or "(제목 없음)", body or "(본문 없음)", date or ""

if __name__ == "__main__":
    import argparse
    ap = argparse.ArgumentParser()
    ap.add_argument("url", help="기사 URL")
    ap.add_argument("--hint", help="CSS selector 수동 지정 (쉼표로 여러 개)")
    args = ap.parse_args()

    title, body, date = news_bodyparser(args.url, args.hint)
    print("\n===== TITLE =====\n", title)
    print("\n===== DATE =====\n", date or "(날짜 없음)")
    print("\n===== BODY ({} chars) =====\n".format(len(body)))
    print(body)
