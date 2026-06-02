from datetime import date
from database import get_db
from triage import CATEGORY_ICONS


def generate_digest() -> str:
    today = date.today()

    with get_db() as conn:
        emergencies = conn.execute("""
            SELECT * FROM processed_emails
            WHERE urgency = 5 AND status = 'pending'
            ORDER BY received_at ASC
        """).fetchall()

        overdue_followups = conn.execute("""
            SELECT f.*, e.from_name, e.category, e.summary
            FROM follow_ups f
            JOIN processed_emails e ON f.email_id = e.id
            WHERE f.status = 'open' AND f.due_at <= datetime('now')
            ORDER BY f.priority ASC
        """).fetchall()

        complaints = conn.execute("""
            SELECT * FROM processed_emails
            WHERE category = 'COMPLAINT' AND status = 'pending'
        """).fetchall()

        vip_pending = conn.execute("""
            SELECT * FROM processed_emails
            WHERE (is_vip = 1 OR category = 'VIP_COMMERCIAL') AND status = 'pending'
            ORDER BY urgency DESC
        """).fetchall()

        quotes = conn.execute("""
            SELECT * FROM processed_emails
            WHERE category = 'QUOTE_REQUEST' AND status = 'pending'
            ORDER BY received_at ASC
        """).fetchall()

        breakdown = conn.execute("""
            SELECT category, COUNT(*) as n
            FROM processed_emails
            GROUP BY category ORDER BY n DESC
        """).fetchall()

        spam_count = conn.execute(
            "SELECT COUNT(*) as n FROM processed_emails WHERE category = 'SPAM'"
        ).fetchone()

    total = sum(r["n"] for r in breakdown)
    lines = [
        f"🦝 POSSUM PATROL — MORNING DIGEST",
        f"   {today.strftime('%A, %B %d, %Y')}",
        "=" * 52,
        f"Inbox processed: {total} emails",
        f"Spam auto-archived: {spam_count['n'] if spam_count else 0}",
        "",
    ]

    if emergencies:
        lines.append(f"🚨  EMERGENCIES — CALL NOW ({len(emergencies)}):")
        for e in emergencies:
            lines.append(f"   • {e['from_name']}: {e['summary']}")
            if e["phone_number"]:
                lines.append(f"     📞 {e['phone_number']}")
        lines.append("")

    if overdue_followups:
        lines.append(f"⏰  OVERDUE FOLLOW-UPS ({len(overdue_followups)}):")
        for f in overdue_followups:
            lines.append(f"   • {f['from_name']} ({f['category']}): {f['description']}")
        lines.append("")

    if complaints:
        lines.append(f"⚠️   COMPLAINTS — RESPOND TODAY ({len(complaints)}):")
        for e in complaints:
            lines.append(f"   • {e['from_name']}: {e['summary']}")
        lines.append("")

    if vip_pending:
        seen: set = set()
        unique = [e for e in vip_pending if e["id"] not in seen and not seen.add(e["id"])]
        lines.append(f"⭐  VIP / COMMERCIAL PENDING ({len(unique)}):")
        for e in unique[:6]:
            lines.append(f"   • {e['from_name']}: {e['summary']}")
        lines.append("")

    if quotes:
        lines.append(f"💰  QUOTE REQUESTS — REVENUE PIPELINE ({len(quotes)}):")
        for e in quotes[:6]:
            lines.append(f"   • {e['from_name']}: {e['summary']}")
        if len(quotes) > 6:
            lines.append(f"   ... and {len(quotes) - 6} more")
        lines.append("")

    lines.append("Inbox breakdown:")
    for row in breakdown:
        icon = CATEGORY_ICONS.get(row["category"], "📧")
        lines.append(f"   {icon}  {row['category']}: {row['n']}")

    lines.append("")
    lines.append("=" * 52)
    lines.append("Open dashboard → http://localhost:8000")

    return "\n".join(lines)
