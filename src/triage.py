import json
from datetime import datetime, timedelta
from config import INBOX_PATH
from database import init_db, is_processed, save_processed_email, create_follow_up
from customer_lookup import lookup, is_vip, is_blocklisted, format_customer_context
from ai_processor import classify_email

CATEGORY_ICONS = {
    "EMERGENCY": "🚨",
    "COMPLAINT": "⚠️",
    "VIP_COMMERCIAL": "⭐",
    "QUOTE_REQUEST": "💰",
    "SCHEDULED_SERVICE": "📅",
    "VENDOR_OPERATIONAL": "🧾",
    "COMMUNITY": "❤️",
    "MISC": "📧",
    "SPAM": "🗑️",
    "WEIRD": "🤔",
    "BLOCKLIST": "🚫",
}


def run_triage(verbose: bool = True):
    init_db()

    with open(INBOX_PATH) as f:
        inbox = json.load(f)

    emails = inbox["emails"]
    new_emails = [e for e in emails if not is_processed(e["id"])]

    if not new_emails:
        print("No new emails to process.")
        return

    print(f"Processing {len(new_emails)} emails through Claude...\n")

    counts: dict[str, int] = {}

    for i, email in enumerate(new_emails, 1):
        sender_email = email["from"]["email"]
        sender_name = email["from"]["name"]

        customer = lookup(sender_email)
        blocklisted = is_blocklisted(sender_email, sender_name)
        vip = is_vip(customer)
        customer_context = format_customer_context(customer)
        if blocklisted:
            customer_context += " ⚠️ BLOCKLIST: Mike Poteet or known associate — decline politely."

        result = classify_email(email, customer_context)

        record = {
            "id": email["id"],
            "from_address": sender_email,
            "from_name": sender_name,
            "subject": email["subject"],
            "received_at": email["received_at"],
            "body_preview": email["body"][:400],
            "is_vip": vip,
            "is_blocklist": blocklisted,
            "customer_id": customer["customer_id"] if customer else None,
            **result,
        }

        follow_up_hours = result.get("follow_up_hours") or 24
        if result.get("requires_follow_up"):
            due_at = (datetime.now() + timedelta(hours=follow_up_hours)).isoformat()
            create_follow_up(email["id"], result.get("summary", email["subject"]), due_at, result.get("urgency", 3))
        save_processed_email(record)

        category = result.get("category", "MISC")
        counts[category] = counts.get(category, 0) + 1
        icon = CATEGORY_ICONS.get(category, "📧")

        

        if verbose:
            urgency_str = f"[u{result.get('urgency', '?')}]"
            summary = result.get("summary", email["subject"])[:72]
            print(f"  {i:02d}/{len(new_emails)} {icon} {urgency_str} {sender_name}: {summary}")

    print(f"\n✅ Done. Breakdown:")
    for cat, n in sorted(counts.items(), key=lambda x: -x[1]):
        print(f"   {CATEGORY_ICONS.get(cat, '📧')}  {cat}: {n}")
    print(f"\n→ Dashboard: http://localhost:8000")
