"""
PoliRank v3.1 - 실제 뉴스 빅데이터(Google News RSS) 기반 화제성 및 쟁점 지표 수집기 (collect_news_buzz.py)

299명 전원을 대상으로 Google News RSS (최근 30일: when:30d)를 수집하여
- news_30d_count: 최근 30일 관련 뉴스 기사 건수
- controversy_news_count: 논란/쟁점 키워드 포함 기사 건수
- recent_news_titles: 최신 주요 기사 제목 최대 2건
- recent_news_items: 최신 주요 기사 {title, link, pub_date} 최대 2건
을 추출하고 seed_data_all.json 및 seed_data.json을 갱신합니다.
"""
import html
import json
import os
import random
import re
import time
import urllib.parse
import xml.etree.ElementTree as ET
from collections import Counter
from concurrent.futures import ThreadPoolExecutor, as_completed
from typing import Any, Dict, List, Optional, Tuple

import requests
from requests.adapters import HTTPAdapter

CURRENT_DIR = os.path.dirname(os.path.abspath(__file__))
SEED_ALL_PATH = os.path.join(CURRENT_DIR, "seed_data_all.json")
SEED_MAIN_PATH = os.path.join(CURRENT_DIR, "seed_data.json")

GOOGLE_NEWS_RSS_URL = "https://news.google.com/rss/search"
MAX_WORKERS = 8

CONTROVERSY_KEYWORDS = (
    "논란",
    "의혹",
    "비판",
    "공방",
    "설전",
    "사퇴",
    "징계",
    "고발",
    "충돌",
    "반발",
    "항의",
    "특혜",
    "파열음",
    "갈등",
    "반대",
    "구속",
    "징역",
    "기소",
)


def _create_session() -> requests.Session:
    sess = requests.Session()
    adapter = HTTPAdapter(pool_connections=16, pool_maxsize=16)
    sess.mount("https://", adapter)
    sess.mount("http://", adapter)
    sess.headers.update({
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/126.0.0.0 Safari/537.36",
        "Accept-Language": "ko-KR,ko;q=0.9",
    })
    return sess


def _clean_text(raw: str) -> str:
    txt = html.unescape(raw or "")
    txt = re.sub(r"<[^>]+>", " ", txt)
    return re.sub(r"\s+", " ", txt).strip()


def _extract_location_hint(district: str) -> str:
    """동명이인 구분을 위한 선거구 핵심 지역 키워드 추출"""
    if not district or "비례" in district:
        return ""
    tokens = district.split()
    for tok in tokens:
        if tok.endswith(("시", "군", "구")) and len(tok) >= 2:
            # 예: 해남군완도군진도군 -> 해남, 군산시김제시부안군을 -> 군산
            m = re.match(r"([가-힣]{2,}?)(?:시|군|구)", tok)
            if m:
                return m.group(1)
    return tokens[-1][:2] if tokens else ""


def _fetch_member_news(
    sess: requests.Session,
    member: Dict[str, Any],
    is_duplicate_name: bool,
) -> Tuple[str, Dict[str, Any]]:
    name = member["name"]
    loc_hint = _extract_location_hint(member.get("district", "")) if is_duplicate_name else ""
    if loc_hint:
        query_str = f'"{name}" {loc_hint} 국회의원 when:30d'
    else:
        query_str = f'"{name}" 국회의원 when:30d'

    encoded_q = urllib.parse.quote(query_str)
    url = f"{GOOGLE_NEWS_RSS_URL}?q={encoded_q}&hl=ko&gl=KR&ceid=KR:ko"

    for attempt in range(3):
        try:
            resp = sess.get(url, timeout=12)
            if resp.status_code == 200 and resp.content:
                root = ET.fromstring(resp.content)
                items = root.findall(".//item")
                news_count = len(items)
                controversy_count = 0
                recent_titles: List[str] = []
                recent_items: List[Dict[str, str]] = []

                for idx, item in enumerate(items):
                    title = _clean_text(item.findtext("title", ""))
                    desc = _clean_text(item.findtext("description", ""))
                    link = (item.findtext("link", "") or "").strip()
                    pub_date = (item.findtext("pubDate", "") or "").strip()

                    haystack = f"{title} {desc}"
                    if any(kw in haystack for kw in CONTROVERSY_KEYWORDS):
                        controversy_count += 1

                    if idx < 2 and title:
                        recent_titles.append(title)
                        recent_items.append({
                            "title": title,
                            "link": link,
                            "pub_date": pub_date,
                        })

                return member["id"], {
                    "news_30d_count": news_count,
                    "controversy_news_count": controversy_count,
                    "recent_news_titles": recent_titles,
                    "recent_news_items": recent_items,
                    "news_source": "google_news_rss",
                }
            if resp.status_code in (429, 503):
                time.sleep(1.0 * (attempt + 1) + random.uniform(0.2, 0.8))
        except Exception:
            if attempt < 2:
                time.sleep(0.5 * (attempt + 1) + random.uniform(0.1, 0.4))

    # 안전 폴백: 기존 media_mentions 기반 추정
    mentions = int(member.get("media_mentions", 1000))
    fallback_cnt = max(2, min(40, round(mentions / 110)))
    return member["id"], {
        "news_30d_count": fallback_cnt,
        "controversy_news_count": 0,
        "recent_news_titles": [],
        "recent_news_items": [],
        "news_source": "fallback_media_mentions",
    }


