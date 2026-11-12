"""
PoliRank - 국회의원 객관적 랭킹 & 커뮤니티 MVP 플랫폼 백엔드 (FastAPI) - 6대 정량 지표 & 재미요소 확장
"""
import base64
import hashlib
import hmac
import json
import os
import sys
import time
import uuid
from typing import Optional
from fastapi import FastAPI, HTTPException, Query, Request, Response
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse, HTMLResponse, JSONResponse
from pydantic import BaseModel

CURRENT_DIR = os.path.dirname(os.path.abspath(__file__))
if CURRENT_DIR not in sys.path:
    sys.path.insert(0, CURRENT_DIR)

import polirank_mvp.database as polirank_db

init_db = polirank_db.init_db
get_all_members = polirank_db.get_all_members
get_member_by_id = polirank_db.get_member_by_id
record_cheer_with_guard = polirank_db.record_cheer_with_guard
get_cheered_member_ids = polirank_db.get_cheered_member_ids
get_comments = polirank_db.get_comments
add_comment = polirank_db.add_comment
get_summary_stats = polirank_db.get_summary_stats
authenticate_office_account = polirank_db.authenticate_office_account
get_office_account_by_username = polirank_db.get_office_account_by_username
issue_office_account = polirank_db.issue_office_account
toggle_member_verification = polirank_db.toggle_member_verification
update_office_notice = polirank_db.update_office_notice
list_office_accounts = polirank_db.list_office_accounts
get_dev_support_settings = polirank_db.get_dev_support_settings
update_dev_support_settings = polirank_db.update_dev_support_settings
add_feedback = polirank_db.add_feedback
list_feedbacks = polirank_db.list_feedbacks
mark_feedback_status = polirank_db.mark_feedback_status

import polirank_mvp.scoring as polirank_scoring
import polirank_mvp.avatar_generator as polirank_avatar

SCORING_METHODOLOGY = polirank_scoring.SCORING_METHODOLOGY
generate_caricature_svg = polirank_avatar.generate_caricature_svg

from polirank_core_config import POLIRANK_CONFIG, PolirankScoringEngine
from rank_core import create_ranking_app, BaseDatabaseManager

# Rank Core 서브 앱 마운트 준비
core_engine = PolirankScoringEngine(POLIRANK_CONFIG.weights)
core_db_path = os.path.join(CURRENT_DIR, POLIRANK_CONFIG.db_filename)
core_db = BaseDatabaseManager(core_db_path)
core_app = create_ranking_app(POLIRANK_CONFIG, core_db, core_engine)

app = FastAPI(
    title="PoliRank API",
    description="제22대 국회의원 299인 6대 핵심 축 · 14대 실제 공공 팩트 + 공식 의원실 소통 & 후원/의견 API (rank_core 기반)",
    version="3.4.0"
)

# Core API Mount
app.mount("/core", core_app)

VID_COOKIE_NAME = "polirank_vid"
VID_COOKIE_MAX_AGE = 60 * 60 * 24 * 365
OFFICE_COOKIE_NAME = "polirank_office_session"
OFFICE_SESSION_TTL = 60 * 60 * 24 * 7
COMMENT_COOLDOWN_SEC = 15.0
COMMENT_RATE_LIMITS: dict[str, float] = {}
FEEDBACK_RATE_LIMITS: dict[str, float] = {}
BLOCKED_PROFANITY_WORDS = (
    "씨발", "시발", "병신", "개새끼", "미친놈", "미친년", "존나", "씹새", "애미", "죽어라"
)


def _sha256(value: str) -> str:
    return hashlib.sha256(value.encode("utf-8")).hexdigest()


def _get_client_ip(request: Request) -> str:
    forwarded_for = request.headers.get("x-forwarded-for")
    if forwarded_for:
        first_ip = forwarded_for.split(",")[0].strip()
        if first_ip:
            return first_ip
    real_ip = request.headers.get("x-real-ip")
    if real_ip:
        return real_ip.strip()
    if request.client and request.client.host:
        return request.client.host
    return "unknown"


