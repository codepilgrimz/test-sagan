from flask import Blueprint, abort, flash, redirect, render_template, request, url_for

from models import account as account_model
from models import client as client_model
from models import report as report_model
from routes.auth import login_required

bp = Blueprint("clients", __name__, url_prefix="/clients")


@bp.route("/")
@login_required
def list_view():
    clients = client_model.list_clients()
    last_reports = {}
    for c in clients:
        last = report_model.last_report_for_client(c.id)
        last_reports[c.id] = last
    return render_template("clients/list.html", clients=clients, last_reports=last_reports)


@bp.route("/new", methods=["GET", "POST"])
@login_required
def new_view():
    if request.method == "POST":
        if not request.form.get("client1_name"):
            flash("Client 1 name is required.", "error")
        else:
            cid = client_model.create_client(request.form.to_dict())
            flash("Client created. Add their accounts below.", "success")
            return redirect(url_for("clients.detail_view", client_id=cid))
    return render_template("clients/form.html", client=None, action="create")


@bp.route("/<int:client_id>")
@login_required
def detail_view(client_id):
    client = client_model.get_client(client_id)
    if not client:
        abort(404)
    accounts = account_model.list_accounts(client_id)
    reports = report_model.list_reports(client_id)
    return render_template(
        "clients/detail.html",
        client=client,
        accounts=accounts,
        reports=reports,
        age_c1=client_model.calculate_age(client.client1_dob),
        age_c2=client_model.calculate_age(client.client2_dob),
        type_options=account_model.ACCOUNT_TYPE_OPTIONS,
    )


@bp.route("/<int:client_id>/edit", methods=["GET", "POST"])
@login_required
def edit_view(client_id):
    client = client_model.get_client(client_id)
    if not client:
        abort(404)
    if request.method == "POST":
        if not request.form.get("client1_name"):
            flash("Client 1 name is required.", "error")
        else:
            client_model.update_client(client_id, request.form.to_dict())
            flash("Client updated.", "success")
            return redirect(url_for("clients.detail_view", client_id=client_id))
    return render_template("clients/form.html", client=client, action="edit")


@bp.route("/<int:client_id>/delete", methods=["POST"])
@login_required
def delete_view(client_id):
    client_model.delete_client(client_id)
    flash("Client deleted.", "success")
    return redirect(url_for("clients.list_view"))


@bp.route("/<int:client_id>/accounts", methods=["POST"])
@login_required
def add_account_view(client_id):
    client = client_model.get_client(client_id)
    if not client:
        abort(404)
    data = request.form.to_dict()
    if data.get("account_type_other"):
        data["account_type"] = data["account_type_other"]
    if not data.get("account_type"):
        flash("Account type is required.", "error")
        return redirect(url_for("clients.detail_view", client_id=client_id))
    # auto-suggest sacs role if not chosen
    if data.get("category") == "non_retirement" and not data.get("sacs_role"):
        data["sacs_role"] = account_model.auto_sacs_role(data["account_type"]) or ""
    account_model.create_account(client_id, data)
    flash("Account added.", "success")
    return redirect(url_for("clients.detail_view", client_id=client_id))


@bp.route("/<int:client_id>/accounts/<int:account_id>/delete", methods=["POST"])
@login_required
def delete_account_view(client_id, account_id):
    account_model.delete_account(account_id)
    flash("Account removed.", "success")
    return redirect(url_for("clients.detail_view", client_id=client_id))
