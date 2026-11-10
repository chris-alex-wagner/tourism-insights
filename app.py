"""Tourism Insights – a Flask web app on short-term rental tourism in Europe.

Pages
  /          Home
  /explore   Map and Top 10 ranking for countries or NUTS 2 regions
  /country   Country Insights: key figures, seasonal heatmaps, top regions
  /model     Housing price model: compares four ML models

Run locally:  python app.py  ->  http://127.0.0.1:5000
"""
from pathlib import Path

from flask import Flask, abort, jsonify, render_template, request, url_for

import country_insights as ci
import predictions
from data_prep import INDICATORS, MONTH_NAMES, RESIDENCE, YEARS, data, indicator_values, region_name

app = Flask(__name__)


def facts():
    return {
        "countries": int(data.loc[data["level"] == 0, "geo"].nunique()),
        "regions": int(data.loc[data["level"] == 2, "geo"].nunique()),
        "first_year": YEARS[0], "last_year": YEARS[-1],
    }


@app.context_processor
def common():
    return {"indicators": INDICATORS, "residence": RESIDENCE, "years": YEARS, "months": MONTH_NAMES,
            "asset": asset_url}


def asset_url(filename):
    """URL of a static file with a version stamp, so browsers never use an outdated cached copy."""
    path = Path(app.static_folder) / filename
    version = int(path.stat().st_mtime) if path.exists() else 0
    return url_for("static", filename=filename, v=version)


# ----------------------------------------------------------------------------- pages
@app.route("/")
def home():
    return render_template("home.html", facts=facts(), active="home")


@app.route("/explore")
def explore():
    return render_template("explore.html", active="explore")


@app.route("/country")
def country():
    return render_template("country.html", countries=ci.countries(), active="country")


@app.route("/model")
def model():
    return render_template("model.html", active="model")


# ----------------------------------------------------------------------------- data API
def arg(name, default, cast=str, allowed=None):
    value = request.args.get(name, default)
    try:
        value = cast(value)
    except ValueError:
        abort(400, f"Invalid {name}")
    if allowed is not None and value not in allowed:
        abort(400, f"Invalid {name}")
    return value


@app.route("/api/explore")
def api_explore():
    level = arg("level", 0, int, {0, 2})
    indicator = arg("indicator", "stays", str, INDICATORS)
    resid = arg("resid", "TOTAL", str, RESIDENCE)
    year = arg("year", YEARS[-1], int, YEARS)
    month = arg("month", 0, int, range(13))
    df = indicator_values(indicator, level=level, resid=resid, year=year, month=month)
    items = [{"geo": g, "name": region_name(g), "value": float(v)}
             for g, v in df.sort_values("value", ascending=False)[["geo", "value"]].itertuples(index=False)]
    return jsonify({"items": items, "indicator": INDICATORS[indicator]})


@app.route("/api/country/<code>")
def api_country(code):
    if code not in {c["code"] for c in ci.countries()}:
        abort(404)
    year = arg("year", YEARS[-1], int, YEARS)
    level = arg("level", 1, int, {1, 2})
    indicator = arg("indicator", "guest_nights", str, INDICATORS)
    return jsonify({
        "name": region_name(code),
        "stats": ci.country_statistics(code, year, level),
        "heatmap": ci.heatmap_data(code, year, level, indicator),
        "trend": ci.top_regions_trend(code, year, level, indicator),
        "indicator": INDICATORS[indicator],
    })


@app.route("/api/model")
def api_model():
    cv_type = arg("cv", "simple", str, {"simple", "nested"})
    return jsonify(predictions.run(cv_type))


if __name__ == "__main__":
    app.run(debug=True)