def _compute_ip_ua_hash(request: Request) -> str:
    ip = _get_client_ip(request)
    ua = (request.headers.get("user-agent") or "unknown").strip()
    return _sha256(f"{ip}|{ua}")


def _resolve_visitor_cookie(request: Request) -> tuple[str, str, bool]:
    vid = (request.cookies.get(VID_COOKIE_NAME) or "").strip()
    if len(vid) < 12:
        vid = str(uuid.uuid4())
        return vid, _sha256(vid), True
    return vid, _sha256(vid), False


def _set_vid_cookie(resp: Response, vid: str, request: Request) -> None:
    is_https = (
        request.headers.get("x-forwarded-proto", "").lower() == "https"
        or request.url.scheme == "https"
    )
    resp.set_cookie(
        key=VID_COOKIE_NAME,
        value=vid,
        max_age=VID_COOKIE_MAX_AGE,
        httponly=True,
        samesite="lax",
        secure=is_https,
        path="/",
    )


def _get_signing_secret() -> str:
    env_secret = os.environ.get("POLIRANK_SECRET_KEY")
    if env_secret:
        return env_secret
    seed_pw = os.environ.get("POLIRANK_ADMIN_PASSWORD") or "polirank_admin_2026!"
    return hashlib.sha256(f"{seed_pw}|polirank-v33-session-secret".encode("utf-8")).hexdigest()


def _create_office_session_token(account: dict) -> str:
    payload = {
        "u": account["username"],
        "r": account["role"],
        "m": account.get("member_id"),
        "o": account.get("office_name"),
        "exp": int(time.time()) + OFFICE_SESSION_TTL,
    }
    raw_json = json.dumps(payload, ensure_ascii=False, separators=(",", ":")).encode("utf-8")
    payload_b64 = base64.urlsafe_b64encode(raw_json).decode("ascii")
    sig = hmac.new(_get_signing_secret().encode("utf-8"), payload_b64.encode("ascii"), hashlib.sha256).hexdigest()
    return f"{payload_b64}.{sig}"


def _decode_office_session(request: Request) -> Optional[dict]:
    token = (request.cookies.get(OFFICE_COOKIE_NAME) or "").strip()
    if not token or "." not in token:
        return None
    try:
        payload_b64, sig = token.rsplit(".", 1)
        expected_sig = hmac.new(
            _get_signing_secret().encode("utf-8"),
            payload_b64.encode("ascii"),
            hashlib.sha256,
        ).hexdigest()
        if not hmac.compare_digest(expected_sig, sig):
            return None
        payload = json.loads(base64.urlsafe_b64decode(payload_b64.encode("ascii")).decode("utf-8"))
        if int(payload.get("exp", 0)) < int(time.time()):
            return None
        account = get_office_account_by_username(payload.get("u", ""))
        if not account:
            return None
        return account
    except Exception:
        return None


def _set_office_cookie(resp: Response, token: str, request: Request) -> None:
    is_https = (
        request.headers.get("x-forwarded-proto", "").lower() == "https"
        or request.url.scheme == "https"
    )
    resp.set_cookie(
        key=OFFICE_COOKIE_NAME,
        value=token,
        max_age=OFFICE_SESSION_TTL,
        httponly=True,
        samesite="lax",
        secure=is_https,
        path="/",
    )


# CORS 설정
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# 정적 파일 디렉토리
STATIC_DIR = os.path.join(CURRENT_DIR, "static")
if not os.path.exists(STATIC_DIR):
    os.makedirs(STATIC_DIR, exist_ok=True)

app.mount("/static", StaticFiles(directory=STATIC_DIR), name="static")

class CommentCreate(BaseModel):
    author: Optional[str] = "익명 유권자"
    stance: Optional[str] = "cheer"  # cheer, critique, proposal
    content: str
    parent_id: Optional[int] = None
    is_official_reply: Optional[bool] = False


class OfficeLoginRequest(BaseModel):
    username: str
    password: str


class OfficeNoticeRequest(BaseModel):
    notice: str
    member_id: Optional[str] = None


class AdminIssueAccountRequest(BaseModel):
    member_id: str
    username: str
    password: str
    verify_now: bool = True
    office_name: Optional[str] = None


