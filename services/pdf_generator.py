"""
PDF generation for SACS and TCC reports using ReportLab.

Both reports are drawn directly on the canvas for pixel-stable layout — exactly
what Rebecca asked for ("we want the form set so nothing can move").
"""
from __future__ import annotations

import io
from datetime import datetime

from reportlab.lib.colors import HexColor, white
from reportlab.lib.pagesizes import LETTER, landscape
from reportlab.pdfgen import canvas


# -----------------------------------------------------------------------------
# Colors (matching the Andrew/Rebecca templates)
# -----------------------------------------------------------------------------
GREEN_INFLOW = HexColor("#2f8a3d")
GREEN_INFLOW_DARK = HexColor("#1f5f29")
RED_OUTFLOW = HexColor("#c0392b")
RED_OUTFLOW_DARK = HexColor("#8b271b")
BLUE_PRIVATE = HexColor("#2f5f99")
BLUE_PRIVATE_DARK = HexColor("#1f3f6f")
LIGHT_BLUE_FICA = HexColor("#c8d8e8")
DARK_BLUE_INVEST = HexColor("#1f3a5f")
GRAY_BOX = HexColor("#bfc4ca")
GRAY_LIGHT = HexColor("#e8eaed")
TEXT_DARK = HexColor("#1a1f2c")
MUTED = HexColor("#6b7280")
GREEN_CLIENT = HexColor("#8aa667")
DANGER = HexColor("#c0392b")


# -----------------------------------------------------------------------------
# Helpers
# -----------------------------------------------------------------------------
def _money(v, decimals=0, suffix=""):
    if v is None:
        return "—"
    try:
        if decimals:
            return f"${float(v):,.{decimals}f}{suffix}"
        return f"${float(v):,.0f}{suffix}"
    except (TypeError, ValueError):
        return str(v)


def _money_with_star(v, stale: bool, decimals=0, suffix=""):
    s = _money(v, decimals=decimals, suffix=suffix)
    return f"{s}*" if stale else s


def _stale(value_date, report_date) -> bool:
    return bool(value_date and report_date and value_date < report_date)


def _draw_circle(c, cx, cy, r, fill, stroke=None, stroke_width=0):
    c.saveState()
    c.setFillColor(fill)
    if stroke:
        c.setStrokeColor(stroke)
        c.setLineWidth(stroke_width)
        c.circle(cx, cy, r, stroke=1, fill=1)
    else:
        c.circle(cx, cy, r, stroke=0, fill=1)
    c.restoreState()


def _draw_text_center(c, x, y, text, font="Helvetica", size=10, color=TEXT_DARK):
    c.setFont(font, size)
    c.setFillColor(color)
    c.drawCentredString(x, y, str(text))


def _draw_arrow(c, x1, y1, x2, y2, color, thickness=18, head_size=14, bidirectional=False):
    """Draw a chunky filled arrow (rectangle body + triangle head)."""
    import math
    c.saveState()
    c.setFillColor(color)
    c.setStrokeColor(color)
    dx = x2 - x1
    dy = y2 - y1
    length = math.hypot(dx, dy)
    if length == 0:
        c.restoreState()
        return
    ux, uy = dx / length, dy / length
    # perpendicular unit vector
    px, py = -uy, ux

    head_len = head_size
    body_len = length - head_len
    if bidirectional:
        body_len -= head_len
        body_start = x1 + ux * head_len, y1 + uy * head_len
    else:
        body_start = x1, y1

    # Rectangle body
    bx, by = body_start
    half = thickness / 2
    p = c.beginPath()
    p.moveTo(bx + px * half, by + py * half)
    p.lineTo(bx + ux * body_len + px * half, by + uy * body_len + py * half)
    p.lineTo(bx + ux * body_len - px * half, by + uy * body_len - py * half)
    p.lineTo(bx - px * half, by - py * half)
    p.close()
    c.drawPath(p, fill=1, stroke=0)

    # Forward arrowhead at (x2, y2)
    head_base_x = x2 - ux * head_len
    head_base_y = y2 - uy * head_len
    half_head = thickness  # head wider than body
    p = c.beginPath()
    p.moveTo(x2, y2)
    p.lineTo(head_base_x + px * half_head, head_base_y + py * half_head)
    p.lineTo(head_base_x - px * half_head, head_base_y - py * half_head)
    p.close()
    c.drawPath(p, fill=1, stroke=0)

    if bidirectional:
        # Arrowhead at (x1, y1)
        head_base_x = x1 + ux * head_len
        head_base_y = y1 + uy * head_len
        p = c.beginPath()
        p.moveTo(x1, y1)
        p.lineTo(head_base_x + px * half_head, head_base_y + py * half_head)
        p.lineTo(head_base_x - px * half_head, head_base_y - py * half_head)
        p.close()
        c.drawPath(p, fill=1, stroke=0)

    c.restoreState()


