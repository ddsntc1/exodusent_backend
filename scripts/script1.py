import os
import pymysql

DB_HOST = os.getenv("DB_HOST", "localhost")
DB_PORT = int(os.getenv("DB_PORT", "3306"))
DB_NAME = os.getenv("DB_NAME", "food")
DB_USER = os.getenv("DB_USER", "test")
DB_PASSWORD = os.getenv("DB_PASSWORD", "test1234")

conn = pymysql.connect(
    host=DB_HOST,
    port=DB_PORT,
    user=DB_USER,
    password=DB_PASSWORD,
    db=DB_NAME,
    charset="utf8mb4",
    autocommit=True,
)

with conn.cursor() as cur:
    cur.execute(
        "INSERT INTO polls (title, description, is_active) VALUES (%s, %s, %s)",
        ("점심 메뉴", "짜장면 vs 짬뽕", 1),
    )
    poll_id = cur.lastrowid
    cur.executemany(
        "INSERT INTO poll_options (poll_id, label, sort_order) VALUES (%s, %s, %s)",
        [
            (poll_id, "짜장면", 1),
            (poll_id, "짬뽕", 2),
        ],
    )

conn.close()
print("seed 완료")
