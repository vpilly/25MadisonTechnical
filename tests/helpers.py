def make_email_record(**overrides):
    """Return a minimal valid processed_email dict, with optional field overrides."""
    base = {
        "id": "msg_test_001",
        "from_address": "test@example.com",
        "from_name": "Test User",
        "subject": "Test Subject",
        "received_at": "2025-06-01T08:00:00",
        "body_preview": "Body text.",
        "category": "MISC",
        "urgency": 3,
        "summary": "A test summary.",
        "customer_id": None,
        "is_vip": False,
        "is_blocklist": False,
        "animal_type": None,
        "address": None,
        "phone_number": None,
        "suggested_action": "Reply.",
        "draft_response": "Dear Test User,",
        "requires_follow_up": False,
        "follow_up_hours": None,
        "skye_notes": None,
    }
    base.update(overrides)
    return base
