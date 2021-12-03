from os import name
import streamlit as st
import pandas as pd
import geopandas as gpd
import pydeck as pdk
import altair as alt
from sklearn import preprocessing as pre
from constants import BREAKS, COLOR_RANGE
import utils
# from fpdf import FPDF
from ipywidgets import HTML

import queries

def color_scale(val: float) -> list:
    for i, b in enumerate(BREAKS):
        if val <= b:
            return COLOR_RANGE[i]
    return COLOR_RANGE[i]


def make_map(geo_df: pd.DataFrame, df: pd.DataFrame, map_feature: str, data_format: str = 'Raw Values'):
    if 'Census Tract' in geo_df.columns:
        geo_df.reset_index(inplace=True)
    if 'Census Tract' in df.columns:
        df.reset_index(inplace=True)
    geo_df_copy = geo_df.copy()

    label = map_feature
    if data_format == 'Per Capita':
        print('Per Cap')
        label = f"{map_feature} per capita"
        df[label] = df[map_feature] / df['Total Population']
        pass
    elif data_format == 'Per Square Mile':
        print('SQMI')
        label = f"{map_feature} per sqmi"
        df[label] = df[map_feature] / df['sqmi']

    geojson = utils.convert_geom(geo_df_copy, df, [label])
    geojson_df = pd.DataFrame(geojson)

    geo_df_copy["coordinates"] = geojson_df["features"].apply(lambda row: row["geometry"]["coordinates"])
    geo_df_copy["name"] = geojson_df["features"].apply(lambda row: row["properties"]["name"])
    geo_df_copy[label] = geojson_df["features"].apply(lambda row: row["properties"][label])
    scaler = pre.MinMaxScaler()
    feat_series = geo_df_copy[label]
    feat_type = None
    if feat_series.dtype == 'object':
        try:
            feat_type = 'category'
            feat_dict = {k: (i % 10) / 10 for i, k in enumerate(
                feat_series.unique())}  # max 10 categories, following from constants.BREAK, enumerated rather than encoded
            normalized_vals = feat_series.apply(lambda x: feat_dict[x])  # getting normalized vals, manually.
        except TypeError:
            feat_type = 'numerical'
            normalized_vals = scaler.fit_transform(
                pd.DataFrame(feat_series)
            )
    else:
        feat_type = 'numerical'
        normalized_vals = scaler.fit_transform(
            pd.DataFrame(feat_series)
        )
    # norm_df = pd.DataFrame(feat_series)
    colors = list(map(color_scale, normalized_vals))
    geo_df_copy['fill_color'] = colors
    geo_df_copy.fillna(0, inplace=True)

    tooltip = {"html": ""}
    if 'Census Tract' in set(geo_df_copy.columns):
        keep_cols = ['coordinates', 'name', 'fill_color', 'geom', map_feature]
        geo_df_copy.drop(list(set(geo_df_copy.columns) - set(keep_cols)), axis=1, inplace=True)
        tooltip = {"html": "<b>Tract:</b> {name} </br>" + "<b>" + str(label) + ":</b> {" + str(label) + "}"}
    elif 'County Name' in set(geo_df_copy.columns):
        geo_df_copy.drop(['geom', 'County Name'], axis=1, inplace=True)
        tooltip = {
            "html": "<b>County:</b> {name} </br>" + "<b>" + str(label) + ":</b> {" + str(label) + "}"}
    if len(geo_df_copy['coordinates'][0][0][0]) > 0:
        view_state = pdk.ViewState(
            **{"latitude": geo_df_copy['coordinates'][0][0][0][1], "longitude": geo_df_copy['coordinates'][0][0][0][0],
               "zoom": 5, "maxZoom": 16, "pitch": 0, "bearing": 0})
    else:
        view_state = pdk.ViewState(
            **{"latitude": 36, "longitude": -95, "zoom": 3, "maxZoom": 16, "pitch": 0, "bearing": 0})

    geo_df_copy = geo_df_copy.astype({label: 'float64'})

    polygon_layer = pdk.Layer(
        "PolygonLayer",
        geo_df_copy,
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
    for feature in feature_cols:
        feat_type = 'category' if df[feature].dtype == 'object' else 'numerical'
        if feat_type == 'category':
            return
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


def make_chart(df: pd.DataFrame, feature: str, data_format: str = 'Raw Values'):
    data_df = pd.DataFrame(df[[feature, 'County Name']])
    # feat_type = 'category' if data_df[feature].dtype == 'object' else 'numerical'
    # if feat_type == 'category':
    #     print("Categorical Data called on make_chart")
    # else:
    label = feature
    if data_format == 'Per Capita':
        print('Per Cap')
        label = f"{feature} per capita"
        data_df[label] = data_df[feature] / df['Total Population']
    elif data_format == 'Per Square Mile':
        print('SQMI')
        label = f"{feature} per sqmi"
        data_df[label] = data_df[feature] / df['sqmi']
    data_df = data_df.round(3)

    bar = alt.Chart(data_df) \
        .mark_bar() \
        .encode(x='County Name',
                y=label + ':Q',
                tooltip=['County Name', label]) \
        .interactive()
    st.altair_chart(bar, use_container_width=True)


def make_census_chart(df: pd.DataFrame, feature: str):
    feat_type = 'category' if df[feature].dtype == 'object' else 'numerical'
    data_df = pd.DataFrame(df[[feature, 'Census Tract', 'county_name']])
    if feat_type == 'category':
        data_df = pd.DataFrame(data_df.groupby(['county_name', feature]).size())
        data_df = data_df.rename(columns={0: "tract count"})
        data_df = data_df.reset_index()
        bar = alt.Chart(data_df) \
            .mark_bar() \
            .encode(x='county_name',
                    y="tract count" + ':Q',
                    color=feature,
                    tooltip=['county_name', feature, "tract count"]) \
            .interactive()
    else:
        bar = alt.Chart(df) \
            .mark_bar() \
            .encode(x='Census Tract',
                    y=feature + ':Q',
                    tooltip=['Census Tract', feature]) \
            .interactive()
    st.altair_chart(bar, use_container_width=True)

def make_scatter_plot_counties(df: pd.DataFrame, feature_1: str, feature_2: str,
                               scaling_feature: str = 'Total Population', data_format:str='Raw Values'):
    label_1 = feature_1
    label_2 = feature_2
    if data_format == 'Per Capita':
        print('Per Cap')
        label_1 = f"{feature_1} per capita"
        df[label_1] = df[feature_1] / df['Total Population']
        label_2 = f"{feature_2} per capita"
        df[label_2] = df[feature_2] / df['Total Population']
    elif data_format == 'Per Square Mile':
        print('SQMI')
        label_1 = f"{feature_1} per sqmi"
        df[label_1] = df[feature_1] / df['sqmi']
        label_2 = f"{feature_2} per sqmi"
        df[label_2] = df[feature_2] / df['sqmi']
    df = df.round(3)


    scatter_df = df[[label_1, label_2, 'County Name', scaling_feature]]
    scatter = alt.Chart(scatter_df).mark_point() \
        .encode(x=label_1 + ':Q', y=label_2 + ':Q',
                tooltip=['County Name', scaling_feature, label_1, label_2],
                size=scaling_feature).interactive()
    st.altair_chart(scatter, use_container_width=True)


def make_scatter_plot_census_tracts(df: pd.DataFrame, feature_1: str, feature_2: str,
                                    scaling_feature: str = 'tot_population_census_2010'):
    scatter_df = df.reset_index(drop=True)[[feature_1, feature_2, 'Census Tract', scaling_feature]]
    scatter = alt.Chart(scatter_df).mark_point() \
        .encode(x=feature_1 + ':Q', y=feature_2 + ':Q',
                tooltip=['Census Tract', scaling_feature, feature_1, feature_2],
                size=scaling_feature).interactive()
    st.altair_chart(scatter, use_container_width=True)
        
def make_equity_census_map(geo_df: pd.DataFrame, df: pd.DataFrame, map_feature: str):

    EQUITY_MAP_HEADERS = [map_feature] + [x + '_check' for x in queries.EQUITY_CENSUS_POC_LOW_INCOME] + [x + '_check' for x in queries.EQUITY_CENSUS_REMAINING_HEADERS]

    if 'Census Tract' in geo_df.columns:
        geo_df.reset_index(inplace=True)
    if 'Census Tract' in df.columns:
        df.reset_index(inplace=True)
    geo_df_copy = geo_df.copy()
    geojson = utils.convert_geom(geo_df_copy, df, EQUITY_MAP_HEADERS)
    geojson_df = pd.DataFrame(geojson)

    geo_df_copy["coordinates"] = geojson_df["features"].apply(lambda row: row["geometry"]["coordinates"])
    geo_df_copy["name"] = geojson_df["features"].apply(lambda row: row["properties"]["name"])

    for header in EQUITY_MAP_HEADERS:
        geo_df_copy[header] = geojson_df["features"].apply(lambda row: row["properties"][header])

    scaler = pre.MinMaxScaler()
    feat_series = geo_df_copy[map_feature]
    feat_type = None
    if feat_series.dtype == 'object':
        feat_type = 'category'
        feat_dict = {k: (i % 10) / 10 for i, k in enumerate(feat_series.unique())} # max 10 categories, following from constants.BREAK, enumerated rather than encoded
        normalized_vals = feat_series.apply(lambda x: feat_dict[x]) # getting normalized vals, manually.
    else:
        feat_type = 'numerical'
        normalized_vals = scaler.fit_transform(
            pd.DataFrame(feat_series)
        )
  
    colors = list(map(color_scale, normalized_vals))
    geo_df_copy['fill_color'] = colors
    geo_df_copy.fillna(0, inplace=True)

    tooltip = {"html": ""}
    if 'Census Tract' in set(geo_df_copy.columns):
        keep_cols = ['coordinates', 'name', 'fill_color', 'geom', map_feature]
        geo_df_copy.drop(list(set(geo_df_copy.columns) - set(keep_cols)), axis=1, inplace=True)
        if feat_type == 'numerical':
            tooltip = {
                "html": "<b>Tract ID:</b> {" + str('name') + "} </br>" +
                "<b>" + str(map_feature) + ":</b> {" + str(map_feature) + "}% </br>"
                }
        else:
            tooltip = {
                "html": "<b> {" + str(map_feature) + "} </b> </br>" +
                "<b>Tract ID:</b> {" + str('name') + "} </br>" 
                }

    elif 'County Name' in set(geo_df_copy.columns):
        geo_df_copy.drop(['geom', 'County Name'], axis=1, inplace=True)
        tooltip = {
            "html": "<b>County:</b> {name} </br>" + "<b>" + str(map_feature) + ":</b> {" + str(map_feature) + "}"
            }
    if len(geo_df_copy['coordinates'][0][0][0]) > 0:
        view_state = pdk.ViewState(**{"latitude": geo_df_copy['coordinates'][0][0][0][1], "longitude": geo_df_copy['coordinates'][0][0][0][0], "zoom": 5, "maxZoom": 16, "pitch": 0, "bearing": 0})
    else:
        view_state = pdk.ViewState(**{"latitude": 36, "longitude": -95, "zoom": 3, "maxZoom": 16, "pitch": 0, "bearing": 0})

    if feat_type == 'numerical':
        geo_df_copy = geo_df_copy.astype({map_feature: 'float64'})

    polygon_layer = pdk.Layer(
        "PolygonLayer",
        geo_df_copy,
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

def make_transport_census_map(geo_df: pd.DataFrame, df: pd.DataFrame, map_feature: str):

    if 'Census Tract' in geo_df.columns:
        geo_df.reset_index(inplace=True)
    if 'Census Tract' in df.columns:
        df.reset_index(inplace=True)
    geo_df_copy = geo_df.copy()
    geojson = utils.convert_geom(geo_df_copy, df, queries.TRANSPORT_CENSUS_HEADERS)
    geojson_df = pd.DataFrame(geojson)

    geo_df_copy["coordinates"] = geojson_df["features"].apply(lambda row: row["geometry"]["coordinates"])
    geo_df_copy["name"] = geojson_df["features"].apply(lambda row: row["properties"]["name"])

    for header in queries.TRANSPORT_CENSUS_HEADERS:
        geo_df_copy[header] = geojson_df["features"].apply(lambda row: row["properties"][header])

    scaler = pre.MinMaxScaler()
    feat_series = geo_df_copy[map_feature]
    feat_type = None
    if feat_series.dtype == 'object':
        feat_type = 'category'
        feat_dict = {k: (i % 10) / 10 for i, k in enumerate(feat_series.unique())} # max 10 categories, following from constants.BREAK, enumerated rather than encoded
        normalized_vals = feat_series.apply(lambda x: feat_dict[x]) # getting normalized vals, manually.
    else:
        feat_type = 'numerical'
        normalized_vals = scaler.fit_transform(
            pd.DataFrame(feat_series)
        )

    colors = list(map(color_scale, normalized_vals))
    geo_df_copy['fill_color'] = colors
    geo_df_copy.fillna(0, inplace=True)

    tooltip = {"html": ""}
    if 'Census Tract' in set(geo_df_copy.columns):
        keep_cols = ['coordinates', 'name', 'fill_color', 'geom', map_feature]
        geo_df_copy.drop(list(set(geo_df_copy.columns) - set(keep_cols)), axis=1, inplace=True)
        if map_feature == 'Index Value':
            tooltip = {
            "html": "<b>Tract ID:</b> {" + str('name') + "} </br>" +
            "<b>" + str(map_feature) + ":</b> {" + str(map_feature) + "} </br>"
            }
        else:
            tooltip = {
            "html": "<b>Tract ID:</b> {" + str('name') + "} </br>" +
            "<b>" + str(map_feature) + ":</b> {" + str(map_feature) + "}% </br>"
            }  
        
    if len(geo_df_copy['coordinates'][0][0][0]) > 0:
        view_state = pdk.ViewState(**{"latitude": geo_df_copy['coordinates'][0][0][0][1], "longitude": geo_df_copy['coordinates'][0][0][0][0], "zoom": 5, "maxZoom": 16, "pitch": 0, "bearing": 0})
    else:
        view_state = pdk.ViewState(**{"latitude": 36, "longitude": -95, "zoom": 3, "maxZoom": 16, "pitch": 0, "bearing": 0})

    if feat_type == 'numerical':
        geo_df_copy = geo_df_copy.astype({map_feature: 'float64'})

    polygon_layer = pdk.Layer(
        "PolygonLayer",
        geo_df_copy,
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

def make_equity_census_chart(df: pd.DataFrame, threshold: dict, average: dict, feature: str):
    df['average']= average[feature]
    df['threshold'] = threshold[feature]

    baselines = pd.DataFrame([{"name":'average', "value": average[feature]},
        {"name":'concentration threshold', "value": threshold[feature]}])

    feature = feature + ' (%)'
    feat_type = 'category' if df[feature].dtype == 'object' else 'numerical'
    data_df = pd.DataFrame(df[[feature, 'Census Tract', 'county_name']])
    
    if feat_type == 'category':
        data_df = pd.DataFrame(data_df.groupby(['county_name', feature]).size())
        data_df = data_df.rename(columns={0: "tract count"})
        # print(data_df)
        data_df = data_df.reset_index()
        bar = alt.Chart(data_df)\
            .mark_bar() \
            .encode(x=alt.X('county_name', axis = alt.Axis(labels=False)),
                    y="tract count" + ':Q',
                    color=feature,
                    tooltip=['county_name', feature, "tract count"])\
            .interactive()
    else:
        bar = alt.Chart(df)\
            .mark_bar() \
            .encode(x=alt.X('Census Tract:O', axis = alt.Axis(labels=False), title='Census Tract Distribution', sort='y'),
                    y=alt.Y(feature + ':Q', title=feature),
                    color=alt.Color('Census Tract',
                    # scale=alt.Scale(scheme='blues'),
                     legend=alt.Legend(orient='bottom')),
                    tooltip=['Census Tract', feature])\
            .interactive()
        
        rules = alt.Chart(baselines).mark_rule().encode(
            y='value:Q'
        )

        text = alt.Chart(baselines).mark_text(
            align='left', dx=-300, dy=5, fontSize=15, fontWeight='bold'
        ).encode(
            alt.Y('value:Q'), text = 'name'
        )
        
    st.altair_chart(bar+rules+text, use_container_width=True)

def make_transport_census_chart(df: pd.DataFrame, average: dict, feature: str):
    df['average']= average[feature]

    baselines = pd.DataFrame([{"name":'county average', "value": average[feature]}])

    feat_type = 'category' if df[feature].dtype == 'object' else 'numerical'
    data_df = pd.DataFrame(df[[feature, 'Census Tract', 'county_name']])
    
    if feat_type == 'category':
        data_df = pd.DataFrame(data_df.groupby(['county_name', feature]).size())
        data_df = data_df.rename(columns={0: "tract count"})
        # print(data_df)
        data_df = data_df.reset_index()
        bar = alt.Chart(data_df)\
            .mark_bar() \
            .encode(x=alt.X('county_name', axis = alt.Axis(labels=False)),
                    y="tract count" + ':Q',
                    color=feature,
                    tooltip=['county_name', feature, "tract count"])\
            .interactive()
    else:
        bar = alt.Chart(df)\
            .mark_bar() \
            .encode(x=alt.X('Census Tract:O', axis = alt.Axis(labels=False), title='Census Tracts', sort='y'),
                    y=alt.Y(feature + ':Q', title='Households(%)'),
                    tooltip=['Census Tract', feature])\
            .interactive()
        
        rules = alt.Chart(baselines).mark_rule().encode(
            y='value:Q'
        )

        text = alt.Chart(baselines).mark_text(
            align='right', dx=300, dy=5, fontSize=15, fontWeight='bold'
        ).encode(
            alt.Y('value:Q'), text = 'name'
        )
        
    st.altair_chart(bar+rules+text, use_container_width=True)

def make_horizontal_bar_chart(average: dict, epc_average: dict, feature: str):
    df = pd.DataFrame([{"name":'County average', "value": average[feature]},
        {"name":'EPC average', "value": epc_average[feature]}])

    bar = alt.Chart(df)\
            .mark_bar() \
            .encode(x=alt.X('value:Q', title = 'Households (%)'), 
                    y=alt.Y('name:O', axis=alt.Axis(title = "")),
                    color=alt.Color('name', legend=None))

    st.altair_chart(bar, use_container_width=True)

def make_grouped_bar_chart(df: pd.DataFrame, id_var: str, features: list, features_name: str):
    df = df.melt( [id_var], features, features_name)

    bar = alt.Chart(df)\
            .mark_bar() \
            .encode(column=alt.Column(features_name+':N'), x=alt.X(id_var+':O'), 
                    y=alt.Y('value'+':Q'),
                    color=id_var+':N',
                    tooltip=[id_var, 'value'])\
            .interactive()
    st.altair_chart(bar, use_container_width=True)

def make_stacked(df:pd.DataFrame):

    bar = alt.Chart(df)\
            .mark_bar() \
            .encode(x=alt.X('Census Tract:O', axis = alt.Axis(labels=False), title='Census Tracts', sort='y'),
                    y=alt.Y('sum(Index Value):Q', title='Transportation Vulnerability Index'),
                    color=alt.Color('Indicators:N', legend=alt.Legend(orient='left')),
                    tooltip=['Census Tract'])\
            .interactive()
        
    st.altair_chart(bar, use_container_width=True)

def make_histogram(df: pd.DataFrame, feature: str):
    base = alt.Chart(df)
    hist = base.mark_bar().encode(
        x = alt.X(feature+':Q', bin=alt.BinParams()
        ),
        y='count()'
        )
    median_line = base.mark_rule().encode(
        x = alt.X('mean('+feature+'):Q', title = feature),
        size = alt.value(5)
    )
    st.altair_chart(hist+median_line, use_container_width=True)

def make_simple_chart(df: pd.DataFrame, feature: str):
    
    bar = alt.Chart(df.reset_index())\
        .mark_bar() \
        .encode(x='index:O',
                y=feature + ':Q',
                tooltip=['index', feature])\
        .interactive()
    st.altair_chart(bar, use_container_width=True)

#This function can be used with shapefiles (point and linestring geometries)

# def make_transit_map(geo_df: pd.DataFrame, df: pd.DataFrame, map_feature: str):
    
#     NTM_shapes = gpd.read_file('NTM_shapes.json')
#     NTM_shapes['start']=NTM_shapes['geometry'].apply(lambda x: [x.coords[0][0], x.coords[0][1]])
#     NTM_shapes['end']=NTM_shapes['geometry'].apply(lambda x: [x.coords[1][0], x.coords[1][1]])
    
#     NTM_stops = gpd.read_file('NTM_stops.json')
#     NTM_stops['coordinates']=NTM_stops['geometry'].apply(lambda p: [p.x, p.y])
#     NTM_stops.rename(columns={"stop_name":"route_desc"})
    
#     if 'Census Tract' in geo_df.columns:
#         geo_df.reset_index(inplace=True)
#     # if 'Census Tract' in df.columns:
#         # df.reset_index(inplace=True)
#     geo_df_copy = geo_df.copy()
#     geojson = utils.convert_geom(geo_df_copy, df, queries.TRANSPORT_CENSUS_HEADERS)
#     geojson_df = pd.DataFrame(geojson)

#     geo_df_copy["coordinates"] = geojson_df["features"].apply(lambda row: row["geometry"]["coordinates"])
#     geo_df_copy["name"] = geojson_df["features"].apply(lambda row: row["properties"]["name"])

#     for header in queries.TRANSPORT_CENSUS_HEADERS:
#         geo_df_copy[header] = geojson_df["features"].apply(lambda row: row["properties"][header])

#     scaler = pre.MinMaxScaler()
#     feat_series = geo_df_copy[map_feature]
#     feat_type = None
#     if feat_series.dtype == 'object':
#         feat_type = 'category'
#         feat_dict = {k: (i % 10) / 10 for i, k in enumerate(feat_series.unique())} # max 10 categories, following from constants.BREAK, enumerated rather than encoded
#         normalized_vals = feat_series.apply(lambda x: feat_dict[x]) # getting normalized vals, manually.
#     else:
#         feat_type = 'numerical'
#         normalized_vals = scaler.fit_transform(
#             pd.DataFrame(feat_series)
#         )
#     # norm_df = pd.DataFrame(feat_series)
#     colors = list(map(color_scale, normalized_vals))
#     geo_df_copy['fill_color'] = colors
#     geo_df_copy.fillna(0, inplace=True)

#     tooltip = {"html": ""}
#     if 'Census Tract' in set(geo_df_copy.columns):
#         keep_cols = ['coordinates', 'name', 'fill_color', 'geom', map_feature]
#         geo_df_copy.drop(list(set(geo_df_copy.columns) - set(keep_cols)), axis=1, inplace=True)
#         tooltip = {
#             "html": "<b> Description:</b> {route_desc} </br>" +
#             # "<b> Type: </b>" + 
#             " {route_type_text} </br>" + 
#             # "<b> Link: </b>" +
#             "{route_url}" }

#     # elif 'County Name' in set(geo_df_copy.columns):
#     #     geo_df_copy.drop(['geom', 'County Name'], axis=1, inplace=True)
#     #     tooltip = {
#     #         "html": "<b>County:</b> {name} </br>" + "<b>" + str(map_feature) + ":</b> {" + str(map_feature) + "}"
#     #         # "<b>" + str(EQUITY_CENSUS_HEADERS[0]) + ":</b> {" + str(EQUITY_CENSUS_HEADERS[0]) + "}" +
#     #         }
#     if len(geo_df_copy['coordinates'][0][0][0]) > 0:
#         view_state = pdk.ViewState(**{"latitude": geo_df_copy['coordinates'][0][0][0][1], "longitude": geo_df_copy['coordinates'][0][0][0][0], "zoom": 5, "maxZoom": 16, "pitch": 0, "bearing": 0})
#     else:
#         view_state = pdk.ViewState(**{"latitude": 36, "longitude": -95, "zoom": 3, "maxZoom": 16, "pitch": 0, "bearing": 0})

#     if feat_type == 'numerical':
#         geo_df_copy = geo_df_copy.astype({map_feature: 'float64'})
        
#     polygon_layer = pdk.Layer(
#         "PolygonLayer",
#         geo_df_copy,
#         get_polygon="coordinates",
#         filled=True,
#         get_fill_color='fill_color',
#         stroked=False,
#         opacity=0.15,
#         pickable=False,
#         auto_highlight=True,
#     )
    
#     shape_layer = pdk.Layer(
#         "LineLayer",
#         NTM_shapes,
#         get_source_position='start',
#         get_target_position='end',
#         get_color=[176, 203, 156],
#         get_width=10,
#         highlight_color=[176, 203, 156],
#         picking_radius=10,
#         auto_highlight=True,
#         pickable=True,
#         )
    
#     stop_layer = pdk.Layer(
#         'ScatterplotLayer',
#         NTM_stops,
#         get_position='coordinates',
#         auto_highlight=True,
#         get_radius=10,
#         # get_fill_color='color',
#         pickable=True)
    
#     r = pdk.Deck(
#         layers=[polygon_layer, shape_layer, stop_layer],
#         initial_view_state=view_state,
#         map_style=pdk.map_styles.LIGHT,
#         tooltip=tooltip
#     )
    
#     st.pydeck_chart(r)

   