def _draw_dashed_line(c, x1, y1, x2, y2, color=MUTED, width=1.5, dash=(4, 3)):
    c.saveState()
    c.setStrokeColor(color)
    c.setLineWidth(width)
    c.setDash(dash[0], dash[1])
    c.line(x1, y1, x2, y2)
    c.restoreState()


def _draw_money_pill(c, x, y, w, h, label, fill=white, border=TEXT_DARK):
    """Small white pill showing the dollar amount inside a circle."""
    c.saveState()
    c.setFillColor(fill)
    c.setStrokeColor(border)
    c.setLineWidth(0.6)
    c.roundRect(x - w / 2, y - h / 2, w, h, 3, stroke=1, fill=1)
    c.setFillColor(TEXT_DARK)
    c.setFont("Helvetica-Bold", 12)
    c.drawCentredString(x, y - 4, label)
    c.restoreState()


def _draw_floor_pill(c, cx, y, label):
    c.saveState()
    c.setFillColor(HexColor("#d9e7d9"))
    c.setStrokeColor(HexColor("#9ab39a"))
    c.setLineWidth(0.4)
    w = 60
    c.roundRect(cx - w / 2, y - 6, w, 12, 3, stroke=1, fill=1)
    c.setFillColor(TEXT_DARK)
    c.setFont("Helvetica", 7)
    c.drawCentredString(cx, y - 3, label)
    c.restoreState()


def _wrap_left(c, x, y, text, font="Helvetica", size=9, color=MUTED, leading=11):
    c.setFont(font, size)
    c.setFillColor(color)
    for line in str(text).split("\n"):
        c.drawString(x, y, line)
        y -= leading


