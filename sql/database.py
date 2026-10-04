"""
Database connection adapter with dual-engine support (MySQL 8.0 with SQLite3 fallback).
Provides a unified parameterized query interface and manages schema execution.
"""

import os
import sqlite3
import pymysql
from dotenv import load_dotenv

load_dotenv()

DB_ENGINE = os.getenv("DB_ENGINE", "auto").lower()  # 'mysql', 'sqlite', or 'auto'
MYSQL_HOST = os.getenv("MYSQL_HOST", "localhost")
MYSQL_PORT = int(os.getenv("MYSQL_PORT", "3306"))
MYSQL_USER = os.getenv("MYSQL_USER", "root")
MYSQL_PASSWORD = os.getenv("MYSQL_PASSWORD", "")
MYSQL_DATABASE = os.getenv("MYSQL_DATABASE", "tourism_dmdw")

SQLITE_PATH = os.getenv(
    "SQLITE_PATH",
    os.path.join(os.path.dirname(os.path.dirname(__file__)), "data", "processed", "tourism_dw.db")
)


class DatabaseAdapter:
    def __init__(self):
        self.engine_type = None
        self._detect_and_init_engine()

    def _detect_and_init_engine(self):
        if DB_ENGINE == "sqlite":
            self.engine_type = "sqlite"
            return

        if DB_ENGINE in ("mysql", "auto"):
            try:
                # Test connection to MySQL server
                conn = pymysql.connect(
                    host=MYSQL_HOST,
                    port=MYSQL_PORT,
                    user=MYSQL_USER,
                    password=MYSQL_PASSWORD,
                    connect_timeout=2
                )
                with conn.cursor() as cur:
                    cur.execute(f"CREATE DATABASE IF NOT EXISTS `{MYSQL_DATABASE}` CHARACTER SET utf8mb4;")
                conn.close()
                self.engine_type = "mysql"
                return
            except Exception:
                if DB_ENGINE == "mysql":
                    raise ConnectionError(
                        f"Failed to connect to MySQL at {MYSQL_HOST}:{MYSQL_PORT} with user '{MYSQL_USER}'."
                    )
                # Fallback to sqlite if auto
                self.engine_type = "sqlite"

    def get_connection(self):
        if self.engine_type == "mysql":
            return pymysql.connect(
                host=MYSQL_HOST,
                port=MYSQL_PORT,
                user=MYSQL_USER,
                password=MYSQL_PASSWORD,
                database=MYSQL_DATABASE,
                cursorclass=pymysql.cursors.DictCursor,
                autocommit=True
            )
        else:
            os.makedirs(os.path.dirname(SQLITE_PATH), exist_ok=True)
            conn = sqlite3.connect(SQLITE_PATH)
            conn.row_factory = sqlite3.Row
            conn.execute("PRAGMA foreign_keys = ON;")
            return conn

    def execute_script(self, sql_script):
        conn = self.get_connection()
        try:
            if self.engine_type == "mysql":
                # PyMySQL doesn't support executing entire script at once without split
                statements = [stmt.strip() for stmt in sql_script.split(";") if stmt.strip()]
                with conn.cursor() as cursor:
                    for stmt in statements:
                        # Skip transactions or comments if any
                        cursor.execute(stmt)
            else:
                # For SQLite, adapt MySQL specific syntax
                adapted_sql = self._adapt_mysql_to_sqlite(sql_script)
                conn.executescript(adapted_sql)
                conn.commit()
        finally:
            conn.close()

    def _adapt_mysql_to_sqlite(self, sql):
        lines = []
        for line in sql.split("\n"):
            # Skip MySQL specific syntax
            stripped = line.strip()
            if stripped.startswith("CREATE INDEX") and "WITH ROLLUP" in stripped:
                continue
            line = line.replace("TINYINT(1)", "INTEGER")
            line = line.replace("DECIMAL(9,6)", "REAL")
            line = line.replace("DECIMAL(10,2)", "REAL")
            line = line.replace("DECIMAL(12,2)", "REAL")
            line = line.replace("DECIMAL(4,1)", "REAL")
            line = line.replace("DECIMAL(4,2)", "REAL")
            line = line.replace("DECIMAL(6,4)", "REAL")
            line = line.replace("DECIMAL(8,1)", "REAL")
            line = line.replace("DECIMAL(8,4)", "REAL")
            line = line.replace("AUTO_INCREMENT", "AUTOINCREMENT")
            lines.append(line)
        return "\n".join(lines)

    def fetch_all(self, query, params=None):
        conn = self.get_connection()
        try:
            if self.engine_type == "mysql":
                with conn.cursor() as cur:
                    cur.execute(query, params or ())
                    return cur.fetchall()
            else:
                # Convert %s placeholders to ? for sqlite if needed
                cur = conn.cursor()
                sqlite_query = query.replace("%s", "?")
                cur.execute(sqlite_query, params or ())
                rows = cur.fetchall()
                return [dict(r) for r in rows]
        finally:
            conn.close()

    def fetch_one(self, query, params=None):
        conn = self.get_connection()
        try:
            if self.engine_type == "mysql":
                with conn.cursor() as cur:
                    cur.execute(query, params or ())
                    return cur.fetchone()
            else:
                cur = conn.cursor()
                sqlite_query = query.replace("%s", "?")
                cur.execute(sqlite_query, params or ())
                row = cur.fetchone()
                return dict(row) if row else None
        finally:
            conn.close()

    def execute(self, query, params=None):
        conn = self.get_connection()
        try:
            if self.engine_type == "mysql":
                with conn.cursor() as cur:
                    cur.execute(query, params or ())
                    return cur.rowcount
            else:
                cur = conn.cursor()
                sqlite_query = query.replace("%s", "?")
                cur.execute(sqlite_query, params or ())
                conn.commit()
                return cur.rowcount
        finally:
            conn.close()

    def executemany(self, query, params_list):
        if not params_list:
            return 0
        conn = self.get_connection()
        try:
            if self.engine_type == "mysql":
                with conn.cursor() as cur:
                    cur.executemany(query, params_list)
                    return cur.rowcount
            else:
                cur = conn.cursor()
                sqlite_query = query.replace("%s", "?")
                cur.executemany(sqlite_query, params_list)
                conn.commit()
                return cur.rowcount
        finally:
            conn.close()


# Global database singleton
db = DatabaseAdapter()
