"""The customer context the portal supplies. Resolved before anyone types.

This is Weber Impressions' own record of the order — what was bought, from whom, and what
has been charged. Fulfilment status belongs to each publisher and is fetched live.
"""

ORDER = {
    "number": "94105",
    "placed": "2026-08-17",
    "total_usd": 305.00,
    "ship_to": "United States",
    "lines": [
        {"publisher": 1, "title": "Portraits", "author": "William Eggleston", "price_usd": 120.00, "charged": True},
        {"publisher": 2, "title": "Cape Light", "author": "Joel Meyerowitz", "price_usd": 100.00, "charged": True},
        {"publisher": 3, "title": "Modern Color", "author": "Fred Herzog", "price_usd": 85.00, "charged": False},
    ],
}


def line_for(publisher):
    for line in ORDER["lines"]:
        if line["publisher"] == publisher:
            return line
    return None
