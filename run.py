import itertools
import math
import os

import pandas as pd
import sklearn.preprocessing as pre

import api
import queries

# Pandas options
pd.set_option('max_rows', 10)
pd.set_option('max_columns', 10)
pd.set_option('expand_frame_repr', True)
pd.set_option('large_repr', 'truncate')
pd.options.display.float_format = '{:.2f}'.format


def filter_state(data: pd.DataFrame, state: str) -> pd.DataFrame:
    return data[data['State'] == state]


def filter_counties(data: pd.DataFrame, counties: list) -> pd.DataFrame:
    return data[data['County Name'].isin(counties)]


def clean_fred_data(data: pd.DataFrame) -> pd.DataFrame:
    data['Non-Home Ownership (%)'] = 100 - data['Home Ownership (%)']

    data.drop([
        'Home Ownership (%)',
        'county_id',
        'Burdened Households Date',
        'Home Ownership Date',
        'Income Inequality Date',
        'Population Below Poverty Line Date',
        'Single Parent Households Date',
        'SNAP Benefits Recipients Date',
        'Unemployment Rate Date'
    ], axis=1, inplace=True)

    data.set_index(['State', 'County Name'], drop=True)
    data = data.loc[:, ~data.columns.str.contains('^Unnamed')]

    data.to_excel('Output/FRED_data_cleaned.xlsx')

    return data


def percent_to_population(feature: str, name: str, df: pd.DataFrame) -> pd.DataFrame:
    df[name] = (df[feature] / 100) * df['Resident_Population_thousands_of_persons'] * 1000
    return df


def cross_features(df: pd.DataFrame) -> pd.DataFrame:
    cols = ['Pop_Below_Poverty_Level', 'Pop_Unemployed', 'Income Inequality (Ratio)', 'Non_Home_Ownership_Pop',
            'Num_Burdened_Households', 'Num_Single_Parent_Households']
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
    crossed_df.to_excel('data_crossed.xlsx')

    return crossed_df


def normalize(df) -> pd.DataFrame:
    df = percent_to_population('Population Below Poverty Line (%)', 'Pop_Below_Poverty_Level', df)
    df = percent_to_population('Unemployment Rate (%)', 'Pop_Unemployed', df)
    df = percent_to_population('Burdened Households (%)', 'Num_Burdened_Households', df)
    df = percent_to_population('Single Parent Households (%)', 'Num_Single_Parent_Households', df)
    df = percent_to_population('Non-Home Ownership (%)', 'Non_Home_Ownership_Pop', df)

    df = df.drop(['Percent_of_Pop_Below_Poverty_Level',
                  'Unemployment_Cleaned',
                  'Burdened Households (%)',
                  'Single Parent Households (%)',
                  'Resident_Population_thousands_of_persons',
                  'Non-Home Ownership (%)'], axis=1)

    scaler = pre.MaxAbsScaler()
    df_scaled = pd.DataFrame(scaler.fit_transform(df), index=df.index, columns=df.columns)
    output_df = df_scaled.copy()
    output_df['Sum'] = output_df.sum(axis=1)
    output_df.to_excel('data_normalized.xlsx')

    return df_scaled


def normalize_column(df: pd.DataFrame, col) -> pd.DataFrame:
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


def priority_indicator(relative_risk: float, policy_index: float, time_left: float) -> float:
    return relative_risk * (1 - policy_index) / math.sqrt(time_left)


def main(df):
    df = clean_fred_data(df)
    # analysis_df = normalize(df)
    #
    # policy_df = api.get_from_csv('data/policy_index.csv')
    # policy_df['PolicyIndex'] = 1 - policy_df['PolicyIndex']
    #
    # crossed = cross_features(analysis_df)
    #
    # analysis_df['Crossed'] = crossed['Mean']
    # analysis_df = normalize_column(analysis_df, 'Crossed')
    # analysis_df['Total Relative Risk'] = analysis_df.sum(axis=1)
    # temp_df = pd.DataFrame([analysis_df['Total Relative Risk'], policy_df['PolicyIndex']])
    # max_sum = analysis_df['Total Relative Risk'].max()
    # analysis_df['Relative Rank'] = (analysis_df['Total Relative Risk'] / max_sum)
    # analysis_df.to_excel('overall_vulnerability.xlsx')
    #
    # return analysis_df


def get_single_county(county: str, state: str) -> pd.DataFrame:
    if os.path.exists("Output/all_tables.xlsx"):
        print('Using local `all_tables.xlsx`')
        df = pd.read_excel('Output/all_tables.xlsx')
    else:
        # Todo: Use query function to get from database
        df = pd.DataFrame()

    df = filter_state(df, state)
    df = filter_counties(df, [county])

    return df


def get_multiple_counties(counties: list, state: str) -> pd.DataFrame:
    if os.path.exists("Output/all_tables.xlsx"):
        print('Using local `all_tables.xlsx`')
        df = pd.read_excel('Output/all_tables.xlsx')
    else:
        # Todo: Use query function to get from database
        df = pd.DataFrame()

    df = filter_state(df, state)
    df = filter_counties(df, counties)

    return df


def get_state_data(state: str) -> pd.DataFrame:
    if os.path.exists("Output/all_tables.xlsx"):
        print('Using local `all_tables.xlsx`')
        df = pd.read_excel('Output/all_tables.xlsx')
    else:
        # Todo: Use query function to get from database
        df = pd.DataFrame()

    df = filter_state(df, state)
    return df


if __name__ == '__main__':
    if not os.path.exists('Output'):
        os.makedirs('Output')

    task = input(
        'Are you analyzing a single county (1), multiple counties (2), or all the counties in a state (3)? [default: 1]')

    if task == '1' or task is None or task == '':
        res = input('Enter the county and state (ie: Jefferson County, Colorado):')
        res = res.strip().split(',')
        county = res[0].strip()
        state = res[1].strip()
        df = get_single_county(county, state)
    elif task == '2':
        state = input("Which state are you looking for (ie: California)?]").strip()
        counties = input('Please specify one or more counties, separated by commas [ie: ].').split(',')
        counties = [_.strip() for _ in counties]
        df = get_multiple_counties(counties, state)
    elif task == '3':
        state = input("Which state are you looking for (ie: California)?]").strip()
        df = get_state_data(state)
    else:
        raise Exception('INVALID INPUT! Enter a valid task number.')

    main(df)
