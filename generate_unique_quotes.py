"""
PoliRank v3.4 - 제22대 국회의원 299인 100% 고유 한마디(어록) 생성 엔진

각 의원의 실제 공공 팩트 데이터:
1) 최근 대표발의 법안명 (recent_bills[0..2].bill_name)
2) 실제 경력 (mem_title 파싱: 직함/기관명)
3) 지역구(district), 소관 상임위(committee), 직책(committee_role_label), 선수(terms), 정당(party)
을 결합하여 299명 전원 중복 없는 고유한 어록을 생성합니다.
(기존 MEMBER_FUN_AND_EXTRA_DATA 정성 어록 28인은 그대로 보존)
"""
import html
import json
import os
import re
from typing import Any, Dict, List, Optional, Set, Tuple

CURRENT_DIR = os.path.dirname(os.path.abspath(__file__))
SEED_ALL_PATH = os.path.join(CURRENT_DIR, "seed_data_all.json")
SEED_MAIN_PATH = os.path.join(CURRENT_DIR, "seed_data.json")


def _last_char_has_batchim(text: str) -> Tuple[bool, bool]:
    """문자열 마지막 글자의 받침 여부와 ㄹ 받침 여부를 반환: (has_batchim, is_rieul)"""
    clean = re.sub(r"[『』「」\"'()\s.,!?~·]+$", "", text or "")
    if not clean:
        return False, False
    ch = clean[-1]
    code = ord(ch)
    if 0xAC00 <= code <= 0xD7A3:
        jong = (code - 0xAC00) % 28
        return jong != 0, jong == 8
    # 숫자/영문 대표 발음
    if ch in "013678lmnrLMNR":
        return True, ch in "178lL"
    return False, False


def josa(word: str, pair: str) -> str:
    """한국어 조사 자동 결합 (예: josa('교육법', '을/를') -> '교육법을')"""
    has_b, is_r = _last_char_has_batchim(word)
    a, b = pair.split("/", 1)
    if pair == "으로/로":
        suffix = b if (not has_b or is_r) else a
    else:
        suffix = a if has_b else b
    return f"{word}{suffix}"


def _clean_bill_title(raw_bill: str) -> Optional[str]:
    """국회 의안명에서 핵심 법률명을 깔끔하게 추출"""
    if not raw_bill:
        return None
    text = html.unescape(raw_bill).strip()
    text = re.sub(r"\(대안\)\s*$", "", text).strip()

    # 흔한 접미사 정리
    suffixes = [
        " 일부개정법률안",
        " 전부개정법률안",
        " 개정법률안",
        " 제정법률안",
        " 폐지법률안",
        " 특별법안",
        " 법률안",
        " 법안",
    ]
    base = text
    for suf in suffixes:
        if base.endswith(suf):
            if suf == " 특별법안":
                base = base[: -len(suf)] + " 특별법"
            elif suf == " 법률안":
                base = base[: -len(suf)] + " 법률"
            elif suf == " 법안":
                base = base[: -len(suf)]
            else:
                base = base[: -len(suf)]
            break

    # 긴 "~의 설치 및 운용에 관한 법률" / "~에 관한 법률" 자연 축약 (조사 '에' 잔존 방지)
    base = re.sub(r"\s*등에\s+관한\s+법률$", "법", base)
    base = re.sub(r"\s*설치\s+및\s+운용에\s+관한\s+법률$", " 설치법", base)
    base = re.sub(r"\s*설치\s+및\s+운영에\s+관한\s+법률$", " 설치·운영법", base)
    base = re.sub(r"\s*보호\s+및\s+지원에\s+관한\s+법률$", " 지원법", base)
    base = re.sub(r"\s*보호\s+및\s+정착지원에\s+관한\s+법률$", " 정착지원법", base)
    base = re.sub(r"\s*관리에\s+관한\s+특별법$", " 관리특별법", base)
    base = re.sub(r"\s*관리에\s+관한\s+법률$", " 관리법", base)
    base = re.sub(r"\s*처리에\s+관한\s+법률$", " 처리법", base)
    base = re.sub(r"\s*촉진에\s+관한\s+법률$", " 촉진법", base)
    base = re.sub(r"\s*육성에\s+관한\s+법률$", " 육성법", base)
    base = re.sub(r"\s*진흥에\s+관한\s+법률$", " 진흥법", base)
    base = re.sub(r"\s*지원에\s+관한\s+특별법$", " 지원특별법", base)
    base = re.sub(r"\s*지원에\s+관한\s+법률$", " 지원법", base)
    base = re.sub(r"\s*공정화에\s+관한\s+법률$", " 공정화법", base)
    base = re.sub(r"에\s+관한\s+특별법$", " 특별법", base)
    base = re.sub(r"에\s+관한\s+법률$", "법", base)
    base = re.sub(r"\s+관한\s+특별법$", " 특별법", base)
    base = re.sub(r"\s+관한\s+법률$", "법", base)
    base = re.sub(r"\s+위한\s+특별법$", " 특별법", base)
    base = re.sub(r"\s+", " ", base).strip()
    if base.endswith("에법"):
        base = base[:-2] + "법"
    base = re.sub(r"법률$", "법", base) if base.endswith("법률") and len(base) > 12 else base
    base = re.sub(r"\s+", " ", base).strip()

    if len(base) > 22:
        words = base.split()
        trimmed = ""
        for w in words:
            if len(trimmed) + len(w) + 1 <= 18:
                trimmed = f"{trimmed} {w}".strip()
            else:
                break
        if trimmed and not trimmed.endswith(("법", "법안")):
            trimmed = trimmed.rstrip("의 및") + " 관련법"
        base = trimmed or (base[:18] + "법")

    if not base.endswith(("법", "특별법", "법률", "규칙", "규정")):
        base = f"{base}법"
    return base


