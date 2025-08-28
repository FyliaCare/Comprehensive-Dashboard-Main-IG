import streamlit as st
import plotly.express as px
import pandas as pd
import json
from app_modules import db
from app_modules.utils import df_from_records

st.set_page_config(page_title="Regions & Heat Zones", page_icon="🗺️", layout="wide")
db.init_db()

st.title("🗺️ Ghana Regions & Heat Zones")

# ---------------------------
# Load Data
# ---------------------------
clients = df_from_records(db.list_table("clients"))
tasks = df_from_records(db.list_table("tasks"))
regions_db = df_from_records(db.list_table("regions"))

# If no regions table yet → fallback to static Ghana regions
if regions_db.empty:
    regions_db = pd.DataFrame({
        "id": range(1, 17),
        "name": [
            "Greater Accra","Ashanti","Western","Western North","Central","Eastern",
            "Volta","Oti","Northern","Savannah","North East","Upper East",
            "Upper West","Bono","Bono East","Ahafo"
        ]
    })

# ---------------------------
# Activity calculation (HEAT)
# ---------------------------
activity_by_region = pd.DataFrame({"id": regions_db["id"], "name": regions_db["name"]})

# Default all to zero
activity_by_region["clients_count"] = 0
activity_by_region["open_tasks"] = 0
activity_by_region["critical_tasks"] = 0

# Add clients count
if not clients.empty and "region_id" in clients.columns:
    base = clients.groupby("region_id").size().reset_index(name="clients_count")
    activity_by_region = activity_by_region.merge(base, left_on="id", right_on="region_id", how="left")
    activity_by_region["clients_count"] = activity_by_region["clients_count_y"].fillna(0).astype(int)
    activity_by_region = activity_by_region.drop(columns=[c for c in activity_by_region.columns if c.endswith("_y") or c == "region_id"])

# Add tasks count
if not tasks.empty and "client_id" in tasks.columns and not clients.empty:
    task_client = tasks.merge(
        clients[["id", "region_id"]],
        left_on="client_id",
        right_on="id",
        how="left",
        suffixes=("", "_cli")
    )

    # Open tasks
    if "status" in task_client.columns:
        open_mask = ~task_client["status"].fillna("").str.lower().isin(["done", "completed"])
        open_by_region = task_client[open_mask].groupby("region_id").size().reset_index(name="open_tasks")
        activity_by_region = activity_by_region.merge(open_by_region, left_on="id", right_on="region_id", how="left")
        activity_by_region["open_tasks"] = activity_by_region["open_tasks_x"].fillna(0).astype(int)
        activity_by_region = activity_by_region.drop(columns=["region_id", "open_tasks_x"])

    # Critical tasks
    if "priority" in task_client.columns:
        crit_mask = task_client["priority"].fillna("").str.lower().eq("critical")
        crit_by_region = task_client[crit_mask].groupby("region_id").size().reset_index(name="critical_tasks")
        activity_by_region = activity_by_region.merge(crit_by_region, left_on="id", right_on="region_id", how="left")
        if "critical_tasks" in activity_by_region.columns:
            activity_by_region["critical_tasks"] = activity_by_region["critical_tasks"].fillna(0).astype(int)
        activity_by_region = activity_by_region.drop(columns=["region_id"])

# Guarantee required columns exist
for col in ["clients_count", "open_tasks", "critical_tasks"]:
    if col not in activity_by_region.columns:
        activity_by_region[col] = 0
    else:
        activity_by_region[col] = activity_by_region[col].fillna(0).astype(int)

# Final HEAT metric
activity_by_region["heat"] = (
    activity_by_region["clients_count"] * 1.0
    + activity_by_region["open_tasks"] * 0.5
    + activity_by_region["critical_tasks"] * 2.0
)

# ---------------------------
# Load Ghana GeoJSON
# ---------------------------
with open("app_modules/data/ghana_regions.geojson", "r") as f:
    ghana_geojson = json.load(f)

# ---------------------------
# Choropleth Map
# ---------------------------
fig = px.choropleth_mapbox(
    activity_by_region,
    geojson=ghana_geojson,
    featureidkey="properties.name",
    locations="name",
    color="heat",
    color_continuous_scale="YlOrRd",
    mapbox_style="carto-positron",
    center={"lat": 7.9, "lon": -1.0},
    zoom=6,
    opacity=0.65,
    hover_name="name",
    hover_data={
        "clients_count": True,
        "open_tasks": True,
        "critical_tasks": True,
        "heat": True
    }
)

fig.update_layout(
    margin={"r":0,"t":30,"l":0,"b":0},
    title="📊 Regional Heat Zones (Clients + Tasks)"
)

st.plotly_chart(fig, use_container_width=True)

# ---------------------------
# Sidebar Region Details
# ---------------------------
st.sidebar.header("📋 Region Details")
selected_region = st.sidebar.selectbox("Choose a Region", activity_by_region["name"].tolist())

if selected_region:
    st.sidebar.subheader(f"🔍 {selected_region}")
    region_id = activity_by_region.loc[activity_by_region["name"] == selected_region, "id"].iloc[0]

    # Clients
    if not clients.empty:
        clients_in_region = clients[clients["region_id"] == region_id]
        if not clients_in_region.empty:
            st.sidebar.write("### Clients")
            for _, row in clients_in_region.iterrows():
                st.sidebar.write(f"- **{row['name']}** ({row.get('contact_person','N/A')})")
        else:
            st.sidebar.info("No clients in this region yet.")

    # Tasks
    if not tasks.empty and "client_id" in tasks.columns:
        task_client = tasks.merge(
            clients[["id", "region_id"]],
            left_on="client_id",
            right_on="id",
            how="left",
            suffixes=("", "_cli")
        )
        tasks_in_region = task_client[task_client["region_id"] == region_id]
        if not tasks_in_region.empty:
            st.sidebar.write("### Tasks")
            for _, row in tasks_in_region.iterrows():
                st.sidebar.write(f"- {row['title']} ({row.get('status','Unknown')})")
        else:
            st.sidebar.info("No tasks logged for this region yet.")
