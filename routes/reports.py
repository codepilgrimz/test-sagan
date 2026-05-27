from datetime import date

from flask import (
    Blueprint, abort, current_app, flash, make_response, redirect,
    render_template, request, url_for,
)

from models import account as account_model
from models import client as client_model
from models import report as report_model
from routes.auth import login_required
from services import calculations, pdf_generator

bp = Blueprint("reports", __name__)


def _client_or_404(client_id):
    c = client_model.get_client(client_id)
    if not c:
        abort(404)
    return c


def _report_or_404(report_id):
    r = report_model.get_report(report_id)
    if not r:
        abort(404)
    return r


@bp.route("/clients/<int:client_id>/reports/new", methods=["GET"])
@login_required
def new_view(client_id):
    client = _client_or_404(client_id)
    accounts = account_model.list_accounts(client_id)
    return render_template(
        "reports/generate.html",
        client=client,
        accounts=accounts,
        today=date.today().isoformat(),
    )


@bp.route("/clients/<int:client_id>/reports", methods=["POST"])
@login_required
def create_view(client_id):
    client = _client_or_404(client_id)
    accounts = account_model.list_accounts(client_id)
    form = request.form

    report_date = form.get("report_date") or date.today().isoformat()

    # SACS profile overrides (let the user tweak salaries/outflow for this report
    # without having to leave the form to edit the client profile)
    c1_salary = float(form.get("client1_salary") or client.client1_salary or 0)
    c2_salary = float(form.get("client2_salary") or client.client2_salary or 0)
    outflow = float(form.get("monthly_outflow") or client.monthly_outflow or 0)
    deductibles = float(form.get("insurance_deductibles_total") or client.insurance_deductibles_total or 0)

    sacs = calculations.sacs_totals(c1_salary, c2_salary, outflow, deductibles)

    # Per-account balance entries
    account_snapshot = []
    sacs_balances = {"private_reserve": None, "investment": None,
                     "private_reserve_date": None, "investment_date": None}

    for a in accounts:
        bal_raw = form.get(f"balance_{a.id}")
        cash_raw = form.get(f"cash_{a.id}")
        date_raw = form.get(f"date_{a.id}") or report_date

        if bal_raw in (None, ""):
            flash(f"Missing balance for {a.account_type}.", "error")
            return redirect(url_for("reports.new_view", client_id=client_id))

        balance = float(bal_raw)
        cash = float(cash_raw) if cash_raw not in (None, "") else None

        stale = bool(date_raw and date_raw < report_date)
        account_snapshot.append({
            "id": a.id,
            "category": a.category,
            "owner": a.owner,
            "account_type": a.account_type,
            "account_number_last4": a.account_number_last4,
            "sacs_role": a.sacs_role,
            "property_address": a.property_address,
            "interest_rate": a.interest_rate,
            "balance": balance,
            "cash_balance": cash,
            "value_date": date_raw,
            "stale": stale,
        })

        # Cache last entered values on the account row
        account_model.update_account_snapshot(a.id, balance, cash, date_raw)

        # Capture SACS-tagged accounts for the page-2 layout
        if a.sacs_role == "private_reserve":
            sacs_balances["private_reserve"] = balance
            sacs_balances["private_reserve_date"] = date_raw
        elif a.sacs_role == "investment":
            sacs_balances["investment"] = balance
            sacs_balances["investment_date"] = date_raw

    # Allow direct override fields on the form if the user doesn't have those
    # accounts configured yet
    if sacs_balances["private_reserve"] is None and form.get("sacs_private_reserve"):
        sacs_balances["private_reserve"] = float(form["sacs_private_reserve"])
        sacs_balances["private_reserve_date"] = form.get("sacs_private_reserve_date") or report_date
    if sacs_balances["investment"] is None and form.get("sacs_investment"):
        sacs_balances["investment"] = float(form["sacs_investment"])
        sacs_balances["investment_date"] = form.get("sacs_investment_date") or report_date

    tcc = calculations.tcc_totals(account_snapshot)

    snapshot = {
        "report_date": report_date,
        "client": {
            "client1_name": client.client1_name,
            "client1_dob": client.client1_dob,
            "client1_ssn_last4": client.client1_ssn_last4,
            "client1_age": client_model.calculate_age(client.client1_dob),
            "client1_salary": c1_salary,
            "client2_name": client.client2_name,
            "client2_dob": client.client2_dob,
            "client2_ssn_last4": client.client2_ssn_last4,
            "client2_age": client_model.calculate_age(client.client2_dob),
            "client2_salary": c2_salary,
            "monthly_outflow": outflow,
            "insurance_deductibles_total": deductibles,
            "account_floor": client.account_floor,
        },
        "sacs": {**sacs, **{k: v for k, v in sacs_balances.items()}},
        "tcc": tcc,
        "accounts": account_snapshot,
    }

    report_id = report_model.create_report(client_id, report_date, snapshot)
    flash("Report generated.", "success")
    return redirect(url_for("clients.detail_view", client_id=client_id) + f"#report-{report_id}")


def _pdf_response(pdf_bytes: bytes, filename: str):
    resp = make_response(pdf_bytes)
    resp.headers["Content-Type"] = "application/pdf"
    resp.headers["Content-Disposition"] = f'inline; filename="{filename}"'
    return resp


@bp.route("/reports/<int:report_id>/sacs.pdf")
@login_required
def sacs_pdf(report_id):
    report = _report_or_404(report_id)
    client = client_model.get_client(report.client_id)
    pdf_bytes = pdf_generator.render_sacs_pdf(report.snapshot)
    safe_name = (client.client1_name or "client").split()[0]
    return _pdf_response(pdf_bytes, f"SACS_{safe_name}_{report.report_date}.pdf")


@bp.route("/reports/<int:report_id>/tcc.pdf")
@login_required
def tcc_pdf(report_id):
    report = _report_or_404(report_id)
    client = client_model.get_client(report.client_id)
    pdf_bytes = pdf_generator.render_tcc_pdf(report.snapshot)
    safe_name = (client.client1_name or "client").split()[0]
    return _pdf_response(pdf_bytes, f"TCC_{safe_name}_{report.report_date}.pdf")