def extract_bill_phrases(member: Dict[str, Any]) -> List[str]:
    """의원의 최근 대표발의 법안 목록에서 중복 없는 핵심 법안명 추출"""
    bills = member.get("recent_bills") or member.get("weekly_stats", {}).get("recent_bills") or []
    results: List[str] = []
    seen: Set[str] = set()
    for b in bills:
        raw = b.get("bill_name", "") if isinstance(b, dict) else str(b)
        cleaned = _clean_bill_title(raw)
        if cleaned and cleaned not in seen:
            seen.add(cleaned)
            results.append(f"『{cleaned}』")
    return results


def _clean_career_line(line: str) -> str:
    """MEM_TITLE 경력 줄 정제"""
    s = html.unescape(line or "").strip()
    # 불릿, 연도, 현/전 마커 정리
    s = re.sub(r"^[□■○●◎◆◈◇•·\-\*\s]+", "", s)
    s = re.sub(r"^\d{4}(\.\d{1,2})?\s*[~\-∼]?\s*(\d{4}(\.\d{1,2})?|현재|현)?\s*", "", s)
    s = re.sub(r"^(\(?[현전現前]\)?[\)\.]?\s*)+", "", s)
    s = re.sub(r"\((현|전|現|前)\)\s*$", "", s)
    s = re.sub(r"\s+", " ", s).strip()
    # 괄호 안 부연이 너무 길면 제거
    s = re.sub(r"\([^)]{14,}\)", "", s).strip()
    return s


