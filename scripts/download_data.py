"""Download the Eurostat dataset tour_ce_omn12 and save it as data/tour_ce_omn12.csv.

Run once (and again whenever you want fresher data):
    python scripts/download_data.py
"""
from datetime import date
from pathlib import Path

import eurostat

DATASET = "tour_ce_omn12"
out = Path(__file__).resolve().parent.parent / "data" / f"{DATASET}.csv"

print(f"Downloading {DATASET} from Eurostat ...")
df = eurostat.get_data_df(DATASET)
out.parent.mkdir(exist_ok=True)
df.to_csv(out, index=False)
(out.parent / f"{DATASET}_downloaded.txt").write_text(f"Downloaded from Eurostat on {date.today().isoformat()}\n")
print(f"Saved {len(df):,} rows to {out}")
