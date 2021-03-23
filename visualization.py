import streamlit as st
import pandas as pd
import matplotlib.pyplot as plt
import seaborn as sns
import pydeck as pdk
import altair as alt
from sklearn import preprocessing as pre

from constants import BREAKS, COLOR_RANGE
import utils


def color_scale(val):
    for i, b in enumerate(BREAKS):
        if val < b:
            return COLOR_RANGE[i]
    return COLOR_RANGE[i]


def make_map(geo_df: pd.DataFrame, df: pd.DataFrame, map_feature: str):
    temp = df.copy()
    temp.reset_index(inplace=True)
    # counties = temp['County Name'].to_list()
    geojson = utils.convert_geom(geo_df, temp, [map_feature])
    merged_df = pd.DataFrame(geojson)
    # st.write(geojson)
    geo_df["coordinates"] = merged_df["features"].apply(lambda row: row["geometry"]["coordinates"])
    geo_df["name"] = merged_df["features"].apply(lambda row: row["properties"]["name"])
    geo_df[map_feature] = merged_df["features"].apply(lambda row: row["properties"][map_feature])
    scaler = pre.MinMaxScaler()
    norm_df = pd.DataFrame(geo_df[map_feature])
    normalized_vals = scaler.fit_transform(norm_df)
    colors = list(map(color_scale, normalized_vals))
    geo_df['fill_color'] = colors
    geo_df.drop(['geom', 'County Name'], axis=1, inplace=True)

    view_state = pdk.ViewState(
        **{"latitude": 36, "longitude": -95, "zoom": 3, "maxZoom": 16, "pitch": 0, "bearing": 0}
    )
    geo_df = geo_df.astype({map_feature: 'float64'})

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
    tooltip = {"html": "<b>County:</b> {name} </br>" + "<b>" + str(map_feature) + ":</b> {" + str(map_feature) + "}"}

    r = pdk.Deck(
        layers=[polygon_layer],
        initial_view_state=view_state,
        map_style=pdk.map_styles.LIGHT,
        tooltip=tooltip
    )
    st.pydeck_chart(r)

def make_census_map(geo_df: pd.DataFrame, df: pd.DataFrame, map_feature: str):
    temp = df.copy()
    temp.reset_index(inplace=True)
    geojson = utils.convert_geom(geo_df, temp, [map_feature])
    # st.write(geojson)
    merged_df = pd.DataFrame(geojson)
    geo_df["coordinates"] = merged_df["features"].apply(lambda row: row["geometry"]["coordinates"])
    geo_df["name"] = merged_df["features"].apply(lambda row: row["properties"]["name"])
    geo_df[map_feature] = merged_df["features"].apply(lambda row: row["properties"][map_feature])
    scaler = pre.MinMaxScaler()
    norm_df = pd.DataFrame(geo_df[map_feature])
    normalized_vals = scaler.fit_transform(norm_df)
    colors = list(map(color_scale, normalized_vals))
    geo_df['fill_color'] = colors
    geo_df.drop(['geom', 'County Name'], axis=1, inplace=True)

    view_state = pdk.ViewState(
        **{"latitude": 36, "longitude": -95, "zoom": 3, "maxZoom": 16, "pitch": 0, "bearing": 0}
    )
    geo_df = geo_df.astype({map_feature: 'float64'})

    polygon_layer = pdk.Layer(
        "PolygonLayer",
        geo_df,
        get_polygon="wkt",
        filled=True,
        stroked=False,
        opacity=0.5,
        get_fill_color='fill_color',
        auto_highlight=True,
        pickable=True,
    )
    # The brackets here are expected for pdk, so string formatting is less friendly
    tooltip = {"html": "<b>County:</b> {name} </br>" + "<b>" + str(map_feature) + ":</b> {" + str(map_feature) + "}"}

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


def make_bar_chart(df: pd.DataFrame, feature: str):
    bar_df = pd.DataFrame(df.reset_index()[[feature, 'County Name']])
    bar = alt.Chart(bar_df).mark_bar() \
        .encode(x='County Name', y=feature + ':Q',
                tooltip=['County Name', feature])
    st.altair_chart(bar, use_container_width=True)

def make_census_bar_chart(df: pd.DataFrame, feature: str):
    bar = alt.Chart(df).mark_bar() \
        .encode(x='tract_id', y=feature + ':Q',
                tooltip=['tract_id', feature])
    st.altair_chart(bar, use_container_width=True)