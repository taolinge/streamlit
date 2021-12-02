from numpy import maximum
import pandas as pd
import streamlit as st
# from fpdf import FPDF
# import base64

import queries
import utils
import visualization
from constants import STATES, EQUITY_DATA_TABLE, TRANSPORT_DATA_TABLE, LINKS

# def create_download_link(val, filename):
#     b64 = base64.b64encode(val)  # val looks like b'...'
#     return f'<a href="data:application/octet-stream;base64,{b64.decode()}" download="{filename}.pdf">Download file</a>'

def county_equity_explorer():
    st.write('## County Equity Explorer')
    st.write('Currently, the equity explorer is limited to a census tract level. Please select the Census Tracts radio button on the sidebar.')

def census_equity_explorer():
    indent = 4
    
    st.write('## Equity Explorer')
    st.write("""This interface allows you to see and interact with census tract data in our database. """)

    st.write('''  
            # \n  \n  
            ### Select a Geography
            *Identify which census tracts you are interested in exploring.*            
            ''')

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
        county_list = queries.all_counties_query()
        county_list = county_list[county_list['state_name'] == state]['county_name'].to_list()
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
        
        df = queries.clean_equity_data(df)
        
        st.write('''
                # \n  \n  
                ### Equity Geographies
                *Census tracts qualify as Equity Geographies by meeting at least one of the two criteria below. This methodology is based on the equity priority community [methodology](https://bayareametro.github.io/Spatial-Analysis-Mapping-Projects/Project-Documentation/Equity-Priority-Communities/#summary-of-mtc-epc-demographic-factors--demographic-factor-definitions) developed by the San Francisco Bay Area Metropolitan Transportation Commission (MTC).*                 
                # \n 
                ''')

        col1, col2, col3= st.columns((5,1,5))
        with col1:
            st.write('##### **Criteria A:**')
            st.write('Census tracts have a concentration of BOTH people of color AND low-income households')
        with col3: 
            st.write('##### **Criteria B:**')
            st.write('Census tracts have a concentration of three or more of the remaining six equity indicators AND a concentration of low-income households')
        
        st.write('')
        with st.expander('List of equity indicators'):
            st.write('''
                     We currently have almost 40 tables in the database, representing over 2 million rows of data. The following datasets were used for the equity indicators considered.
                      \n  \n  
                    ''',
                    EQUITY_DATA_TABLE,
                    "For more information on the framework that the criteria is based on, read [here](" +LINKS['mtc_framework']+ ") for more info.")
        st.write('''
                 # \n
                 ##### Identify a concentration threshold
                 ''')
        st.caption('Equity geographies are compared against concentration thresholds as defined below.')
        st.write('''
                 # \n
                 *concentration threshold = average + (standard deviation* * **coefficient)**
                 # \n
                 ''')
        
        col1, col2= st.columns((1+indent,1))
        with col1:
            concentration = st.select_slider('Limit the number of equity geographies by setting the coefficient to low (0.5), medium (1), or high (1.5).',
                options=['Low', 'Medium', 'High'])
            coeff = {'Low':0.5, 'Medium':1, 'High':1.5}

        df, total_census_tracts, concentration_thresholds, averages, epc_averages  = queries.get_equity_geographies(df, coeff[concentration])

        geo_df = df.copy()
        geo_total = total_census_tracts.copy()
        df_copy = df.copy()
        df.drop(['geom'], inplace=True, axis=1)
        total_census_tracts.drop(['geom'], inplace=True, axis=1)
        geo_df = geo_df[['geom', 'Census Tract']]
        geo_total = geo_total[['geom', 'Census Tract']]

        st.write('''
                #  \n  \n
                 ##### View Equity Geographies on Map
                 ''')
        st.caption('The map below shows all the equity geographies based on the selected coefficient above. Scroll over the equity geographies to view which of the criteria is met.')
        visualization.make_equity_census_map(geo_df, df, 'Criteria')  
        # visualization.make_equity_census_map(geo_total, total_census_tracts, 'Criteria')    
        
        st.write('''
                #  \n  \n
                ### Equity Indicators
                *Compare Equity Geographies to the rest of the county for any of the equity indicators. Refer to criteria A and B above for more information on how equity indicators are used to identify Equity Geographies.*  
                #  \n
                ''')
        
        col1, col2= st.columns((1+indent,1))
        with col1:
            feature = st.selectbox("Select an equity indicator to see how the census tract levels compare to the county average",
                queries.EQUITY_CENSUS_POC_LOW_INCOME+queries.EQUITY_CENSUS_REMAINING_HEADERS)

        st.write('''
                # \n  
                ###### How does the Equity Geography average compare to the county-wide average?''')
        visualization.make_horizontal_bar_chart(averages, epc_averages, feature)
        
        st.write('###### View variation by geography')
        
        radio_data = st.radio('Filter map for:', ('Equity Geographies only', 'All census tracts in selected region'),key='equity')
        select_data = {'All census tracts in selected region':total_census_tracts, 'Equity Geographies only':df}
        select_geo = {'All census tracts in selected region':geo_total, 'Equity Geographies only':geo_df}
        
        visualization.make_equity_census_map(select_geo[radio_data], select_data[radio_data], feature+' (%)') 
        
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

        transport_df = transport_df.loc[:, ~transport_df.columns.duplicated()]
        if 'state_name' in transport_df.columns:
            transport_df['State'] = transport_df['state_name']
        if 'county_name' in transport_df.columns:
            transport_df['County Name'] = transport_df['county_name']
        transport_df.set_index(['State', 'County Name'], drop=True, inplace=True)
        
        transport_epc, transport_df, normalized_data, averages, epc_averages = queries.clean_transport_data(transport_df, df_copy)

        geo_df = transport_df.copy()
        geo_epc = transport_epc.copy()
        geo_df = geo_df[['geom', 'Census Tract']]
        geo_epc = geo_epc[['geom', 'Census Tract']]
        st.markdown("""---""")
        
        st.write('''
                ### Equity in Transportation
                *Analyze behavior and transportation considerations for vulnerable communities in the county.*                 
                ''')
        with st.expander('More about this dataset'):
                st.write('''
                     We currently have almost 40 tables in the database, representing over 2 million rows of data. The following datasets were used for the transportation indicators considered.
                      \n  \n  
                    ''',
                    TRANSPORT_DATA_TABLE)
        st.write('''
                #  \n
                #### Transportation Indicators''')
        col1, col2= st.columns((1+indent,1))
        with col1:
            feature = st.selectbox("Select an indicator to see how the census tract levels compare to the county average",
                queries.TRANSPORT_CENSUS_HEADERS)

        st.write('###### How does the Equity Geography average compare to the county-wide average?')
        visualization.make_horizontal_bar_chart(averages, epc_averages, feature)

        st.write('###### View variation by geography')
        radio_data = st.radio('Filter map for:', ('Equity Geographies only', 'All census tracts in selected region'),key='transport')
        select_data = {'All census tracts in selected region':transport_df, 'Equity Geographies only':transport_epc}
        select_geo = {'All census tracts in selected region':geo_df, 'Equity Geographies only':geo_epc}
        
        visualization.make_transport_census_map(select_geo[radio_data], select_data[radio_data], feature) 
        
        transport_epc.drop(['geom'], inplace=True, axis=1)
        transport_df.drop(['geom'], inplace=True, axis=1)
        normalized_data.drop(['geom'], inplace=True, axis=1)
        st.write('')
        st.write('###### Equity Geography Census Tracts (', feature, '):')
        
        visualization.make_transport_census_chart(transport_epc, averages, feature)
        
        st.write('''
                # \n
                #### Create Transportation Vulnerability Index
                *Consider the vulnerability of Equity Geographies with regard to their access to transit*                 
                # \n
                ###### Select which indicators to use in the Transportation Vulnerability Index
                ''')
        
        selected_indicators = st.multiselect('Transportation Indicators', queries.TRANSPORT_CENSUS_HEADERS, 
                    default =['Zero-Vehicle Households', 'Vehicle Miles Traveled', 'Drive Alone Commuters', 'No Computer Households']
                    )
        
        st.write('''
                # \n
                ###### Select weights for the selected indicators to compare the Equity Geographies                
                ''')
        index_value = {}
        for header in selected_indicators:
                index_value[header] = st.number_input(header, min_value=0, max_value=100, value=round((100/len(selected_indicators))), key = header)
        
        if sum(index_value.values())>101 or sum(index_value.values())<99:
            st.error("Weights must sum to 100")
        
        st.write('''
                # \n
                ###### Equity Geographies are sorted below based on the assigned Transportation Vulnerability index values                
                ''')
        normalized_data = normalized_data.melt('Census Tract', selected_indicators, 'Indicators')
        normalized_data['value'] = normalized_data['Indicators'].apply(lambda x: index_value[x])*normalized_data['value']
        transport_index = normalized_data.groupby(['Census Tract'])['value'].sum()
        visualization.make_stacked(normalized_data)

        transport_index.sort_values(ascending=False, inplace=True)
        
        st.write('###### View the census tracts with the highest index values')
        num_tracts = st.slider('Select number of census tracts to view', 
                  min_value = 1, max_value = len(transport_index),
                  value = [5 if 5 < len(transport_index) else len(transport_index)]
                  )[0]
        
        selected = transport_index.head(num_tracts).reset_index()
        selected_tracts = transport_epc.loc[transport_epc['Census Tract'].isin(selected['Census Tract'])]
        selected_tracts['value'] = selected_tracts['Census Tract'].apply(lambda x: transport_index.loc[x])
        selected_geo = geo_epc.loc[geo_epc['Census Tract'].isin(selected['Census Tract'])]
        selected_geo['value'] = selected_geo['Census Tract'].apply(lambda x: round(transport_index.loc[x]))
        
        visualization.make_transport_census_map(selected_geo, selected_tracts, 'value')
        # visualization.make_transit_map(selected_geo, selected_tracts, 'value')