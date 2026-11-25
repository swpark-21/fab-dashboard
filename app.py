import sqlite3
from pathlib import Path

import pandas as pd
import streamlit as st

st.set_page_config(page_title="Fab Tool Monitoring Dashboard", layout="wide")
st.title("Fab Tool Monitoring Dashboard")

DB_PATH = Path.home() / "fablink" / "data" / "fablink.db"

CHART_PARAMS = {
    "pressure_mtorr": "Chamber Pressure (mTorr)",
    "rf_power_w": "RF Power (W)",
}

VIEWS = ["Overview", "Etch-01", "Etch-02", "Etch-03", "Etch-04"]
TOOL_OPTIONS = ["All Tools", "ETCH-01", "ETCH-02", "ETCH-03", "ETCH-04"]

SAMPLE_TOOLS = [
    {"Tool": "ETCH-01", "Status": "Running", "Availability (%)": 98.2, "Alarms": 0},
    {"Tool": "ETCH-02", "Status": "Running", "Availability (%)": 96.5, "Alarms": 1},
    {"Tool": "ETCH-03", "Status": "Alarm", "Availability (%)": 87.3, "Alarms": 3},
    {"Tool": "ETCH-04", "Status": "Idle", "Availability (%)": 99.1, "Alarms": 0},
]
SAMPLE_ALARMS = [
    {"Time": "08:12", "Tool": "ETCH-03", "Severity": "Critical", "Message": "RF power out of range"},
    {"Time": "08:05", "Tool": "ETCH-03", "Severity": "Warning", "Message": "Chamber pressure high"},
    {"Time": "07:48", "Tool": "ETCH-02", "Severity": "Warning", "Message": "Gas flow unstable"},
    {"Time": "07:31", "Tool": "ETCH-03", "Severity": "Critical", "Message": "Temperature interlock"},
]


def load_live_etch01(db_path):
    """Derive ETCH-01's live state from the FabLink simulator DB.

    ETCH-01 is the FabLink virtual tool (chamber PM1). Returns a dict
    with status, active_alarms, availability, the currently active
    alarm rows and the 5 most recent alarm rows, or None when the
    simulator has not logged anything yet.
    """
    if not db_path.exists():
        return None
    conn = sqlite3.connect(f"file:{db_path}?mode=ro", uri=True)
    alarms_live = pd.read_sql_query(
        "SELECT ts, alid, name, state, alcd, text FROM alarms ORDER BY ts", conn)
    events_live = pd.read_sql_query(
        "SELECT MIN(ts) AS first_ts, MAX(ts) AS last_ts FROM wafer_events", conn)
    conn.close()

    has_alarms = len(alarms_live) > 0
    has_events = len(events_live) > 0 and pd.notna(events_live["first_ts"].iloc[0])
    if not has_alarms and not has_events:
        return None

    first_ts = None
    last_ts = None
    if has_alarms:
        alarms_live["ts"] = pd.to_datetime(alarms_live["ts"])
        first_ts = alarms_live["ts"].min()
        last_ts = alarms_live["ts"].max()
    if has_events:
        event_first = pd.to_datetime(events_live["first_ts"].iloc[0])
        event_last = pd.to_datetime(events_live["last_ts"].iloc[0])
        first_ts = event_first if first_ts is None else min(first_ts, event_first)
        last_ts = event_last if last_ts is None else max(last_ts, event_last)

    # Pair each SET with the next CLEAR for the same alarm.
    open_sets = {}
    alarm_seconds = 0.0
    active_rows = []
    if has_alarms:
        for _, row in alarms_live.iterrows():
            if row["state"] == "SET":
                open_sets.setdefault(row["alid"], []).append(row)
            elif row["state"] == "CLEAR" and open_sets.get(row["alid"]):
                start = open_sets[row["alid"]].pop(0)
                alarm_seconds += (row["ts"] - start["ts"]).total_seconds()
        active_rows = [row for rows in open_sets.values() for row in rows]
        for row in active_rows:
            alarm_seconds += (last_ts - row["ts"]).total_seconds()

    span = (last_ts - first_ts).total_seconds()
    availability = round((1 - alarm_seconds / span) * 100, 1) if span >= 60 else None

    now = pd.Timestamp.now()
    if len(active_rows) > 0:
        status = "Alarm"
    elif (now - last_ts).total_seconds() <= 120:
        status = "Running"
    else:
        status = "Idle"

    # The 5 most recent alarm records (SET and CLEAR) for the Overview table.
    recent_rows = []
    if has_alarms:
        for _, row in alarms_live.sort_values("ts", ascending=False).head(5).iterrows():
            category = int(row["alcd"]) & 0x7F
            severity = "Critical" if category in (1, 2, 8, 16) else "Warning"
            recent_rows.append({
                "Time": row["ts"].strftime("%H:%M"),
                "Tool": "ETCH-01",
                "Severity": severity,
                "Message": f"{row['name']} {row['state']}: {row['text']}",
            })

    return {
        "status": status,
        "active_alarms": len(active_rows),
        "availability": availability,
        "recent_rows": recent_rows,
    }


