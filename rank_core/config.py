import json
import os
from dataclasses import dataclass, field, asdict
from typing import Dict, Any, Optional


# ── 개발자 후원(공통) ────────────────────────────────────────────────────────
# 진호 님이 만드는 **모든 사이트**에 동일하게 적용되는 후원 채널.
# 2026-11-16 등록: Buy Me a Coffee — https://buymeacoffee.com/javaleo
#   · 한 곳만 고치면 polirank·krank·앞으로 만드는 사이트 전부에 반영된다.
#   · 환경변수 BUYMEACOFFEE_URL 로 덮어쓸 수 있다(배포 환경별 계정 분리 대비).
DEFAULT_BUYMEACOFFEE_URL = "https://buymeacoffee.com/javaleo"
DEFAULT_SUPPORT_MESSAGE = (
    "이 사이트는 정파와 자본으로부터 독립된 1인 개발자가 운영합니다. "
    "서버 유지비와 데이터 파이프라인 고도화를 위해 커피 한 잔을 응원해 주세요!"
)


def get_buymeacoffee_url() -> str:
    """공통 후원 링크 — 모든 사이트가 이 함수 하나만 부르면 된다."""
    return (os.environ.get("BUYMEACOFFEE_URL") or DEFAULT_BUYMEACOFFEE_URL).strip()


def get_support_links() -> Dict[str, str]:
    """후원 링크 묶음(사이트 공통 응답 스키마)."""
    return {
        "buymeacoffee": get_buymeacoffee_url(),
        "support_message": (os.environ.get("SUPPORT_MESSAGE") or DEFAULT_SUPPORT_MESSAGE).strip(),
    }


@dataclass
class ScoringWeightConfig:
    """순위 집계 가중치 설정 (합계 1.0 또는 100%)"""
    metrics: Dict[str, float] = field(default_factory=lambda: {
        "poll_score": 0.30,      # 여론조사 / 팬덤 투표
        "news_score": 0.25,      # 언론 노출 / 소셜 버즈
        "activity_score": 0.25,  # 의정/공식 활동 / 음원/공연 활동
        "approval_score": 0.20   # 호감도 / 긍정 비율
    })

    def validate(self) -> bool:
        total = sum(self.metrics.values())
        return abs(total - 1.0) < 0.01 or abs(total - 100.0) < 0.1


@dataclass
class PlatformConfig:
    """플랫폼 화이트라벨 설정"""
    platform_id: str                      # e.g., 'polirank', 'krank'
    platform_title: str                   # e.g., 'Polirank (정치인 랭킹)', 'K-Rank (K-컬처 랭킹)'
    entity_name_kr: str                   # e.g., '정치인', '아티스트'
    entity_name_en: str                   # e.g., 'Politician', 'Artist'
    description: str = ""
    theme_primary_color: str = "#1E40AF"  # 대표 메인 컬러
    theme_secondary_color: str = "#3B82F6"
    db_filename: str = "app.db"
    election_safe_mode: bool = False      # 선거 기간 여론조사/순위 규제 대응 세이프 모드
    weights: ScoringWeightConfig = field(default_factory=ScoringWeightConfig)
    custom_labels: Dict[str, str] = field(default_factory=dict)
    extra_features: Dict[str, bool] = field(default_factory=lambda: {
        "enable_user_voting": True,
        "enable_news_buzz": True,
        "enable_i18n": True,
        "enable_methodology_page": True
    })

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)

    @classmethod
    def from_json(cls, json_path: str) -> "PlatformConfig":
        with open(json_path, "r", encoding="utf-8") as f:
            data = json.load(f)
        weights_data = data.pop("weights", {})
        weights = ScoringWeightConfig(metrics=weights_data) if weights_data else ScoringWeightConfig()
        return cls(weights=weights, **data)