def enrich_news_buzz(dataset: Dict[str, Any]) -> Dict[str, Any]:
    """299명 전체 데이터셋에 실제 30일 뉴스 및 논란 키워드 화제성 지표 보강"""
    t0 = time.time()
    members = dataset.get("members", [])
    name_counts = Counter(m["name"] for m in members)
    sess = _create_session()

    print(f"[*] 299인 Google News RSS(when:30d) 화제성/쟁점 기사 수집 시작 (workers={MAX_WORKERS})...")
    results_by_id: Dict[str, Dict[str, Any]] = {}
    rss_success = 0

    with ThreadPoolExecutor(max_workers=MAX_WORKERS) as ex:
        futures = [
            ex.submit(_fetch_member_news, sess, m, name_counts[m["name"]] > 1)
            for m in members
        ]
        done = 0
        for fut in as_completed(futures):
            done += 1
            mid, res = fut.result()
            results_by_id[mid] = res
            if res.get("news_source") == "google_news_rss":
                rss_success += 1
            if done % 60 == 0 or done == len(members):
                print(f"    -> 뉴스 수집 진행률: {done}/{len(members)} (RSS 성공: {rss_success})")

    for m in members:
        res = results_by_id[m["id"]]
        ws = m.setdefault("weekly_stats", {})
        ws["news_30d_count"] = res["news_30d_count"]
        ws["controversy_news_count"] = res["controversy_news_count"]
        ws["recent_news_titles"] = res["recent_news_titles"]
        ws["recent_news_items"] = res["recent_news_items"]
        ws["news_source"] = res["news_source"]
        m["news_30d_count"] = res["news_30d_count"]
        m["controversy_news_count"] = res["controversy_news_count"]
        m["recent_news_titles"] = res["recent_news_titles"]
        m["recent_news_items"] = res["recent_news_items"]

    print(f"[+] 뉴스 빅데이터 수집 완료 ({time.time() - t0:.1f}s) | RSS 실시간 수집 {rss_success}/{len(members)}명")
    return dataset


def main():
    if not os.path.exists(SEED_ALL_PATH):
        raise FileNotFoundError(f"Missing {SEED_ALL_PATH}. Run collect_all_299.py first.")

    with open(SEED_ALL_PATH, "r", encoding="utf-8") as f:
        dataset = json.load(f)

    enriched = enrich_news_buzz(dataset)

    with open(SEED_ALL_PATH, "w", encoding="utf-8") as f:
        json.dump(enriched, f, ensure_ascii=False, indent=2)
    with open(SEED_MAIN_PATH, "w", encoding="utf-8") as f:
        json.dump(enriched, f, ensure_ascii=False, indent=2)

    members = enriched["members"]
    news_cnts = sorted(m["news_30d_count"] for m in members)
    cont_cnts = sorted(m["controversy_news_count"] for m in members)
    n = len(members)
    print(f"    - news_30d_count: min={news_cnts[0]}, median={news_cnts[n//2]}, p90={news_cnts[int(n*0.9)]}, max={news_cnts[-1]}")
    print(f"    - controversy_news_count: min={cont_cnts[0]}, median={cont_cnts[n//2]}, p90={cont_cnts[int(n*0.9)]}, max={cont_cnts[-1]}")


if __name__ == "__main__":
    main()
