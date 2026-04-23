# app/auth.py
from urllib.parse import urlparse

from flask import Blueprint, flash, redirect, render_template, request, url_for
from flask_login import LoginManager, login_required, login_user, logout_user
from sqlmodel import Session, select
from werkzeug.security import check_password_hash, generate_password_hash

from .database import get_engine
from .models import User

auth_bp = Blueprint("auth", __name__, url_prefix="/auth")
login_manager = LoginManager()
login_manager.login_view = "auth.login"


def _safe_redirect_target(target: str | None) -> str | None:
    """Only allow redirects to local app routes."""
    if not target:
        return None

    parsed = urlparse(target)
    if parsed.scheme or parsed.netloc:
        return None
    if not target.startswith("/"):
        return None
    return target


@login_manager.user_loader
def load_user(user_id: str):
    try:
        user_pk = int(user_id)
    except (TypeError, ValueError):
        return None

    with Session(get_engine()) as session:
        return session.get(User, user_pk)


@auth_bp.route("/login", methods=["GET", "POST"])
def login():
    if request.method == "POST":
        email = request.form.get("email", "").strip().lower()
        password = request.form.get("password", "")

        if not email or not password:
            flash("Email and password are required.", "warning")
            return render_template("login.html"), 400

        with Session(get_engine()) as session:
            stmt = select(User).where(User.email == email)
            user = session.exec(stmt).first()

        if user and check_password_hash(user.password_hash, password):
            login_user(user)
            flash("Logged in.", "success")
            next_url = _safe_redirect_target(request.args.get("next"))
            return redirect(next_url or url_for("mood.dashboard"))

        flash("Invalid email or password.", "danger")

    return render_template("login.html")


@auth_bp.route("/logout")
@login_required
def logout():
    logout_user()
    flash("Logged out.", "info")
    return redirect(url_for("auth.login"))


@auth_bp.route("/register", methods=["GET", "POST"])
def register():
    if request.method == "POST":
        email = request.form.get("email", "").strip().lower()
        password = request.form.get("password", "")

        if not email or not password:
            flash("Email and password are required.", "warning")
            return render_template("register.html"), 400

        with Session(get_engine()) as session:
            existing_user = session.exec(
                select(User).where(User.email == email)
            ).first()
            if existing_user:
                flash("Email already taken.", "warning")
                return redirect(url_for("auth.register"))

            user = User(
                email=email,
                password_hash=generate_password_hash(password),
            )
            session.add(user)
            session.commit()

        flash("Account created. Please log in.", "success")
        return redirect(url_for("auth.login"))

    return render_template("register.html")
