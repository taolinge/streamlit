import streamlit as st
import pandas as pd
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
    if 'Census Tract' in geo_df.columns:
        geo_df.reset_index(inplace=True)
    if 'Census Tract' in df.columns:
        df.reset_index(inplace=True)
    # counties = temp['County Name'].to_list()
    geojson = utils.convert_geom(geo_df, temp, [map_feature])
    merged_df = pd.DataFrame(geojson)
    geo_df["coordinates"] = merged_df["features"].apply(lambda row: row["geometry"]["coordinates"])
    geo_df["name"] = merged_df["features"].apply(lambda row: row["properties"]["name"])
    geo_df[map_feature] = merged_df["features"].apply(lambda row: row["properties"][map_feature])
    scaler = pre.MinMaxScaler()
    norm_df = pd.DataFrame(geo_df[map_feature])
    normalized_vals = scaler.fit_transform(norm_df)
    colors = list(map(color_scale, normalized_vals))
    geo_df['fill_color'] = colors
    if 'County Name' in geo_df.columns:
        geo_df.drop(['geom', 'County Name'], axis=1, inplace=True)
        tooltip = {
            "html": "<b>County:</b> {name} </br>" + "<b>" + str(map_feature) + ":</b> {" + str(map_feature) + "}"}
    elif 'Census Tract' in geo_df.columns:
        geo_df.drop(['geom', 'Census Tract'], axis=1, inplace=True)
        tooltip = {"html": "<b>Tract:</b> {name} </br>" + "<b>" + str(map_feature) + ":</b> {" + str(map_feature) + "}"}

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

    r = pdk.Deck(
        layers=[polygon_layer],
        initial_view_state=view_state,
        map_style=pdk.map_styles.LIGHT,
        tooltip=tooltip
    )
    st.pydeck_chart(r)


def make_correlation_plot(df: pd.DataFrame, default_cols=[]):
    df = df.astype('float64')
    st.subheader('Correlation Plot')
    st.write('''
    This plot shows how individual features in the database correlate to each other. Values range from -1 to 1. 
    A value of 1 means that for a positive increase in one feature, there will be an increase in the other by a fixed proportion.
    A value of -1 means that for a positive increase in one feature, there will be a decrease in the other by a fixed proportion. 
    A value of 0 means that the two features are unrelated. A higher value can be read as a stronger relationship 
    (either postive or negative) between the two features.
    ''')
    cols_to_compare = st.multiselect('Columns to consider', list(df.columns), default_cols)
    if len(cols_to_compare) > 2:
        df_corr = df[cols_to_compare].corr().stack().reset_index().rename(
            columns={0: 'correlation', 'level_0': 'variable', 'level_1': 'variable2'})
        df_corr['correlation_label'] = df_corr['correlation'].map('{:.2f}'.format)

        base = alt.Chart(df_corr).encode(
            x='variable2:O',
            y='variable:O'
        )

        # Text layer with correlation labels
        # Colors are for easier readability
        text = base.mark_text().encode(
            text='correlation_label',
            color=alt.condition(
                alt.datum.correlation > 0.5,
                alt.value('white'),
                alt.value('black')
            )
        )

        # The correlation heatmap itself
        cor_plot = base.mark_rect().encode(
            color='correlation:Q',
        ).properties(
            width=700,
            height=700
        )

        st.altair_chart(cor_plot + text)


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
