import streamlit as st
import pandas as pd

st.title("Fab Tool Monitoring Dashboard")
st.write("Etch tool status, alarms, and availability — first screen")

# Simulated etch tool data
tools = pd.DataFrame({
    "Tool": ["ETCH-01", "ETCH-02", "ETCH-03", "ETCH-04"],
    "Status": ["Running", "Running", "Alarm", "Idle"],
    "Availability (%)": [98.2, 96.5, 87.3, 99.1],
    "Active Alarms": [0, 1, 3, 0],
})

# Summary metrics
total_alarms = int(tools["Active Alarms"].sum())
avg_availability = round(tools["Availability (%)"].mean(), 1)
running_tools = int((tools["Status"] == "Running").sum())

col1, col2, col3, col4 = st.columns(4)
col1.metric("Total Tools", len(tools))
col2.metric("Running", running_tools)
col3.metric("Active Alarms", total_alarms)
col4.metric("Avg Availability", f"{avg_availability}%")

st.subheader("Tool Status")
st.dataframe(tools, use_container_width=True)
st.subheader("Availability by Tool")
st.bar_chart(tools.set_index("Tool")["Availability (%)"])

# Recent alarms
alarms = pd.DataFrame({
    "Time": ["08:12", "08:05", "07:48", "07:31"],
    "Tool": ["ETCH-03", "ETCH-03", "ETCH-02", "ETCH-03"],
    "Severity": ["Critical", "Warning", "Warning", "Critical"],
    "Message": ["RF power out of range", "Chamber pressure high", "Gas flow unstable", "Temperature interlock"],
})

st.subheader("Recent Alarms")
st.dataframe(alarms, use_container_width=True)