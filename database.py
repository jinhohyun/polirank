"""
PoliRank - SQLite 데이터베이스 스키마 및 CRUD 연동 모듈 (6대 지표 & 재미 요소 확장)
"""
import sqlite3
import os
import json
from typing import List, Dict, Any, Optional
from datetime import datetime

DB_PATH = os.path.join(os.path.dirname(__file__), "polirank.db")

def get_connection():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn

def init_db():
    """데이터베이스 테이블 생성 및 6대 지표/재미요소 컬럼 마이그레이션"""
    conn = get_connection()
    cursor = conn.cursor()
    
    # 국회의원 테이블 생성 (신규 필드 포함)
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS members (
        id TEXT PRIMARY KEY,
        name TEXT NOT NULL,
        hanja_name TEXT,
        party TEXT NOT NULL,
        party_color TEXT NOT NULL,
        district TEXT NOT NULL,
        region_type TEXT,
        committee TEXT,
        committee_role TEXT,
        terms INTEGER DEFAULT 1,
        age INTEGER,
        photo_url TEXT,
        official_photo_url TEXT,
        bio TEXT,
        quote TEXT,
        keywords_json TEXT,
        media_mentions INTEGER DEFAULT 0,
        donation_account TEXT,
        cheer_count INTEGER DEFAULT 0,
        legislation_score REAL DEFAULT 0.0,
        passed_score REAL DEFAULT 0.0,
        attendance_score REAL DEFAULT 0.0,
        voting_score REAL DEFAULT 0.0,
        speech_score REAL DEFAULT 0.0,
        policy_score REAL DEFAULT 0.0,
        voting_rate REAL DEFAULT 0.0,
        speech_count INTEGER DEFAULT 0,
        total_score REAL DEFAULT 0.0,
        tier TEXT DEFAULT 'B',
        tier_title TEXT,
        weekly_stats_json TEXT,
        recent_bills_json TEXT,
        updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    );
    """)
    
    # 토론 및 응원 댓글 테이블
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS comments (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        member_id TEXT NOT NULL,
        author TEXT NOT NULL,
        stance TEXT DEFAULT 'cheer',  -- cheer(응원해요), critique(분발해요), proposal(정책제언)
        content TEXT NOT NULL,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        likes INTEGER DEFAULT 0,
        FOREIGN KEY (member_id) REFERENCES members (id)
    );
    """)
    
    conn.commit()
    conn.close()

def get_all_members(party: Optional[str] = None, sort_by: str = "total", search: Optional[str] = None) -> List[Dict[str, Any]]:
    """조건에 따른 국회의원 목록 및 랭킹 조회 (6대 지표 및 응원순 지원)"""
    conn = get_connection()
    cursor = conn.cursor()
    
    # 정렬 컬럼 매핑 (6대 지표)
    sort_column_map = {
        "total": "total_score DESC, passed_score DESC, legislation_score DESC",
        "legislation": "legislation_score DESC, total_score DESC",
        "passed": "passed_score DESC, total_score DESC",
        "attendance": "attendance_score DESC, total_score DESC",
        "voting": "voting_score DESC, total_score DESC",
        "speech": "speech_score DESC, total_score DESC",
        "policy": "policy_score DESC, total_score DESC",
        "cheer": "cheer_count DESC, total_score DESC"
    }
    order_clause = sort_column_map.get(sort_by, sort_column_map["total"])
    
    query = "SELECT * FROM members WHERE 1=1"
    params = []
    
    if party and party != "all":
        query += " AND party = ?"
        params.append(party)
        
    if search and search.strip():
        search_term = f"%{search.strip()}%"
        query += " AND (name LIKE ? OR district LIKE ? OR committee LIKE ? OR quote LIKE ?)"
        params.extend([search_term, search_term, search_term, search_term])
        
    query += f" ORDER BY {order_clause}"
    cursor.execute(query, params)
    rows = cursor.fetchall()
    
    results = []
    current_rank = 1
    sort_key_attr = {
        "total": "total_score",
        "legislation": "legislation_score",
        "passed": "passed_score",
        "attendance": "attendance_score",
        "voting": "voting_score",
        "speech": "speech_score",
        "policy": "policy_score",
        "cheer": "cheer_count"
    }.get(sort_by, "total_score")

    score_list = [dict(r)[sort_key_attr] for r in rows]

    for idx, row in enumerate(rows):
        item = dict(row)
        cur_val = item[sort_key_attr]
        if idx > 0:
            prev_val = dict(rows[idx - 1])[sort_key_attr]
            if prev_val != cur_val:
                current_rank = idx + 1
        else:
            current_rank = 1

        is_tied = score_list.count(cur_val) > 1
        item["rank"] = current_rank
        item["rank_text"] = f"공동 {current_rank}위" if is_tied else f"{current_rank}위"
        item["is_tied"] = is_tied
        if item.get("weekly_stats_json"):
            item["weekly_stats"] = json.loads(item["weekly_stats_json"])
        if item.get("recent_bills_json"):
            item["recent_bills"] = json.loads(item["recent_bills_json"])
        if item.get("keywords_json"):
            item["keywords"] = json.loads(item["keywords_json"])
        else:
            item["keywords"] = ["#국회의원", "#입법활동", "#민생우선"]
        results.append(item)
        
    conn.close()
    return results

