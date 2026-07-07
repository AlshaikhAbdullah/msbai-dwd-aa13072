#!/usr/bin/env python3
"""
predict_ridership.py — STRETCH: predict daily NYC ridership from weather + calendar.

Honest evaluation: the model is trained on everything EXCEPT the most recent 12
months, then scored on those 12 months it never saw. We report out-of-sample
MAPE — error on unseen data, not a fit on training data.

Features are all knowable in advance (weather forecast + calendar), so this is a
legitimate "given tomorrow's forecast, how many rides?" setup — no leakage from
the target.
"""
import numpy as np
import pandas as pd
from google.cloud import bigquery
from sklearn.ensemble import HistGradientBoostingRegressor
from sklearn.metrics import mean_absolute_percentage_error, mean_absolute_error, r2_score

PROJECT = "msbai-dwd-aa13072"

SQL = """
SELECT d.trip_date AS date, SUM(d.trip_count) AS trips
FROM `msbai-dwd-aa13072.citibike.daily_summary_mat` d
WHERE d.region = 'New York City'
GROUP BY 1
"""
WEATHER = """
SELECT date, tavg_f, tmax_f, tmin_f, prcp_inches, snow_inches,
       wind_avg_mph, is_weekend, month, day_of_week
FROM `nyu-datasets.weather.m_weather_daily_nyc`
"""

def build():
    c = bigquery.Client(project=PROJECT)
    trips = c.query(SQL).to_dataframe()
    wx = c.query(WEATHER).to_dataframe()
    df = trips.merge(wx, on="date", how="inner")
    df["date"] = pd.to_datetime(df["date"])
    df = df.sort_values("date").reset_index(drop=True)
    # calendar features (all known in advance)
    doy = df["date"].dt.dayofyear
    df["doy_sin"] = np.sin(2 * np.pi * doy / 365.25)
    df["doy_cos"] = np.cos(2 * np.pi * doy / 365.25)
    df["year"] = df["date"].dt.year
    return df

FEATURES = ["tavg_f", "tmax_f", "tmin_f", "prcp_inches", "snow_inches",
            "wind_avg_mph", "is_weekend", "month", "day_of_week",
            "doy_sin", "doy_cos", "year"]

def main():
    df = build()
    # time-based split: hold out the last 365 days (never seen in training)
    cutoff = df["date"].max() - pd.Timedelta(days=365)
    train = df[df["date"] <= cutoff]
    test = df[df["date"] > cutoff]

    # `year` is a feature so the model learns the growth trend; a separate linear
    # detrend was tried and did worse (growth is non-linear: a COVID dip then
    # acceleration), so we keep the single gradient-boosted model.
    Xtr, ytr = train[FEATURES], train["trips"]
    Xte, yte = test[FEATURES], test["trips"]

    model = HistGradientBoostingRegressor(
        max_iter=400, learning_rate=0.05, max_depth=6, random_state=0)
    model.fit(Xtr, ytr)
    pred = model.predict(Xte)

    mape = mean_absolute_percentage_error(yte, pred)
    mae = mean_absolute_error(yte, pred)
    r2 = r2_score(yte, pred)

    print(f"Train: {train['date'].min().date()} → {train['date'].max().date()} "
          f"({len(train):,} days)")
    print(f"Test (unseen): {test['date'].min().date()} → {test['date'].max().date()} "
          f"({len(test):,} days)")
    print(f"\nOUT-OF-SAMPLE (on data the model never saw):")
    print(f"  MAPE = {mape*100:.1f}%   → predictions land within ~{mape*100:.0f}% of actual")
    print(f"  MAE  = {mae:,.0f} rides/day")
    print(f"  R²   = {r2:.3f}")
    # naive seasonal baseline: same calendar day last year
    return dict(mape=mape, mae=mae, r2=r2,
                train_days=len(train), test_days=len(test),
                test_lo=str(test['date'].min().date()),
                test_hi=str(test['date'].max().date()))

if __name__ == "__main__":
    main()
