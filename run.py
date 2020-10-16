import getopt
import itertools
import math
import os
import sys

import pandas as pd
import sklearn.preprocessing as pre
import streamlit as st
import seaborn as sns
import matplotlib.pyplot as plt

import api
import queries
from constants import STATES

# Pandas options
pd.set_option('max_rows', 25)
pd.set_option('max_columns', 12)
pd.set_option('expand_frame_repr', True)
pd.set_option('large_repr', 'truncate')
pd.options.display.float_format = '{:.2f}'.format

HOUSING_STOCK_DISTRIBUTION = {
    # Assumed National housing distribution [https://www.census.gov/programs-surveys/ahs/data/interactive/ahstablecreator.html?s_areas=00000&s_year=2017&s_tablename=TABLE2&s_bygroup1=1&s_bygroup2=1&s_filtergroup1=1&s_filtergroup2=1]
    0: 0.0079,
    1: 0.1083,
    2: 0.2466,
    3: 0.4083,
    4: 0.2289
}

BURDENED_HOUSEHOLD_PROPORTION = [5, 25, 33, 50, 75]
MODE = 'UI'


def filter_state(data: pd.DataFrame, state: str) -> pd.DataFrame:
    return data[data['State'].str.lower() == state.lower()]


def filter_counties(data: pd.DataFrame, counties: list) -> pd.DataFrame:
    counties = [_.lower() for _ in counties]
    return data[data['County Name'].str.lower().isin(counties)]


def clean_data(data: pd.DataFrame) -> pd.DataFrame:
    data.set_index(['State', 'County Name'], drop=True, inplace=True)
    data['Non-Home Ownership (%)'] = 100 - pd.to_numeric(data['Home Ownership (%)'], downcast='float')

    data.drop([
        'Home Ownership (%)',
        'Burdened Households Date',
        'Home Ownership Date',
        'Income Inequality Date',
        'Population Below Poverty Line Date',
        'Single Parent Households Date',
        'SNAP Benefits Recipients Date',
        'Unemployment Rate Date',
        'Resident Population Date'
    ], axis=1, inplace=True)
    data = data.loc[:, ~data.columns.str.contains('^Unnamed')]

    return data


def percent_to_population(feature: str, name: str, df: pd.DataFrame) -> pd.DataFrame:
    df[name] = (df[feature].astype(float) / 100) * df['Resident Population (Thousands of Persons)'].astype(float) * 1000
    return df


def cross_features(df: pd.DataFrame) -> pd.DataFrame:
    cols = ['Pop Below Poverty Level', 'Pop Unemployed', 'Income Inequality (Ratio)', 'Non-Home Ownership Pop',
            'Num Burdened Households', 'Num Single Parent Households']
    all_combinations = []
    for r in range(2, 3):
        combinations_list = list(itertools.combinations(cols, r))
        all_combinations += combinations_list
    new_cols = []
    for combo in all_combinations:
        new_cols.append(cross(combo, df))

    crossed_df = pd.DataFrame(new_cols)
    crossed_df = crossed_df.T
    crossed_df['Mean'] = crossed_df.mean(axis=1)

    return crossed_df


def normalize(df: pd.DataFrame) -> pd.DataFrame:
    df = percent_to_population('Population Below Poverty Line (%)', 'Pop Below Poverty Level', df)
    df = percent_to_population('Unemployment Rate (%)', 'Pop Unemployed', df)
    df = percent_to_population('Burdened Households (%)', 'Num Burdened Households', df)
    df = percent_to_population('Single Parent Households (%)', 'Num Single Parent Households', df)
    df = percent_to_population('Non-Home Ownership (%)', 'Non-Home Ownership Pop', df)

    if 'Policy Value' in list(df.columns) or 'Countdown' in list(df.columns):
        df = df.drop(['Policy Value', 'Countdown'], axis=1)

    df = df.drop(['Population Below Poverty Line (%)',
                  'Unemployment Rate (%)',
                  'Burdened Households (%)',
                  'Single Parent Households (%)',
                  'Non-Home Ownership (%)',
                  'Resident Population (Thousands of Persons)',
                  ], axis=1)

    scaler = pre.MaxAbsScaler()
    df_scaled = pd.DataFrame(scaler.fit_transform(df), index=df.index, columns=df.columns)

    return df_scaled


