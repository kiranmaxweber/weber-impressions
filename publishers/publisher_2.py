"""Publisher 2 — JSON with their own field names, Spanish status values, dd/mm/yyyy dates.

Three normalisations: rename the fields, map the statuses, reformat the dates.
"""

import requests

URL = "https://oditzhgdrnvfjtmwkdeq.supabase.co"
KEY = "sb_publishable_Z2FJtKzujZflPsTLsaM6Aw_l3L5BRbh"  # read-only by RLS; safe to commit

STATUS = {
    "pendiente": "pending",
    "enviado": "shipped",
    "entregado": "delivered",
    "cancelado": "cancelled",
}


def iso(date):
    """'19/08/2026' -> '2026-08-19'. Their export format is text, not a date."""
    if not date:
        return None
    day, month, year = date.split("/")
    return f"{year}-{month}-{day}"


def lookup(order_number):
    r = requests.get(
        f"{URL}/rest/v1/pedidos",
        params={"referencia_tienda": f"eq.{order_number}", "select": "*"},
        headers={"apikey": KEY},
        timeout=10,
    )
    r.raise_for_status()
    rows = r.json()
    if not rows:
        return None
    row = rows[0]
    return {
        "publisher": 2,
        "title": row["titulo"],
        "author": row["autor"],
        "status": STATUS.get(row["estado"], row["estado"]),
        "dispatched_on": iso(row["fecha_envio"]),
        "estimated_delivery": iso(row["entrega_estimada"]),
        "carrier": row["paqueteria"],
        "tracking_number": row["numero_guia"],
    }
