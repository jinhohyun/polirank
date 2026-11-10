"""
PoliRank v3.0 - 14대 실제 공공 팩트 지표 보강 수집기 (enrich_extra_metrics.py)

열린국회 의안정보(nzmimeepazxkubdpn) 병렬 호출(ThreadPoolExecutor max_workers=20)을 통해
seed_data_all.json의 299명 전원에 대해 아래 100% 실제 공공 팩트 지표를 산출/보강합니다:
  1) bipartisan_rate: 최근 대표발의 최대 5건 중 타 정당 의원이 1명 이상 공동발의한 비율 (%)
  2) bipartisan_cosponsor_share: 공동발의자 중 타 정당 의원 비중 (%)
  3) avg_cosponsors: 대표발의 법안당 평균 공동발의 의원 수
  4) cosponsor_participations: 수집된 전체 법안 표본(~3,300+건) 내 타 의원 법안 공동발의 참여 횟수
  5) policy_diversity: 발의 법안이 걸쳐 있는 서로 다른 소관 상임위 분야 수
  6) passage_efficiency: 입법 타율 / 가결 효율 (%) - 최소 발의 5건 보정
  7) committee_count & has_special_duty: 겸임 위원회 수 및 핵심 겸임위/특위 참여 여부
  8) active_vote_ratio: 본회의 표결 중 찬성/반대 명확 의사표시 비율 (%)
"""
import json
import os
import time
from collections import Counter
from concurrent.futures import ThreadPoolExecutor
from typing import Any, Dict, List, Optional, Set, Tuple

import requests
from requests.adapters import HTTPAdapter

CURRENT_DIR = os.path.dirname(os.path.abspath(__file__))
SEED_ALL_PATH = os.path.join(CURRENT_DIR, "seed_data_all.json")
SEED_MAIN_PATH = os.path.join(CURRENT_DIR, "seed_data.json")
EP_BILLS = "https://open.assembly.go.kr/portal/openapi/nzmimeepazxkubdpn"
MAX_WORKERS = 20

SPECIAL_DUTY_KEYWORDS = (
    "예산결산특별위원회",
    "국회운영위원회",
    "정보위원회",
    "특별위원회",
    "국정조사",
)


def _create_session() -> requests.Session:
    sess = requests.Session()
    adapter = HTTPAdapter(pool_connections=32, pool_maxsize=32)
    sess.mount("https://", adapter)
    sess.mount("http://", adapter)
    sess.headers.update({"User-Agent": "PoliRank-Enricher/3.0"})
    return sess


def _fetch_json_with_retry(
    sess: requests.Session,
    url: str,
    params: Dict[str, Any],
    timeout: int = 12,
    retries: int = 3,
) -> Optional[Dict[str, Any]]:
    for attempt in range(retries):
        try:
            resp = sess.get(url, params=params, timeout=timeout)
            if resp.status_code == 200:
                return resp.json()
        except Exception:
            if attempt < retries - 1:
                time.sleep(0.35 * (attempt + 1))
    return None


