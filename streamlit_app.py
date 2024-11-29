import streamlit as st
import requests
import plotly.graph_objects as go
from datetime import datetime, date, timedelta
from typing import Dict, Any
from collections import defaultdict

# Configure the page
st.set_page_config(
    page_title="Griffin's accountability dashboard", page_icon="📈", layout="wide"
)

# Add title
st.title("Griffin's accountability dashboard")

# Define parameter options and their descriptions
FIDELITY_OPTIONS = {
    "5minute": "5 Minutes",
    "10minute": "10 Minutes",
    "hour": "Hourly",
    "day": "Daily",
    "week": "Weekly",
}

SPAN_OPTIONS = {
    "day": "day",
    "week": "week",
    "month": "month",
    "3month": "3month",
    "year": "year",
}

# Update the time range options
TIME_RANGE_OPTIONS = {
    "1d": {"label": "1D", "span": "day", "fidelity": "5minute"},
    "1w": {"label": "1W", "span": "week", "fidelity": "hour"},
    "1m": {"label": "1M", "span": "month", "fidelity": "day"},
    "ytd": {"label": "YTD", "span": "year", "fidelity": "day"},
}
# Initialize session state for selected range if it doesn't exist
if "selected_range" not in st.session_state:
    st.session_state.selected_range = "1d"

# Move time range selection to sidebar and keep buttons horizontal
with st.sidebar:
    st.header("Time Range")
    cols = st.columns(len(TIME_RANGE_OPTIONS))
    for col, (key, options) in zip(cols, TIME_RANGE_OPTIONS.items()):
        if col.button(
            options["label"],
            key=f"btn_{key}",
            type="primary" if st.session_state.selected_range == key else "secondary",
            on_click=lambda k=key: setattr(st.session_state, "selected_range", k),
        ):
            st.rerun()

time_range = st.session_state.selected_range
fidelity = TIME_RANGE_OPTIONS[time_range]["fidelity"]
span = TIME_RANGE_OPTIONS[time_range]["span"]
bounds = "regular"


# Function to fetch data from the FastAPI backend
@st.cache_data(ttl=300)  # Cache the data for 5 minutes
def fetch_portfolio_data(params: Dict[str, Any]) -> Dict[str, Any]:
    try:
        with st.spinner("Fetching portfolio data..."):
            response = requests.get(
                "http://localhost:8000/portfolio/historical/percentage", params=params
            )
            response.raise_for_status()
            return response.json()
    except requests.RequestException as e:
        st.error(f"Error fetching data: {str(e)}")
        return None


# Update parameters
params = {"fidelity": fidelity, "bounds": bounds, "span": span}

# Fetch the data
data = fetch_portfolio_data(params)


def filter_date_range(dates, values, start_date=None, end_date=None):
    """Filter data based on date range or YTD, excluding weekends."""
    if not dates or not values:
        return [], []

    def is_weekday(d):
        """Return True if date is a weekday (Mon-Fri)"""
        return d.weekday() < 5  # Monday = 0, Sunday = 6

    if start_date and end_date:
        # Convert dates to timezone-naive datetime for comparison
        start_dt = datetime.combine(start_date, datetime.min.time())
        end_dt = datetime.combine(end_date, datetime.max.time())

        # Convert API dates to timezone-naive and filter weekdays
        filtered_data = [
            (d.replace(tzinfo=None), v)
            for d, v in zip(dates, values)
            if start_dt <= d.replace(tzinfo=None) <= end_dt and is_weekday(d)
        ]
    else:
        # Filter for YTD and weekdays
        current_year = date.today().year
        filtered_data = [
            (d, v)
            for d, v in zip(dates, values)
            if d.replace(tzinfo=None).year >= current_year and is_weekday(d)
        ]

    if not filtered_data:
        return [], []

    return [d for d, _ in filtered_data], [v for _, v in filtered_data]


def bucket_by_week(dates, values):
    """Group data by week and calculate the average for each week."""
    weekly_data = defaultdict(list)

    # Group values by week
    for date, value in zip(dates, values):
        # Get the start of the week (Monday)
        week_start = date - timedelta(days=date.weekday())
        weekly_data[week_start].append(value)

    # Calculate average for each week
    weekly_dates = sorted(weekly_data.keys())
    weekly_values = [sum(weekly_data[d]) / len(weekly_data[d]) for d in weekly_dates]

    return weekly_dates, weekly_values


