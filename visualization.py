import streamlit as st
import pandas as pd
import matplotlib.pyplot as plt
import seaborn as sns
import pydeck as pdk
import altair as alt
import geopandas as gpd
from sklearn import preprocessing as pre

from constants import BREAKS, COLOR_RANGE


def color_scale(val):
    for i, b in enumerate(BREAKS):
        if val < b:
            return COLOR_RANGE[i]
    return COLOR_RANGE[i]


def make_map(geo_df: pd.DataFrame, df: pd.DataFrame, map_feature: str):
    temp = df.copy()
    temp.reset_index(inplace=True)
    counties = temp['County Name'].to_list()

    def convert_coordinates(row):
        for f in row['coordinates']['features']:
            new_coords = []
            if f['geometry']['type'] == 'MultiPolygon':
                f['geometry']['type'] = 'Polygon'
                combined = []
                for i in range(len(f['geometry']['coordinates'])):
                    combined.extend(list(f['geometry']['coordinates'][i]))
                f['geometry']['coordinates'] = combined
            coords = f['geometry']['coordinates']
            for coord in coords:
                for point in coord:
                    new_coords.append([point[0], point[1]])
            f['geometry']['coordinates'] = new_coords
        return row['coordinates']

    def make_geojson(geo_df: pd.DataFrame):
        geojson = {"type": "FeatureCollection", "features": []}
        for i, row in geo_df.iterrows():
            feature = row['coordinates']['features'][0]
            feature["properties"] = {map_feature: row[map_feature], "name": row['County Name']}
            del feature["id"]
            del feature["bbox"]
            feature["geometry"]["coordinates"] = [feature["geometry"]["coordinates"]]
            geojson["features"].append(feature)

        return geojson

    temp = temp[['County Name', map_feature]]
    geo_df = geo_df.merge(temp, on='County Name')
    geo_df['geom'] = geo_df.apply(lambda row: row['geom'].buffer(0), axis=1)
    geo_df['coordinates'] = geo_df.apply(lambda row: gpd.GeoSeries(row['geom']).__geo_interface__, axis=1)
    geo_df['coordinates'] = geo_df.apply(lambda row: convert_coordinates(row), axis=1)
    geojson = make_geojson(geo_df)
    json = pd.DataFrame(geojson)
    geo_df["coordinates"] = json["features"].apply(lambda row: row["geometry"]["coordinates"])
    geo_df["name"] = json["features"].apply(lambda row: row["properties"]["name"])
    geo_df[map_feature] = json["features"].apply(lambda row: row["properties"][map_feature])
    scaler = pre.MaxAbsScaler()
    norm_df = pd.DataFrame(geo_df[map_feature])
    normalized_vals = scaler.fit_transform(norm_df)
    colors = list(map(color_scale, normalized_vals))
    geo_df['fill_color'] = colors
    geo_df.drop(['geom', 'County Name'], axis=1, inplace=True)

    view_state = pdk.ViewState(
        **{"latitude": 36, "longitude": -95, "zoom": 3, "maxZoom": 16, "pitch": 0, "bearing": 0}
    )
    polygon_layer = pdk.Layer(
        "PolygonLayer",
        geo_df,
        get_polygon="coordinates",
        filled=True,
        stroked=False,
        opacity=0.5,
        get_fill_color='fill_color',
        auto_highlight=True,
        pickable=True,
    )
    # The brackets here are expected for pdk, so string formatting is less friendly
    tooltip = {"html": "<b>County:</b> {name} </br> <b>" + str(map_feature) + ":</b> {" + str(map_feature) + "}"}

    r = pdk.Deck(
        layers=[polygon_layer],
        initial_view_state=view_state,
        map_style=pdk.map_styles.LIGHT,
        tooltip=tooltip
    )
    st.pydeck_chart(r)


def make_correlation_plot(df: pd.DataFrame):
    st.subheader('Correlation Plot')
    fig, ax = plt.subplots(figsize=(10, 10))
    st.write(sns.heatmap(df.corr(), annot=True, linewidths=0.5))
    st.pyplot(fig)