# -----------------------------------------------------------------------------
# SACS — 2 pages
# -----------------------------------------------------------------------------
def render_sacs_pdf(snapshot: dict) -> bytes:
    buf = io.BytesIO()
    c = canvas.Canvas(buf, pagesize=LETTER)
    width, height = LETTER

    client_name = _client_display_name(snapshot["client"])
    report_date = snapshot["report_date"]

    # ---------- PAGE 1: MONTHLY CASHFLOW ----------
    _sacs_header(c, width, height, client_name, report_date)

    sacs = snapshot["sacs"]
    inflow = sacs.get("inflow", 0)
    outflow = sacs.get("outflow", 0)
    excess = sacs.get("excess", 0)
    floor = snapshot["client"].get("account_floor", 1000)

    # Top-left: per-spouse salary breakdown + dollar-sign accent
    c.setFillColor(GREEN_INFLOW)
    c.setFont("Helvetica-Bold", 30)
    c.drawString(50, height - 100, "$")
    c.setFont("Helvetica", 8)
    c.setFillColor(GREEN_INFLOW_DARK)
    c1_name = snapshot["client"].get("client1_name") or "Client 1"
    c2_name = snapshot["client"].get("client2_name")
    c1_salary = snapshot["client"].get("client1_salary") or 0
    c2_salary = snapshot["client"].get("client2_salary") or 0
    c.drawString(75, height - 95, f"{_money(c1_salary)} - {c1_name}")
    if c2_name:
        c.drawString(75, height - 105, f"{_money(c2_salary)} - {c2_name}")

    # Top-right: "X = Monthly Expenses" annotation
    c.setFont("Helvetica", 9)
    c.setFillColor(TEXT_DARK)
    c.drawRightString(width - 50, height - 100, "X = Monthly")
    c.drawRightString(width - 50, height - 112, "Expenses")
    # bills icon (stylized stack of rectangles)
    c.setFillColor(HexColor("#8a9a8a"))
    c.setStrokeColor(HexColor("#4a5a4a"))
    c.setLineWidth(0.5)
    for i, off in enumerate([0, 3, 6]):
        c.roundRect(width - 90 + off, height - 85 - off, 30, 18, 2, stroke=1, fill=1)

    # ---- Inflow circle (top-left area) ----
    inflow_cx, inflow_cy, r = 175, height - 220, 80
    _draw_circle(c, inflow_cx, inflow_cy, r, GREEN_INFLOW)
    _draw_text_center(c, inflow_cx, inflow_cy + 28, "INFLOW", font="Helvetica-Bold", size=14, color=white)
    _draw_money_pill(c, inflow_cx, inflow_cy - 5, 110, 26, _money(inflow))
    _draw_floor_pill(c, inflow_cx, inflow_cy - r + 6, f"{_money(floor)} Floor")

    # ---- Outflow circle (top-right area) ----
    outflow_cx, outflow_cy = width - 175, height - 220
    _draw_circle(c, outflow_cx, outflow_cy, r, RED_OUTFLOW)
    _draw_text_center(c, outflow_cx, outflow_cy + 28, "OUTFLOW", font="Helvetica-Bold", size=14, color=white)
    outflow_label = _money(outflow)
    _draw_money_pill(c, outflow_cx, outflow_cy - 5, 110, 26, outflow_label)
    _draw_floor_pill(c, outflow_cx, outflow_cy - r + 6, f"{_money(floor)} Floor")

    # ---- Red arrow Inflow → Outflow ----
    arrow_start_x = inflow_cx + r + 6
    arrow_end_x = outflow_cx - r - 6
    arrow_y = inflow_cy + 5
    _draw_arrow(c, arrow_start_x, arrow_y, arrow_end_x, arrow_y, RED_OUTFLOW, thickness=22, head_size=18)
    # Label inside / above the arrow
    mid_x = (arrow_start_x + arrow_end_x) / 2
    c.setFillColor(white)
    c.setFont("Helvetica-Bold", 9)
    c.drawCentredString(mid_x, arrow_y - 2, f"X = {_money(outflow)}/month*")
    c.setFillColor(TEXT_DARK)
    c.setFont("Helvetica", 7)
    c.drawCentredString(mid_x, arrow_y - 16, "Automated transfer on the 28th")

    # ---- Private Reserve circle (center-bottom) ----
    pr_cx, pr_cy = width / 2, height - 380
    _draw_circle(c, pr_cx, pr_cy, 80, BLUE_PRIVATE)
    _draw_text_center(c, pr_cx, pr_cy + 28, "PRIVATE", font="Helvetica-Bold", size=13, color=white)
    _draw_text_center(c, pr_cx, pr_cy + 12, "RESERVE", font="Helvetica-Bold", size=13, color=white)
    # Tiny piggy-bank icon (stylized)
    _draw_piggy(c, pr_cx, pr_cy - 22)
    pr_balance = sacs.get("private_reserve")
    pr_stale_p1 = _stale(sacs.get("private_reserve_date"), report_date)
    if pr_balance is not None:
        _draw_money_pill(c, pr_cx, pr_cy - 50, 100, 22, _money_with_star(pr_balance, pr_stale_p1))

    # ---- Blue arrow Inflow → Private Reserve (down-right diagonal) ----
    blue_start_x, blue_start_y = inflow_cx + 20, inflow_cy - r - 6
    blue_end_x, blue_end_y = pr_cx - 90, pr_cy + 30
    _draw_arrow(c, blue_start_x, blue_start_y, blue_end_x, blue_end_y, HexColor("#5a8ac9"), thickness=18, head_size=14)
    # Label sits above-left of the arrow midpoint (outside the body so it doesn't get clipped)
    mid_blue_x = (blue_start_x + blue_end_x) / 2
    mid_blue_y = (blue_start_y + blue_end_y) / 2
    c.setFillColor(TEXT_DARK)
    c.setFont("Helvetica-Bold", 9)
    c.drawString(mid_blue_x - 70, mid_blue_y + 12, f"{_money(excess)}/mo*")

    # ---- MONTHLY CASHFLOW label + dashed line continuation ----
    c.setFont("Helvetica-Bold", 11)
    c.setFillColor(TEXT_DARK)
    c.drawCentredString(width / 2, height - 500, "MONTHLY  CASHFLOW")
    # Vertical dashed line stub from Private Reserve toward page bottom
    _draw_dashed_line(c, width / 2, pr_cy - 80, width / 2, 60, color=BLUE_PRIVATE_DARK, width=1.2, dash=(5, 4))

    # Footer: stale-data legend if any starred values appeared on page 1
    if pr_stale_p1 or _has_stale_inflow_outflow(sacs, report_date):
        _draw_legend(c, width, 40)

    c.showPage()

    # ---------- PAGE 2: LONG TERM CASHFLOW ----------
    _sacs_header(c, width, height, client_name, report_date)

    # Dashed-line stub at top (continuation from page 1)
    _draw_dashed_line(c, width / 2, height - 110, width / 2, height - 230, color=BLUE_PRIVATE_DARK, width=1.2, dash=(5, 4))

    # FICA Account (light blue) — left
    fica_cx, fica_cy, fr = width / 2 - 130, height - 320, 85
    _draw_circle(c, fica_cx, fica_cy, fr, LIGHT_BLUE_FICA)
    _draw_text_center(c, fica_cx, fica_cy + 22, "FICA", font="Helvetica-Bold", size=15, color=TEXT_DARK)
    _draw_text_center(c, fica_cx, fica_cy + 6, "ACCOUNT", font="Helvetica-Bold", size=15, color=TEXT_DARK)
    pr_balance_p2 = sacs.get("private_reserve")
    pr_stale_p2 = _stale(sacs.get("private_reserve_date"), report_date)
    _draw_money_pill(
        c, fica_cx, fica_cy - 20, 130, 24,
        _money_with_star(pr_balance_p2, pr_stale_p2) if pr_balance_p2 is not None else "—",
        fill=HexColor("#a8c0d8"),
    )
    c.setFont("Helvetica", 8)
    c.setFillColor(TEXT_DARK)
    c.drawCentredString(fica_cx, fica_cy - fr - 12, "6X Monthly Expenses + Deductibles")
    target = sacs.get("target")
    if target:
        c.setFillColor(MUTED)
        c.setFont("Helvetica-Oblique", 8)
        c.drawCentredString(fica_cx, fica_cy - fr - 24, f"(target: {_money(target)})")

    # Investment Account (dark blue) — right
    inv_cx, inv_cy = width / 2 + 130, height - 320
    _draw_circle(c, inv_cx, inv_cy, fr, DARK_BLUE_INVEST)
    _draw_text_center(c, inv_cx, inv_cy + 22, "INVESTMENT", font="Helvetica-Bold", size=14, color=white)
    _draw_text_center(c, inv_cx, inv_cy + 6, "ACCOUNT", font="Helvetica-Bold", size=14, color=white)
    inv_balance = sacs.get("investment")
    inv_stale = _stale(sacs.get("investment_date"), report_date)
    inv_label = (
        f"{_money(inv_balance)}+" if inv_balance is not None else "—"
    )
    if inv_stale and inv_balance is not None:
        inv_label += "*"
    _draw_money_pill(c, inv_cx, inv_cy - 20, 130, 24, inv_label, fill=white, border=TEXT_DARK)
    c.setFont("Helvetica", 8)
    c.setFillColor(TEXT_DARK)
    c.drawCentredString(inv_cx, inv_cy - fr - 12, "Remainder")

    # Bidirectional arrow between FICA and Investment
    arrow_left = fica_cx + fr + 6
    arrow_right = inv_cx - fr - 6
    _draw_arrow(c, arrow_left, fica_cy, arrow_right, fica_cy,
                DARK_BLUE_INVEST, thickness=24, head_size=20, bidirectional=True)

    # Section labels at the bottom
    c.setFont("Helvetica-Bold", 12)
    c.setFillColor(TEXT_DARK)
    c.drawCentredString(width / 2, 130, "LONG TERM  CASHFLOW")
    c.setFont("Helvetica-Oblique", 10)
    c.setFillColor(HexColor("#3a6ea8"))
    c.drawCentredString(width / 2, 115, "(Magnified Private Reserve Cashflow)")

    if pr_stale_p2 or inv_stale:
        _draw_legend(c, width, 60)

    c.save()
    return buf.getvalue()