# --- Keep the sidebar Tool and the tab bar in sync ---
if "active_view" not in st.session_state:
    st.session_state.active_view = "Overview"


def _sync_tool_to_view():
    tool = st.session_state.sidebar_tool
    st.session_state.active_view = "Overview" if tool == "All Tools" else tool.replace("ETCH", "Etch")


def _sync_view_to_tool():
    view = st.session_state.active_view
    st.session_state.sidebar_tool = "All Tools" if view == "Overview" else view.replace("Etch", "ETCH")


# --- Sidebar, upper part: Fab - Overview ---
st.sidebar.header("Fab - Overview")
tool_filter = st.sidebar.selectbox("Tool", TOOL_OPTIONS, key="sidebar_tool", on_change=_sync_tool_to_view)
severity = st.sidebar.selectbox("Severity", ["All", "Critical", "Warning"])

# --- Sidebar, lower part: Live Chart (only while viewing Etch-01) ---
if tool_filter == "ETCH-01":
    st.sidebar.header("Live Chart")
    chart_param = st.sidebar.selectbox(
        "Parameter", list(CHART_PARAMS), format_func=lambda c: CHART_PARAMS[c])
else:
    chart_param = "pressure_mtorr"


@st.fragment(run_every=10)
def render_overview():
    """Overview tab. Re-reads the FabLink DB every 10 seconds so
    ETCH-01 stays live without clicking anything."""
    live = load_live_etch01(DB_PATH)
    etch01 = {
        "Tool": "ETCH-01",
        "Status": live["status"] if live else "Running",
        "Availability (%)": live["availability"] if live and live["availability"] is not None else 98.2,
        "Alarms": live["active_alarms"] if live else 0,
    }
    tools = [etch01] + [t for t in SAMPLE_TOOLS if t["Tool"] != "ETCH-01"]
    tools_df = pd.DataFrame(tools)

    alarms = list(SAMPLE_ALARMS)
    if live:
        alarms = alarms + live["recent_rows"]
    alarms_df = pd.DataFrame(alarms)

    filtered = alarms_df.copy()
    if severity != "All":
        filtered = filtered[filtered["Severity"] == severity]

    if live:
        st.caption("ETCH-01 is connected to the live FabLink simulator (chamber PM1). ETCH-02–04 are sample data. This tab refreshes every 10 seconds.")
    else:
        st.caption("FabLink simulator is not running — ETCH-01 shows sample data. Start equipment_sim.py and host.py to connect it live.")

    col1, col2, col3, col4 = st.columns(4)
    col1.metric("Total Tools", len(tools_df))
    col2.metric("Running", (tools_df["Status"] == "Running").sum())
    col3.metric("Active Alarms", int(tools_df["Alarms"].sum()))
    col4.metric("Avg Availability", f"{tools_df['Availability (%)'].mean():.1f}%")

    st.subheader("Tool Status")
    st.dataframe(tools_df, width="stretch", hide_index=True)

    st.subheader("Recent Alarms")
    st.write(f"Showing {len(filtered)} of {len(alarms_df)} alarms")
    st.dataframe(filtered, width="stretch", hide_index=True)

    st.subheader("Availability by Tool")
    st.bar_chart(tools_df.set_index("Tool")["Availability (%)"], width="stretch")


def render_tool_overview(tool, note="No live data linked yet — showing sample data."):
    """Sample-data overview for a tool without live data (Etch-02/03/04)."""
    row = next(t for t in SAMPLE_TOOLS if t["Tool"] == tool)
    st.subheader(f"{tool} Overview")
    if note:
        st.info(note)
    c1, c2, c3 = st.columns(3)
    c1.metric("Status", row["Status"])
    c2.metric("Availability", f"{row['Availability (%)']}%")
    c3.metric("Alarms", int(row["Alarms"]))
    st.subheader("Recent Alarms")
    tool_alarms = [a for a in SAMPLE_ALARMS if a["Tool"] == tool]
    if tool_alarms:
        st.dataframe(pd.DataFrame(tool_alarms), width="stretch", hide_index=True)
    else:
        st.write("No alarms for this tool.")


