# 진행사항 정리

본 문서는 현재 대화에서 진행된 작업과 상태를 요약한 것입니다.

---

## 1) 구현/설계 완료 사항

- 투표 API 설계(익명 투표, 재투표/취소 규칙, Redis 캐시, WS fanout)
- FastAPI 백엔드 구현(REST + WebSocket)
- MariaDB/Redis Docker Compose 구성
- Alembic 마이그레이션 구성 및 초기 테이블 생성 스크립트
- 프론트 전달용 API 문서 작성(`API.md`, `API_SPEC.md`)
- 시드 데이터 스크립트(짜장면 vs 짬뽕)
- CORS 허용(`http://localhost:3000`)

---

## 2) 주요 파일 목록

- `docker-compose.yml` (MariaDB + Redis)
- `requirements.txt` (FastAPI, SQLAlchemy, Redis, Alembic 등)
- `app/main.py` (API/WS 엔드포인트, Redis 집계)
- `app/models.py` (DB 모델)
- `app/schemas.py` (요청/응답 스키마)
- `app/database.py`, `app/config.py`, `app/redis_client.py`, `app/ws.py`
- `alembic/` + `alembic.ini` (마이그레이션)
- `API.md`, `API_SPEC.md` (프론트 전달용 문서)
- `scripts/seed_poll_jjajang_jjambbong.sql` (시드)

---

## 3) API 동작 요약

- `GET /polls/{pollId}`: 투표 항목 조회
- `POST /polls/{pollId}/votes`: 투표/변경/취소
  - 동일 옵션 재요청: 취소(`action=canceled`)
  - 다른 옵션 재요청: 변경(`action=updated`)
- `GET /polls/results`: 활성 투표(최신 id 1건) 결과 반환
- `WS /ws/polls/{pollId}`: 실시간 결과 push

---

## 4) 마이그레이션 상태

- `0000_create_tables`: polls, poll_options, votes 생성
- `0001_remove_poll_dates`: 날짜 컬럼 제거 및 인덱스 정리

주의:
- `polls` 테이블이 없으면 `0001` 단독 실행 시 실패하므로 `upgrade head` 권장

---

## 5) 실행 관련 확인사항

- `uvicorn` 리로드 사용 시 `mariadb_data` 권한 문제 발생 가능
  - 권장: `uvicorn app.main:app --reload --reload-dir app`
  - 또는 `--reload-exclude`로 `mariadb_data`, `redis_data` 제외

- `app` 디렉토리에서 실행 시 `PYTHONPATH` 설정 필요
  - 예: `PYTHONPATH=.. uvicorn main:app --reload --reload-dir .`

---

## 6) 남은/추가 결정사항

- WebSocket 인증 방식(무인증/토큰 등) 필요 시 확정
- 프로덕션 배포 시 CORS 허용 Origin 확장 여부
- 마이그레이션 자동화(스크립트/CI) 여부
