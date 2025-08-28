import streamlit as st
import pydeck as pdk
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

st.title("🗺️ Regions & Heat Zones")

# ------------------------------------------------
# Add Region (using predefined coordinates)
# ------------------------------------------------
with st.expander("➕ Add Region", expanded=False):
    with st.form("region_form"):
        region_name = st.selectbox("Select Region*", options=REGIONS_GH)
        weight = st.number_input("Heat Weight", min_value=0.0, value=1.0, step=0.1)
        color = st.color_picker("Optional Color", value="#2457F5")
        notes = st.text_area("Notes", height=80)

        submitted = st.form_submit_button("Save Region")
        if submitted:
            if not region_name:
                st.error("Region is required.")
            else:
                lat, lon = REGION_COORDS[region_name]
                payload = {
                    "name": region_name,
                    "country": "Ghana",
                    "latitude": lat,
                    "longitude": lon,
                    "weight": float(weight),
                    "color": color,
                    "notes": notes or None,
                }
                db.insert("regions", payload)
                st.success(f"Region '{region_name}' saved.")

st.divider()

# ------------------------------------------------
# Show Regions + Map
# ------------------------------------------------
regions = df_from_records(db.list_table("regions"))

if regions.empty:
    st.warning("⚠️ No regions yet. Add one above.")
else:
    st.metric("🌍 Total Regions", len(regions))

    st.dataframe(
        regions.drop(columns=["created_at", "updated_at"]),
        use_container_width=True, hide_index=True
    )

    # Build map layers
    scatter = pdk.Layer(
        "ScatterplotLayer",
        data=regions,
        get_position=["longitude", "latitude"],
        get_color="color",
        get_radius="weight*20000",
        pickable=True
    )
    heat = pdk.Layer(
        "HeatmapLayer",
        data=regions,
        get_position=["longitude", "latitude"],
        aggregation='"SUM"',
        get_weight="weight"
    )

    view_state = pdk.ViewState(
        latitude=7.9, longitude=-1.0, zoom=6, pitch=20
    )

    r = pdk.Deck(
        map_style="mapbox://styles/mapbox/light-v9",
        initial_view_state=view_state,
        layers=[heat, scatter],
        tooltip={"text": "{name} — {country}\nWeight: {weight}"}
    )
    st.pydeck_chart(r, use_container_width=True)

    # ------------------------------------------------
    # Edit / Delete Section
    # ------------------------------------------------
    with st.expander("✏️ Edit / Delete Region", expanded=False):
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
                color = st.color_picker("Color", value=row.get("color") or "#2457F5")
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
