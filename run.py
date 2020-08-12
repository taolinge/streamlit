import itertools
import math
import os

import matplotlib.pyplot as plt
import numpy as np
import openpyxl
import pandas as pd
import sklearn.preprocessing as pre

import api
import datasets

COUNTIES_OF_INTEREST = [
    'Alameda',
    'Contra Costa',
    'Marin',
    'Napa',
    'San Mateo',
    'San Francisco',
    'Santa Clara',
    'Solano',
    'Sonoma',
]

ACTION_OVERHEAD = 7


def process_poverty_data():
    files = [
        {
            'name': 'CA Statewide Poverty Data',
            'type': 'xlsx',
            'directory': 'data/',
            'sheet': 'Data',
            'features': [
                'race_eth_code',
                'race_eth_name',
                'geoname',
                'county_name',
                'strata_one_code',
                'strata_one_name',
                'numerator',
                'denominator',
                'estimate',
            ]
        },
    ]
    for file in files:
        data = datasets.DataSet(file['directory'], file['name'], file['type'], file['sheet'])
        data.get_data()
        data.drop_blank_feature_values(file['features'])
        data.drop_non_feature_columns(file['features'])
        df = data.filter_counties(COUNTIES_OF_INTEREST, 'county_name')

        data.save()


def reshape_data() -> pd.DataFrame:
    data = []
    features = []
    ignore_features = ['Unemployment_Crises_changes_3m', 'Unemployment_Crises_changes']
    for filename in os.listdir('../data-analysis/new_story/data'):
        if filename.startswith("FRED"):
            name = filename[5:][:-4]
            if name not in ignore_features:
                features.append(name)
                df = api.get_from_csv('data/' + filename)
                data.append(df)

    transformed_df = pd.DataFrame(index=COUNTIES_OF_INTEREST)
    for i, d in enumerate(data):
        d = d[COUNTIES_OF_INTEREST]
        most_recent = d.tail(1)
        most_recent = most_recent.T
        most_recent.columns = [features[i]]
        transformed_df[features[i]] = most_recent

    transformed_df['non_homeownership_rate_percentage'] = 100 - transformed_df['homeownership_rate_percentage']

    vulnerability_df = api.get_from_csv('data/vulnerability_index.csv')
    vulnerability_df.rename(columns={'VulnerabilityIndex': 'COVID_VulnerabilityIndex'}, inplace=True)
    vulnerability_df['COVID_VulnerabilityIndex'] = vulnerability_df['COVID_VulnerabilityIndex'] - 100
    transformed_df = transformed_df.join(vulnerability_df.set_index('County'))

    # transformed_df = transformed_df.join(policy_df.set_index('County'))

    shelter_df = api.get_from_excel('data/shelter_capacity.xlsx', sheet_name='capacity in use')
    shelter_df.drop(['PIT Sheltered Homeless, 2016', 'Total Year Round Beds', 'Seasonal Beds', 'Overflow Beds',
                     'Sheltered Homeless to Total Beds', 'PIT Available Beds'], axis=1, inplace=True)
    shelter_df.rename(columns={'2019 Sheltered Homeless to Total Beds': 'Percent_Shelter_Beds_Occupied'}, inplace=True)
    transformed_df = transformed_df.join(shelter_df.set_index('County'))

    transformed_df.drop([
        'homeownership_rate_percentage',
        'Rank'
    ], axis=1, inplace=True)
    transformed_df.to_excel('data_clean.xlsx')

    return transformed_df


def percent_to_population(feature: str, name: str, df: pd.DataFrame) -> pd.DataFrame:
    df[name] = (df[feature] / 100) * df['Resident_Population_thousands_of_persons'] * 1000
    return df