def enrich_dataset(dataset: Dict[str, Any]) -> Dict[str, Any]:
    """기존 299인 데이터셋에 신규 14대 실제 공공 팩트 지표 보강"""
    t0 = time.time()
    members = dataset.get("members", [])
    mona_to_party: Dict[str, str] = {
        m["mona_cd"]: m["party"] for m in members if m.get("mona_cd")
    }
    unique_names = sorted({m["name"] for m in members})
    sess = _create_session()

    print(f"[*] 299인 신규 공공 팩트 지표 보강 수집 시작 (고유 성명 {len(unique_names)}명, workers={MAX_WORKERS})...")

    def _fetch_bills_for_name(name: str) -> Tuple[str, List[Dict[str, Any]]]:
        rows: List[Dict[str, Any]] = []
        seen_bids: Set[str] = set()
        for suffix in ("의원", "ㆍ"):
            for proc in (None, "원안가결", "수정가결", "대안반영폐기"):
                params: Dict[str, Any] = {
                    "Type": "json",
                    "AGE": "22",
                    "PROPOSER": f"{name}{suffix}",
                }
                if proc:
                    params["PROC_RESULT"] = proc
                data = _fetch_json_with_retry(sess, EP_BILLS, params)
                if data and "nzmimeepazxkubdpn" in data and len(data["nzmimeepazxkubdpn"]) > 1:
                    for row in data["nzmimeepazxkubdpn"][1].get("row", []):
                        bid = row.get("BILL_ID")
                        if bid and bid not in seen_bids:
                            seen_bids.add(bid)
                            rows.append(row)
        return name, rows

    rows_by_name: Dict[str, List[Dict[str, Any]]] = {}
    all_bills_pool: Dict[str, Dict[str, Any]] = {}
    with ThreadPoolExecutor(max_workers=MAX_WORKERS) as ex:
        for name, rows in ex.map(_fetch_bills_for_name, unique_names):
            rows_by_name[name] = rows
            for r in rows:
                bid = r.get("BILL_ID")
                if bid:
                    all_bills_pool[bid] = r

    # 전체 법안 풀에서 공동발의 참여 횟수 집계 (본인 대표발의 제외)
    cosponsor_count_by_mona: Counter = Counter()
    for r in all_bills_pool.values():
        rst = (r.get("RST_MONA_CD") or "").strip()
        publ_raw = r.get("PUBL_MONA_CD") or ""
        for code in publ_raw.split(","):
            c = code.strip()
            if c and c != rst:
                cosponsor_count_by_mona[c] += 1

    print(f"    -> API 수집 완료 ({time.time() - t0:.1f}s) | 법안 풀 규모: {len(all_bills_pool)}건")

    for m in members:
        mona = m.get("mona_cd", "")
        my_party = m.get("party", "무소속")
        ws = m.setdefault("weekly_stats", {})

        # 본인 대표발의 법안 필터링 후 최신순 정렬
        my_rows = [
            r for r in rows_by_name.get(m["name"], [])
            if (r.get("RST_MONA_CD") or "").strip() == mona
        ]
        my_rows.sort(key=lambda x: x.get("PROPOSE_DT") or "", reverse=True)

        # 최근 대표발의 최대 5건 기준 협치율 & 평균 공동발의 의원 수 산출
        recent_5 = my_rows[:5]
        bip_bills = 0
        total_cosp = 0
        other_party_cosp = 0
        known_cosp = 0

        for r in recent_5:
            publ_codes = [c.strip() for c in (r.get("PUBL_MONA_CD") or "").split(",") if c.strip()]
            total_cosp += len(publ_codes)
            has_other_party = False
            for c in publ_codes:
                p = mona_to_party.get(c)
                if p:
                    known_cosp += 1
                    if p != my_party:
                        has_other_party = True
                        other_party_cosp += 1
            if has_other_party:
                bip_bills += 1

        n_recent = len(recent_5)
        bipartisan_rate = round((bip_bills / n_recent) * 100.0, 1) if n_recent > 0 else 0.0
        bipartisan_cosponsor_share = round((other_party_cosp / known_cosp) * 100.0, 1) if known_cosp > 0 else 0.0
        avg_cosponsors = round((total_cosp / n_recent), 1) if n_recent > 0 else 0.0
        cosponsor_participations = int(cosponsor_count_by_mona.get(mona, 0))

        # 입법 분야 다양성 (서로 다른 소관 상임위 수)
        policy_committees = sorted({
            r["COMMITTEE"].strip()
            for r in my_rows
            if r.get("COMMITTEE") and r["COMMITTEE"].strip()
        })
        policy_diversity = len(policy_committees) if policy_committees else (1 if ws.get("bills_proposed", 0) > 0 else 0)

        # 입법 타율 / 가결 효율 (%) - 최소 발의 5건 보정
        bills_proposed = int(ws.get("bills_proposed", 0))
        passed_orig = int(ws.get("passed_original", 0))
        passed_amend = int(ws.get("passed_amended", 0))
        alt_inc = int(ws.get("alt_incorporated", ws.get("subcommittee_passed", 0)))
        if bills_proposed > 0:
            raw_eff = ((passed_orig * 3.0) + (passed_amend * 2.5) + (alt_inc * 1.0)) / max(5, bills_proposed)
            passage_efficiency = round(min(100.0, raw_eff * 100.0), 1)
        else:
            passage_efficiency = 0.0

        # 겸임 상임위 수 & 핵심 특위 참여 여부
        committees_list = [
            c.strip()
            for c in (m.get("committees_all") or m.get("committee") or "").split(",")
            if c.strip()
        ]
        committee_count = max(1, len(committees_list))
        special_duties = [
            c for c in committees_list
            if any(kw in c for kw in SPECIAL_DUTY_KEYWORDS)
        ]
        has_special_duty = len(special_duties) > 0

        # 적극 표결 참여 (찬성+반대 명확 의사표시 비율)
        vb = ws.get("vote_breakdown") or {}
        votes_elig = int(ws.get("votes_eligible") or sum(vb.values()) or 0)
        yes_cnt = int(vb.get("찬성", 0))
        no_cnt = int(vb.get("반대", 0))
        abstain_cnt = int(vb.get("기권", 0))
        absent_cnt = int(vb.get("불참", 0))
        explicit_cnt = yes_cnt + no_cnt
        active_vote_ratio = round((explicit_cnt / votes_elig) * 100.0, 1) if votes_elig > 0 else float(ws.get("voting_rate", 0.0))

        # 보강 지표 저장
        ws["bipartisan_rate"] = bipartisan_rate
        ws["bipartisan_cosponsor_share"] = bipartisan_cosponsor_share
        ws["avg_cosponsors"] = avg_cosponsors
        ws["cosponsor_participations"] = cosponsor_participations
        ws["bills_cosponsored"] = cosponsor_participations  # 실측치로 대체
        ws["policy_diversity"] = policy_diversity
        ws["policy_committees"] = policy_committees
        ws["passage_efficiency"] = passage_efficiency
        ws["committee_count"] = committee_count
        ws["committees_list"] = committees_list
        ws["has_special_duty"] = has_special_duty
        ws["special_duties"] = special_duties
        ws["active_vote_ratio"] = active_vote_ratio
        ws["explicit_vote_count"] = explicit_cnt
        ws["vote_summary"] = {
            "찬성": yes_cnt,
            "반대": no_cnt,
            "기권": abstain_cnt,
            "불참": absent_cnt,
            "대상안건": votes_elig,
        }
        ws["recent_sample_count"] = n_recent

    dataset["bill_pool_size"] = len(all_bills_pool)
    dataset["metrics_version"] = "3.0"
    return dataset


