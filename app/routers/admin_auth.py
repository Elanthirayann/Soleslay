from fastapi import APIRouter, Cookie, Depends, Form, Request
from fastapi.responses import RedirectResponse
from sqlalchemy.orm import Session

from ..admin_common import render_admin
from ..auth import (
    SESSION_COOKIE_NAME,
    clear_session_cookie,
    create_session,
    destroy_session,
    get_current_session,
    is_rate_limited,
    record_login_attempt,
    set_session_cookie,
    verify_password,
)
from ..db import get_db
from ..models_db import AdminUser

router = APIRouter(prefix="/admin", tags=["admin-auth"])


@router.get("/login")
def login_form(request: Request, session=Depends(get_current_session)):
    if session:
        return RedirectResponse("/admin", status_code=303)
    return render_admin(request, "login.html", {})


@router.post("/login")
def login_submit(
    request: Request,
    username: str = Form(...),
    password: str = Form(...),
    db: Session = Depends(get_db),
):
    if is_rate_limited(request):
        return render_admin(
            request, "login.html",
            {"error": "Too many failed attempts. Please wait 15 minutes and try again."},
            status_code=429,
        )

    user = db.query(AdminUser).filter(AdminUser.username == username.strip()).first()
    valid = bool(user) and user.is_active and verify_password(password, user.password_hash)
    record_login_attempt(request, db, username, valid)

    if not valid:
        return render_admin(
            request, "login.html",
            {"error": "Incorrect username or password."},
            status_code=401,
        )

    session = create_session(db, user, request)
    response = RedirectResponse("/admin", status_code=303)
    set_session_cookie(response, session.token)
    return response


@router.post("/logout")
def logout(
    db: Session = Depends(get_db),
    token: str = Cookie(default=None, alias=SESSION_COOKIE_NAME),
):
    destroy_session(db, token)
    response = RedirectResponse("/admin/login", status_code=303)
    clear_session_cookie(response)
    return response
