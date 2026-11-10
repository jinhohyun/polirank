"""
PoliRank v2.0 - 299인 전체 실데이터, 6대 정량 지표, 공동순위, 299인 SVG 아바타 단위 및 통합 검증 테스트 스크립트
"""
import os
import sys
import unittest

CURRENT_DIR = os.path.dirname(os.path.abspath(__file__))
if CURRENT_DIR not in sys.path:
    sys.path.insert(0, CURRENT_DIR)

from database import init_db, get_all_members, get_connection
from scoring import calculate_member_scores
from avatar_generator import generate_caricature_svg
from starlette.testclient import TestClient
from app import app


class TestPoliRankV2(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        init_db()
        cls.client = TestClient(app)

    def test_01_six_metrics_scoring_engine(self):
        """6대 객관적 정량 지표 계산 엔진 단위 테스트 (299인 실데이터 스케일 포함)"""
        sample_member = {
            "committee_role": "chair",
            "weekly_stats": {
                "bills_proposed": 155,
                "bills_cosponsored": 200,
                "bills_passed": 9,
                "subcommittee_passed": 64,
                "voting_rate": 90.0,
                "committee_speech_count": 10,
                "seminar_hosted": True,
                "interpellation_count": 2,
                "media_mentions_top10": True,
                "unexcused_absences": 0,
            },
        }
        scores = calculate_member_scores(sample_member)
        for key in [
            "legislation_score",
            "passed_score",
            "attendance_score",
            "voting_score",
            "speech_score",
            "policy_score",
            "total_score",
            "tier",
        ]:
            self.assertIn(key, scores)

        for metric in [
            "legislation_score",
            "passed_score",
            "attendance_score",
            "voting_score",
            "speech_score",
            "policy_score",
            "total_score",
        ]:
            self.assertTrue(0 <= scores[metric] <= 100, f"{metric} out of range: {scores[metric]}")

        # 저활동 vs 고활동 변별력 검증
        low_member = {
            "committee_role": "member",
            "weekly_stats": {
                "bills_proposed": 8,
                "bills_passed": 0,
                "subcommittee_passed": 0,
                "voting_rate": 30.0,
                "committee_speech_count": 2,
                "seminar_hosted": False,
                "interpellation_count": 0,
            },
        }
        low_scores = calculate_member_scores(low_member)
        self.assertGreater(scores["total_score"], low_scores["total_score"] + 25.0)
        print(
            f"[PASS] 6-Metrics Scoring Engine v2.0 verified: High={scores['total_score']} ({scores['tier']}), Low={low_scores['total_score']} ({low_scores['tier']})"
        )

    def test_02_caricature_svg_generator_all_299(self):
        """299명 전원 성별/나이대/정당컬러/직책 핀 기반 캐리커쳐 SVG 생성 검증"""
        svg_lee = generate_caricature_svg("이준석", "개혁신당", "#FF7920", gender="male", age=41)
        self.assertIn("</svg>", svg_lee)
        self.assertIn("#FF7920", svg_lee)

        # 동명이인 박지원(84세 원로 vs 39세 초선) SVG 차별화 검증
        svg_park_senior = generate_caricature_svg("박지원", "더불어민주당", "#004EA2", gender="male", age=84)
        svg_park_junior = generate_caricature_svg("박지원", "더불어민주당", "#004EA2", gender="male", age=39)
        self.assertIn("</svg>", svg_park_senior)
        self.assertIn("</svg>", svg_park_junior)
        self.assertNotEqual(svg_park_senior, svg_park_junior)

        # 위원장 핀 포함 검증
        svg_chair = generate_caricature_svg("서영교", "더불어민주당", "#004EA2", gender="female", age=62, committee_role="chair")
        self.assertIn("★", svg_chair)

        # DB에 적재된 전체 299명 전원 SVG 무결성 테스트
        all_members = get_all_members()
        self.assertGreaterEqual(len(all_members), 290)
        for m in all_members:
            svg = generate_caricature_svg(
                name=m["name"],
                party=m["party"],
                party_color=m["party_color"],
                gender=m.get("gender"),
                age=m.get("age"),
                committee_role=m.get("committee_role"),
            )
            self.assertIn("<svg", svg)
            self.assertIn("</svg>", svg)

        print(f"[PASS] Caricature SVG Avatar generator verified for all {len(all_members)} members.")

    def test_03_api_root_and_stats_299(self):
        """메인 페이지 UI 최적화 요소 및 290명 이상 통계 API 응답 검증"""
        res_root = self.client.get("/")
        self.assertEqual(res_root.status_code, 200)
        self.assertIn("PoliRank", res_root.text)
        self.assertIn("loadMoreMembers", res_root.text)
        self.assertIn("party-count", res_root.text)

        res_js = self.client.get("/static/app.js")
        self.assertEqual(res_js.status_code, 200)
        self.assertIn('loading="lazy"', res_js.text)
        self.assertIn("PAGE_SIZE = 36", res_js.text)

        res_stats = self.client.get("/api/stats/summary")
        self.assertEqual(res_stats.status_code, 200)
        data = res_stats.json()
        self.assertGreaterEqual(data["total_members"], 290)
        self.assertIn("party_counts", data)
        self.assertEqual(data["party_counts"]["all"], data["total_members"])
        print(f"[PASS] Main, UI Pagination/LazyLoad & Stats API verified: {data['total_members']} members.")

    def test_04_api_member_ranking_tied_and_filters(self):
        """290명 이상 6대 지표 정렬, 공동순위(Tied Ranking), 정당/검색 필터링 검증"""
        res = self.client.get("/api/members?sort_by=total")
        self.assertEqual(res.status_code, 200)
        members = res.json()["members"]
        self.assertGreaterEqual(len(members), 290)

        # 종합 점수 내림차순 및 공동순위 일관성 검증
        totals = [m["total_score"] for m in members]
        self.assertEqual(totals, sorted(totals, reverse=True))
        for idx, m in enumerate(members):
            if idx > 0:
                if members[idx - 1]["total_score"] == m["total_score"]:
                    self.assertEqual(m["rank"], members[idx - 1]["rank"])
                    self.assertTrue(m["is_tied"])
                    self.assertTrue(m["rank_text"].startswith("공동 "))
                else:
                    self.assertEqual(m["rank"], idx + 1)

        # 표결 참여율 순위 정렬
        res_voting = self.client.get("/api/members?sort_by=voting")
        self.assertEqual(res_voting.status_code, 200)
        voting_scores = [m["voting_score"] for m in res_voting.json()["members"]]
        self.assertEqual(voting_scores, sorted(voting_scores, reverse=True))
        # 표결 참여율 동점자(예: 100%) 공동 1위 확인
        self.assertTrue(res_voting.json()["members"][0]["is_tied"])
        self.assertEqual(res_voting.json()["members"][0]["rank_text"], "공동 1위")

        # 정당 필터링 (더불어민주당 & 무소속/기타)
        res_party = self.client.get("/api/members?party=더불어민주당")
        self.assertEqual(res_party.status_code, 200)
        self.assertGreaterEqual(len(res_party.json()["members"]), 100)
        for m in res_party.json()["members"]:
            self.assertEqual(m["party"], "더불어민주당")

        res_etc = self.client.get("/api/members?party=무소속/기타")
        self.assertEqual(res_etc.status_code, 200)
        self.assertGreaterEqual(len(res_etc.json()["members"]), 1)

        # 검색 필터링 (서영교)
        res_search = self.client.get("/api/members?search=서영교")
        self.assertEqual(res_search.status_code, 200)
        self.assertTrue(any(m["name"] == "서영교" for m in res_search.json()["members"]))

        print(f"[PASS] 299-member Ranking, Tied Ranking & Filters verified (count={len(members)}).")

    def test_05_api_member_detail_and_hexagon_chart(self):
        """의원 상세 정보, 6각 레이더 차트, 최근 법안 및 SVG 아바타 엔드포인트 검증"""
        res = self.client.get("/api/members")
        first_member_id = res.json()["members"][0]["id"]

        res_detail = self.client.get(f"/api/members/{first_member_id}")
        self.assertEqual(res_detail.status_code, 200)
        detail = res_detail.json()

        radar = detail.get("radar_chart")
        self.assertIsNotNone(radar)
        self.assertEqual(len(radar["labels"]), 6)
        self.assertEqual(len(radar["datasets"][0]["data"]), 6)

        self.assertIn("quote", detail)
        self.assertIn("keywords", detail)
        self.assertEqual(len(detail["keywords"]), 3)
        self.assertIn("media_mentions", detail)
        self.assertIn("official_photo_url", detail)
        self.assertIn("recent_bills", detail)

        res_avatar = self.client.get(f"/api/members/{first_member_id}/avatar.svg")
        self.assertEqual(res_avatar.status_code, 200)
        self.assertEqual(res_avatar.headers["content-type"], "image/svg+xml")
        print(f"[PASS] Hexagon Radar Chart & Detail verified for: {detail['name']} ({detail['total_score']}점)")

    def test_06_cheer_and_comment_features(self):
        """실시간 응원 및 토론 댓글 기능 검증"""
        res = self.client.get("/api/members")
        member = res.json()["members"][0]
        member_id = member["id"]
        old_cheer = member["cheer_count"]

        res_cheer = self.client.post(f"/api/members/{member_id}/cheer")
        self.assertEqual(res_cheer.status_code, 200)
        new_cheer = res_cheer.json()["cheer_count"]
        self.assertEqual(new_cheer, old_cheer + 1)

        res_comment = self.client.post(
            f"/api/members/{member_id}/comments",
            json={
                "author": "유권자 시민",
                "stance": "proposal",
                "content": "299인 전체 6대 객관 지표로 투명하게 평가하니 신뢰가 갑니다!",
            },
        )
        self.assertEqual(res_comment.status_code, 200)
        comment_id = res_comment.json()["comment"]["id"]
        self.assertIsNotNone(comment_id)

        # 테스트 데이터 정리 (프로덕션 DB 무결성 유지)
        conn = get_connection()
        conn.execute("DELETE FROM comments WHERE id = ?", (comment_id,))
        conn.execute("UPDATE members SET cheer_count = ? WHERE id = ?", (old_cheer, member_id))
        conn.commit()
        conn.close()
        print(f"[PASS] Cheer and Comment features verified (Cheer: {old_cheer} -> {new_cheer})")


if __name__ == "__main__":
    unittest.main()
