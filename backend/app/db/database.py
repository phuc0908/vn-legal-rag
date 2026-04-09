import os
import pymysql
import pymysql.cursors
from contextlib import contextmanager
from dbutils.pooled_db import PooledDB

DB_CONFIG = {
    "host":     os.getenv("DB_HOST", "localhost"),
    "port":     int(os.getenv("DB_PORT", "3307")),
    "user":     os.getenv("DB_USER", "root"),
    "password": os.getenv("DB_PASSWORD", "123456789"),
    "database": os.getenv("DB_NAME", "law"),
    "charset":  "utf8mb4",
    "cursorclass": pymysql.cursors.DictCursor,
}

_pool = None


def _get_pool():
    global _pool
    if _pool is None:
        _pool = PooledDB(
            creator=pymysql,
            mincached=2,
            maxcached=10,
            maxconnections=20,
            blocking=True,
            **DB_CONFIG
        )
    return _pool


def get_connection():
    return _get_pool().connection()


@contextmanager
def get_db():
    conn = get_connection()
    try:
        yield conn
    finally:
        conn.close()


def query_one(sql: str, params=None):
    with get_db() as conn:
        with conn.cursor() as cur:
            cur.execute(sql, params or ())
            return cur.fetchone()


def query_all(sql: str, params=None):
    with get_db() as conn:
        with conn.cursor() as cur:
            cur.execute(sql, params or ())
            return cur.fetchall()
