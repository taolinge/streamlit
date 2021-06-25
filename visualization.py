import streamlit as st
import pandas as pd
import pydeck as pdk
import altair as alt
from sklearn import preprocessing as pre

from constants import BREAKS, COLOR_RANGE
import utils


def color_scale(val: float) -> list:
    for i, b in enumerate(BREAKS):
        if val < b:
            return COLOR_RANGE[i]
    return COLOR_RANGE[i]


def make_map(geo_df: pd.DataFrame, df: pd.DataFrame, map_feature: str):
    if 'Census Tract' in geo_df.columns:
        geo_df.reset_index(inplace=True)
    if 'Census Tract' in df.columns:
        df.reset_index(inplace=True)

    geojson = utils.convert_geom(geo_df, df, [map_feature])
    geojson_df = pd.DataFrame(geojson)

    geo_df["coordinates"] = geojson_df["features"].apply(lambda row: row["geometry"]["coordinates"])
    geo_df["name"] = geojson_df["features"].apply(lambda row: row["properties"]["name"])
    geo_df[map_feature] = geojson_df["features"].apply(lambda row: row["properties"][map_feature])

    scaler = pre.MinMaxScaler()
    norm_df = pd.DataFrame(geo_df[map_feature])
    normalized_vals = scaler.fit_transform(norm_df)
    colors = list(map(color_scale, normalized_vals))
    geo_df['fill_color'] = colors
    geo_df.fillna(0, inplace=True)

    tooltip = {"html": ""}
    if 'Census Tract' in set(geo_df.columns):
        keep_cols = ['coordinates', 'name', 'fill_color', 'geom', map_feature]
        geo_df.drop(list(set(geo_df.columns) - set(keep_cols)), axis=1, inplace=True)
        tooltip = {"html": "<b>Tract:</b> {name} </br>" + "<b>" + str(map_feature) + ":</b> {" + str(map_feature) + "}"}
    elif 'County Name' in set(geo_df.columns):
        # geo_df.drop(['geom', 'County Name'], axis=1, inplace=True)
        tooltip = {
            "html": "<b>County:</b> {name} </br>" + "<b>" + str(map_feature) + ":</b> {" + str(map_feature) + "}"}
    view_state = pdk.ViewState(
        **{"latitude": 36, "longitude": -95, "zoom": 3, "maxZoom": 16, "pitch": 0, "bearing": 0}
    )
    geo_df = geo_df.astype({map_feature: 'float64'})

    polygon_layer = pdk.Layer(
        "PolygonLayer",
        geo_df,
        get_polygon="coordinates",
        filled=True,
        get_fill_color='fill_color',
        stroked=False,
        opacity=0.15,
        pickable=True,
        auto_highlight=True,
    )

    r = pdk.Deck(
        layers=[polygon_layer],
        initial_view_state=view_state,
        map_style=pdk.map_styles.LIGHT,
        tooltip=tooltip
    )
    st.pydeck_chart(r)


def make_correlation_plot(df: pd.DataFrame, feature_cols: list):
    df = df.astype('float64')
    st.subheader('Correlation Plot')
    st.write('''
    This plot shows how individual features in the database correlate to each other. Values range from -1 to 1. 
    A value of 1 means that for a positive increase in one feature, there will be an increase in the other by a fixed proportion.
    A value of -1 means that for a positive increase in one feature, there will be a decrease in the other by a fixed proportion. 
    A value of 0 means that the two features are unrelated. A higher value can be read as a stronger relationship 
    (either positive or negative) between the two features.
    ''')
    avail_cols = list(df.columns)
    avail_cols.sort()
    cols_to_compare = st.multiselect('Columns to consider', avail_cols, feature_cols)
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
    bar_df = pd.DataFrame(df[[feature, 'County Name']])
    bar = alt.Chart(bar_df).mark_bar() \
        .encode(x='County Name', y=feature + ':Q',
                tooltip=['County Name', feature]).interactive()
    st.altair_chart(bar, use_container_width=True)


def make_census_bar_chart(df: pd.DataFrame, feature: str):
    bar = alt.Chart(df).mark_bar() \
        .encode(x='tract_id', y=feature + ':Q',
                tooltip=['tract_id', feature]).interactive()
    st.altair_chart(bar, use_container_width=True)


def make_scatter_plot_counties(df: pd.DataFrame, feature_1: str, feature_2: str,
                               scaling_feature: str = 'Resident Population (Thousands of Persons)'):
    scatter_df = df[[feature_1, feature_2, 'County Name', scaling_feature]]
    scatter = alt.Chart(scatter_df).mark_point() \
        .encode(x=feature_1 + ':Q', y=feature_2 + ':Q',
                tooltip=['County Name', scaling_feature, feature_1, feature_2],
                size=scaling_feature).interactive()
    st.altair_chart(scatter, use_container_width=True)


def make_scatter_plot_census_tracts(df: pd.DataFrame, feature_1: str, feature_2: str,
                                    scaling_feature: str = 'tot_population_census_2010'):
    scatter_df = df.reset_index(drop=True)[[feature_1, feature_2, 'tract_id', scaling_feature]]
    scatter = alt.Chart(scatter_df).mark_point() \
        .encode(x=feature_1 + ':Q', y=feature_2 + ':Q',
                tooltip=['tract_id', scaling_feature, feature_1, feature_2],
                size=scaling_feature).interactive()
    st.altair_chart(scatter, use_container_width=True)
