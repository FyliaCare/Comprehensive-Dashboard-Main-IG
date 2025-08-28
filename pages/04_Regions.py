import math
import json
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import streamlit as st
from app_modules import db
from app_modules.utils import df_from_records

# ---------------------------
# Ghana Regions & Coordinates (from your data)
# ---------------------------
REGIONS_GH = [
    "Greater Accra","Ashanti","Western","Western North","Central",
    "Eastern","Volta","Oti","Northern","Savannah","North East",
    "Upper East","Upper West","Bono","Bono East","Ahafo"
]

REGION_COORDS = {
    'Greater Accra': (5.6037, -0.1870),
    'Ashanti': (6.6666, -1.6163),
    'Western': (4.9167, -1.7607),
    'Western North': (6.6667, -2.2600),
    'Central': (5.1214, -1.3442),
    'Eastern': (6.0455, -0.2474),
    'Volta': (6.5786, 0.4726),
    'Oti': (8.0500, 0.3667),
    'Northern': (9.4008, -0.8393),
    'Savannah': (8.3500, -1.0833),
    'North East': (9.6500, -0.2500),
    'Upper East': (10.6856, -0.2076),
    'Upper West': (10.2833, -2.2333),
    'Bono': (7.7333, -2.0833),
    'Bono East': (7.9000, -1.7333),
    'Ahafo': (7.3500, -2.3000)
}

# ---------------------------
# Streamlit init
# ---------------------------
st.set_page_config(page_title="Regions & Heat Zones", page_icon="🗺️", layout="wide")
db.init_db()

st.title("🗺️ Regions & Heat Zones")
st.caption("Heat shows **where activity is ongoing** (clients & tasks). Hover for quick info, use the selector for full details.")

# ---------------------------
# Helpers
# ---------------------------
def km_to_deg_offsets(lat_deg: float, half_side_km: float):
    """Return (dlat, dlon) degree offsets for a square half side length around given latitude."""
    dlat = half_side_km / 110.574  # ~km per degree latitude
    dlon = half_side_km / (111.320 * math.cos(math.radians(max(min(lat_deg, 89.9), -89.9))))
    return dlat, dlon

def square_polygon(lon: float, lat: float, half_side_km: float = 60.0):
    """Return a closed square polygon (list of [lon,lat]) centered at lon/lat."""
    dlat, dlon = km_to_deg_offsets(lat, half_side_km)
    return [
        [lon - dlon, lat - dlat],
        [lon + dlon, lat - dlat],
        [lon + dlon, lat + dlat],
        [lon - dlon, lat + dlat],
        [lon - dlon, lat - dlat],
    ]

def build_regions_geojson():
    """Build a simple FeatureCollection with square polygons for each Ghana region."""
    features = []
    for name, (lat, lon) in REGION_COORDS.items():
        poly = square_polygon(lon, lat, half_side_km=60)  # adjust size if you want
        feature = {
            "type": "Feature",
            "id": name,
            "properties": {"name": name},
            "geometry": {"type": "Polygon", "coordinates": [poly]},
        }
        features.append(feature)
    return {"type": "FeatureCollection", "features": features}

def ensure_regions_seeded():
    """Ensure your DB 'regions' table contains the 16 Ghana regions with coords."""
    existing = df_from_records(db.list_table("regions"))
    have = set(existing["name"].tolist()) if not existing.empty else set()
    for name, (lat, lon) in REGION_COORDS.items():
        if name not in have:
            db.insert("regions", {
                "name": name,
                "country": "Ghana",
                "latitude": float(lat),
                "longitude": float(lon),
                "weight": 1.0,
                "color": "#1f77b4",
                "notes": None
            })

# ---------------------------
# Data
# ---------------------------
# Make sure all 16 regions exist so analytics always render
ensure_regions_seeded()

clients = df_from_records(db.list_table("clients"))  # columns include: id, name, industry_id, region_id, ...
industries = df_from_records(db.list_table("industries"))  # id, name
regions_db = df_from_records(db.list_table("regions"))  # id, name, country, latitude, longitude, ...

# Optional tasks to weight heat by work volume
try:
    tasks = df_from_records(db.list_table("tasks"))
except Exception:
    tasks = pd.DataFrame()

