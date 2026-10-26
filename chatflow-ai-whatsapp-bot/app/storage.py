"""SQLite-backed inbound message queue, basic customer preferences and chat history.

Run one worker process with SQLite. For large deployments switch to a hosted queue
and a managed database. Processing is at-least-once, not exactly-once.
"""
import sqlite3
import time
from pathlib import Path
from typing import Optional


class Storage:
    def __init__(self, path: str):
        self.path = path

    def connect(self):
        connection = sqlite3.connect(self.path, timeout=10)
        connection.row_factory = sqlite3.Row
        connection.execute('PRAGMA busy_timeout=10000')
        connection.execute('PRAGMA journal_mode=WAL')
        return connection

    def initialize(self):
        Path(self.path).parent.mkdir(parents=True, exist_ok=True)
        with self.connect() as db:
            db.executescript('''
                CREATE TABLE IF NOT EXISTS inbox (
                    id TEXT PRIMARY KEY,
                    sender TEXT NOT NULL,
                    body TEXT NOT NULL,
                    received_ts INTEGER NOT NULL,
                    status TEXT NOT NULL DEFAULT 'pending',
                    attempts INTEGER NOT NULL DEFAULT 0,
                    available_at REAL NOT NULL DEFAULT 0,
                    last_error TEXT,
                    created_at REAL NOT NULL
                );
                CREATE INDEX IF NOT EXISTS idx_inbox_queue
                  ON inbox(status, available_at, created_at);
                CREATE TABLE IF NOT EXISTS chat_history (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    sender TEXT NOT NULL,
                    role TEXT NOT NULL,
                    content TEXT NOT NULL,
                    created_at REAL NOT NULL
                );
                CREATE INDEX IF NOT EXISTS idx_history_sender
                  ON chat_history(sender, id);
                CREATE TABLE IF NOT EXISTS preferences (
                    sender TEXT PRIMARY KEY,
                    opted_out INTEGER NOT NULL DEFAULT 0,
                    paused INTEGER NOT NULL DEFAULT 0
                );
            ''')
            # If the server stopped during processing, replay the message.
            db.execute("UPDATE inbox SET status='retry' WHERE status='processing'")

    def enqueue(self, message_id: str, sender: str, body: str, received_ts: int):
        with self.connect() as db:
            result = db.execute('''
                INSERT OR IGNORE INTO inbox(id, sender, body, received_ts, created_at)
                VALUES(?, ?, ?, ?, ?)
            ''', (message_id, sender, body, received_ts, time.time()))
            return result.rowcount == 1

    def claim_next(self) -> Optional[dict]:
        with self.connect() as db:
            db.execute('BEGIN IMMEDIATE')
            row = db.execute('''
                SELECT * FROM inbox
                WHERE status IN ('pending', 'retry') AND available_at <= ?
                ORDER BY created_at, rowid LIMIT 1
            ''', (time.time(),)).fetchone()
            if row is None:
                return None
            db.execute("UPDATE inbox SET status='processing', attempts=attempts+1 WHERE id=?", (row['id'],))
            return dict(row) | {'attempts': row['attempts'] + 1}

    def finish(self, message_id: str, status: str = 'done'):
        with self.connect() as db:
            db.execute('UPDATE inbox SET status=?, last_error=NULL WHERE id=?', (status, message_id))

    def fail(self, message_id: str, attempts: int, reason: str, permanent: bool = False):
        status = 'failed' if permanent or attempts >= 5 else 'retry'
        delay = min(5 * (2 ** max(0, attempts - 1)), 300)
        with self.connect() as db:
            db.execute('''UPDATE inbox
                SET status=?, available_at=?, last_error=? WHERE id=?
            ''', (status, time.time() + delay, reason[:500], message_id))

    def preferences(self, sender: str):
        with self.connect() as db:
            row = db.execute('SELECT * FROM preferences WHERE sender=?', (sender,)).fetchone()
        return dict(row) if row else {'opted_out': 0, 'paused': 0}

    def set_preferences(self, sender: str, *, opted_out=None, paused=None):
        current = self.preferences(sender)
        if opted_out is None:
            opted_out = current['opted_out']
        if paused is None:
            paused = current['paused']
        with self.connect() as db:
            db.execute('''INSERT INTO preferences(sender, opted_out, paused)
                VALUES(?, ?, ?) ON CONFLICT(sender) DO UPDATE SET
                opted_out=excluded.opted_out, paused=excluded.paused''',
                (sender, int(opted_out), int(paused)))

    def history(self, sender: str, limit: int = 10):
        with self.connect() as db:
            rows = db.execute('''SELECT role, content FROM chat_history WHERE sender=?
                ORDER BY id DESC LIMIT ?''', (sender, limit)).fetchall()
        return [dict(row) for row in reversed(rows)]

    def append_exchange(self, sender: str, user_message: str, reply: str):
        now = time.time()
        with self.connect() as db:
            db.executemany('''INSERT INTO chat_history(sender, role, content, created_at)
                VALUES(?, ?, ?, ?)''', [
                (sender, 'user', user_message[:2000], now),
                (sender, 'assistant', reply[:4096], now),
            ])

    def prune(self, retention_days: int):
        cutoff = time.time() - max(1, retention_days) * 86400
        with self.connect() as db:
            db.execute('DELETE FROM chat_history WHERE created_at < ?', (cutoff,))
            db.execute("DELETE FROM inbox WHERE created_at < ? AND status IN ('done','skipped','failed')", (cutoff,))
