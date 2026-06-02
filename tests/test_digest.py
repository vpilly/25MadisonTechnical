"""
Tests for digest.py — morning digest output.
Each test controls DB state precisely to verify the right sections
appear (or don't) and formatting is correct.
"""
import pytest
from helpers import make_email_record
import database
from digest import generate_digest


# ── Basic structure ───────────────────────────────────────────────────────────

def test_digest_runs_on_empty_db(db):
    output = generate_digest()
    assert "POSSUM PATROL" in output
    assert "Inbox processed: 0" in output


def test_digest_shows_correct_total_count(db):
    for i in range(5):
        database.save_processed_email(make_email_record(id=f"e_{i}"))
    assert "Inbox processed: 5" in generate_digest()


def test_digest_shows_spam_count(db):
    database.save_processed_email(make_email_record(id="s1", category="SPAM"))
    database.save_processed_email(make_email_record(id="s2", category="SPAM"))
    assert "Spam auto-archived: 2" in generate_digest()


def test_digest_includes_breakdown_section(db):
    database.save_processed_email(make_email_record(category="MISC"))
    assert "Inbox breakdown:" in generate_digest()
    assert "MISC" in generate_digest()


# ── Emergency section ─────────────────────────────────────────────────────────

def test_digest_emergency_section_appears(db):
    database.save_processed_email(make_email_record(
        id="emerg_001", category="EMERGENCY", urgency=5,
        from_name="Judy Crisis", summary="Bats in the bedroom",
        phone_number="(423) 555-0100",
    ))
    output = generate_digest()
    assert "EMERGENCIES" in output
    assert "Judy Crisis" in output
    assert "Bats in the bedroom" in output
    assert "(423) 555-0100" in output


def test_digest_no_emergency_section_when_none(db):
    database.save_processed_email(make_email_record(urgency=3))  # not an emergency
    assert "EMERGENCIES" not in generate_digest()


def test_digest_done_emergency_not_in_section(db):
    database.save_processed_email(make_email_record(
        id="emerg_001", category="EMERGENCY", urgency=5, from_name="Judy Crisis",
    ))
    database.update_email_status("emerg_001", "done")
    assert "EMERGENCIES" not in generate_digest()


# ── Complaint section ─────────────────────────────────────────────────────────

def test_digest_complaint_section_appears(db):
    database.save_processed_email(make_email_record(
        id="comp_001", category="COMPLAINT", urgency=4,
        from_name="Angry Customer", summary="Terrible service last week",
    ))
    output = generate_digest()
    assert "COMPLAINTS" in output
    assert "Angry Customer" in output


def test_digest_no_complaint_section_when_none(db):
    database.save_processed_email(make_email_record(category="MISC"))
    assert "COMPLAINTS" not in generate_digest()


# ── VIP section ───────────────────────────────────────────────────────────────

def test_digest_vip_section_appears_for_vip_email(db):
    database.save_processed_email(make_email_record(
        id="vip_001", is_vip=True, from_name="Dottie Henderson",
        summary="Need raccoon help again",
    ))
    output = generate_digest()
    assert "VIP" in output
    assert "Dottie Henderson" in output


def test_digest_vip_section_appears_for_vip_commercial(db):
    database.save_processed_email(make_email_record(
        id="vip_com_001", category="VIP_COMMERCIAL", from_name="Tony Marchetti",
        summary="Monthly inspection due",
    ))
    assert "VIP" in generate_digest()


# ── Follow-up section ─────────────────────────────────────────────────────────

def test_digest_overdue_followup_section_appears(db):
    database.save_processed_email(make_email_record())
    database.create_follow_up(
        "msg_test_001",
        "Call back about raccoon removal",
        "2020-01-01T09:00:00",  # past date = overdue
        3,
    )
    output = generate_digest()
    assert "OVERDUE" in output
    assert "Call back about raccoon removal" in output


def test_digest_no_overdue_section_for_future_followup(db):
    database.save_processed_email(make_email_record())
    database.create_follow_up("msg_test_001", "Future task", "2099-01-01T09:00:00", 3)
    assert "OVERDUE" not in generate_digest()


# ── Quote truncation ──────────────────────────────────────────────────────────

def test_digest_shows_and_more_when_quotes_exceed_six(db):
    for i in range(8):
        database.save_processed_email(make_email_record(
            id=f"quote_{i:03d}",
            from_name=f"Customer {i}",
            category="QUOTE_REQUEST",
        ))
    output = generate_digest()
    assert "and 2 more" in output


def test_digest_no_truncation_message_for_six_or_fewer_quotes(db):
    for i in range(6):
        database.save_processed_email(make_email_record(
            id=f"quote_{i:03d}",
            category="QUOTE_REQUEST",
        ))
    assert "more" not in generate_digest()