class AdminToggleVerifyRequest(BaseModel):
    member_id: str
    verified: Optional[bool] = None


class DevSupportUpdateRequest(BaseModel):
    dev_bank_info: str = ""
    dev_toss_link: str = ""
    dev_kakaopay_link: str = ""
    dev_message: str = ""


class FeedbackCreateRequest(BaseModel):
    category: str = "제안"
    author: Optional[str] = "익명 사용자"
    contact: Optional[str] = ""
    content: str


def _require_admin(request: Request) -> dict:
    session = _decode_office_session(request)
    if not session:
        raise HTTPException(status_code=401, detail="운영자 로그인이 필요합니다.")
    if session.get("role") != "admin":
        raise HTTPException(status_code=403, detail="운영자 권한이 필요합니다.")
    return session


def _check_rate_limit(bucket: dict[str, float], key: str, cooldown_sec: float = COMMENT_COOLDOWN_SEC) -> Optional[int]:
    now = time.time()
    last_ts = bucket.get(key)
    if last_ts is not None and (now - last_ts) < cooldown_sec:
        return int(cooldown_sec - (now - last_ts)) + 1
    bucket[key] = now
    if len(bucket) > 2000:
        cutoff = now - 60.0
        for k in [k for k, ts in bucket.items() if ts < cutoff]:
            bucket.pop(k, None)
    return None

import polirank_mvp.seed_data as polirank_seed
seed = polirank_seed.seed
get_connection = polirank_db.get_connection

@app.on_event("startup")
def startup_event():
    init_db()
    conn = get_connection()
    c = conn.cursor()
    try:
        c.execute("SELECT COUNT(*) as cnt FROM members")
        cnt = c.fetchone()["cnt"]
        c.execute("SELECT COUNT(*) as v31_cnt FROM members WHERE fandom_score > 0 OR hidden_gem_score > 0")
        v31_cnt = c.fetchone()["v31_cnt"]
        has_all_seed = os.path.exists(os.path.join(CURRENT_DIR, "seed_data_all.json"))
        if cnt == 0 or (has_all_seed and (cnt < 200 or v31_cnt == 0)):
            print(f"[*] Database requires v3.1 seeding (total={cnt}, v31={v31_cnt}). Seeding 299-member data...")
            seed()
    except Exception as e:
        print("[!] Startup check failed, running seed:", e)
        seed()
    finally:
        conn.close()

@app.get("/", response_class=HTMLResponse)
def read_root():
    """메인 페이지 HTML 서빙"""
    index_path = os.path.join(STATIC_DIR, "index.html")
    if os.path.exists(index_path):
        return FileResponse(index_path)
    return HTMLResponse("<h1>PoliRank API Server is Running</h1><p>index.html not found yet.</p>")

@app.get("/methodology", response_class=HTMLResponse)
def read_methodology():
    """점수 산출 방식 및 가중치 설명 전용 페이지 서빙"""
    meth_path = os.path.join(STATIC_DIR, "methodology.html")
    if os.path.exists(meth_path):
        return FileResponse(meth_path)
    return HTMLResponse("<h1>Methodology Page Not Found</h1>", status_code=404)

@app.get("/api/stats/summary")
def get_stats():
    """상단 헤더 라이브 통계 지표"""
    return get_summary_stats()

@app.get("/api/scoring/methodology")
def get_methodology():
    """v3.1 6대 핵심 축 및 가중치 설계 원칙"""
    return SCORING_METHODOLOGY

@app.get("/api/members")
def list_members(
    party: Optional[str] = Query(None, description="정당 필터 (all, 더불어민주당, 국민의힘 등)"),
    sort_by: str = Query("total", description="정렬 기준 (total, passed, voting, legislation, bipartisan, committee, policy, cheer, fandom, controversy, hidden_gem)"),
    search: Optional[str] = Query(None, description="이름, 지역구, 상임위, 어록 검색")
):
    """국회의원 랭킹 목록 조회 (v3.1 6대 핵심 축 & 재미·화제성 랭킹)"""
    members = get_all_members(party=party, sort_by=sort_by, search=search)
    for m in members:
        m["avatar_url"] = f"/api/members/{m['id']}/avatar.svg"
    return {
        "status": "success",
        "count": len(members),
        "sort_by": sort_by,
        "party_filter": party or "all",
        "members": members
    }

