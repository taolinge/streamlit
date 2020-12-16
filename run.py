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


def make_correlation_plot(df: pd.DataFrame):
    st.subheader('Correlation Plot')
    fig, ax = plt.subplots(figsize=(10, 10))
    st.write(sns.heatmap(df.corr(), annot=True, linewidths=0.5))
    st.pyplot(fig)


def visualizations(df: pd.DataFrame, state: str = None):
    if state:
        temp = df.copy()
        temp.reset_index(inplace=True)
        counties = temp['County Name'].to_list()
        if state != 'national':
            geo_df = queries.get_county_geoms(counties, state.lower())
            visualization.make_map(geo_df, df, 'Relative Risk')

    make_correlation_plot(df)


def data_explorer(df: pd.DataFrame, state: str):

    feature_labels = list(set(df.columns) - {'County Name', 'county_id', 'Resident Population (Thousands of Persons)'})
    feature_labels.sort()
    st.write('''
            ### View Feature
            Select a feature to view for each county
            ''')
    single_feature = st.selectbox('Feature', feature_labels, 0)
    bar_df = pd.DataFrame(df.reset_index()[[single_feature, 'County Name']])
    # bar_df.set_index('County Name', inplace=True)
    bar = alt.Chart(bar_df).mark_bar() \
        .encode(x='County Name', y=single_feature + ':Q',
                tooltip=['County Name',  single_feature])
    st.altair_chart(bar, use_container_width=True)

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
        scatter_df = df.reset_index()[[feature_1, feature_2, 'County Name', 'Resident Population (Thousands of Persons)']]
        scatter = alt.Chart(scatter_df).mark_point()\
            .encode(x=feature_1+':Q', y=feature_2+':Q',
                    tooltip=['County Name', 'Resident Population (Thousands of Persons)', feature_1, feature_2],
                    size='Resident Population (Thousands of Persons)')
        st.altair_chart(scatter, use_container_width=True)

    st.write('### Correlation Plot')
    make_correlation_plot(df)


def cost_of_evictions(df, metro_areas, locations):
    rent_type = st.selectbox('Rent Type', ['Fair Market', 'Median'])
    location = st.selectbox('Select a location to assume a housing distribution:', locations)
    distribution = {
        0: float(metro_areas.loc[location, '0_br_pct']),
        1: float(metro_areas.loc[location, '1_br_pct']),
        2: float(metro_areas.loc[location, '2_br_pct']),
        3: float(metro_areas.loc[location, '3_br_pct']),
        4: float(metro_areas.loc[location, '4_br_pct']),
    }

    pct_burdened = st.slider('Percent of Burdened Population to Support', 0, 100, value=50, step=1)

    if rent_type == '' or rent_type == 'Fair Market':
        df = analysis.calculate_cost_estimate(df, pct_burdened, rent_type='fmr', distribution=distribution)
    elif rent_type == 'Median':
        df = analysis.calculate_cost_estimate(df, pct_burdened, rent_type='rent50', distribution=distribution)

    cost_df = df.reset_index()
    cost_df.drop(columns=['State'], inplace=True)
    cost_df.set_index('County Name', inplace=True)
    # cost_df = cost_df[['br_cost_0', 'br_cost_1', 'br_cost_2', 'br_cost_3', 'br_cost_4', 'total_cost']]
    # st.dataframe(
    #     cost_df[['total_cost']])
    st.bar_chart(cost_df['total_cost'])
    return cost_df


def run_UI():
    st.set_page_config(
        page_title="Arup Social Data",
        page_icon="🏠",
        initial_sidebar_state="expanded")
    st.sidebar.write('# Arup Social Data')
    workflow = st.sidebar.selectbox('Workflow', ['Eviction Analysis', 'Data Explorer'])
    st.sidebar.write("""
    This tool supports analysis of United States county level data from a variety of data sources. There are two workflows: an Eviction
     Analysis workflow, which is specifically focused on evictions as a result of COVID-19, and a Data Explorer workflow,
     which allows you to see and interact with the data we have without doing any analysis.
     
     You can also use our Python code in a scripting environment or query our database directly. Details are at our 
     [GitHub](https://github.com/arup-group/social-data). If you find that this interface doesn't do what you need it to,
      you can create an issue at our GitHub repository or better yet, contribute a pull request. You can reach out to 
      the team on LinkedIn or Twitter if you have questions or feedback.
 
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
        and helped support this work. 
        
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
                        if st.checkbox('Show cost data'):
                            st.dataframe(evictions_cost_df)
                        st.markdown(
                            utils.get_table_download_link(evictions_cost_df, county + '_cost_data',
                                                          'Download cost data'),
                            unsafe_allow_html=True)

                else:
                    st.warning('Enter a valid county and state, separated by a comma')
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
                    if st.checkbox('Show cost data'):
                        st.dataframe(evictions_cost_df)
                    st.markdown(
                        utils.get_table_download_link(evictions_cost_df, state + '_custom_cost_data',
                                                      'Download cost data'),
                        unsafe_allow_html=True)
                ranks = analysis.rank_counties(df, state + '_selected_counties').sort_values(by='Relative Risk',
                                                                                             ascending=False)
                st.write('## Results')
                st.dataframe(ranks)
                st.write(f'Features considered {list(ranks.columns)}')
                st.markdown(
                    utils.get_table_download_link(ranks, state + '_custom_ranking', 'Download Relative Risk ranking'),
                    unsafe_allow_html=True)

                visualizations(ranks, state)
            else:
                st.warning('Select counties to analyze')
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
                if st.checkbox('Show cost data'):
                    st.dataframe(evictions_cost_df)
                st.markdown(
                    utils.get_table_download_link(evictions_cost_df, state + '_cost_data', 'Download cost data'),
                    unsafe_allow_html=True)

            ranks = analysis.rank_counties(df, state).sort_values(by='Relative Risk', ascending=False)
            st.subheader('Ranking')
            st.write('Higher values correspond to more relative risk')
            st.write(ranks['Relative Risk'])
            st.write(f'Features considered {list(ranks.columns)}')
            st.markdown(utils.get_table_download_link(ranks, state + '_ranking', 'Download Relative Risk ranking'),
                        unsafe_allow_html=True)

            visualizations(ranks, state)

        elif task == 'National':
            st.write('Analysis every county in the US can take a while! Please wait...')
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

            ranks = analysis.rank_counties(natl_df, 'US_national').sort_values(by='Relative Risk', ascending=False)
            st.subheader('Ranking')
            st.write('Higher values correspond to more relative risk')
            st.write(ranks['Relative Risk'])
            st.write(f'Features considered {list(ranks.columns)}')
            st.markdown(utils.get_table_download_link(natl_df, 'national_ranking', 'Download Relative Risk ranking'),
                        unsafe_allow_html=True)

            # visualizations(natl_df, 'National')
    else:
        st.write('## Data Explorer')
        st.write('This interface allows you to see and interact with data in our database. ')
        task = st.selectbox('What type of analysis are you doing?',
                            ['Single County', 'Multiple Counties', 'State', 'National'])
        metro_areas, locations = load_distributions()
        if task == 'Single County' or task == '':
            res = st.text_input('Enter the county and state (ie: Jefferson County, Colorado):')
            if res:
                res = res.strip().split(',')
                county = res[0].strip()
                state = res[1].strip()
                if county and state:
                    df = get_single_county(county, state)
                    st.write(df)
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
                st.warning('Select counties to analyze')
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
