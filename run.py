import getopt
import os
import sys

import pandas as pd
import streamlit as st
import seaborn as sns
import matplotlib.pyplot as plt
import altair as alt

import queries
import analysis
import utils
import visualization
from constants import STATES

# Pandas options
pd.set_option('max_rows', 25)
pd.set_option('max_columns', 12)
pd.set_option('expand_frame_repr', True)
pd.set_option('large_repr', 'truncate')
pd.options.display.float_format = '{:.2f}'.format

MODE = 'UI'


def filter_state(data: pd.DataFrame, state: str) -> pd.DataFrame:
    return data[data['State'].str.lower() == state.lower()]


def filter_counties(data: pd.DataFrame, counties: list) -> pd.DataFrame:
    counties = [_.lower() for _ in counties]
    return data[data['County Name'].str.lower().isin(counties)]


def load_all_data() -> pd.DataFrame:
    if os.path.exists("Output/all_tables.xlsx"):
        try:
            res = input('Previous data found. Use data from local `all_tables.xlsx`? [y/N]')
            if res.lower() == 'y' or res.lower() == 'yes':
                df = pd.read_excel('Output/all_tables.xlsx')
            else:
                df = queries.latest_data_all_tables()
        except:
            print('Something went wrong with the Excel file. Falling back to database query.')
            df = queries.latest_data_all_tables()
    else:
        df = queries.latest_data_all_tables()

    return df


def get_existing_policies(df: pd.DataFrame) -> pd.DataFrame:
    policy_df = queries.policy_query()
    temp_df = df.merge(policy_df, on='county_id')
    if not temp_df.empty and len(df) == len(temp_df):
        if MODE == 'SCRIPT':
            res = input('Policy data found in database. Use this data? [Y/n]').strip()
            if res.lower() == 'y' or res.lower() == 'yes' or res == '':
                return temp_df
        elif MODE == 'UI':
            if st.checkbox('Use existing policy data?'):
                return temp_df
    else:
        policy_df = pd.read_excel('Policy Workbook.xlsx', sheet_name='Analysis Data')
        temp_df = df.merge(policy_df, on='County Name')
        if not temp_df.empty and len(df) == len(temp_df):
            return temp_df
        # else:
        #     print(
        #         "INFO: Policy data not found. Check that you've properly filled in the Analysis Data page in `Policy Workbook.xlsx` with the counties you're analyzing.")

    return df


def get_single_county(county: str, state: str) -> pd.DataFrame:
    df = load_all_data()
    df = filter_state(df, state)
    df = filter_counties(df, [county])
    df = get_existing_policies(df)
    df = analysis.clean_data(df)

    return df


def get_multiple_counties(counties: list, state: str) -> pd.DataFrame:
    df = load_all_data()
    df = filter_state(df, state)
    df = filter_counties(df, counties)
    df = get_existing_policies(df)
    df = analysis.clean_data(df)

    return df


def get_state_data(state: str) -> pd.DataFrame:
    df = load_all_data()
    df = filter_state(df, state)
    df = get_existing_policies(df)
    df = analysis.clean_data(df)

    return df


def print_summary(df: pd.DataFrame, output: str):
    print('*** Results ***')
    if 'Rank' in df.columns:
        print('* Shown in order by overall priority, higher values mean higher priority.')
        df.sort_values('Rank', ascending=False, inplace=True)
        print(df['Rank'])
        print('Normalized analysis data is located at {o}'.format(o=output[:-5]) + '_overall_vulnerability.xlsx')
    elif len(df) > 1:
        print('* Shown in order by relative risk, higher values mean higher relative risk.')
        df.sort_values('Relative Risk', ascending=False, inplace=True)
        print(df['Relative Risk'])
        print('Normalized analysis data is located at {o}'.format(o=output[:-5]) + '_overall_vulnerability.xlsx')
    else:
        print('Fetched single county data')

    print('Raw fetched data is located at {o}'.format(o=output))
    print('Done!')


def load_distributions():
    metro_areas = queries.generic_select_query('housing_stock_distribution', [
        'location',
        '0_br_pct',
        '1_br_pct',
        '2_br_pct',
        '3_br_pct',
        '4_br_pct'
    ])
    locations = list(metro_areas['location'])
    metro_areas.set_index('location', inplace=True)

    return metro_areas, locations