@app.get("/api/members/{member_id}")
def get_member(member_id: str):
    """국회의원 상세 정보, 6각 레이더 차트 및 14대 세부 팩트 시트 조회"""
    member = get_member_by_id(member_id)
    if not member:
        raise HTTPException(status_code=404, detail="Member not found")
        
    member["avatar_url"] = f"/api/members/{member['id']}/avatar.svg"
    
    # v3.0 6대 핵심 축 6각 레이더 차트 데이터 (메이저 -> 마이너 순)
    member["radar_chart"] = {
        "labels": [
            "입법품질(30%)",
            "본회의표결(20%)",
            "입법발의(15%)",
            "초당적협치(15%)",
            "위원회직무(12%)",
            "정책소통(8%)",
        ],
        "datasets": [{
            "label": f"{member['name']} 의원 6대 핵심 축",
            "data": [
                member["passed_score"],
                member["voting_score"],
                member["legislation_score"],
                member.get("bipartisan_score", 0.0),
                member.get("committee_score", member["attendance_score"]),
                member["policy_score"]
            ],
            "backgroundColor": f"{member['party_color']}33",
            "borderColor": member["party_color"],
            "pointBackgroundColor": member["party_color"]
        }]
    }
    return member

@app.get("/api/members/{member_id}/avatar.svg")
def get_member_avatar(member_id: str, size: int = 140):
    """의원의 고품질 만화풍/캐리커쳐 SVG 아바타 반환"""
    member = get_member_by_id(member_id)
    if not member:
        name = "의원"
        party = "무소속"
        color = "#4A5568"
        gender = None
        age = None
        committee_role = None
    else:
        name = member["name"]
        party = member["party"]
        color = member["party_color"]
        gender = member.get("gender")
        age = member.get("age")
        committee_role = member.get("committee_role")

    svg_code = generate_caricature_svg(
        name=name,
        party=party,
        party_color=color,
        size=size,
        gender=gender,
        age=age,
        committee_role=committee_role,
    )
    return Response(content=svg_code, media_type="image/svg+xml")

@app.get("/api/my-cheers")
def read_my_cheers(request: Request, response: Response):
    """현재 방문자(HttpOnly 쿠키 + IP/UA 해시)가 이미 응원한 의원 ID 목록 반환"""
    vid, cookie_hash, is_new = _resolve_visitor_cookie(request)
    ip_ua_hash = _compute_ip_ua_hash(request)
    cheered_ids = get_cheered_member_ids(
        cookie_hash=None if is_new else cookie_hash,
        ip_ua_hash=ip_ua_hash,
    )
    if is_new:
        _set_vid_cookie(response, vid, request)
    return {
        "status": "success",
        "cheered_member_ids": cheered_ids,
        "count": len(cheered_ids),
    }


@app.post("/api/members/{member_id}/cheer")
def cheer(member_id: str, request: Request):
    """실시간 1인 1의원 1회 중복방지 응원 카운터 증가"""
    member = get_member_by_id(member_id)
    if not member:
        raise HTTPException(status_code=404, detail="Member not found")

    vid, cookie_hash, is_new = _resolve_visitor_cookie(request)
    ip_ua_hash = _compute_ip_ua_hash(request)

    result = record_cheer_with_guard(
        member_id=member_id,
        cookie_hash=cookie_hash,
        ip_ua_hash=ip_ua_hash,
    )

    if not result.get("allowed"):
        resp = JSONResponse(
            status_code=409,
            content={
                "status": "already_cheered",
                "message": "이미 응원하신 의원입니다. (1인 1의원 1회 제한)",
                "member_id": member_id,
                "name": member["name"],
                "cheer_count": result["cheer_count"],
            },
        )
        if is_new:
            _set_vid_cookie(resp, vid, request)
        return resp

    resp = JSONResponse(
        status_code=200,
        content={
            "status": "success",
            "member_id": member_id,
            "name": member["name"],
            "cheer_count": result["cheer_count"],
            "fandom_score": result.get("fandom_score"),
        },
    )
    if is_new:
        _set_vid_cookie(resp, vid, request)
    return resp

