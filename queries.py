import os
import sys
import psycopg2
import pandas as pd
from sqlalchemy import create_engine
from shapely import wkb
import streamlit as st

import credentials
from constants import STATES

FRED_TABLES = [
    'burdened_households',
    # 'homeownership_rate',
    'income_inequality',
    'population_below_poverty',
    'resident_population',
    'single_parent_households',
    'snap_benefits_recipients',
    'unemployment_rate',
]

STATIC_TABLES = [
    'chmura_economic_vulnerability_index',
    'fair_market_rents'
    'median_rents',
]

STATIC_COLUMNS = {
    'chmura_economic_vulnerability_index': ['VulnerabilityIndex', 'Rank'],
    'fair_market_rents': ['fmr_0', 'fmr_1', 'fmr_2', 'fmr_3', 'fmr_4'],
    'median_rents': ['rent50_0', 'rent50_1', 'rent50_2', 'rent50_3', 'rent50_4']
}

TABLE_HEADERS = {
    'burdened_households': 'Burdened Households',
    'homeownership_rate': 'Home Ownership',
    'income_inequality': 'Income Inequality',
    'population_below_poverty': 'Population Below Poverty Line',
    'single_parent_households': 'Single Parent Households',
    'snap_benefits_recipients': 'SNAP Benefits Recipients',
    'unemployment_rate': 'Unemployment Rate',
    'resident_population': 'Resident Population',
}

TABLE_UNITS = {
    'burdened_households': '%',
    'homeownership_rate': '%',
    'income_inequality': 'Ratio',
    'population_below_poverty': '%',
    'single_parent_households': '%',
    'snap_benefits_recipients': 'Persons',
    'unemployment_rate': '%',
    'resident_population': 'Thousands of Persons',
}

CENSUS_TABLES = ['disability_status',
                 'educational_attainment',
                 'employment_status',
                 'english_proficiency',
                 'family_type',
                 'hispanic_or_latino_origin_by_race',
                 'household_job_availability',
                 'household_technology_availability',
                 'household_vehicle_availability',
                 'housing_units_in_structure',
                 'level_of_urbanicity',
                 'occupants_per_bedroom',
                 'poverty_status',
                 'resident_population_census_tract',
                 'sex_by_age',
                 'sex_of_workers_by_vehicles_available',
                 'trip_miles',
                 'walkability_index']


def init_engine():
    engine = create_engine(
        f'postgresql://{credentials.DB_USER}:{credentials.DB_PASSWORD}@{credentials.DB_HOST}:{credentials.DB_PORT}/{credentials.DB_NAME}')
    return engine


def init_connection():
    if st.secrets:
        conn = psycopg2.connect(**st.secrets["postgres"])
    else:
        conn = psycopg2.connect(
            user=credentials.DB_USER,
            password=credentials.DB_PASSWORD,
            host=credentials.DB_HOST,
            port=credentials.DB_PORT,
            dbname=credentials.DB_NAME
        )
    return conn


def write_table(df: pd.DataFrame, table: str):
    engine = init_engine()
    df.to_sql(table, engine, if_exists='replace', method='multi')


def all_counties_query() -> pd.DataFrame:
    conn = init_connection()
    cur = conn.cursor()
    cur.execute(
        'SELECT DISTINCT county_name, state_name, county_id FROM id_index;'
    )
    colnames = [desc[0] for desc in cur.description]
    results = cur.fetchall()
    conn.commit()
    df = pd.DataFrame(results, columns=colnames)
    return df


def table_names_query() -> list:
    conn = init_connection()
    cur = conn.cursor()
    cur.execute("""SELECT table_name FROM information_schema.tables
        WHERE table_schema = 'public'
        """)
    results = cur.fetchall()
    conn.commit()

    res = [_[0] for _ in results]
    return res


@st.experimental_memo()
def read_table(table: str, columns: list = None, where_clause: str = None, order_by: str = None,
               order: str = 'ASC') -> pd.DataFrame:
    conn = init_connection()
    if columns is not None:
        cols = ', '.join(columns)
        query = f"SELECT {cols} FROM {table}"
    else:
        query = f"SELECT * FROM {table}"
    if where_clause is not None:
        query += f" WHERE {where_clause}"
    if order_by is not None:
        query += f"ORDER BY {order_by} {order}"
    query += ';'

    df = pd.read_sql(query, con=conn)
    return df


