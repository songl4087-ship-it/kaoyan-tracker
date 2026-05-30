import os
import sqlite3
from datetime import date, timedelta

DATABASE_URL = os.environ.get('DATABASE_URL')

def get_db():
    if DATABASE_URL:
        import psycopg2
        import psycopg2.extras
        conn = psycopg2.connect(DATABASE_URL)
        conn.autocommit = False
        return conn
    else:
        db_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'data.db')
        conn = sqlite3.connect(db_path)
        conn.row_factory = sqlite3.Row
        conn.execute("PRAGMA foreign_keys = ON")
        return conn


def _placeholder():
    return '%s' if DATABASE_URL else '?'


def _dict_row(cursor, row_or_none):
    if row_or_none is None:
        return None
    if DATABASE_URL:
        columns = [desc[0] for desc in cursor.description]
        return dict(zip(columns, row_or_none))
    else:
        return dict(row_or_none)


def _fetch_one(conn, sql, params=()):
    p = sql.replace('?', '%s') if DATABASE_URL else sql
    cur = conn.cursor()
    cur.execute(p, params)
    row = cur.fetchone()
    return _dict_row(cur, row)


def _fetch_all(conn, sql, params=()):
    p = sql.replace('?', '%s') if DATABASE_URL else sql
    cur = conn.cursor()
    cur.execute(p, params)
    rows = cur.fetchall()
    if DATABASE_URL:
        columns = [desc[0] for desc in cur.description]
        return [dict(zip(columns, row)) for row in rows]
    else:
        return [dict(row) for row in rows]


def _execute(conn, sql, params=()):
    p = sql.replace('?', '%s') if DATABASE_URL else sql
    cur = conn.cursor()
    cur.execute(p, params)
    return cur


def init_db():
    conn = get_db()
    cur = conn.cursor()
    if DATABASE_URL:
        cur.execute('''
            CREATE TABLE IF NOT EXISTS tasks (
                id SERIAL PRIMARY KEY,
                name TEXT NOT NULL,
                unit TEXT NOT NULL DEFAULT '题',
                total INTEGER NOT NULL,
                completed INTEGER NOT NULL DEFAULT 0,
                start_date TEXT NOT NULL,
                deadline TEXT NOT NULL,
                created_at TEXT NOT NULL DEFAULT (TO_CHAR(NOW(), 'YYYY-MM-DD HH24:MI:SS'))
            )
        ''')
        cur.execute('''
            CREATE TABLE IF NOT EXISTS daily_logs (
                id SERIAL PRIMARY KEY,
                task_id INTEGER NOT NULL REFERENCES tasks(id) ON DELETE CASCADE,
                date TEXT NOT NULL,
                planned INTEGER NOT NULL DEFAULT 0,
                actual INTEGER,
                is_rest_day INTEGER NOT NULL DEFAULT 0,
                UNIQUE(task_id, date)
            )
        ''')
        cur.execute('''
            CREATE TABLE IF NOT EXISTS weekly_rests (
                id SERIAL PRIMARY KEY,
                week_start TEXT NOT NULL UNIQUE,
                rest_date TEXT NOT NULL
            )
        ''')
        conn.commit()
    else:
        cur.executescript('''
            CREATE TABLE IF NOT EXISTS tasks (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                name TEXT NOT NULL,
                unit TEXT NOT NULL DEFAULT '题',
                total INTEGER NOT NULL,
                completed INTEGER NOT NULL DEFAULT 0,
                start_date TEXT NOT NULL,
                deadline TEXT NOT NULL,
                created_at TEXT NOT NULL DEFAULT (datetime('now', 'localtime'))
            );
            CREATE TABLE IF NOT EXISTS daily_logs (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                task_id INTEGER NOT NULL,
                date TEXT NOT NULL,
                planned INTEGER NOT NULL DEFAULT 0,
                actual INTEGER,
                is_rest_day INTEGER NOT NULL DEFAULT 0,
                FOREIGN KEY (task_id) REFERENCES tasks(id) ON DELETE CASCADE,
                UNIQUE(task_id, date)
            );
            CREATE TABLE IF NOT EXISTS weekly_rests (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                week_start TEXT NOT NULL UNIQUE,
                rest_date TEXT NOT NULL
            );
        ''')
        conn.commit()
    conn.close()


