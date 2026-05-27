from functools import wraps

from flask import Blueprint, flash, redirect, render_template, request, session, url_for

import config

bp = Blueprint("auth", __name__)


def login_required(view):
    @wraps(view)
    def wrapped(*args, **kwargs):
        if not session.get("authed"):
            return redirect(url_for("auth.login", next=request.path))
        return view(*args, **kwargs)
    return wrapped


@bp.route("/login", methods=["GET", "POST"])
def login():
    if request.method == "POST":
        password = request.form.get("password", "")
        if password == config.PORTAL_PASSWORD:
            session["authed"] = True
            session.permanent = True
            return redirect(request.args.get("next") or url_for("clients.list_view"))
        flash("Incorrect password.", "error")
    return render_template("login.html")


@bp.route("/logout", methods=["POST"])
def logout():
    session.clear()
    return redirect(url_for("auth.login"))
