"""
PoliRank - 국회의원 객관적 능력치 산출 및 랭킹 스코어링 엔진 (6대 정량 지표 v2.0)
제22대 국회의원 299인 전체 실제 공공데이터(0~360+건 발의, 가결/대안반영폐기, 본회의 전자표결률, 직책) 정규화 적용
"""
import math
from typing import Dict, Any


def calculate_member_scores(member_data: Dict[str, Any]) -> Dict[str, Any]:
    """
    국회의원의 의정활동 데이터를 분석하여 6대 객관 지표 점수 및 종합 PoliScore를 산출합니다.

    6대 핵심 객관 지표:
    1. legislation_score (입법 실적, 가중치 25%): 22대 실제 대표발의 수(로그 정규화) + 직책 가산
    2. passed_score (가결 성과, 가중치 25%): 본회의 직접가결(원안/수정)*3.5 + 대안반영폐기*1.0 + 직책 가산
    3. attendance_score (의정 출석 성실도, 가중치 20%): 실제 본회의 표결참여율 연계 출석 성실도 + 직책 가산
    4. voting_score (본회의 표결 참여율, 가중치 15%): 최근 본회의 통과 10개 안건 전자투표 참여율 (%)
    5. speech_score (상임위 속기록 발언력, 가중치 10%): 발언 횟수 + 직책 가산
    6. policy_score (정책 세미나/대정부질문/아젠다, 가중치 5%): 세미나/대정부질문/언론아젠다 + 직책 가산

    종합 점수 (total_score, 0~100):
    가중치 합 = 25% + 25% + 20% + 15% + 10% + 5% = 100%
    """
    stats = member_data.get("weekly_stats", {})
    role = member_data.get("committee_role", "member")
    role_bonus = 4.0 if role == "chair" else (2.0 if role == "secretary" else 0.0)

    # 1. 입법 실적 (Legislation, 25%): 제22대 실제 대표발의 수(0~360+건) 로그 정규화
    bills_proposed = float(stats.get("bills_proposed", 0))
    bills_cosponsored = float(stats.get("bills_cosponsored", 0))
    effective_proposed = bills_proposed + min(3.0, bills_cosponsored * 0.25) if bills_proposed < 10 else bills_proposed
    leg_raw = (math.log1p(effective_proposed) / math.log1p(210.0)) * 96.0
    if bills_proposed > 0:
        leg_raw += role_bonus * 0.8
    legislation_score = min(100.0, max(0.0, float(leg_raw)))

    # 2. 법안 가결 성과 (Passed Bills, 25%): 본회의 직접 가결(원안+수정) 3.5배 + 대안반영폐기 1.0배
    bills_passed = float(stats.get("bills_passed", 0))
    subcommittee_passed = float(stats.get("subcommittee_passed", 0))
    effective_passed = (bills_passed * 3.5) + subcommittee_passed
    if effective_passed > 0:
        pass_raw = (math.log1p(effective_passed) / math.log1p(85.0)) * 96.0 + role_bonus
    elif bills_proposed > 0:
        # 가결 전 발의 노력 반영 (최대 18점)
        pass_raw = min(18.0, (math.log1p(bills_proposed) / math.log1p(60.0)) * 15.0)
    else:
        pass_raw = 0.0
    passed_score = min(100.0, max(0.0, float(pass_raw)))

    # 3. 의정 출석 성실도 (Attendance, 20%): 실측 본회의 표결참여율 + 상임위 직책 반영
    voting_rate = float(stats.get("voting_rate", 92.5))
    if "voting_rate" in stats:
        att_raw = max(45.0, 48.0 + (voting_rate * 0.49) + role_bonus)
    else:
        att_raw = 80.0
        if stats.get("plenary_attendance", True):
            att_raw += 10.0
        if stats.get("committee_attendance", True):
            att_raw += 10.0

    unexcused_abs = float(stats.get("unexcused_absences", 0))
    att_raw -= unexcused_abs * 10.0
    if stats.get("disciplinary_action", False):
        att_raw -= 25.0
    if stats.get("ethics_complaint", False):
        att_raw -= 10.0
    attendance_score = min(100.0, max(0.0, float(att_raw)))

    # 4. 본회의 표결 참여율 (Voting Rate, 15%): 0~100% 직결
    voting_score = min(100.0, max(0.0, float(voting_rate)))

    # 5. 상임위 속기록 발언 횟수 (Speech Count, 10%): 발언 횟수 + 직책 가산
    speech_count = int(stats.get("committee_speech_count", stats.get("committee_questions", 2) * 3 + 2))
    speech_raw = (speech_count * 8.5) + (role_bonus * 1.5)
    speech_score = min(100.0, max(0.0, float(speech_raw)))

    # 6. 정책 활동 (Policy & Seminar, 5%): 세미나 40 + 대정부질문(최대 40) + 언론아젠다 15 + 직책 가산
    policy_raw = 0.0
    if stats.get("seminar_hosted", False):
        policy_raw += 40.0
    policy_raw += min(40.0, float(stats.get("interpellation_count", 0)) * 20.0)
    if stats.get("media_mentions_top10", False):
        policy_raw += 15.0
    policy_raw += role_bonus * 2.5
    policy_score = min(100.0, max(0.0, float(policy_raw)))

    # 종합 점수 (Total PoliScore, 6대 가중치 적용)
    total_score = (
        (legislation_score * 0.25)
        + (passed_score * 0.25)
        + (attendance_score * 0.20)
        + (voting_score * 0.15)
        + (speech_score * 0.10)
        + (policy_score * 0.05)
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
        "tier_title": tier_title,
    }
