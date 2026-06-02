"""
Tests for dashboard.py — FastAPI routes.
Each test uses a fresh temp database (via `db`) and a TestClient
that hits the real FastAPI app with all templates rendered.
"""
import pytest
from starlette.testclient import TestClient
from helpers import make_email_record
import database


@pytest.fixture
def client(db):
    from dashboard import app
    return TestClient(app)


# ── GET routes return 200 ─────────────────────────────────────────────────────

def test_home_returns_200(client):
    assert client.get("/").status_code == 200


def test_inbox_returns_200(client):
    assert client.get("/inbox").status_code == 200


def test_followups_returns_200(client):
    assert client.get("/followups").status_code == 200


def test_digest_returns_200(client):
    assert client.get("/digest").status_code == 200


# ── GET routes render with data ───────────────────────────────────────────────

def test_home_renders_with_pending_emails(client, db):
    database.save_processed_email(make_email_record(urgency=5, category="EMERGENCY"))
    resp = client.get("/")
    assert resp.status_code == 200
    assert "Test User" in resp.text


def test_inbox_renders_pending_emails(client, db):
    database.save_processed_email(make_email_record())
    resp = client.get("/inbox")
    assert "Test User" in resp.text


def test_inbox_renders_archive_sections(client, db):
    database.save_processed_email(make_email_record(id="done_001"))
    database.save_processed_email(make_email_record(id="dismissed_001"))
    database.update_email_status("done_001", "done")
    database.update_email_status("dismissed_001", "dismissed")
    resp = client.get("/inbox")
    assert resp.status_code == 200
    assert "Done" in resp.text
    assert "Dismissed" in resp.text


# ── POST: mark done / undone ──────────────────────────────────────────────────

def test_mark_done_redirects(client, db):
    database.save_processed_email(make_email_record())
    resp = client.post("/email/msg_test_001/done", follow_redirects=False)
    assert resp.status_code == 303


def test_mark_done_changes_db_status(client, db):
    database.save_processed_email(make_email_record())
    client.post("/email/msg_test_001/done")
    assert database.get_done_emails()[0]["id"] == "msg_test_001"
    assert database.get_pending_emails() == []


def test_undone_restores_to_pending(client, db):
    database.save_processed_email(make_email_record())
    client.post("/email/msg_test_001/done")
    client.post("/email/msg_test_001/undone")
    assert len(database.get_pending_emails()) == 1
    assert database.get_done_emails() == []


# ── POST: dismiss / undismiss ─────────────────────────────────────────────────

def test_dismiss_redirects(client, db):
    database.save_processed_email(make_email_record())
    resp = client.post("/email/msg_test_001/dismiss", follow_redirects=False)
    assert resp.status_code == 303


def test_dismiss_changes_db_status(client, db):
    database.save_processed_email(make_email_record())
    client.post("/email/msg_test_001/dismiss")
    assert database.get_dismissed_emails()[0]["id"] == "msg_test_001"
    assert database.get_pending_emails() == []


def test_undismiss_restores_to_pending(client, db):
    database.save_processed_email(make_email_record())
    client.post("/email/msg_test_001/dismiss")
    client.post("/email/msg_test_001/undismiss")
    assert len(database.get_pending_emails()) == 1
    assert database.get_dismissed_emails() == []


# ── POST: follow-up complete / reopen ────────────────────────────────────────

def test_complete_followup_redirects(client, db):
    database.save_processed_email(make_email_record())
    database.create_follow_up("msg_test_001", "Call back", "2030-01-01T09:00:00", 3)
    fid = database.get_follow_ups()[0]["id"]
    resp = client.post(f"/followup/{fid}/complete", follow_redirects=False)
    assert resp.status_code == 303


def test_complete_followup_marks_done(client, db):
    database.save_processed_email(make_email_record())
    database.create_follow_up("msg_test_001", "Call back", "2030-01-01T09:00:00", 3)
    fid = database.get_follow_ups()[0]["id"]
    client.post(f"/followup/{fid}/complete")
    assert database.get_follow_ups() == []


def test_reopen_followup_restores_to_open(client, db):
    database.save_processed_email(make_email_record())
    database.create_follow_up("msg_test_001", "Call back", "2030-01-01T09:00:00", 3)
    fid = database.get_follow_ups()[0]["id"]
    client.post(f"/followup/{fid}/complete")
    client.post(f"/followup/{fid}/reopen")
    assert len(database.get_follow_ups()) == 1
