"""
PoliRank v3.0 - 6대 핵심 축, 14대 실제 공공 팩트 지표, 공동순위, 299인 SVG 단위 및 통합 검증 테스트
"""
import os
import sys
import unittest

CURRENT_DIR = os.path.dirname(os.path.abspath(__file__))
if CURRENT_DIR not in sys.path:
    sys.path.insert(0, CURRENT_DIR)

from database import init_db, get_all_members, get_connection
from scoring import calculate_member_scores, calculate_fun_metrics
from avatar_generator import generate_caricature_svg
from starlette.testclient import TestClient
from app import app


class TestPoliRankV3(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        init_db()
        cls.client = TestClient(app)

    def test_01_v3_six_axes_and_quality_hierarchy(self):
        """v3.0 6대 핵심 축 가중치(30/20/15/15/12/8) 및 양치기 vs 실속협치 변별력 검증"""
        quality_member = {
            "committee_role": "chair",
            "weekly_stats": {
                "bills_proposed": 75,
                "passed_original": 4,
                "passed_amended": 3,
                "alt_incorporated": 25,
                "passage_efficiency": 52.0,
                "bipartisan_rate": 100.0,
                "bipartisan_cosponsor_share": 18.0,
                "avg_cosponsors": 13.5,
                "cosponsor_participations": 210,
                "policy_diversity": 6,
                "committee_count": 2,
                "has_special_duty": True,
                "special_duties": ["예산결산특별위원회"],
                "voting_rate": 100.0,
                "active_vote_ratio": 100.0,
                "committee_speech_count": 9,
                "seminar_hosted": True,
                "interpellation_count": 2,
                "media_mentions_top10": True,
            },
        }
        scores = calculate_member_scores(quality_member)
        for key in [
            "passed_score",
            "voting_score",
            "legislation_score",
            "bipartisan_score",
            "committee_score",
            "policy_score",
            "total_score",
            "tier",
        ]:
            self.assertIn(key, scores)
            if key != "tier":
                self.assertTrue(0 <= scores[key] <= 100, f"{key} out of range: {scores[key]}")

        # 가중치 공식 정합성 검증 (30% + 20% + 15% + 15% + 12% + 8% = 100%)
        expected_total = round(
            scores["passed_score"] * 0.30
            + scores["voting_score"] * 0.20
            + scores["legislation_score"] * 0.15
            + scores["bipartisan_score"] * 0.15
            + scores["committee_score"] * 0.12
            + scores["policy_score"] * 0.08,
            1,
        )
        self.assertAlmostEqual(scores["total_score"], expected_total, delta=0.2)

        # 양치기 쪼개기 발의(다량 발의 200건, 가결 0, 협치 0) vs 실속 협치 입법가 비교
        spam_member = {
            "committee_role": "member",
            "weekly_stats": {
                "bills_proposed": 200,
                "passed_original": 0,
                "passed_amended": 0,
                "alt_incorporated": 0,
                "passage_efficiency": 0.0,
                "bipartisan_rate": 0.0,
                "bipartisan_cosponsor_share": 0.0,
                "avg_cosponsors": 9.0,
                "cosponsor_participations": 30,
                "policy_diversity": 1,
                "committee_count": 1,
                "has_special_duty": False,
                "voting_rate": 70.0,
                "active_vote_ratio": 70.0,
                "committee_speech_count": 3,
            },
        }
        spam_scores = calculate_member_scores(spam_member)
        self.assertGreater(scores["total_score"], spam_scores["total_score"] + 25.0)
        print(
            f"[PASS] v3.0 Scoring Engine verified: Quality={scores['total_score']} ({scores['tier']}), Quantity-only={spam_scores['total_score']} ({spam_scores['tier']})"
        )

    def test_02_caricature_svg_generator_all_299(self):
        """299명 전원 성별/나이대/정당컬러/직책 핀 기반 캐리커쳐 SVG 생성 검증"""
        svg_park_senior = generate_caricature_svg("박지원", "더불어민주당", "#004EA2", gender="male", age=84)
        svg_park_junior = generate_caricature_svg("박지원", "더불어민주당", "#004EA2", gender="male", age=39)
        self.assertNotEqual(svg_park_senior, svg_park_junior)

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

    def test_03_api_root_methodology_and_stats(self):
        """메인 UI(v3.1 2그룹 분리/14대 팩트 시트), /methodology 전용 페이지 및 통계 API 검증"""
        res_root = self.client.get("/")
        self.assertEqual(res_root.status_code, 200)
        self.assertIn("PoliRank", res_root.text)
        self.assertIn('href="/methodology"', res_root.text)
        self.assertIn('data-group="core"', res_root.text)
        self.assertIn('data-group="fun"', res_root.text)
        self.assertIn('data-sort="fandom"', res_root.text)
        self.assertIn('data-sort="controversy"', res_root.text)
        self.assertIn('data-sort="hidden_gem"', res_root.text)
        self.assertIn("fun-mode-banner", res_root.text)
        self.assertIn("modal-fact-sheet-grid", res_root.text)

        res_meth_page = self.client.get("/methodology")
        self.assertEqual(res_meth_page.status_code, 200)
        self.assertIn("weightDonutChart", res_meth_page.text)
        self.assertIn("랭킹 보드로 돌아가기", res_meth_page.text)

        res_js = self.client.get("/static/app.js")
        self.assertEqual(res_js.status_code, 200)
        self.assertIn("renderModalFactSheet14", res_js.text)
        self.assertIn("renderModalNews", res_js.text)
        self.assertIn('loading="lazy"', res_js.text)
        self.assertIn("PAGE_SIZE = 36", res_js.text)

        res_meth = self.client.get("/api/scoring/methodology")
        self.assertEqual(res_meth.status_code, 200)
        meth = res_meth.json()
        self.assertEqual(meth["version"], "3.0")
        self.assertEqual(sum(w["weight"] for w in meth["weights"]), 100)

        res_stats = self.client.get("/api/stats/summary")
        self.assertEqual(res_stats.status_code, 200)
        data = res_stats.json()
        self.assertGreaterEqual(data["total_members"], 290)
        self.assertEqual(data["party_counts"]["all"], data["total_members"])
        self.assertIn("last_updated_at", data)
        self.assertIn("update_schedule", data)
        print(f"[PASS] UI v3.1, /methodology page, & Stats API verified: {data['total_members']} members (updated: {data['last_updated_at']}).")

    def test_04_api_member_ranking_core_and_fun_sorts(self):
        """v3.1 본질 6대 축 + 재미 랭킹 3종(인기·논란·흙속의진주) 정렬 및 공동순위 검증"""
        for sort_key, attr in [
            ("total", "total_score"),
            ("passed", "passed_score"),
            ("voting", "voting_score"),
            ("legislation", "legislation_score"),
            ("bipartisan", "bipartisan_score"),
            ("committee", "committee_score"),
            ("policy", "policy_score"),
            ("fandom", "fandom_score"),
            ("controversy", "controversy_score"),
            ("hidden_gem", "hidden_gem_score"),
            ("cheer", "cheer_count"),
        ]:
            res = self.client.get(f"/api/members?sort_by={sort_key}")
            self.assertEqual(res.status_code, 200)
            members = res.json()["members"]
            self.assertGreaterEqual(len(members), 290)
            vals = [m[attr] for m in members]
            self.assertEqual(vals, sorted(vals, reverse=True), f"Sorting mismatch on {sort_key}")

        # 공동순위 검증
        top_res = self.client.get("/api/members?sort_by=total").json()["members"]
        for idx, m in enumerate(top_res):
            if idx > 0 and top_res[idx - 1]["total_score"] == m["total_score"]:
                self.assertEqual(m["rank"], top_res[idx - 1]["rank"])
                self.assertTrue(m["is_tied"])

        # 정당/검색 필터
        res_party = self.client.get("/api/members?party=더불어민주당")
        self.assertEqual(res_party.status_code, 200)
        self.assertTrue(all(m["party"] == "더불어민주당" for m in res_party.json()["members"]))

        res_etc = self.client.get("/api/members?party=무소속/기타")
        self.assertEqual(res_etc.status_code, 200)
        self.assertGreaterEqual(len(res_etc.json()["members"]), 1)

        print("[PASS] v3.1 Core 6-Axis & Fun 3-Ranking Sortings, Tied Ranking & Filters verified.")

    def test_05_api_member_detail_and_14_metrics(self):
        """의원 상세 6각 레이더 차트 및 14대 실제 공공 팩트 지표(fact_sheet_14) 검증"""
        res = self.client.get("/api/members")
        first_member_id = res.json()["members"][0]["id"]

        res_detail = self.client.get(f"/api/members/{first_member_id}")
        self.assertEqual(res_detail.status_code, 200)
        detail = res_detail.json()

        radar = detail.get("radar_chart")
        self.assertIsNotNone(radar)
        self.assertEqual(len(radar["labels"]), 6)
        self.assertIn("입법품질(30%)", radar["labels"])
        self.assertIn("초당적협치(15%)", radar["labels"])
        self.assertIn("위원회직무(12%)", radar["labels"])

        fs = detail.get("fact_sheet_14")
        self.assertIsNotNone(fs)
        required_14_keys = [
            "bills_proposed",
            "passed_original",
            "passed_amended",
            "alt_incorporated",
            "passage_efficiency",
            "bipartisan_rate",
            "bipartisan_cosponsor_share",
            "avg_cosponsors",
            "cosponsor_participations",
            "policy_diversity",
            "voting_rate",
            "active_vote_ratio",
            "committee_count",
            "has_special_duty",
            "speech_count",
            "media_mentions",
        ]
        for k in required_14_keys:
            self.assertIn(k, fs, f"Missing 14-metric key: {k}")

        # 재미 지표 및 뉴스 데이터 존재 확인
        for fk in ["fandom_score", "controversy_score", "hidden_gem_score", "news_30d_count", "recent_news_titles"]:
            self.assertIn(fk, detail)

        res_avatar = self.client.get(f"/api/members/{first_member_id}/avatar.svg")
        self.assertEqual(res_avatar.status_code, 200)
        self.assertEqual(res_avatar.headers["content-type"], "image/svg+xml")
        print(
            f"[PASS] Detail Radar, 14-Metric Fact Sheet & Fun Badges verified for: {detail['name']} ({detail['total_score']}점, 팬덤 {detail['fandom_score']})"
        )

    def test_06_cheer_comment_and_total_score_isolation(self):
        """실시간 응원/댓글 및 재미 지표가 total_score에 영향을 주지 않는 완전 격리 불변성 검증"""
        res = self.client.get("/api/members")
        member = res.json()["members"][0]
        member_id = member["id"]
        old_cheer = member["cheer_count"]
        old_total = member["total_score"]

        # 재미 지표 단위 계산 불변성 검증 (뉴스·응원이 극단적으로 달라져도 total_score는 불변)
        fun_low = calculate_fun_metrics({"news_30d_count": 2, "media_mentions": 100}, total_score=old_total, cheer_count=10)
        fun_high = calculate_fun_metrics({"news_30d_count": 90, "controversy_news_count": 40, "media_mentions": 8000}, total_score=old_total, cheer_count=5000)
        self.assertGreater(fun_high["fandom_score"], fun_low["fandom_score"])
        self.assertGreater(fun_high["controversy_score"], fun_low["controversy_score"])

        res_cheer = self.client.post(f"/api/members/{member_id}/cheer")
        self.assertEqual(res_cheer.status_code, 200)
        new_cheer = res_cheer.json()["cheer_count"]
        self.assertEqual(new_cheer, old_cheer + 1)

        res_comment = self.client.post(
            f"/api/members/{member_id}/comments",
            json={
                "author": "유권자 시민",
                "stance": "critique",
                "content": "재미 지표가 변동되어도 본질 의정 점수 total_score는 영향을 받지 않아야 합니다.",
            },
        )
        self.assertEqual(res_comment.status_code, 200)
        comment_id = res_comment.json()["comment"]["id"]
        self.assertIsNotNone(comment_id)

        # 응원/댓글 이후에도 total_score 불변 확인
        after_detail = self.client.get(f"/api/members/{member_id}").json()
        self.assertEqual(after_detail["total_score"], old_total)

        conn = get_connection()
        conn.execute("DELETE FROM comments WHERE id = ?", (comment_id,))
        conn.execute("UPDATE members SET cheer_count = ? WHERE id = ?", (old_cheer, member_id))
        from database import _refresh_fun_scores_in_conn
        _refresh_fun_scores_in_conn(conn, member_id)
        conn.commit()
        conn.close()
        print(f"[PASS] Cheer, Comment & total_score Isolation verified (Cheer: {old_cheer}->{new_cheer}, total_score={old_total} unchanged)")


if __name__ == "__main__":
    unittest.main()
