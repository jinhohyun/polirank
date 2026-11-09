"""
PoliRank MVP - 원클릭 서버 구동 스크립트
"""
import os
import sys
import uvicorn

# 현재 폴더 경로 설정
CURRENT_DIR = os.path.dirname(os.path.abspath(__file__))
if CURRENT_DIR not in sys.path:
    sys.path.insert(0, CURRENT_DIR)

# DB 초기화 및 시딩 확인
from seed_data import seed
from database import get_connection

def ensure_initialized():
    conn = get_connection()
    c = conn.cursor()
    try:
        c.execute("SELECT COUNT(*) as cnt FROM members")
        cnt = c.fetchone()["cnt"]
        if cnt == 0:
            print("[*] Empty database detected. Seeding 32 members data...")
            seed()
    except Exception:
        print("[*] Database not initialized. Running seed...")
        seed()
    finally:
        conn.close()

if __name__ == "__main__":
    ensure_initialized()
    port = 8000
    print("\n" + "="*60)
    print("🏛️  PoliRank (폴리랭크) - 대한민국 국회의원 객관적 랭킹 & 커뮤니티")
    print(f"🌐  웹 브라우저 접속 주소: http://localhost:{port}")
    print(f"📖  REST API 문서: http://localhost:{port}/docs")
    print("="*60 + "\n")
    uvicorn.run("app:app", host="0.0.0.0", port=port, reload=False)
