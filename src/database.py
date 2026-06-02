import sqlite3
from contextlib import contextmanager
from config import DATABASE_PATH

SCHEMA = """
CREATE TABLE IF NOT EXISTS processed_emails (
    id TEXT PRIMARY KEY,
    from_address TEXT,
    from_name TEXT,
    subject TEXT,
    received_at TEXT,
    body_preview TEXT,
    category TEXT,
    urgency INTEGER,
    summary TEXT,
    customer_id TEXT,
    is_vip INTEGER DEFAULT 0,
    is_blocklist INTEGER DEFAULT 0,
    animal_type TEXT,
    address TEXT,
    phone_number TEXT,
    suggested_action TEXT,
    draft_response TEXT,
    requires_follow_up INTEGER DEFAULT 0,
    follow_up_hours INTEGER,
    skye_notes TEXT,
    status TEXT DEFAULT 'pending',
    processed_at TEXT DEFAULT (datetime('now'))
);

CREATE TABLE IF NOT EXISTS follow_ups (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    email_id TEXT REFERENCES processed_emails(id),
    description TEXT,
    due_at TEXT,
    priority INTEGER DEFAULT 3,
    status TEXT DEFAULT 'open',
    completed_at TEXT
);
"""


@contextmanager
def get_db():
    conn = sqlite3.connect(DATABASE_PATH)
    conn.row_factory = sqlite3.Row
    try:
        yield conn
        conn.commit()
    finally:
        conn.close()


def init_db():
    with get_db() as conn:
        conn.executescript(SCHEMA)


def is_processed(email_id: str) -> bool:
    with get_db() as conn:
        return conn.execute(
            "SELECT 1 FROM processed_emails WHERE id = ?", (email_id,)
        ).fetchone() is not None


def save_processed_email(data: dict):
    with get_db() as conn:
        conn.execute("""
            INSERT OR REPLACE INTO processed_emails
            (id, from_address, from_name, subject, received_at, body_preview,
             category, urgency, summary, customer_id, is_vip, is_blocklist,
             animal_type, address, phone_number, suggested_action, draft_response,
             requires_follow_up, follow_up_hours, skye_notes, status)
            VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)
        """, (
            data["id"], data["from_address"], data["from_name"],
            data["subject"], data["received_at"], data.get("body_preview", ""),
            data.get("category"), data.get("urgency"),
            data.get("summary"), data.get("customer_id"),
            int(data.get("is_vip", False)), int(data.get("is_blocklist", False)),
            data.get("animal_type"), data.get("address"),
            data.get("phone_number"), data.get("suggested_action"),
            data.get("draft_response"),
            int(data.get("requires_follow_up", False)),
            data.get("follow_up_hours"),
            data.get("skye_notes"), "pending",
        ))


def create_follow_up(email_id: str, description: str, due_at: str, priority: int):
    with get_db() as conn:
        conn.execute(
            "INSERT INTO follow_ups (email_id, description, due_at, priority) VALUES (?,?,?,?)",
            (email_id, description, due_at, priority),
        )


def get_pending_emails():
    with get_db() as conn:
        return conn.execute("""
            SELECT * FROM processed_emails
            WHERE status = 'pending' AND category != 'SPAM'
            ORDER BY urgency DESC,
                     CASE WHEN is_vip THEN 0 ELSE 1 END,
                     received_at ASC
        """).fetchall()


def get_all_follow_ups():
    with get_db() as conn:
        return conn.execute("""
            SELECT f.*, e.from_name, e.from_address, e.subject, e.category, e.is_vip, e.summary
            FROM follow_ups f
            JOIN processed_emails e ON f.email_id = e.id
            ORDER BY
                CASE WHEN f.status = 'open' THEN 0 ELSE 1 END,
                f.priority ASC,
                f.due_at ASC
        """).fetchall()


def get_follow_ups():
    with get_db() as conn:
        return conn.execute("""
            SELECT f.*, e.from_name, e.from_address, e.subject, e.category, e.is_vip
            FROM follow_ups f
            JOIN processed_emails e ON f.email_id = e.id
            WHERE f.status = 'open'
            ORDER BY f.priority ASC, f.due_at ASC
            LIMIT 20
        """).fetchall()


def get_stats():
    with get_db() as conn:
        return conn.execute("""
            SELECT
                COUNT(*) as total,
                SUM(CASE WHEN urgency = 5 THEN 1 ELSE 0 END) as emergencies,
                SUM(CASE WHEN category = 'QUOTE_REQUEST' THEN 1 ELSE 0 END) as quotes,
                SUM(CASE WHEN category = 'SPAM' THEN 1 ELSE 0 END) as spam_archived,
                SUM(CASE WHEN status = 'pending' AND category != 'SPAM' THEN 1 ELSE 0 END) as pending
            FROM processed_emails
        """).fetchone()


def get_done_emails():
    with get_db() as conn:
        return conn.execute("""
            SELECT * FROM processed_emails
            WHERE status = 'done'
            ORDER BY processed_at DESC
        """).fetchall()


def get_dismissed_emails():
    with get_db() as conn:
        return conn.execute("""
            SELECT * FROM processed_emails
            WHERE status = 'dismissed'
            ORDER BY processed_at DESC
        """).fetchall()


def update_email_status(email_id: str, status: str):
    with get_db() as conn:
        conn.execute(
            "UPDATE processed_emails SET status = ? WHERE id = ?",
            (status, email_id),
        )


def reopen_follow_up(fid: int):
    with get_db() as conn:
        conn.execute(
            "UPDATE follow_ups SET status = 'open', completed_at = NULL WHERE id = ?",
            (fid,),
        )


def complete_follow_up(fid: int):
    with get_db() as conn:
        conn.execute(
            "UPDATE follow_ups SET status = 'completed', completed_at = datetime('now') WHERE id = ?",
            (fid,),
        )