def make_correlation_plot(df: pd.DataFrame, default_cols=[]):
    st.subheader('Correlation Plot')
    st.write('''
    This plot shows how individual features in the database correlate to each other. Values range from -1 to 1. 
    A value of 1 means that for a positive increase in one feature, there will be an increase in the other by a fixed proportion.
    A value of -1 means that for a positive increase in one feature, there will be a decrease in the other by a fixed proportion. 
    A value of 0 means that the two features are unrelated. A higher value can be read as a stronger relationship 
    (either postive or negative) between the two features.
    ''')
    fig, ax = plt.subplots(figsize=(10, 10))
    df = df.astype('float64')
    cols_to_compare = st.multiselect('Columns to consider', list(df.columns), default_cols)
    if len(cols_to_compare) > 2:
        st.write(sns.heatmap(df[cols_to_compare].corr(), annot=True, linewidths=0.5))
    st.pyplot(fig)


def eviction_visualizations(df: pd.DataFrame, state: str = None):
    if state:
        temp = df.copy()
        temp.reset_index(inplace=True)
        counties = temp['County Name'].to_list()
        if state.lower() != 'national':
            geo_df = queries.get_county_geoms(counties, state.lower())
            visualization.make_map(geo_df, df, 'Relative Risk')
        else:
            frames = []
            for s in STATES:
                frames.append(queries.get_county_geoms(counties, s.lower()))
            geo_df = pd.concat(frames)
            visualization.make_map(geo_df, df, 'Relative Risk')


def data_explorer(df: pd.DataFrame, state: str):
    feature_labels = list(set(df.columns) - {'County Name', 'county_id'})
    feature_labels.sort()
    st.write('''
            ### View Feature
            Select a feature to view for each county
            ''')
    single_feature = st.selectbox('Feature', feature_labels, 0)
    visualization.make_bar_chart(df, single_feature)

    if state:
        temp = df.copy()
        temp.reset_index(inplace=True)
        counties = temp['County Name'].to_list()
        if state != 'national':
            geo_df = queries.get_county_geoms(counties, state.lower())
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
    if feature_1 and feature_2:
        scatter_df = df.reset_index()[
            [feature_1, feature_2, 'County Name', 'Resident Population (Thousands of Persons)']]
        scatter = alt.Chart(scatter_df).mark_point() \
            .encode(x=feature_1 + ':Q', y=feature_2 + ':Q',
                    tooltip=['County Name', 'Resident Population (Thousands of Persons)', feature_1, feature_2],
                    size='Resident Population (Thousands of Persons)')
        st.altair_chart(scatter, use_container_width=True)
      
    df.drop(['county_id'], axis=1, inplace=True)
    make_correlation_plot(df, ['Burdened Households (%)', 'Unemployment Rate (%)', 'VulnerabilityIndex',
                               'Non-White Population (%)', 'Renter Occupied Units', 'Income Inequality (Ratio)',
                               'Median Age',
                               'Population Below Poverty Line (%)', 'Single Parent Households (%)'])


def census_data_explorer(df: pd.DataFrame, county, state: str, table):
    feature_labels = list(set(df.columns) - {'County Name', 'county_id', 'index', 'county_name'})
    feature_labels.sort()
    st.write('''
            ### View Feature
            Select a feature to view for each county
            ''')
    single_feature = st.selectbox('Feature', feature_labels, 0)
    visualization.make_census_bar_chart(df, single_feature)

    if state:
        temp = df.copy()
        temp.reset_index(inplace=True)
        tracts = temp['tract_id'].to_list()
        if state != 'national':
            geo_df = queries.census_tracts_geom_query(table[0], county, state.lower())
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
    if feature_1 and feature_2:
        scatter_df = df.reset_index()[
            [feature_1, feature_2, 'tract_id', 'tot_population_census_2010']]
        scatter = alt.Chart(scatter_df).mark_point() \
            .encode(x=feature_1 + ':Q', y=feature_2 + ':Q',
                    tooltip=['tract_id', 'tot_population_census_2010', feature_1, feature_2],
                    size='tot_population_census_2010')
        st.altair_chart(scatter, use_container_width=True)

    df.drop(['county_id', 'county_name', 'state_name', 'index', 'tract_id', 'tot_population_census_2010'], axis=1, inplace=True)
    display_columns = []
    for col in df.columns:
        display_columns.append(col)  
    make_correlation_plot(df, display_columns)