def cross_features(df: pd.DataFrame) -> pd.DataFrame:
    cols = ['Pop_Below_Poverty_Level', 'Pop_Unemployed', 'income_inequality_ratio', 'non_homeowners',
            'Num_Burdened_HouseHolds', 'Num_Single_Parent_Households']
    all_combinations = []
    for r in range(3, len(cols)):
        combinations_list = list(itertools.combinations(cols, r))
        all_combinations += combinations_list
    all_combinations.pop(0)
    new_cols = []
    for combo in all_combinations:
        new_cols.append(cross(combo, df))

    crossed_df = pd.DataFrame(new_cols)
    crossed_df = crossed_df.T
    # crossed_df['Sum'] = crossed_df.sum(axis=1)
    crossed_df['Mean'] = crossed_df.mean(axis=1)
    # crossed_df['Median'] = crossed_df.median(axis=1)
    crossed_df.to_excel('data_crossed.xlsx')

    return crossed_df


def normalize(df) -> pd.DataFrame:
    df = percent_to_population('Percent_of_Pop_Below_Poverty_Level', 'Pop_Below_Poverty_Level', df)
    df = percent_to_population('Unemployment_Cleaned', 'Pop_Unemployed', df)
    df = percent_to_population('Burdened_HouseHolds', 'Num_Burdened_HouseHolds', df)
    df = percent_to_population('Single_Parent_Households', 'Num_Single_Parent_Households', df)
    df = percent_to_population('non_homeownership_rate_percentage', 'non_homeowners', df)

    df = df.drop(['Percent_of_Pop_Below_Poverty_Level',
                  'Unemployment_Cleaned',
                  'Burdened_HouseHolds',
                  'Single_Parent_Households',
                  'Resident_Population_thousands_of_persons',
                  'non_homeownership_rate_percentage'], axis=1)

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


def priority_indicator(relative_risk: float, policy_index: float, time_left: float, time_to_action: float) -> float:
    return relative_risk * (1 - policy_index) * time_to_action / math.sqrt(time_left)


def poverty_demographics():
    df = pd.read_excel('data/CA Statewide Poverty Data clean.xlsx')
    res = df.groupby(['county_name', 'race_eth_name']).sum()
    res['estimate'] = res['numerator'] / res['denominator']
    res.drop(index='Total', level=1, inplace=True)
    g = res['estimate'].groupby(level=0, group_keys=False, )
    df = g.apply(lambda x: x.sort_values(ascending=False))
    df.to_excel('CAPoverty_sorted.xlsx')


def main():
    df = reshape_data()
    analysis_df = normalize(df)
    policy_df = api.get_from_csv('data/policy_index.csv')
    policy_df['PolicyIndex'] = 1 - policy_df['PolicyIndex']

    crossed = cross_features(analysis_df)

    analysis_df['Crossed'] = crossed['Mean']
    analysis_df = normalize_column(analysis_df, 'Crossed')
    analysis_df['Total Relative Risk'] = analysis_df.sum(axis=1)
    temp_df = pd.DataFrame([analysis_df['Total Relative Risk'], policy_df['PolicyIndex']])
    max_sum = analysis_df['Total Relative Risk'].max()
    analysis_df['Relative Rank'] = (analysis_df['Total Relative Risk'] / max_sum)
    analysis_df.to_excel('overall_vulnerability.xlsx')

    presentation_df = df.copy()
    presentation_df['Crossed'] = analysis_df['Crossed']
    presentation_df['Relative Rank'] = analysis_df['Relative Rank']
    presentation_df.to_excel('presentation_data.xlsx')


if __name__ == '__main__':
    # Pandas options
    pd.set_option('max_rows', 10)
    pd.set_option('max_columns', 10)
    pd.set_option('expand_frame_repr', True)
    pd.set_option('large_repr', 'truncate')
    pd.options.display.float_format = '{:.2f}'.format

    if len(COUNTIES_OF_INTEREST) == 0:
        COUNTIES_OF_INTEREST = input(
            'No counties specified. Please specify one or more counties, separated by commas.').split(',')
    COUNTIES_OF_INTEREST = [x.strip() for x in COUNTIES_OF_INTEREST]

    if ACTION_OVERHEAD is None or ACTION_OVERHEAD == '':
        ACTION_OVERHEAD = int(input(
            'Please specify the amount of time it takes to implement the required action or policy. '
            'Make sure that this is provided in the same unit as the countdown time.').strip())

    main()
