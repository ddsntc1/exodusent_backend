## 투표 API 설계 (MariaDB + Redis + WebSocket)

아래는 MariaDB 기준 스키마입니다. 익명 투표를 기본으로 하고, 필요 시 사용자 테이블을 연동할 수 있게 확장 포인트를 둡니다.  
실시간 집계는 Redis에 캐시하고, WebSocket으로 구독 중인 사용자에게 push 합니다.

### 1) 테이블 설계

#### polls
- id (bigint unsigned, PK, auto_increment)
- title (varchar(200), not null)
- description (text, null)
- is_active (tinyint(1), not null, default 1)
- created_at (datetime, not null, default current_timestamp)
- updated_at (datetime, not null, default current_timestamp on update current_timestamp)

인덱스
- idx_polls_active (is_active)

#### poll_options
- id (bigint unsigned, PK, auto_increment)
- poll_id (bigint unsigned, not null, FK -> polls.id)
- label (varchar(200), not null)
- sort_order (int, not null, default 0)
- created_at (datetime, not null, default current_timestamp)

인덱스
- idx_poll_options_poll (poll_id, sort_order)

#### votes
- id (bigint unsigned, PK, auto_increment)
- poll_id (bigint unsigned, not null, FK -> polls.id)
- option_id (bigint unsigned, not null, FK -> poll_options.id)
- voter_token (char(36), not null) -- 익명 토큰 (재투표/철회용)
- created_at (datetime, not null, default current_timestamp)

제약/인덱스
- uniq_vote_per_poll (poll_id, voter_token) unique
- idx_votes_poll (poll_id)
- idx_votes_option (option_id)

메모
- 익명 토큰은 서버에서 발급하고, 클라이언트가 저장해 재투표 시 동일 토큰을 전달.
- 다중 선택 투표가 필요하면 uniq 제약을 (poll_id, voter_token, option_id) 로 조정.
- MariaDB에서 FK/인덱스 성능을 위해 InnoDB + 적절한 FK 인덱스 유지.

---

### 1-1) MariaDB DDL 예시

CREATE TABLE polls (
  id BIGINT UNSIGNED PRIMARY KEY AUTO_INCREMENT,
  title VARCHAR(200) NOT NULL,
  description TEXT NULL,
  is_active TINYINT(1) NOT NULL DEFAULT 1,
  created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
  updated_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
  INDEX idx_polls_active (is_active)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

CREATE TABLE poll_options (
  id BIGINT UNSIGNED PRIMARY KEY AUTO_INCREMENT,
  poll_id BIGINT UNSIGNED NOT NULL,
  label VARCHAR(200) NOT NULL,
  sort_order INT NOT NULL DEFAULT 0,
  created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
  INDEX idx_poll_options_poll (poll_id, sort_order),
  CONSTRAINT fk_poll_options_poll_id FOREIGN KEY (poll_id) REFERENCES polls(id)
    ON DELETE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

CREATE TABLE votes (
  id BIGINT UNSIGNED PRIMARY KEY AUTO_INCREMENT,
  poll_id BIGINT UNSIGNED NOT NULL,
  option_id BIGINT UNSIGNED NOT NULL,
  voter_token CHAR(36) NOT NULL,
  created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
  UNIQUE KEY uniq_vote_per_poll (poll_id, voter_token),
  INDEX idx_votes_poll (poll_id),
  INDEX idx_votes_option (option_id),
  CONSTRAINT fk_votes_poll_id FOREIGN KEY (poll_id) REFERENCES polls(id)
    ON DELETE CASCADE,
  CONSTRAINT fk_votes_option_id FOREIGN KEY (option_id) REFERENCES poll_options(id)
    ON DELETE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

---

### 2) API 개요 (요청하신 3가지)

#### 1. 투표할 항목 조회
GET /polls/{pollId}
응답 예시:
{
  "id": 1,
  "title": "점심 메뉴",
  "description": "오늘 점심",
  "options": [
    {"id": 10, "label": "한식"},
    {"id": 11, "label": "양식"}
  ]
}

#### 2. 투표
POST /polls/{pollId}/votes
요청 예시 (첫 투표, 토큰 없음):
{
  "optionId": 10
}

요청 예시 (재투표/취소):
{
  "optionId": 10,
  "voterToken": "550e8400-e29b-41d4-a716-446655440000"
}

성공 응답:
201 Created
{
  "voteId": 100,
  "pollId": 1,
  "optionId": 10,
  "voterToken": "550e8400-e29b-41d4-a716-446655440000",
  "action": "created"
}

에러:
- 400 Bad Request (옵션 불일치)
- 404 Not Found (pollId 또는 optionId 없음)

#### 2-1) 재투표/철회 규칙
- 최초 투표 시 서버가 voterToken 발급 (UUID 권장) 후 응답에 포함
- 이후 동일 pollId에 투표 요청 시 voterToken을 전달하면 기존 투표를 찾아 처리
- 기존 optionId와 동일한 값으로 재요청하면 "취소"로 처리
- 취소 시: votes 행 삭제
- 다른 optionId로 재요청하면 "변경"으로 처리
- 변경 시: votes 행의 option_id 업데이트
 - 응답에 action 필드 추가 권장: created | updated | canceled

#### 3. 투표 결과 확인
GET /polls/{pollId}/results
응답 예시:
{
  "pollId": 1,
  "totalVotes": 120,
  "results": [
    {"optionId": 10, "label": "한식", "count": 70},
    {"optionId": 11, "label": "양식", "count": 50}
  ]
}

---

### 3) Redis + WebSocket 실시간 집계 (순수 WS)

#### Redis 키 설계
- poll:{pollId}:total -> int (전체 투표수)
- poll:{pollId}:options -> hash (optionId => count)
- poll:{pollId}:updated_at -> timestamp (optional, 캐시 갱신 시각)

#### 집계 흐름
1) 투표 POST 성공 시:
   - 신규 토큰이면 votes insert
   - 기존 토큰:
     - 동일 optionId면 취소: votes delete
     - 다른 optionId면 변경: votes update
   - Redis 갱신:
     - 신규: option +1, total +1
     - 변경: 이전 option -1, 신규 option +1, total 변화 없음
     - 취소: option -1, total -1
   - WebSocket으로 poll:{pollId} 채널에 갱신 이벤트 broadcast
2) 결과 조회 GET /polls/{pollId}/results:
   - Redis 캐시가 있으면 캐시 기반 응답
   - 없으면 DB 집계 후 Redis에 채우고 응답

#### WebSocket 이벤트 예시
채널: poll:{pollId}
payload:
{
  "type": "poll_results_updated",
  "pollId": 1,
  "totalVotes": 121,
  "results": [
    {"optionId": 10, "label": "한식", "count": 71},
    {"optionId": 11, "label": "양식", "count": 50}
  ]
}

---

다음 확인이 필요합니다:
1) WebSocket 인증/구독 방식은 어떻게 할까요? (예: 쿼리스트링 토큰, 헤더, 무인증)
2) 취소 시에도 200 OK로 동일 응답 포맷을 줄까요, 아니면 별도 타입을 줄까요?

원하시면 위 스키마를 기반으로 실제 DDL과 API 구현 코드까지 이어서 진행하겠습니다.
