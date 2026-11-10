"""
PoliRank v3.2 - 6대 핵심 축, 14대 실제 공공 팩트 지표, 재미 랭킹 격리 및 3중 중복 응원 방지 검증 테스트
"""
import os
import sys
import tempfile
import unittest

CURRENT_DIR = os.path.dirname(os.path.abspath(__file__))
if CURRENT_DIR not in sys.path:
    sys.path.insert(0, CURRENT_DIR)

import database as db_module
from database import init_db, get_all_members, get_connection
from seed_data import seed
from scoring import calculate_member_scores, calculate_fun_metrics
from avatar_generator import generate_caricature_svg
from starlette.testclient import TestClient
from app import app, COMMENT_RATE_LIMITS, FEEDBACK_RATE_LIMITS


class TestPoliRankV3(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls._orig_db_path = db_module.DB_PATH
        cls._tmp_dir = tempfile.TemporaryDirectory()
        cls._test_db_path = os.path.join(cls._tmp_dir.name, "test_polirank.db")
        db_module.DB_PATH = cls._test_db_path
        COMMENT_RATE_LIMITS.clear()
        FEEDBACK_RATE_LIMITS.clear()
        seed(preserve_user_data=False)
        cls.client = TestClient(app)

    @classmethod
    def tearDownClass(cls):
        try:
            cls.client.close()
        except Exception:
            pass
        db_module.DB_PATH = cls._orig_db_path
        cls._tmp_dir.cleanup()

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
        self.assertIn("office-login-modal", res_root.text)
        self.assertIn("admin-issue-modal", res_root.text)
        self.assertIn("modal-office-notice-section", res_root.text)
        self.assertIn("dev-support-modal", res_root.text)
        self.assertIn("feedback-modal", res_root.text)
        self.assertIn("admin-tab-feedbacks", res_root.text)
        self.assertIn("admin-tab-devsupport", res_root.text)
        self.assertNotIn("polirank_admin_2026", res_root.text)

        res_meth_page = self.client.get("/methodology")
        self.assertEqual(res_meth_page.status_code, 200)
        self.assertIn("weightDonutChart", res_meth_page.text)
        self.assertIn("랭킹 보드로 돌아가기", res_meth_page.text)

        res_js = self.client.get("/static/app.js")
        self.assertEqual(res_js.status_code, 200)
        self.assertIn("renderModalFactSheet14", res_js.text)
        self.assertIn("renderModalNews", res_js.text)
        self.assertIn("submitOfficeLogin", res_js.text)
        self.assertIn("submitAdminIssueAccount", res_js.text)
        self.assertIn("submitOfficialReply", res_js.text)
        self.assertIn("openDevSupportModal", res_js.text)
        self.assertIn("submitFeedbackForm", res_js.text)
        self.assertIn("submitAdminDevSupport", res_js.text)
        self.assertNotIn("polirank_admin_2026", res_js.text)
        self.assertIn("loadMyCheers", res_js.text)
        self.assertIn("already_cheered", res_js.text)
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
        self.assertEqual(data["total_cheers"], 0)
        self.assertEqual(data["total_comments"], 0)
        self.assertEqual(data["party_counts"]["all"], data["total_members"])
        self.assertIn("last_updated_at", data)
        self.assertIn("update_schedule", data)
        print(f"[PASS] UI v3.2 Clean Zero State, /methodology & Stats API verified: {data['total_members']} members, cheers=0, comments=0.")

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
        """실시간 응원/댓글 및 fandom_score 민감도가 total_score에 영향을 주지 않는 완전 격리 검증"""
        res = self.client.get("/api/members")
        member = res.json()["members"][0]
        member_id = member["id"]
        old_cheer = member["cheer_count"]
        old_total = member["total_score"]
        self.assertEqual(old_cheer, 0)

        # v3.2: 0표 / 1표 / 5표 / 10표 증가에 따른 fandom_score 체감 상승 검증
        sample_m = {"news_30d_count": 10, "media_mentions": 500}
        f0 = calculate_fun_metrics(sample_m, total_score=old_total, cheer_count=0)["fandom_score"]
        f1 = calculate_fun_metrics(sample_m, total_score=old_total, cheer_count=1)["fandom_score"]
        f5 = calculate_fun_metrics(sample_m, total_score=old_total, cheer_count=5)["fandom_score"]
        f10 = calculate_fun_metrics(sample_m, total_score=old_total, cheer_count=10)["fandom_score"]
        self.assertLess(f0, f1)
        self.assertLess(f1, f5)
        self.assertLess(f5, f10)

        fun_low = calculate_fun_metrics({"news_30d_count": 2, "media_mentions": 100}, total_score=old_total, cheer_count=0)
        fun_high = calculate_fun_metrics({"news_30d_count": 90, "controversy_news_count": 40, "media_mentions": 8000}, total_score=old_total, cheer_count=100)
        self.assertGreater(fun_high["fandom_score"], fun_low["fandom_score"])
        self.assertGreater(fun_high["controversy_score"], fun_low["controversy_score"])

        res_cheer = self.client.post(
            f"/api/members/{member_id}/cheer",
            headers={"User-Agent": "IsolationTest/1.0", "X-Forwarded-For": "192.0.2.10"},
        )
        self.assertEqual(res_cheer.status_code, 200)
        new_cheer = res_cheer.json()["cheer_count"]
        self.assertEqual(new_cheer, 1)

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

        after_detail = self.client.get(f"/api/members/{member_id}").json()
        self.assertEqual(after_detail["total_score"], old_total)
        self.assertGreater(after_detail["fandom_score"], member["fandom_score"])
        print(
            f"[PASS] Cheer, Comment & total_score Isolation verified (Cheer: {old_cheer}->{new_cheer}, fandom: {f0}->{f1}->{f5}->{f10}, total_score={old_total} unchanged)"
        )

    def test_07_duplicate_cheer_three_layer_guard(self):
        """1인 1의원 1회 중복 응원 방지 (HttpOnly 쿠키 + IP/UA 해시 + /api/my-cheers) 검증"""
        members = self.client.get("/api/members").json()["members"]
        target = members[2]
        mid = target["id"]
        self.assertEqual(target["cheer_count"], 0)

        # 1) 방문자 A 첫 조회 및 응원 -> 0 -> 1 성공 + HttpOnly 쿠키 발급
        headers_a = {"User-Agent": "Chrome-Visitor-A/120.0", "X-Forwarded-For": "203.0.113.10"}
        client_a = TestClient(app)
        my_before = client_a.get("/api/my-cheers", headers=headers_a)
        self.assertEqual(my_before.status_code, 200)
        self.assertNotIn(mid, my_before.json()["cheered_member_ids"])
        self.assertIn("polirank_vid", client_a.cookies)

        res_ok = client_a.post(f"/api/members/{mid}/cheer", headers=headers_a)
        self.assertEqual(res_ok.status_code, 200)
        self.assertEqual(res_ok.json()["status"], "success")
        self.assertEqual(res_ok.json()["cheer_count"], 1)

        my_after = client_a.get("/api/my-cheers", headers=headers_a)
        self.assertIn(mid, my_after.json()["cheered_member_ids"])

        # 2) 동일 쿠키로 연타 시 409 차단 및 카운트 유지
        res_dup_cookie = client_a.post(f"/api/members/{mid}/cheer", headers=headers_a)
        self.assertEqual(res_dup_cookie.status_code, 409)
        self.assertEqual(res_dup_cookie.json()["status"], "already_cheered")
        self.assertEqual(res_dup_cookie.json()["cheer_count"], 1)

        # 3) 쿠키 삭제 / 시크릿창 (새 TestClient, 동일 IP + 동일 UA) -> ip_ua_hash로 409 차단
        client_a_incognito = TestClient(app)
        my_incog = client_a_incognito.get("/api/my-cheers", headers=headers_a)
        self.assertIn(mid, my_incog.json()["cheered_member_ids"])
        res_dup_ipua = client_a_incognito.post(f"/api/members/{mid}/cheer", headers=headers_a)
        self.assertEqual(res_dup_ipua.status_code, 409)
        self.assertEqual(res_dup_ipua.json()["status"], "already_cheered")
        self.assertEqual(res_dup_ipua.json()["cheer_count"], 1)

        # 4) 동일 쿠키 유지 상태에서 IP/UA 헤더 변경 시도 -> cookie_hash로 409 차단
        res_spoof = client_a.post(
            f"/api/members/{mid}/cheer",
            headers={"User-Agent": "SpoofedBrowser/9.9", "X-Forwarded-For": "198.51.100.88"},
        )
        self.assertEqual(res_spoof.status_code, 409)
        self.assertEqual(res_spoof.json()["cheer_count"], 1)

        # 5) 실제 다른 IP + 다른 브라우저 방문자 B -> 정상 1 -> 2 증가 허용
        headers_b = {"User-Agent": "Safari-Visitor-B/17.0", "X-Forwarded-For": "203.0.113.99"}
        client_b = TestClient(app)
        my_b = client_b.get("/api/my-cheers", headers=headers_b)
        self.assertNotIn(mid, my_b.json()["cheered_member_ids"])
        res_b = client_b.post(f"/api/members/{mid}/cheer", headers=headers_b)
        self.assertEqual(res_b.status_code, 200)
        self.assertEqual(res_b.json()["status"], "success")
        self.assertEqual(res_b.json()["cheer_count"], 2)

        client_a.close()
        client_a_incognito.close()
        client_b.close()
        print(f"[PASS] 3-Layer Duplicate Cheer Prevention verified for {target['name']}: 0->1, same cookie 409, cleared cookie 409, IP/UA spoof 409, visitor B 1->2.")

    def test_08_office_auth_b2b_issue_official_reply_and_notice(self):
        """v3.3 운영자 B2B 의원실 계정 발급 · 인증 배지 · 권한 격리(401/403) · 계층형 공식 대댓글 및 공지 검증"""
        members = self.client.get("/api/members").json()["members"]
        self.assertTrue(all(int(m.get("is_verified_office", 0)) == 0 for m in members))

        target = next((m for m in members if m["name"] == "서영교"), members[0])
        other = next((m for m in members if m["id"] != target["id"]), members[1])
        target_id = target["id"]
        other_id = other["id"]

        # 1) 비로그인 상태에서 /api/office/me & admin 엔드포인트 차단 확인
        me_anon = self.client.get("/api/office/me")
        self.assertEqual(me_anon.status_code, 200)
        self.assertFalse(me_anon.json()["authenticated"])

        unauth_issue = self.client.post(
            "/api/admin/issue-office-account",
            json={"member_id": target_id, "username": "unauth_try", "password": "pw1234", "verify_now": True},
        )
        self.assertEqual(unauth_issue.status_code, 401)

        # 2) 운영자 로그인 & 의원실 계정 발급
        admin_client = TestClient(app)
        admin_pw = os.environ.get("POLIRANK_ADMIN_PASSWORD") or "polirank_admin_2026!"
        bad_login = admin_client.post("/api/office/login", json={"username": "admin", "password": "wrong_password"})
        self.assertEqual(bad_login.status_code, 401)

        res_admin_login = admin_client.post("/api/office/login", json={"username": "admin", "password": admin_pw})
        self.assertEqual(res_admin_login.status_code, 200)
        self.assertEqual(res_admin_login.json()["role"], "admin")
        self.assertIn("polirank_office_session", admin_client.cookies)

        res_issue = admin_client.post(
            "/api/admin/issue-office-account",
            json={
                "member_id": target_id,
                "username": "office_seoyg_test",
                "password": "office_pass_2026!",
                "verify_now": True,
            },
        )
        self.assertEqual(res_issue.status_code, 200)
        issued = res_issue.json()["account"]
        self.assertEqual(issued["member_id"], target_id)
        self.assertEqual(issued["is_verified_office"], 1)

        # 해시 미노출 확인 + toggle-verify 테스트
        res_acc_list = admin_client.get("/api/admin/office-accounts")
        self.assertEqual(res_acc_list.status_code, 200)
        self.assertNotIn("password_hash", str(res_acc_list.json()))

        res_tog_off = admin_client.post("/api/admin/toggle-verify", json={"member_id": target_id})
        self.assertEqual(res_tog_off.status_code, 200)
        self.assertEqual(res_tog_off.json()["is_verified_office"], 0)
        res_tog_on = admin_client.post("/api/admin/toggle-verify", json={"member_id": target_id})
        self.assertEqual(res_tog_on.status_code, 200)
        self.assertEqual(res_tog_on.json()["is_verified_office"], 1)

        # 3) 발급된 의원실 계정으로 로그인 & 관리자 API 접근 차단(403)
        office_client = TestClient(app)
        res_off_login = office_client.post(
            "/api/office/login",
            json={"username": "office_seoyg_test", "password": "office_pass_2026!"},
        )
        self.assertEqual(res_off_login.status_code, 200)
        self.assertEqual(res_off_login.json()["role"], "office")
        self.assertEqual(res_off_login.json()["member_id"], target_id)

        self.assertEqual(
            office_client.post(
                "/api/admin/issue-office-account",
                json={"member_id": other_id, "username": "hack", "password": "pw1234", "verify_now": True},
            ).status_code,
            403,
        )

        # 4) 일반 시민 댓글 작성 후 타 의원 페이지 공식 답변 차단(403) + 본인 의원 공식 대댓글 작성(200)
        res_citizen = self.client.post(
            f"/api/members/{target_id}/comments",
            headers={"User-Agent": "CitizenOfficeFlow/1.0", "X-Forwarded-For": "198.51.100.11"},
            json={"author": "지역 유권자", "stance": "proposal", "content": "지역 교통 개선 법안 일정이 궁금합니다."},
        )
        self.assertEqual(res_citizen.status_code, 200)
        parent_id = res_citizen.json()["comment"]["id"]

        res_citizen_other = self.client.post(
            f"/api/members/{other_id}/comments",
            headers={"User-Agent": "CitizenOtherFlow/1.0", "X-Forwarded-For": "198.51.100.12"},
            json={"author": "시민B", "stance": "cheer", "content": "응원합니다."},
        )
        other_parent_id = res_citizen_other.json()["comment"]["id"]

        # 비로그인 공식 대댓글 -> 401
        res_unauth_reply = TestClient(app).post(
            f"/api/members/{target_id}/comments",
            json={"content": "무단 공식 답변", "parent_id": parent_id, "is_official_reply": True},
        )
        self.assertEqual(res_unauth_reply.status_code, 401)

        # 타 의원 페이지에 공식 대댓글 시도 -> 403
        res_cross_reply = office_client.post(
            f"/api/members/{other_id}/comments",
            json={"content": "타 의원 답변 시도", "parent_id": other_parent_id, "is_official_reply": True},
        )
        self.assertEqual(res_cross_reply.status_code, 403)

        # 본인 의원 페이지 공식 대댓글 작성 -> 200 & 계층형 replies 반환 확인
        res_ok_reply = office_client.post(
            f"/api/members/{target_id}/comments",
            json={"content": "안녕하세요, 의원실입니다. 다음 주 상임위 소위에서 상정 논의 예정입니다.", "parent_id": parent_id, "is_official_reply": True},
        )
        self.assertEqual(res_ok_reply.status_code, 200)
        self.assertEqual(res_ok_reply.json()["comment"]["is_official_reply"], 1)

        res_tree = self.client.get(f"/api/members/{target_id}/comments").json()
        matched_parent = next((c for c in res_tree["comments"] if c["id"] == parent_id), None)
        self.assertIsNotNone(matched_parent)
        self.assertEqual(len(matched_parent["replies"]), 1)
        self.assertEqual(matched_parent["replies"][0]["is_official_reply"], 1)
        self.assertIn("의원실 공식", matched_parent["replies"][0]["official_badge_name"])

        # 5) 공식 의정 브리핑 등록 및 타 의원 수정 차단(403)
        res_cross_notice = office_client.post("/api/office/notice", json={"notice": "무단 수정", "member_id": other_id})
        self.assertEqual(res_cross_notice.status_code, 403)

        res_notice = office_client.post(
            "/api/office/notice",
            json={"notice": "제22대 국회 민생 입법 현황을 투명하게 공유드리겠습니다.", "member_id": target_id},
        )
        self.assertEqual(res_notice.status_code, 200)
        detail = self.client.get(f"/api/members/{target_id}").json()
        self.assertEqual(detail["is_verified_office"], 1)
        self.assertIn("민생 입법 현황", detail["office_notice"])

        admin_client.close()
        office_client.close()
        print(f"[PASS] v3.3 B2B Office Auth, Verification Badge, Cross-MP 403 Guard, Hierarchical Reply & Notice verified for {target['name']}.")

    def test_09_citizen_anonymous_comments_profanity_and_rate_limit(self):
        """무기명 시민 댓글 정상 등록, 유해어 차단(400) 및 15초 연속 도배 방지(429) 검증"""
        members = self.client.get("/api/members").json()["members"]
        target_id = members[3]["id"]
        headers_spam = {"User-Agent": "CitizenSpamTester/1.0", "X-Forwarded-For": "198.51.100.77"}

        res_first = self.client.post(
            f"/api/members/{target_id}/comments",
            headers=headers_spam,
            json={"author": "", "stance": "cheer", "content": "지역구 민생 법안 꼼꼼히 챙겨주세요!"},
        )
        self.assertEqual(res_first.status_code, 200)
        self.assertEqual(res_first.json()["comment"]["is_official_reply"], 0)
        self.assertEqual(res_first.json()["comment"]["author"], "익명 유권자")

        # 15초 이내 동일 IP+UA 연속 도배 -> 429 차단
        res_rapid = self.client.post(
            f"/api/members/{target_id}/comments",
            headers=headers_spam,
            json={"author": "도배러", "stance": "critique", "content": "연속 도배 테스트"},
        )
        self.assertEqual(res_rapid.status_code, 429)
        self.assertEqual(res_rapid.json()["status"], "rate_limited")

        # 심한 비속어 필터 -> 400 차단
        res_profane = self.client.post(
            f"/api/members/{target_id}/comments",
            headers={"User-Agent": "ProfanityTest/1.0", "X-Forwarded-For": "198.51.100.78"},
            json={"author": "시민", "stance": "critique", "content": "이런 씨발 같은 테스트"},
        )
        self.assertEqual(res_profane.status_code, 400)
        print("[PASS] Citizen Anonymous Comment, 15s Rate-Limit (429) & Profanity Filter (400) verified.")

    def test_10_unique_299_quotes_zero_duplicates(self):
        """v3.4 299명 전원 100% 고유 한마디(중복 제로) 및 문법 무결성 검증"""
        res = self.client.get("/api/members")
        self.assertEqual(res.status_code, 200)
        members = res.json()["members"]
        self.assertEqual(len(members), 299)
        quotes = [m.get("quote", "").strip() for m in members]
        self.assertTrue(all(len(q) >= 10 for q in quotes))
        self.assertEqual(len(set(quotes)), len(members), f"Duplicate quotes found: {len(quotes)} vs {len(set(quotes))}")
        self.assertFalse(any("에법" in q for q in quotes))
        print(f"[PASS] 299/299 Unique Quotes verified (100% unique, 0 duplicates).")

    def test_11_dev_support_and_user_feedback_workflow(self):
        """v3.4 개발자 후원 설정/조회, 유저 의견 보내기(400/429 포함) 및 관리자 전용 열람(401/403 차단) 검증"""
        # 1) 초기 dev-support 조회 (미설정 상태)
        res_dev0 = self.client.get("/api/dev-support")
        self.assertEqual(res_dev0.status_code, 200)
        self.assertFalse(res_dev0.json()["is_configured"])
        self.assertTrue(len(res_dev0.json()["dev_message"]) > 10)

        # 2) 비관리자 접근 차단 (401 / 403)
        self.assertEqual(self.client.get("/api/admin/feedbacks").status_code, 401)
        self.assertEqual(
            self.client.post("/api/admin/dev-support", json={"dev_bank_info": "hack"}).status_code,
            401,
        )
        office_client = TestClient(app)
        office_login = office_client.post(
            "/api/office/login",
            json={"username": "office_seoyg_test", "password": "office_pass_2026!"},
        )
        self.assertEqual(office_login.status_code, 200)
        self.assertEqual(office_client.get("/api/admin/feedbacks").status_code, 403)
        self.assertEqual(
            office_client.post("/api/admin/dev-support", json={"dev_bank_info": "hack"}).status_code,
            403,
        )
        office_client.close()

        # 3) 일반 유저 의견 접수 + 빈 내용(400) + 15초 도배 방지(429)
        fb_headers = {"User-Agent": "FeedbackClient/1.0", "X-Forwarded-For": "198.51.100.91"}
        res_empty = self.client.post(
            "/api/feedback",
            headers=fb_headers,
            json={"category": "제안", "content": "   "},
        )
        self.assertEqual(res_empty.status_code, 400)

        res_fb = self.client.post(
            "/api/feedback",
            headers=fb_headers,
            json={
                "category": "의원실·제휴문의",
                "author": "보좌관 K",
                "contact": "office@assembly.example",
                "content": "서영교 의원실 공식 계정 연동 시연 요청드립니다.",
            },
        )
        self.assertEqual(res_fb.status_code, 200)
        fb_id = res_fb.json()["feedback"]["id"]

        res_fb_spam = self.client.post(
            "/api/feedback",
            headers=fb_headers,
            json={"category": "기타", "content": "연속 도배 테스트"},
        )
        self.assertEqual(res_fb_spam.status_code, 429)

        # 4) 관리자 로그인 -> 의견 열람 & 확인완료 처리 + 개발자 후원 정보 실시간 업데이트
        admin_client = TestClient(app)
        admin_pw = os.environ.get("POLIRANK_ADMIN_PASSWORD") or "polirank_admin_2026!"
        self.assertEqual(
            admin_client.post("/api/office/login", json={"username": "admin", "password": admin_pw}).status_code,
            200,
        )

        res_list = admin_client.get("/api/admin/feedbacks")
        self.assertEqual(res_list.status_code, 200)
        self.assertGreaterEqual(res_list.json()["count"], 1)
        self.assertEqual(res_list.json()["feedbacks"][0]["id"], fb_id)

        res_chk = admin_client.post(f"/api/admin/feedbacks/{fb_id}/check")
        self.assertEqual(res_chk.status_code, 200)
        self.assertEqual(res_chk.json()["status"], "checked")

        # XSS javascript: URI 차단 확인
        res_bad_url = admin_client.post(
            "/api/admin/dev-support",
            json={"dev_bank_info": "카카오뱅크 3333", "dev_toss_link": "javascript:alert(1)"},
        )
        self.assertEqual(res_bad_url.status_code, 400)

        res_save_dev = admin_client.post(
            "/api/admin/dev-support",
            json={
                "dev_bank_info": "카카오뱅크 3333-01-9999999 (현진호)",
                "dev_toss_link": "https://toss.me/jinhopolirank",
                "dev_kakaopay_link": "https://qr.kakaopay.com/polirankdev",
                "dev_message": "응원 감사합니다! 더 정확한 입법 데이터로 보답하겠습니다.",
            },
        )
        self.assertEqual(res_save_dev.status_code, 200)
        self.assertTrue(res_save_dev.json()["is_configured"])

        res_dev1 = self.client.get("/api/dev-support").json()
        self.assertEqual(res_dev1["dev_bank_info"], "카카오뱅크 3333-01-9999999 (현진호)")
        self.assertEqual(res_dev1["dev_toss_link"], "https://toss.me/jinhopolirank")
        admin_client.close()
        print("[PASS] v3.4 Dev Support live config, XSS guard & Admin Feedback Inbox (401/403/429) verified.")

    def test_12_preserve_real_user_data_on_weekly_seed(self):
        """주간 자동 업데이트(seed preserve_user_data=True) 시 실제 유저 응원/댓글/의원실/후원/의견 100% 보존 검증"""
        conn = get_connection()
        before_cheers = conn.execute("SELECT COALESCE(SUM(cheer_count), 0) FROM members").fetchone()[0]
        before_comments = conn.execute("SELECT COUNT(*) FROM comments").fetchone()[0]
        before_logs = conn.execute("SELECT COUNT(*) FROM cheer_logs").fetchone()[0]
        before_verified = conn.execute("SELECT COUNT(*) FROM members WHERE is_verified_office = 1").fetchone()[0]
        before_accounts = conn.execute("SELECT COUNT(*) FROM office_accounts").fetchone()[0]
        before_feedbacks = conn.execute("SELECT COUNT(*) FROM feedbacks").fetchone()[0]
        conn.close()

        self.assertGreater(before_cheers, 0)
        self.assertGreater(before_comments, 0)
        self.assertGreater(before_logs, 0)
        self.assertGreater(before_verified, 0)
        self.assertGreaterEqual(before_accounts, 2)
        self.assertGreaterEqual(before_feedbacks, 1)

        seed(preserve_user_data=True)

        conn = get_connection()
        after_cheers = conn.execute("SELECT COALESCE(SUM(cheer_count), 0) FROM members").fetchone()[0]
        after_comments = conn.execute("SELECT COUNT(*) FROM comments").fetchone()[0]
        after_logs = conn.execute("SELECT COUNT(*) FROM cheer_logs").fetchone()[0]
        after_verified = conn.execute("SELECT COUNT(*) FROM members WHERE is_verified_office = 1").fetchone()[0]
        after_accounts = conn.execute("SELECT COUNT(*) FROM office_accounts").fetchone()[0]
        after_feedbacks = conn.execute("SELECT COUNT(*) FROM feedbacks").fetchone()[0]
        conn.close()

        self.assertEqual(after_cheers, before_cheers)
        self.assertEqual(after_comments, before_comments)
        self.assertEqual(after_logs, before_logs)
        self.assertEqual(after_verified, before_verified)
        self.assertEqual(after_accounts, before_accounts)
        self.assertEqual(after_feedbacks, before_feedbacks)
        dev_after = self.client.get("/api/dev-support").json()
        self.assertEqual(dev_after["dev_bank_info"], "카카오뱅크 3333-01-9999999 (현진호)")
        print(f"[PASS] Weekly seed(preserve_user_data=True) lossless preservation verified: cheers={after_cheers}, comments={after_comments}, logs={after_logs}, verified={after_verified}, accounts={after_accounts}, feedbacks={after_feedbacks}")


if __name__ == "__main__":
    unittest.main()