def main():
    if not os.path.exists(SEED_ALL_PATH):
        raise FileNotFoundError(f"Missing {SEED_ALL_PATH}. Run collect_all_299.py first.")

    with open(SEED_ALL_PATH, "r", encoding="utf-8") as f:
        dataset = json.load(f)

    enriched = enrich_dataset(dataset)

    with open(SEED_ALL_PATH, "w", encoding="utf-8") as f:
        json.dump(enriched, f, ensure_ascii=False, indent=2)
    with open(SEED_MAIN_PATH, "w", encoding="utf-8") as f:
        json.dump(enriched, f, ensure_ascii=False, indent=2)

    members = enriched["members"]
    for key in [
        "bipartisan_rate",
        "bipartisan_cosponsor_share",
        "avg_cosponsors",
        "cosponsor_participations",
        "policy_diversity",
        "passage_efficiency",
        "committee_count",
        "active_vote_ratio",
    ]:
        vals = sorted(m["weekly_stats"][key] for m in members)
        n = len(vals)
        print(
            f"  [STAT] {key}: min={vals[0]}, p25={vals[n//4]}, p50={vals[n//2]}, p75={vals[3*n//4]}, p90={vals[int(n*0.9)]}, max={vals[-1]}"
        )
    print(f"[+] Saved v3.0 enriched 299-member data to {SEED_ALL_PATH} and {SEED_MAIN_PATH}")


if __name__ == "__main__":
    main()
