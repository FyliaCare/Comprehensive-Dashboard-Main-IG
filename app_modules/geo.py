import pandas as pd
import pydeck as pdk

def heatmap_layer(df: pd.DataFrame, lat_col="latitude", lon_col="longitude", weight_col="weight", radius=60):
    if df.empty:
        return None
    df2 = df[[lat_col, lon_col, weight_col]].copy()
    layer = pdk.Layer(
        "HeatmapLayer",
        data=df2,
        get_position=[lon_col, lat_col],
        aggregation=pdk.types.String("MEAN"),
        get_weight=weight_col,
        radiusPixels=radius,
    )
    return layer

def scatter_layer(df: pd.DataFrame, lat_col="latitude", lon_col="longitude", radius=6):
    if df.empty:
        return None
    layer = pdk.Layer(
        "ScatterplotLayer",
        data=df,
        get_position=[lon_col, lat_col],
        get_radius=radius*120,
        pickable=True,
        auto_highlight=True,
    )
    return layer

def deck_view(df: pd.DataFrame, lat_col="latitude", lon_col="longitude"):
    if df.empty:
        return pdk.ViewState(latitude=0, longitude=0, zoom=1.5, pitch=0)
    return pdk.ViewState(latitude=float(df[lat_col].mean()), longitude=float(df[lon_col].mean()), zoom=2.2, pitch=30)
