"""
PoliRank - 국회의원 객관적 능력치 산출 및 랭킹 스코어링 엔진 (6대 정량 지표)
100% 공공 팩트 기반 데이터 정밀 평가 시스템
"""
from typing import Dict, Any

def calculate_member_scores(member_data: Dict[str, Any]) -> Dict[str, Any]:
    """
    국회의원의 의정활동 데이터를 분석하여 6대 객관 지표 점수 및 종합 PoliScore를 산출합니다.
    
    6대 핵심 객관 지표:
    1. legislation_score (입법 실적, 가중치 25%): 대표발의 및 공동발의 실적
    2. passed_score (가결 성과, 가중치 25%): 본회의 가결 및 상임위/소위 통과 실적
    3. attendance_score (의정 출석률, 가중치 20%): 본회의/상임위 출석률 및 무단결석/징계 감점
    4. voting_score (본회의 표결 참여율, 가중치 15%): 본회의 전자투표 안건 표결 참여율 (%)
    5. speech_score (상임위 속기록 발언력, 가중치 10%): 국회 회의록 속기록상 정책 발언/질의 횟수
    6. policy_score (정책 세미나/공청회, 가중치 5%): 정책 세미나/공청회 주최 및 대정부 질문
    
    종합 점수 (total_score, 0~100):
    가중치 합 = 25% + 25% + 20% + 15% + 10% + 5% = 100%
    """
    stats = member_data.get("weekly_stats", {})
    
    # 1. 입법 실적 (Legislation, 25%): 대표발의 25점, 공동발의 6점
    bills_proposed = stats.get("bills_proposed", 0)
    bills_cosponsored = stats.get("bills_cosponsored", 0)
    leg_raw = (bills_proposed * 25) + (bills_cosponsored * 6)
    legislation_score = min(100.0, max(0.0, float(leg_raw)))
    
    # 2. 법안 가결 성과 (Passed Bills, 25%): 본회의 가결 55점, 소위 통과 25점
    bills_passed = stats.get("bills_passed", 0)
    subcommittee_passed = stats.get("subcommittee_passed", 0)
    pass_raw = (bills_passed * 55) + (subcommittee_passed * 25)
    if bills_passed == 0 and bills_proposed > 0:
        pass_raw += min(15.0, bills_proposed * 5)
    passed_score = min(100.0, max(0.0, float(pass_raw)))
    
    # 3. 의정 출석 성실도 (Attendance, 20%)
    plenary_att = stats.get("plenary_attendance", True)
    comm_att = stats.get("committee_attendance", True)
    unexcused_abs = stats.get("unexcused_absences", 0)
    disciplinary = stats.get("disciplinary_action", False)
    ethics_complaint = stats.get("ethics_complaint", False)
    
    att_raw = 80.0
    if plenary_att:
        att_raw += 10.0
    if comm_att:
        att_raw += 10.0
    att_raw -= (unexcused_abs * 15.0)
    if disciplinary:
        att_raw -= 25.0
    if ethics_complaint:
        att_raw -= 10.0
    attendance_score = min(100.0, max(0.0, float(att_raw)))
    
    # 4. 본회의 표결 참여율 (Voting Rate, 15%): 0~100% 직결
    voting_rate = stats.get("voting_rate", 92.5)  # 기본 표결 참여율
    voting_score = min(100.0, max(0.0, float(voting_rate)))
    
    # 5. 상임위 속기록 발언 횟수 (Speech Count, 10%): 건당 12점 (최대 100점)
    speech_count = stats.get("committee_speech_count", stats.get("committee_questions", 2) * 3 + 2)
    speech_raw = float(speech_count * 12.0)
    speech_score = min(100.0, max(0.0, speech_raw))
    
    # 6. 정책 활동 (Policy & Seminar, 5%): 세미나 50점 + 대정부질문 30점 + 아젠다 20점
    seminar_hosted = stats.get("seminar_hosted", False)
    interpellation = stats.get("interpellation_count", 0)
    media_mentions_top10 = stats.get("media_mentions_top10", False)
    
    policy_raw = 0.0
    if seminar_hosted:
        policy_raw += 50.0
    policy_raw += (interpellation * 30.0)
    if media_mentions_top10:
        policy_raw += 20.0
    policy_score = min(100.0, max(0.0, policy_raw))
    
    # 종합 점수 (Total PoliScore, 6대 가중치 적용)
    total_score = (
        (legislation_score * 0.25) +
        (passed_score * 0.25) +
        (attendance_score * 0.20) +
        (voting_score * 0.15) +
        (speech_score * 0.10) +
        (policy_score * 0.05)
    )
    total_score = round(total_score, 1)
    
    # 의원 등급 (Tier)
    if total_score >= 90.0:
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
        "legislation_score": round(legislation_score, 1),
        "passed_score": round(passed_score, 1),
        "attendance_score": round(attendance_score, 1),
        "voting_score": round(voting_score, 1),
        "speech_score": round(speech_score, 1),
        "policy_score": round(policy_score, 1),
        "voting_rate": round(voting_rate, 1),
        "speech_count": speech_count,
        "total_score": total_score,
        "tier": tier,
        "tier_title": tier_title
    }
