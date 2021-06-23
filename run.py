import os
import pandas as pd
import streamlit as st

import data_explorer
import eviction_analysis
import queries
import analysis
import utils
from constants import STATES

# Pandas options
pd.set_option('max_rows', 25)
pd.set_option('max_columns', 12)
pd.set_option('expand_frame_repr', True)
pd.set_option('large_repr', 'truncate')
pd.options.display.float_format = '{:.2f}'.format


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


def run_shell() -> pd.DataFrame:
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
        df = queries.get_county_data(state, [county])

        if cost_of_evictions == 'y' or cost_of_evictions == '':
            df = analysis.calculate_cost_estimate(df, rent_type='fmr')

        utils.output_table(df, 'Output/' + county.capitalize() + '.xlsx')
        print_summary(df, 'Output/' + county.capitalize() + '.xlsx')
        return df
    elif task == '2':
        state = input("Which state are you looking for? (ie: California)").strip()
        counties = input('Please specify one or more counties, separated by commas.').strip().split(',')
        counties = [_.strip().lower() for _ in counties]
        counties = [_ + ' county' for _ in counties if ' county' not in _]
        df = queries.get_county_data(state,counties)
        cost_of_evictions = input(
            'Run an analysis to estimate the cost to avoid evictions? (Y/n) ')
        if cost_of_evictions == 'y' or cost_of_evictions == '':
            df = analysis.calculate_cost_estimate(df, rent_type='fmr')

        utils.output_table(df, 'Output/' + state + '_selected_counties.xlsx')
        analysis_df = analysis.rank_counties(df, state + '_selected_counties')
        print_summary(analysis_df, 'Output/' + state + '_selected_counties.xlsx')
        return df
    elif task == '3':
        state = input("Which state are you looking for? (ie: California)").strip()
        df = queries.get_county_data(state)
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
        return df
    elif task == '4':
        frames = []
        for state in STATES:
            df = queries.get_county_data(state)
            frames.append(df)
        natl_df = pd.concat(frames)
        cost_of_evictions = input(
            'Run an analysis to estimate the cost to avoid evictions (Y/n) ')
        if cost_of_evictions == 'y' or cost_of_evictions == '':
            df = analysis.calculate_cost_estimate(natl_df, rent_type='fmr')

        utils.output_table(natl_df, 'Output/US_national.xlsx')
        analysis_df = analysis.rank_counties(natl_df, 'US_national')
        print_summary(analysis_df, 'Output/US_national.xlsx')
        return df
    else:
        raise Exception('INVALID INPUT! Enter a valid task number.')


def run_UI():
    st.set_page_config(
        page_title="Arup Social Data",
        page_icon="🏠",
        initial_sidebar_state="expanded")
    st.sidebar.title('Arup Social Data')
    workflow = st.sidebar.selectbox('Workflow', ['Data Explorer', 'Eviction Analysis'])
    data_type=None
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
        - [Angela Wilson 🐦](https://twitter.com/AngelaWilson925) 
        - Sam Lustado
        - Lingyi Chen
        - Kevin McGee
        - [Jared Stock 🐦](https://twitter.com/jaredstock) 
        - Jen Combs
        - Zoe Temco


        Special thanks to Julieta Moradei and Kamini Ayer from New Story, Kristin Maun from the city of Tulsa, 
        Emily Walport and Irene Gleeson with Arup's Community Engagment team, and everyone else who has given feedback 
        and helped support this work. Also thanks to the team at Streamlit for their support of this work.

        The analysis and underlying data are provided as open source under an [MIT license](https://github.com/arup-group/social-data/blob/master/LICENSE). 

        Made by [Arup](https://www.arup.com/).
            """
    if workflow == 'Eviction Analysis':
        eviction_analysis.eviction_UI()
    else:
        if data_type == 'County Level':
            data_explorer.county_data_explorer()
        else:
            data_explorer.census_data_explorer()


if __name__ == '__main__':
    if not os.path.exists('Output'):
        os.makedirs('Output')
    if st._is_running_with_streamlit:
        run_UI()
    else:
        run_shell()
