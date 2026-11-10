"""
PoliRank - 국회의원 객관적 능력치 산출 및 랭킹 스코어링 엔진 (v3.0: 6대 핵심 축 + 14대 공공 팩트 지표)

[메이저 vs 마이너 위계 기반 가중치 설계]
1. [메이저 1위 - 30%] 🎯 입법 성과·품질 (passed_score):
   - 본회의 원안가결(3.0배)·수정가결(2.5배)·대안반영폐기(1.0배) 절대 실적 (70%)
   - 입법 타율 / 가결 효율 passage_efficiency (30%, 최소 5건 보정으로 양치기 쪼개기 발의 필터링)
2. [메이저 2위 - 20%] 🗳️ 본회의 표결·참여 (voting_score):
   - 본회의 10개 통과 안건 전자표결 참여율(92%) + 기권 제외 찬반 적극 의사표시율(8%) (이중계산 제거)
3. [핵심 축 - 15%] 📜 입법 발의·협업 (legislation_score):
   - 제22대 대표발의 총 건수 로그 정규화 (75%) + 동료 법안 공동발의 참여수 cosponsor_participations (25%)
4. [신규 핵심 축 - 15%] 🤝 초당적 협치·연대 (bipartisan_score):
   - 타 정당 의원이 1명 이상 공동발의에 동참한 법안 비율 및 타당 의원 비중 (65%)
   - 법안당 평균 공동발의 설득 인원 avg_cosponsors (35%)
5. [중요 축 - 12%] ⚖️ 위원회 직무·성실 (committee_score):
   - 겸임 상임위 수(committee_count) & 핵심 특위(예결/운영/정보/국조특위 등) 참여 + 의장·위원장·간사 직책 + 청렴도 + 성실도
6. [마이너 축 - 8%] 🎙️ 정책 소통·다양성 (policy_score):
   - 발의 법안 소관 분야 다양성 policy_diversity (45%) + 상임위 발언력 (30%) + 정책 세미나·대정부질문·언론 주목도 (25%)
"""
import math
from typing import Dict, Any, Optional


SCORING_METHODOLOGY = {
    "version": "3.0",
    "title": "PoliRank v3.0 — 헌법적 본질과 입법 품질 중심의 6대 축 · 14대 팩트 지표",
    "weights": [
        {
            "key": "passed_score",
            "name": "🎯 입법 성과·품질",
            "weight": 30,
            "tier": "메이저 1위",
            "description": "법안은 개수보다 통과가 본질입니다. 원안/수정가결 및 대안반영폐기 절대 실적(70%)과 입법 타율·효율(30%)을 결합해 쪼개기 양치기 발의를 걸러냅니다.",
        },
        {
            "key": "voting_score",
            "name": "🗳️ 본회의 표결·참여",
            "weight": 20,
            "tier": "메이저 2위",
            "description": "국민의 대리인으로서 헌법기관의 표결 책무를 다했는지 최근 본회의 통과 안건 전자표결 참여율과 찬·반 적극 의사표시 비율로 평가합니다.",
        },
        {
            "key": "legislation_score",
            "name": "📜 입법 발의·협업",
            "weight": 15,
            "tier": "핵심 축",
            "description": "대표발의 총량(75%)과 더불어, 3,300여 건의 동료 의원 법안에 공동발의로 얼마나 적극 협력했는지(25%)를 함께 반영합니다.",
        },
        {
            "key": "bipartisan_score",
            "name": "🤝 초당적 협치·연대",
            "weight": 15,
            "tier": "신규 핵심 축",
            "description": "진영 정치를 넘어 타 정당 의원의 공동발의를 이끌어낸 초당적 협치율(65%)과 법안당 평균 공동발의 설득 인원(35%)을 측정합니다.",
        },
        {
            "key": "committee_score",
            "name": "⚖️ 위원회 직무·성실",
            "weight": 12,
            "tier": "중요 축",
            "description": "겸임 위원회 수, 예결·운영·정보·특위 등 핵심 겸임위 헌신도, 위원장/간사 직책 수행, 징계 여부 및 성실도를 종합 평가합니다.",
        },
        {
            "key": "policy_score",
            "name": "🎙️ 정책 소통·다양성",
            "weight": 8,
            "tier": "마이너 축",
            "description": "단일 영역을 넘어 여러 소관 상임위를 아우르는 입법 분야 다양성(45%), 상임위 발언력(30%), 세미나·대정부질문·언론 주목도(25%)를 반영합니다.",
        },
    ],
}