def render_etch01():
    """Etch-01 tab: live tool overview + live SECS/GEM data."""
    live = load_live_etch01(DB_PATH)
    st.subheader("Etch-01 Overview")
    if not live:
        st.warning("FabLink simulator is not running — start equipment_sim.py and host.py to see live data.")
        render_tool_overview("ETCH-01", note=None)
        return
    c1, c2, c3 = st.columns(3)
    c1.metric("Status", live["status"])
    c2.metric("Availability", f"{live['availability']}%" if live["availability"] is not None else "—")
    c3.metric("Active Alarms", live["active_alarms"])

    st.subheader("FabLink Live — SECS/GEM Messages")
    st.write("Shows the real messages logged by host.py into the SQLite database.")
    st.write(f"Database: `{DB_PATH}`")
    if st.button("Refresh data"):
        st.rerun()

    if not DB_PATH.exists():
        st.warning("Database not found yet. Start equipment_sim.py and host.py, wait a few seconds, then press Refresh data.")
        return
    conn = sqlite3.connect(f"file:{DB_PATH}?mode=ro", uri=True)
    alarms_live = pd.read_sql_query("SELECT * FROM alarms ORDER BY ts DESC", conn)
    events_live = pd.read_sql_query("SELECT * FROM wafer_events ORDER BY ts DESC", conn)
    conn.close()

    alarms_live["ts"] = pd.to_datetime(alarms_live["ts"])
    events_live["ts"] = pd.to_datetime(events_live["ts"])

    # --- Pair SET/CLEAR to compute MTTR and active alarms ---
    open_sets = {}
    mttr_records = []
    for _, row in alarms_live.sort_values("ts").iterrows():
        if row["state"] == "SET":
            open_sets.setdefault(row["alid"], []).append(row["ts"])
        elif row["state"] == "CLEAR" and open_sets.get(row["alid"]):
            start = open_sets[row["alid"]].pop(0)
            mttr_records.append({
                "Alarm": row["name"],
                "SET": start,
                "CLEAR": row["ts"],
                "MTTR (s)": round((row["ts"] - start).total_seconds(), 1),
            })
    active_count = sum(len(v) for v in open_sets.values())
    mttr_df = pd.DataFrame(mttr_records)

    wafers_done = (events_live["event"] == "WaferEnd").sum()
    avg_mttr = round(mttr_df["MTTR (s)"].mean(), 1) if len(mttr_df) > 0 else 0

    m1, m2, m3, m4 = st.columns(4)
    m1.metric("Alarm SETs", int((alarms_live["state"] == "SET").sum()))
    m2.metric("Active Alarms", int(active_count))
    m3.metric("Wafers Completed", int(wafers_done))
    m4.metric("Avg MTTR (s)", avg_mttr)

    st.subheader("Alarms from Equipment (S5F1)")
    if len(alarms_live) > 0:
        st.dataframe(alarms_live.head(20), width="stretch", hide_index=True)
    else:
        st.write("No alarms logged yet.")

    st.subheader("MTTR by Alarm (SET to CLEAR)")
    if len(mttr_df) > 0:
        summary = mttr_df.groupby("Alarm")["MTTR (s)"].agg(["count", "mean"]).round(1)
        summary.columns = ["Occurrences", "Avg MTTR (s)"]
        st.dataframe(summary, width="stretch")
    else:
        st.write("No completed alarm cycles yet (need a SET followed by a CLEAR).")

    st.subheader("Wafer Events (S6F11)")
    if len(events_live) > 0:
        st.dataframe(events_live.head(20), width="stretch", hide_index=True)
        st.subheader(f"{CHART_PARAMS[chart_param]} Trend")
        trend = events_live.sort_values("ts").set_index("ts")[chart_param]
        st.line_chart(trend, width="stretch")
    else:
        st.write("No wafer events logged yet.")


# --- Tab bar (button-style tabs; the sidebar Tool switches them) ---
view = st.radio("View", VIEWS, horizontal=True, key="active_view",
                label_visibility="collapsed", on_change=_sync_view_to_tool)

if view == "Overview":
    render_overview()
elif view == "Etch-01":
    render_etch01()
elif view == "Etch-02":
    render_tool_overview("ETCH-02")
elif view == "Etch-03":
    render_tool_overview("ETCH-03")
elif view == "Etch-04":
    render_tool_overview("ETCH-04")