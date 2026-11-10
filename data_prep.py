"""Load and prepare the Eurostat dataset tour_ce_omn12.

tour_ce_omn12 covers short-stay accommodation booked via online platforms
(Airbnb, Booking.com, Expedia Group, Tripadvisor) by month, residence of the guest
and NUTS region. Eurostat's example: a family of four staying three nights counts as
1 stay, 3 nights rented and 12 guest nights.

The raw data is read from a local snapshot (data/tour_ce_omn12.csv), created with
`python scripts/download_data.py`.
"""
import json
from pathlib import Path

import pandas as pd

DATA_DIR = Path(__file__).resolve().parent / "data"
RAW_FILE = DATA_DIR / "tour_ce_omn12.csv"
YEARS = list(range(2018, 2025))  # analysis period
MONTH_NAMES = ["January", "February", "March", "April", "May", "June", "July",
               "August", "September", "October", "November", "December"]

# Eurostat codes -> readable indicators
INDICATORS = {
    "stays": {"code": "STY", "label": "Stays", "unit": "stays",
              "help": "Number of bookings – one stay per booking, regardless of how many guests or nights."},
    "nights_rented": {"code": "LSTY", "label": "Nights rented", "unit": "nights",
                      "help": "Number of nights the accommodation was occupied (Eurostat: 'length of stay', summed over all stays)."},
    "guest_nights": {"code": "NGT_SP", "label": "Guest nights", "unit": "guest nights",
                     "help": "Nights rented multiplied by the number of guests (Eurostat: 'nights spent')."},
    "avg_length": {"code": None, "label": "Average length of stay", "unit": "nights per stay",
                   "help": "Nights rented divided by stays: how long a typical booking lasts."},
}
CODE_TO_KEY = {v["code"]: k for k, v in INDICATORS.items() if v["code"]}
RESIDENCE = {"TOTAL": "All guests", "DOM": "Domestic guests", "FOR": "Foreign guests"}

with open(DATA_DIR / "nuts_mapping.json", encoding="utf-8") as f:
    NUTS_NAMES = json.load(f)  # NUTS 2021 code -> name


def load_raw():
    if not RAW_FILE.exists():
        raise FileNotFoundError(
            f"{RAW_FILE} not found. Run 'python scripts/download_data.py' once to download the Eurostat data.")
    return pd.read_csv(RAW_FILE, dtype=str).rename(columns={"geo\\TIME_PERIOD": "geo"})


def build_tidy(raw):
    """One row per region, indicator, guest residence, year and month (month 0 = whole year)."""
    year_cols = [str(y) for y in YEARS if str(y) in raw.columns]
    df = raw.melt(id_vars=["indic_to", "c_resid", "month", "geo"], value_vars=year_cols,
                  var_name="year", value_name="value")
    df["value"] = pd.to_numeric(df["value"], errors="coerce")
    df = df.dropna(subset=["value"])
    # Keep NUTS 2021 regions only (newer NUTS 2024 codes would double-count regions in 2024)
    df = df[df["geo"].isin(NUTS_NAMES) & (df["geo"] != "EU27_2020")]
    df["indicator"] = df["indic_to"].map(CODE_TO_KEY)
    df["year"] = df["year"].astype(int)
    df["month"] = df["month"].str.replace("M", "", regex=False).replace("TOTAL", "0").astype(int)
    df["level"] = df["geo"].str.len() - 2  # 0 = country, 1 = NUTS 1, 2 = NUTS 2
    df = df.rename(columns={"c_resid": "resid"})
    return df[["geo", "level", "indicator", "resid", "year", "month", "value"]].reset_index(drop=True)


data = build_tidy(load_raw())


def region_name(code):
    return NUTS_NAMES.get(code, code)


def indicator_values(indicator, **filters):
    """Values per region for an indicator; 'avg_length' is derived as nights rented / stays."""
    sub = data
    for col, val in filters.items():
        sub = sub[sub[col] == val]
    if indicator != "avg_length":
        return sub[sub["indicator"] == indicator]
    keys = [c for c in ["geo", "level", "resid", "year", "month"] if c in sub.columns]
    nights = sub[sub["indicator"] == "nights_rented"].set_index(keys)["value"]
    stays = sub[sub["indicator"] == "stays"].set_index(keys)["value"]
    ratio = (nights / stays).dropna()
    ratio = ratio[stays.reindex(ratio.index) > 0]
    out = ratio.rename("value").reset_index()
    out["indicator"] = "avg_length"
    return out
