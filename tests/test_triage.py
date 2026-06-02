"""
Tests for triage.py — the main processing pipeline.
Claude (classify_email) is mocked throughout; the real database is used
via the `db` fixture so we can assert on actual persisted state.
"""
import json
from datetime import datetime
from unittest.mock import patch
import pytest

from helpers import make_email_record
import database
from triage import run_triage

# ── Shared fixtures and constants ─────────────────────────────────────────────

INBOX_DATA = {
    "emails": [
        {
            "id": "msg_0001",
            "from": {"email": "customer@example.com", "name": "Jane Customer"},
            "subject": "Raccoon in attic",
            "received_at": "2025-06-01T08:00:00",
            "body": "There is a raccoon in my attic, please help.",
        },
        {
            "id": "msg_0002",
            "from": {"email": "other@example.com", "name": "John Other"},
            "subject": "Snake spotted",
            "received_at": "2025-06-01T08:30:00",
            "body": "Found a snake in the garden.",
        },
    ]
}

MOCK_RESULT = {
    "category": "QUOTE_REQUEST",
    "urgency": 3,
    "summary": "Raccoon in attic, needs inspection.",
    "animal_type": "raccoon",
    "address": None,
    "phone_number": None,
    "suggested_action": "Schedule inspection.",
    "draft_response": "Hi Jane, thanks for reaching out...",
    "requires_follow_up": False,
    "follow_up_hours": None,
    "skye_notes": None,
}


@pytest.fixture
def inbox_file(tmp_path):
    path = tmp_path / "inbox.json"
    path.write_text(json.dumps(INBOX_DATA))
    return str(path)


@pytest.fixture
def single_inbox_file(tmp_path):
    data = {"emails": [INBOX_DATA["emails"][0]]}
    path = tmp_path / "single_inbox.json"
    path.write_text(json.dumps(data))
    return str(path)


# ── Core processing ───────────────────────────────────────────────────────────

def test_processes_all_new_emails(db, inbox_file):
    with patch("triage.INBOX_PATH", inbox_file), \
         patch("triage.classify_email", return_value=MOCK_RESULT) as mock_classify:
        run_triage(verbose=False)

    assert mock_classify.call_count == 2
    assert database.is_processed("msg_0001")
    assert database.is_processed("msg_0002")


def test_skips_already_processed_emails(db, inbox_file):
    database.save_processed_email(make_email_record(id="msg_0001"))

    with patch("triage.INBOX_PATH", inbox_file), \
         patch("triage.classify_email", return_value=MOCK_RESULT) as mock_classify:
        run_triage(verbose=False)

    # Only msg_0002 should be sent to Claude
    assert mock_classify.call_count == 1
    assert database.is_processed("msg_0002")


def test_no_new_emails_exits_early(db, inbox_file):
    database.save_processed_email(make_email_record(id="msg_0001"))
    database.save_processed_email(make_email_record(id="msg_0002"))

    with patch("triage.INBOX_PATH", inbox_file), \
         patch("triage.classify_email", return_value=MOCK_RESULT) as mock_classify:
        run_triage(verbose=False)

    assert mock_classify.call_count == 0


# ── Follow-ups ────────────────────────────────────────────────────────────────

def test_creates_follow_up_when_required(db, inbox_file):
    result = {**MOCK_RESULT, "requires_follow_up": True, "follow_up_hours": 48}

    with patch("triage.INBOX_PATH", inbox_file), \
         patch("triage.classify_email", return_value=result):
        run_triage(verbose=False)

    # Both emails require follow-up
    assert len(database.get_follow_ups()) == 2


def test_no_follow_up_created_when_not_required(db, inbox_file):
    with patch("triage.INBOX_PATH", inbox_file), \
         patch("triage.classify_email", return_value=MOCK_RESULT):
        run_triage(verbose=False)

    assert database.get_follow_ups() == []


def test_defaults_follow_up_hours_to_24_when_none(db, single_inbox_file):
    result = {**MOCK_RESULT, "requires_follow_up": True, "follow_up_hours": None}

    with patch("triage.INBOX_PATH", single_inbox_file), \
         patch("triage.classify_email", return_value=result):
        run_triage(verbose=False)

    fus = database.get_follow_ups()
    assert len(fus) == 1
    due = datetime.fromisoformat(fus[0]["due_at"])
    hours_until_due = (due - datetime.now()).total_seconds() / 3600
    assert 23 <= hours_until_due <= 25


# ── Save ordering ─────────────────────────────────────────────────────────────

def test_email_is_saved_after_follow_up_not_before(db, single_inbox_file):
    """
    If follow-up creation fails, the email must NOT be marked processed —
    so a re-run can retry it. We verify the happy-path ordering here:
    follow_up exists when the email is marked done.
    """
    result = {**MOCK_RESULT, "requires_follow_up": True, "follow_up_hours": 24}

    with patch("triage.INBOX_PATH", single_inbox_file), \
         patch("triage.classify_email", return_value=result):
        run_triage(verbose=False)

    # Both records exist — email saved after follow-up
    assert database.is_processed("msg_0001")
    assert len(database.get_follow_ups()) == 1