def _has_stale_inflow_outflow(sacs, report_date) -> bool:
    return _stale(sacs.get("private_reserve_date"), report_date)


def _draw_piggy(c, x, y):
    """Simple piggy-bank icon."""
    c.saveState()
    c.setFillColor(HexColor("#e08a9a"))
    c.setStrokeColor(HexColor("#a85a6a"))
    c.setLineWidth(0.6)
    # body (ellipse)
    c.ellipse(x - 18, y - 9, x + 18, y + 9, stroke=1, fill=1)
    # ear
    p = c.beginPath()
    p.moveTo(x + 8, y + 8)
    p.lineTo(x + 14, y + 14)
    p.lineTo(x + 14, y + 8)
    p.close()
    c.drawPath(p, stroke=1, fill=1)
    # snout
    c.ellipse(x + 12, y - 3, x + 19, y + 3, stroke=1, fill=1)
    # legs
    c.rect(x - 10, y - 14, 4, 6, stroke=1, fill=1)
    c.rect(x + 4, y - 14, 4, 6, stroke=1, fill=1)
    # coin slot
    c.setFillColor(HexColor("#8a4555"))
    c.rect(x - 6, y + 7, 10, 1.5, stroke=0, fill=1)
    c.restoreState()


def _sacs_header(c, width, height, client_name, report_date):
    c.setFillColor(TEXT_DARK)
    c.setFont("Helvetica-Bold", 16)
    c.drawCentredString(width / 2, height - 50, "Simple Automated Cashflow System (SACS)")
    c.setFont("Helvetica-Bold", 12)
    c.drawCentredString(width / 2, height - 70, client_name)
    c.setFont("Helvetica", 9)
    c.setFillColor(MUTED)
    c.drawCentredString(width / 2, height - 83, f"as of {report_date}")


