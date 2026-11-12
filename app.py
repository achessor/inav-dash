import datetime as dt
import io

import pandas as pd
import streamlit as st

from store import import_csv, original_csv, read_samples, session_names, uploaded_files

st.set_page_config(page_title="INAV Telemetry", layout="wide")
st.title("INAV Telemetry")

with st.sidebar:
    st.header("Import logs")
    files = st.file_uploader(
        "Raw and telemetry CSVs",
        type="csv",
        accept_multiple_files=True,
        help="Upload either file or both. Standard logger filenames pair by session timestamp.",
    )
    if st.button("Import selected files", disabled=not files, type="primary"):
        for file in files:
            try:
                if import_csv(file.name, file.getvalue()):
                    st.success(f"Imported {file.name}")
                else:
                    st.info(f"Already imported: {file.name}")
            except (ValueError, UnicodeError) as exc:
                st.error(f"{file.name}: {exc}")

sessions = session_names()
if not sessions:
    st.info("Upload your INAV CSVs to start comparing sessions.")
    st.stop()


def session_label(key):
    try:
        return dt.datetime.strptime(key, "%Y%m%d_%H%M%S").strftime("%b %d, %Y %H:%M:%S")
    except ValueError:
        return key


def reading_label(key):
    command, metric = key
    return f"{metric.replace('_', ' ')} ({command})"


view = st.radio("View", ["Charts", "All decoded readings", "Uploaded files"], horizontal=True)
if view == "Uploaded files":
    uploads = {entry[0]: entry[1:] for entry in uploaded_files()}
    digest = st.selectbox(
        "Uploaded CSV", list(uploads),
        format_func=lambda key: f"{uploads[key][1]} ({key[:8]})",
    )
    _, filename, _ = uploads[digest]
    content = original_csv(digest)
    table = pd.read_csv(io.BytesIO(content), dtype=str, keep_default_na=False, encoding="utf-8-sig")
    if "command" in table.columns:
        commands = st.multiselect("Commands", sorted(table["command"].unique()),
                                  help="Leave empty to show every command.")
        if commands:
            table = table[table["command"].isin(commands)]
    st.caption(f"{len(table):,} rows")
    st.dataframe(table, hide_index=True, use_container_width=True)
    st.download_button("Download original CSV", content, file_name=filename, mime="text/csv")
    st.stop()

selected = st.multiselect("Sessions to compare", sessions, default=sessions, format_func=session_label)
if not selected:
    st.info("Select at least one session.")
    st.stop()

data = pd.DataFrame(
    read_samples(selected),
    columns=["session", "utc", "command", "measurement", "value", "source"],
).drop_duplicates(["session", "utc", "command", "measurement"], keep="first")
if data.empty:
    st.info("The selected uploads contain no decoded readings.")
    st.stop()
data["utc"] = pd.to_datetime(data["utc"], utc=True)
data["elapsed_s"] = (data["utc"] - data.groupby("session")["utc"].transform("min")).dt.total_seconds()
data["session"] = data["session"].map(session_label)
if view == "All decoded readings":
    commands = st.multiselect("Commands", sorted(data["command"].unique()),
                              help="Leave empty to show every command.")
    if commands:
        data = data[data["command"].isin(commands)]
    measurements = st.multiselect("Measurements", sorted(data["measurement"].unique()),
                                  help="Leave empty to show every measurement.")
    if measurements:
        data = data[data["measurement"].isin(measurements)]
    columns = ["session", "utc", "elapsed_s", "command", "measurement", "value", "source"]
    table = data[columns]
    st.caption(f"{len(table):,} rows")
    st.dataframe(table, hide_index=True, use_container_width=True)
    st.download_button("Download displayed readings", table.to_csv(index=False),
                       file_name="inav_readings.csv", mime="text/csv")
    st.stop()

data["numeric"] = pd.to_numeric(data["value"], errors="coerce").replace(
    [float("inf"), float("-inf")], float("nan")
)
chart_data = data.dropna(subset=["numeric"])
if chart_data.empty:
    st.info("The selected sessions contain text readings only. View them under All decoded readings.")
    st.stop()

group_labels = {
    "analog": "Battery - legacy",
    "battery_state": "Battery",
    "raw_gps": "GPS",
    "comp_gps": "GPS home",
    "attitude": "Attitude",
    "altitude": "Altitude and vertical speed",
    "raw_imu": "Accelerometer, gyro, and compass",
    "rc": "RC inputs",
    "servo": "Servo outputs",
    "motor": "Motor outputs",
    "nav_status": "Navigation",
    "status": "Controller status",
    "status_ex": "Controller status and arming",
}
commands = sorted(chart_data["command"].unique(), key=lambda cmd: group_labels.get(cmd, cmd))
initial = next((cmd for cmd in ("battery_state", "analog") if cmd in commands), commands[0])
group = st.selectbox(
    "Data to chart", ["All numeric readings", *commands],
    index=commands.index(initial) + 1,
    format_func=lambda cmd: group_labels.get(cmd, cmd),
)
if group != "All numeric readings":
    chart_data = chart_data[chart_data["command"] == group]
options = sorted(set(zip(chart_data["command"], chart_data["measurement"])), key=reading_label)
picked = st.multiselect(
    "Limit to specific readings", options, format_func=reading_label,
    help="Leave empty to chart every numeric reading in this group.",
    key=f"chart_readings_{group}",
)
readings = picked or options

axis = st.radio("Time axis", ["Elapsed seconds", "Recorded time (UTC)"], horizontal=True)
x = "elapsed_s" if axis == "Elapsed seconds" else "utc"
for command, measurement in readings:
    st.subheader(reading_label((command, measurement)))
    group = chart_data.loc[(chart_data["command"] == command) & (chart_data["measurement"] == measurement)]
    numeric = group.dropna(subset=["numeric"])
    if not numeric.empty:
        st.line_chart(numeric, x=x, y="numeric", color="session", x_label=axis,
                      y_label=measurement.replace("_", " "), height=275)
        stats = numeric.groupby("session")["numeric"].agg(["count", "min", "max", "mean"])
        with st.expander("Session statistics"):
            st.dataframe(stats, use_container_width=True)
    with st.expander("Recorded values", expanded=numeric.empty):
        st.dataframe(group[["session", "utc", "value", "source"]], hide_index=True,
                     use_container_width=True)