@app.post("/api/office/login")
def office_login(payload: OfficeLoginRequest, request: Request):
    """공식 의원실 및 운영자 로그인 (HttpOnly HMAC 서명 세션 발급)"""
    account = authenticate_office_account(payload.username, payload.password)
    if not account:
        raise HTTPException(status_code=401, detail="아이디 또는 비밀번호가 올바르지 않습니다.")
    token = _create_office_session_token(account)
    resp = JSONResponse(
        status_code=200,
        content={
            "status": "success",
            "authenticated": True,
            "username": account["username"],
            "role": account["role"],
            "member_id": account.get("member_id"),
            "office_name": account["office_name"],
        },
    )
    _set_office_cookie(resp, token, request)
    return resp


@app.post("/api/office/logout")
def office_logout():
    """의원실 / 운영자 로그아웃 (세션 쿠키 삭제)"""
    resp = JSONResponse(status_code=200, content={"status": "success", "authenticated": False})
    resp.delete_cookie(key=OFFICE_COOKIE_NAME, path="/")
    return resp


@app.get("/api/office/me")
def office_me(request: Request):
    """현재 로그인된 의원실 / 운영자 세션 상태 조회"""
    session = _decode_office_session(request)
    if not session:
        return {
            "authenticated": False,
            "username": None,
            "role": None,
            "member_id": None,
            "office_name": None,
        }
    return {
        "authenticated": True,
        "username": session["username"],
        "role": session["role"],
        "member_id": session.get("member_id"),
        "office_name": session["office_name"],
    }


@app.post("/api/office/notice")
def save_office_notice(payload: OfficeNoticeRequest, request: Request):
    """로그인한 의원실 계정의 본인 의원 공식 의정 브리핑/소명 공지 저장"""
    session = _decode_office_session(request)
    if not session:
        raise HTTPException(status_code=401, detail="의원실 공식 계정 로그인이 필요합니다.")
    if session.get("role") != "office" or not session.get("member_id"):
        raise HTTPException(status_code=403, detail="의원실 계정으로만 의정 브리핑을 등록할 수 있습니다.")
    if payload.member_id and payload.member_id != session["member_id"]:
        raise HTTPException(status_code=403, detail="본인 의원실 페이지의 의정 브리핑만 수정할 수 있습니다.")

    notice_text = (payload.notice or "").strip()
    if len(notice_text) > 1000:
        raise HTTPException(status_code=400, detail="의정 브리핑은 1000자 이내로 작성해주세요.")

    updated = update_office_notice(session["member_id"], notice_text)
    if not updated:
        raise HTTPException(status_code=404, detail="Member not found")
    return {"status": "success", **updated}


@app.post("/api/admin/issue-office-account")
def admin_issue_account(payload: AdminIssueAccountRequest, request: Request):
    """운영자 전용(role=admin): 299명 중 원하는 의원실 계정 발급/초기화 및 즉시 공식인증"""
    session = _decode_office_session(request)
    if not session:
        raise HTTPException(status_code=401, detail="운영자 로그인이 필요합니다.")
    if session.get("role") != "admin":
        raise HTTPException(status_code=403, detail="운영자 권한이 필요합니다.")

    try:
        account = issue_office_account(
            member_id=payload.member_id,
            username=payload.username,
            password=payload.password,
            verify_now=payload.verify_now,
            office_name=payload.office_name,
        )
        return {"status": "success", "account": account}
    except LookupError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@app.post("/api/admin/toggle-verify")