def _draw_legend(c, width, y):
    c.setFont("Helvetica-Oblique", 8)
    c.setFillColor(DANGER)
    c.drawRightString(width - 40, y, "* Indicates we do not have up to date information")


def _client_display_name(client: dict) -> str:
    n1 = client.get("client1_name") or "Client"
    n2 = client.get("client2_name")
    return f"{n1} & {n2}" if n2 else n1


# -----------------------------------------------------------------------------
# TCC — single landscape page with variable account bubbles
# -----------------------------------------------------------------------------
def render_tcc_pdf(snapshot: dict) -> bytes:
    buf = io.BytesIO()
    page_size = landscape(LETTER)
    c = canvas.Canvas(buf, pagesize=page_size)
    width, height = page_size

    client = snapshot["client"]
    accounts = snapshot["accounts"]
    tcc = snapshot["tcc"]
    report_date = snapshot["report_date"]

    # Header (top-left, kept entirely above the grand-total band)
    c.setFont("Helvetica-Bold", 9)
    c.setFillColor(TEXT_DARK)
    c.drawString(40, height - 22, f"NAME      {_client_display_name(client)}")
    c.drawString(40, height - 34, f"DATE       {_format_report_date(report_date)}")

    # Grand total box (top center) — shifted further down to clear the header band
    grand_w = 150
    grand_x = width / 2 - grand_w / 2
    grand_y = height - 78
    c.setFillColor(GRAY_BOX)
    c.rect(grand_x, grand_y, grand_w, 26, stroke=0, fill=1)
    c.setFillColor(white)
    c.setFont("Helvetica-Bold", 9)
    c.drawCentredString(width / 2, grand_y + 15, "GRAND TOTAL")
    c.setFont("Helvetica-Bold", 11)
    c.drawCentredString(width / 2, grand_y + 3, _money(tcc.get("grand_total"), decimals=2))

    # Client 1 / Client 2 green bubbles flanking the grand-total box. The bubble
    # only has room for a short title — the full name is in the NAME header above,
    # matching the customer's existing template convention.
    c1_bubble_cx = width / 2 - 130
    c2_bubble_cx = width / 2 + 130
    bubble_y = grand_y + 12
    _draw_client_info_bubble(c, c1_bubble_cx, bubble_y, "Client 1",
                             client.get("client1_age"), client.get("client1_dob"), client.get("client1_ssn_last4"))
    if client.get("client2_name"):
        _draw_client_info_bubble(c, c2_bubble_cx, bubble_y, "Client 2",
                                 client.get("client2_age"), client.get("client2_dob"), client.get("client2_ssn_last4"))

    # Per-spouse retirement summary boxes (gray) flanking outermost.
    # Labels follow the customer's existing convention: "Client 1 Retirement Only".
    _draw_summary_box(c, 80, grand_y + 12, "Client 1 Retirement Only", _money(tcc.get("client1_retirement"), decimals=2))
    if client.get("client2_name"):
        _draw_summary_box(c, width - 80, grand_y + 12, "Client 2 Retirement Only", _money(tcc.get("client2_retirement"), decimals=2))

    # Liabilities summary box (light gray, just below grand total)
    liab_total = tcc.get("liabilities") or 0
    c.setFillColor(GRAY_LIGHT)
    c.setStrokeColor(MUTED)
    c.setLineWidth(0.5)
    c.rect(width / 2 - 75, grand_y - 16, 150, 12, stroke=1, fill=1)
    c.setFillColor(TEXT_DARK)
    c.setFont("Helvetica", 8)
    c.drawCentredString(width / 2, grand_y - 13, f"Liabilities:  {_money(liab_total, decimals=2)}")

    # Horizontal divider between retirement (top) and non-retirement (bottom)
    divider_y = height / 2 - 20
    c.setStrokeColor(MUTED)
    c.setLineWidth(0.5)
    c.line(40, divider_y, width - 40, divider_y)

    # Section labels
    c.setFont("Helvetica-Bold", 8)
    c.setFillColor(HexColor("#558040"))
    c.drawString(50, divider_y + 8, "RETIREMENT")
    c.drawRightString(width - 50, divider_y + 8, "RETIREMENT")
    c.drawString(50, divider_y - 18, "NON")
    c.drawString(50, divider_y - 28, "RETIREMENT")
    c.drawRightString(width - 50, divider_y - 18, "NON")
    c.drawRightString(width - 50, divider_y - 28, "RETIREMENT")

    # --- Bubble layout ---
    # 4 quadrants for accounts, center column for trust + grand-total + liabilities

    # Bubble dimensions — keep tight enough that 3 rows fit per quadrant
    bub_r = 32
    bub_gap_x = 82
    bub_gap_y = 70

    def _draw_account_bubble(cx, cy, account):
        _draw_circle(c, cx, cy, bub_r, white, stroke=TEXT_DARK, stroke_width=0.7)
        lines = [f"ACCT #"]
        if account.get("account_type"):
            lines.append(account["account_type"])
        bal = account.get("balance")
        stale = account.get("stale")
        if bal is not None:
            lines.append(_money_with_star(bal, stale, decimals=2 if bal % 1 else 0))
        if account.get("value_date"):
            lines.append(f"{'*' if stale else ''}a/o {_format_short_date(account['value_date'])}")
        line_y = cy + 14
        for i, line in enumerate(lines):
            c.setFont("Helvetica-Bold" if i == 0 else "Helvetica", 7)
            c.setFillColor(TEXT_DARK)
            c.drawCentredString(cx, line_y, line)
            line_y -= 9
        # Inner cash bubble for investment accounts
        cash = account.get("cash_balance")
        if cash is not None:
            inner_r = 14
            c.setStrokeColor(TEXT_DARK)
            c.setLineWidth(0.6)
            c.setFillColor(white)
            c.circle(cx + bub_r * 0.5, cy - bub_r * 0.55, inner_r, stroke=1, fill=1)
            c.setFillColor(TEXT_DARK)
            c.setFont("Helvetica", 6)
            c.drawCentredString(cx + bub_r * 0.5, cy - bub_r * 0.55 + 2, _money(cash))
            c.setFont("Helvetica", 6)
            c.drawCentredString(cx + bub_r * 0.5, cy - bub_r * 0.55 - 5, "Cash")

    # Top half (retirement): client1 left, client2 right
    # top_y_start is the CENTER y of the first row of bubbles.
    # Bubbles extend bub_r above & below center, so leave room below the summary
    # boxes (around grand_y - 30) and above the divider (need bub_r clearance).
    top_y_start = grand_y - 60
    _layout_quadrant(
        c, draw=_draw_account_bubble,
        accounts=[a for a in accounts if a["category"] == "retirement" and a.get("owner") == "client1"],
        x_start=80, y_start=top_y_start, max_x=width / 2 - 100, max_y=divider_y + 20,
        bub_r=bub_r, gap_x=bub_gap_x, gap_y=bub_gap_y,
    )
    _layout_quadrant(
        c, draw=_draw_account_bubble,
        accounts=[a for a in accounts if a["category"] == "retirement" and a.get("owner") == "client2"],
        x_start=width / 2 + 100, y_start=top_y_start, max_x=width - 80, max_y=divider_y + 20,
        bub_r=bub_r, gap_x=bub_gap_x, gap_y=bub_gap_y,
    )
    # Bottom half (non-retirement): split by owner; joint + client1 on left, client2 on right
    bot_y_start = divider_y - 50
    bot_min_y = 80
    left_non = [a for a in accounts if a["category"] == "non_retirement" and a.get("owner") in (None, "joint", "client1")]
    right_non = [a for a in accounts if a["category"] == "non_retirement" and a.get("owner") == "client2"]
    _layout_quadrant(
        c, draw=_draw_account_bubble,
        accounts=left_non,
        x_start=80, y_start=bot_y_start, max_x=width / 2 - 100, max_y=bot_min_y,
        bub_r=bub_r, gap_x=bub_gap_x, gap_y=bub_gap_y, direction_y=-1,
    )
    _layout_quadrant(
        c, draw=_draw_account_bubble,
        accounts=right_non,
        x_start=width / 2 + 100, y_start=bot_y_start, max_x=width - 80, max_y=bot_min_y,
        bub_r=bub_r, gap_x=bub_gap_x, gap_y=bub_gap_y, direction_y=-1,
    )

    # Non-retirement totals box (bottom center, like the screenshot)
    nr_total = tcc.get("non_retirement") or 0
    c.setFillColor(GRAY_BOX)
    c.rect(width / 2 - 100, 50, 200, 26, stroke=0, fill=1)
    c.setFillColor(white)
    c.setFont("Helvetica-Bold", 9)
    c.drawCentredString(width / 2, 66, "NON RETIREMENT TOTAL")
    c.setFont("Helvetica-Bold", 11)
    c.drawCentredString(width / 2, 54, _money(nr_total, decimals=2))

    # Center column: Trust bubble + Liabilities list
    trust_accounts = [a for a in accounts if a["category"] == "trust"]
    trust_cy = divider_y + 60
    if trust_accounts:
        ta = trust_accounts[0]
        cx = width / 2
        cy = trust_cy
        r = 50
        _draw_circle(c, cx, cy, r, white, stroke=TEXT_DARK, stroke_width=0.7)
        c.setFont("Helvetica-Bold", 7)
        c.setFillColor(TEXT_DARK)
        c.drawCentredString(cx, cy + 22, "ACCT #")
        c.setFont("Helvetica", 7)
        c.drawCentredString(cx, cy + 12, (ta.get("account_type") or "Trust"))
        if ta.get("property_address"):
            c.drawCentredString(cx, cy + 2, ta["property_address"][:24])
        bal = ta.get("balance") or 0
        c.setFont("Helvetica-Bold", 8)
        c.drawCentredString(cx, cy - 8, _money(bal, decimals=2 if bal % 1 else 0))
        if ta.get("value_date"):
            stale = ta.get("stale")
            c.setFont("Helvetica", 6)
            c.drawCentredString(cx, cy - 18, f"{'*' if stale else ''}a/o {_format_short_date(ta['value_date'])}")

    # Liabilities table (center, below grand-total)
    liabilities = [a for a in accounts if a["category"] == "liability"]
    if liabilities:
        lx = width / 2 - 90
        ly = divider_y - 80
        box_h = 12 + len(liabilities) * 10
        c.setFillColor(GRAY_LIGHT)
        c.setStrokeColor(MUTED)
        c.setLineWidth(0.4)
        c.rect(lx, ly - box_h, 180, box_h, stroke=1, fill=1)
        c.setFillColor(TEXT_DARK)
        c.setFont("Helvetica-Bold", 7)
        c.drawString(lx + 6, ly - 10, "Liabilities:")
        c.setFont("Helvetica", 7)
        y = ly - 20
        for a in liabilities:
            name = (a.get("account_type") or "")[:24]
            c.drawString(lx + 6, y, name)
            bal = a.get("balance") or 0
            c.drawRightString(lx + 174, y, _money(bal, decimals=2))
            y -= 10

    # Stale-data legend (bottom-right) if any starred values exist
    any_stale = any(a.get("stale") for a in accounts)
    if any_stale:
        c.setFont("Helvetica-Oblique", 7)
        c.setFillColor(DANGER)
        c.drawRightString(width - 40, 38, "* Indicates we do not have up to date information")

    c.save()
    return buf.getvalue()