def create_task(name, unit, total, start_date, deadline):
    conn = get_db()
    if DATABASE_URL:
        cur = _execute(conn,
            'INSERT INTO tasks (name, unit, total, start_date, deadline) VALUES (?, ?, ?, ?, ?) RETURNING id',
            (name, unit, total, start_date, deadline))
        task_id = cur.fetchone()[0]
    else:
        cur = _execute(conn,
            'INSERT INTO tasks (name, unit, total, start_date, deadline) VALUES (?, ?, ?, ?, ?)',
            (name, unit, total, start_date, deadline))
        task_id = cur.lastrowid
    conn.commit()
    conn.close()
    return task_id


def get_all_tasks():
    conn = get_db()
    tasks = _fetch_all(conn, 'SELECT * FROM tasks ORDER BY deadline')
    conn.close()
    return tasks


def get_task(task_id):
    conn = get_db()
    task = _fetch_one(conn, 'SELECT * FROM tasks WHERE id = ?', (task_id,))
    conn.close()
    return task


def delete_task(task_id):
    conn = get_db()
    _execute(conn, 'DELETE FROM tasks WHERE id = ?', (task_id,))
    conn.commit()
    conn.close()


def checkin(task_id, date_str, actual):
    conn = get_db()
    if DATABASE_URL:
        _execute(conn, '''
            INSERT INTO daily_logs (task_id, date, planned, actual)
            VALUES (?, ?, 0, ?)
            ON CONFLICT(task_id, date) DO UPDATE SET actual = EXCLUDED.actual
        ''', (task_id, date_str, actual))
    else:
        _execute(conn, '''
            INSERT INTO daily_logs (task_id, date, planned, actual)
            VALUES (?, ?, 0, ?)
            ON CONFLICT(task_id, date) DO UPDATE SET actual = ?
        ''', (task_id, date_str, actual, actual))

    row = _fetch_one(conn,
        'SELECT COALESCE(SUM(actual), 0) as total_done FROM daily_logs WHERE task_id = ? AND actual IS NOT NULL',
        (task_id,))
    if row:
        _execute(conn, 'UPDATE tasks SET completed = ? WHERE id = ?', (row['total_done'], task_id))
    conn.commit()
    conn.close()


def get_daily_log(task_id, date_str):
    conn = get_db()
    log = _fetch_one(conn,
        'SELECT * FROM daily_logs WHERE task_id = ? AND date = ?',
        (task_id, date_str))
    conn.close()
    return log


def get_task_logs(task_id):
    conn = get_db()
    logs = _fetch_all(conn,
        'SELECT * FROM daily_logs WHERE task_id = ? ORDER BY date DESC',
        (task_id,))
    conn.close()
    return logs


def set_rest_day(date_str):
    d = date.fromisoformat(date_str)
    week_start = (d - timedelta(days=d.weekday())).isoformat()
    conn = get_db()
    if DATABASE_URL:
        _execute(conn, '''
            INSERT INTO weekly_rests (week_start, rest_date)
            VALUES (?, ?)
            ON CONFLICT(week_start) DO UPDATE SET rest_date = EXCLUDED.rest_date
        ''', (week_start, date_str))
    else:
        _execute(conn, '''
            INSERT INTO weekly_rests (week_start, rest_date)
            VALUES (?, ?)
            ON CONFLICT(week_start) DO UPDATE SET rest_date = ?
        ''', (week_start, date_str, date_str))
    conn.commit()
    conn.close()


def get_rest_days():
    conn = get_db()
    rests = _fetch_all(conn, 'SELECT * FROM weekly_rests')
    conn.close()
    return rests


def is_rest_day(date_str):
    conn = get_db()
    rest = _fetch_one(conn,
        'SELECT * FROM weekly_rests WHERE rest_date = ?', (date_str,))
    conn.close()
    return rest is not None


def get_week_rest(week_start):
    conn = get_db()
    rest = _fetch_one(conn,
        'SELECT * FROM weekly_rests WHERE week_start = ?', (week_start,))
    conn.close()
    return rest