def relative_risk_ranking(df: pd.DataFrame, label: str) -> pd.DataFrame:
    st.subheader('Relative Risk')
    st.write('Relative Risk is a metric to compare the potential risk of eviction between multiple counties. '
             'Values are normalized and combined to create the Relative Risk index. '
             'You can add or remove features, or just use our defaults which we developed working with our partners.')
    columns_to_consider = st.multiselect('Features to consider in Relative Risk',
                                         list(set(df.columns) - {'county_id'}),
                                         ["Burdened Households (%)",
                                          "Income Inequality (Ratio)",
                                          "Population Below Poverty Line (%)",
                                          "Single Parent Households (%)",
                                          "Unemployment Rate (%)",
                                          "Resident Population (Thousands of Persons)",
                                          "VulnerabilityIndex",
                                          "Housing Units",
                                          "Vacant Units",
                                          "Renter Occupied Units",
                                          "Median Age",
                                          "Non-White Population (%)"]) + ['county_id']
    ranks = analysis.rank_counties(df[columns_to_consider], label + '_selected_counties').sort_values(
        by='Relative Risk',
        ascending=False)
    st.write('Higher values correspond to more relative risk. Values can be between 0 and 1.')
    st.write(ranks['Relative Risk'])
    st.markdown(utils.get_table_download_link(ranks, label + '_ranking', 'Download Relative Risk ranking'),
                unsafe_allow_html=True)
    return ranks


def cost_of_evictions(df, metro_areas, locations):
    st.write('You can use either the Fair Market or Median rents in a county for this analysis.')
    rent_type = st.selectbox('Rent Type', ['Fair Market', 'Median'], 0)
    st.write('This calculation is based on the combined rent for 0 bedroom to 4+ bedroom units. The distribution of '
             'housing stock changes around the US, so you can pick a distribution similar to your location or just use '
             'the national average. You can then select a proportion of the rent-burdened population to support.')
    location = st.selectbox('Select a location to assume a housing distribution:', locations)
    distribution = {
        0: float(metro_areas.loc[location, '0_br_pct']),
        1: float(metro_areas.loc[location, '1_br_pct']),
        2: float(metro_areas.loc[location, '2_br_pct']),
        3: float(metro_areas.loc[location, '3_br_pct']),
        4: float(metro_areas.loc[location, '4_br_pct']),
    }
    if st.checkbox('Show distribution (decimal values)'):
        st.write(distribution)

    pct_burdened = st.slider('Percent of Burdened Population to Support', 0, 100, value=50, step=1)

    if rent_type == '' or rent_type == 'Fair Market':
        df = analysis.calculate_cost_estimate(df, pct_burdened, rent_type='fmr', distribution=distribution)
    elif rent_type == 'Median':
        df = analysis.calculate_cost_estimate(df, pct_burdened, rent_type='rent50', distribution=distribution)

    cost_df = df.reset_index()
    cost_df.drop(columns=['State'], inplace=True)
    cost_df.set_index('County Name', inplace=True)
    cost_df = cost_df.round(0)
    cost_cols = ['rent50_0', 'rent50_1', 'rent50_2', 'rent50_3', 'rent50_4', 'fmr_0', 'fmr_1', 'fmr_2', 'fmr_3',
                 'fmr_4', 'br_cost_0', 'br_cost_1', 'br_cost_2', 'br_cost_3', 'br_cost_4', 'total_cost']
    cost_df.drop(list(set(df.columns) - set(cost_cols)), axis=1, inplace=True)
    st.bar_chart(cost_df['total_cost'])
    if st.checkbox('Show cost data'):
        st.write('`fmr_*` represents the fair market rent per unit and `rent_50_*` represents the median rent per unit.'
                 '`br_cost_*` is the total cost for the chosen housing stock distribution and percentage of the'
                 ' burdened population for each type of unit. `total_cost` is sum of the `br_cost_` for each type of'
                 ' housing unit.')
        st.dataframe(cost_df)
    return cost_df