def _layout_quadrant(c, draw, accounts, x_start, y_start, max_x, max_y, bub_r, gap_x, gap_y, direction_y=1):
    """Grid layout: fill horizontally up to max_x, then wrap downward."""
    if not accounts:
        return
    available_w = max_x - x_start
    cols = max(1, int(available_w / gap_x))
    if len(accounts) < cols:
        cols = len(accounts)
    slot_w = available_w / cols
    for i, a in enumerate(accounts):
        row = i // cols
        col = i % cols
        cx = x_start + col * slot_w + slot_w / 2
        cy = y_start - row * gap_y
        draw(cx, cy, a)


def _draw_client_info_bubble(c, cx, cy, name, age, dob, ssn4):
    r = 30
    _draw_circle(c, cx, cy, r, GREEN_CLIENT, stroke=HexColor("#3a5a2a"), stroke_width=0.8)
    c.setFillColor(white)
    c.setFont("Helvetica-Bold", 8)
    c.drawCentredString(cx, cy + 14, name[:18])
    c.setFont("Helvetica", 7)
    c.drawCentredString(cx, cy + 4, f"Age  {age if age is not None else '—'}")
    c.drawCentredString(cx, cy - 4, f"DOB  {dob or '—'}")
    c.drawCentredString(cx, cy - 12, f"SSN  ****{ssn4 or ''}")


def _draw_summary_box(c, cx, cy, label, amount):
    w, h = 130, 28
    c.setFillColor(GRAY_BOX)
    c.rect(cx - w / 2, cy - h / 2, w, h, stroke=0, fill=1)
    c.setFillColor(white)
    c.setFont("Helvetica-Bold", 7)
    c.drawCentredString(cx, cy + 4, label.upper())
    c.setFont("Helvetica-Bold", 11)
    c.drawCentredString(cx, cy - 8, amount)


def _format_report_date(s: str) -> str:
    try:
        d = datetime.strptime(s, "%Y-%m-%d")
        return d.strftime("%B %d, %Y")
    except (TypeError, ValueError):
        return s or ""


def _format_short_date(s: str) -> str:
    try:
        d = datetime.strptime(s, "%Y-%m-%d")
        return d.strftime("%m/%d/%y")
    except (TypeError, ValueError):
        return s or ""
