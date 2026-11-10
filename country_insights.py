"""Country Insights: statistics, heatmap and top-region trends for one country and year.

Author: Christian Wagner
"""
from data_prep import MONTH_NAMES, NUTS_NAMES, data, indicator_values, region_name


def label(code):
    """Region name; NUTS 2 regions that cover a whole NUTS 1 region (e.g. Berlin) are marked."""
    name = region_name(code)
    if len(code) == 4 and NUTS_NAMES.get(code[:3]) == name:
        return name + " ¹"
    return name


def countries():
    codes = sorted(data.loc[data["level"] == 0, "geo"].unique())
    return sorted(({"code": c, "name": region_name(c)} for c in codes), key=lambda x: x["name"])


def _total(indicator, country, year=None, resid="TOTAL", month=0):
    sub = data[(data["geo"] == country) & (data["indicator"] == indicator) &
               (data["resid"] == resid) & (data["month"] == month)]
    if year is not None:
        sub = sub[sub["year"] == year]
    return float(sub["value"].sum()) if not sub.empty else None


def country_statistics(country, year, level):
    """Key figures for the statistics table."""
    stays_year = _total("stays", country, year)
    stays_foreign = _total("stays", country, year, resid="FOR")

    monthly = data[(data["geo"] == country) & (data["indicator"] == "stays") & (data["resid"] == "TOTAL") &
                   (data["year"] == year) & (data["month"] > 0)]
    peak = monthly.loc[monthly["value"].idxmax()] if not monthly.empty else None

    def avg_length(resid):
        nights = _total("nights_rented", country, year, resid=resid)
        stays = _total("stays", country, year, resid=resid)
        return nights / stays if nights and stays else None

    regions = indicator_values("avg_length", level=level, resid="TOTAL", year=year, month=0)
    regions = regions[regions["geo"].str.startswith(country)]
    longest = regions.loc[regions["value"].idxmax()] if not regions.empty else None

    return {
        "stays_all_years": _total("stays", country),
        "stays_year": stays_year,
        "share_foreign": (stays_foreign / stays_year * 100) if stays_year and stays_foreign is not None else None,
        "peak_month": MONTH_NAMES[int(peak["month"]) - 1] if peak is not None else None,
        "peak_month_stays": float(peak["value"]) if peak is not None else None,
        "avg_length": {"TOTAL": avg_length("TOTAL"), "DOM": avg_length("DOM"), "FOR": avg_length("FOR")},
        "longest_region": region_name(longest["geo"]) if longest is not None else None,
        "longest_region_value": float(longest["value"]) if longest is not None else None,
    }


def _regions_monthly(country, year, level, indicator, resid):
    sub = indicator_values(indicator, level=level, resid=resid, year=year)
    sub = sub[sub["geo"].str.startswith(country) & (sub["month"] > 0)]
    return sub


def heatmap_data(country, year, level, indicator):
    """Month x region matrix for domestic and foreign guests (same regions and order for both)."""
    frames = {r: _regions_monthly(country, year, level, indicator, r) for r in ("DOM", "FOR")}
    totals = _regions_monthly(country, year, level, indicator, "TOTAL").groupby("geo")["value"].sum()
    regions = list(totals.sort_values(ascending=False).index) or sorted(
        set(frames["DOM"]["geo"]) | set(frames["FOR"]["geo"]))
    result = {"regions": [label(g) for g in regions], "codes": regions, "months": MONTH_NAMES}
    for resid, df in frames.items():
        pivot = df.pivot_table(index="geo", columns="month", values="value", aggfunc="sum")
        pivot = pivot.reindex(index=regions, columns=range(1, 13))
        result[resid] = [[None if v != v else float(v) for v in row] for row in pivot.values.tolist()]
    return result


def top_regions_trend(country, year, level, indicator, n=3):
    """Monthly values of the n largest regions (by yearly total), for domestic and foreign guests."""
    result = {}
    for resid in ("DOM", "FOR"):
        df = _regions_monthly(country, year, level, indicator, resid)
        top = df.groupby("geo")["value"].sum().nlargest(n).index
        series = []
        for geo in top:
            s = df[df["geo"] == geo].set_index("month")["value"].reindex(range(1, 13))
            series.append({"name": label(geo), "code": geo, "values": [None if v != v else float(v) for v in s]})
        result[resid] = series
    result["months"] = MONTH_NAMES
    return result