@st.experimental_memo(ttl=1200)
def latest_data_census_tracts(state: str, counties: list, tables: list) -> pd.DataFrame:
    conn = init_connection()
    cur = conn.cursor()
    tracts_df = census_tracts_geom_query(counties, state)
    counties_str = str(tuple(counties)).replace(',)', ')')
    where_clause = f"WHERE id_index.state_name ='{state}' AND id_index.county_name IN {counties_str}"

    for table_name in tables:
        query =f"""SELECT {table_name}.*, id_index.county_name, id_index.county_id, id_index.state_name, id_index.tract_id,
        resident_population_census_tract.tot_population_census_2010
            FROM {table_name} 
            INNER JOIN id_index ON {table_name}.tract_id = id_index.tract_id
            INNER JOIN resident_population_census_tract ON {table_name}.tract_id = resident_population_census_tract.tract_id
            {where_clause};"""
        cur.execute(query)
        results = cur.fetchall()
        conn.commit()

        colnames = [desc[0] for desc in cur.description]
        df = pd.DataFrame(results, columns=colnames)
        df = df.loc[:, ~df.columns.duplicated()]
        df.rename({'tract_id': 'Census Tract'}, axis=1, inplace=True)

        tracts_df = tracts_df.merge(df, on="Census Tract", how="inner", suffixes=('', '_y'))
        tracts_df.drop(tracts_df.filter(regex='_y$').columns.tolist(), axis=1, inplace=True)
        tracts_df = tracts_df.loc[:, ~tracts_df.columns.duplicated()]
    return tracts_df


