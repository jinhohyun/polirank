import sqlite3
import json
import os
from typing import Dict, List, Any, Optional

class BaseDatabaseManager:
    """
    공통 랭킹 플랫폼 데이터베이스 매니저 (SQLite 기반)
    엔티티(정치인/아티스트), 투표, 메트릭, 뉴스/소셜 통계, 댓글/의견 처리
    """
    def __init__(self, db_path: str):
        self.db_path = db_path
        self._init_db()

    def get_connection(self):
        target_path = self.db_path
        if os.environ.get("VERCEL"):
            db_name = os.path.basename(self.db_path)
            tmp_path = os.path.join("/tmp", db_name)
            if not os.path.exists(tmp_path) and os.path.exists(self.db_path):
                import shutil
                try:
                    shutil.copy2(self.db_path, tmp_path)
                except Exception:
                    pass
            if os.path.exists(tmp_path):
                target_path = tmp_path

        os.makedirs(os.path.dirname(os.path.abspath(target_path)), exist_ok=True)
        conn = sqlite3.connect(target_path)
        conn.row_factory = sqlite3.Row
        return conn

    def _init_db(self):
        try:
            os.makedirs(os.path.dirname(os.path.abspath(self.db_path)), exist_ok=True)
        except Exception:
            pass
        with self.get_connection() as conn:
            cursor = conn.cursor()
            # 1. 엔티티 메인 테이블 (공통 필드 + JSON extra_data)
            cursor.execute("""
            CREATE TABLE IF NOT EXISTS entities (
                id TEXT PRIMARY KEY,
                name TEXT NOT NULL,
                name_en TEXT,
                category TEXT,
                subcategory TEXT,
                image_url TEXT,
                total_score REAL DEFAULT 0.0,
                current_rank INTEGER DEFAULT 0,
                previous_rank INTEGER DEFAULT 0,
                description TEXT,
                extra_data TEXT, -- JSON 확장 필드
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
            """)

            # 2. 메트릭 세부 테이블
            cursor.execute("""
            CREATE TABLE IF NOT EXISTS entity_metrics (
                entity_id TEXT PRIMARY KEY,
                poll_score REAL DEFAULT 50.0,
                news_score REAL DEFAULT 50.0,
                activity_score REAL DEFAULT 50.0,
                approval_score REAL DEFAULT 50.0,
                metrics_json TEXT, -- 추가 커스텀 메트릭
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (entity_id) REFERENCES entities(id) ON DELETE CASCADE
            )
            """)

            # 3. 투표 기록 테이블
            cursor.execute("""
            CREATE TABLE IF NOT EXISTS votes (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                entity_id TEXT NOT NULL,
                vote_type TEXT NOT NULL, -- 'up' or 'down' / 'support' or 'oppose'
                user_ip TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (entity_id) REFERENCES entities(id)
            )
            """)

            # 4. 피드백/댓글 테이블
            cursor.execute("""
            CREATE TABLE IF NOT EXISTS comments (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                entity_id TEXT NOT NULL,
                user_nickname TEXT,
                content TEXT NOT NULL,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (entity_id) REFERENCES entities(id)
            )
            """)
            conn.commit()

    def upsert_entity(self, entity_data: Dict[str, Any]):
        """엔티티 추가 또는 업데이트"""
        extra_data = json.dumps(entity_data.get("extra_data", {}), ensure_ascii=False)
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
            INSERT INTO entities (id, name, name_en, category, subcategory, image_url, total_score, current_rank, previous_rank, description, extra_data)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            ON CONFLICT(id) DO UPDATE SET
                name=excluded.name,
                name_en=excluded.name_en,
                category=excluded.category,
                subcategory=excluded.subcategory,
                image_url=excluded.image_url,
                total_score=excluded.total_score,
                current_rank=excluded.current_rank,
                previous_rank=excluded.previous_rank,
                description=excluded.description,
                extra_data=excluded.extra_data,
                updated_at=CURRENT_TIMESTAMP
            """, (
                entity_data["id"],
                entity_data["name"],
                entity_data.get("name_en", ""),
                entity_data.get("category", ""),
                entity_data.get("subcategory", ""),
                entity_data.get("image_url", ""),
                entity_data.get("total_score", 0.0),
                entity_data.get("current_rank", 0),
                entity_data.get("previous_rank", 0),
                entity_data.get("description", ""),
                extra_data
            ))

            # 메트릭도 저장
            metrics = entity_data.get("metrics", {})
            cursor.execute("""
            INSERT INTO entity_metrics (entity_id, poll_score, news_score, activity_score, approval_score, metrics_json)
            VALUES (?, ?, ?, ?, ?, ?)
            ON CONFLICT(entity_id) DO UPDATE SET
                poll_score=excluded.poll_score,
                news_score=excluded.news_score,
                activity_score=excluded.activity_score,
                approval_score=excluded.approval_score,
                metrics_json=excluded.metrics_json,
                updated_at=CURRENT_TIMESTAMP
            """, (
                entity_data["id"],
                metrics.get("poll_score", 50.0),
                metrics.get("news_score", 50.0),
                metrics.get("activity_score", 50.0),
                metrics.get("approval_score", 50.0),
                json.dumps(metrics, ensure_ascii=False)
            ))
            conn.commit()

    def get_all_entities(self) -> List[Dict[str, Any]]:
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
            SELECT e.*, m.poll_score, m.news_score, m.activity_score, m.approval_score, m.metrics_json
            FROM entities e
            LEFT JOIN entity_metrics m ON e.id = m.entity_id
            ORDER BY e.total_score DESC
            """)
            rows = cursor.fetchall()
            results = []
            for row in rows:
                item = dict(row)
                if item.get("extra_data"):
                    item["extra_data"] = json.loads(item["extra_data"])
                if item.get("metrics_json"):
                    item["metrics"] = json.loads(item["metrics_json"])
                else:
                    item["metrics"] = {
                        "poll_score": item.get("poll_score", 50.0),
                        "news_score": item.get("news_score", 50.0),
                        "activity_score": item.get("activity_score", 50.0),
                        "approval_score": item.get("approval_score", 50.0),
                    }
                results.append(item)
            return results

    def add_vote(self, entity_id: str, vote_type: str, user_ip: str = "127.0.0.1"):
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(
                "INSERT INTO votes (entity_id, vote_type, user_ip) VALUES (?, ?, ?)",
                (entity_id, vote_type, user_ip)
            )
            conn.commit()

    def get_vote_counts(self, entity_id: str) -> Dict[str, int]:
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(
                "SELECT vote_type, COUNT(*) as cnt FROM votes WHERE entity_id = ? GROUP BY vote_type",
                (entity_id,)
            )
            rows = cursor.fetchall()
            return {r["vote_type"]: r["cnt"] for r in rows}
