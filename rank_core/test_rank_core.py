import os
import sys
import unittest

# rank_core 상위 디렉터리를 path에 추가
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from rank_core import PlatformConfig, ScoringWeightConfig, WeightedScoringEngine, BaseDatabaseManager, create_ranking_app
from fastapi.testclient import TestClient

class TestRankCore(unittest.TestCase):
    def setUp(self):
        self.db_path = "test_core.db"
        if os.path.exists(self.db_path):
            os.remove(self.db_path)

        self.config = PlatformConfig(
            platform_id="test_platform",
            platform_title="테스트 랭킹 플랫폼",
            entity_name_kr="대상",
            entity_name_en="Target",
            weights=ScoringWeightConfig(metrics={
                "poll_score": 0.4,
                "news_score": 0.3,
                "activity_score": 0.3
            })
        )
        self.db = BaseDatabaseManager(self.db_path)
        self.engine = WeightedScoringEngine(self.config.weights)

    def tearDown(self):
        if os.path.exists(self.db_path):
            os.remove(self.db_path)

    def test_database_and_scoring(self):
        # Sample Entity 추가
        self.db.upsert_entity({
            "id": "item1",
            "name": "아이템 A",
            "category": "CatA",
            "metrics": {"poll_score": 90.0, "news_score": 80.0, "activity_score": 70.0}
        })
        self.db.upsert_entity({
            "id": "item2",
            "name": "아이템 B",
            "category": "CatB",
            "metrics": {"poll_score": 50.0, "news_score": 60.0, "activity_score": 50.0}
        })

        entities = self.db.get_all_entities()
        self.assertEqual(len(entities), 2)

        ranked = self.engine.rank_entities(entities)
        # item1 점수 = 90*0.4 + 80*0.3 + 70*0.3 = 36 + 24 + 21 = 81.0
        self.assertEqual(ranked[0]["id"], "item1")
        self.assertEqual(ranked[0]["total_score"], 81.0)
        self.assertEqual(ranked[0]["current_rank"], 1)

        # item2 점수 = 50*0.4 + 60*0.3 + 50*0.3 = 20 + 18 + 15 = 53.0
        self.assertEqual(ranked[1]["id"], "item2")
        self.assertEqual(ranked[1]["total_score"], 53.0)
        self.assertEqual(ranked[1]["current_rank"], 2)

    def test_factory_and_api(self):
        self.db.upsert_entity({
            "id": "item1",
            "name": "아이템 A",
            "metrics": {"poll_score": 90.0, "news_score": 80.0, "activity_score": 70.0}
        })
        app = create_ranking_app(self.config, self.db, self.engine)
        client = TestClient(app)

        # 1. Config API 테스트
        res_config = client.get("/api/config")
        self.assertEqual(res_config.status_code, 200)
        self.assertEqual(res_config.json()["platform_id"], "test_platform")

        # 2. Rankings API 테스트
        res_rankings = client.get("/api/rankings")
        self.assertEqual(res_rankings.status_code, 200)
        data = res_rankings.json()["data"]
        self.assertEqual(len(data), 1)
        self.assertEqual(data[0]["name"], "아이템 A")

        # 3. Vote API 테스트
        res_vote = client.post("/api/vote/item1?vote_type=up")
        self.assertEqual(res_vote.status_code, 200)
        self.assertEqual(res_vote.json()["votes"]["up"], 1)

        # 4. i18n API 테스트
        res_i18n = client.get("/api/i18n?lang=en")
        self.assertEqual(res_i18n.status_code, 200)
        self.assertEqual(res_i18n.json()["translations"]["rank"], "Rank")


if __name__ == "__main__":
    unittest.main()