# When displaying the graph, wrap it in an expander
with st.expander("Bucketed percentage change", expanded=True):
    if data:
        # Convert datetime strings to datetime objects
        dates = [datetime.fromisoformat(db["date"]) for db in data]
        values = [db["percentage"] for db in data]

        # Filter based on selected date range
        if time_range == "ytd":
            dates, filtered_values = filter_date_range(dates, values)
        else:
            dates, filtered_values = filter_date_range(
                dates, values, start_date=None, end_date=None
            )

        # Check if we have any data after filtering
        if not filtered_values:
            st.warning("No data available for the selected time range.")
        else:
            start_date = dates[0]
            end_date = dates[-1]
            # Bucket by week if span is longer than 3 months
            if span in ["year", "5year", "all"] or (
                time_range != "ytd" and (end_date - start_date).days > 90
            ):
                dates, filtered_values = bucket_by_week(dates, filtered_values)

            # Convert percentage values (multiply by 100 and round)
            filtered_values = [round(v * 100, 2) for v in filtered_values]

            # Create colors array based on values
            colors = ["#FF4B4B" if v < 0 else "#00C805" for v in filtered_values]

            # Create the plot
            fig = go.Figure()

            # Add the bar plot with filtered data and dynamic colors
            fig.add_trace(
                go.Bar(
                    x=dates,
                    y=filtered_values,
                    name="Portfolio Performance",
                    marker_color=colors,  # Use the dynamic colors array
                    hovertemplate="%{y:.2f}%<extra></extra>",
                )
            )

            # Update title to indicate weekly bucketing if applied
            title_date = (
                "2024 YTD"
                if time_range == "ytd"
                else f"{start_date.strftime('%Y-%m-%d')} to {end_date.strftime('%Y-%m-%d')}"
            )
            bucketing_text = " (Weekly Average)" if len(dates) != len(data) else ""

            # Determine date format based on fidelity
            if fidelity in ["5minute", "10minute", "hour"]:
                date_format = "%Y-%m-%d %H:%M"  # Include time for intraday data
            else:
                date_format = "%Y-%m-%d"  # Just date for daily/weekly data

            # Configure x-axis to remove gaps
            fig.update_layout(
                title=f"Portfolio Performance ({title_date}{bucketing_text} - {FIDELITY_OPTIONS[fidelity]} intervals)",
                xaxis=dict(
                    type="category",  # Use category type to remove gaps
                    tickformat="%Y-%m-%d",  # Format the date display
                    tickmode="array",
                    ticktext=[
                        d.strftime(date_format) for d in dates
                    ],  # Use appropriate date format
                    tickvals=list(range(len(dates))),  # Use indices as positions
                    tickangle=45,  # Angle the dates for better readability
                ),
                yaxis=dict(
                    tickformat=".2f",
                    ticksuffix="%",
                    zeroline=True,
                    zerolinecolor="rgba(255,255,255,0.2)",
                    zerolinewidth=1,
                ),
                template="plotly_dark",
                height=600,
                hovermode="x unified",
                bargap=0.1,
                showlegend=False,
                margin=dict(b=100),  # Add bottom margin for rotated labels
            )

            # Display the plot
            st.plotly_chart(fig, use_container_width=True)

            # Display metrics
            col1, col2, col3 = st.columns(3)
            with col1:
                st.metric(
                    "Current Change",
                    f"{filtered_values[-1]:.2f}%",
                    f"{(filtered_values[-1] - filtered_values[0]):.2f}%",
                )

            with col2:
                st.metric("Highest Change", f"{max(filtered_values):.2f}%")

            with col3:
                st.metric("Lowest Change", f"{min(filtered_values):.2f}%")
    else:
        st.error(
            "Unable to fetch portfolio data. Please make sure the API server is running."
        )


# Function to fetch YTD data
@st.cache_data(ttl=300)
def fetch_ytd_data() -> Dict[str, Any]:
    try:
        with st.spinner("Fetching YTD data..."):
            response = requests.get("http://localhost:8000/portfolio/ytd")
            response.raise_for_status()
            return response.json()
    except requests.RequestException as e:
        st.error(f"Error fetching YTD data: {str(e)}")
        return None

# Add YTD line plot in a new expander
with st.expander("YTD Performance", expanded=True):
    ytd_data = fetch_ytd_data()

    if ytd_data:
        # Convert data
        dates = [datetime.fromisoformat(d["date"]) for d in ytd_data]
        values = [d["percentage"] * 100 for d in ytd_data]  # Convert to percentages

        # Create the line plot
        fig = go.Figure()

        # Add the line trace
        fig.add_trace(
            go.Scatter(
                x=dates,
                y=values,
                mode="lines",
                name="YTD Performance",
                line=dict(color="#00C805" if values[-1] >= 0 else "#FF4B4B", width=2),
                hovertemplate="%{y:.2f}%<extra></extra>",
            )
        )

        # Add a horizontal line at y=0
        fig.add_hline(
            y=0, line_dash="dash", line_color="rgba(255,255,255,0.2)", line_width=1
        )

        # Configure layout
        fig.update_layout(
            title="Portfolio Performance (YTD)",
            xaxis=dict(
                title="Date",
                tickformat="%Y-%m-%d",
                tickangle=45,
            ),
            yaxis=dict(
                title="Percentage Change",
                tickformat=".2f",
                ticksuffix="%",
                zeroline=False,
            ),
            template="plotly_dark",
            height=600,
            hovermode="x unified",
            showlegend=False,
            margin=dict(b=100),
        )

        # Display the plot
        st.plotly_chart(fig, use_container_width=True)

        # Display YTD metrics
        col1, col2, col3 = st.columns(3)
        with col1:
            st.metric("YTD Change", f"{values[-1]:.2f}%")

        with col2:
            st.metric("YTD High", f"{max(values):.2f}%")

        with col3:
            st.metric("YTD Low", f"{min(values):.2f}%")
    else:
        st.error(
            "Unable to fetch YTD data. Please make sure the API server is running."
        )

# Add footer
st.markdown("---")
st.markdown("*Data provided by Robinhood API*")

