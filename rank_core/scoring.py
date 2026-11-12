from abc import ABC, abstractmethod
from typing import Dict, List, Any, Tuple
from .config import ScoringWeightConfig

class BaseScoringEngine(ABC):
    """
    추상 스코어링 엔진
    각 도메인(Polirank, Krank 등)에서 상속받거나 가중치 백분율 기반 점수 산출
    """
    def __init__(self, weights: ScoringWeightConfig):
        self.weights = weights

    @abstractmethod
    def calculate_score(self, metrics: Dict[str, float]) -> float:
        """개별 엔티티 메트릭 데이터 기반 종합 점수(0~100) 계산"""
        pass

    @abstractmethod
    def rank_entities(self, entities: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """엔티티 리스트를 받아 점수 계산 및 랭킹/변동폭 부여"""
        pass


class WeightedScoringEngine(BaseScoringEngine):
    """
    설정 기반 가중치 종합 점수 산출 엔진
    """
    def calculate_score(self, metrics: Dict[str, float]) -> float:
        total_score = 0.0
        weight_sum = sum(self.weights.metrics.values())
        if weight_sum <= 0:
            weight_sum = 1.0

        for key, weight in self.weights.metrics.items():
            val = float(metrics.get(key, 50.0))  # 기본 중간값 50점
            # 점수가 0~100 스케일이라고 가정
            val = max(0.0, min(100.0, val))
            total_score += val * (weight / weight_sum)

        return round(total_score, 1)

    def rank_entities(self, entities: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        # 1. 각 엔티티 점수 계산
        scored_entities = []
        for item in entities:
            entity_copy = dict(item)
            # metrics 디셔너리가 있으면 사용, 없으면 루트 Dict에서 추출
            metrics_data = entity_copy.get("metrics", {})
            if not metrics_data:
                # 루트 딕셔너리에서 scoring weight metric 들을 추출
                metrics_data = {k: entity_copy.get(k, 50.0) for k in self.weights.metrics.keys()}
            
            computed_score = self.calculate_score(metrics_data)
            entity_copy["total_score"] = computed_score
            scored_entities.append(entity_copy)

        # 2. 내림차순 정렬
        scored_entities.sort(key=lambda x: x["total_score"], reverse=True)

        # 3. 랭킹 순위 및 Rank Delta 계산
        for idx, item in enumerate(scored_entities):
            new_rank = idx + 1
            old_rank = item.get("previous_rank", new_rank)
            item["current_rank"] = new_rank
            item["rank_delta"] = old_rank - new_rank  # 양수면 상승, 음수면 하강

        return scored_entities
