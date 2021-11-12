from numpy import maximum
import pandas as pd
import streamlit as st

import queries
import utils
import visualization
from constants import STATES


def county_equity_explorer():
    st.write('## County Equity Explorer')
    st.write('Currently, the equity explorer is limited to a census tract level. We hope to include a count-level analysis in the future.')

def census_equity_explorer():
    indent = 4
    
    st.write('## Equity Explorer')
    st.write("""This interface allows you to see and interact with census tract data in our database. """)

    st.write('')
    st.write('')
    st.write('''
            ### Select a Geography
            *Identify which census tracts you are interested in exploring.*                 
            ''')
    st.write('')


    col1, col2= st.columns((1+indent,1))
    with col1:
        state = st.selectbox("Select a state", STATES).strip()
        county_list = queries.counties_query()
        county_list = county_list[county_list['State'] == state]['County Name'].to_list()
        county_list.sort()
        counties = st.multiselect('Select a county', ['All'] + county_list)
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
            st.dataframe(df.iloc[:, 2:])
            st.markdown(utils.get_table_download_link(df, state + '_data', 'Download raw data'), unsafe_allow_html=True)
        if 'state_name' in df.columns:
            df = df.loc[:, ~df.columns.duplicated()]
            df['State'] = df['state_name']
        if 'county_name' in df.columns:
            df = df.loc[:, ~df.columns.duplicated()]
            df['County Name'] = df['county_name']
        df.set_index(['State', 'County Name'], drop=True, inplace=True)
        
        
        st.write('')
        st.write('')
        st.write('''
                ### Equity Geographies
                *Census tracts qualify as Equity Geographies by meeting at least one of the two criteria below. This methodology is based on the equity priority community [methodology](https://bayareametro.github.io/Spatial-Analysis-Mapping-Projects/Project-Documentation/Equity-Priority-Communities/#summary-of-mtc-epc-demographic-factors--demographic-factor-definitions) developed by the San Francisco Bay Area Metropolitan Transportation Commission (MTC).*                 
                ''')
        st.write('')

        col1, col2, col3= st.columns(((1+indent)/2,(1+indent)/2,1))
        with col1:
            st.write('##### **Criteria A:**')
            st.write('Census tracts have a concentration of BOTH people of color AND low-income households')
        with col2: 
            st.write('##### **Criteria B:**')
            st.write('Census tracts have a concentration of three or more of the remaining six equity indicators AND a concentration of low-income households')
        col1, col2= st.columns((1+indent,1))

        with col1:
            st.write('')
            with st.expander('List of equity indicators'):
                st.write("More details to come! Read [here](https://bayareametro.github.io/Spatial-Analysis-Mapping-Projects/Project-Documentation/Equity-Priority-Communities/#summary-of-mtc-epc-demographic-factors--demographic-factor-definitions) for more info")
        
        # col1, col2, col3= st.columns((1,indent,1))
        st.write('')
        st.write('')
        # with col2:
        st.write('##### Identify a concentration threshold')
        st.caption('Equity geographies are compared against concentration thresholds as defined below.')
        st.write('')
        st.write('*concentration threshold = average + (standard deviation* * **coefficient)**')
        st.write('')
        st.write('')
        col1, col2= st.columns((1+indent,1))
        with col1:
            concentration = st.select_slider('Limit the number of equity geographies by setting the coefficient to low (0.5), medium (1), or high (1.5).',
                options=['Low', 'Medium', 'High'])
            coeff = {'Low':0.5, 'Medium':1, 'High':1.5}

        df = queries.clean_equity_data(df)
        df, total_census_tracts, concentration_thresholds, averages, epc_averages  = queries.get_equity_geographies(df, coeff[concentration])

        geo_df = df.copy()
        df_copy = df.copy()
        df.drop(['geom'], inplace=True, axis=1)
        total_census_tracts.drop(['geom'], inplace=True, axis=1)
        geo_df = geo_df[['geom', 'Census Tract', 'tract_id']]

        st.write('')
        st.write('')
        st.write('##### View Equity Geographies on Map')
        st.caption('The map below shows all the equity geographies based on the selected coefficient above. Scroll over the equity geographies to view which of the criteria is met.')
        visualization.make_equity_census_map(geo_df, df, 'Criteria')    

        st.write('')
        st.write('')
        st.write('''
                ### Equity Indicators
                *Compare Equity Geographies to the rest of the county for any of the equity indicators. Refer to criteria A and B above for more information on how equity indicators are used to identify Equity Geographies.*                 
                ''')
        st.write('')
        
        col1, col2= st.columns((1+indent,1))
        with col1:
            feature = st.selectbox("Select an equity indicator to see how the census tract levels compare to the county average",
                queries.EQUITY_CENSUS_POC_LOW_INCOME+queries.EQUITY_CENSUS_REMAINING_HEADERS)

        # col1, col2, col3= st.columns((1,indent,1))
        # with col2:  
        st.write('')
        st.write('')
        visualization.make_horizontal_bar_chart(averages, epc_averages, feature)

        st.write('')
        visualization.make_equity_census_map(geo_df, df, feature+' (%)') 
        st.write('')
        st.write('')
        # st.write('##### Compare Equity Geographies to other census tracts in the county')
        # st.caption('See how the Equity Geographies are distributed for the selected equity indicator.')
        # feature = st.selectbox("Select an equity indicator to see how the census tract levels compare to the county average",
        #     queries.EQUITY_CENSUS_POC_LOW_INCOME+queries.EQUITY_CENSUS_REMAINING_HEADERS
        #         )
        # visualization.make_equity_census_chart(total_census_tracts, concentration_thresholds, averages, feature)
        
        with st.expander('View data at the census tract level'):
            filter_data = (['Census Tract']+[x+' (%)' for x in queries.EQUITY_CENSUS_POC_LOW_INCOME]+
                [x+' (%)' for x in queries.EQUITY_CENSUS_REMAINING_HEADERS]
                )
            st.dataframe(df[filter_data].reset_index(drop=True))

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
        st.markdown("""---""")
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
        
        st.write('###### See the variation by geography:')
        visualization.make_transport_census_map(select_geo[radio_data], select_data[radio_data], select_feature[radio_feature]) 

        st.write('###### How does the Equity Geography average compare to the county-wide average?')
        visualization.make_horizontal_bar_chart(averages, epc_averages, select_feature[radio_feature])

        transport_epc.drop(['geom'], inplace=True, axis=1)
        transport_df.drop(['geom'], inplace=True, axis=1)
        st.write('###### Equity Geography Census Tracts (', radio_feature, '):')
        visualization.make_transport_census_chart(transport_epc, averages, select_feature[radio_feature])
        
        st.write('#### Walkability Index')
        # values = st.slider('Select a range', 0.0, max(transport_df['walkability_index']), (0.0, max(transport_df['walkability_index'])))
        visualization.make_transport_census_map(geo_epc, transport_epc, 'walkability_index')

        st.write('#### Vehicle Miles Traveled')
        visualization.make_transport_census_map(geo_epc, transport_epc, 'vehicle_miles_traveled')