def admin_toggle_verify(payload: AdminToggleVerifyRequest, request: Request):
    """운영자 전용(role=admin): 특정 의원 공식 인증 배지(0/1) 토글"""
    session = _decode_office_session(request)
    if not session:
        raise HTTPException(status_code=401, detail="운영자 로그인이 필요합니다.")
    if session.get("role") != "admin":
        raise HTTPException(status_code=403, detail="운영자 권한이 필요합니다.")

    res = toggle_member_verification(payload.member_id, verified=payload.verified)
    if not res:
        raise HTTPException(status_code=404, detail="Member not found")
    return {"status": "success", **res}


@app.get("/api/admin/office-accounts")
def admin_list_accounts(request: Request):
    """운영자 전용(role=admin): 발급된 의원실 계정 목록 조회"""
    _require_admin(request)
    return {"status": "success", "accounts": list_office_accounts()}


@app.get("/api/dev-support")
def read_dev_support():
    """개발자 후원 계좌/송금링크/메시지 조회"""
    return {"status": "success", **get_dev_support_settings()}


@app.post("/api/admin/dev-support")
def admin_update_dev_support(payload: DevSupportUpdateRequest, request: Request):
    """운영자 전용(role=admin): 개발자 후원 계좌/송금링크 실시간 수정 저장"""
    _require_admin(request)
    for field_name, link in [("토스 송금 링크", payload.dev_toss_link), ("카카오페이 송금 링크", payload.dev_kakaopay_link)]:
        clean_link = (link or "").strip()
        if clean_link and not (clean_link.startswith("https://") or clean_link.startswith("http://")):
            raise HTTPException(status_code=400, detail=f"{field_name}는 http:// 또는 https://로 시작하는 유효한 URL이어야 합니다.")

    updated = update_dev_support_settings(
        dev_bank_info=payload.dev_bank_info,
        dev_toss_link=payload.dev_toss_link,
        dev_kakaopay_link=payload.dev_kakaopay_link,
        dev_message=payload.dev_message,
    )
    return {"status": "success", **updated}


@app.post("/api/feedback")
def submit_user_feedback(payload: FeedbackCreateRequest, request: Request):
    """유저 의견 제안 / 데이터 오류 제보 / 의원실 제휴 문의 접수 (15초 도배 방지)"""
    clean_content = (payload.content or "").strip()
    if not clean_content:
        raise HTTPException(status_code=400, detail="의견 내용을 입력해주세요.")
    if len(clean_content) > 1500:
        raise HTTPException(status_code=400, detail="의견 내용은 1500자 이내로 작성해주세요.")

    allowed_categories = {"제안", "오류제보", "의원실·제휴문의", "기타"}
    category = (payload.category or "제안").strip()
    if category not in allowed_categories:
        category = "기타"

    ip_ua_hash = _compute_ip_ua_hash(request)
    retry_after = _check_rate_limit(FEEDBACK_RATE_LIMITS, ip_ua_hash, COMMENT_COOLDOWN_SEC)
    if retry_after is not None:
        return JSONResponse(
            status_code=429,
            content={
                "status": "rate_limited",
                "detail": f"도배 방지를 위해 {retry_after}초 후 다시 전송해주세요.",
                "message": f"도배 방지를 위해 {retry_after}초 후 다시 전송해주세요.",
                "retry_after": retry_after,
            },
        )

    saved = add_feedback(
        category=category,
        author=(payload.author or "").strip() or "익명 사용자",
        contact=(payload.contact or "").strip()[:120],
        content=clean_content,
        ip_ua_hash=ip_ua_hash,
    )
    return {
        "status": "success",
        "message": "소중한 의견이 개발자에게 전달되었습니다! 감사합니다.",
        "feedback": saved,
    }


@app.get("/api/admin/feedbacks")
def admin_read_feedbacks(request: Request, limit: int = 100):
    """운영자 전용(role=admin): 접수된 유저 의견 및 제휴 문의 목록 조회"""
    _require_admin(request)
    rows = list_feedbacks(limit=limit)
    return {"status": "success", "count": len(rows), "feedbacks": rows}


@app.post("/api/admin/feedbacks/{feedback_id}/check")
def admin_check_feedback(feedback_id: int, request: Request):
    """운영자 전용(role=admin): 유저 의견 확인 완료 처리"""
    _require_admin(request)
    res = mark_feedback_status(feedback_id, status="checked")
    if not res:
        raise HTTPException(status_code=404, detail="Feedback not found")
    return {"status": "success", **res}


