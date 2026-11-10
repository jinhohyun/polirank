"""
PoliRank v3.1 - 매주 자동 무손실 데이터 업데이터 (weekly_updater.py)

파이프라인:
1. 최신 제22대 국회 공공 빅데이터 수집 (collect_all_299 -> enrich_extra_metrics -> collect_news_buzz)
2. 기존 polirank.db 내 유저 참여 데이터(cheer_count 및 comments 테이블 전체)를 100% 보존(Preserve User Data)
3. 신규/변동 의정 스탯, 6대 핵심 축 점수, 재미·화제성 지표(fandom, controversy, hidden_gem) 최신화
4. metadata 테이블 last_updated_at 갱신
"""
import argparse
import json
import os
import sys
import time

CURRENT_DIR = os.path.dirname(os.path.abspath(__file__))
if CURRENT_DIR not in sys.path:
    sys.path.insert(0, CURRENT_DIR)

from collect_all_299 import build_all_members_dataset, SEED_ALL_PATH, SEED_MAIN_PATH
from enrich_extra_metrics import enrich_dataset
from collect_news_buzz import enrich_news_buzz
from seed_data import seed


def run_weekly_update(skip_crawl: bool = False):
    t0 = time.time()
    print("=" * 64)
    print("[*] PoliRank Weekly Auto-Updater 시작 (User Cheer & Comments 100% 무손실 보존)")
    print("=" * 64)

    if not skip_crawl:
        dataset = build_all_members_dataset()
        dataset = enrich_dataset(dataset)
        dataset = enrich_news_buzz(dataset)

        with open(SEED_ALL_PATH, "w", encoding="utf-8") as f:
            json.dump(dataset, f, ensure_ascii=False, indent=2)
        with open(SEED_MAIN_PATH, "w", encoding="utf-8") as f:
            json.dump(dataset, f, ensure_ascii=False, indent=2)
        print(f"[+] 공공데이터 + 뉴스 빅데이터 수집 및 JSON 저장 완료 ({len(dataset.get('members', []))}명)")
    else:
        print("[*] --skip-crawl 지정됨: 기존 seed_data_all.json 기반으로 무손실 DB 동기화만 수행합니다.")

    # 기존 cheer_count & comments 테이블 100% 보존하면서 DB 최신화
    seed(preserve_user_data=True)
    print(f"[+] 주간 무손실 업데이터 완료! 총 소요 시간: {time.time() - t0:.1f}초")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="PoliRank 주간 자동 무손실 업데이터")
    parser.add_argument("--skip-crawl", action="store_true", help="외부 API 수집을 생략하고 로컬 JSON으로 DB만 무손실 갱신")
    args = parser.parse_args()
    run_weekly_update(skip_crawl=args.skip_crawl)
