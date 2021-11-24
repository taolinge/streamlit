from numpy import maximum
import pandas as pd
import streamlit as st
from fpdf import FPDF
import base64

import queries
import utils
import visualization
from constants import STATES

def create_download_link(val, filename):
    b64 = base64.b64encode(val)  # val looks like b'...'
    return f'<a href="data:application/octet-stream;base64,{b64.decode()}" download="{filename}.pdf">Download file</a>'

def county_equity_explorer():
    st.write('## County Equity Explorer')
    st.write('Currently, the equity explorer is limited to a census tract level. Please select the Census Tracts radio button on the sidebar.')

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

    # report_text = st.text_input("Report Text")
    # export_as_pdf = st.button("Export Report")
    # if export_as_pdf:
    #     pdf = FPDF()
    #     pdf.add_page()
    #     pdf.set_font('Arial', 'B', 16)
    #     pdf.cell(40, 10, report_text)
    #     html = create_download_link(pdf.output(dest="S").encode("latin-1"), "test")

    #     st.markdown(html, unsafe_allow_html=True)

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

        col1, col2, col3= st.columns((5,1,5))
        with col1:
            st.write('##### **Criteria A:**')
            st.write('Census tracts have a concentration of BOTH people of color AND low-income households')
        with col3: 
            st.write('##### **Criteria B:**')
            st.write('Census tracts have a concentration of three or more of the remaining six equity indicators AND a concentration of low-income households')
        col1, col2= st.columns((1+indent,1))

        with col1:
            st.write('')
            with st.expander('List of equity indicators'):
                st.write("More details to come! Read [here](" +queries.LINKS['mtc_framework']+ ") for more info")
        
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
        geo_total = total_census_tracts.copy()
        df_copy = df.copy()
        df.drop(['geom'], inplace=True, axis=1)
        total_census_tracts.drop(['geom'], inplace=True, axis=1)
        geo_df = geo_df[['geom', 'Census Tract', 'tract_id']]
        geo_total = geo_total[['geom', 'Census Tract', 'tract_id']]

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
        st.write('###### How does the Equity Geography average compare to the county-wide average?')
        visualization.make_horizontal_bar_chart(averages, epc_averages, feature)
        
        st.write('###### View variation by geography')
        col1, col2 = st.columns((1, indent))
        with col1:
            radio_data = st.radio('Filter map for:', ('Equity Geos', 'All census tracts'),key='equity')
            select_data = {'All census tracts':total_census_tracts, 'Equity Geos':df}
            select_geo = {'All census tracts':geo_total, 'Equity Geos':geo_df}
        with col2:
            visualization.make_equity_census_map(select_geo[radio_data], select_data[radio_data], feature+' (%)') 
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
        
        transport_epc, transport_df, normalized_data, averages, epc_averages = queries.clean_transport_data(transport_df, df_copy)

        geo_df = transport_df.copy()
        geo_epc = transport_epc.copy()
        geo_df = geo_df[['geom', 'Census Tract', 'tract_id']]
        geo_epc = geo_epc[['geom', 'Census Tract', 'tract_id']]
        st.markdown("""---""")
        
        st.write('''
                ### Equity in Transportation
                *Analyze behavior and transportation considerations for vulnerable communities in the county.*                 
                ''')
        with st.expander('More about this dataset'):
                st.write("More details to come! Read [here](" +queries.LINKS['household_vehicle_availability']+ ") for more info")
        st.write('')
        st.write('#### Transportation Indicators')
        col1, col2= st.columns((1+indent,1))
        with col1:
            feature = st.selectbox("Select an indicator to see how the census tract levels compare to the county average",
                queries.TRANSPORT_CENSUS_HEADERS)

        st.write('###### How does the Equity Geography average compare to the county-wide average?')
        visualization.make_horizontal_bar_chart(averages, epc_averages, feature)

        st.write('###### View variation by geography')
        col1, col2 = st.columns((1, indent))
        with col1:
            radio_data = st.radio('Filter map for:', ('Equity Geos', 'All census tracts'), key = 'transport')
            select_data = {'All census tracts':transport_df, 'Equity Geos':transport_epc}
            select_geo = {'All census tracts':geo_df, 'Equity Geos':geo_epc}
        with col2:
            visualization.make_transport_census_map(select_geo[radio_data], select_data[radio_data], feature) 
        
        st.write('')
        transport_epc.drop(['geom'], inplace=True, axis=1)
        transport_df.drop(['geom'], inplace=True, axis=1)
        normalized_data.drop(['geom'], inplace=True, axis=1)
        st.write('###### Equity Geography Census Tracts (', feature, '):')
        
        visualization.make_transport_census_chart(transport_epc, averages, feature)
        st.write('')
        
        st.write('')
        st.write('''
                #### Create Transportation Vulnerability Index
                *Select weights for the following indicators to compare the vulnerability of Equity Geographies*                 
                ''')
        col1, col2, col3 = st.columns((1,1,1))
        with col1:
            index_options = [0,1,2,3]
            index_value = {}
            for header in queries.TRANSPORT_CENSUS_HEADERS[:3]:
                index_value[header] = st.select_slider(header, options = index_options, key = header, value = 1)
        with col2:
            for header in queries.TRANSPORT_CENSUS_HEADERS[3:5]:
                index_value[header] = st.select_slider(header, options = index_options, key = header, value = 1)
        with col3:
            for header in queries.TRANSPORT_CENSUS_HEADERS[5:7]:
                index_value[header] = st.select_slider(header, options = index_options, key = header, value = 1)

        normalized_data = normalized_data.melt('tract_id', queries.TRANSPORT_CENSUS_HEADERS, 'Indicators')
        normalized_data['value'] = normalized_data['Indicators'].apply(lambda x: index_value[x])*normalized_data['value']
        transport_index = normalized_data.groupby(['tract_id'])['value'].sum()
        visualization.make_stacked(normalized_data)

        transport_index.sort_values(ascending=False, inplace=True)
        
        st.write('###### View census tracts with highest index values')
        num_tracts = st.slider('Select number of census tracts to view', 
                  min_value = 1, max_value = len(transport_index),
                  value = [5 if 5 < len(transport_index) else len(transport_index)]
                  )[0]
        
        selected = transport_index.head(num_tracts).reset_index()
        selected_tracts = transport_epc.loc[transport_epc['tract_id'].isin(selected['tract_id'])]
        selected_tracts['value'] = selected_tracts['tract_id'].apply(lambda x: transport_index.loc[x])
        selected_geo = geo_epc.loc[geo_epc['tract_id'].isin(selected['tract_id'])]
        selected_geo['value'] = selected_geo['tract_id'].apply(lambda x: transport_index.loc[x])
        
        visualization.make_transport_census_map(selected_geo, selected_tracts, 'value')