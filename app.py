

import streamlit as st
import pandas as pd
import plotly.express as px

st.set_page_config(
    page_title="Cooper Library Dashboard",
    layout="wide"
)

st.title("Cooper Library Occupancy Dashboard")
st.caption("FY 2025 | July 1, 2024 – June 30, 2025")

# Load data
@st.cache_data
def load_data():
    occ = pd.read_csv("occuspace .csv")
    loc = pd.read_excel("location list.xlsx")

    occ["date"] = pd.to_datetime(
        occ["normalizedDate"]
    )

    occ = occ[
        occ["date"].between(
            "2024-07-01", "2025-06-30"
        )
    ].copy()

    df = occ.merge(
        loc[["id", "name", "capacity"]],
        left_on="location",
        right_on="id",
        validate="many_to_one"
    )

    df["avg_pct"] = (
        df["avgPercentageOccupied"] * 100
    )
    df["peak_pct"] = (
        df["peakPercentageOccupied"] * 100
    )

    return df

df = load_data()

# Sidebar filters
st.sidebar.header("Filters")

zones = sorted(df["name"].unique())

selected_zones = st.sidebar.multiselect(
    "Select zones",
    zones,
    default=[
        "4th Floor East",
        "4th Floor West"
    ]
)

date_range = st.sidebar.date_input(
    "Date range",
    value=(
        df["date"].min().date(),
        df["date"].max().date()
    ),
    min_value=df["date"].min().date(),
    max_value=df["date"].max().date()
)

if not selected_zones:
    st.warning("Select at least one zone.")
    st.stop()

if len(date_range) != 2:
    st.info("Select both start and end dates.")
    st.stop()

start, end = date_range

filtered = df[
    df["name"].isin(selected_zones)
    & df["date"].dt.date.between(start, end)
].copy()

if filtered.empty:
    st.warning("No observations for these filters.")
    st.stop()

# KPI metrics
mean_rate = filtered["avg_pct"].mean()
peak_days = (filtered["peak_pct"] > 100).sum()
observations = len(filtered)

c1, c2, c3 = st.columns(3)

c1.metric(
    "Mean daily average rate",
    f"{mean_rate:.2f}%"
)
c2.metric(
    "Above-reference zone-days",
    f"{peak_days}"
)
c3.metric(
    "Zone-day observations",
    f"{observations}"
)

st.caption(
    "KPIs are pooled across selected zone-day records. "
    "They are not building-wide occupancy measures."
)

# Chart 1: Zone comparison
st.subheader("Zone Occupancy Comparison")

summary = (
    filtered.groupby("name", as_index=False)
    .agg(mean_avg_pct=("avg_pct", "mean"))
)

fig1 = px.bar(
    summary.sort_values("mean_avg_pct"),
    x="mean_avg_pct",
    y="name",
    orientation="h",
    color="name",
    labels={
        "mean_avg_pct":
        "Mean daily average occupancy / capacity (%)",
        "name": "Monitored zone"
    },
    color_discrete_map={
    "4th Floor East": "#522D80",
    "4th Floor West": "#F56600"
}
)

fig1.update_layout(showlegend=False)

st.plotly_chart(fig1, use_container_width=True)

# Chart 2: Weekly occupancy trends
st.subheader("Weekly Occupancy Trends")

weekly = (
    filtered.set_index("date")
    .groupby("name")["avg_pct"]
    .resample("W")
    .mean()
    .reset_index()
)

fig2 = px.line(
    weekly,
    x="date",
    y="avg_pct",
    color="name",
    labels={
        "date": "Date",
        "avg_pct":
        "Mean daily average occupancy / capacity (%)",
        "name": "Zone"
    }
)

st.plotly_chart(fig2, use_container_width=True)

# Chart 3: Weekday-month heatmap
st.subheader("Occupancy Heatmap")

heat_zone = st.selectbox(
    "Choose zone for heatmap",
    selected_zones
)

heat = filtered[
    filtered["name"] == heat_zone
].copy()

heat["weekday"] = heat["date"].dt.day_name()
heat["month"] = heat["date"].dt.strftime("%b")

weekday_order = [
    "Monday", "Tuesday", "Wednesday",
    "Thursday", "Friday", "Saturday", "Sunday"
]

month_order = [
    "Jul", "Aug", "Sep", "Oct", "Nov", "Dec",
    "Jan", "Feb", "Mar", "Apr", "May", "Jun"
]

matrix = heat.pivot_table(
    index="weekday",
    columns="month",
    values="avg_pct",
    aggfunc="mean"
).reindex(
    index=weekday_order,
    columns=month_order
)

fig3 = px.imshow(
    matrix,
    labels={
        "x": "Month",
        "y": "Day of week",
        "color": "Occupancy (%)"
    },
    color_continuous_scale="YlOrRd",
    zmin=0,
    zmax=100,
    aspect="auto"
)

st.plotly_chart(fig3, use_container_width=True)

st.info(
    "Occupancy estimates people present. "
    "Reference capacity is not a verified seat count. "
    "Daily data cannot identify hourly peaks or "
    "real-time study-space availability."
)

# Download filtered data
st.download_button(
    "Download filtered data",
    filtered.to_csv(index=False),
    file_name="cooper_filtered_data.csv",
    mime="text/csv"
)
