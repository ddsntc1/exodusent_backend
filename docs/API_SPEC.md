# 투표 API 명세서 (Frontend 전달용)

이 문서는 프론트엔드에서 투표 기능을 정확히 연동하기 위한 상세 명세입니다.

---

## 1) 시스템 개요

- Backend: FastAPI
- DB: MariaDB
- Cache/Fanout: Redis → Backend fanout → WebSocket
- 투표 방식: 익명 투표 + `voterToken` 재사용
- 실시간 업데이트: WebSocket push

---

## 2) 공통 규칙

### 2-1. 익명 토큰(`voterToken`)
- 최초 투표 시 서버가 `voterToken`을 발급해 응답에 포함
- 프론트는 브라우저 저장소(LocalStorage 등)에 저장 후 재요청 시 전달
- 동일 `pollId`에서만 토큰을 재사용

### 2-2. 재투표/취소 규칙
- 동일 `optionId`로 재요청: **취소** (`action = canceled`)
- 다른 `optionId`로 재요청: **변경** (`action = updated`)
- 최초 투표: **생성** (`action = created`)
- 성공 시 항상 `200 OK` + 동일 응답 포맷

### 2-3. 에러 코드
- 400 Bad Request: 비활성 투표
- 404 Not Found: `pollId` 또는 `optionId` 없음
- 422 Unprocessable Entity: 요청 파라미터/타입 오류

---

## 3) REST API

### 3-1. 투표할 항목 조회

GET `/polls/{pollId}`

Path Param:
- `pollId` (number, required)

응답 스키마:
```json
{
  "id": 0,
  "title": "string",
  "description": "string | null",
  "options": [
    {"id": 0, "label": "string"}
  ]
}
```

응답 예시:
```json
{
  "id": 1,
  "title": "점심 메뉴",
  "description": "짜장면 vs 짬뽕",
  "options": [
    {"id": 10, "label": "짜장면"},
    {"id": 11, "label": "짬뽕"}
  ]
}
```

---

### 3-2. 투표 (신규/변경/취소)

POST `/polls/{pollId}/votes`

Path Param:
- `pollId` (number, required)

요청 바디 스키마:
```json
{
  "optionId": 0,
  "voterToken": "string | null"
}
```

요청 예시 (최초 투표, 토큰 없음):
```json
{
  "optionId": 10
}
```

요청 예시 (재투표/취소):
```json
{
  "optionId": 11,
  "voterToken": "550e8400-e29b-41d4-a716-446655440000"
}
```

응답 스키마:
```json
{
  "voteId": 0,
  "pollId": 0,
  "optionId": 0,
  "voterToken": "string",
  "action": "created | updated | canceled"
}
```

응답 예시:
```json
{
  "voteId": 100,
  "pollId": 1,
  "optionId": 11,
  "voterToken": "550e8400-e29b-41d4-a716-446655440000",
  "action": "updated"
}
```

---

### 3-3. 투표 결과 확인

GET `/polls/results`

주의: `pollId` 없는 고정 경로입니다. `/polls/{pollId}`와 혼동 금지.

응답 스키마:
```json
{
  "pollId": 0,
  "totalVotes": 0,
  "results": [
    {"optionId": 0, "label": "string", "count": 0}
  ]
}
```

응답 예시:
```json
{
  "pollId": 1,
  "totalVotes": 120,
  "results": [
    {"optionId": 10, "label": "짜장면", "count": 70},
    {"optionId": 11, "label": "짬뽕", "count": 50}
  ]
}
```

동작 규칙:
- `is_active = 1`인 투표 중 최신(id 기준) 1건을 반환
- 활성 투표가 없으면 404 응답

---

## 4) WebSocket 실시간 집계

WebSocket 연결:
- URL: `ws://{HOST}/ws/polls/{pollId}`
- 프로토콜: 순수 WebSocket

서버 push 이벤트 스키마:
```json
{
  "type": "poll_results_updated",
  "pollId": 0,
  "totalVotes": 0,
  "results": [
    {"optionId": 0, "label": "string", "count": 0}
  ]
}
```

서버 push 이벤트 예시:
```json
{
  "type": "poll_results_updated",
  "pollId": 1,
  "totalVotes": 121,
  "results": [
    {"optionId": 10, "label": "짜장면", "count": 71},
    {"optionId": 11, "label": "짬뽕", "count": 50}
  ]
}
```

클라이언트 처리 권장:
- 초기 화면은 `GET /polls/results`로 렌더링
- 이후 WS 이벤트로 실시간 갱신
- `action` 값은 UI 선택 상태와 동기화에 사용

---

## 5) CORS

- 허용 Origin: `http://localhost:3000`
- 필요 시 추가 Origin 요청 요망
