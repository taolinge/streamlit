import os
import sys
import psycopg2
import pandas as pd
from sqlalchemy import create_engine
from shapely import wkb

import credentials

fred_tables = [
    'burdened_households',
    # 'homeownership_rate',
    'income_inequality',
    'population_below_poverty',
    'single_parent_households',
    # 'snap_benefits_recipients',
    'unemployment_rate',
    'resident_population',
]

static_tables = [
    'chmura_economic_vulnerability_index',
    'median_rents',
    'fair_market_rents'
]

static_columns = {
    'chmura_economic_vulnerability_index': ['VulnerabilityIndex', 'Rank'],
    'fair_market_rents': ['fmr_0', 'fmr_1', 'fmr_2', 'fmr_3', 'fmr_4', ],
    'median_rents': ['rent50_0', 'rent50_1', 'rent50_2', 'rent50_3', 'rent50_4', ]
}

table_headers = {
    'burdened_households': 'Burdened Households',
    'homeownership_rate': 'Home Ownership',
    'income_inequality': 'Income Inequality',
    'population_below_poverty': 'Population Below Poverty Line',
    'single_parent_households': 'Single Parent Households',
    'snap_benefits_recipients': 'SNAP Benefits Recipients',
    'unemployment_rate': 'Unemployment Rate',
    'resident_population': 'Resident Population',
}

table_units = {
    'burdened_households': '%',
    'homeownership_rate': '%',
    'income_inequality': 'Ratio',
    'population_below_poverty': '%',
    'single_parent_households': '%',
    'snap_benefits_recipients': 'Persons',
    'unemployment_rate': '%',
    'resident_population': 'Thousands of Persons',
}


def init_connection():
    conn = psycopg2.connect(
        dbname=credentials.DB_NAME,
        user=credentials.DB_USER,
        password=credentials.DB_PASSWORD,
        port=credentials.DB_PORT,
        host=credentials.DB_HOST
    )

    engine = create_engine(
        f'postgresql://{credentials.DB_USER}:{credentials.DB_PASSWORD}@{credentials.DB_HOST}:{credentials.DB_PORT}/{credentials.DB_NAME}')
    return conn, engine


def write_table(df: pd.DataFrame, table: str):
    conn, engine = init_connection()
    df.to_sql(table, engine, if_exists='replace', method='multi')
    conn.close()


def counties_query() -> pd.DataFrame:
    conn, engine = init_connection()
    cur = conn.cursor()
    cur.execute(
        'SELECT id as county_id, state as "State", name as "County Name" '
        'FROM counties'
    )
    colnames = [desc[0] for desc in cur.description]
    results = cur.fetchall()
    conn.close()
    return pd.DataFrame(results, columns=colnames)


def policy_query() -> pd.DataFrame:
    conn, engine = init_connection()
    cur = conn.cursor()
    cur.execute(
        'SELECT county_id as county_id, policy_value as "Policy Value", countdown as "Countdown" '
        'FROM policy'
    )
    colnames = [desc[0] for desc in cur.description]
    results = cur.fetchall()
    conn.close()
    return pd.DataFrame(results, columns=colnames)


def latest_data_single_table(table_name: str, require_counties: bool = True) -> pd.DataFrame:
    conn, engine = init_connection()

    cur = conn.cursor()
    cur.execute(
        'SELECT DISTINCT ON (county_id) '
        'county_id, date AS "{} Date", value AS "{} ({})" '
        'FROM {} '
        'ORDER BY county_id , "date" DESC'.format(table_headers[table_name], table_headers[table_name],
                                                  table_units[table_name], table_name))
    results = cur.fetchall()
    colnames = [desc[0] for desc in cur.description]
    conn.close()

    df = pd.DataFrame(results, columns=colnames)
    if require_counties:
        counties_df = counties_query()
        df = counties_df.merge(df)
    return df