def normalize_column(df: pd.DataFrame, col: str) -> pd.DataFrame:
    scaler = pre.MaxAbsScaler()
    df[col] = scaler.fit_transform(df[col].values.reshape(-1, 1))

    return df


def normalize_percent(percent: float) -> float:
    return percent / 100


def cross(columns: tuple, df: pd.DataFrame) -> pd.Series:
    columns = list(columns)
    new_col = '_X_'.join(columns)
    new_series = pd.Series(df[columns].product(axis=1), name=new_col).abs()
    return new_series


def priority_indicator(socioeconomic_index: float, policy_index: float, time_left: int = 1) -> float:
    if time_left < 1:
        # Handle 0 values
        time_left = 1

    return float(socioeconomic_index) * (1 - float(policy_index)) / math.sqrt(time_left)


def rank_counties(df: pd.DataFrame, label: str) -> pd.DataFrame:
    df.drop(['county_id'], axis=1, inplace=True)
    analysis_df = normalize(df)

    crossed = cross_features(analysis_df)
    analysis_df['Crossed'] = crossed['Mean']
    analysis_df = normalize_column(analysis_df, 'Crossed')

    analysis_df['Relative Risk'] = analysis_df.sum(axis=1)
    max_sum = analysis_df['Relative Risk'].max()
    analysis_df['Relative Risk'] = (analysis_df['Relative Risk'] / max_sum)

    if 'Policy Value' in list(df.columns):
        analysis_df['Policy Value'] = df['Policy Value']
        analysis_df['Countdown'] = df['Countdown']
        analysis_df['Rank'] = analysis_df.apply(
            lambda x: priority_indicator(x['Relative Risk'], x['Policy Value'], x['Countdown']), axis=1
        )

    analysis_df.to_excel('Output/' + label + '_overall_vulnerability.xlsx')

    return analysis_df


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
        else:
            print(
                "INFO: Policy data not found. Check that you've properly filled in the Analysis Data page in `Policy Workbook.xlsx` with the counties you're analyzing.")

    return df


def get_single_county(county: str, state: str) -> pd.DataFrame:
    df = load_all_data()
    df = filter_state(df, state)
    df = filter_counties(df, [county])
    df = get_existing_policies(df)
    df = clean_data(df)

    return df


def get_multiple_counties(counties: list, state: str) -> pd.DataFrame:
    df = load_all_data()
    df = filter_state(df, state)
    df = filter_counties(df, counties)
    df = get_existing_policies(df)
    df = clean_data(df)

    return df


def get_state_data(state: str) -> pd.DataFrame:
    df = load_all_data()
    df = filter_state(df, state)
    df = get_existing_policies(df)
    df = clean_data(df)

    return df


def output_table(df: pd.DataFrame, path: str):
    df = df.loc[:, ~df.columns.str.contains('^Unnamed')]
    df.to_excel(path)


def calculate_cost_estimate(df: pd.DataFrame, distribution: dict, rent_type: str = 'fmr') -> pd.DataFrame:
    if rent_type == 'fmr':
        cost_df = queries.static_data_single_table('fair_market_rents', queries.static_columns['fair_market_rents'])
    elif rent_type == 'med':
        cost_df = queries.static_data_single_table('median_rents', queries.static_columns['median_rents'])
    else:
        raise Exception(
            'Invalid input - {x} is not a valid rent type. Must be either `fmr` (Free Market Rent) or `med` (Median Rent)'.format(
                x=rent_type))

    cost_df = cost_df.drop([
        'State',
        'County Name'
    ], axis=1)

    df = df.reset_index().merge(cost_df, how="left", on='county_id').set_index(['State', 'County Name'])
    df = df.astype(float)
    for key, value in distribution.items():
        for pro in BURDENED_HOUSEHOLD_PROPORTION:
            df[str(key) + '_br_cost_' + str(pro)] = value * df['fmr_0'] * (pro / 100) * (
                    df['Resident Population (Thousands of Persons)'] * 1000) * (df['Burdened Households (%)'] / 100)
            df[str(key) + '_br_cost_' + str(pro)] = value * df['fmr_1'] * (pro / 100) * (
                    df['Resident Population (Thousands of Persons)'] * 1000) * (df['Burdened Households (%)'] / 100)
            df[str(key) + '_br_cost_' + str(pro)] = value * df['fmr_2'] * (pro / 100) * (
                    df['Resident Population (Thousands of Persons)'] * 1000) * (df['Burdened Households (%)'] / 100)
            df[str(key) + '_br_cost_' + str(pro)] = value * df['fmr_3'] * (pro / 100) * (
                    df['Resident Population (Thousands of Persons)'] * 1000) * (df['Burdened Households (%)'] / 100)
            df[str(key) + '_br_cost_' + str(pro)] = value * df['fmr_4'] * (pro / 100) * (
                    df['Resident Population (Thousands of Persons)'] * 1000) * (df['Burdened Households (%)'] / 100)
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


