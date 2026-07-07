"""
NYC Weather × Citibike Ridership Dashboard
Audience: journalists and city planners — no data-analyst jargon.
Data loads once; all filtering is in-memory pandas. Never re-queries BigQuery.
"""
import pandas as pd
import streamlit as st
import plotly.express as px
import plotly.graph_objects as go
from data import load_data

# ── Page config ──────────────────────────────────────────────────────────────
st.set_page_config(
    page_title="NYC Citibike × Weather",
    page_icon="🚲",
    layout="wide",
)



# ── Sidebar filters ───────────────────────────────────────────────────────────
def sidebar_filters(df: pd.DataFrame):
    st.sidebar.title("Filters")

    # Date range
    min_date = df["date"].min().date()
    max_date = df["date"].max().date()
    date_range = st.sidebar.date_input(
        "Date range",
        value=(min_date, max_date),
        min_value=min_date,
        max_value=max_date,
    )
    if isinstance(date_range, (list, tuple)) and len(date_range) == 2:
        start, end = pd.Timestamp(date_range[0]), pd.Timestamp(date_range[1])
    else:
        start, end = pd.Timestamp(min_date), pd.Timestamp(max_date)

    # Rider type
    rider = st.sidebar.radio("Rider type", ["All", "Member", "Casual"])

    # Weather band
    bands = ["All"] + list(df["weather_band"].cat.categories)
    weather_band = st.sidebar.selectbox("Weather band", bands)

    # Wet / dry
    precip = st.sidebar.radio("Precipitation", ["All", "Dry days only", "Rainy days only"])

    # Bike type (data note: available 2021+)
    has_bike_type = df["num_classic_trips"].notna().any()
    bike_type = "All"
    if has_bike_type:
        st.sidebar.markdown("---")
        st.sidebar.caption("🚲 Bike-type data available from 2021 onward only.")
        bike_type = st.sidebar.radio("Bike type (totals only)", ["All", "Classic", "E-bike"])

    return start, end, rider, weather_band, precip, bike_type


def apply_filters(df, start, end, rider, weather_band, precip, bike_type):
    mask = (df["date"] >= start) & (df["date"] <= end)

    if weather_band != "All":
        mask &= df["weather_band"] == weather_band

    if precip == "Dry days only":
        mask &= df["is_rainy"] == 0
    elif precip == "Rainy days only":
        mask &= df["is_rainy"] == 1

    fdf = df[mask].copy()

    # Rider-type selection reshapes the trips column used by V1/V2/V3
    if rider == "Member":
        fdf["_trips"] = fdf["num_member_trips"]
    elif rider == "Casual":
        fdf["_trips"] = fdf["num_casual_trips"]
    else:
        fdf["_trips"] = fdf["num_trips"]

    # Bike-type selection reshapes trips for standalone bike views
    if bike_type == "Classic" and fdf["num_classic_trips"].notna().any():
        fdf["_bike_trips"] = fdf["num_classic_trips"]
    elif bike_type == "E-bike" and fdf["num_electric_trips"].notna().any():
        fdf["_bike_trips"] = fdf["num_electric_trips"]
    else:
        fdf["_bike_trips"] = fdf["num_trips"]

    return fdf


# ── Views ─────────────────────────────────────────────────────────────────────

def v1_ridership_over_time(fdf: pd.DataFrame, rider: str):
    """V1 — Is a ridership dip weather-driven or operational?"""
    st.subheader("V1 — Is this dip weather, or is it us?")
    st.caption(
        "Primary line = daily rides (7-day average). Overlay = temperature or precipitation. "
        "If the dip aligns with bad weather, it's explainable. If it doesn't, it's worth a manager's attention."
    )

    weather_var = st.radio(
        "Overlay", ["Avg temperature (°F)", "Precipitation (inches)"],
        horizontal=True, key="v1_overlay",
    )

    # Recompute 7d rolling on filtered data
    fdf = fdf.copy()
    fdf["trips_7d"] = fdf["_trips"].rolling(7, min_periods=1).mean()

    overlay_col = "tavg_f" if "temperature" in weather_var else "prcp_inches"
    overlay_label = weather_var

    fig = go.Figure()
    fig.add_trace(go.Scatter(
        x=fdf["date"], y=fdf["trips_7d"],
        name=f"Rides (7-day avg) — {rider}",
        line=dict(color="#1f77b4", width=2),
        yaxis="y1",
    ))
    fig.add_trace(go.Scatter(
        x=fdf["date"], y=fdf[overlay_col],
        name=overlay_label,
        line=dict(color="#ff7f0e", width=1.5, dash="dot"),
        yaxis="y2",
        opacity=0.75,
    ))
    fig.update_layout(
        title="A dip that lines up with bad weather is explainable; one that doesn't is operational.",
        yaxis=dict(title="Daily rides (7-day avg)"),
        yaxis2=dict(title=overlay_label, overlaying="y", side="right", showgrid=False),
        legend=dict(orientation="h", y=1.14),
        hovermode="x unified",
        height=450,
        margin=dict(t=70, b=40),
    )
    st.plotly_chart(fig, use_container_width=True)