def extract_career_candidates(member: Dict[str, Any]) -> List[str]:
    """MEM_TITLE에서 의원의 색깔을 보여주는 고유 경력/직함 추출"""
    raw_title = member.get("mem_title") or ""
    raw_lines = [ln.strip() for ln in html.unescape(raw_title).replace("\r\n", "\n").split("\n") if ln.strip()]

    skip_tokens = (
        "학력", "경력", "약력", "주요경력", "주요약력", "프로필", "출생",
        "초등학교", "중학교", "고등학교", "대학교 졸업", "대학원 졸업", "수료",
        "국회의원", "지역위원장", "당협위원장", "공보물", "운영위원장",
    )
    high_signal_roles = (
        "장관", "차관", "시장", "구청장", "군수", "도지사", "대표이사", "대변인",
        "비서관", "수석", "교수", "총장", "원장", "검사", "판사", "변호사",
        "기자", "앵커", "아나운서", "PD", "의사", "약사", "간호사", "노조",
        "위원장", "국회의장", "부의장", "사령관", "본부장", "단장", "국장",
        "청장", "연구원", "회계사", "세무사", "특보", "의원", "기획관",
    )

    priority_items: List[str] = []
    secondary_items: List[str] = []
    seen: Set[str] = set()

    for ln in raw_lines:
        cleaned = _clean_career_line(ln)
        if not cleaned or len(cleaned) < 3 or len(cleaned) > 34:
            continue
        if any(tok in cleaned for tok in skip_tokens):
            continue
        if cleaned in seen:
            continue
        seen.add(cleaned)
        if any(role in cleaned for role in high_signal_roles):
            priority_items.append(cleaned)
        else:
            secondary_items.append(cleaned)

    candidates = priority_items + secondary_items
    # 괄호/여분 공백 재정돈
    normalized: List[str] = []
    for c in candidates:
        c = re.sub(r"_[가-힣]+$", "", c).strip()
        if 3 <= len(c) <= 28 and c not in normalized:
            normalized.append(c)
    return normalized[:4]


def shorten_district(district: str, party: str) -> Tuple[str, bool]:
    """지역구 명칭을 구어체 어록에 자연스럽게 어울리도록 다듬기"""
    d = (district or "").strip()
    if not d or "비례" in d:
        return f"{party} 비례대표", True
    # 지나치게 긴 복합 선거구 축약 (예: 전남 순천시광양시곡성군구례군갑 -> 순천·광양·곡성·구례)
    parts = d.split(None, 1)
    if len(parts) == 2 and len(parts[1]) >= 10:
        chunks = re.findall(r"[가-힣]+(?:시|군|구)", parts[1])
        if len(chunks) >= 2:
            short_chunks = [re.sub(r"(시|군|구)$", "", ch) for ch in chunks[:4]]
            return "·".join(short_chunks), False
    return d, False


def shorten_committee(committee: str) -> str:
    """상임위 약칭/표준명"""
    c = (committee or "국회 상임위원회").strip()
    short_map = {
        "국회운영위원회": "운영위",
        "법제사법위원회": "법사위",
        "정무위원회": "정무위",
        "재정경제기획위원회": "재경위",
        "기획재정위원회": "기재위",
        "교육위원회": "교육위",
        "과학기술정보방송통신위원회": "과방위",
        "외교통일위원회": "외통위",
        "국방위원회": "국방위",
        "행정안전위원회": "행안위",
        "문화체육관광위원회": "문체위",
        "농림축산식품해양수산위원회": "농해수위",
        "산업통상자원중소벤처기업위원회": "산자위",
        "보건복지위원회": "복지위",
        "기후에너지환경노동위원회": "환노위",
        "환경노동위원회": "환노위",
        "국토교통위원회": "국토위",
        "정보위원회": "정보위",
        "성평등가족위원회": "여가위",
        "여성가족위원회": "여가위",
    }
    return short_map.get(c, c)


def terms_phrase(terms: int, role_label: str) -> str:
    if role_label == "국회의장":
        return "국회의장으로서"
    if role_label == "위원장":
        return f"{terms}선 위원장으로서" if terms >= 2 else "상임위원장으로서"
    if role_label == "간사":
        return "상임위 간사로서"
    if terms >= 5:
        return f"{terms}선 중진의 경륜으로"
    if terms >= 3:
        return f"{terms}선 의원의 책임감으로"
    if terms == 2:
        return "재선의 실행력으로"
    return "초선의 패기와 진정성으로"