def run_UI():
    st.set_page_config(
        page_title="Arup Social Data",
        page_icon="🏠",
        initial_sidebar_state="expanded")
    st.sidebar.title('Arup Social Data')
    workflow = st.sidebar.selectbox('Workflow', ['Data Explorer', 'Eviction Analysis'])
    if workflow == 'Data Explorer':
        data_type = st.sidebar.radio("Select data boundary:", ('County Level', 'Census Tracts'), index=0)
    st.sidebar.write("""
    This tool supports analysis of United States county level data from a variety of data sources. There are two workflows: an Eviction
     Analysis workflow, which is specifically focused on evictions as a result of COVID-19, and a Data Explorer workflow,
     which allows you to see and interact with the data we have without doing any analysis.
     
     You can also use our Python code in a scripting environment or query our database directly. Details are at our 
     [GitHub](https://github.com/arup-group/social-data). If you find bugs, please reach out or create an issue on our 
     GitHub repository. If you find that this interface doesn't do what you need it to, you can create an feature request 
     at our repository or better yet, contribute a pull request of your own. You can reach out to the team on LinkedIn or 
     Twitter if you have questions or feedback.
 
    More documentation and contribution details are at our [GitHub Repository](https://github.com/arup-group/social-data).
    """)
    with st.sidebar.beta_expander("Credits"):
        """
        This app is the result of hard work by our team:
        - Angela Wilson
        - Sam Lustado
        - Lingyi Chen
        - Kevin McGee
        - [Jared Stock 🐦](https://twitter.com/jaredstock) 
    
        
        Special thanks to Julieta Moradei and Kamini Ayer from New Story, Kristin Maun from the city of Tulsa, 
        Emily Walport and Irene Gleeson with Arup's Community Engagment team, and everyone else who has given feedback 
        and helped support this work. Also thanks to the team at Streamlit for their support of this work.
        
        The analysis and underlying data are provided as open source under an [MIT license](https://github.com/arup-group/social-data/blob/master/LICENSE). 
        
        Made by [Arup](https://www.arup.com/).
            """
    if workflow == 'Eviction Analysis':
        st.write('### Eviction Data Analysis')
        with st.beta_expander("About"):
            st.write(
                """
                This is an analysis based on work we did with [New Story](https://newstorycharity.org/) to help them
                 make decisions about how to distribute direct aid to families to help keep people in their homes. The 
                 end result of this analysis is something we call 'Relative Risk.' This value is a synthesis of the 
                 sociodemographic characteristics of a county that can be used to compare counties against each other. 
                 It is *not* a measure of objective risk.
                 
                 This analysis uses *total population* in its current iteration, not percentage values. This is to 
                 capture that counties with more people represent more potential risk than smaller counties. Values from 
                 a variety of data sources are normalized and then combined to represent the Relative Risk Index. 
                 
                 In addition to the Relative Risk calculation, we've also built calculations to estimate the cost to 
                 avoid evictions by providing direct aid for a subset of the community.  
                 
                 As with any analysis that relies on public data, we should acknowledge that the underlying data is not 
                 perfect. Public data has the potential to continue and exacerbate the under-representation of 
                 certain groups. This data should not be equated with the ground truth of the conditions in a community. 
                 You can read more about how we think about public data [here](https://medium.com/swlh/digital-government-and-data-theater-a-very-real-cause-of-very-fake-news-fe23c0dfa0a2).
                 
                 You can read more about the data and calculations happening here on our [GitHub](https://github.com/arup-group/social-data).
                """
            )

        task = st.selectbox('What type of analysis are you doing?',
                            ['Single County', 'Multiple Counties', 'State', 'National'], 1)
        metro_areas, locations = load_distributions()

        if task == 'Single County' or task == '':
            res = st.text_input('Enter the county and state (ie: Jefferson County, Colorado):')
            if res:
                res = res.strip().split(',')
                county = res[0].strip()
                state = res[1].strip()
                if county and state:
                    df = get_single_county(county, state)
                    if st.checkbox('Show raw data'):
                        st.subheader('Raw Data')
                        st.dataframe(df)
                        st.markdown(utils.get_table_download_link(df, county + '_data', 'Download raw data'),
                                    unsafe_allow_html=True)

                    with st.beta_expander('Cost to avoid evictions'):
                        st.write("""
                        The cost to avoid evictions is defined as the cost to a municipality or other entity if it was to pay 
                        people's rent directly. In this calculation, we assume a distribution of housing stock (0 bedroom to 4+ bedroom)
                         based on Census data. You can select which distribution to use that is most similar to the community that you're analyzing. 

                         We default to using Fair Market Rents for this calculation, but you can use the Median value as well. 

                         We also assume that only the burdened population is being considered for support, but not every burdened 
                         person will receive support. You can adjust the percentage of the burdened population to consider.

                         The reported value is the *monthly cost* to an entity to support the chosen housing distribution, rent type, and percent of the burdened population. 

                         This is only an estimate, and should not be used for detailed planning or policy making.
                        """)

                    if st.checkbox('Do cost to avoid eviction analysis?'):
                        evictions_cost_df = cost_of_evictions(df, metro_areas, locations)
                        st.markdown(
                            utils.get_table_download_link(evictions_cost_df, county + '_cost_data',
                                                          'Download cost data'),
                            unsafe_allow_html=True)

                else:
                    st.error('Enter a valid county and state, separated by a comma')
                    st.stop()

        elif task == 'Multiple Counties':
            state = st.selectbox("Select a state", STATES).strip()
            county_list = queries.counties_query()
            county_list = county_list[county_list['State'] == state]['County Name'].to_list()
            counties = st.multiselect('Please specify one or more counties', county_list)
            counties = [_.strip().lower() for _ in counties]
            if len(counties) > 0:
                df = get_multiple_counties(counties, state)

                if st.checkbox('Show raw data'):
                    st.subheader('Raw Data')
                    st.dataframe(df)
                    st.markdown(utils.get_table_download_link(df, state + '_custom_data', 'Download raw data'),
                                unsafe_allow_html=True)

                with st.beta_expander('Cost to avoid evictions'):
                    st.write("""
                    The cost to avoid evictions is defined as the cost to a municipality or other entity if it was to pay 
                    people's rent directly. In this calculation, we assume a distribution of housing stock (0 bedroom to 4+ bedroom)
                     based on Census data. You can select which distribution to use that is most similar to the community that you're analyzing. 

                     We default to using Fair Market Rents for this calculation, but you can use the Median value as well. 

                     We also assume that only the burdened population is being considered for support, but not every burdened 
                     person will receive support. You can adjust the percentage of the burdened population to consider.

                     The reported value is the *monthly cost* to an entity to support the chosen housing distribution, rent type, and percent of the burdened population. 

                     This is only an estimate, and should not be used for detailed planning or policy making.
                    """)

                if st.checkbox('Do cost to avoid eviction analysis?'):
                    evictions_cost_df = cost_of_evictions(df, metro_areas, locations)
                    st.markdown(
                        utils.get_table_download_link(evictions_cost_df, state + '_custom_cost_data',
                                                      'Download cost data'),
                        unsafe_allow_html=True)
                ranks = relative_risk_ranking(df, state)
                eviction_visualizations(ranks, state)
            else:
                st.error('Select counties to analyze')
                st.stop()
        elif task == 'State':
            state = st.selectbox("Select a state", STATES).strip()
            df = get_state_data(state)

            if st.checkbox('Show raw data'):
                st.subheader('Raw Data')
                st.dataframe(df)
                st.markdown(utils.get_table_download_link(df, state + '_data', 'Download raw data'),
                            unsafe_allow_html=True)
            with st.beta_expander('Cost to avoid evictions'):
                st.write("""
                The cost to avoid evictions is defined as the cost to a municipality or other entity if it was to pay 
                people's rent directly. In this calculation, we assume a distribution of housing stock (0 bedroom to 4+ bedroom)
                 based on Census data. You can select which distribution to use that is most similar to the community that you're analyzing. 

                 We default to using Fair Market Rents for this calculation, but you can use the Median value as well. 

                 We also assume that only the burdened population is being considered for support, but not every burdened 
                 person will receive support. You can adjust the percentage of the burdened population to consider.

                 The reported value is the *monthly cost* to an entity to support the chosen housing distribution, rent type, and percent of the burdened population. 

                 This is only an estimate, and should not be used for detailed planning or policy making.
                """)

            if st.checkbox('Do cost to avoid eviction analysis?'):
                evictions_cost_df = cost_of_evictions(df, metro_areas, locations)
                st.markdown(
                    utils.get_table_download_link(evictions_cost_df, state + '_cost_data', 'Download cost data'),
                    unsafe_allow_html=True)

            ranks = relative_risk_ranking(df, state)
            eviction_visualizations(ranks, state)

        elif task == 'National':
            st.info('Analysis for every county in the US can take a while! Please wait...')
            with st.beta_expander("Caveats"):
                st.write(
                    "There are some counties that don't show up in this analysis because of how they are named or because data is missing. We are aware of this issue.")

            frames = []
            for state in STATES:
                df = get_state_data(state)
                frames.append(df)
            natl_df = pd.concat(frames)
            if st.checkbox('Show raw data'):
                st.subheader('Raw Data')
                st.dataframe(natl_df)
                st.markdown(utils.get_table_download_link(natl_df, 'national_data', 'Download raw data'),
                            unsafe_allow_html=True)
            with st.beta_expander('Cost to avoid evictions'):
                st.write("""
                The cost to avoid evictions is defined as the cost to a municipality or other entity if it was to pay 
                people's rent directly. In this calculation, we assume a distribution of housing stock (0 bedroom to 4+ bedroom)
                 based on Census data. You can select which distribution to use that is most similar to the community that you're analyzing. 
                 
                 We default to using Fair Market Rents for this calculation, but you can use the Median value as well. 
                 
                 We also assume that only the burdened population is being considered for support, but not every burdened 
                 person will receive support. You can adjust the percentage of the burdened population to consider.
                 
                 The reported value is the *monthly cost* to an entity to support the chosen housing distribution, rent type, and percent of the burdened population. 
                 
                 This is only an estimate, and should not be used for detailed planning or policy making.
                """)

            if st.checkbox('Do cost to avoid eviction analysis?'):
                evictions_cost_df = cost_of_evictions(natl_df, metro_areas, locations)
                st.markdown(utils.get_table_download_link(evictions_cost_df, 'national_cost', 'Download cost data'),
                            unsafe_allow_html=True)
            ranks = relative_risk_ranking(natl_df, 'National')
            eviction_visualizations(ranks, 'National')
    else:
        if data_type == 'County Level':
            st.write('## County Data Explorer')
            st.write('This interface allows you to see and interact with county data in our database. ')
            task = st.selectbox('How much data do you want to look at?',
                                ['Single County', 'Multiple Counties', 'State', 'National'], 2)
            if task == 'Single County' or task == '':
                res = st.text_input('Enter the county and state (ie: Jefferson County, Colorado):')
                if res:
                    res = res.strip().split(',')
                    county = res[0].strip()
                    state = res[1].strip()
                    if county and state:
                        df = get_single_county(county, state)
                        if st.checkbox('Show raw data'):
                            st.subheader('Raw Data')
                            st.dataframe(df)
                            st.markdown(
                                utils.get_table_download_link(df, county + '_data', 'Download raw data'),
                                unsafe_allow_html=True)
                        data_explorer(df, state)

            elif task == 'Multiple Counties':
                state = st.selectbox("Select a state", STATES).strip()
                county_list = queries.counties_query()
                county_list = county_list[county_list['State'] == state]['County Name'].to_list()
                counties = st.multiselect('Please specify one or more counties', county_list)
                counties = [_.strip().lower() for _ in counties]
                if len(counties) > 0:
                    df = get_multiple_counties(counties, state)

                    if st.checkbox('Show raw data'):
                        st.subheader('Raw Data')
                        st.dataframe(df)
                        st.markdown(utils.get_table_download_link(df, state + '_custom_data', 'Download raw data'),
                                    unsafe_allow_html=True)
                    data_explorer(df, state)
                else:
                    st.error('Select counties to analyze')
                    st.stop()

            elif task == 'State':
                state = st.selectbox("Select a state", STATES).strip()
                df = get_state_data(state)

                if st.checkbox('Show raw data'):
                    st.subheader('Raw Data')
                    st.dataframe(df)
                    st.markdown(utils.get_table_download_link(df, state + '_data', 'Download raw data'),
                                unsafe_allow_html=True)

                data_explorer(df, state)

            elif task == 'National':
                st.info('National analysis can take some time and be difficult to visualize at the moment.')
                frames = []
                for state in STATES:
                    df = get_state_data(state)
                    frames.append(df)
                natl_df = pd.concat(frames)
                if st.checkbox('Show raw data'):
                    st.subheader('Raw Data')
                    st.dataframe(natl_df)
                    st.markdown(utils.get_table_download_link(natl_df, 'national_data', 'Download raw data'),
                                unsafe_allow_html=True)
                data_explorer(natl_df, 'national')

        else:
            st.write('## Census Tract Data Explorer')
            st.write('This interface allows you to see and interact with census tract data in our database. ')
            state = st.selectbox("Select a state", STATES).strip()
            county_list = queries.counties_query()
            county_list = county_list[county_list['State'] == state]['County Name'].to_list()
            counties = st.selectbox('Please a county', county_list)
            table_list = queries.table_names_query()
            tables = st.multiselect('Please specify one or more datasets to view', table_list)
            tables = [_.strip().lower() for _ in tables]
            if tables:
                df = queries.latest_data_census_tracts(state, counties, tables[0])
                if st.checkbox('Show raw data'):
                    st.subheader('Raw Data')
                    st.dataframe(df)
                    st.markdown(utils.get_table_download_link(df, state + '_data', 'Download raw data'),
                                unsafe_allow_html=True)
                df['State'] = df['state_name']
                df['County Name'] = df['county_name']
                df.set_index(['State', 'County Name'], drop=True, inplace=True)
                census_data_explorer(df, counties, state, tables)


