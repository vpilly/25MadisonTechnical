import os
from dotenv import load_dotenv

load_dotenv()

ANTHROPIC_API_KEY = os.getenv("ANTHROPIC_API_KEY", "")
CLAUDE_MODEL = os.getenv("CLAUDE_MODEL", "claude-sonnet-4-6")

DATABASE_PATH = os.getenv("DATABASE_PATH", "possum_patrol.db")
INBOX_PATH = os.getenv("INBOX_PATH", "sample/inbox.json")
CUSTOMERS_PATH = os.getenv("CUSTOMERS_PATH", "sample/customers.csv")
