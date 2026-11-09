"""
PoliRank - 국회의원 객관적 랭킹 & 커뮤니티 MVP 플랫폼 백엔드 (FastAPI) - 6대 정량 지표 & 재미요소 확장
"""
import os
import sys
from typing import Optional
from fastapi import FastAPI, HTTPException, Query, Response
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse, HTMLResponse
from pydantic import BaseModel

CURRENT_DIR = os.path.dirname(os.path.abspath(__file__))
if CURRENT_DIR not in sys.path:
    sys.path.insert(0, CURRENT_DIR)

from database import (
    init_db,
    get_all_members,
    get_member_by_id,
    cheer_member,
    get_comments,
    add_comment,
    get_summary_stats
)
from avatar_generator import generate_caricature_svg

app = FastAPI(
    title="PoliRank API",
    description="국회의원 객관적 6대 정량 지표 랭킹 & 커뮤니티 MVP API",
    version="1.1.0"
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

from seed_data import seed
from database import get_connection

@app.on_event("startup")
def startup_event():
    init_db()
    conn = get_connection()
    c = conn.cursor()
    try:
        c.execute("SELECT COUNT(*) as cnt FROM members")
        cnt = c.fetchone()["cnt"]
        if cnt == 0:
            print("[*] Empty database detected on startup. Seeding members data...")
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

@app.get("/api/stats/summary")
def get_stats():
    """상단 헤더 라이브 통계 지표"""
    return get_summary_stats()

@app.get("/api/members")
def list_members(
    party: Optional[str] = Query(None, description="정당 필터 (all, 더불어민주당, 국민의힘 등)"),
    sort_by: str = Query("total", description="정렬 기준 (total, legislation, passed, attendance, voting, speech, policy, cheer)"),
    search: Optional[str] = Query(None, description="이름, 지역구, 상임위, 어록 검색")
):
    """국회의원 랭킹 목록 조회 (객관적 6대 스탯 순위)"""
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
    """국회의원 상세 정보 및 6각 레이더 차트 지표 조회"""
    member = get_member_by_id(member_id)
    if not member:
        raise HTTPException(status_code=404, detail="Member not found")
        
    member["avatar_url"] = f"/api/members/{member['id']}/avatar.svg"
    
    # 6대 핵심 객관 지표 6각 레이더 차트 데이터
    member["radar_chart"] = {
        "labels": ["입법 실적", "법안 가결", "의정 출석", "표결 참여", "상임위 발언", "정책 세미나"],
        "datasets": [{
            "label": f"{member['name']} 의원 6대 능력치",
            "data": [
                member["legislation_score"],
                member["passed_score"],
                member["attendance_score"],
                member["voting_score"],
                member["speech_score"],
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
    else:
        name = member["name"]
        party = member["party"]
        color = member["party_color"]
        
    svg_code = generate_caricature_svg(name=name, party=party, party_color=color, size=size)
    return Response(content=svg_code, media_type="image/svg+xml")

@app.post("/api/members/{member_id}/cheer")
def cheer(member_id: str):
    """실시간 1클릭 응원 카운터 증가"""
    member = get_member_by_id(member_id)
    if not member:
        raise HTTPException(status_code=404, detail="Member not found")
    new_count = cheer_member(member_id)
    return {
        "status": "success",
        "member_id": member_id,
        "name": member["name"],
        "cheer_count": new_count
    }

@app.get("/api/members/{member_id}/comments")
def read_comments(member_id: str, limit: int = 50):
    """의원 상세 토론 댓글 피드 조회"""
    comments = get_comments(member_id, limit=limit)
    return {
        "status": "success",
        "member_id": member_id,
        "count": len(comments),
        "comments": comments
    }

@app.post("/api/members/{member_id}/comments")
def create_comment(member_id: str, payload: CommentCreate):
    """의원 토론 댓글 작성"""
    member = get_member_by_id(member_id)
    if not member:
        raise HTTPException(status_code=404, detail="Member not found")
        
    if not payload.content or not payload.content.strip():
        raise HTTPException(status_code=400, detail="Comment content cannot be empty")
        
    new_comment = add_comment(
        member_id=member_id,
        author=payload.author or "익명 시민",
        content=payload.content,
        stance=payload.stance or "cheer"
    )
    return {
        "status": "success",
        "comment": new_comment
    }
