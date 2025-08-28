import streamlit as st
import plotly.graph_objects as go
from app_modules import db
from app_modules.utils import df_from_records

# ---------------------------
# Ghana Regions & Coordinates
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

st.set_page_config(page_title="Regions & Heat Zones", page_icon="🗺️", layout="wide")
db.init_db()

st.title("🗺️ Ghana Regions & Heat Zones")

# ---------------------------
# Create static Ghana map
# ---------------------------
def plot_ghana_map(regions_db):
    fig = go.Figure()

    # Add all region points
    for region, (lat, lon) in REGION_COORDS.items():
        # check if DB has custom weight/color
        row = regions_db[regions_db["name"] == region]
        if not row.empty:
            weight = row.iloc[0].get("weight", 1)
            color = row.iloc[0].get("color", "#1f77b4")
        else:
            weight = 1
            color = "#1f77b4"

        fig.add_trace(go.Scattergeo(
            lon=[lon],
            lat=[lat],
            text=f"{region}<br>Weight: {weight}",
            mode="markers+text",
            textposition="top center",
            marker=dict(
                size=10 + weight * 5,
                color=color,
                line=dict(width=1, color="black")
            ),
            name=region
        ))

    fig.update_geos(
        scope="africa",
        showcountries=True, countrycolor="black",
        showland=True, landcolor="rgb(243,243,243)",
        showocean=True, oceancolor="lightblue",
        projection_type="mercator",
        lataxis_range=[4, 11.5],   # Ghana latitude range
        lonaxis_range=[-3.5, 1.5]  # Ghana longitude range
    )
    fig.update_layout(
        margin={"r":0,"t":0,"l":0,"b":0},
        height=600,
        title="📍 Ghana Regions Map",
        showlegend=False
    )
    return fig

# ---------------------------
# Manage DB + Display Map
# ---------------------------
regions = df_from_records(db.list_table("regions"))

# Prepopulate DB with all regions if empty
if regions.empty:
    for region, (lat, lon) in REGION_COORDS.items():
        db.insert("regions", {
            "name": region,
            "country": "Ghana",
            "latitude": lat,
            "longitude": lon,
            "weight": 1.0,
            "color": "#1f77b4",
            "notes": None
        })
    regions = df_from_records(db.list_table("regions"))

st.plotly_chart(plot_ghana_map(regions), use_container_width=True)

# ---------------------------
# Edit Section
# ---------------------------
with st.expander("✏️ Edit Region Settings", expanded=False):
    ids = regions["id"].tolist()
    target_id = st.selectbox(
        "Select Region",
        options=ids,
        format_func=lambda i: regions.loc[regions["id"] == i, "name"].values[0] if i in ids else "-"
    )

    if target_id:
        row = regions[regions["id"] == target_id].iloc[0]
        with st.form("edit_region"):
            weight = st.number_input("Heat Weight", min_value=0.0, value=float(row.get("weight") or 1.0), step=0.1)
            color = st.color_picker("Color", value=row.get("color") or "#1f77b4")
            notes = st.text_area("Notes", value=row.get("notes") or "", height=80)

            c1, c2 = st.columns(2)
            with c1:
                if st.form_submit_button("💾 Save Changes"):
                    db.update("regions", int(target_id), {
                        "weight": float(weight),
                        "color": color,
                        "notes": notes or None,
                    })
                    st.success("Region updated.")
            with c2:
                if st.form_submit_button("🗑️ Delete Region"):
                    db.delete("regions", int(target_id))
                    st.warning("Region deleted.")
