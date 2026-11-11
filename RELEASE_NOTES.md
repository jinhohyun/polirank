# PoliRank (폴리랭크) 릴리즈 노트 (Release Notes)

> **프로젝트명:** PoliRank (국회의원 팩트 데이터 기반 랭킹 & 커뮤니티)  
> **최종 버전:** v1.2.0 Member Staff Directory Release  
> **최종 갱신일:** 2026-11-12  
> **배포 상태:** 제22대 국회의원 299인 보좌진 전수 데이터베이스 구축 & UI 수립 완료  

---

## 🚀 버전별 배포 및 릴리즈 이력

### 📌 v1.2.0 (2026-11-12) - Member Staff Directory Release
- **제22대 국회의원 299인 보좌진 전수 파싱 및 공공데이터 ETL 연동**
  - 열린국회 API `nwvrqwxyaytdsfvhu` 응답 데이터에서 STAFF(4급 보좌관), SECRETARY(5급 비서관), SECRETARY2(6~9급 비서 및 인턴) 자동 정제 및 급수별 맵 구조 구축
  - `collect_all_299.py` 수집기 최신화로 299명 의원별 총 보좌진 수 및 급수별 전체 성명 데이터베이스 저장
- **데이터베이스 스키마 확장 & 백엔드 REST API 연동**
  - SQLite `members` 테이블에 `staff_total_count`, `staff_advisors_4th_json`, `staff_secretaries_5th_json`, `staff_assistants_6to9th_json` 컬럼 추가 및 마이그레이션 적용
  - `/api/members` 및 `/api/members/{id}` 응답에 `staff_info` 객체 바인딩
- **국회의원 카드 & 상세 모달 UI/UX 갱신**
  - 국회의원 메인 카드에 `보좌진 N명` 배지 직관 표기
  - 국회의원 상세 모달 내 `보좌진 명단 보기` 인터랙티브 토글 버튼 및 접이식 슬라이드 패널 탑재
  - **급수별 명단 디자인**: 4급 보좌관(보라), 5급 비서관(파랑), 6~9급/인턴(회색) 구분 배지로 성명이 빠짐없이 시각화되어 표시
- **단위 및 통합 검증 테스트 강화**
  - `test_polirank.py` 내 `test_13_member_staff_info` 테스트 케이스 추가 및 13개 테스트 전원 통과 (OK)

---

### 📌 v1.1.0 (2026-11-10) - Advanced MVP Release
- **제22대 국회의원 299명 전수 데이터 수집 및 DB화 완료**
  - 국회 공공데이터 API 연동 파이프라인(`collect_all_299.py`) 구축
  - SQLite 마스터 데이터베이스 (`polirank.db`) 및 시드 데이터(`seed_data_all.json`) 구축
- **6대 정량 지표 스코어링 엔진(PoliScore v1.1) 도입**
  - 기존 4개 지표(입법, 가결, 출석, 세미나)에서 **전자표결 참여율(15%)** 및 **속기록 발언력(10%)** 지표 추가
  - 100점 만점 기준 6대 축 레이더 차트(Chart.js) 시각화 및 S+ ~ C 등급 티어 뱃지 부여
- **3D 인터랙티브 카드 & 아바타/실사진 플립(Flip) 기능**
  - 캐리커쳐 아바타 ➔ 클릭 시 3D 회전 애니메이션과 함께 국회 공식 사진으로 전환
- **자동화 파이프라인 (GitHub Actions)**
  - 매주 월요일 00:00 KST 공공데이터 자동 동기화 워크플로우(`.github/workflows/weekly_update.yml`) 적용
- **시민 참여 & 후원 연계**
  - 실시간 1클릭 하트 응원 기능 및 한줄 토론 피드
  - 중앙선관위 `give.go.kr` 공식 아웃링크 및 계좌 1초 복사 기능

---

### 📌 v1.0.0 (2026-11-08) - Initial MVP Prototype
- **FastAPI 백엔드 & TailwindCSS 프론트엔드 기본 구조 정립**
- 32명 주요 국회의원 파일럿 스코어링 및 인터랙티브 웹 UI 탑재
- 기본 4대 정량 지표(입법 실적, 가결률, 본회의/상임위 출석률, 정책 세미나) 산출 알고리즘 적용

---

## 🛠️ 주요 시스템 구성 요소

| 구분 | 파일 경로 | 설명 |
| :--- | :--- | :--- |
| **메인 웹 애플리케이션** | `app.py`, `run.py` | FastAPI 기반 RESTful API 및 정적 Web 서버 |
| **데이터베이스** | `database.py`, `polirank.db` | SQLite 마스터 DB 및 ORM/SQL 레이어 |
| **스코어링 엔진** | `scoring.py` | 6대 팩트 지표 산출 및 티어 계산 알고리즘 |
| **전수 데이터 수집기** | `collect_all_299.py` | 제22대 국회의원 299명 공공데이터 자동 ETL 스크립트 |
| **자동 갱신 워크플로우** | `.github/workflows/weekly_update.yml` | GitHub Actions 기반 주간 자동 데이터 파이프라인 |
| **시각화 프론트엔드** | `static/index.html`, `static/app.js` | 6축 레이더 차트, 카드 플립, 하트 피드 UI |

---

## 🔗 연계 관련 문서
- **[상세 기술 및 알고리즘 명세서]**: `01_Biz_Projects/polirank_mvp/SYSTEM_SPECIFICATION.md`
- **[마스터 사업계획서]**: `01_Biz_Projects/판타지정치_사업계획서.md`
