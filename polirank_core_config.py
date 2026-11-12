import os
import sys

CURRENT_DIR = os.path.dirname(os.path.abspath(__file__))
if CURRENT_DIR not in sys.path:
    sys.path.insert(0, CURRENT_DIR)

from rank_core import PlatformConfig, ScoringWeightConfig, WeightedScoringEngine

POLIRANK_CONFIG = PlatformConfig(
    platform_id="polirank",
    platform_title="PoliRank (국회의원 정량 랭킹)",
    entity_name_kr="국회의원",
    entity_name_en="National Assembly Member",
    description="제22대 국회의원 299인 6대 핵심 축 및 공공 팩트 기반 정량 랭킹 플랫폼",
    theme_primary_color="#1E3A8A",
    db_filename="polirank.db",
    weights=ScoringWeightConfig(metrics={
        "legislative_score": 0.25, # 입법 활동
        "attendance_score": 0.20,  # 출석률
        "news_buzz_score": 0.20,   # 언론 노출 및 버즈
        "public_cheer_score": 0.15,# 국민 응원/표심
        "promise_score": 0.10,     # 공약 이행률
        "integrity_score": 0.10    # 청렴도/윤리
    }),
    custom_labels={
        "cheer_button": "응원하기 (좋아요)",
        "entity_unit": "인"
    }
)

class PolirankScoringEngine(WeightedScoringEngine):
    """Polirank 전용 확장 스코어링 엔진"""
    pass