def calculate_member_scores(member_data: Dict[str, Any]) -> Dict[str, Any]:
    """
    국회의원의 14대 실제 공공 팩트 데이터를 분석하여 6대 핵심 축 점수 및 종합 PoliScore를 산출합니다.
    """
    stats = member_data.get("weekly_stats", {})
    role = member_data.get("committee_role", "member")
    role_bonus = 4.0 if role == "chair" else (2.0 if role == "secretary" else 0.0)

    # 1. [30% 메이저 1위] 입법 성과·품질 (passed_score)
    bills_proposed = float(stats.get("bills_proposed", 0))
    passed_orig = float(stats.get("passed_original", stats.get("bills_passed", 0)))
    passed_amend = float(stats.get("passed_amended", 0))
    # 구버전 입력 호환: passed_original과 passed_amended 합이 bills_passed보다 작을 경우 보정
    bills_passed_total = float(stats.get("bills_passed", passed_orig + passed_amend))
    if passed_orig + passed_amend == 0 and bills_passed_total > 0:
        passed_orig = bills_passed_total
    alt_incorporated = float(stats.get("alt_incorporated", stats.get("subcommittee_passed", 0)))

    effective_passed = (passed_orig * 3.0) + (passed_amend * 2.5) + (alt_incorporated * 1.0)
    if effective_passed > 0:
        abs_passed_score = min(100.0, (math.log1p(effective_passed) / math.log1p(75.0)) * 96.0 + role_bonus)
    elif bills_proposed > 0:
        abs_passed_score = min(18.0, (math.log1p(bills_proposed) / math.log1p(60.0)) * 16.0)
    else:
        abs_passed_score = 0.0

    # 입법 타율 (최소 5건 보정)
    if "passage_efficiency" in stats:
        passage_efficiency = float(stats["passage_efficiency"])
    elif bills_proposed > 0:
        passage_efficiency = min(100.0, (effective_passed / max(5.0, bills_proposed)) * 100.0)
    else:
        passage_efficiency = 0.0

    eff_score = min(100.0, ((min(passage_efficiency, 60.0) / 60.0) ** 0.55) * 100.0) if passage_efficiency > 0 else 0.0
    passed_score = min(100.0, max(0.0, (abs_passed_score * 0.70) + (eff_score * 0.30)))

    # 2. [20% 메이저 2위] 본회의 표결·참여 (voting_score) — 이중계산 제거
    voting_rate = float(stats.get("voting_rate", 90.0))
    active_vote_ratio = float(stats.get("active_vote_ratio", voting_rate))
    voting_score = min(100.0, max(0.0, (voting_rate * 0.92) + (active_vote_ratio * 0.08)))

    # 3. [15% 핵심 축] 입법 발의·협업 (legislation_score)
    prop_score = min(100.0, (math.log1p(bills_proposed) / math.log1p(190.0)) * 100.0) if bills_proposed > 0 else 0.0
    cosponsor_participations = float(stats.get("cosponsor_participations", stats.get("bills_cosponsored", 0)))
    cosp_score = min(100.0, ((min(cosponsor_participations, 260.0) / 260.0) ** 0.55) * 100.0) if cosponsor_participations > 0 else 0.0
    legislation_score = min(100.0, max(0.0, (prop_score * 0.75) + (cosp_score * 0.25)))

    # 4. [15% 신규 핵심 축] 초당적 협치·연대 (bipartisan_score)
    bipartisan_rate = float(stats.get("bipartisan_rate", 0.0))
    bipartisan_share = float(stats.get("bipartisan_cosponsor_share", 0.0))
    avg_cosponsors = float(stats.get("avg_cosponsors", 0.0))

    bip_rate_norm = min(100.0, ((min(bipartisan_rate, 100.0) / 100.0) ** 0.65) * 100.0) if bipartisan_rate > 0 else 0.0
    bip_share_norm = min(100.0, ((min(bipartisan_share, 20.0) / 20.0) ** 0.60) * 100.0) if bipartisan_share > 0 else 0.0
    bip_component = min(100.0, (bip_rate_norm * 0.70) + (bip_share_norm * 0.30))

    if avg_cosponsors <= 0:
        persuasion_score = 0.0
    else:
        persuasion_score = min(100.0, 42.0 + (math.log1p(max(0.0, avg_cosponsors - 8.0)) / math.log1p(16.0)) * 58.0)

    bipartisan_score = min(100.0, max(0.0, (bip_component * 0.65) + (persuasion_score * 0.35)))

    # 5. [12% 중요 축] 위원회 직무·성실 (committee_score)
    committee_count = int(stats.get("committee_count", 1))
    special_duties = stats.get("special_duties", [])
    has_special_duty = bool(stats.get("has_special_duty", len(special_duties) > 0))

    comm_base = 44.0 + (voting_rate * 0.20)
    comm_workload = min(28.0, 12.0 + max(0, committee_count - 1) * 8.0)
    spec_bonus = (10.0 + min(5.0, max(0, len(special_duties) - 1) * 3.0)) if has_special_duty else 0.0
    duty_bonus = 14.0 if role == "chair" else (9.0 if role == "secretary" else 0.0)
    penalty = (
        float(stats.get("unexcused_absences", 0)) * 10.0
        + (25.0 if stats.get("disciplinary_action", False) else 0.0)
        + (10.0 if stats.get("ethics_complaint", False) else 0.0)
    )
    committee_score = min(100.0, max(0.0, comm_base + comm_workload + spec_bonus + duty_bonus - penalty))

    # 6. [8% 마이너 축] 정책 소통·다양성 (policy_score)
    policy_diversity = float(stats.get("policy_diversity", 1 if bills_proposed > 0 else 0))
    div_score = min(100.0, ((min(policy_diversity, 7.0) / 7.0) ** 0.70) * 100.0) if policy_diversity > 0 else 0.0

    speech_count = int(stats.get("committee_speech_count", stats.get("committee_questions", 2) * 3 + 2))
    speech_score = min(100.0, max(0.0, speech_count * 9.5))

    seminar_score = (
        (45.0 if stats.get("seminar_hosted", False) else 10.0)
        + min(35.0, float(stats.get("interpellation_count", 0)) * 18.0)
        + (20.0 if stats.get("media_mentions_top10", False) else 5.0)
    )
    policy_score = min(100.0, max(0.0, (div_score * 0.45) + (speech_score * 0.30) + (seminar_score * 0.25)))

    # 종합 PoliScore (v3.0 위계 가중치 100%)
    total_score = (
        (passed_score * 0.30)
        + (voting_score * 0.20)
        + (legislation_score * 0.15)
        + (bipartisan_score * 0.15)
        + (committee_score * 0.12)
        + (policy_score * 0.08)
    )
    total_score = round(total_score, 1)

    # 의원 등급 (Tier)
    if total_score >= 88.0:
        tier = "S+"
        tier_title = "최우수 의정 마스터"
    elif total_score >= 80.0:
        tier = "S"
        tier_title = "우수 입법 리더"
    elif total_score >= 70.0:
        tier = "A"
        tier_title = "성실 의정 활동가"
    elif total_score >= 60.0:
        tier = "B"
        tier_title = "일반 의정 수행"
    else:
        tier = "C"
        tier_title = "의정 활동 분발요망"

    return {
        "passed_score": round(passed_score, 1),
        "voting_score": round(voting_score, 1),
        "legislation_score": round(legislation_score, 1),
        "bipartisan_score": round(bipartisan_score, 1),
        "committee_score": round(committee_score, 1),
        "attendance_score": round(committee_score, 1),  # 구버전 호환 별칭
        "speech_score": round(speech_score, 1),
        "policy_score": round(policy_score, 1),
        "voting_rate": round(voting_rate, 1),
        "speech_count": speech_count,
        "total_score": total_score,
        "tier": tier,
        "tier_title": tier_title,
    }


