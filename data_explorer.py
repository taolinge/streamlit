import pandas as pd
import streamlit as st

import queries
import utils
import visualization
from constants import STATES


def county_data_explorer():
    st.write('## County Data Explorer')
    st.write('This interface allows you to see and interact with county data in our database.')
    task = st.selectbox('How much data do you want to look at?', ['Counties', 'State', 'National'], 0)
    state, counties, name, df = None, None, None, None
    if task == 'Counties':
        state = st.selectbox("Select a state", STATES).strip()
        county_list = queries.counties_query()
        county_list = county_list[county_list['State'] == state]['County Name'].to_list()
        county_list.sort()
        counties = st.multiselect('Please specify one or more counties', county_list)
        counties = [_.strip().lower() for _ in counties]
        if len(counties) > 0:
            df = queries.get_county_data(state, counties)
            name = f"{state}_county_data"
    elif task == 'State':
        state = st.selectbox("Select a state", STATES).strip()
        df = queries.get_county_data(state)
        name = f"{state}_data"
    elif task == 'National':
        st.info('National analysis can take some time and be difficult to visualize at the moment.')
        df = queries.get_national_county_data()
        name = "national_data"

    if df is not None:
        if st.checkbox('Show raw data'):
            st.subheader('Raw Data')
            st.caption(str(df.shape))
            st.dataframe(df)
            st.markdown(utils.get_table_download_link(df, name, 'Download raw data'), unsafe_allow_html=True)

        feature_labels = list(set(df.columns) - {'County Name', 'county_id'})
        feature_labels.sort()

        st.write('''
                ### View Feature
                Select a feature to view for each county
                ''')
        single_feature = st.selectbox('Feature', feature_labels, 0)
        temp = df.copy()
        temp.reset_index(inplace=True)
        visualization.make_bar_chart(temp, single_feature)

        counties = temp['County Name'].to_list()
        if task != 'National':
            geo_df = queries.get_county_geoms(counties, state.lower())
            visualization.make_map(geo_df, temp, single_feature)
        else:
            county_ids = temp['county_id'].to_list()
            geo_df = queries.get_county_geoms_by_id(county_ids)
            visualization.make_map(geo_df, temp, single_feature)
        st.write('''
            ### Compare Features
            Select two features to compare on the X and Y axes
            ''')
        col1, col2, col3 = st.beta_columns(3)
        with col1:
            feature_1 = st.selectbox('X Feature', feature_labels, 0)
        with col2:
            feature_2 = st.selectbox('Y Feature', feature_labels, 1)
        with col3:
            scaling_feature = st.selectbox('Scaling Feature', feature_labels, 17)
        if feature_1 and feature_2:
            visualization.make_scatter_plot_counties(temp, feature_1, feature_2, scaling_feature)
        temp.drop(['State', 'County Name', 'county_id'], inplace=True, axis=1)
        visualization.make_correlation_plot(temp, ['Burdened Households (%)',
                                                   'Housing Units',
                                                   'Income Inequality (Ratio)',
                                                   'Median Age',
                                                   'Non-White Population (%)',
                                                   'Population Below Poverty Line (%)',
                                                   'Renter Occupied Units',
                                                   'Resident Population (Thousands of Persons)',
                                                   'Single Parent Households (%)',
                                                   'Unemployment Rate (%)',
                                                   'Vacant Units',
                                                   'VulnerabilityIndex',
                                                   ])


def census_data_explorer():
    st.write('## Census Tract Data Explorer')
    st.write("""This interface allows you to see and interact with census tract data in our database. """)
    state = st.selectbox("Select a state", STATES).strip()
    county_list = queries.counties_query()
    county_list = county_list[county_list['State'] == state]['County Name'].to_list()
    county_list.sort()
    counties = st.multiselect('Please a county', ['All'] + county_list)
    tables = st.multiselect('Please specify one or more datasets to view', queries.CENSUS_TABLES)
    tables = [_.strip().lower() for _ in tables]
    tables.sort()

    if len(tables) > 0 and len(counties) > 0:
        try:
            if 'All' in counties:
                df = queries.latest_data_census_tracts(state, county_list, tables)
            else:
                df = queries.latest_data_census_tracts(state, counties, tables)
        except:
            df=pd.DataFrame()

        if st.checkbox('Show raw data'):
            st.subheader('Raw Data')
            st.caption(str(df.shape))
            st.dataframe(df)
            st.markdown(utils.get_table_download_link(df, state + '_data', 'Download raw data'), unsafe_allow_html=True)
        if 'state_name' in df.columns:
            df = df.loc[:, ~df.columns.duplicated()]
            df['State'] = df['state_name']
        if 'county_name' in df.columns:
            df = df.loc[:, ~df.columns.duplicated()]
            df['County Name'] = df['county_name']
        df.set_index(['State', 'County Name'], drop=True, inplace=True)
        feature_labels = list(
            set(df.columns) - {'County Name', 'county_id', 'index', 'county_name', 'Census Tract', 'geom',
                               'state_id', 'state_name', 'tract', 'tract_id'})
        feature_labels.sort()
        st.write('''
                ### View Feature
                Select a feature to view for each county
                ''')
        single_feature = st.selectbox('Feature', feature_labels, 0)
        visualization.make_census_bar_chart(df, single_feature)

        geo_df = df.copy()
        geo_df = geo_df[['geom', 'Census Tract', 'tract_id']]
        visualization.make_map(geo_df, df, single_feature)

        st.write('''
            ### Compare Features
            Select two features to compare on the X and Y axes
            ''')
        col1, col2, col3 = st.beta_columns(3)
        with col1:
            feature_1 = st.selectbox('X Feature', feature_labels, 0)
        with col2:
            feature_2 = st.selectbox('Y Feature', feature_labels, 1)
        with col3:
            scaling_feature = st.selectbox('Scaling Feature', feature_labels, len(feature_labels)-1)
        if feature_1 and feature_2:
            visualization.make_scatter_plot_census_tracts(df, feature_1, feature_2, scaling_feature)

        df.drop(list(set(df.columns) - set(feature_labels)), axis=1, inplace=True)
        display_columns = []
        for col in df.columns:
            display_columns.append(col)
        display_columns.sort()
        visualization.make_correlation_plot(df, display_columns)
