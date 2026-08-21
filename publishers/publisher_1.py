"""Publisher 1 — a clean JSON API. The row is already the shape we use internally."""

import requests

URL = "https://ahembfwcterdgkkakpuv.supabase.co"
KEY = "sb_publishable_f-IB5M8UJKPk2t_kbv1_yA_iPLy9DZB"  # read-only by RLS; safe to commit


def lookup(order_number):
    r = requests.get(
        f"{URL}/rest/v1/orders",
        params={"marketplace_ref": f"eq.{order_number}", "select": "*"},
        headers={"apikey": KEY},
        timeout=10,
    )
    r.raise_for_status()
    rows = r.json()
    if not rows:
        return None
    row = rows[0]
    return {
        "publisher": 1,
        "title": row["title"],
        "author": row["author"],
        "status": row["status"],
        "dispatched_on": row["dispatched_on"],
        "estimated_delivery": row["estimated_delivery"],
        "carrier": row["carrier"],
        "tracking_number": row["tracking_number"],
    }
