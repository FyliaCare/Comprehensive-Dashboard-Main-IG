import streamlit as st
import pydeck as pdk
import pandas as pd
import json
import plotly.express as px
from app_modules import db
from app_modules.utils import df_from_records

st.set_page_config(page_title="Regions & Heat Zones", page_icon="🗺️", layout="wide")
db.init_db()

st.title("🗺️ Regional Heat Zones & Activity Insights")

# ---- Load Data ----
regions = df_from_records(db.list_table("regions"))
clients = df_from_records(db.list_table("clients"))
tasks = df_from_records(db.list_table("tasks"))

with open("data/ghana_regions.geojson", "r") as f:
    ghana_geojson = json.load(f)

# ---- Prepare Activity Data ----
REGION_COORDS = {r["name"]: (r["latitude"], r["longitude"]) for _, r in regions.iterrows()} if not regions.empty else {}

activity_by_region = pd.DataFrame([
    {"region": name, "clients": 0, "open_tasks": 0, "completed_tasks": 0, "critical_tasks": 0}
    for name in [f["properties"]["name"] for f in ghana_geojson["features"]]
])

if not clients.empty:
    client_counts = clients.groupby("region_id")["id"].count().to_dict()
    for idx, row in regions.iterrows():
        if row["id"] in client_counts:
            activity_by_region.loc[activity_by_region["region"] == row["name"], "clients"] = client_counts[row["id"]]

if not tasks.empty:
    for _, row in tasks.iterrows():
        region_id = None
        if row.get("client_id") in clients["id"].values:
            region_id = clients.loc[clients["id"] == row["client_id"], "region_id"].values[0]
        if region_id in regions["id"].values:
            region_name = regions.loc[regions["id"] == region_id, "name"].values[0]
            if row["status"] in ["Open", "In Progress", "Blocked"]:
                activity_by_region.loc[activity_by_region["region"] == region_name, "open_tasks"] += 1
            if row["status"] == "Completed":
                activity_by_region.loc[activity_by_region["region"] == region_name, "completed_tasks"] += 1
            if row.get("priority") == "Critical":
                activity_by_region.loc[activity_by_region["region"] == region_name, "critical_tasks"] += 1

# ---- Map Layers ----
ghana_layer = pdk.Layer(
    "GeoJsonLayer",
    ghana_geojson,
    opacity=0.25,
    stroked=True,
    filled=True,
    extruded=False,
    get_fill_color=[180, 180, 180, 60],
    get_line_color=[50, 50, 50],
)

pins = []
for _, row in activity_by_region.iterrows():
    coords = REGION_COORDS.get(row["region"])
    if coords:
        color = [50, 200, 50]  # green
        if row["critical_tasks"] > 0:
            color = [220, 20, 60]  # red
        elif row["open_tasks"] > 5:
            color = [255, 165, 0]  # orange
        elif row["open_tasks"] > 0:
            color = [255, 215, 0]  # yellow

        pins.append({
            "name": row["region"],
            "latitude": coords[0],
            "longitude": coords[1],
            "clients": row["clients"],
            "open_tasks": row["open_tasks"],
            "completed_tasks": row["completed_tasks"],
            "critical_tasks": row["critical_tasks"],
            "color": color,
            "size": max(8, row["clients"] * 3 + row["open_tasks"] * 2),
        })

pin_layer = pdk.Layer(
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
    layers=[ghana_layer, pin_layer],
    tooltip={
        "html": "<b>{name}</b><br/>👥 Clients: {clients}<br/>📋 Open Tasks: {open_tasks}<br/>✅ Completed: {completed_tasks}<br/>🔴 Critical: {critical_tasks}"
    },
)

st.pydeck_chart(deck, use_container_width=True)

# ---- Professional Summary ----
st.markdown("## 📊 Regional Activity Summary")

activity_by_region["completion_rate"] = (
    (activity_by_region["completed_tasks"] / 
     (activity_by_region["open_tasks"] + activity_by_region["completed_tasks"]).replace(0, 1)) * 100
).round(1)

for _, row in activity_by_region.iterrows():
    c1, c2, c3, c4, c5 = st.columns([2,1,1,1,2])
    with c1:
        st.markdown(f"### {row['region']}")
    with c2:
        st.metric("Clients", row["clients"])
    with c3:
        st.metric("Open", row["open_tasks"])
    with c4:
        st.metric("Critical", row["critical_tasks"])
    with c5:
        st.metric("Completion %", f"{row['completion_rate']}%")

st.divider()

# ---- Better Charts ----
st.markdown("## 📈 Regional Breakdown")

col1, col2 = st.columns(2)

with col1:
    fig_clients = px.bar(
        activity_by_region.sort_values("clients", ascending=False),
        x="region", y="clients", text="clients",
        title="Clients per Region",
        color="clients", color_continuous_scale="Blues"
    )
    fig_clients.update_traces(textposition="outside")
    st.plotly_chart(fig_clients, use_container_width=True)

with col2:
    fig_tasks = px.bar(
        activity_by_region.melt(id_vars="region", value_vars=["open_tasks", "completed_tasks"]),
        x="region", y="value", color="variable",
        barmode="stack", title="Tasks per Region (Open vs Completed)",
        color_discrete_map={"open_tasks": "orange", "completed_tasks": "green"}
    )
    st.plotly_chart(fig_tasks, use_container_width=True)
