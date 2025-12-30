# Exodus Backend

초기 실행 기준으로 백엔드 구동 절차를 정리했습니다. 기본값은 `docker-compose.yml` 기준(MariaDB/Redis)과 맞춰져 있습니다.

## 1) Docker Compose 띄우는 방법

```bash
cd ./backend/app
docker compose up -d
```

## 2) uv로 venv 생성, requirements 설치, Alembic 설정

```bash
cd ./backend/app
uv venv
source .venv/bin/activate
uv pip install -r requirements.txt
```

환경변수는 기본값을 사용해도 됩니다. 필요 시 아래 값만 덮어쓰기 합니다.

```bash
export DB_HOST=localhost
export DB_PORT=3306
export DB_NAME=food
export DB_USER=test
export DB_PASSWORD=test1234
export REDIS_URL=redis://localhost:6379/0
```

Alembic 마이그레이션:

```bash
cd ./backend/app
export PYTHONPATH=..
alembic upgrade head
```

새 마이그레이션 생성(필요 시):

```bash
alembic revision --autogenerate -m "your_message"
```

## 3) script 폴더 내 py 스크립트 사용방법

DB가 먼저 떠 있어야 합니다. 기본값 그대로라면 아래처럼 실행합니다.

```bash
cd ./backend/app
python scripts/script1.py
```

DB 접속 정보를 바꿔야 한다면 환경변수를 지정해서 실행합니다.

```bash
DB_HOST=localhost DB_PORT=3306 DB_NAME=food DB_USER=test DB_PASSWORD=test1234 \
  python scripts/script1.py
```

## 4) 백엔드 실행방법

개발 모드 실행:

```bash
cd ./backend/app
export PYTHONPATH=..
uvicorn app.main:app --reload --reload-dir app
```

`--reload-dir`를 지정하면 `mariadb_data`, `redis_data` 변경 감지를 피할 수 있습니다.
