from flask import session, flash, redirect, url_for, render_template
from functools import wraps


def login_required(f):
    @wraps(f)
    def wrapper(*args, **kwargs):
        if "user" not in session:
            flash("Debe iniciar sesion para acceder", "warning")
            return redirect(url_for("index"))
        return f(*args, **kwargs)
    return wrapper


def admin_required(f):
    @wraps(f)
    def wrapper(*args, **kwargs):
        if "user" not in session:
            flash("Debe iniciar sesion para acceder", "warning")
            return redirect(url_for("index"))
        if session.get("rol") != "admin":
            return render_template("403.html"), 403
        return f(*args, **kwargs)
    return wrapper


def worker_required(f):
    @wraps(f)
    def wrapper(*args, **kwargs):
        if "user" not in session:
            flash("Debe iniciar sesion para acceder", "warning")
            return redirect(url_for("index"))
        if session.get("rol") != "trabajador":
            return render_template("403.html"), 403
        return f(*args, **kwargs)
    return wrapper
