"""Publisher 3 — an unstructured integration. One confirmation email per order, in French.

There is no status field and no date column. The adapter hands the email to the model and
the model reads it. No regex, no date parsing here — the text is the record.
"""

import requests

URL = "https://cmtqkovuvneupzdbeszu.supabase.co"
KEY = "sb_publishable_zjWWMNZPbco-0WLxJoe5Qg_qOC6_Q9d"  # read-only by RLS; safe to commit


def lookup(order_number):
    r = requests.get(
        f"{URL}/rest/v1/commandes",
        params={"reference": f"eq.{order_number}", "select": "*"},
        headers={"apikey": KEY},
        timeout=10,
    )
    r.raise_for_status()
    rows = r.json()
    if not rows:
        return None
    row = rows[0]
    return {
        "publisher": 3,
        "received": row["recu_le"],
        "raw_email": row["raw_email"],
        "note": "Publisher 3 sends no structured status. Read the email.",
    }