def v2_rides_vs_temperature(fdf: pd.DataFrame, rider: str):
    """V2 — Where is demand elastic to weather, and for whom?"""
    st.subheader("V2 — Demand rises with warmth — but casual riders respond more sharply")
    st.caption(
        "Each dot is one day. The curve shows the average. "
        "Casual riders' steeper slope is the commercial opportunity: "
        "a warm-weather promo targets the right segment."
    )

    # Always show member vs casual split regardless of rider filter
    # (spec: V2 splits by rider type only)
    plot_df = fdf[["date", "tavg_f", "num_member_trips", "num_casual_trips"]].copy()
    plot_df = plot_df.melt(
        id_vars=["date", "tavg_f"],
        value_vars=["num_member_trips", "num_casual_trips"],
        var_name="rider_type", value_name="trips",
    )
    plot_df["rider_type"] = plot_df["rider_type"].map({
        "num_member_trips": "Member", "num_casual_trips": "Casual"
    })

    fig = px.scatter(
        plot_df, x="tavg_f", y="trips",
        color="rider_type",
        color_discrete_map={"Member": "#1f77b4", "Casual": "#ff7f0e"},
        trendline="lowess",
        labels={"tavg_f": "Avg temperature (°F)", "trips": "Daily rides", "rider_type": "Rider type"},
        opacity=0.35,
        height=450,
    )
    fig.update_layout(
        title="Ridership rises with warmth — and casual riders respond more sharply than members.",
        margin=dict(t=70, b=40),
    )
    st.plotly_chart(fig, use_container_width=True)


def v3_member_vs_casual_weather_bands(fdf: pd.DataFrame):
    """V3 — How does casual ridership respond across weather conditions?"""
    st.subheader("V3 — Casual riders are disproportionately absent in bad weather")
    st.caption(
        "Average daily rides per weather band. "
        "The gap between casual and member bars widens in poor conditions — "
        "casual demand is more elastic, so weather-triggered promos can move the needle."
    )

    band_df = (
        fdf.groupby("weather_band", observed=True)[["num_member_trips", "num_casual_trips"]]
        .mean()
        .reset_index()
        .melt(id_vars="weather_band", var_name="rider_type", value_name="avg_trips")
    )
    band_df["rider_type"] = band_df["rider_type"].map({
        "num_member_trips": "Member", "num_casual_trips": "Casual"
    })

    fig = px.bar(
        band_df, x="weather_band", y="avg_trips",
        color="rider_type", barmode="group",
        color_discrete_map={"Member": "#1f77b4", "Casual": "#ff7f0e"},
        labels={"weather_band": "Weather band", "avg_trips": "Avg daily rides", "rider_type": "Rider type"},
        category_orders={"weather_band": ["Cold (<40 °F)", "Mild (40–60 °F)", "Warm (60–75 °F)", "Hot (>75 °F)"]},
        height=430,
    )
    fig.update_layout(
        title="The casual–member gap widens in bad weather: casual demand is the elastic segment.",
        margin=dict(t=70, b=40),
    )
    st.plotly_chart(fig, use_container_width=True)