def latest_data_all_tables() -> pd.DataFrame:
    counties_df = counties_query()
    for table_name in fred_tables:
        table_output = latest_data_single_table(table_name, require_counties=False)
        counties_df = counties_df.merge(table_output)
    chmura_df = static_data_single_table('chmura_economic_vulnerability_index', ['VulnerabilityIndex'])
    counties_df = counties_df.merge(chmura_df)
    demo_df = generic_select_query('socio_demographics',
                                   ['id', 'hse_units', 'vacant', 'renter_occ', 'med_age', 'white', 'black', 'ameri_es',
                                    'asian', 'hawn_pi', 'hispanic', 'other', 'mult_race', 'males', 'females', 'population'])
    demo_df.rename({
        'id': 'county_id',
        'hse_units': 'Housing Units',
        'vacant': 'Vacant Units',
        'renter_occ': 'Renter Occupied Units',
        'med_age': 'Median Age',
        'white': 'White',
        'black': 'Black',
        'ameri_es': 'Native American',
        'asian': 'Asian',
        'hawn_pi': 'Pacific Islander',
        'hispanic': 'Hispanic',
        'other': 'Other',
        'mult_race': 'Multiple Race',
        'males': 'Males',
        'females': 'Females'
    }, axis=1, inplace=True)
    demo_df['Percent Non-White'] = (demo_df['Black'] + demo_df['Native American'] + demo_df['Asian'] + demo_df[
        'Pacific Islander'] + demo_df['Hispanic'] + demo_df['Other'] + demo_df['Multiple Race']) / demo_df['population'] * 100
    demo_df.drop(['population'],axis=1, inplace=True)
    counties_df = counties_df.merge(demo_df)
    return counties_df


def static_data_single_table(table_name: str, columns: list) -> pd.DataFrame:
    conn, engine = init_connection()
    cur = conn.cursor()
    str_columns = ', '.join('"{}"'.format(c) for c in columns)
    query = 'SELECT county_id, {} FROM {} '.format(str_columns, table_name)
    cur.execute(query)
    results = cur.fetchall()
    colnames = [desc[0] for desc in cur.description]
    df = pd.DataFrame(results, columns=colnames)
    counties_df = counties_query()
    df = counties_df.merge(df)
    conn.close()
    return df


def generic_select_query(table_name: str, columns: list) -> pd.DataFrame:
    conn, engine = init_connection()
    cur = conn.cursor()
    str_columns = ', '.join('"{}"'.format(c) for c in columns)
    query = 'SELECT {} FROM {} '.format(str_columns, table_name)
    cur.execute(query)
    results = cur.fetchall()
    colnames = [desc[0] for desc in cur.description]
    conn.close()
    df = pd.DataFrame(results, columns=colnames)
    return df


def get_county_geoms(counties_list: list, state: str) -> pd.DataFrame:
    conn, engine = init_connection()
    counties = "(" + ",".join(["'" + str(_) + "'" for _ in counties_list]) + ")"
    cur = conn.cursor()
    query = "SELECT * FROM counties_geom WHERE cnty_name in {} AND LOWER(state)='{}';".format(counties, state)
    cur.execute(query)
    results = cur.fetchall()
    colnames = [desc[0] for desc in cur.description]
    df = pd.DataFrame(results, columns=colnames)
    parcels = []
    for parcel in df['geom']:
        parcels.append(wkb.loads(parcel, hex=True))
    geom_df = pd.DataFrame()
    geom_df['County Name'] = df['cnty_name']
    # geom_df['State'] = df['state']
    geom_df['geom'] = pd.Series(parcels)
    conn.close()
    return geom_df


def list_tables():
    conn, engine = init_connection()

    conn.close()
    return


def static_data_all_table() -> pd.DataFrame:
    counties_df = counties_query()
    for table_name in static_tables:
        table_output = static_data_single_table(table_name, static_columns[table_name])
        counties_df = counties_df.merge(table_output)
    return counties_df


def output_data(df: pd.DataFrame, table_name: str = 'fred_tables', ext: str = 'xlsx') -> str:
    if not os.path.isdir('Output'):
        os.mkdir('Output')
    if ext == 'pk':
        path = 'Output/{}.pk'.format(table_name)
        df.to_pickle(path)
    elif ext == 'xlsx':
        path = 'Output/{}.xlsx'.format(table_name)
        df.to_excel(path)
    else:
        print('Only .pk and .xlsx outputs are currently supported.')
        sys.exit()
    return path


def fmr_data():
    conn, engine = init_connection()
    cur = conn.cursor()
    cur.execute(
        'SELECT state_full as "State", countyname as "County Name" '
        'FROM fair_market_rents'
    )
    colnames = [desc[0] for desc in cur.description]
    results = cur.fetchall()
    conn.close()
    return pd.DataFrame(results, columns=colnames)


if __name__ == '__main__':
    args = {k: v for k, v in [i.split('=') for i in sys.argv[1:] if '=' in i]}
    table = args.get('--table', None)
    output_format = args.get('--output', None)

    if table:
        df = latest_data_single_table(table)
    else:
        df = latest_data_all_tables()

    if output_format:
        if table:
            path = output_data(df, table_name=table, ext=output_format)
        else:
            path = output_data(df, ext=output_format)
    else:
        if table:
            path = output_data(df, table_name=table)
        else:
            path = output_data(df)

    print('Successful query returned. Output at {}.'.format(path))
    # get_county_geoms(['Boulder County', 'Arapahoe County'], 'colorado')
