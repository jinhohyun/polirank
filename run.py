"""
PoliRank MVP - 원클릭 서버 구동 스크립트
"""
import os
import sys
import socket
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
        if cnt == 0 or (cnt < 200 and os.path.exists(os.path.join(CURRENT_DIR, "seed_data_all.json"))):
            print(f"[*] Database has {cnt} members. Seeding full 299-member data...")
            seed()
    except Exception:
        print("[*] Database not initialized. Running seed...")
        seed()
    finally:
        conn.close()

def find_available_port(candidates=(8000, 8500, 8888, 9000, 5000)) -> int:
    """Windows 예약 포트(WinError 10013)나 충돌 포트를 자동 회피하여 가용 포트를 반환합니다."""
    env_port = os.environ.get("PORT")
    if env_port:
        return int(env_port)
    for port in candidates:
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
            try:
                s.bind(("0.0.0.0", port))
                return port
            except OSError:
                continue
    return 8500


if __name__ == "__main__":
    ensure_initialized()
    port = find_available_port()
    print("\n" + "="*60)
    print("🏛️  PoliRank (폴리랭크) - 대한민국 국회의원 객관적 랭킹 & 커뮤니티")
    print(f"🌐  웹 브라우저 접속 주소: http://localhost:{port}")
    print(f"📖  REST API 문서: http://localhost:{port}/docs")
    print("="*60 + "\n")
    uvicorn.run("app:app", host="0.0.0.0", port=port, reload=False)
