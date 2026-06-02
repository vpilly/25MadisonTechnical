from pathlib import Path
from datetime import datetime

from fastapi import FastAPI, Request, Form
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.templating import Jinja2Templates

from database import (
    get_pending_emails,
    get_follow_ups,
    get_stats,
    update_email_status,
    complete_follow_up,
)
from digest import generate_digest

app = FastAPI(title="Possum Patrol Inbox")
templates = Jinja2Templates(directory=str(Path(__file__).parent.parent / "templates"))


@app.get("/", response_class=HTMLResponse)
async def home(request: Request):
    emails = get_pending_emails()
    follow_ups = get_follow_ups()
    stats = get_stats()
    return templates.TemplateResponse("dashboard.html", {
        "request": request,
        "emails": emails,
        "follow_ups": follow_ups,
        "stats": stats,
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


@app.post("/followup/{fid}/complete")
async def mark_followup_done(fid: int):
    complete_follow_up(fid)
    return RedirectResponse("/", status_code=303)


@app.get("/digest", response_class=HTMLResponse)
async def digest_view():
    content = generate_digest()
    return HTMLResponse(
        f"<html><body><pre style='font-family:monospace;padding:2rem;max-width:700px;"
        f"white-space:pre-wrap;line-height:1.6'>{content}</pre></body></html>"
    )
