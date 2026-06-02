"""
Tests for database.py — all CRUD operations, ordering guarantees,
status transitions, follow-up lifecycle, stats, and nav counts.
Each test gets a fresh temporary SQLite database via the `db` fixture.
"""
import sqlite3
import pytest
from helpers import make_email_record
import database


# ── Schema ────────────────────────────────────────────────────────────────────

def test_init_db_creates_both_tables(db):
    conn = sqlite3.connect(db)
    tables = {r[0] for r in conn.execute(
        "SELECT name FROM sqlite_master WHERE type='table'"
    ).fetchall()}
    conn.close()
    assert "processed_emails" in tables
    assert "follow_ups" in tables


def test_init_db_is_idempotent(db):
    database.init_db()  # second call should not raise
    database.init_db()


# ── is_processed ──────────────────────────────────────────────────────────────

def test_is_processed_false_for_unknown(db):
    assert database.is_processed("nonexistent_id") is False


def test_is_processed_true_after_save(db):
    database.save_processed_email(make_email_record())
    assert database.is_processed("msg_test_001") is True


# ── save / get_pending ────────────────────────────────────────────────────────

def test_save_email_appears_in_pending(db):
    database.save_processed_email(make_email_record(category="QUOTE_REQUEST", urgency=4))
    emails = database.get_pending_emails()
    assert len(emails) == 1
    assert emails[0]["from_name"] == "Test User"
    assert emails[0]["category"] == "QUOTE_REQUEST"


def test_pending_excludes_spam(db):
    database.save_processed_email(make_email_record(category="SPAM"))
    assert database.get_pending_emails() == []


def test_pending_excludes_done_emails(db):
    database.save_processed_email(make_email_record())
    database.update_email_status("msg_test_001", "done")
    assert database.get_pending_emails() == []


def test_pending_excludes_dismissed_emails(db):
    database.save_processed_email(make_email_record())
    database.update_email_status("msg_test_001", "dismissed")
    assert database.get_pending_emails() == []


def test_pending_ordered_by_urgency_descending(db):
    for i, urgency in enumerate([2, 5, 4, 1, 3], start=1):
        database.save_processed_email(make_email_record(id=f"msg_{i:03d}", urgency=urgency))
    urgencies = [e["urgency"] for e in database.get_pending_emails()]
    assert urgencies == sorted(urgencies, reverse=True)


def test_vip_emails_rank_ahead_of_same_urgency(db):
    database.save_processed_email(make_email_record(id="regular", urgency=3, is_vip=False))
    database.save_processed_email(make_email_record(id="vip", urgency=3, is_vip=True))
    emails = database.get_pending_emails()
    assert emails[0]["id"] == "vip"


# ── get_done / get_dismissed ──────────────────────────────────────────────────

def test_get_done_emails(db):
    database.save_processed_email(make_email_record())
    database.update_email_status("msg_test_001", "done")
    done = database.get_done_emails()
    assert len(done) == 1
    assert done[0]["status"] == "done"


def test_get_dismissed_emails(db):
    database.save_processed_email(make_email_record())
    database.update_email_status("msg_test_001", "dismissed")
    dismissed = database.get_dismissed_emails()
    assert len(dismissed) == 1
    assert dismissed[0]["status"] == "dismissed"


# ── update_email_status ───────────────────────────────────────────────────────

def test_update_status_done_then_back_to_pending(db):
    database.save_processed_email(make_email_record())
    database.update_email_status("msg_test_001", "done")
    database.update_email_status("msg_test_001", "pending")
    assert len(database.get_pending_emails()) == 1
    assert database.get_done_emails() == []


def test_update_status_dismissed_then_back_to_pending(db):
    database.save_processed_email(make_email_record())
    database.update_email_status("msg_test_001", "dismissed")
    database.update_email_status("msg_test_001", "pending")
    assert len(database.get_pending_emails()) == 1
    assert database.get_dismissed_emails() == []


# ── follow-ups ────────────────────────────────────────────────────────────────

def test_create_and_get_follow_up(db):
    database.save_processed_email(make_email_record())
    database.create_follow_up("msg_test_001", "Call back about raccoon", "2030-01-01T09:00:00", 4)
    fus = database.get_follow_ups()
    assert len(fus) == 1
    assert fus[0]["description"] == "Call back about raccoon"
    assert fus[0]["priority"] == 4


def test_get_follow_ups_returns_only_open(db):
    database.save_processed_email(make_email_record())
    database.create_follow_up("msg_test_001", "Task", "2030-01-01T09:00:00", 3)
    fid = database.get_follow_ups()[0]["id"]
    database.complete_follow_up(fid)
    assert database.get_follow_ups() == []


def test_complete_follow_up_sets_completed_at(db):
    database.save_processed_email(make_email_record())
    database.create_follow_up("msg_test_001", "Task", "2030-01-01T09:00:00", 3)
    fid = database.get_follow_ups()[0]["id"]
    database.complete_follow_up(fid)
    all_fus = database.get_all_follow_ups()
    completed = [f for f in all_fus if f["status"] == "completed"]
    assert len(completed) == 1
    assert completed[0]["completed_at"] is not None


def test_reopen_follow_up_clears_completed_at(db):
    database.save_processed_email(make_email_record())
    database.create_follow_up("msg_test_001", "Task", "2030-01-01T09:00:00", 3)
    fid = database.get_follow_ups()[0]["id"]
    database.complete_follow_up(fid)
    database.reopen_follow_up(fid)
    open_fus = database.get_follow_ups()
    assert len(open_fus) == 1
    assert open_fus[0]["status"] == "open"
    assert open_fus[0]["completed_at"] is None


def test_get_all_follow_ups_includes_completed(db):
    database.save_processed_email(make_email_record())
    database.create_follow_up("msg_test_001", "Task A", "2030-01-01T09:00:00", 3)
    database.create_follow_up("msg_test_001", "Task B", "2030-01-02T09:00:00", 3)
    fid = database.get_follow_ups()[0]["id"]
    database.complete_follow_up(fid)
    all_fus = database.get_all_follow_ups()
    assert len(all_fus) == 2


# ── stats / nav counts ────────────────────────────────────────────────────────

def test_get_stats_aggregates_correctly(db):
    database.save_processed_email(make_email_record(id="e1", urgency=5, category="EMERGENCY"))
    database.save_processed_email(make_email_record(id="e2", category="QUOTE_REQUEST"))
    database.save_processed_email(make_email_record(id="e3", category="SPAM"))
    stats = database.get_stats()
    assert stats["emergencies"] == 1
    assert stats["quotes"] == 1
    assert stats["spam_archived"] == 1
    assert stats["pending"] == 2  # SPAM excluded from pending count


def test_get_stats_empty_db(db):
    stats = database.get_stats()
    # SQLite SUM() returns NULL on empty tables, treated as 0 everywhere it's used
    assert not stats["emergencies"]
    assert not stats["pending"]


def test_get_nav_counts(db):
    database.save_processed_email(make_email_record(id="e1"))           # pending
    database.save_processed_email(make_email_record(id="e2"))           # → done
    database.save_processed_email(make_email_record(id="e3"))           # → dismissed
    database.save_processed_email(make_email_record(id="e4", category="SPAM"))  # spam (excluded from pending)
    database.update_email_status("e2", "done")
    database.update_email_status("e3", "dismissed")
    database.create_follow_up("e1", "Task", "2030-01-01T09:00:00", 3)
    counts = database.get_nav_counts()
    assert counts["pending"] == 1
    assert counts["done"] == 1
    assert counts["dismissed"] == 1
    assert counts["open_followups"] == 1