def _build_candidate_quotes(member: Dict[str, Any]) -> List[str]:
    """한 의원에 대해 팩트(법안/경력/지역구/상임위/직책/선수) 조합 후보 문장 풀 생성"""
    name = member.get("name", "")
    party = member.get("party", "")
    committee = member.get("committee", "국회 상임위원회")
    comm_short = shorten_committee(committee)
    role_label = member.get("committee_role_label") or "위원"
    terms = int(member.get("terms") or 1)
    t_phrase = terms_phrase(terms, role_label)

    dist_label, is_pr = shorten_district(member.get("district", ""), party)
    bills = extract_bill_phrases(member)
    careers = extract_career_candidates(member)

    bill1 = bills[0] if len(bills) >= 1 else None
    bill2 = bills[1] if len(bills) >= 2 else None
    bill3 = bills[2] if len(bills) >= 3 else None
    career1 = careers[0] if len(careers) >= 1 else None
    career2 = careers[1] if len(careers) >= 2 else None

    candidates: List[str] = []

    # 1) 경력 + 대표발의 법안 + 지역구/상임위 (가장 풍부한 3종 팩트 결합)
    if career1 and bill1:
        if is_pr:
            candidates.extend([
                f"{career1} 경력을 밑거름 삼아 {bill1} 입법 등 {committee} 현장 개혁을 완수하겠습니다.",
                f"{josa(career1, '으로/로')} 쌓은 전문성을 살려 {bill1} 통과와 민생 혁신에 앞장서겠습니다.",
                f"{bill1} 발의를 비롯해 {career1} 출신답게 {comm_short}에서 실사구시 대안을 만들겠습니다.",
                f"{career1}에서 쌓은 현장 감각을 담아 {bill1} 등 국민 체감 입법을 이끌겠습니다.",
                f"{career1} 시절부터 고민해온 과제를 {bill1} 입법으로 매듭짓겠습니다.",
            ])
        else:
            candidates.extend([
                f"{career1} 경험을 바탕으로 {bill1} 입법과 {dist_label} 숙원 해결을 동시에 이뤄내겠습니다.",
                f"{dist_label} 주민과의 약속을 {bill1} 개정으로 증명하며 {career1}의 전문성을 쏟아붓겠습니다.",
                f"{josa(career1, '으로/로')} 다진 실력으로 {comm_short}에서 {bill1} 등 민생 법안을 끝까지 책임지겠습니다.",
                f"{bill1} 발의를 통해 {dist_label}의 내일을 바꾸고 {career1} 시절의 초심을 지키겠습니다.",
                f"{t_phrase} {dist_label} 현장을 뛰며 {career1} 경력에 부끄럽지 않은 입법 성과를 내겠습니다.",
            ])

    # 2) 경력 + 2번째/3번째 법안 결합
    for b_alt in [b for b in (bill2, bill3) if b]:
        if career1:
            if is_pr:
                candidates.append(f"{career1}의 시각으로 {b_alt} 등 {committee} 핵심 현안의 해법을 제시하겠습니다.")
                candidates.append(f"{t_phrase} {b_alt} 추진과 {career1} 현장과의 가교 역할을 충실히 하겠습니다.")
            else:
                candidates.append(f"{dist_label} 민심을 나침반 삼아 {career1} 경력과 {b_alt} 입법으로 보답하겠습니다.")
                candidates.append(f"{career1}에서 배운 원칙으로 {b_alt} 통과와 {dist_label} 발전을 앞당기겠습니다.")

    if career2 and bill1:
        if is_pr:
            candidates.append(f"{career2} 경력에서 확인한 현장의 필요를 {bill1} 입법으로 실현하겠습니다.")
        else:
            candidates.append(f"{career2} 경험을 살려 {dist_label} 변화와 {bill1} 통과에 힘을 보태겠습니다.")

    # 3) 법안 중심 + 지역구/상임위/선수 다채로운 템플릿
    for idx_b, b_item in enumerate([b for b in (bill1, bill2, bill3) if b]):
        if is_pr:
            candidates.extend([
                f"{t_phrase} {b_item} 입법 등 {committee}의 실질적 정책 대안을 끝까지 완성하겠습니다.",
                f"{b_item} 발의에 담은 문제의식을 토대로 {comm_short}에서 국민 삶이 나아지는 변화를 만들겠습니다.",
                f"{josa(party, '과/와')} 함께 {b_item} 통과를 이끌어 민생 중심의 의정 성과를 증명하겠습니다.",
                f"말보다 결과로 답하기 위해 {b_item} 추진 등 {comm_short} 민생 입법에 전념하겠습니다.",
                f"약자의 시선에서 출발한 {b_item} 개정이 현장에서 온전히 작동하도록 꼼꼼히 챙기겠습니다.",
            ])
        else:
            candidates.extend([
                f"{dist_label} 주민의 목소리를 담은 {b_item} 입법으로 {committee}에서 확실한 성과를 내겠습니다.",
                f"{t_phrase} {dist_label} 발전과 {b_item} 통과라는 두 마리 토끼를 반드시 잡겠습니다.",
                f"{josa(dist_label, '은/는')} 물론 대한민국의 미래를 위해 {b_item} 등 실효성 높은 법안을 관철하겠습니다.",
                f"{b_item} 발의를 시작으로 {dist_label} 골목마다 체감할 수 있는 {comm_short} 개혁을 펼치겠습니다.",
                f"지역 현장에서 건져 올린 아이디어를 {b_item} 개정으로 연결해 {dist_label}에 보답하겠습니다.",
                f"{committee} 활동과 {b_item} 입법을 축으로 {dist_label}의 더 나은 내일을 열겠습니다.",
                f"현장 밀착 정치로 {dist_label} 현안을 풀고 {b_item} 추진에 모든 역량을 집중하겠습니다.",
            ])
        if idx_b == 0 and bill2:
            if is_pr:
                candidates.append(f"{bill1}과 {bill2} 입법을 축으로 {committee} 민생 개혁에 흔들림 없이 나아가겠습니다.")
            else:
                candidates.append(f"{bill1}·{bill2} 발의에 이어 {dist_label}의 품격을 높이는 책임 입법을 완수하겠습니다.")

    # 4) 경력 중심 (법안이 없거나 경력이 돋보이는 경우: 예 - 국회의장 등)
    for c_item in careers:
        if role_label == "국회의장":
            candidates.extend([
                f"{c_item}의 경륜과 {t_phrase} 여야 협치와 민생 중심의 제22대 국회를 흔들림 없이 이끌겠습니다.",
                f"{dist_label}을 대표하는 {terms}선 중진이자 {c_item} 경력을 바탕으로 대화와 타협의 국회를 지키겠습니다.",
            ])
        elif is_pr:
            candidates.extend([
                f"{c_item} 시절 현장에서 체득한 지혜로 {committee}의 개혁 과제를 흔들림 없이 풀어가겠습니다.",
                f"{t_phrase} {c_item} 경험에 기반한 {comm_short} 정책 대안으로 국민의 기대에 부응하겠습니다.",
            ])
        else:
            candidates.extend([
                f"{c_item} 경력에서 쌓은 신뢰로 {dist_label} 주민과 {committee}의 가교 역할을 다하겠습니다.",
                f"{t_phrase} {c_item} 시절의 현장 감각을 살려 {dist_label}의 숙원 사업을 끝까지 해결하겠습니다.",
            ])

    # 5) 법안·경력 모두가 빈약한 경우의 개인화된 고유 폴백 (지역구+상임위+정당+선수+직책 조합)
    if is_pr:
        candidates.extend([
            f"{t_phrase} {party}의 정책 역량을 {committee} 입법에 쏟아 국민께 효능감 있는 정치를 보이겠습니다.",
            f"{committee}에서 {t_phrase} 시대의 변화에 걸맞은 개혁 입법과 치열한 정책 검증을 이어가겠습니다.",
            f"특정 진영보다 국민의 이익을 우선하며 {party} {comm_short} 위원으로서 정직한 의정활동을 펼치겠습니다.",
        ])
    else:
        candidates.extend([
            f"{josa(dist_label, '이/가')} 키워주신 믿음에 {t_phrase} {committee} 민생 입법과 성실한 의정으로 보답하겠습니다.",
            f"{dist_label} 골목 현장의 생생한 민심을 {committee} 정책과 예산에 빠짐없이 반영하겠습니다.",
            f"{t_phrase} {dist_label}의 도약과 대한민국의 건강한 변화를 이끄는 든든한 일꾼이 되겠습니다.",
        ])

    # 결정론적 셔플/로테이션: 의원 이름·MONA 코드에 따라 문체 시작 순서를 다르게 배분하여
    # 전체 어록의 어투가 균일하게 다채롭도록 구성
    seed_val = sum(ord(ch) for ch in (member.get("mona_cd") or name))
    if len(candidates) > 1:
        rot = seed_val % len(candidates)
        # 상위 3그룹 내 다양성을 해치지 않으면서 시작점 분산
        head = candidates[:min(12, len(candidates))]
        r_head = rot % len(head)
        candidates = head[r_head:] + head[:r_head] + candidates[len(head):]

    return candidates