def calculate_fun_metrics(
    member_data: Dict[str, Any],
    total_score: Optional[float] = None,
    cheer_count: Optional[int] = None,
    comment_stats: Optional[Dict[str, int]] = None,
) -> Dict[str, float]:
    """
    종합 의정 점수(total_score)와 100% 독립된 재미·화제성 지표를 산출합니다.
    (절대 본질 의정 점수에 합산되거나 영향을 주지 않습니다.)

    - fandom_score (0~100): 인기·팬덤 지수 (실시간 응원 + 긍정 댓글 + 최근 30일 뉴스 + 누적 화제성)
    - controversy_score (0~100°C): 논란·핫이슈 온도 (쟁점 키워드 뉴스 비중·건수 + 반대/기권/불참 성향 + 분발 댓글)
    - hidden_gem_score (0~100): 흙속의 진주 지수 (높은 의정 실력 대비 낮은 언론 노출도)
    """
    ws = member_data.get("weekly_stats") or {}
    c_stats = comment_stats or {}

    resolved_total = float(total_score if total_score is not None else member_data.get("total_score", 65.0))
    resolved_cheer = int(cheer_count if cheer_count is not None else member_data.get("cheer_count", 100))

    tot_comments = sum(int(v) for v in c_stats.values())
    cheer_comments = int(c_stats.get("cheer", 0))
    critique_comments = int(c_stats.get("critique", 0))

    news_cnt = int(member_data.get("news_30d_count", ws.get("news_30d_count", 15)))
    cont_cnt = int(member_data.get("controversy_news_count", ws.get("controversy_news_count", 0)))
    media_mentions = int(member_data.get("media_mentions", 1000))

    vb = ws.get("vote_breakdown") or {}
    v_yes = int(vb.get("찬성", 0))
    v_no = int(vb.get("반대", 0))
    v_abs = int(vb.get("기권", 0))
    v_rate = float(ws.get("voting_rate", member_data.get("voting_rate", 80.0)))

    # 1. 🔥 인기·팬덤 지수 (fandom_score, 0~100)
    news_buzz = min(100.0, (math.log1p(news_cnt) / math.log1p(75.0)) * 100.0)
    media_buzz = min(100.0, (math.log1p(media_mentions) / math.log1p(4800.0)) * 100.0)
    cheer_norm = min(100.0, (math.log1p(resolved_cheer) / math.log1p(400.0)) * 100.0)
    cheer_comm_norm = ((cheer_comments + 2.0) / (tot_comments + 4.0)) * 100.0
    fandom_score = min(
        100.0,
        max(0.0, (news_buzz * 0.42) + (media_buzz * 0.25) + (cheer_norm * 0.23) + (cheer_comm_norm * 0.10)),
    )

    # 2. ⚡ 논란·핫이슈 온도 (controversy_score, 0~100°C)
    cont_cnt_norm = min(100.0, (math.log1p(cont_cnt) / math.log1p(25.0)) * 100.0)
    cont_ratio = cont_cnt / max(4.0, float(news_cnt))
    cont_ratio_norm = min(100.0, ((min(cont_ratio, 0.70) / 0.70) ** 0.70) * 100.0) if cont_cnt > 0 else 0.0
    opp_ratio = ((v_no + v_abs) / max(1, v_yes + v_no + v_abs)) * 100.0
    absent_heat = max(0.0, (55.0 - v_rate) * 0.7) if v_rate < 55.0 else 0.0
    vote_heat = min(100.0, (opp_ratio * 1.4) + absent_heat)
    crit_heat = (critique_comments / (tot_comments + 3.0)) * 100.0
    controversy_score = min(
        100.0,
        max(0.0, (cont_cnt_norm * 0.50) + (cont_ratio_norm * 0.30) + (vote_heat * 0.10) + (crit_heat * 0.10)),
    )

    # 3. 💎 흙속의 진주 지수 (hidden_gem_score, 0~100)
    skill_norm = 0.0 if resolved_total < 60.0 else min(100.0, ((resolved_total - 55.0) / 36.0) * 100.0)
    quiet_news = max(
        0.0,
        min(100.0, (1.0 - (math.log1p(news_cnt) - math.log1p(5.0)) / (math.log1p(45.0) - math.log1p(5.0))) * 100.0),
    )
    quiet_media = max(
        0.0,
        min(100.0, (1.0 - (math.log1p(media_mentions) - math.log1p(500.0)) / (math.log1p(4500.0) - math.log1p(500.0))) * 100.0),
    )
    quiet_norm = (quiet_news * 0.75) + (quiet_media * 0.25)
    gem_raw = ((skill_norm * 0.52) + (quiet_norm * 0.48)) * 1.15
    if resolved_total < 70.0:
        gem_raw *= 0.65
    if news_cnt >= 25:
        gem_raw *= 0.85
    hidden_gem_score = min(100.0, max(0.0, gem_raw))

    return {
        "fandom_score": round(fandom_score, 1),
        "controversy_score": round(controversy_score, 1),
        "hidden_gem_score": round(hidden_gem_score, 1),
    }
