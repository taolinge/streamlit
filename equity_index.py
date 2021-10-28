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
        
        st.write('')
        st.write('''
                ### Equity Priority Communities
                *Census tracts have been selected as Equity Priority Communities (EPCs) using the MTC Equity Framework for Plan Bay Area 2040. 
                Census tracts qualify by meeting at least one of the two criteria below.*                 
                ''')
                
        col1, col2 = st.columns((1,1))
        with col1:
            st.write('###### **Criteria A:**')
            st.write('Census tracts have a concentration of BOTH people of color AND low-income households')
        with col2: 
            st.write('###### **Criteria B:**')
            st.write('Census tracts have a concentration of three or more of the remaining 6 factors AND a concentration of low-income households')
        st.expander('Details on Equity Priority Community factors')

        st.write('')
        st.write('')
        st.write('###### Concentration thresholds')
        concentration = st.select_slider('Increase the concentration threshold to limit the number of equity priority communities',
            options=['Low', 'Medium', 'High'])
        coeff = {'Low':0.5, 'Medium':1, 'High':1.5}

        df = queries.clean_equity_data(df)
        df, thresholds, averages, total_census_tracts = queries.get_equity_priority_communities(df, coeff[concentration])

        geo_df = df.copy()
        df_copy = df.copy()
        df.drop(['geom'], inplace=True, axis=1)
        geo_df = geo_df[['geom', 'Census Tract', 'tract_id']]

        st.write('')
        st.write('')
        st.write('##### View Equity Priority Communities on Map')
        col1, col2 = st.columns((1,4))
        with col1:
            EPC_map = st.radio("View census tracts that meet criteria", ('Criteria A', 'Criteria B'))
        with col2:
            visualization.make_equity_census_map(geo_df, total_census_tracts, EPC_map)    

        feature = st.selectbox("Select an equity indicator to see how the census tract levels compare to the county average",
            queries.EQUITY_CENSUS_POC_LOW_INCOME+queries.EQUITY_CENSUS_REMAINING_HEADERS
                )
        
        visualization.make_equity_census_chart(df, thresholds, averages, feature)

        tables = queries.TRANSPORT_CENSUS_TABLES
        tables = [_.strip().lower() for _ in tables]
        tables.sort()

        if len(tables) > 0 and len(counties) > 0:
            try:
                if 'All' in counties:
                    transport_df = queries.latest_data_census_tracts(state, county_list, tables)
                else:
                    transport_df = queries.latest_data_census_tracts(state, counties, tables)
            except:
                transport_df=pd.DataFrame()

        if 'state_name' in transport_df.columns:
            transport_df = transport_df.loc[:, ~transport_df.columns.duplicated()]
            transport_df['State'] = transport_df['state_name']
        if 'county_name' in transport_df.columns:
            transport_df = transport_df.loc[:, ~transport_df.columns.duplicated()]
            transport_df['County Name'] = transport_df['county_name']
        transport_df.set_index(['State', 'County Name'], drop=True, inplace=True)
        
        geo_df = transport_df.copy()
        transport_epc, averages, epc_averages, transport_df = queries.clean_transport_data(transport_df, df_copy)
        geo_df = transport_df.copy()
        geo_epc = transport_epc.copy()
        geo_df = geo_df[['geom', 'Census Tract', 'tract_id']]
        geo_epc = geo_epc[['geom', 'Census Tract', 'tract_id']]

        st.write('''
                ### Compare Transportation Factors
                #### Vehicles per household
                 ''')

        col1, col2 = st.columns((1,1))
        with col1:
            radio_feature = st.radio('Filter analysis for ',('0 vehicles per household', '1 vehicle per household', '2 or more vehicles per household'))
            select_feature = {'0 vehicles per household':'percent_hh_0_veh', '1 vehicle per household':'percent_hh_1_veh', '2 or more vehicles per household':'percent_hh_2more_veh'}
        with col2:
            radio_data = st.radio('', ('Equity Priority Communities only', 'All census tracts'))
            select_data = {'All census tracts':transport_df, 'Equity Priority Communities only':transport_epc}
            select_geo = {'All census tracts':geo_df, 'Equity Priority Communities only':geo_epc}
        st.write('')
        st.write('###### Compare averages:')
        visualization.make_horizontal_bar_chart(averages, epc_averages, select_feature[radio_feature])
        st.write('###### Identify census tracts:')
        visualization.make_transport_census_map(select_geo[radio_data], select_data[radio_data], select_feature[radio_feature]) 

        transport_epc.drop(['geom'], inplace=True, axis=1)
        transport_df.drop(['geom'], inplace=True, axis=1)
        st.write('###### View distribution for equity priority commmunities (', radio_feature, '):')
        visualization.make_transport_census_chart(transport_epc, averages, select_feature[radio_feature])
 
        
