from pathlib import Path
from datetime import datetime

from fastapi import FastAPI, Request
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.templating import Jinja2Templates
from jinja2 import Environment, FileSystemLoader

from database import (
    get_pending_emails,
    get_done_emails,
    get_dismissed_emails,
    get_follow_ups,
    get_all_follow_ups,
    get_stats,
    get_nav_counts,
    update_email_status,
    complete_follow_up,
    reopen_follow_up,
)
from digest import generate_digest

app = FastAPI(title="Possum Patrol Inbox")
_templates_dir = str(Path(__file__).parent.parent / "templates")
_jinja_env = Environment(loader=FileSystemLoader(_templates_dir), cache_size=0)
templates = Jinja2Templates(env=_jinja_env)


def _base(active_page: str) -> dict:
    return {"nav": get_nav_counts(), "active_page": active_page, "now": datetime.now()}


# ── Home ──────────────────────────────────────────────────────────────────────

@app.get("/", response_class=HTMLResponse)
async def home(request: Request):
    pending = get_pending_emails()
    important = [
        e for e in pending
        if e["urgency"] >= 4 or e["is_vip"] or e["category"] == "COMPLAINT"
    ]
    other_count = len(pending) - len(important)
    return templates.TemplateResponse(request, "dashboard.html", {
        **_base("home"),
        "follow_ups": get_follow_ups(),
        "stats": get_stats(),
        "important_emails": important,
        "other_count": other_count,
    })


# ── Inbox ─────────────────────────────────────────────────────────────────────

@app.get("/inbox", response_class=HTMLResponse)
async def inbox_view(request: Request):
    return templates.TemplateResponse(request, "inbox.html", {
        **_base("inbox"),
        "pending":   get_pending_emails(),
        "done":      get_done_emails(),
        "dismissed": get_dismissed_emails(),
    })


@app.post("/email/{email_id}/done")
async def mark_done(request: Request, email_id: str):
    update_email_status(email_id, "done")
    return RedirectResponse(request.headers.get("referer", "/inbox"), status_code=303)


@app.post("/email/{email_id}/dismiss")
async def dismiss_email(request: Request, email_id: str):
    update_email_status(email_id, "dismissed")
    return RedirectResponse(request.headers.get("referer", "/inbox"), status_code=303)


@app.post("/email/{email_id}/undone")
async def undone_email(request: Request, email_id: str):
    update_email_status(email_id, "pending")
    return RedirectResponse(request.headers.get("referer", "/inbox"), status_code=303)


@app.post("/email/{email_id}/undismiss")
async def undismiss_email(request: Request, email_id: str):
    update_email_status(email_id, "pending")
    return RedirectResponse(request.headers.get("referer", "/inbox"), status_code=303)


# ── Follow-ups ────────────────────────────────────────────────────────────────

@app.get("/followups", response_class=HTMLResponse)
async def followups_view(request: Request):
    return templates.TemplateResponse(request, "followups.html", {
        **_base("followups"),
        "followups": get_all_follow_ups(),
    })


@app.post("/followup/{fid}/complete")
async def mark_followup_done(request: Request, fid: int):
    complete_follow_up(fid)
    return RedirectResponse(request.headers.get("referer", "/"), status_code=303)


@app.post("/followup/{fid}/reopen")
async def reopen_followup(fid: int):
    reopen_follow_up(fid)
    return RedirectResponse("/followups", status_code=303)


# ── Digest ────────────────────────────────────────────────────────────────────

@app.get("/digest", response_class=HTMLResponse)
async def digest_view(request: Request):
    return templates.TemplateResponse(request, "digest.html", {
        **_base("digest"),
        "content": generate_digest(),
    })
