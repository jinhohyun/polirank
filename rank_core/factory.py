from fastapi import FastAPI, HTTPException, Request, Query
from fastapi.middleware.cors import CORSMiddleware
from typing import Optional, List, Dict, Any
from .config import PlatformConfig
from .scoring import BaseScoringEngine, WeightedScoringEngine
from .database import BaseDatabaseManager

def create_ranking_app(
    config: PlatformConfig,
    db: BaseDatabaseManager,
    scoring_engine: Optional[BaseScoringEngine] = None
) -> FastAPI:
    """
    설정과 데이터베이스, 스코어링 엔진을 주입받아
    완전한 REST API 웹 서버 애플리케이션을 생성하는 팩토리 함수
    """
    if scoring_engine is None:
        scoring_engine = WeightedScoringEngine(config.weights)

    app = FastAPI(
        title=config.platform_title,
        description=f"{config.platform_title} - Core Ranking Platform Engine API",
        version="1.0.0"
    )

    app.add_middleware(
        CORSMiddleware,
        allow_origins=["*"],
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    @app.get("/api/config")
    def get_config():
        """플랫폼 화이트라벨 설정 및 정보 반환"""
        return config.to_dict()

    @app.get("/api/rankings")
    def get_rankings(
        category: Optional[str] = None,
        search: Optional[str] = None,
        sort_by: str = "rank",
        limit: int = 100
    ):
        """전체 순위 리스트 및 필터링 검색"""
        entities = db.get_all_entities()
        
        # 스코어링 계산 및 랭킹 정렬
        ranked_entities = scoring_engine.rank_entities(entities)

        # 필터링
        if category and category.lower() != "all":
            ranked_entities = [e for e in ranked_entities if e.get("category") == category or e.get("subcategory") == category]

        if search:
            search_term = search.lower()
            ranked_entities = [
                e for e in ranked_entities 
                if search_term in e.get("name", "").lower() 
                or search_term in e.get("name_en", "").lower()
                or search_term in e.get("description", "").lower()
            ]

        return {
            "platform": config.platform_id,
            "total_count": len(ranked_entities),
            "data": ranked_entities[:limit]
        }

    @app.get("/api/entity/{entity_id}")
    def get_entity_detail(entity_id: str):
        """특정 엔티티 상세 정보 및 투표 수치"""
        entities = db.get_all_entities()
        ranked = scoring_engine.rank_entities(entities)
        target = next((e for e in ranked if e["id"] == entity_id), None)
        if not target:
            raise HTTPException(status_code=404, detail="Entity not found")

        vote_counts = db.get_vote_counts(entity_id)
        target["votes"] = vote_counts
        return target

    @app.post("/api/vote/{entity_id}")
    def post_vote(entity_id: str, vote_type: str, request: Request):
        """투표 API (up/down 또는 support/oppose)"""
        client_ip = request.client.host if request.client else "127.0.0.1"
        db.add_vote(entity_id, vote_type, client_ip)
        vote_counts = db.get_vote_counts(entity_id)
        return {
            "status": "success",
            "entity_id": entity_id,
            "votes": vote_counts
        }

    @app.get("/api/methodology")
    def get_methodology():
        """순위 산출 방법론 명세"""
        return {
            "platform_title": config.platform_title,
            "weights": config.weights.metrics,
            "description": config.description,
            "extra_features": config.extra_features
        }

    return app
