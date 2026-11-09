"""
PoliRank MVP - 6대 정량 지표 & 재미요소 단위 및 통합 기능 검증 테스트 스크립트
"""
import os
import sys
import unittest

CURRENT_DIR = os.path.dirname(os.path.abspath(__file__))
if CURRENT_DIR not in sys.path:
    sys.path.insert(0, CURRENT_DIR)

from database import init_db, get_all_members, get_member_by_id, cheer_member, add_comment, get_comments
from scoring import calculate_member_scores
from avatar_generator import generate_caricature_svg
from starlette.testclient import TestClient
from app import app

class TestPoliRankMVP(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        init_db()
        cls.client = TestClient(app)

    def test_01_six_metrics_scoring_engine(self):
        """6대 객관적 정량 지표 계산 엔진 단위 테스트"""
        sample_member = {
            "weekly_stats": {
                "bills_proposed": 3,
                "bills_cosponsored": 5,
                "bills_passed": 1,
                "subcommittee_passed": 1,
                "plenary_attendance": True,
                "committee_attendance": True,
                "voting_rate": 98.5,
                "committee_speech_count": 8,
                "seminar_hosted": True,
                "interpellation_count": 1,
                "unexcused_absences": 0
            }
        }
        scores = calculate_member_scores(sample_member)
        self.assertIn("legislation_score", scores)
        self.assertIn("passed_score", scores)
        self.assertIn("attendance_score", scores)
        self.assertIn("voting_score", scores)
        self.assertIn("speech_score", scores)
        self.assertIn("policy_score", scores)
        self.assertIn("total_score", scores)
        self.assertIn("tier", scores)

        # 6대 점수 범위 검증 (0~100)
        for metric in ["legislation_score", "passed_score", "attendance_score", "voting_score", "speech_score", "policy_score", "total_score"]:
            self.assertTrue(0 <= scores[metric] <= 100, f"{metric} out of range: {scores[metric]}")
            
        print(f"[PASS] 6-Metrics Scoring Engine verified: Total={scores['total_score']} ({scores['tier']} Tier)")

    def test_02_caricature_svg_generator_detailed(self):
        """정밀화된 만화풍/캐리커쳐 SVG 아바타 생성기 검증"""
        # 이준석 (2:8 가르마 & 청년 헤어)
        svg_lee = generate_caricature_svg("이준석", "개혁신당", "#FF7920")
        self.assertIn("</svg>", svg_lee)
        self.assertIn("#FF7920", svg_lee)

        # 박지원 (연륜 백발 & 눈가주름)
        svg_park = generate_caricature_svg("박지원", "더불어민주당", "#004EA2")
        self.assertIn("</svg>", svg_park)

        # 정청래 (굵은 뿔테)
        svg_jung = generate_caricature_svg("정청래", "더불어민주당", "#004EA2")
        self.assertIn("</svg>", svg_jung)
        print("[PASS] Refined Caricature SVG Avatar generator verified.")

    def test_03_api_root_and_stats(self):
        """메인 페이지 및 6대 지표 통계 API 응답 검증"""
        res_root = self.client.get("/")
        self.assertEqual(res_root.status_code, 200)
        self.assertIn("PoliRank", res_root.text)

        res_stats = self.client.get("/api/stats/summary")
        self.assertEqual(res_stats.status_code, 200)
        data = res_stats.json()
        self.assertGreaterEqual(data["total_members"], 30)
        self.assertGreaterEqual(data["total_cheers"], 0)
        print(f"[PASS] Main & Stats API verified: {data['total_members']} members.")

    def test_04_api_member_ranking_and_six_sorts(self):
        """6대 지표 정렬 및 정당 필터링 API 검증"""
        # 종합 순위 정렬
        res = self.client.get("/api/members?sort_by=total")
        self.assertEqual(res.status_code, 200)
        members = res.json()["members"]
        self.assertGreaterEqual(len(members), 30)

        # 신규: 표결 참여율 순위 정렬
        res_voting = self.client.get("/api/members?sort_by=voting")
        self.assertEqual(res_voting.status_code, 200)
        voting_scores = [m["voting_score"] for m in res_voting.json()["members"]]
        self.assertEqual(voting_scores, sorted(voting_scores, reverse=True))

        # 신규: 상임위 발언 횟수 순위 정렬
        res_speech = self.client.get("/api/members?sort_by=speech")
        self.assertEqual(res_speech.status_code, 200)
        speech_scores = [m["speech_score"] for m in res_speech.json()["members"]]
        self.assertEqual(speech_scores, sorted(speech_scores, reverse=True))

        # 정당 필터링
        res_party = self.client.get("/api/members?party=더불어민주당")
        self.assertEqual(res_party.status_code, 200)
        for m in res_party.json()["members"]:
            self.assertEqual(m["party"], "더불어민주당")
        print("[PASS] 6-Metric Sortings & Party Filters verified.")

    def test_05_api_member_detail_and_hexagon_chart(self):
        """의원 상세 정보 및 6각 레이더 차트/재미요소 검증"""
        res = self.client.get("/api/members")
        first_member_id = res.json()["members"][0]["id"]

        res_detail = self.client.get(f"/api/members/{first_member_id}")
        self.assertEqual(res_detail.status_code, 200)
        detail = res_detail.json()
        
        # 6각 레이더 차트 검증
        radar = detail.get("radar_chart")
        self.assertIsNotNone(radar)
        self.assertEqual(len(radar["labels"]), 6)
        self.assertEqual(len(radar["datasets"][0]["data"]), 6)

        # 재미 요소 검증 (어록, 키워드, 언론 언급)
        self.assertIn("quote", detail)
        self.assertIn("keywords", detail)
        self.assertIn("media_mentions", detail)
        self.assertIn("official_photo_url", detail)

        # SVG Avatar 엔드포인트
        res_avatar = self.client.get(f"/api/members/{first_member_id}/avatar.svg")
        self.assertEqual(res_avatar.status_code, 200)
        self.assertEqual(res_avatar.headers["content-type"], "image/svg+xml")
        print(f"[PASS] Hexagon Radar Chart & Fun Factors verified for member: {detail['name']} (Quote: {detail['quote'][:20]}...)")

    def test_06_cheer_and_comment_features(self):
        """실시간 응원 및 토론 댓글 기능 검증"""
        res = self.client.get("/api/members")
        member = res.json()["members"][0]
        member_id = member["id"]
        old_cheer = member["cheer_count"]

        # Cheer
        res_cheer = self.client.post(f"/api/members/{member_id}/cheer")
        self.assertEqual(res_cheer.status_code, 200)
        new_cheer = res_cheer.json()["cheer_count"]
        self.assertEqual(new_cheer, old_cheer + 1)

        # Comment
        res_comment = self.client.post(f"/api/members/{member_id}/comments", json={
            "author": "유권자 시민",
            "stance": "proposal",
            "content": "6대 객관 지표로 투명하게 평가하니 신뢰가 갑니다!"
        })
        self.assertEqual(res_comment.status_code, 200)
        comment_id = res_comment.json()["comment"]["id"]
        self.assertIsNotNone(comment_id)
        print(f"[PASS] Cheer and Comment features verified (Cheer: {old_cheer} -> {new_cheer})")

if __name__ == "__main__":
    unittest.main()