def get_member_by_id(member_id: str) -> Optional[Dict[str, Any]]:
    """특정 의원의 상세 정보 및 전체 순위 조회"""
    conn = get_connection()
    cursor = conn.cursor()
    
    cursor.execute("SELECT * FROM members WHERE id = ?", (member_id,))
    row = cursor.fetchone()
    if not row:
        conn.close()
        return None
        
    member = dict(row)
    if member.get("weekly_stats_json"):
        member["weekly_stats"] = json.loads(member["weekly_stats_json"])
    if member.get("recent_bills_json"):
        member["recent_bills"] = json.loads(member["recent_bills_json"])
    if member.get("keywords_json"):
        member["keywords"] = json.loads(member["keywords_json"])
    else:
        member["keywords"] = ["#국회의원", "#입법활동", "#민생우선"]
        
    # 전체 순위 계산
    cursor.execute("SELECT COUNT(*) + 1 AS rank FROM members WHERE total_score > ?", (member["total_score"],))
    rank_row = cursor.fetchone()
    member["total_rank"] = rank_row["rank"] if rank_row else 1
    
    # 댓글 개수
    cursor.execute("SELECT COUNT(*) as comment_count FROM comments WHERE member_id = ?", (member_id,))
    comm_count_row = cursor.fetchone()
    member["comment_count"] = comm_count_row["comment_count"] if comm_count_row else 0
    
    conn.close()
    return member

def cheer_member(member_id: str) -> int:
    """국회의원 실시간 1클릭 응원 카운터 증가"""
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("UPDATE members SET cheer_count = cheer_count + 1 WHERE id = ?", (member_id,))
    conn.commit()
    
    cursor.execute("SELECT cheer_count FROM members WHERE id = ?", (member_id,))
    row = cursor.fetchone()
    new_count = row["cheer_count"] if row else 0
    conn.close()
    return new_count

def get_comments(member_id: str, limit: int = 50) -> List[Dict[str, Any]]:
    """특정 의원의 토론 댓글 목록 조회"""
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("""
        SELECT * FROM comments 
        WHERE member_id = ? 
        ORDER BY created_at DESC 
        LIMIT ?
    """, (member_id, limit))
    rows = cursor.fetchall()
    comments = [dict(row) for row in rows]
    conn.close()
    return comments

def add_comment(member_id: str, author: str, content: str, stance: str = "cheer") -> Dict[str, Any]:
    """의원 상세 토론 댓글 등록"""
    conn = get_connection()
    cursor = conn.cursor()
    created_at = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    cursor.execute("""
        INSERT INTO comments (member_id, author, stance, content, created_at, likes)
        VALUES (?, ?, ?, ?, ?, 0)
    """, (member_id, author.strip() or "익명 시민", stance, content.strip(), created_at))
    new_id = cursor.lastrowid
    conn.commit()
    conn.close()
    
    return {
        "id": new_id,
        "member_id": member_id,
        "author": author.strip() or "익명 시민",
        "stance": stance,
        "content": content.strip(),
        "created_at": created_at,
        "likes": 0
    }

def get_summary_stats() -> Dict[str, Any]:
    """플랫폼 전체 요약 통계"""
    conn = get_connection()
    cursor = conn.cursor()
    
    cursor.execute("SELECT COUNT(*) as total_members FROM members")
    total_members = cursor.fetchone()["total_members"]
    
    cursor.execute("SELECT SUM(cheer_count) as total_cheers FROM members")
    total_cheers = cursor.fetchone()["total_cheers"] or 0
    
    cursor.execute("SELECT COUNT(*) as total_comments FROM comments")
    total_comments = cursor.fetchone()["total_comments"] or 0
    
    cursor.execute("SELECT AVG(total_score) as avg_score FROM members")
    avg_score = round(cursor.fetchone()["avg_score"] or 0.0, 1)
    
    cursor.execute("SELECT name, total_score, party FROM members ORDER BY total_score DESC LIMIT 1")
    top_member = cursor.fetchone()
    
    conn.close()
    return {
        "total_members": total_members,
        "total_cheers": total_cheers,
        "total_comments": total_comments,
        "avg_score": avg_score,
        "top_member": dict(top_member) if top_member else None
    }