def load_distributions() -> tuple:
    metro_areas = generic_select_query('housing_stock_distribution', [
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


def policy_query() -> pd.DataFrame:
    conn = init_connection()
    cur = conn.cursor()
    cur.execute(
        'SELECT county_id as county_id, policy_value as "Policy Value", countdown as "Countdown" '
        'FROM policy'
    )
    colnames = [desc[0] for desc in cur.description]
    results = cur.fetchall()
    conn.commit()

    return pd.DataFrame(results, columns=colnames)


def latest_data_single_table(table_name: str, require_counties: bool = True) -> pd.DataFrame:
    conn = init_connection()
    cur = conn.cursor()
    cur.execute(
        'SELECT DISTINCT ON (county_id) '
        'county_id, date AS "{} Date", value AS "{} ({})" '
        'FROM {} '
        'ORDER BY county_id , "date" DESC'.format(TABLE_HEADERS[table_name], TABLE_HEADERS[table_name],
                                                  TABLE_UNITS[table_name], table_name))
    results = cur.fetchall()
    conn.commit()

    colnames = [desc[0] for desc in cur.description]

    df = pd.DataFrame(results, columns=colnames)
    if require_counties:
        counties_df = all_counties_query()
        df = counties_df.merge(df)
    return df


@st.experimental_memo(ttl=1200)
def get_all_county_data(state: str, counties: list) -> pd.DataFrame:
    # for table_name in FRED_TABLES:
    #     table_output = read_table(table_name,where_clause=f'')
    # counties_df = counties_df.merge(table_output, how='outer')
    # chmura_df = static_data_single_table('chmura_economic_vulnerability_index', ['VulnerabilityIndex'])
    # counties_df = counties_df.merge(chmura_df, how='outer')

    if counties:
        counties_list = [_.replace("'", "''") for _ in counties]
        counties_str = "(" + ",".join(["'" + str(_) + "'" for _ in counties_list]) + ")"
        demo_df = generic_select_query('county_demographics',
                                       ['fips', 'state_name', 'county_name', 'hse_units', 'vacant', 'renter_occ',
                                        'med_age', 'white', 'black', 'ameri_es',
                                        'asian', 'hawn_pi', 'hispanic', 'other', 'mult_race', 'males', 'females',
                                        'population'], where=f"state_name='{state}' AND county_name in {counties_str};")
    else:
        demo_df = generic_select_query('county_demographics',
                                       ['fips', 'state_name', 'county_name', 'hse_units', 'vacant', 'renter_occ',
                                        'med_age', 'white', 'black',
                                        'ameri_es',
                                        'asian', 'hawn_pi', 'hispanic', 'other', 'mult_race', 'males', 'females',
                                        'population'], where=f"state_name='{state}';")
    demo_df['Non-White Population'] = (demo_df['black'] + demo_df['ameri_es'] + demo_df['asian'] + demo_df[
        'hawn_pi'] + demo_df['hispanic'] + demo_df['other'] + demo_df['mult_race'])
    demo_df['Non-White Population (%)'] = demo_df['Non-White Population'] / demo_df['population'] * 100
    demo_df['fips'] = demo_df['fips'].astype(int)

    demo_df.rename({
        'fips': 'county_id',
        'state_name': 'State',
        'county_name': 'County Name',
        'hse_units': 'Housing Units',
        'vacant': 'Vacant Units',
        'renter_occ': 'Renter Occupied Units',
        'med_age': 'Median Age',
        'white': 'White Population',
        'black': 'Black Population',
        'ameri_es': 'Native American Population',
        'asian': 'Asian Population',
        'hawn_pi': 'Pacific Islander Population',
        'hispanic': 'Hispanic Population',
        'other': 'Other Population',
        'mult_race': 'Multiple Race Population',
        'males': 'Male Population',
        'females': 'Female Population',
        'population': 'Total Population',
    }, axis=1, inplace=True)
    return demo_df


def static_data_single_table(table_name: str, columns: list) -> pd.DataFrame:
    conn = init_connection()
    cur = conn.cursor()
    str_columns = ', '.join('"{}"'.format(c) for c in columns)
    query = 'SELECT county_id, {} FROM {} '.format(str_columns, table_name)
    cur.execute(query)
    results = cur.fetchall()
    conn.commit()

    colnames = [desc[0] for desc in cur.description]
    df = pd.DataFrame(results, columns=colnames)
    counties_df = all_counties_query()
    df = counties_df.merge(df, how='outer')
    return df


def generic_select_query(table_name: str, columns: list, where: str = None) -> pd.DataFrame:
    conn = init_connection()
    cur = conn.cursor()
    str_columns = ', '.join('"{}"'.format(c) for c in columns)
    query = 'SELECT {} FROM {} '.format(str_columns, table_name)
    if where is not None:
        query += f'WHERE {where}'
    cur.execute(query)
    results = cur.fetchall()
    conn.commit()

    colnames = [desc[0] for desc in cur.description]
    df = pd.DataFrame(results, columns=colnames)
    return df


@st.experimental_memo(ttl=1200)
def get_county_geoms(counties_list: list, state: str) -> pd.DataFrame:
    conn = init_connection()
    counties_list = [_.replace("'", "''") for _ in counties_list]
    counties = "(" + ",".join(["'" + str(_) + "'" for _ in counties_list]) + ")"
    cur = conn.cursor()
    query = f"SELECT * FROM county_geoms WHERE state_name='{state}' AND county_name in {counties};"
    cur.execute(query)
    results = cur.fetchall()
    conn.commit()

    colnames = [desc[0] for desc in cur.description]
    df = pd.DataFrame(results, columns=colnames)
    parcels = []
    for parcel in df['geom']:
        geom = wkb.loads(parcel, hex=True)
        parcels.append(geom.simplify(tolerance=0.001, preserve_topology=True))
    geom_df = pd.DataFrame()
    geom_df['county_id'] = df['county_id']
    geom_df['County Name'] = df['county_name']
    geom_df['State'] = df['state_name']
    geom_df['Area sqmi'] = df['sqmi']
    geom_df['geom'] = pd.Series(parcels)
    return geom_df


@st.experimental_memo(ttl=1200)
def get_county_geoms_by_id(counties_list: list) -> pd.DataFrame:
    conn = init_connection()
    counties = "(" + ",".join(["'" + str(_) + "'" for _ in counties_list]) + ")"
    cur = conn.cursor()
    query = f"SELECT * FROM county_geoms WHERE county_id in {counties};"
    cur.execute(query)
    results = cur.fetchall()
    conn.commit()

    colnames = [desc[0] for desc in cur.description]
    df = pd.DataFrame(results, columns=colnames)
    parcels = []
    for parcel in df['geom']:
        geom = wkb.loads(parcel, hex=True)
        parcels.append(geom.simplify(tolerance=0.001, preserve_topology=True))
    geom_df = pd.DataFrame()
    geom_df['county_id'] = df['county_id']
    geom_df['County Name'] = df['county_name']
    geom_df['State'] = df['state_name']
    geom_df['Area sqmi'] = df['sqmi']
    geom_df['geom'] = pd.Series(parcels)
    return geom_df


@st.experimental_memo(ttl=1200)
def census_tracts_geom_query(counties, state) -> pd.DataFrame:
    conn = init_connection()
    cur = conn.cursor()
    if len(counties) > 1:
        where_clause = 'WHERE id_index.state_name = ' + "'" + state + "'" + ' ' + 'AND id_index.county_name IN ' + str(
            tuple(counties))
    if len(counties) == 1:
        where_clause = 'WHERE id_index.state_name = ' + "'" + state + "'" + ' ' + 'AND id_index.county_name IN (' + "'" + \
                       counties[0] + "'" + ')'
    cur.execute(f"""
        SELECT id_index.county_name, id_index.state_name, census_tracts_geom.tract_id, census_tracts_geom.geom
        FROM id_index
        INNER JOIN census_tracts_geom ON census_tracts_geom.tract_id=id_index.tract_id
        {where_clause};
    """)
    colnames = [desc[0] for desc in cur.description]
    results = cur.fetchall()
    conn.commit()

    df = pd.DataFrame(results, columns=colnames)
    parcels = []
    for parcel in df['geom']:
        geom = wkb.loads(parcel, hex=True)
        parcels.append(geom.simplify(tolerance=0.00055, preserve_topology=False))
    geom_df = pd.DataFrame()
    geom_df['Census Tract'] = df['tract_id']
    geom_df['geom'] = pd.Series(parcels)
    return geom_df


@st.experimental_memo(ttl=1200)
def static_data_all_table() -> pd.DataFrame:
    counties_df = all_counties_query()
    for table_name in STATIC_TABLES:
        table_output = static_data_single_table(table_name, STATIC_COLUMNS[table_name])
        counties_df = counties_df.merge(table_output)
    return counties_df


def output_data(df: pd.DataFrame, table_name: str = 'fred_tables', ext: str = 'xlsx') -> str:
    path = f'Output/{table_name}.{ext}'
    if ext == 'pk':
        df.to_pickle(path)
    elif ext == 'xlsx':
        df.to_excel(path)
    elif ext == 'csv':
        df.to_csv(path)
    else:
        print('Only .pk, .csv, and .xlsx outputs are currently supported.')
        sys.exit()
    return path


def fmr_data():
    conn = init_connection()
    cur = conn.cursor()
    cur.execute('SELECT state_full as "State", countyname as "County Name" FROM fair_market_rents;')
    colnames = [desc[0] for desc in cur.description]
    results = cur.fetchall()
    conn.commit()

    return pd.DataFrame(results, columns=colnames)


def filter_state(data: pd.DataFrame, state: str) -> pd.DataFrame:
    return data[data['State'].str.lower() == state.lower()]


def filter_counties(data: pd.DataFrame, counties: list) -> pd.DataFrame:
    counties = [_.lower() for _ in counties]
    return data[data['County Name'].str.lower().isin(counties)]


@st.experimental_memo(ttl=1200)
def load_all_data() -> pd.DataFrame:
    if os.path.exists("Output/all_tables.xlsx"):
        try:
            res = input('Previous data found. Use data from local `all_tables.xlsx`? [y/N]')
            if res.lower() == 'y' or res.lower() == 'yes':
                df = pd.read_excel('Output/all_tables.xlsx')
            else:
                df = get_all_county_data()
        except:
            print('Something went wrong with the Excel file. Falling back to database query.')
            df = get_all_county_data()
    else:
        df = get_all_county_data()

    return df


def clean_data(data: pd.DataFrame) -> pd.DataFrame:
    data.set_index(['State', 'County Name'], drop=True, inplace=True)

    # data.drop([
    #     'Burdened Households Date',
    #     'Income Inequality Date',
    #     'Population Below Poverty Line Date',
    #     'Single Parent Households Date',
    #     'Unemployment Rate Date',
    #     'Resident Population Date',
    #     'SNAP Benefits Recipients Date'
    # ], axis=1, inplace=True)

    data.rename({'Vulnerability Index': 'COVID Vulnerability Index'}, axis=1, inplace=True)

    data = data.loc[:, ~data.columns.str.contains('^Unnamed')]

    return data


def get_existing_policies(df: pd.DataFrame) -> pd.DataFrame:
    policy_df = policy_query()
    temp_df = df.merge(policy_df, on='county_id')
    if not temp_df.empty and len(df) == len(temp_df):
        if st._is_running_with_streamlit:
            if st.checkbox('Use existing policy data?'):
                return temp_df
        else:
            res = input('Policy data found in database. Use this data? [Y/n]').strip()
            if res.lower() == 'y' or res.lower() == 'yes' or res == '':
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


@st.experimental_memo(ttl=1200)
def get_county_data(state: str, counties: list = None, policy: bool = False):
    df = get_all_county_data(state, counties)

    df = clean_data(df)
    return df


@st.experimental_memo(ttl=3600)
def get_national_county_data() -> pd.DataFrame:
    frames = []
    for s in STATES:
        tmp_df = get_county_data(s)
        frames.append(tmp_df)
    df = pd.concat(frames)
    return df


@st.experimental_memo(ttl=3600)
def get_national_county_geom_data(counties: list) -> pd.DataFrame:
    frames = []
    for c in counties:
        tmp_df = get_county_geoms()
        frames.append(tmp_df)
    df = pd.concat(frames)
    return df


def test_new_counties():
    conn = init_connection()
    cur = conn.cursor()
    query = f"SELECT * FROM esri_counties;"
    cur.execute(query)
    results = cur.fetchall()
    conn.commit()
    colnames = [desc[0] for desc in cur.description]
    esri_df = pd.DataFrame(results, columns=colnames)

    query = f"SELECT * FROM id_index;"
    cur.execute(query)
    results = cur.fetchall()
    conn.commit()
    colnames = [desc[0] for desc in cur.description]
    idx_df = pd.DataFrame(results, columns=colnames)
    idx_df.drop(['index', 'tract_id', 'state_id', 'state_name'], axis=1, inplace=True)

    new_df = esri_df.copy()
    # new_df = new_df[['state_name', 'name', 'state_fips', 'fips', 'wkb_geometry', 'sqmi']]
    new_df.rename({"state_fips": "state_id"}, axis=1, inplace=True)
    new_df['county_id'] = new_df['fips'].astype(int)
    new_df.drop(['wkb_geometry', 'shape_area', 'shape_length', 'name'], inplace=True, axis=1)
    print(new_df.shape)
    print(new_df.head(n=200))

    # new_df.to_csv('Output/new_county_geoms.csv')
    # new_df.drop(['county_name'], axis=1, inplace=True)

    merge_df = pd.merge(new_df, idx_df, on='county_id', how='left', validate='one_to_many')
    merge_df.drop_duplicates(inplace=True)
    # merge_df.drop(['state_name_y','name'], axis=1, inplace=True)
    print(merge_df.shape)
    # col5, col6 = st.columns(2)
    # with col5:
    print(merge_df.head(n=150))
    merge_df.to_csv('Output/demographics.csv')
    # with col6:
    #     st.write(merge_df.tail(n=150))


if __name__ == '__main__':
    # latest_data_census_tracts('California', ['Contra Costa County'],
    #                           ['household_technology_availability', 'disability_status'])
    # args = {k: v for k, v in [i.split('=') for i in sys.argv[1:] if '=' in i]}
    # table = args.get('--table', None)
    # output_format = args.get('--output', None)
    #
    # if table:
    #     df = latest_data_single_table(table)
    # else:
    #     df = latest_data_all_tables()
    #
    # if output_format:
    #     if table:
    #         path = output_data(df, table_name=table, ext=output_format)
    #     else:
    #         path = output_data(df, ext=output_format)
    # else:
    #     if table:
    #         path = output_data(df, table_name=table)
    #     else:
    #         path = output_data(df)
    #
    # print('Successful query returned. Output at {}.'.format(path))
    test_new_counties()
    # df=pd.read_csv('Output/clean_counties.csv')
    # print('writing....')
    # write_table(df,'county_geoms')
    # df=pd.read_csv('Output/demographics.csv')
    # print('writing....')
    # write_table(df,'county_demographics')
