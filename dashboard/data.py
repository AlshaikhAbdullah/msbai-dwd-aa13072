"""
data.py — BigQuery loader, importable by both app.py and check_correctness.py.
Keeps all BQ/pandas logic out of the Streamlit layer.
"""
import pandas as pd
import streamlit as st
from google.cloud import bigquery

PROJECT = "msbai-dwd-aa13072"

WEATHER_BINS   = [-999, 40, 60, 75, 999]
WEATHER_LABELS = ["Cold (<40 °F)", "Mild (40–60 °F)", "Warm (60–75 °F)", "Hot (>75 °F)"]


def _fetch(sql: str) -> pd.DataFrame:
    return bigquery.Client(project=PROJECT).query(sql).to_dataframe()


@st.cache_data(show_spinner="Loading ridership + weather data…")
def load_data() -> pd.DataFrame:
    """
    Joins Citibike daily trips to NYC weather on date.
    Tries the project's own daily_summary_mat first; falls back to
    nyu-datasets.citibike.m_daily_trips if absent or empty.
    Weather bands are computed here — all downstream filtering is pure pandas.
    """
    try:
        n = _fetch(
            "SELECT COUNT(*) AS n FROM `msbai-dwd-aa13072.citibike.daily_summary_mat`"
        ).iloc[0]["n"]
        use_own = int(n) > 0
    except Exception:
        use_own = False

    if use_own:
        trips_sql = """
            SELECT
                trip_date                          AS date,
                SUM(trip_count)                    AS num_trips,
                SUM(CASE WHEN rider_type='member' THEN trip_count ELSE 0 END)
                                                   AS num_member_trips,
                SUM(CASE WHEN rider_type='casual' THEN trip_count ELSE 0 END)
                                                   AS num_casual_trips,
                SUM(CASE WHEN rider_type NOT IN ('member','casual') THEN trip_count ELSE 0 END)
                                                   AS num_unknown_trips,
                SUM(CASE WHEN region='New York City' THEN trip_count ELSE 0 END)
                                                   AS num_nyc_trips,
                SUM(CASE WHEN region='New Jersey'    THEN trip_count ELSE 0 END)
                                                   AS num_jc_trips,
                SUM(CASE WHEN bike_type='classic'  THEN trip_count ELSE 0 END)
                                                   AS num_classic_trips,
                SUM(CASE WHEN bike_type='electric' THEN trip_count ELSE 0 END)
                                                   AS num_electric_trips,
                AVG(avg_duration_min)              AS avg_trip_duration_minutes
            FROM `msbai-dwd-aa13072.citibike.daily_summary_mat`
            GROUP BY trip_date
        """
    else:
        trips_sql = """
            SELECT
                date,
                num_trips,
                num_member_trips,
                num_casual_trips,
                0 AS num_unknown_trips,
                num_nyc_trips,
                num_jc_trips,
                num_classic_trips,
                num_electric_trips,
                avg_trip_duration_minutes
            FROM `nyu-datasets.citibike.m_daily_trips`
        """

    weather_sql = """
        SELECT
            date,
            tavg_f, tmax_f, tmin_f,
            prcp_inches,
            is_rainy, is_snowy, is_hot_day, is_freezing,
            season, is_weekend,
            month, day_of_week,
            wind_avg_mph, wind_gust_mph,
            snow_inches
        FROM `nyu-datasets.weather.m_weather_daily_nyc`
    """

    trips_df   = _fetch(trips_sql)
    weather_df = _fetch(weather_sql)

    df = trips_df.merge(weather_df, on="date", how="inner")
    df["date"] = pd.to_datetime(df["date"])
    df.sort_values("date", inplace=True)
    df.reset_index(drop=True, inplace=True)

    df["weather_band"] = pd.cut(
        df["tavg_f"],
        bins=WEATHER_BINS,
        labels=WEATHER_LABELS,
    )
    df["trips_7d"] = df["num_trips"].rolling(7, min_periods=1).mean()

    return df


def load_data_plain() -> pd.DataFrame:
    """Same as load_data() but without the @st.cache_data decorator — for scripts."""
    import functools
    # Temporarily unwrap the cached version
    return load_data.__wrapped__() if hasattr(load_data, "__wrapped__") else _load_data_impl()


def _load_data_impl() -> pd.DataFrame:
    """Uncached implementation — called by load_data_plain()."""
    try:
        n = _fetch(
            "SELECT COUNT(*) AS n FROM `msbai-dwd-aa13072.citibike.daily_summary_mat`"
        ).iloc[0]["n"]
        use_own = int(n) > 0
    except Exception:
        use_own = False

    if use_own:
        trips_sql = """
            SELECT
                trip_date AS date,
                SUM(trip_count) AS num_trips,
                SUM(CASE WHEN rider_type='member' THEN trip_count ELSE 0 END) AS num_member_trips,
                SUM(CASE WHEN rider_type='casual' THEN trip_count ELSE 0 END) AS num_casual_trips,
                SUM(CASE WHEN rider_type NOT IN ('member','casual') THEN trip_count ELSE 0 END) AS num_unknown_trips,
                SUM(CASE WHEN region='New York City' THEN trip_count ELSE 0 END) AS num_nyc_trips,
                SUM(CASE WHEN region='New Jersey' THEN trip_count ELSE 0 END) AS num_jc_trips,
                SUM(CASE WHEN bike_type='classic' THEN trip_count ELSE 0 END) AS num_classic_trips,
                SUM(CASE WHEN bike_type='electric' THEN trip_count ELSE 0 END) AS num_electric_trips,
                AVG(avg_duration_min) AS avg_trip_duration_minutes
            FROM `msbai-dwd-aa13072.citibike.daily_summary_mat`
            GROUP BY trip_date
        """
    else:
        trips_sql = """
            SELECT date, num_trips, num_member_trips, num_casual_trips,
                   0 AS num_unknown_trips,
                   num_nyc_trips, num_jc_trips, num_classic_trips, num_electric_trips,
                   avg_trip_duration_minutes
            FROM `nyu-datasets.citibike.m_daily_trips`
        """

    weather_sql = """
        SELECT date, tavg_f, tmax_f, tmin_f, prcp_inches,
               is_rainy, is_snowy, is_hot_day, is_freezing,
               season, is_weekend, month, day_of_week,
               wind_avg_mph, wind_gust_mph, snow_inches
        FROM `nyu-datasets.weather.m_weather_daily_nyc`
    """

    df = _fetch(trips_sql).merge(_fetch(weather_sql), on="date", how="inner")
    df["date"] = pd.to_datetime(df["date"])
    df.sort_values("date", inplace=True)
    df.reset_index(drop=True, inplace=True)
    df["weather_band"] = pd.cut(df["tavg_f"], bins=WEATHER_BINS, labels=WEATHER_LABELS)
    df["trips_7d"] = df["num_trips"].rolling(7, min_periods=1).mean()
    return df
