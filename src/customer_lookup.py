import csv
from functools import lru_cache
from config import CUSTOMERS_PATH

# customer_id 6 = Mike Poteet (blocklist)
BLOCKLIST_IDS = {"6"}
BLOCKLIST_EMAILS = {"mpoteet1985@yahoo.com"}
BLOCKLIST_NAMES = {"mike poteet", "michael poteet"}

VIP_IDS = {"1", "2", "3", "4", "5"}  # Dottie, Tony Marchetti, Pastor Jim, Linda HOA, Dr. Wendy


@lru_cache(maxsize=None)
def _load_customers() -> tuple[dict, dict]:
    by_email: dict[str, dict] = {}
    by_id: dict[str, dict] = {}
    try:
        with open(CUSTOMERS_PATH, newline="") as f:
            for row in csv.DictReader(f):
                by_id[row["customer_id"]] = row
                if row["email"]:
                    by_email[row["email"].lower()] = row
    except FileNotFoundError:
        pass
    return by_email, by_id


def lookup(email_address: str) -> dict | None:
    by_email, _ = _load_customers()
    return by_email.get(email_address.lower())


def is_vip(customer: dict | None) -> bool:
    return bool(customer and customer.get("customer_id") in VIP_IDS)


def is_blocklisted(email_address: str, from_name: str) -> bool:
    _, by_id = _load_customers()
    by_email, _ = _load_customers()
    customer = by_email.get(email_address.lower())
    if customer and customer.get("customer_id") in BLOCKLIST_IDS:
        return True
    if email_address.lower() in BLOCKLIST_EMAILS:
        return True
    if from_name.lower().strip() in BLOCKLIST_NAMES:
        return True
    return False


def format_customer_context(customer: dict | None) -> str:
    if not customer:
        return "New / unknown customer — no history on file."
    vip_tag = " [VIP]" if customer.get("customer_id") in VIP_IDS else ""
    return (
        f"Known customer{vip_tag}: {customer['name']} | "
        f"Since {customer['first_service_date'][:4]} | "
        f"{customer['total_jobs']} jobs | "
        f"${customer['total_revenue_usd']} total revenue | "
        f"Notes: {customer.get('notes') or 'None'}"
    )