def v4_seasonality(fdf: pd.DataFrame, rider: str):
    """V4 — Typical calendar pattern so unusual days stand out."""
    st.subheader("V4 — July is always busy; don't mistake the calendar for weather")
    st.caption(
        "Average rides by month (left) and by day of week (right). "
        "Use this to separate 'it's summer' from 'it was sunny' when explaining a spike."
    )

    col1, col2 = st.columns(2)

    month_df = (
        fdf.groupby("month")["_trips"].mean()
        .reset_index()
        .rename(columns={"_trips": "avg_trips"})
    )
    month_df["month_name"] = pd.to_datetime(month_df["month"], format="%m").dt.strftime("%b")

    with col1:
        fig1 = px.bar(
            month_df, x="month_name", y="avg_trips",
            labels={"month_name": "Month", "avg_trips": "Avg daily rides"},
            color_discrete_sequence=["#1f77b4"],
            height=360,
            title=f"Summer is always busy — a calendar effect, not weather ({rider})",
        )
        fig1.update_layout(margin=dict(t=60, b=40), title=dict(font=dict(size=13)))
        st.plotly_chart(fig1, use_container_width=True)

    dow_labels = {0: "Mon", 1: "Tue", 2: "Wed", 3: "Thu", 4: "Fri", 5: "Sat", 6: "Sun"}
    dow_df = (
        fdf.groupby("day_of_week")["_trips"].mean()
        .reset_index()
        .rename(columns={"_trips": "avg_trips"})
    )
    dow_df["dow_name"] = dow_df["day_of_week"].map(dow_labels)

    with col2:
        fig2 = px.bar(
            dow_df, x="dow_name", y="avg_trips",
            labels={"dow_name": "Day of week", "avg_trips": "Avg daily rides"},
            color_discrete_sequence=["#1f77b4"],
            category_orders={"dow_name": list(dow_labels.values())},
            height=360,
            title=f"Weekday vs weekend is a calendar effect, not weather ({rider})",
        )
        fig2.update_layout(margin=dict(t=60, b=40), title=dict(font=dict(size=13)))
        st.plotly_chart(fig2, use_container_width=True)


def v5_nyc_vs_jc(fdf: pd.DataFrame):
    """V5 — NYC vs Jersey City split over time."""
    st.subheader("V5 — Jersey City ridership tracks NYC but at a fraction of the volume")
    st.caption(
        "Daily rides for New York City vs Jersey City (7-day average). "
        "JC is a separate operational footprint — its weather sensitivity may differ."
    )

    fdf = fdf.copy()
    fdf["nyc_7d"] = fdf["num_nyc_trips"].rolling(7, min_periods=1).mean()
    fdf["jc_7d"]  = fdf["num_jc_trips"].rolling(7, min_periods=1).mean()

    fig = go.Figure()
    fig.add_trace(go.Scatter(
        x=fdf["date"], y=fdf["nyc_7d"],
        name="New York City", line=dict(color="#1f77b4", width=2),
    ))
    fig.add_trace(go.Scatter(
        x=fdf["date"], y=fdf["jc_7d"],
        name="Jersey City", line=dict(color="#2ca02c", width=2),
    ))
    fig.update_layout(
        title="Jersey City ridership tracks NYC's seasonal rhythm but at a fraction of the volume.",
        yaxis_title="Daily rides (7-day avg)",
        legend=dict(orientation="h", y=1.14),
        hovermode="x unified",
        height=430,
        margin=dict(t=70, b=40),
    )
    st.plotly_chart(fig, use_container_width=True)


# ── Main ──────────────────────────────────────────────────────────────────────
def main():
    st.title("🚲 NYC Citibike × Weather — Ridership Dashboard")
    st.markdown(
        "For journalists and city planners. "
        "Every chart answers a specific question — use the sidebar to focus on the period or conditions you care about."
    )

    df = load_data()
    start, end, rider, weather_band, precip, bike_type = sidebar_filters(df)
    fdf = apply_filters(df, start, end, rider, weather_band, precip, bike_type)

    if fdf.empty:
        st.warning("No data matches these filters. Try widening the date range or changing the weather band.")
        return

    # Summary metrics
    col1, col2, col3, col4 = st.columns(4)
    col1.metric("Days selected",      f"{len(fdf):,}")
    col2.metric("Total rides",        f"{int(fdf['_trips'].sum()):,}")
    col3.metric("Avg daily rides",    f"{int(fdf['_trips'].mean()):,}")
    col4.metric("Avg temperature",    f"{fdf['tavg_f'].mean():.1f} °F")

    st.divider()

    tab1, tab2, tab3, tab4, tab5 = st.tabs([
        "V1 — Ridership over time",
        "V2 — Rides vs temperature",
        "V3 — Member vs casual",
        "V4 — Seasonality",
        "V5 — NYC vs Jersey City",
    ])

    with tab1: v1_ridership_over_time(fdf, rider)
    with tab2: v2_rides_vs_temperature(fdf, rider)
    with tab3: v3_member_vs_casual_weather_bands(fdf)
    with tab4: v4_seasonality(fdf, rider)
    with tab5: v5_nyc_vs_jc(fdf)

    st.caption(
        f"Data: Citibike daily trips (2013–present) joined to NOAA NYC weather. "
        f"Loaded {len(df):,} days. Bike-type data available from 2021 onward."
    )


if __name__ == "__main__":
    main()
