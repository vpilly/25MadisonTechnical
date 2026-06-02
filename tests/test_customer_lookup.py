"""
Tests for customer_lookup.py — lookup, VIP detection, blocklist detection,
and customer context formatting. The CSV loader is replaced with controlled
in-memory data for every test via an autouse fixture.
"""
import pytest
import customer_lookup
from customer_lookup import lookup, is_vip, is_blocklisted, format_customer_context

# ── Test data ─────────────────────────────────────────────────────────────────

_BY_EMAIL = {
    "dottie@example.com": {
        "customer_id": "1",
        "name": "Dottie Henderson",
        "email": "dottie@example.com",
        "first_service_date": "2003-05-01",
        "total_jobs": "47",
        "total_revenue_usd": "8425",
        "notes": "Senior discount always",
    },
    "regular@example.com": {
        "customer_id": "99",
        "name": "Regular Customer",
        "email": "regular@example.com",
        "first_service_date": "2022-01-01",
        "total_jobs": "2",
        "total_revenue_usd": "450",
        "notes": "",
    },
    "mpoteet1985@yahoo.com": {
        "customer_id": "6",
        "name": "Mike Poteet",
        "email": "mpoteet1985@yahoo.com",
        "first_service_date": "2019-03-01",
        "total_jobs": "1",
        "total_revenue_usd": "250",
        "notes": "",
    },
}
_BY_ID = {v["customer_id"]: v for v in _BY_EMAIL.values()}


@pytest.fixture(autouse=True)
def patch_customers(monkeypatch):
    """Replace the LRU-cached CSV loader with in-memory test data for every test."""
    # Clear before the test so any real cached data doesn't bleed in
    customer_lookup._load_customers.cache_clear()
    monkeypatch.setattr(customer_lookup, "_load_customers", lambda: (_BY_EMAIL, _BY_ID))
    yield
    # monkeypatch restores the original after teardown; no cache_clear needed here
    # because the next test's setup clears it before the real function can be called


# ── lookup ────────────────────────────────────────────────────────────────────

def test_lookup_returns_known_customer():
    result = lookup("dottie@example.com")
    assert result is not None
    assert result["name"] == "Dottie Henderson"


def test_lookup_returns_none_for_unknown():
    assert lookup("nobody@example.com") is None


def test_lookup_is_case_insensitive():
    assert lookup("DOTTIE@EXAMPLE.COM") is not None
    assert lookup("Dottie@Example.Com") is not None


# ── is_vip ────────────────────────────────────────────────────────────────────

def test_is_vip_true_for_vip_id():
    customer = _BY_EMAIL["dottie@example.com"]
    assert is_vip(customer) is True


def test_is_vip_false_for_non_vip():
    customer = _BY_EMAIL["regular@example.com"]
    assert is_vip(customer) is False


def test_is_vip_false_for_none():
    assert is_vip(None) is False


# ── is_blocklisted ────────────────────────────────────────────────────────────

def test_blocklisted_by_customer_id():
    # Mike Poteet has customer_id "6" which is in BLOCKLIST_IDS
    assert is_blocklisted("mpoteet1985@yahoo.com", "Mike Poteet") is True


def test_blocklisted_by_known_email_even_with_different_name():
    assert is_blocklisted("mpoteet1985@yahoo.com", "Unknown Name") is True


def test_blocklisted_by_name_even_with_unknown_email():
    assert is_blocklisted("random@example.com", "Mike Poteet") is True


def test_blocklisted_by_name_case_insensitive():
    assert is_blocklisted("random@example.com", "MIKE POTEET") is True


def test_not_blocklisted_for_regular_customer():
    assert is_blocklisted("regular@example.com", "Regular Customer") is False


def test_not_blocklisted_for_unknown_customer():
    assert is_blocklisted("newperson@example.com", "New Person") is False


# ── format_customer_context ───────────────────────────────────────────────────

def test_format_includes_vip_tag():
    customer = _BY_EMAIL["dottie@example.com"]
    ctx = format_customer_context(customer)
    assert "[VIP]" in ctx


def test_format_includes_customer_name_and_revenue():
    customer = _BY_EMAIL["dottie@example.com"]
    ctx = format_customer_context(customer)
    assert "Dottie Henderson" in ctx
    assert "8425" in ctx


def test_format_no_vip_tag_for_regular():
    customer = _BY_EMAIL["regular@example.com"]
    ctx = format_customer_context(customer)
    assert "[VIP]" not in ctx
    assert "Regular Customer" in ctx


def test_format_unknown_customer_message():
    ctx = format_customer_context(None)
    assert "unknown" in ctx.lower() or "new" in ctx.lower()
