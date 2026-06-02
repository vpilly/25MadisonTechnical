from pathlib import Path
from datetime import datetime

from fastapi import FastAPI, Request, Form
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
    update_email_status,
    complete_follow_up,
    reopen_follow_up,
)
from digest import generate_digest

app = FastAPI(title="Possum Patrol Inbox")
_templates_dir = str(Path(__file__).parent.parent / "templates")
_jinja_env = Environment(loader=FileSystemLoader(_templates_dir), cache_size=0)
templates = Jinja2Templates(env=_jinja_env)


@app.get("/", response_class=HTMLResponse)
async def home(request: Request):
    emails = get_pending_emails()
    follow_ups = get_follow_ups()
    stats = get_stats()
    dismissed_count = len(get_dismissed_emails())
    done_count = len(get_done_emails())
    return templates.TemplateResponse(request, "dashboard.html", {
        "emails": emails,
        "follow_ups": follow_ups,
        "stats": stats,
        "dismissed_count": dismissed_count,
        "done_count": done_count,
        "now": datetime.now(),
    })


@app.post("/email/{email_id}/done")
async def mark_done(email_id: str):
    update_email_status(email_id, "done")
    return RedirectResponse("/", status_code=303)


@app.post("/email/{email_id}/dismiss")
async def dismiss_email(email_id: str):
    update_email_status(email_id, "dismissed")
    return RedirectResponse("/", status_code=303)


@app.get("/followups", response_class=HTMLResponse)
async def followups_view(request: Request):
    all_followups = get_all_follow_ups()
    return templates.TemplateResponse(request, "followups.html", {
        "followups": all_followups,
        "now": datetime.now(),
    })


@app.post("/followup/{fid}/reopen")
async def reopen_followup(fid: int):
    reopen_follow_up(fid)
    return RedirectResponse("/followups", status_code=303)


@app.get("/done", response_class=HTMLResponse)
async def done_view(request: Request):
    done = get_done_emails()
    return templates.TemplateResponse(request, "done.html", {
        "done": done,
        "now": datetime.now(),
    })


@app.post("/email/{email_id}/undone")
async def undone_email(email_id: str):
    update_email_status(email_id, "pending")
    return RedirectResponse("/done", status_code=303)


@app.get("/dismissed", response_class=HTMLResponse)
async def dismissed_view(request: Request):
    dismissed = get_dismissed_emails()
    return templates.TemplateResponse(request, "dismissed.html", {
        "dismissed": dismissed,
        "now": datetime.now(),
    })


@app.post("/email/{email_id}/undismiss")
async def undismiss_email(email_id: str):
    update_email_status(email_id, "pending")
    return RedirectResponse("/dismissed", status_code=303)


@app.post("/followup/{fid}/complete")
async def mark_followup_done(request: Request, fid: int):
    complete_follow_up(fid)
    referer = request.headers.get("referer", "/")
    return RedirectResponse(referer, status_code=303)


@app.get("/digest", response_class=HTMLResponse)
async def digest_view():
    content = generate_digest()
    return HTMLResponse(
        f"<html><body><pre style='font-family:monospace;padding:2rem;max-width:700px;"
        f"white-space:pre-wrap;line-height:1.6'>{content}</pre></body></html>"
    )