def assign_unique_quotes(
    members: List[Dict[str, Any]],
    preserved_extra: Optional[Dict[str, Dict[str, Any]]] = None,
) -> List[Dict[str, Any]]:
    """
    299명 전체 의원의 quote가 단 1건도 중복되지 않도록 100% 고유한 한마디 배정.
    - 기존 MEMBER_FUN_AND_EXTRA_DATA 정성 어록(H7X3372O 제외)은 우선 보존.
    - 나머지는 개인화 팩트 템플릿에서 미사용 문장을 배정.
    - 최종 len(set(quotes)) == len(members) 강제 검증.
    """
    if preserved_extra is None:
        try:
            from seed_data import MEMBER_FUN_AND_EXTRA_DATA
            preserved_extra = MEMBER_FUN_AND_EXTRA_DATA
        except Exception:
            preserved_extra = {}

    used_quotes: Set[str] = set()
    pending_indices: List[int] = []

    # 1차 패스: 기존 정성 어록 보존 대상 우선 확정
    for idx, m in enumerate(members):
        name = m.get("name", "")
        mona_cd = m.get("mona_cd", "")
        if name in preserved_extra and mona_cd != "H7X3372O":
            q = (preserved_extra[name].get("quote") or "").strip()
            if q and q not in used_quotes:
                m["quote"] = q
                used_quotes.add(q)
                continue
        pending_indices.append(idx)

    # 2차 패스: 나머지 전원 팩트 기반 고유 어록 배정
    for idx in pending_indices:
        m = members[idx]
        candidates = _build_candidate_quotes(m)
        chosen = None
        for cand in candidates:
            cand_clean = re.sub(r"\s+", " ", cand).strip()
            if cand_clean and cand_clean not in used_quotes:
                chosen = cand_clean
                break

        # 극단적 충돌 시 2차 개인화 팩트 변형
        if not chosen:
            name = m.get("name", "")
            dist_label, is_pr = shorten_district(m.get("district", ""), m.get("party", ""))
            comm = m.get("committee", "국회")
            terms = int(m.get("terms") or 1)
            bills = extract_bill_phrases(m)
            law_note = f"{bills[0]} 등 " if bills else ""
            if is_pr:
                fallback = f"{m.get('party', '')} {terms}선 {comm} {m.get('committee_role_label', '위원')} {name}, {law_note}민생 중심 개혁 입법을 끝까지 완수하겠습니다."
            else:
                fallback = f"{dist_label} {terms}선 {comm} {name}, {law_note}지역 발전과 민생 입법 성과를 책임 있게 만들어가겠습니다."
            chosen = fallback

        m["quote"] = chosen
        used_quotes.add(chosen)

    all_quotes = [m.get("quote", "") for m in members]
    assert len(all_quotes) == len(members), "Member count mismatch"
    assert len(set(all_quotes)) == len(members), f"Duplicate quotes remain: {len(all_quotes)} vs {len(set(all_quotes))}"
    return members


def main():
    for path in (SEED_ALL_PATH, SEED_MAIN_PATH):
        if not os.path.exists(path):
            print(f"[!] Not found: {path}")
            continue
        with open(path, "r", encoding="utf-8") as f:
            data = json.load(f)
        members = data.get("members", [])
        assign_unique_quotes(members)
        data["members"] = members
        with open(path, "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
        print(f"[+] Updated {os.path.basename(path)}: {len(members)}/{len(set(m['quote'] for m in members))} unique quotes (100% unique!)")


if __name__ == "__main__":
    main()