@app.get("/api/members/{member_id}/comments")
def read_comments(member_id: str, limit: int = 50):
    """의원 상세 토론 댓글 및 공식 대댓글 계층 피드 조회"""
    comments = get_comments(member_id, limit=limit)
    total_count = sum(1 + len(c.get("replies", [])) for c in comments)
    return {
        "status": "success",
        "member_id": member_id,
        "count": total_count,
        "top_level_count": len(comments),
        "comments": comments
    }


@app.post("/api/members/{member_id}/comments")
def create_comment(member_id: str, payload: CommentCreate, request: Request):
    """의원 토론 시민 댓글(무기명 허용 + 도배 방지) 또는 공식 의원실 대댓글 작성"""
    member = get_member_by_id(member_id)
    if not member:
        raise HTTPException(status_code=404, detail="Member not found")

    clean_content = (payload.content or "").strip()
    if not clean_content:
        raise HTTPException(status_code=400, detail="댓글 내용을 입력해주세요.")
    if len(clean_content) > 600:
        raise HTTPException(status_code=400, detail="댓글은 600자 이내로 작성해주세요.")

    if payload.is_official_reply:
        session = _decode_office_session(request)
        if not session:
            raise HTTPException(status_code=401, detail="공식 답변을 작성하려면 의원실 계정 로그인이 필요합니다.")
        if session.get("role") != "office" or session.get("member_id") != member_id:
            raise HTTPException(status_code=403, detail="본인 의원실 페이지의 댓글에만 공식 대댓글을 작성할 수 있습니다.")
        if payload.parent_id is None:
            raise HTTPException(status_code=400, detail="공식 대댓글 대상 부모 댓글(parent_id)이 필요합니다.")

        badge_name = f"{member['name']} 의원실 공식"
        try:
            new_comment = add_comment(
                member_id=member_id,
                author=f"{member['name']} 의원실",
                content=clean_content,
                stance="official",
                parent_id=payload.parent_id,
                is_official_reply=True,
                official_badge_name=badge_name,
            )
        except ValueError as e:
            raise HTTPException(status_code=404, detail=str(e))
        return {
            "status": "success",
            "comment": new_comment,
            "is_verified_office": 1,
        }

    # 일반 시민 무기명 댓글: 기본 유해어 필터 + 동일 IP/UA 15초 연속 도배 방지(429)
    lowered = clean_content.lower()
    if any(bad in lowered for bad in BLOCKED_PROFANITY_WORDS):
        raise HTTPException(status_code=400, detail="건전한 토론 문화 조성을 위해 심한 비속어/유해 표현은 제한됩니다.")

    ip_ua_hash = _compute_ip_ua_hash(request)
    now = time.time()
    last_post = COMMENT_RATE_LIMITS.get(ip_ua_hash)
    if last_post is not None and (now - last_post) < COMMENT_COOLDOWN_SEC:
        retry_after = int(COMMENT_COOLDOWN_SEC - (now - last_post)) + 1
        return JSONResponse(
            status_code=429,
            content={
                "status": "rate_limited",
                "detail": f"도배 방지를 위해 {retry_after}초 후 다시 작성해주세요.",
                "message": f"도배 방지를 위해 {retry_after}초 후 다시 작성해주세요.",
                "retry_after": retry_after,
            },
        )
    COMMENT_RATE_LIMITS[ip_ua_hash] = now
    if len(COMMENT_RATE_LIMITS) > 2000:
        cutoff = now - 60.0
        for k in [k for k, ts in COMMENT_RATE_LIMITS.items() if ts < cutoff]:
            COMMENT_RATE_LIMITS.pop(k, None)

    try:
        new_comment = add_comment(
            member_id=member_id,
            author=(payload.author or "").strip() or "익명 유권자",
            content=clean_content,
            stance=payload.stance or "cheer",
            parent_id=payload.parent_id,
            is_official_reply=False,
            official_badge_name="",
        )
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))

    return {
        "status": "success",
        "comment": new_comment
    }