# Safety: normalize dtypes
for df in [clients, industries, regions_db, tasks]:
    if not df.empty and "id" in df.columns:
        df["id"] = pd.to_numeric(df["id"], errors="coerce")

# Join clients -> industries names
if not clients.empty and not industries.empty and "industry_id" in clients.columns:
    industries_small = industries[["id", "name"]].rename(columns={"name": "industry_name"})
    clients = clients.merge(industries_small, left_on="industry_id", right_on="id", how="left", suffixes=("", "_ind"))
    if "id_ind" in clients.columns:
        clients = clients.drop(columns=["id_ind"])

# ---------------------------
# Activity calculation (HEAT)
# ---------------------------
# Base activity = number of clients in region
activity_by_region = pd.DataFrame({"id": regions_db["id"], "name": regions_db["name"]})
activity_by_region["clients_count"] = 0
activity_by_region["open_tasks"] = 0
activity_by_region["critical_tasks"] = 0

if not clients.empty:
    base = clients.groupby("region_id").size().reset_index(name="clients_count")
    activity_by_region = activity_by_region.merge(base, left_on="id", right_on="region_id", how="left")
    activity_by_region["clients_count"] = activity_by_region["clients_count_y"].fillna(0).astype(int)
    activity_by_region = activity_by_region.drop(columns=[c for c in activity_by_region.columns if c.endswith("_y") or c == "region_id"])

# Optional: task weighting (if you log tasks with client_id & status/priority)
if not tasks.empty and "client_id" in tasks.columns:
    # Map tasks -> region via client_id
    if not clients.empty:
        task_client = tasks.merge(clients[["id", "region_id"]], left_on="client_id", right_on="id", how="left", suffixes=("", "_cli"))
        # Open tasks (not Completed/Done)
        if "status" in task_client.columns:
            open_mask = ~task_client["status"].fillna("").str.lower().isin(["done", "completed"])
        else:
            open_mask = pd.Series([True] * len(task_client))
        open_by_region = task_client[open_mask].groupby("region_id").size().reset_index(name="open_tasks")
        activity_by_region = activity_by_region.merge(open_by_region, left_on="id", right_on="region_id", how="left")
        activity_by_region["open_tasks"] = activity_by_region["open_tasks"].fillna(0).astype(int)
        # Critical tasks
        if "priority" in task_client.columns:
            crit_mask = task_client["priority"].fillna("").str.lower().eq("critical")
            crit_by_region = task_client[crit_mask].groupby("region_id").size().reset_index(name="critical_tasks")
            activity_by_region = activity_by_region.merge(crit_by_region, left_on="id", right_on="region_id", how="left")
            activity_by_region["critical_tasks"] = activity_by_region["critical_tasks"].fillna(0).astype(int)

        # Clean temp columns
        for c in ["region_id"]:
            if c in activity_by_region.columns:
                dup_cols = [col for col in activity_by_region.columns if col == c]
                for dc in dup_cols:
                    try:
                        activity_by_region = activity_by_region.drop(columns=[dc])
                    except Exception:
                        pass

# Final HEAT metric (tune weights as you prefer)
activity_by_region["heat"] = (
    activity_by_region["clients_count"] * 1.0
    + activity_by_region["open_tasks"] * 0.5
    + activity_by_region["critical_tasks"] * 2.0
)

# ---------------------------
# Build GeoJSON (no external files)
# ---------------------------
ghana_geojson = build_regions_geojson()

# Data for map (by region name)
map_df = activity_by_region.merge(regions_db[["id", "name", "latitude", "longitude"]], on=["id", "name"], how="left")
map_df["heat"] = map_df["heat"].fillna(0)
map_df["clients_count"] = map_df["clients_count"].fillna(0).astype(int)
map_df["open_tasks"] = map_df["open_tasks"].fillna(0).astype(int)
map_df["critical_tasks"] = map_df["critical_tasks"].fillna(0).astype(int)

# Hover text: top clients & industries
def top_items_text(region_id: int, n: int = 5):
    if clients.empty:
        return "Clients: none"
    sub = clients[clients["region_id"] == region_id]
    if sub.empty:
        return "Clients: none"
    names = sub["name"].dropna().astype(str).tolist()
    if not names:
        return "Clients: none"
    names = names[:n]
    inds = sorted(set(sub["industry_name"].dropna().astype(str).tolist())) if "industry_name" in sub.columns else []
    ind_txt = ", ".join(inds[:5]) if inds else "—"
    return f"Clients: {', '.join(names)}<br>Industries: {ind_txt}"

