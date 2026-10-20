from flask import Blueprint, current_app, redirect, render_template, url_for

dashboard_bp = Blueprint("dashboard", __name__)


@dashboard_bp.get("/")
def raiz():
    return redirect(url_for("dashboard.dashboard"))


@dashboard_bp.get("/login")
def login():
    return render_template(
        "login.html",
        supabase_url=current_app.config["SUPABASE_URL"],
        supabase_anon_key=current_app.config["SUPABASE_ANON_KEY"],
    )


@dashboard_bp.get("/dashboard")
def dashboard():
    """Não checa sessão aqui — o JWT fica em localStorage, não em cookie,
    então a validação é client-side: dashboard.js chama /api/me ao
    carregar e redireciona pro /login sozinho se vier 401."""
    return render_template("dashboard.html")
