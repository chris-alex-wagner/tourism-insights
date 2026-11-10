"""Predictive model testing: can tourism and socio-economic indicators predict the yearly
change in housing prices of a country?

Features (standardised, one row per country and year): short-term rental stays, nights and
length of stay (domestic and foreign), share of population with tertiary education,
share of households with internet access, plus year and country indicators.
Target: yearly change of the house price index.
"""
from functools import lru_cache
from pathlib import Path

import numpy as np
import pandas as pd
from sklearn.ensemble import RandomForestRegressor
from sklearn.linear_model import Lasso, LinearRegression
from sklearn.metrics import mean_absolute_error, mean_absolute_percentage_error, mean_squared_error, r2_score
from sklearn.model_selection import KFold, RandomizedSearchCV, cross_validate, train_test_split
from sklearn.preprocessing import KBinsDiscretizer
from sklearn.svm import SVR

DATA_DIR = Path(__file__).resolve().parent / "data"
SEED = 42


def load_datasets():
    X = pd.read_csv(DATA_DIR / "merged_dataX.csv", index_col=0)
    y = pd.read_csv(DATA_DIR / "merged_dataY.csv", index_col=0).values.ravel()
    return X, y


def stratified_split(X, y, test_size=0.2, n_bins=5):
    """Train/test split that keeps the distribution of the target similar in both parts."""
    bins = KBinsDiscretizer(n_bins=n_bins, encode="ordinal", strategy="quantile").fit_transform(y.reshape(-1, 1)).ravel()
    return train_test_split(X, y, stratify=bins, test_size=test_size, random_state=SEED)


def models_and_grids():
    models = {
        "Linear Regression": LinearRegression(),
        "Lasso Regression": Lasso(random_state=SEED),
        "Random Forest": RandomForestRegressor(random_state=SEED),
        "SVR": SVR(),
    }
    grids = {
        "Linear Regression": {},
        "Lasso Regression": {"alpha": [0.01, 0.1, 1, 10]},
        "Random Forest": {"n_estimators": [50, 100, 200], "max_depth": [None, 10, 20]},
        "SVR": {"C": [0.1, 1, 10], "kernel": ["linear", "rbf"]},
    }
    return models, grids


def _tuned(model, grid, cv):
    if not grid:
        return model
    n_iter = min(10, int(np.prod([len(v) for v in grid.values()])))
    return RandomizedSearchCV(model, grid, scoring="r2", cv=cv, n_iter=n_iter, random_state=SEED, n_jobs=1)


@lru_cache(maxsize=2)
def run(cv_type="simple"):
    """Compare the models with simple or nested cross-validation, then test the best one."""
    X, y = load_datasets()
    X_train, X_test, y_train, y_test = stratified_split(X, y)
    models, grids = models_and_grids()
    inner_cv = KFold(n_splits=3, shuffle=True, random_state=SEED)
    outer_cv = KFold(n_splits=5, shuffle=True, random_state=SEED)

    rows = []
    for name, model in models.items():
        estimator = _tuned(model, grids[name], inner_cv) if cv_type == "nested" else model
        # one pass computes both metrics (half the training time of two separate passes)
        scores = cross_validate(estimator, X_train, y_train, cv=outer_cv, scoring=("r2", "neg_mean_absolute_error"), n_jobs=-1)  # folds in parallel
        rows.append({"model": name, "r2": float(np.mean(scores["test_r2"])),
                     "mae": float(-np.mean(scores["test_neg_mean_absolute_error"]))})

    best = max(rows, key=lambda r: r["r2"])["model"]
    final = _tuned(models[best], grids[best], inner_cv).fit(X_train, y_train)
    final = getattr(final, "best_estimator_", final)
    pred = final.predict(X_test)
    baseline_mae = float(np.mean(np.abs(y_test - np.mean(y_train))))

    return {
        "cv_type": cv_type,
        "n_rows": int(len(X)), "n_train": int(len(X_train)), "n_test": int(len(X_test)),
        "n_features": int(X.shape[1]),
        "results": rows,
        "best_model": best,
        "test": {
            "r2": float(r2_score(y_test, pred)),
            "mae": float(mean_absolute_error(y_test, pred)),
            "rmse": float(np.sqrt(mean_squared_error(y_test, pred))),
            "mape": float(mean_absolute_percentage_error(y_test, pred)),
            "baseline_mae": baseline_mae,
        },
        "target_mean": float(np.mean(y)), "target_std": float(np.std(y)),
    }
