import json
from dataclasses import dataclass, field, asdict
from typing import Dict, Any, Optional

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
