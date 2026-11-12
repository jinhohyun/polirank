from abc import ABC, abstractmethod
from typing import Dict, List, Any

class BaseCollector(ABC):
    """
    공통 데이터 수집/크롤러 베이스 인터페이스
    뉴스, 소셜 트렌드, 공식 데이터 수집기 구현체
    """

    @abstractmethod
    def collect_metrics_for_entity(self, entity_id: str, name: str) -> Dict[str, float]:
        """특정 엔티티의 최신 메트릭(뉴스/버즈 점수 등) 수집"""
        pass

    @abstractmethod
    def collect_batch(self, entities: List[Dict[str, Any]]) -> Dict[str, Dict[str, float]]:
        """배치 수집"""
        pass


class MockTrendCollector(BaseCollector):
    """
    기본 트렌드/버즈 수집 템플릿 구현체
    """
    def collect_metrics_for_entity(self, entity_id: str, name: str) -> Dict[str, float]:
        return {
            "news_score": 75.0,
            "activity_score": 80.0,
            "approval_score": 70.0
        }

    def collect_batch(self, entities: List[Dict[str, Any]]) -> Dict[str, Dict[str, float]]:
        results = {}
        for ent in entities:
            results[ent["id"]] = self.collect_metrics_for_entity(ent["id"], ent["name"])
        return results
