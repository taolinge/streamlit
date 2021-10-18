import pandas as pd
import streamlit as st

import queries
import utils
import visualization
from constants import STATES


def county_equity_index():
    st.write('## County Equity Index')
    st.write('This interface allows you to see and interact with county data in our database.')
    task = st.selectbox('How much data do you want to look at?', ['Counties', 'State', 'National'], 0)
    state, counties, name, df = None, None, None, None
    if task == 'Counties':
        state = st.selectbox("Select a state", STATES).strip()
        county_list = queries.counties_query()
        county_list = county_list[county_list['State'] == state]['County Name'].to_list()
        county_list.sort()
        counties = st.multiselect('Please specify counties to compare', county_list)
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

        # st.write('''
        #         ### View Feature
        #         Select a feature to view for each county
        #         ''')
        # single_feature = st.selectbox('Feature', feature_labels, 0)
        
        temp = df.copy()
        temp.reset_index(inplace=True)
        # temp.drop(['geom'], inplace=True, axis=1)

        st.write('''
                ### View Equity Data
                Age 19 or Under''')
        visualization.make_chart(temp, 'Age 19 or Under')

        st.write('Age 65 or over')
        visualization.make_chart(temp, 'Age 65 or Over')

        st.write('Non-White Population (%)')
        visualization.make_chart(temp, 'Non-White Population (%)')

        # counties = temp['County Name'].to_list()
        # if task != 'National':
        #     geo_df = queries.get_county_geoms(counties, state.lower())
        #     visualization.make_map(geo_df, temp, single_feature)
        # else:
        #     county_ids = temp['county_id'].to_list()
        #     geo_df = queries.get_county_geoms_by_id(county_ids)
        #     visualization.make_map(geo_df, temp, single_feature)

        # st.write('''
        #     ### Compare Features
        #     Select two features to compare on the X and Y axes. Only numerical data can be compared.
        #     ''')
        # col1, col2, col3 = st.beta_columns(3)
        # with col1:
        #     feature_1 = st.selectbox('X Feature', feature_labels, 0)
        # with col2:
        #     feature_2 = st.selectbox('Y Feature', feature_labels, 1)
        # with col3:
        #     scaling_feature = st.selectbox('Scaling Feature', feature_labels, 17)
        # if feature_1 and feature_2:
        #     visualization.make_scatter_plot_counties(temp, feature_1, feature_2, scaling_feature)
        
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


def census_equity_index():
    st.write('## Census Tract Equity Index')
    st.write("""This interface allows you to see and interact with census tract data in our database. """)
    state = st.selectbox("Select a state", STATES).strip()
    county_list = queries.counties_query()
    county_list = county_list[county_list['State'] == state]['County Name'].to_list()
    county_list.sort()
    counties = st.multiselect('Please a county', ['All'] + county_list)
    # tables = st.multiselect('Please specify one or more datasets to view', queries.CENSUS_TABLES)
    # tables = ['poverty_status', 'sex_by_age']
    tables = queries.EQUITY_CENSUS_TABLES
    
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


        df = queries.clean_equity_data(df)
        df, thresholds, averages = queries.get_equity_priority_communities(df)

        geo_df = df.copy()
        df.drop(['geom'], inplace=True, axis=1)
        # st.write(df.loc[:, df.columns != 'geom'])
        
        geo_df = geo_df[['geom', 'Census Tract', 'tract_id']]

        st.write('''
                ### Equity Priority Communities
                Census tracts have been selected as Equity Priority Communities (EPCs) using the MTC Equity Framework for Plan Bay Area 2040. 
                Census tracts qualify by meeting at least one of the two criteria below.                 
                ''')
        

        col1, col2 = st.columns((1,1))
        with col1:
            st.write('''**Criteria A:**
                *Census tracts have a concentration of BOTH people of color AND low-income households* 
                ''')
        with col2: 
            with st.expander(label='View in map'):
                st.write('Census tracts that meet Criteria A to be considered Equity Priority Communities')
                visualization.make_equity_census_map(geo_df, df, 'Criteria A')
        
        col1, col2 = st.columns((1,1))
        with col1:
            st.write('''
                **Criteria B:** *Census tracts have a concentration of three or more of the remaining 6 factors AND a concentration of low-income households* 
                ''')
        with col2: 
            with st.expander(label='View in map'):
                st.write('Census tracts that meet Criteria A to be considered Equity Priority Communities')
                visualization.make_equity_census_map(geo_df, df, 'Criteria B')

        feature = st.selectbox("Select an equity indicator to see how the census tract levels compare to the county average",
            queries.EQUITY_CENSUS_POC_LOW_INCOME+queries.EQUITY_CENSUS_REMAINING_HEADERS
                )
        
        visualization.make_equity_census_chart(df, averages, feature)

        st.write("Map of the Equity Priority Communities")
        # visualization.make_equity_census_map(geo_df, df, 'tot_population_census_2010')
       
        # with st.expander(label='Filter census tracts '):
        #     col1, col2 = st.columns((1,1))
        #     with col1:
        #         number_tracts = st.selectbox("Limit number of census tracts shown", [5,10,15,20])
        #     with col2:
        #         sort_by = st.selectbox("Sort census tracts by", ['tract value', 'equity index value'])
        # col1, col2 = st.columns((1,3))
        # with col1:
        #     st.write('''**Select census tracts for analysis**''')
        #     if sort_by == 'tract value':
        #         for tract in geo_df['tract_id'].sort_values().head(number_tracts):
        #             selected=st.checkbox(str(tract), value=True, help='Include census tract in Transportation analysis below')
        #             if selected:
        #                 selected_tracts.append(tract)
        #             st.write('###### Equity index value: ', 
        #                 str(df[df['tract_id']==tract].loc[:,'equity_index_value'].item())                    
        #             )
        #             st.write("")
        #     else:
        #         for tract in df.loc[df['tract_id'].isin(geo_df['tract_id'])].sort_values('equity_index_value', ascending=False).head(number_tracts)['tract_id']:
        #             selected=st.checkbox(str(tract), value=True, help='Include census tract in Transportation analysis below')
        #             if selected:
        #                 selected_tracts.append(tract)
        #             st.write('###### Equity index value: ', 
        #                 str(df[df['tract_id']==tract].loc[:,'equity_index_value'].item())                    
        #             )
        #             st.write("")

        # with col2:
        #     visualization.make_equity_census_map(geo_df, df, 'equity_index_value')


        tables = queries.TRANSPORT_CENSUS_TABLES
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

        if 'state_name' in df.columns:
            df = df.loc[:, ~df.columns.duplicated()]
            df['State'] = df['state_name']
        if 'county_name' in df.columns:
            df = df.loc[:, ~df.columns.duplicated()]
            df['County Name'] = df['county_name']
        df.set_index(['State', 'County Name'], drop=True, inplace=True)

        geo_df = df.copy()
        df.drop(['geom'], inplace=True, axis=1)

        st.write('''
                ### Compare Transportation Factors
                 ''')

        visualization.make_grouped_bar_chart(df,'tract_id', ['percent_hh_0_veh','percent_hh_1_veh', 'percent_hh_2more_veh'],
            'Household Vehicles'
            )
        

        # for header in queries.TRANSPORT_CENSUS_HEADERS[3:]:
        #     st.write(header)
        #     visualization.make_equity_census_chart(df.loc[df['tract_id'].isin(selected_tracts)], header)
