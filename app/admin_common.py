"""
Shared helpers used by every admin router: a single Jinja2Templates
instance for app/templates/admin, a tiny flash-message mechanism (passed
via a signed query param so it survives the redirect after a POST without
needing server-side session storage for messages), and CSRF helpers.
"""
from pathlib import Path
from urllib.parse import urlencode

from fastapi import Request
from fastapi.responses import RedirectResponse
from fastapi.templating import Jinja2Templates

from .models_db import AdminSession

ADMIN_TEMPLATES_DIR = Path(__file__).resolve().parent / "templates" / "admin"
admin_templates = Jinja2Templates(directory=str(ADMIN_TEMPLATES_DIR))


def render_admin(request: Request, template: str, context: dict, session: AdminSession = None, status_code: int = 200):
    ctx = {"request": request, "csrf_token": session.csrf_token if session else "", **context}
    if "success" not in ctx:
        ctx["success"] = request.query_params.get("success")
    if "error" not in ctx:
        ctx["error"] = request.query_params.get("error")
    return admin_templates.TemplateResponse(template, ctx, status_code=status_code)


def redirect_with_message(path: str, success: str = None, error: str = None) -> RedirectResponse:
    params = {}
    if success:
        params["success"] = success
    if error:
        params["error"] = error
    url = path + (f"?{urlencode(params)}" if params else "")
    return RedirectResponse(url, status_code=303)
