# Fab Tool Monitoring Dashboard

A Streamlit dashboard that simulates real-time monitoring of semiconductor etch tools: tool status, availability, alarms, and MTTR analytics.

## Features

- Tool status table (Running / Idle / Alarm)
- Summary metrics: total tools, running tools, active alarms, average availability
- Availability bar chart by tool
- Recent alarms log with severity

## Tech Stack

- Python 3.14
- Streamlit
- Pandas

## How to Run

```bash
python3 -m venv venv
source venv/bin/activate
pip install streamlit pandas
streamlit run app.py
```

## Background
Built as a portfolio project drawing on 25+ years of experience in semiconductor equipment software and factory automation (SECS/GEM, EDA, recipe management, MTTR reduction) at Applied Materials.