if __name__ == '__main__':
    if not os.path.exists('Output'):
        os.makedirs('Output')
    opts, args = getopt.getopt(sys.argv[1:], "hm:", ["mode="])
    mode = None

    for opt, arg in opts:
        if opt == '-h':
            print('run.py -mode <mode>')
            sys.exit()
        elif opt in ("-m", "--mode"):
            mode = arg
            print(mode)

    if mode == 'script':
        MODE = 'SCRIPT'
        task = input(
            'Analyze a single county (1), multiple counties (2), all the counties in a state (3), or a nation-wide analysis (4)? [default: 1]') \
            .strip()
        if task == '1' or task == '':
            res = input('Enter the county and state to analyze (ie: Jefferson County, Colorado):')
            res = res.strip().split(',')
            cost_of_evictions = input(
                'Run an analysis to estimate the cost to avoid evictions? (Y/n) ')
            cost_of_evictions.strip()
            county = res[0].strip().lower()
            state = res[1].strip().lower()
            df = get_single_county(county, state)

            if cost_of_evictions == 'y' or cost_of_evictions == '':
                df = analysis.calculate_cost_estimate(df, rent_type='fmr')

            utils.output_table(df, 'Output/' + county.capitalize() + '.xlsx')
            print_summary(df, 'Output/' + county.capitalize() + '.xlsx')
        elif task == '2':
            state = input("Which state are you looking for? (ie: California)").strip()
            counties = input('Please specify one or more counties, separated by commas.').strip().split(',')
            counties = [_.strip().lower() for _ in counties]
            counties = [_ + ' county' for _ in counties if ' county' not in _]
            df = get_multiple_counties(counties, state)
            cost_of_evictions = input(
                'Run an analysis to estimate the cost to avoid evictions? (Y/n) ')
            if cost_of_evictions == 'y' or cost_of_evictions == '':
                df = analysis.calculate_cost_estimate(df, rent_type='fmr')

            utils.output_table(df, 'Output/' + state + '_selected_counties.xlsx')
            analysis_df = analysis.rank_counties(df, state + '_selected_counties')
            print_summary(analysis_df, 'Output/' + state + '_selected_counties.xlsx')
        elif task == '3':
            state = input("Which state are you looking for? (ie: California)").strip()
            df = get_state_data(state)
            cost_of_evictions = input(
                'Run an analysis to estimate the cost to avoid evictions? (Y/n) ')
            if cost_of_evictions == 'y' or cost_of_evictions == '':
                df = analysis.calculate_cost_estimate(df, rent_type='fmr')

            utils.output_table(df, 'Output/' + state + '.xlsx')
            analysis_df = analysis.rank_counties(df, state)
            print_summary(analysis_df, 'Output/' + state + '.xlsx')
            temp = df.copy()
            temp.reset_index(inplace=True)
            counties = temp['County Name'].to_list()
            geom = queries.get_county_geoms(counties, state.lower())
            df = df.merge(geom, on='County Name', how='outer')

        elif task == '4':
            frames = []
            for state in STATES:
                df = get_state_data(state)
                frames.append(df)
            natl_df = pd.concat(frames)
            cost_of_evictions = input(
                'Run an analysis to estimate the cost to avoid evictions (Y/n) ')
            if cost_of_evictions == 'y' or cost_of_evictions == '':
                df = analysis.calculate_cost_estimate(natl_df, rent_type='fmr')

            utils.output_table(natl_df, 'Output/US_national.xlsx')
            analysis_df = analysis.rank_counties(natl_df, 'US_national')
            print_summary(analysis_df, 'Output/US_national.xlsx')
        else:
            raise Exception('INVALID INPUT! Enter a valid task number.')
    else:
        run_UI()
