import math
import itertools
import pandas as pd
import numpy as np
import sklearn.preprocessing as pre
import streamlit as st

import queries


def clean_data(data: pd.DataFrame) -> pd.DataFrame:
    data.set_index(['State', 'County Name'], drop=True, inplace=True)

    data.drop([
        'Burdened Households Date',
        'Income Inequality Date',
        'Population Below Poverty Line Date',
        'Single Parent Households Date',
        'Unemployment Rate Date',
        'Resident Population Date',
    ], axis=1, inplace=True)

    data.rename({'Vulnerability Index': 'COVID Vulnerability Index'}, axis=1, inplace=True)

    data = data.loc[:, ~data.columns.str.contains('^Unnamed')]

    return data


def percent_to_population(feature: str, name: str, df: pd.DataFrame) -> pd.DataFrame:
    pd.set_option('mode.chained_assignment', None)
    df[name] = (df.loc[:, feature].astype(float) / 100) * df.loc[:, 'Resident Population (Thousands of Persons)'].astype(float) * 1000
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


def prepare_analysis_data(df: pd.DataFrame) -> pd.DataFrame:
    cols_to_drop = ['Population Below Poverty Line (%)',
                    'Unemployment Rate (%)',
                    'Burdened Households (%)',
                    'Single Parent Households (%)',
                    'Non-White Population (%)']
    for col in list(df.columns):
        if '(%)' in col:
            if col == 'Unemployment Rate (%)':
                df = percent_to_population('Unemployment Rate (%)', 'Population Unemployed', df)
            else:
                df = percent_to_population(col, col.replace(' (%)', ''), df)

    if 'Policy Value' in list(df.columns) or 'Countdown' in list(df.columns):
        df = df.drop(['Policy Value', 'Countdown'], axis=1)

    for col in cols_to_drop:
        try:
            df.drop([col], axis=1, inplace=True)
        except:
            pass
    return df


def normalize(df: pd.DataFrame) -> pd.DataFrame:
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
    analysis_df = prepare_analysis_data(df)
    analysis_df = normalize(analysis_df)

    # crossed = cross_features(analysis_df)
    # analysis_df['Crossed'] = crossed['Mean']
    # analysis_df = normalize_column(analysis_df, 'Crossed')

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


def calculate_cost_estimate(df: pd.DataFrame, pct_burdened: float, distribution: dict,
                            rent_type: str = 'fmr') -> pd.DataFrame:
    if rent_type == 'fmr':
        cost_df = queries.static_data_single_table('fair_market_rents', queries.static_columns['fair_market_rents'])
    elif rent_type == 'rent50':
        cost_df = queries.static_data_single_table('median_rents', queries.static_columns['median_rents'])
        print(cost_df)
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
        df['br_cost_0'] = value * df[f'{rent_type}_0'] * (pct_burdened / 100) * (
                df['Resident Population (Thousands of Persons)'] * 1000) * (df['Burdened Households (%)'] / 100)
        df['br_cost_1'] = value * df[f'{rent_type}_1'] * (pct_burdened / 100) * (
                df['Resident Population (Thousands of Persons)'] * 1000) * (df['Burdened Households (%)'] / 100)
        df['br_cost_2'] = value * df[f'{rent_type}_2'] * (pct_burdened / 100) * (
                df['Resident Population (Thousands of Persons)'] * 1000) * (df['Burdened Households (%)'] / 100)
        df['br_cost_3'] = value * df[f'{rent_type}_3'] * (pct_burdened / 100) * (
                df['Resident Population (Thousands of Persons)'] * 1000) * (df['Burdened Households (%)'] / 100)
        df['br_cost_4'] = value * df[f'{rent_type}_4'] * (pct_burdened / 100) * (
                df['Resident Population (Thousands of Persons)'] * 1000) * (df['Burdened Households (%)'] / 100)
        df['total_cost'] = np.sum([df['br_cost_0'], df['br_cost_1'], df['br_cost_2'], df['br_cost_3'], df['br_cost_4']],
                                  axis=0)
    return df


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
        df = calculate_cost_estimate(df, pct_burdened, rent_type='fmr', distribution=distribution)
    elif rent_type == 'Median':
        df = calculate_cost_estimate(df, pct_burdened, rent_type='rent50', distribution=distribution)

    cost_df = df.reset_index()
    cost_df.drop(columns=['State'], inplace=True)
    cost_df.set_index('County Name', inplace=True)
    # cost_df = cost_df[['br_cost_0', 'br_cost_1', 'br_cost_2', 'br_cost_3', 'br_cost_4', 'total_cost']]
    # st.dataframe(
    #     cost_df[['total_cost']])
    st.bar_chart(cost_df['total_cost'])
    return cost_df