map_df["hover_html"] = map_df.apply(
    lambda r: (
        f"<b>{r['name']}</b><br>"
        f"Heat: {r['heat']:.1f}<br>"
        f"Clients: {r['clients_count']} | Open Tasks: {r['open_tasks']} | Critical: {r['critical_tasks']}<br>"
        f"{top_items_text(int(r['id']))}"
    ),
    axis=1
)

# ---------------------------
# Choropleth (polygons) + labels (centroids)
# ---------------------------
fig = px.choropleth_mapbox(
    map_df,
    geojson=ghana_geojson,
    featureidkey="properties.name",
    locations="name",
    color="heat",
    color_continuous_scale="YlOrRd",
    range_color=(map_df["heat"].min(), max(1.0, map_df["heat"].max())),
    mapbox_style="carto-positron",
    center={"lat": 7.9, "lon": -1.0},
    zoom=6,
    opacity=0.65,
    hover_name="name",
    hover_data={"heat": True, "clients_count": True, "open_tasks": True, "critical_tasks": True, "name": False}
)

# Add region labels at centroids
fig.add_trace(go.Scattermapbox(
    lat=map_df["latitude"],
    lon=map_df["longitude"],
    mode="text",
    text=map_df["name"],
    textfont=dict(size=11),
    hoverinfo="skip",
))

fig.update_layout(
    margin=dict(l=0, r=0, t=0, b=0),
    height=650,
)

st.plotly_chart(fig, use_container_width=True)

# ---------------------------
# Region Details Panel
# ---------------------------
st.markdown("---")
st.subheader("📋 Region Details")

region_names = map_df["name"].tolist()
sel = st.selectbox("Choose a region", region_names, index=0 if region_names else None)
if sel:
    rid = int(map_df.loc[map_df["name"] == sel, "id"].iloc[0])
    st.markdown(f"### 🔍 {sel}")

    # Clients in region
    if not clients.empty:
        cl = clients[clients["region_id"] == rid].copy()
        if not cl.empty:
            if "industry_name" not in cl.columns and not industries.empty:
                inds_small = industries[["id", "name"]].rename(columns={"name": "industry_name"})
                cl = cl.merge(inds_small, left_on="industry_id", right_on="id", how="left", suffixes=("", "_ind"))
                if "id_ind" in cl.columns:
                    cl = cl.drop(columns=["id_ind"])
            show_cols = [c for c in ["name", "industry_name", "contact_person", "contact_email", "contact_phone"] if c in cl.columns]
            st.write("**Companies / Clients**")
            st.dataframe(cl[show_cols].rename(columns={
                "name": "Client",
                "industry_name": "Industry",
                "contact_person": "Contact",
                "contact_email": "Email",
                "contact_phone": "Phone"
            }), use_container_width=True, hide_index=True)
        else:
            st.info("No clients in this region yet.")
    else:
        st.info("No clients recorded yet.")

    # Task summary for region
    if not tasks.empty and "client_id" in tasks.columns and not clients.empty:
        t = tasks.merge(clients[["id", "region_id"]], left_on="client_id", right_on="id", how="left")
        t = t[t["region_id"] == rid]
        if not t.empty:
            st.write("**Task Snapshot**")
            total_t = len(t)
            completed = (t["status"].fillna("").str.lower().isin(["done", "completed"])).sum()
            open_t = total_t - completed
            crit = (t["priority"].fillna("").str.lower() == "critical").sum() if "priority" in t.columns else 0
            c1, c2, c3 = st.columns(3)
            c1.metric("Total Tasks", total_t)
            c2.metric("Open", open_t)
            c3.metric("Critical", crit)
        else:
            st.info("No tasks associated with clients in this region.")

# ---------------------------
# Legend / Notes
# ---------------------------
st.markdown("""
**Legend & Notes**
- **Color = Heat** = Clients (×1) + Open Tasks (×0.5) + Critical Tasks (×2). Tune weights in code if desired.
- Shapes are simplified **polygons around region centroids** so the map works without external GeoJSON files.
- For official administrative boundaries, drop a `ghana_regions.geojson` in `app_modules/data/` and replace `build_regions_geojson()` with a file load.
""")
