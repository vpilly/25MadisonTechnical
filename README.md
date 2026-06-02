# Possum Patrol Inbox Triage

AI-powered email triage system for **Possum Patrol Pest Control** — a 22-year-old family wildlife removal business in Chattanooga, TN. Skye Ryder was spending **3 hours every morning** manually sorting ~100 emails. This system eliminates that.

---

## What It Does

Each morning, Skye runs one command. Claude reads every email, cross-references the customer database, and:

- **Classifies** each email by category (Emergency, Complaint, Quote Request, Scheduled Service, VIP Commercial, etc.) and urgency (1–5)
- **Flags VIP customers** (known lifetime revenue, personal notes) and **blocks known bad actors**
- **Drafts a ready-to-send reply** in Skye's voice for each email
- **Creates follow-up tasks** automatically for emails that need a callback or check-in
- **Surfaces a morning digest** — the 30-second brief before opening the inbox

The web dashboard lets Skye process the queue in minutes rather than hours.

---

## Features

- **Home** — priority-at-a-glance: urgent emails + open follow-up queue
- **Inbox** — full email list with two-column layout (pending left, done/dismissed archive right), sortable and filterable by urgency, category, and VIP status
- **Follow-ups** — open and completed follow-ups side by side, per-column sort, full filter bar
- **Morning Digest** — scannable terminal or web summary: emergencies, overdue follow-ups, complaints, VIP backlog, revenue pipeline
- **Idempotent triage** — re-running never double-processes an email; safe to run incrementally
- **Prompt caching** — system prompt (~1,400 tokens of business context) is cached across all 100 Claude calls, cutting latency and cost

---

## Tech Stack

| Layer | Choice |
|---|---|
| AI | Anthropic Claude (`claude-sonnet-4-6`) with structured tool use + prompt caching |
| Backend | Python 3, FastAPI, Uvicorn |
| Templates | Jinja2 |
| Database | SQLite (built-in `sqlite3`) |
| Config | `python-dotenv` |

---

## Setup

### 1. Clone and create a virtual environment

```bash
git clone <repo-url>
cd 25MadisonTechnical
python -m venv .venv
source .venv/bin/activate   # Windows: .venv\Scripts\activate
```

### 2. Install dependencies

```bash
pip install -r requirements.txt
```

### 3. Configure environment

```bash
cp .env.example .env
```

Open `.env` and add your Anthropic API key:

```
ANTHROPIC_API_KEY=sk-ant-...
```

### 4. Add sample data

Place the following files in a `sample/` directory:

```
sample/
  inbox.json       # array of email objects
  customers.csv    # customer database with lifetime revenue
```

The `inbox.json` format expected per email:

```json
{
  "id": "msg_0001",
  "from_address": "customer@example.com",
  "from_name": "Customer Name",
  "subject": "Subject line",
  "received_at": "2025-06-01T08:23:00",
  "body": "Full email body text..."
}
```

---

## Usage

### Triage the inbox

Processes all unread emails through Claude and saves results to the database. Safe to re-run — already-processed emails are skipped.

```bash
python main.py triage
```

Add `--quiet` / `-q` to suppress per-email output.

### Launch the dashboard

```bash
python main.py serve
```

Opens at [http://localhost:8000](http://localhost:8000).

### Print the morning digest

```bash
python main.py digest
```

Prints a terminal summary: emergencies, overdue follow-ups, complaints, VIP pending, and quote pipeline.

---

## Project Structure

```
├── main.py                  # CLI entry point (triage / serve / digest)
├── requirements.txt
├── .env.example
├── src/
│   ├── ai_processor.py      # Claude API calls, system prompt, triage tool schema
│   ├── triage.py            # Main triage loop — reads inbox, calls Claude, writes DB
│   ├── customer_lookup.py   # CSV loader, VIP/blocklist logic, context formatter
│   ├── database.py          # SQLite schema, all read/write functions
│   ├── digest.py            # Morning digest generator
│   ├── dashboard.py         # FastAPI app and route handlers
│   └── config.py            # Environment variable loading
├── templates/
│   ├── base.html            # Shared nav bar (extends into all pages)
│   ├── dashboard.html       # Home — priority emails + follow-up queue
│   ├── inbox.html           # Full inbox — pending, done, dismissed
│   ├── followups.html       # Follow-up management
│   └── digest.html          # Web morning digest
└── sample/                  # Gitignored — place inbox.json and customers.csv here
```

---

## How Triage Works

1. Loads `inbox.json` and `customers.csv`
2. For each email, checks the database — skips if already processed
3. Looks up the sender in the customer database (resolves VIP status, lifetime revenue, blocklist)
4. Calls Claude with the email + customer context, receiving structured JSON via tool use:
   - Category, urgency score, summary, animal type, address, phone
   - Draft reply written in Skye's voice
   - Whether a follow-up is needed and in how many hours
   - Skye-specific notes (e.g. "This is Dottie — apply senior discount")
5. If a follow-up is needed, creates the follow-up record *before* marking the email processed — so a crash never leaves an email marked done without its follow-up
6. Saves the processed email to SQLite

The system prompt encodes Marshall's 22 years of institutional knowledge: VIP customer histories, the blocklist, pricing rules, seasonal notes (bat pup season in May/June), and business alerts — so Claude responds the way the Ryders would.
