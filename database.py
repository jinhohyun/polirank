"""
PoliRank - SQLite 데이터베이스 스키마 및 CRUD 연동 모듈 (6대 지표 & 재미 요소 확장)
"""
import sqlite3
import os
import json
import hashlib
import hmac
import secrets
from collections import Counter
from typing import List, Dict, Any, Optional
from datetime import datetime

DB_PATH = os.path.join(os.path.dirname(__file__), "polirank.db")


def hash_password(password: str, iterations: int = 120000) -> str:
    """PBKDF2-HMAC-SHA256 + 랜덤 솔트 기반 안전한 비밀번호 해시 생성"""
    salt_hex = secrets.token_hex(16)
    dk = hashlib.pbkdf2_hmac(
        "sha256",
        password.encode("utf-8"),
        bytes.fromhex(salt_hex),
        iterations,
    ).hex()
    return f"pbkdf2_sha256${iterations}${salt_hex}${dk}"


def verify_password(password: str, stored_hash: str) -> bool:
    """저장된 PBKDF2-HMAC-SHA256 해시와 입력 비밀번호 상수시간 비교 검증"""
    try:
        scheme, iter_s, salt_hex, expected_hex = stored_hash.split("$", 3)
        if scheme != "pbkdf2_sha256":
            return False
        dk = hashlib.pbkdf2_hmac(
            "sha256",
            password.encode("utf-8"),
            bytes.fromhex(salt_hex),
            int(iter_s),
        ).hex()
        return hmac.compare_digest(dk, expected_hex)
    except Exception:
        return False

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
        mona_cd TEXT,
        name TEXT NOT NULL,
        hanja_name TEXT,
        party TEXT NOT NULL,
        party_color TEXT NOT NULL,
        district TEXT NOT NULL,
        region_type TEXT,
        committee TEXT,
        committee_role TEXT,
        committee_role_label TEXT DEFAULT '위원',
        terms INTEGER DEFAULT 1,
        gender TEXT DEFAULT 'male',
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
        bipartisan_score REAL DEFAULT 0.0,
        committee_score REAL DEFAULT 0.0,
        voting_score REAL DEFAULT 0.0,
        speech_score REAL DEFAULT 0.0,
        policy_score REAL DEFAULT 0.0,
        voting_rate REAL DEFAULT 0.0,
        speech_count INTEGER DEFAULT 0,
        total_score REAL DEFAULT 0.0,
        fandom_score REAL DEFAULT 0.0,
        controversy_score REAL DEFAULT 0.0,
        hidden_gem_score REAL DEFAULT 0.0,
        news_30d_count INTEGER DEFAULT 0,
        controversy_news_count INTEGER DEFAULT 0,
        recent_news_json TEXT,
        tier TEXT DEFAULT 'B',
        tier_title TEXT,
        weekly_stats_json TEXT,
        recent_bills_json TEXT,
        is_verified_office INTEGER DEFAULT 0,
        office_notice TEXT DEFAULT '',
        updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    );
    """)

    # 구버전 DB 스키마 호환 마이그레이션
    cursor.execute("PRAGMA table_info(members)")
    existing_cols = {row["name"] for row in cursor.fetchall()}
    for col_name, col_def in [
        ("mona_cd", "TEXT"),
        ("gender", "TEXT DEFAULT 'male'"),
        ("committee_role_label", "TEXT DEFAULT '위원'"),
        ("bipartisan_score", "REAL DEFAULT 0.0"),
        ("committee_score", "REAL DEFAULT 0.0"),
        ("fandom_score", "REAL DEFAULT 0.0"),
        ("controversy_score", "REAL DEFAULT 0.0"),
        ("hidden_gem_score", "REAL DEFAULT 0.0"),
        ("news_30d_count", "INTEGER DEFAULT 0"),
        ("controversy_news_count", "INTEGER DEFAULT 0"),
        ("recent_news_json", "TEXT"),
        ("is_verified_office", "INTEGER DEFAULT 0"),
        ("office_notice", "TEXT DEFAULT ''"),
    ]:
        if col_name not in existing_cols:
            cursor.execute(f"ALTER TABLE members ADD COLUMN {col_name} {col_def}")

    # 메타데이터 테이블 (최근 업데이트 시각 등)
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS metadata (
        key TEXT PRIMARY KEY,
        value TEXT,
        updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    );
    """)
    
    # 토론 및 응원 댓글 테이블 (v3.3 계층형 대댓글 & 공식 답변 지원)
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS comments (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        member_id TEXT NOT NULL,
        author TEXT NOT NULL,
        stance TEXT DEFAULT 'cheer',  -- cheer(응원해요), critique(분발해요), proposal(정책제언), official(공식답변)
        content TEXT NOT NULL,
        parent_id INTEGER DEFAULT NULL,
        is_official_reply INTEGER DEFAULT 0,
        official_badge_name TEXT DEFAULT '',
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        likes INTEGER DEFAULT 0,
        FOREIGN KEY (member_id) REFERENCES members (id)
    );
    """)

    cursor.execute("PRAGMA table_info(comments)")
    existing_comment_cols = {row["name"] for row in cursor.fetchall()}
    for col_name, col_def in [
        ("parent_id", "INTEGER DEFAULT NULL"),
        ("is_official_reply", "INTEGER DEFAULT 0"),
        ("official_badge_name", "TEXT DEFAULT ''"),
    ]:
        if col_name not in existing_comment_cols:
            cursor.execute(f"ALTER TABLE comments ADD COLUMN {col_name} {col_def}")
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_comments_member_parent ON comments (member_id, parent_id, id);")

    # 공식 의원실 & 운영자 계정 테이블
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS office_accounts (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        username TEXT UNIQUE NOT NULL,
        password_hash TEXT NOT NULL,
        member_id TEXT,
        office_name TEXT NOT NULL,
        role TEXT DEFAULT 'office',
        is_active INTEGER DEFAULT 1,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    );
    """)

    # 1인 1의원 1회 중복 응원 방지 로그 테이블 (원본 IP 미저장, SHA-256 해시만 저장)
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS cheer_logs (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        member_id TEXT NOT NULL,
        cookie_hash TEXT,
        ip_ua_hash TEXT,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        FOREIGN KEY (member_id) REFERENCES members (id)
    );
    """)
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_cheer_logs_member_cookie ON cheer_logs (member_id, cookie_hash);")
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_cheer_logs_member_ipua ON cheer_logs (member_id, ip_ua_hash);")

    # 초기 운영자 계정 자동 부트스트랩 (없는 경우 생성, 환경변수 지정 시 해시 동기화)
    env_admin_pw = os.environ.get("POLIRANK_ADMIN_PASSWORD")
    cursor.execute("SELECT id, password_hash FROM office_accounts WHERE role = 'admin' LIMIT 1")
    admin_row = cursor.fetchone()
    if not admin_row:
        initial_pw = env_admin_pw or "polirank_admin_2026!"
        cursor.execute("""
            INSERT INTO office_accounts (username, password_hash, member_id, office_name, role, is_active)
            VALUES ('admin', ?, NULL, 'PoliRank 운영본부', 'admin', 1)
        """, (hash_password(initial_pw),))
    elif env_admin_pw and not verify_password(env_admin_pw, admin_row["password_hash"]):
        cursor.execute(
            "UPDATE office_accounts SET password_hash = ?, is_active = 1 WHERE id = ?",
            (hash_password(env_admin_pw), admin_row["id"]),
        )
    
    conn.commit()
    conn.close()

def get_all_members(party: Optional[str] = None, sort_by: str = "total", search: Optional[str] = None) -> List[Dict[str, Any]]:
    """조건에 따른 국회의원 목록 및 랭킹 조회 (6대 지표 및 응원순 지원)"""
    conn = get_connection()
    cursor = conn.cursor()
    
    # 정렬 컬럼 매핑 (v3.1 6대 핵심 축 + 재미/화제성 3종 + 응원순)
    sort_column_map = {
        "total": "total_score DESC, passed_score DESC, voting_score DESC",
        "passed": "passed_score DESC, total_score DESC",
        "voting": "voting_score DESC, total_score DESC",
        "legislation": "legislation_score DESC, total_score DESC",
        "bipartisan": "bipartisan_score DESC, total_score DESC",
        "committee": "committee_score DESC, total_score DESC",
        "attendance": "committee_score DESC, total_score DESC",
        "speech": "speech_score DESC, total_score DESC",
        "policy": "policy_score DESC, total_score DESC",
        "cheer": "cheer_count DESC, total_score DESC",
        "fandom": "fandom_score DESC, cheer_count DESC, news_30d_count DESC",
        "controversy": "controversy_score DESC, controversy_news_count DESC, news_30d_count DESC",
        "hidden_gem": "hidden_gem_score DESC, total_score DESC"
    }
    order_clause = sort_column_map.get(sort_by, sort_column_map["total"])
    
    query = "SELECT * FROM members WHERE 1=1"
    params = []
    
    if party and party != "all":
        if party in ("무소속/기타", "etc"):
            query += " AND party NOT IN ('더불어민주당', '국민의힘', '조국혁신당', '진보당', '개혁신당', '기본소득당')"
        else:
            query += " AND party = ?"
            params.append(party)
        
    if search and search.strip():
        search_term = f"%{search.strip()}%"
        query += " AND (name LIKE ? OR district LIKE ? OR committee LIKE ? OR party LIKE ? OR quote LIKE ? OR keywords_json LIKE ?)"
        params.extend([search_term, search_term, search_term, search_term, search_term, search_term])
        
    query += f" ORDER BY {order_clause}"
    cursor.execute(query, params)
    rows = cursor.fetchall()
    
    results = []
    current_rank = 1
    sort_key_attr = {
        "total": "total_score",
        "passed": "passed_score",
        "voting": "voting_score",
        "legislation": "legislation_score",
        "bipartisan": "bipartisan_score",
        "committee": "committee_score",
        "attendance": "committee_score",
        "speech": "speech_score",
        "policy": "policy_score",
        "cheer": "cheer_count",
        "fandom": "fandom_score",
        "controversy": "controversy_score",
        "hidden_gem": "hidden_gem_score"
    }.get(sort_by, "total_score")

    score_counts = Counter(row[sort_key_attr] for row in rows)

    for idx, row in enumerate(rows):
        item = dict(row)
        cur_val = item[sort_key_attr]
        if idx > 0:
            prev_val = rows[idx - 1][sort_key_attr]
            if prev_val != cur_val:
                current_rank = idx + 1
        else:
            current_rank = 1

        is_tied = score_counts[cur_val] > 1
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
        if item.get("recent_news_json"):
            news_items = json.loads(item["recent_news_json"])
            item["recent_news_items"] = news_items
            item["recent_news_titles"] = [n["title"] if isinstance(n, dict) else n for n in news_items]
        else:
            item["recent_news_items"] = []
            item["recent_news_titles"] = []
        item["is_verified_office"] = int(item.get("is_verified_office") or 0)
        item["office_notice"] = item.get("office_notice") or ""
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
        ws = json.loads(member["weekly_stats_json"])
        member["weekly_stats"] = ws
    else:
        ws = {}
        member["weekly_stats"] = ws
    if member.get("recent_bills_json"):
        member["recent_bills"] = json.loads(member["recent_bills_json"])
    if member.get("keywords_json"):
        member["keywords"] = json.loads(member["keywords_json"])
    else:
        member["keywords"] = ["#국회의원", "#입법활동", "#민생우선"]
    if member.get("recent_news_json"):
        news_items = json.loads(member["recent_news_json"])
        member["recent_news_items"] = news_items
        member["recent_news_titles"] = [n["title"] if isinstance(n, dict) else n for n in news_items]
    else:
        member["recent_news_items"] = []
        member["recent_news_titles"] = []
    member["is_verified_office"] = int(member.get("is_verified_office") or 0)
    member["office_notice"] = member.get("office_notice") or ""

    # 14대 내부 공공 팩트 지표 요약 시트
    vb = ws.get("vote_breakdown") or {}
    member["fact_sheet_14"] = {
        "bills_proposed": int(ws.get("bills_proposed", 0)),
        "passed_original": int(ws.get("passed_original", 0)),
        "passed_amended": int(ws.get("passed_amended", 0)),
        "alt_incorporated": int(ws.get("alt_incorporated", ws.get("subcommittee_passed", 0))),
        "passage_efficiency": float(ws.get("passage_efficiency", 0.0)),
        "bipartisan_rate": float(ws.get("bipartisan_rate", 0.0)),
        "bipartisan_cosponsor_share": float(ws.get("bipartisan_cosponsor_share", 0.0)),
        "avg_cosponsors": float(ws.get("avg_cosponsors", 0.0)),
        "cosponsor_participations": int(ws.get("cosponsor_participations", 0)),
        "policy_diversity": int(ws.get("policy_diversity", 0)),
        "policy_committees": ws.get("policy_committees", []),
        "voting_rate": float(ws.get("voting_rate", member.get("voting_rate", 0.0))),
        "votes_participated": int(ws.get("votes_participated", 0)),
        "votes_eligible": int(ws.get("votes_eligible", 0)),
        "active_vote_ratio": float(ws.get("active_vote_ratio", member.get("voting_rate", 0.0))),
        "vote_breakdown": {
            "찬성": int(vb.get("찬성", 0)),
            "반대": int(vb.get("반대", 0)),
            "기권": int(vb.get("기권", 0)),
            "불참": int(vb.get("불참", 0)),
        },
        "committee_count": int(ws.get("committee_count", 1)),
        "committees_list": ws.get("committees_list", [member.get("committee", "")]),
        "has_special_duty": bool(ws.get("has_special_duty", False)),
        "special_duties": ws.get("special_duties", []),
        "committee_role_label": member.get("committee_role_label", "위원"),
        "speech_count": int(member.get("speech_count", ws.get("committee_speech_count", 0))),
        "seminar_hosted": bool(ws.get("seminar_hosted", False)),
        "interpellation_count": int(ws.get("interpellation_count", 0)),
        "media_mentions": int(member.get("media_mentions", 0)),
        "news_30d_count": int(member.get("news_30d_count", ws.get("news_30d_count", 0))),
        "controversy_news_count": int(member.get("controversy_news_count", ws.get("controversy_news_count", 0))),
    }
        
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

def set_metadata(key: str, value: str):
    """메타데이터 저장/갱신"""
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("""
        INSERT INTO metadata (key, value, updated_at)
        VALUES (?, ?, CURRENT_TIMESTAMP)
        ON CONFLICT(key) DO UPDATE SET value = excluded.value, updated_at = CURRENT_TIMESTAMP
    """, (key, value))
    conn.commit()
    conn.close()


def get_metadata(key: str, default: Optional[str] = None) -> Optional[str]:
    """메타데이터 조회"""
    conn = get_connection()
    cursor = conn.cursor()
    try:
        cursor.execute("SELECT value FROM metadata WHERE key = ?", (key,))
        row = cursor.fetchone()
        return row["value"] if row else default
    except Exception:
        return default
    finally:
        conn.close()


def _refresh_fun_scores_in_conn(conn: sqlite3.Connection, member_id: str):
    """응원/댓글 변동 시 total_score를 건드리지 않고 재미 지표만 실시간 재계산"""
    from scoring import calculate_fun_metrics

    cursor = conn.cursor()
    cursor.execute("SELECT * FROM members WHERE id = ?", (member_id,))
    row = cursor.fetchone()
    if not row:
        return
    m = dict(row)
    m["weekly_stats"] = json.loads(m["weekly_stats_json"]) if m.get("weekly_stats_json") else {}

    cursor.execute(
        "SELECT stance, COUNT(*) as c FROM comments WHERE member_id = ? AND COALESCE(is_official_reply, 0) = 0 GROUP BY stance",
        (member_id,),
    )
    c_stats = {r["stance"]: r["c"] for r in cursor.fetchall()}

    fun = calculate_fun_metrics(
        m,
        total_score=m["total_score"],
        cheer_count=m["cheer_count"],
        comment_stats=c_stats,
    )
    cursor.execute(
        "UPDATE members SET fandom_score = ?, controversy_score = ?, hidden_gem_score = ? WHERE id = ?",
        (fun["fandom_score"], fun["controversy_score"], fun["hidden_gem_score"], member_id),
    )


def record_cheer_with_guard(
    member_id: str,
    cookie_hash: Optional[str] = None,
    ip_ua_hash: Optional[str] = None,
) -> Dict[str, Any]:
    """
    3중 중복 응원 방지 검증 후 원자적으로 응원수 증가 및 팬덤 지수 실시간 재계산.
    cookie_hash 또는 ip_ua_hash 중 하나라도 기존 응원 로그가 있으면 차단합니다.
    """
    conn = get_connection()
    cursor = conn.cursor()
    try:
        cursor.execute("BEGIN IMMEDIATE")

        conditions = []
        params: List[Any] = [member_id]
        if cookie_hash:
            conditions.append("cookie_hash = ?")
            params.append(cookie_hash)
        if ip_ua_hash:
            conditions.append("ip_ua_hash = ?")
            params.append(ip_ua_hash)

        if conditions:
            where_clause = " OR ".join(conditions)
            cursor.execute(
                f"SELECT id FROM cheer_logs WHERE member_id = ? AND ({where_clause}) LIMIT 1",
                params,
            )
            if cursor.fetchone():
                cursor.execute("SELECT cheer_count FROM members WHERE id = ?", (member_id,))
                row = cursor.fetchone()
                conn.rollback()
                return {
                    "allowed": False,
                    "status": "already_cheered",
                    "cheer_count": row["cheer_count"] if row else 0,
                }

        cursor.execute(
            "INSERT INTO cheer_logs (member_id, cookie_hash, ip_ua_hash) VALUES (?, ?, ?)",
            (member_id, cookie_hash, ip_ua_hash),
        )
        cursor.execute("UPDATE members SET cheer_count = cheer_count + 1 WHERE id = ?", (member_id,))
        _refresh_fun_scores_in_conn(conn, member_id)
        conn.commit()

        cursor.execute("SELECT cheer_count, fandom_score FROM members WHERE id = ?", (member_id,))
        row = cursor.fetchone()
        return {
            "allowed": True,
            "status": "success",
            "cheer_count": row["cheer_count"] if row else 0,
            "fandom_score": row["fandom_score"] if row else 0.0,
        }
    finally:
        conn.close()


def get_cheered_member_ids(
    cookie_hash: Optional[str] = None,
    ip_ua_hash: Optional[str] = None,
) -> List[str]:
    """현재 식별자(cookie_hash 또는 ip_ua_hash)로 이미 응원한 의원 ID 목록 반환"""
    conditions = []
    params: List[Any] = []
    if cookie_hash:
        conditions.append("cookie_hash = ?")
        params.append(cookie_hash)
    if ip_ua_hash:
        conditions.append("ip_ua_hash = ?")
        params.append(ip_ua_hash)

    if not conditions:
        return []

    conn = get_connection()
    cursor = conn.cursor()
    try:
        where_clause = " OR ".join(conditions)
        cursor.execute(f"SELECT DISTINCT member_id FROM cheer_logs WHERE {where_clause}", params)
        return [row["member_id"] for row in cursor.fetchall()]
    except Exception:
        return []
    finally:
        conn.close()


def cheer_member(member_id: str) -> int:
    """국회의원 실시간 1클릭 응원 카운터 증가 (하위 호환 래퍼)"""
    res = record_cheer_with_guard(member_id)
    return res["cheer_count"]

def get_comments(member_id: str, limit: int = 50) -> List[Dict[str, Any]]:
    """특정 의원의 토론 댓글 목록 조회 (계층형: 부모 댓글 + 공식 대댓글 우선 정렬 replies 배열)"""
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("""
        SELECT * FROM comments
        WHERE member_id = ? AND parent_id IS NULL
        ORDER BY id DESC
        LIMIT ?
    """, (member_id, limit))
    parents = []
    parent_map: Dict[int, Dict[str, Any]] = {}
    for row in cursor.fetchall():
        c = dict(row)
        c["is_official_reply"] = int(c.get("is_official_reply") or 0)
        c["official_badge_name"] = c.get("official_badge_name") or ""
        c["replies"] = []
        parents.append(c)
        parent_map[c["id"]] = c

    if parent_map:
        placeholders = ",".join("?" for _ in parent_map)
        cursor.execute(f"""
            SELECT * FROM comments
            WHERE member_id = ? AND parent_id IN ({placeholders})
            ORDER BY COALESCE(is_official_reply, 0) DESC, id ASC
        """, [member_id, *parent_map.keys()])
        for row in cursor.fetchall():
            r = dict(row)
            r["is_official_reply"] = int(r.get("is_official_reply") or 0)
            r["official_badge_name"] = r.get("official_badge_name") or ""
            pid = r.get("parent_id")
            if pid in parent_map:
                parent_map[pid]["replies"].append(r)

    conn.close()
    return parents


def add_comment(
    member_id: str,
    author: str,
    content: str,
    stance: str = "cheer",
    parent_id: Optional[int] = None,
    is_official_reply: bool = False,
    official_badge_name: str = "",
) -> Dict[str, Any]:
    """의원 상세 토론 댓글 또는 공식 의원실 대댓글 등록"""
    conn = get_connection()
    cursor = conn.cursor()
    try:
        if parent_id is not None:
            cursor.execute(
                "SELECT id, member_id, parent_id FROM comments WHERE id = ?",
                (parent_id,),
            )
            parent_row = cursor.fetchone()
            if not parent_row or parent_row["member_id"] != member_id or parent_row["parent_id"] is not None:
                raise ValueError("유효하지 않은 대상 댓글입니다.")

        created_at = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        clean_author = (author or "").strip() or ("공식 의원실" if is_official_reply else "익명 유권자")
        clean_content = content.strip()
        resolved_stance = "official" if is_official_reply else (stance or "cheer")
        official_flag = 1 if is_official_reply else 0
        badge_name = (official_badge_name or "").strip() if is_official_reply else ""

        cursor.execute("""
            INSERT INTO comments (
                member_id, author, stance, content, parent_id, is_official_reply, official_badge_name, created_at, likes
            )
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, 0)
        """, (
            member_id,
            clean_author,
            resolved_stance,
            clean_content,
            parent_id,
            official_flag,
            badge_name,
            created_at,
        ))
        new_id = cursor.lastrowid

        if is_official_reply:
            cursor.execute("UPDATE members SET is_verified_office = 1 WHERE id = ?", (member_id,))

        _refresh_fun_scores_in_conn(conn, member_id)
        conn.commit()
        return {
            "id": new_id,
            "member_id": member_id,
            "author": clean_author,
            "stance": resolved_stance,
            "content": clean_content,
            "parent_id": parent_id,
            "is_official_reply": official_flag,
            "official_badge_name": badge_name,
            "created_at": created_at,
            "likes": 0,
            "replies": [],
        }
    finally:
        conn.close()


def authenticate_office_account(username: str, password: str) -> Optional[Dict[str, Any]]:
    """의원실/운영자 계정 아이디 & PBKDF2 비밀번호 인증"""
    clean_user = (username or "").strip()
    if not clean_user or not password:
        return None
    conn = get_connection()
    cursor = conn.cursor()
    try:
        cursor.execute(
            "SELECT * FROM office_accounts WHERE username = ? AND is_active = 1 LIMIT 1",
            (clean_user,),
        )
        row = cursor.fetchone()
        if not row:
            return None
        if not verify_password(password, row["password_hash"]):
            return None
        return {
            "id": row["id"],
            "username": row["username"],
            "member_id": row["member_id"],
            "office_name": row["office_name"],
            "role": row["role"],
            "is_active": int(row["is_active"]),
        }
    finally:
        conn.close()


def get_office_account_by_username(username: str) -> Optional[Dict[str, Any]]:
    """활성화된 의원실/운영자 계정 안전 조회 (password_hash 미포함)"""
    clean_user = (username or "").strip()
    if not clean_user:
        return None
    conn = get_connection()
    cursor = conn.cursor()
    try:
        cursor.execute(
            "SELECT id, username, member_id, office_name, role, is_active FROM office_accounts WHERE username = ? AND is_active = 1 LIMIT 1",
            (clean_user,),
        )
        row = cursor.fetchone()
        return dict(row) if row else None
    finally:
        conn.close()


def issue_office_account(
    member_id: str,
    username: str,
    password: str,
    verify_now: bool = True,
    office_name: Optional[str] = None,
) -> Dict[str, Any]:
    """운영자 전용: 특정 의원의 공식 의원실 계정 발급/갱신 및 선택적 즉시 인증 배지 부여"""
    clean_user = (username or "").strip()
    if not clean_user or len(clean_user) < 3:
        raise ValueError("아이디는 3자 이상이어야 합니다.")
    if not password or len(password) < 4:
        raise ValueError("비밀번호는 4자 이상이어야 합니다.")

    conn = get_connection()
    cursor = conn.cursor()
    try:
        cursor.execute("SELECT id, name, is_verified_office FROM members WHERE id = ?", (member_id,))
        member_row = cursor.fetchone()
        if not member_row:
            raise LookupError("Member not found")

        cursor.execute("SELECT role FROM office_accounts WHERE username = ?", (clean_user,))
        existing = cursor.fetchone()
        if existing and existing["role"] == "admin":
            raise ValueError("관리자 계정은 의원실 계정으로 덮어쓸 수 없습니다.")

        resolved_office_name = (office_name or "").strip() or f"{member_row['name']} 의원실"
        pw_hash = hash_password(password)

        cursor.execute("""
            INSERT INTO office_accounts (username, password_hash, member_id, office_name, role, is_active)
            VALUES (?, ?, ?, ?, 'office', 1)
            ON CONFLICT(username) DO UPDATE SET
                password_hash = excluded.password_hash,
                member_id = excluded.member_id,
                office_name = excluded.office_name,
                role = 'office',
                is_active = 1
        """, (clean_user, pw_hash, member_id, resolved_office_name))

        verified_val = int(member_row["is_verified_office"] or 0)
        if verify_now:
            cursor.execute("UPDATE members SET is_verified_office = 1 WHERE id = ?", (member_id,))
            verified_val = 1

        conn.commit()
        return {
            "username": clean_user,
            "member_id": member_id,
            "member_name": member_row["name"],
            "office_name": resolved_office_name,
            "role": "office",
            "is_verified_office": verified_val,
        }
    finally:
        conn.close()


def toggle_member_verification(member_id: str, verified: Optional[bool] = None) -> Optional[Dict[str, Any]]:
    """운영자 전용: 특정 의원의 공식 의원실 인증 배지(0/1) 전환"""
    conn = get_connection()
    cursor = conn.cursor()
    try:
        cursor.execute("SELECT id, name, is_verified_office FROM members WHERE id = ?", (member_id,))
        row = cursor.fetchone()
        if not row:
            return None
        current = int(row["is_verified_office"] or 0)
        next_val = (1 if verified else 0) if verified is not None else (0 if current == 1 else 1)
        cursor.execute("UPDATE members SET is_verified_office = ? WHERE id = ?", (next_val, member_id))
        conn.commit()
        return {
            "member_id": member_id,
            "name": row["name"],
            "is_verified_office": next_val,
        }
    finally:
        conn.close()


def update_office_notice(member_id: str, office_notice: str) -> Optional[Dict[str, Any]]:
    """의원실 공식 의정 브리핑/소명 공지 저장 및 공식 인증 활성화"""
    conn = get_connection()
    cursor = conn.cursor()
    try:
        cursor.execute("SELECT id, name FROM members WHERE id = ?", (member_id,))
        row = cursor.fetchone()
        if not row:
            return None
        clean_notice = (office_notice or "").strip()
        cursor.execute(
            "UPDATE members SET office_notice = ?, is_verified_office = 1 WHERE id = ?",
            (clean_notice, member_id),
        )
        conn.commit()
        return {
            "member_id": member_id,
            "name": row["name"],
            "office_notice": clean_notice,
            "is_verified_office": 1,
        }
    finally:
        conn.close()


def list_office_accounts() -> List[Dict[str, Any]]:
    """운영자용: 발급된 의원실 계정 및 인증 현황 조회 (해시 제외)"""
    conn = get_connection()
    cursor = conn.cursor()
    try:
        cursor.execute("""
            SELECT oa.id, oa.username, oa.member_id, oa.office_name, oa.role, oa.is_active, oa.created_at,
                   m.name as member_name, m.party as member_party, COALESCE(m.is_verified_office, 0) as is_verified_office
            FROM office_accounts oa
            LEFT JOIN members m ON oa.member_id = m.id
            WHERE oa.role = 'office'
            ORDER BY oa.id DESC
        """)
        return [dict(r) for r in cursor.fetchall()]
    finally:
        conn.close()

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

    cursor.execute("SELECT party, COUNT(*) as cnt FROM members GROUP BY party")
    party_counts = {row["party"]: row["cnt"] for row in cursor.fetchall()}
    major_parties = {"더불어민주당", "국민의힘", "조국혁신당", "진보당", "개혁신당", "기본소득당"}
    etc_count = sum(cnt for p, cnt in party_counts.items() if p not in major_parties)
    party_counts["all"] = total_members
    party_counts["무소속/기타"] = etc_count

    last_updated_at = None
    try:
        cursor.execute("SELECT value FROM metadata WHERE key = 'last_updated_at'")
        meta_row = cursor.fetchone()
        if meta_row:
            last_updated_at = meta_row["value"]
    except Exception:
        pass
    if not last_updated_at:
        last_updated_at = datetime.now().strftime("%Y-%m-%d %H:%M KST")

    conn.close()
    return {
        "total_members": total_members,
        "total_cheers": total_cheers,
        "total_comments": total_comments,
        "avg_score": avg_score,
        "top_member": dict(top_member) if top_member else None,
        "party_counts": party_counts,
        "last_updated_at": last_updated_at,
        "update_schedule": "매주 월요일 06:00 KST 자동 동기화",
    }