@st.cache
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


def run_UI():
    st.write("""
    # Eviction Data Analysis

    This tool supports analysis of county level data from a variety of data sources.

    More documentation and contribution details are at our [GitHub Repository](https://github.com/arup-group/eviction-data)
    """)
    st.write('# Eviction Data Analysis')
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

                if st.checkbox('Do cost to avoid eviction analysis?'):
                    rent_type = st.selectbox('Rent Type', ['Fair Market', 'Median'])
                    location = st.selectbox('Select a location to assume a housing distribution:', locations)
                    distribution = {
                        0: float(metro_areas.loc[location, '0_br_pct']),
                        1: float(metro_areas.loc[location, '1_br_pct']),
                        2: float(metro_areas.loc[location, '2_br_pct']),
                        3: float(metro_areas.loc[location, '3_br_pct']),
                        4: float(metro_areas.loc[location, '4_br_pct']),
                    }

                    if rent_type == '' or rent_type == 'Fair Market':
                        df = calculate_cost_estimate(df, rent_type='fmr', distribution=distribution)
                    elif rent_type == 'Median':
                        df = calculate_cost_estimate(df, rent_type='med', distribution=distribution)

                output_table(df, 'Output/' + county + '.xlsx')
                st.write('Data was saved at `' + 'Output/' + county + '.xlsx')
                st.write('## Results')
                st.dataframe(df)
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

            if st.checkbox('Do cost to avoid eviction analysis?'):
                rent_type = st.selectbox('Rent Type', ['Fair Market', 'Median'])
                location = st.selectbox('Select a location to assume a housing distribution:', locations)
                distribution = {
                    0: float(metro_areas.loc[location, '0_br_pct']),
                    1: float(metro_areas.loc[location, '1_br_pct']),
                    2: float(metro_areas.loc[location, '2_br_pct']),
                    3: float(metro_areas.loc[location, '3_br_pct']),
                    4: float(metro_areas.loc[location, '4_br_pct']),
                }

                if rent_type == '' or rent_type == 'Fair Market':
                    df = calculate_cost_estimate(df, rent_type='fmr', distribution=distribution)
                elif rent_type == 'Median':
                    df = calculate_cost_estimate(df, rent_type='med', distribution=distribution)
            output_table(df, 'Output/' + state + '_selected_counties.xlsx')
            st.write('Data was saved at `' + 'Output/' + state + '_selected_counties.xlsx')
            ranks = rank_counties(df, state + '_selected_counties').sort_values(by='Relative Risk', ascending=False)
            st.write('## Results')
            st.dataframe(ranks)
    elif task == 'State':
        state = st.selectbox("Select a state", STATES).strip()
        df = get_state_data(state)
        if st.checkbox('Show raw data'):
            st.subheader('Raw Data')
            st.dataframe(df)
        if st.checkbox('Do cost to avoid eviction analysis?'):
            rent_type = st.selectbox('Rent Type', ['Fair Market', 'Median'])
            location = st.selectbox('Select a location to assume a housing distribution:', locations)
            distribution = {
                0: float(metro_areas.loc[location, '0_br_pct']),
                1: float(metro_areas.loc[location, '1_br_pct']),
                2: float(metro_areas.loc[location, '2_br_pct']),
                3: float(metro_areas.loc[location, '3_br_pct']),
                4: float(metro_areas.loc[location, '4_br_pct']),
            }

            if rent_type == '' or rent_type == 'Fair Market':
                df = calculate_cost_estimate(df, rent_type='fmr', distribution=distribution)
            elif rent_type == 'Median':
                df = calculate_cost_estimate(df, rent_type='med', distribution=distribution)

        output_table(df, 'Output/' + state + '.xlsx')
        st.write('Data was saved at `' + 'Output/' + state + '.xlsx')
        ranks = rank_counties(df, state).sort_values(by='Relative Risk', ascending=False)
        st.subheader('Ranking')
        st.write('Higher values correspond to more relative risk')
        st.write(ranks['Relative Risk'])
        st.write('## Charts')
        features = st.multiselect('Features', list(df.columns))
        chart_data = df.reset_index(level='State')[features]
        st.write(chart_data)
        st.bar_chart(chart_data)

        st.subheader('Correlation Plot')
        fig, ax = plt.subplots(figsize=(10, 10))
        st.write(sns.heatmap(df.corr(), annot=True, linewidths=0.5))
        st.pyplot(fig)
    elif task == 'National':
        frames = []
        for state in STATES:
            df = get_state_data(state)
            frames.append(df)
        natl_df = pd.concat(frames)
        output_table(natl_df, 'Output/US_national.xlsx')
        st.write('Data was saved at `' + 'Output/US_national.xlsx')
        if st.checkbox('Show raw data'):
            st.subheader('Raw Data')
            st.dataframe(natl_df)
        if st.checkbox('Do cost to avoid eviction analysis?'):
            rent_type = st.selectbox('Rent Type', ['Fair Market', 'Median'])
            location = st.selectbox('Select a location to assume a housing distribution:', locations)
            distribution = {
                0: float(metro_areas.loc[location, '0_br_pct']),
                1: float(metro_areas.loc[location, '1_br_pct']),
                2: float(metro_areas.loc[location, '2_br_pct']),
                3: float(metro_areas.loc[location, '3_br_pct']),
                4: float(metro_areas.loc[location, '4_br_pct']),
            }

            if rent_type == '' or rent_type == 'Fair Market':
                natl_df = calculate_cost_estimate(natl_df, rent_type='fmr', distribution=distribution)
            elif rent_type == 'Median':
                natl_df = calculate_cost_estimate(natl_df, rent_type='med', distribution=distribution)

        ranks = rank_counties(natl_df, 'US_national').sort_values(by='Relative Risk', ascending=False)
        st.subheader('Ranking')
        st.write('Higher values correspond to more relative risk')
        st.write(ranks['Relative Risk'])
        st.write('## Charts')
        features = st.multiselect('Features', list(natl_df.columns))
        chart_data = natl_df.reset_index(level='State')[features]
        st.write(chart_data)
        st.bar_chart(chart_data)

        st.subheader('Correlation Plot')
        fig, ax = plt.subplots(figsize=(10, 10))
        st.write(sns.heatmap(natl_df.corr(), annot=True, linewidths=0.5))
        st.pyplot(fig)


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
                df = calculate_cost_estimate(df, rent_type='fmr')

            output_table(df, 'Output/' + county.capitalize() + '.xlsx')
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
                df = calculate_cost_estimate(df, rent_type='fmr')

            output_table(df, 'Output/' + state + '_selected_counties.xlsx')
            analysis_df = rank_counties(df, state + '_selected_counties')
            print_summary(analysis_df, 'Output/' + state + '_selected_counties.xlsx')
        elif task == '3':
            state = input("Which state are you looking for? (ie: California)").strip()
            df = get_state_data(state)
            cost_of_evictions = input(
                'Run an analysis to estimate the cost to avoid evictions? (Y/n) ')
            if cost_of_evictions == 'y' or cost_of_evictions == '':
                df = calculate_cost_estimate(df, rent_type='fmr')

            output_table(df, 'Output/' + state + '.xlsx')
            analysis_df = rank_counties(df, state)
            print_summary(analysis_df, 'Output/' + state + '.xlsx')
        elif task == '4':
            frames = []
            for state in STATES:
                df = get_state_data(state)
                frames.append(df)
            natl_df = pd.concat(frames)
            cost_of_evictions = input(
                'Run an analysis to estimate the cost to avoid evictions (Y/n) ')
            if cost_of_evictions == 'y' or cost_of_evictions == '':
                df = calculate_cost_estimate(natl_df, rent_type='fmr')

            output_table(natl_df, 'Output/US_national.xlsx')
            analysis_df = rank_counties(natl_df, 'US_national')
            print_summary(analysis_df, 'Output/US_national.xlsx')
        else:
            raise Exception('INVALID INPUT! Enter a valid task number.')
    else:
        run_UI()
