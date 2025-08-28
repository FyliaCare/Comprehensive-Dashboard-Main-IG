import streamlit as st
import pydeck as pdk
import pandas as pd
import json
from app_modules import db
from app_modules.utils import df_from_records

st.set_page_config(page_title="NAMEs & Heat Zones", page_icon="🗺️", layout="wide")
db.init_db()

st.title("🗺️ NAMEs & Heat Zones")

# ---- Load Data ----
NAMEs = df_from_records(db.list_table("NAMEs"))
clients = df_from_records(db.list_table("clients"))
tasks = df_from_records(db.list_table("tasks"))

# Load Ghana NAME polygons
with open("data/ghana_NAMEs.geojson", "r") as f:
    ghana_geojson = json.load(f)

# ---- Prepare Activity Data ----
NAME_COORDS = {r["name"]: (r["latitude"], r["longitude"]) for _, r in NAMEs.iterrows()} if not NAMEs.empty else {}

activity_by_NAME = pd.DataFrame([
    {"NAME": name, "clients": 0, "open_tasks": 0, "completed_tasks": 0, "critical_tasks": 0}
    # Use the correct property key (update after checking)
    for name in [f["properties"]["name"] for f in ghana_geojson["features"]]
])

if not clients.empty:
    client_counts = clients.groupby("NAME_id")["id"].count().to_dict()
    for idx, row in NAMEs.iterrows():
        if row["id"] in client_counts:
            activity_by_NAME.loc[activity_by_NAME["NAME"] == row["name"], "clients"] = client_counts[row["id"]]

if not tasks.empty:
    for idx, row in tasks.iterrows():
        NAME_id = None
        if row.get("client_id") in clients["id"].values:
            NAME_id = clients.loc[clients["id"] == row["client_id"], "NAME_id"].values[0]
        if NAME_id in NAMEs["id"].values:
            NAME_name = NAMEs.loc[NAMEs["id"] == NAME_id, "name"].values[0]
            if row["status"] in ["Open", "In Progress", "Blocked"]:
                activity_by_NAME.loc[activity_by_NAME["NAME"] == NAME_name, "open_tasks"] += 1
            if row["status"] == "Completed":
                activity_by_NAME.loc[activity_by_NAME["NAME"] == NAME_name, "completed_tasks"] += 1
            if row.get("priority") == "Critical":
                activity_by_NAME.loc[activity_by_NAME["NAME"] == NAME_name, "critical_tasks"] += 1

# ---- Map Layers ----
ghana_layer = pdk.Layer(
    "GeoJsonLayer",
    ghana_geojson,
    opacity=0.2,
    stroked=True,
    filled=True,
    extruded=False,
    get_fill_color=[200, 200, 200, 50],
    get_line_color=[60, 60, 60],
)

# Icon data
pins = []
for _, row in activity_by_NAME.iterrows():
    coords = NAME_COORDS.get(row["NAME"])
    if coords:
        color = [0, 200, 0]  # green
        if row["critical_tasks"] > 0:
            color = [200, 0, 0]  # red
        elif row["open_tasks"] > 5:
            color = [255, 140, 0]  # orange
        elif row["open_tasks"] > 0:
            color = [255, 215, 0]  # yellow

        pins.append({
            "name": row["NAME"],
            "latitude": coords[0],
            "longitude": coords[1],
            "clients": row["clients"],
            "open_tasks": row["open_tasks"],
            "completed_tasks": row["completed_tasks"],
            "critical_tasks": row["critical_tasks"],
            "color": color,
            "size": max(6, row["clients"] * 3 + row["open_tasks"] * 2),
        })

icon_layer = pdk.Layer(
    "ScatterplotLayer",
    data=pins,
    get_position=["longitude", "latitude"],
    get_radius="size",
    get_color="color",
    pickable=True,
)

view_state = pdk.ViewState(latitude=7.9, longitude=-1.0, zoom=6)

deck = pdk.Deck(
    initial_view_state=view_state,
    layers=[ghana_layer, icon_layer],
    tooltip={
        "text": "{name}\nClients: {clients}\nOpen Tasks: {open_tasks}\nCompleted: {completed_tasks}\nCritical: {critical_tasks}"
    },
)

st.pydeck_chart(deck, use_container_width=True)

# ---- Summary beneath map ----
st.subheader("📊 NAMEal Activity Summary")

# Progress column
activity_by_NAME["completion_rate"] = (
    (activity_by_NAME["completed_tasks"] / (activity_by_NAME["open_tasks"] + activity_by_NAME["completed_tasks"]).replace(0, 1)) * 100
).round(1)

# Display as dataframe with progress bars
for _, row in activity_by_NAME.iterrows():
    st.markdown(
        f"### {row['NAME']}  "
        f"🧑 Clients: {row['clients']} | 🔴 Critical: {row['critical_tasks']} | 📋 Open: {row['open_tasks']} | ✅ Completed: {row['completed_tasks']}"
    )
    st.progress(int(row["completion_rate"]))

# ---- Extra Charts ----
st.divider()
st.subheader("📈 NAMEal Breakdown")

col1, col2 = st.columns(2)

with col1:
    st.bar_chart(activity_by_NAME.set_index("NAME")[["clients"]], use_container_width=True)
with col2:
    st.bar_chart(activity_by_NAME.set_index("NAME")[["open_tasks", "completed_tasks"]], use_container_width=True)
