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
    for _, row in regions.iterrows():
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

# Add completion %
activity_by_region["completion_rate"] = (
    (activity_by_region["completed_tasks"] /
     (activity_by_region["open_tasks"] + activity_by_region["completed_tasks"]).replace(0, 1)) * 100
).round(1)

# ---- Map with PIN ICONS ----
# ---- Map with PIN ICONS ----
ICON_URL = "https://img.icons8.com/color/48/marker.png"

# Attach coordinates
activity_by_region["latitude"] = activity_by_region["region"].map(
    lambda r: REGION_COORDS[r][0] if r in REGION_COORDS else None
)
activity_by_region["longitude"] = activity_by_region["region"].map(
    lambda r: REGION_COORDS[r][1] if r in REGION_COORDS else None
)

pins = activity_by_region.dropna(subset=["latitude", "longitude"]).to_dict("records")

icon_layer = pdk.Layer(
    "IconLayer",
    data=pins,
    get_icon="icon_data",
    get_size=4,
    size_scale=10,
    get_position=["longitude", "latitude"],
    pickable=True,
    icon_atlas=ICON_URL,
    get_icon_anchor="bottom",
)


# Drop missing coords
pins = activity_by_region.dropna(subset=["latitude", "longitude"]).to_dict("records")

icon_layer = pdk.Layer(
    "IconLayer",
    data=pins,
    get_icon="icon_data",
    get_size=4,
    size_scale=10,
    get_position=["longitude", "latitude"],
    pickable=True,
    icon_atlas=ICON_URL,
    get_icon_color=[0, 100, 200],
    get_icon_anchor="bottom",
)

ghana_layer = pdk.Layer(
    "GeoJsonLayer",
    ghana_geojson,
    opacity=0.2,
    stroked=True,
    filled=False,
    extruded=False,
    get_line_color=[80, 80, 80],
)

view_state = pdk.ViewState(latitude=7.9, longitude=-1.0, zoom=6)

deck = pdk.Deck(
    initial_view_state=view_state,
    layers=[ghana_layer, icon_layer],
    tooltip={
        "html": "<b>{region}</b><br/>👥 Clients: {clients}<br/>📋 Open: {open_tasks}<br/>✅ Completed: {completed_tasks}<br/>🔴 Critical: {critical_tasks}"
    },
)

st.pydeck_chart(deck, use_container_width=True)

# ---- Regional Activity Summary as Table ----
st.markdown("## 📊 Regional Activity Summary")

styled_df = activity_by_region[["region", "clients", "open_tasks", "critical_tasks", "completed_tasks", "completion_rate"]].copy()
styled_df = styled_df.rename(columns={
    "region": "Region",
    "clients": "Clients",
    "open_tasks": "Open Tasks",
    "critical_tasks": "Critical Tasks",
    "completed_tasks": "Completed",
    "completion_rate": "Completion %"
})

st.dataframe(styled_df, use_container_width=True, hide_index=True)

# ---- Charts ----
st.divider()
st.markdown("## 📈 Regional Breakdown")

col1, col2 = st.columns(2)

with col1:
    fig_clients = px.bar(
        styled_df.sort_values("Clients", ascending=False),
        x="Region", y="Clients", text="Clients",
        title="Clients per Region",
        color="Clients", color_continuous_scale="Blues"
    )
    fig_clients.update_traces(textposition="outside")
    st.plotly_chart(fig_clients, use_container_width=True)

with col2:
    fig_tasks = px.bar(
        styled_df.melt(id_vars="Region", value_vars=["Open Tasks", "Completed"]),
        x="Region", y="value", color="variable",
        barmode="stack", title="Tasks per Region (Open vs Completed)",
        color_discrete_map={"Open Tasks": "orange", "Completed": "green"}
    )
    st.plotly_chart(fig_tasks, use_container_width=True)
