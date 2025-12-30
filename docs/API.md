# 투표 API 가이드 (Backend → Frontend)

이 문서는 프론트엔드에서 투표 기능을 연동하기 위한 API/WS 사용 방법을 정리한 안내서입니다.

---

## 1) 개요

- 스택: FastAPI + MariaDB + Redis + WebSocket
- 투표 방식: 익명 투표
- 재투표/취소 규칙:
  - 최초 투표 시 서버가 `voterToken` 발급
  - 이후 동일 `pollId`에 같은 `optionId`로 요청하면 취소
  - 다른 `optionId`로 요청하면 변경
  - 성공 응답은 항상 200 OK + 동일 포맷

---

## 2) REST API

중요: `/polls/results`는 **poll_id 없이** 호출하는 고정 경로입니다.  
`/polls/{pollId}` 보다 먼저 라우팅되며, `pollId`에 `results` 문자열을 넣으면 400 에러가 납니다.

### 2-1. 투표할 항목 조회

GET `/polls/{pollId}` (path param: number)

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
  "description": "오늘 점심",
  "options": [
    {"id": 10, "label": "한식"},
    {"id": 11, "label": "양식"}
  ]
}
```

### 2-2. 투표 (신규/변경/취소)

POST `/polls/{pollId}/votes` (path param: number)

요청 바디 스키마:
```json
{
  "optionId": 0,
  "voterToken": "string | null"
}
```

요청 바디 예시:
```json
{
  "optionId": 10,
  "voterToken": "550e8400-e29b-41d4-a716-446655440000"
}
```

요청 규칙:
- 최초 투표 시 `voterToken`을 보내지 않아도 됨
- 서버가 응답에 `voterToken`을 내려주므로, 클라이언트 저장 필요
- 동일 `optionId`로 재요청 시 취소
- 다른 `optionId`로 재요청 시 변경

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
  "optionId": 10,
  "voterToken": "550e8400-e29b-41d4-a716-446655440000",
  "action": "created"
}
```

action 값:
- `created`: 신규 투표
- `updated`: 투표 변경
- `canceled`: 투표 취소

에러:
- 400 Bad Request (비활성 투표)
- 404 Not Found (pollId 또는 optionId 없음)

### 2-3. 투표 결과 확인

GET `/polls/results`

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
    {"optionId": 10, "label": "한식", "count": 70},
    {"optionId": 11, "label": "양식", "count": 50}
  ]
}
```

동작 규칙:
- 서버는 현재 활성 상태(is_active=1)인 투표 중 가장 최신(id 기준) 1건을 선택해서 반환
- 활성 투표가 없으면 404 응답

---

## 3) WebSocket 실시간 집계

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
    {"optionId": 10, "label": "한식", "count": 71},
    {"optionId": 11, "label": "양식", "count": 50}
  ]
}
```

클라이언트 처리:
- WS 연결 후 서버가 push 해주는 결과를 그대로 렌더링
- 투표 결과 화면은 `GET /polls/results`로 초기화 후, WS 이벤트로 실시간 갱신

---

## 4) 프론트 구현 팁

- `voterToken`은 브라우저 저장소(LocalStorage/IndexedDB 등)에 저장 권장
- 동일한 `pollId`에 대해 토큰 재사용
- 투표 후 응답의 `action` 값에 따라 UI 처리:
  - `created`: 선택 상태 유지
  - `updated`: 선택 항목 변경
  - `canceled`: 선택 해제
