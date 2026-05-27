from datetime import timedelta

from flask import Flask, redirect, url_for

import config
from models.database import init_db


def create_app() -> Flask:
    app = Flask(__name__)
    app.secret_key = config.SECRET_KEY
    app.permanent_session_lifetime = timedelta(days=14)

    init_db()

    from routes.auth import bp as auth_bp
    from routes.clients import bp as clients_bp
    from routes.reports import bp as reports_bp

    app.register_blueprint(auth_bp)
    app.register_blueprint(clients_bp)
    app.register_blueprint(reports_bp)

    @app.route("/")
    def index():
        return redirect(url_for("clients.list_view"))

    @app.template_filter("money")
    def money(v):
        if v is None or v == "":
            return "—"
        try:
            return f"${float(v):,.2f}"
        except (TypeError, ValueError):
            return str(v)

    @app.template_filter("money0")
    def money0(v):
        if v is None or v == "":
            return "—"
        try:
            return f"${float(v):,.0f}"
        except (TypeError, ValueError):
            return str(v)

    return app


app = create_app()


if __name__ == "__main__":
    app.run(host="127.0.0.1", port=5000, debug=True)
