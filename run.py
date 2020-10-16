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
pd.set_option('max_rows', 10)
pd.set_option('max_columns', 10)
pd.set_option('expand_frame_repr', True)
pd.set_option('large_repr', 'truncate')
pd.options.display.float_format = '{:.2f}'.format


def filter_state(data: pd.DataFrame, state: str) -> pd.DataFrame:
    return data[data['State'].str.lower() == state.lower()]


def filter_counties(data: pd.DataFrame, counties: list) -> pd.DataFrame:
    return data[data['County Name'].str.lower().isin(counties)]


def clean_fred_data(data: pd.DataFrame) -> pd.DataFrame:
    data['Non-Home Ownership (%)'] = 100 - data['Home Ownership (%)'].astype(float)

    data.drop([
        'Home Ownership (%)',
        'county_id',
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
    for r in range(2, len(cols)):
        combinations_list = list(itertools.combinations(cols, r))
        all_combinations += combinations_list
    all_combinations.pop(0)
    new_cols = []
    for combo in all_combinations:
        new_cols.append(cross(combo, df))

    crossed_df = pd.DataFrame(new_cols)
    crossed_df = crossed_df.T
    crossed_df['Mean'] = crossed_df.mean(axis=1)
    crossed_df.to_excel('Output/data_crossed.xlsx')

    return crossed_df


def normalize(df: pd.DataFrame) -> pd.DataFrame:
    df = percent_to_population('Population Below Poverty Line (%)', 'Pop Below Poverty Level', df)
    df = percent_to_population('Unemployment Rate (%)', 'Pop Unemployed', df)
    df = percent_to_population('Burdened Households (%)', 'Num Burdened Households', df)
    df = percent_to_population('Single Parent Households (%)', 'Num Single Parent Households', df)
    df = percent_to_population('Non-Home Ownership (%)', 'Non-Home Ownership Pop', df)

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


def priority_indicator(socioeconomic_index: float, policy_index: float, time_left: float = 1) -> float:
    return socioeconomic_index * (1 - policy_index) / math.sqrt(time_left)


def get_policy_data() -> pd.DataFrame:
    policy_df = api.get_from_csv('data/policy_index.csv')
    policy_df['Policy Index'] = policy_df['PolicyIndex'].copy()
    return policy_df


def rank_counties(df: pd.DataFrame, label: str) -> pd.DataFrame:
    analysis_df = normalize(df)
    # policy_df = get_policy_data()

    crossed = cross_features(analysis_df)
    analysis_df['Crossed'] = crossed['Mean']
    analysis_df = normalize_column(analysis_df, 'Crossed')

    analysis_df['Relative Risk'] = analysis_df.sum(axis=1)
    max_sum = analysis_df['Relative Risk'].max()
    analysis_df['Relative Risk'] = (analysis_df['Relative Risk'] / max_sum)
    # analysis_df['Policy Index'] = policy_df['PolicyIndex'].copy()
    # analysis_df['Countdown'] = policy_df['Countdown'].copy()
    # analysis_df['Rank'] = analysis_df.apply(
    #     lambda x: priority_indicator(x['Relative Risk'], x['PolicyIndex'],x['Countdown']), axis=1
    # )
    analysis_df.to_excel('Output/' + label + '_overall_vulnerability.xlsx')

    return analysis_df


def load_all_data() -> pd.DataFrame:
    if os.path.exists("Output/all_tables.xlsx"):
        try:
            print('Using local `all_tables.xlsx`')
            df = pd.read_excel('Output/all_tables.xlsx')
        except:
            print('Something went wrong with the Excel file. Falling back to database query.')
            df = queries.latest_data_all_tables()
    else:
        df = queries.latest_data_all_tables()

    return df


def get_single_county(county: str, state: str) -> pd.DataFrame:
    df = load_all_data()
    df = clean_fred_data(df)

    df = filter_state(df, state)
    df = filter_counties(df, [county])
    df.set_index(['County Name'], drop=True, inplace=True)
    return df


def get_multiple_counties(counties: list, state: str) -> pd.DataFrame:
    df = load_all_data()
    df = clean_fred_data(df)

    df = filter_state(df, state)
    df = filter_counties(df, counties)
    df.set_index(['State', 'County Name'], drop=True, inplace=True)

    return df


def get_state_data(state: str) -> pd.DataFrame:
    df = load_all_data()
    df = clean_fred_data(df)

    df = filter_state(df, state)
    df.set_index(['State', 'County Name'], drop=True, inplace=True)

    return df


def output_table(df: pd.DataFrame, path: str):
    df = df.loc[:, ~df.columns.str.contains('^Unnamed')]
    df.to_excel(path)


def init_UI():
    st.write("""
    # Eviction Data Analysis
    
    This tool supports data analysis of 
    
    To contribute to this tool or see more details, 
    
    """)
    st.write('# Eviction Data Analysis')
    task = st.selectbox('What type of analysis are you doing?',
                        ['Single County', 'Multiple Counties', 'State', 'National'])

    if task == 'Single County' or task == '':
        res = st.text_input('Enter the county and state (ie: Jefferson County, Colorado):')
        # res = input('Enter the county and state (ie: Jefferson County, Colorado):')
        if st.button("Submit"):
            res = res.strip().split(',')
            county = res[0].strip()
            state = res[1].strip()
            df = get_single_county(county, state)
            if st.checkbox('Show raw data'):
                st.dataframe(df)
            output_table(df, 'Output/' + county + '.xlsx')
            st.write('Data was saved at `' + 'Output/' + county + '.xlsx')
    elif task == 'Multiple Counties':
        state = st.selectbox("Select a state", STATES).strip()
        # state = input("Which state are you looking for (ie: California)?]").strip()
        counties = st.text_area('Please specify one or more counties, separated by commas [ie: ].').strip().split(',')
        if st.button("Submit"):
            # counties = input('Please specify one or more counties, separated by commas [ie: ].').strip().split(',')
            counties = [_.strip().lower() for _ in counties]
            counties = [_ + ' county' for _ in counties if ' county' not in _]
            df = get_multiple_counties(counties, state)
            if st.checkbox('Show raw data'):
                st.subheader('Raw Data')
                st.dataframe(df)
            output_table(df, 'Output/' + state + '_selected_counties.xlsx')
            st.write('Data was saved at `' + 'Output/' + state + '_selected_counties.xlsx')
            ranks = rank_counties(df, state + '_selected_counties').sort_values()
            st.dataframe(ranks)
    elif task == 'State':
        state = st.selectbox("Select a state", STATES).strip()
        # state = input("Which state are you looking for (ie: California)?]").strip()
        df = get_state_data(state)
        if st.checkbox('Show raw data'):
            st.subheader('Raw Data')
            st.dataframe(df)
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

    print(opts)
    mode = None
    for opt, arg in opts:
        if opt == '-h':
            print('run.py -mode <mode>')
            sys.exit()
        elif opt in ("-m", "--mode"):
            mode = arg
            print(mode)

    if mode == 'script':
        task = input(
            'Analyze a single county (1), multiple counties (2), all the counties in a state (3), or a nation-wide analysis (4)? [default: 1]') \
            .strip()

        if task == '1' or task == '':
            res = input('Enter the county and state to analyze (ie: Jefferson County, Colorado):')
            res = res.strip().split(',')
            cost_of_evictions = input(
                'Run an analysis to estimate the cost to avoid evictions for your chosen county? (Y/n) ')
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

            output_table(df, 'Output/' + state + '_selected_counties.xlsx')
            analysis_df = rank_counties(df, state + '_selected_counties')
            print_summary(analysis_df, 'Output/' + state + '_selected_counties.xlsx')
        elif task == '3':
            state = input("Which state are you looking for? (ie: California)").strip()
            df = get_state_data(state)

            output_table(df, 'Output/' + state + '.xlsx')
            analysis_df = rank_counties(df, state)
            print_summary(analysis_df, 'Output/' + state + '.xlsx')
        else:
            raise Exception('INVALID INPUT! Enter a valid task number.')

    else:
        init_UI()
