import streamlit as st
import pandas as pd

st.set_page_config(page_title="Fab Tool Monitoring Dashboard", layout="wide")
st.title("Fab Tool Monitoring Dashboard")

# --- Sample data ---
tools = [
    {"Tool": "ETCH-01", "Status": "Running", "Availability (%)": 98.2, "Alarms": 0},
    {"Tool": "ETCH-02", "Status": "Running", "Availability (%)": 96.5, "Alarms": 1},
    {"Tool": "ETCH-03", "Status": "Alarm", "Availability (%)": 87.3, "Alarms": 3},
    {"Tool": "ETCH-04", "Status": "Idle", "Availability (%)": 99.1, "Alarms": 0},
]
tools_df = pd.DataFrame(tools)

alarms = [
    {"Time": "08:12", "Tool": "ETCH-03", "Severity": "Critical", "Message": "RF power out of range"},
    {"Time": "08:05", "Tool": "ETCH-03", "Severity": "Warning", "Message": "Chamber pressure high"},
    {"Time": "07:48", "Tool": "ETCH-02", "Severity": "Warning", "Message": "Gas flow unstable"},
    {"Time": "07:31", "Tool": "ETCH-03", "Severity": "Critical", "Message": "Temperature interlock"},
]
alarms_df = pd.DataFrame(alarms)

# --- Summary metrics (overall) ---
col1, col2, col3, col4 = st.columns(4)
col1.metric("Total Tools", len(tools_df))
col2.metric("Running", (tools_df["Status"] == "Running").sum())
col3.metric("Active Alarms", len(alarms_df))
col4.metric("Avg Availability", f"{tools_df['Availability (%)'].mean():.1f}%")

# --- Sidebar filters ---
st.sidebar.header("Filters")
severity = st.sidebar.selectbox("Severity", ["All", "Critical", "Warning"])
tool_filter = st.sidebar.selectbox("Tool", ["All Tools"] + tools_df["Tool"].tolist())

# --- Apply the tool filter to BOTH tables ---
if tool_filter == "All Tools":
    shown_tools = tools_df
else:
    shown_tools = tools_df[tools_df["Tool"] == tool_filter]

filtered = alarms_df.copy()
if severity != "All":
    filtered = filtered[filtered["Severity"] == severity]
if tool_filter != "All Tools":
    filtered = filtered[filtered["Tool"] == tool_filter]

# --- Tool status table (filtered) ---
st.subheader("Tool Status")
st.dataframe(shown_tools, width="stretch", hide_index=True)

# --- Recent alarms (filtered) ---
st.subheader("Recent Alarms")
st.write(f"Showing {len(filtered)} of {len(alarms_df)} alarms")
st.dataframe(filtered, width="stretch", hide_index=True)

# --- Availability chart (filtered) ---
st.subheader("Availability by Tool")
st.bar_chart(shown_tools.set_index("Tool")["Availability (%)"], width="stretch")
