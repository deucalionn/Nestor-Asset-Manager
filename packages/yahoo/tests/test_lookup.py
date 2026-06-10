import pandas as pd
from nam_yahoo.lookup import dataframe_to_lookup_rows, pick_lookup_row


def test_pick_lookup_row_prefers_paris_suffix() -> None:
    df = pd.DataFrame(
        {
            "shortName": ["Air Liquide", "Air Liquide"],
            "exchange": ["PAR", "GER"],
            "quoteType": ["equity", "equity"],
        },
        index=["AI.PA", "AILA.DU"],
    )
    rows = dataframe_to_lookup_rows(df)
    hit = pick_lookup_row(rows, prefer_suffix=".PA")
    assert hit.yahoo_symbol == "AI.PA"
