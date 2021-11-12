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

EQUITY_COUNTY_HEADERS = [
    'Age 19 or Under', 'Age 65 or Over', 
    'Non-White Population (%)'
    ]

CENSUS_HEADERS = [
    'People of Color (%)', 'Below Poverty Level (%)',
    'People with Disability (%)', 'Age 19 or Under (%)', 'Age 65 or Over (%)', 
    'Limited English Proficiency (%)', 'Single Parent Family (%)', 'Zero-Vehicle Household (%)'
]

EQUITY_CENSUS_POC_LOW_INCOME = [
    'People of Color', 'Below Poverty Level'
    ]

EQUITY_CENSUS_REMAINING_HEADERS = [
    'People with Disability', 'Age 19 or Under', 'Age 65 or Over', 
    'Limited English Proficiency', 'Single Parent Family', 'Zero-Vehicle Household'
    ]
    
TRANSPORT_CENSUS_HEADERS = [
    'percent_hh_0_veh', 'percent_hh_1_veh', 'percent_hh_2more_veh', 
    # 'person_miles_traveled', 'person_trips',  'vehicle_trips','urbanicity'
    'vehicle_miles_traveled',
    'walkability_index', 
    ]

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

EQUITY_CENSUS_TABLES = ['poverty_status',
                #  'resident_population_census_tract',
                 'sex_by_age',
                 'english_proficiency','household_vehicle_availability',
                'hispanic_or_latino_origin_by_race', 'disability_status',
                'family_type'
                ]

TRANSPORT_CENSUS_TABLES = ['household_vehicle_availability',
    'level_of_urbanicity',
    'trip_miles',
    'walkability_index']


@st.cache(allow_output_mutation=True, hash_funcs={"_thread.RLock": lambda _: None})
def init_engine():
    engine = create_engine(
        f'postgresql://{credentials.DB_USER}:{credentials.DB_PASSWORD}@{credentials.DB_HOST}:{credentials.DB_PORT}/{credentials.DB_NAME}')
    return engine


@st.cache(allow_output_mutation=True, hash_funcs={"_thread.RLock": lambda _: None})
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


def counties_query() -> pd.DataFrame:
    conn = init_connection()
    cur = conn.cursor()
    cur.execute(
        'SELECT id as county_id, state as "State", name as "County Name" '
        'FROM counties'
    )
    colnames = [desc[0] for desc in cur.description]
    results = cur.fetchall()
    conn.commit()

    return pd.DataFrame(results, columns=colnames)


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


@st.cache(ttl=1200, hash_funcs={"_thread.RLock": lambda _: None})
def latest_data_census_tracts(state: str, counties: list, tables: list) -> pd.DataFrame:
    conn = init_connection()
    cur = conn.cursor()
    tracts_df = census_tracts_geom_query(counties, state)
    counties_str = str(tuple(counties)).replace(',)', ')')
    where_clause = f"WHERE id_index.state_name ='{state}' AND id_index.county_name IN {counties_str}"

    for table_name in tables:
        cur.execute(f"""SELECT {table_name}.*, id_index.county_name, id_index.county_id, id_index.state_name, 
        resident_population_census_tract.tot_population_census_2010
            FROM {table_name} 
            INNER JOIN id_index ON {table_name}.tract_id = id_index.tract_id
            INNER JOIN resident_population_census_tract ON {table_name}.tract_id = resident_population_census_tract.tract_id
            {where_clause};""")
        results = cur.fetchall()
        conn.commit()

        colnames = [desc[0] for desc in cur.description]
        df = pd.DataFrame(results, columns=colnames)
        df['Census Tract'] = df['tract_id']
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
        counties_df = counties_query()
        df = counties_df.merge(df)
    return df


def latest_data_all_tables() -> pd.DataFrame:
    counties_df = counties_query()
    for table_name in FRED_TABLES:
        table_output = latest_data_single_table(table_name, require_counties=False)
        counties_df = counties_df.merge(table_output)
    chmura_df = static_data_single_table('chmura_economic_vulnerability_index', ['VulnerabilityIndex'])
    counties_df = counties_df.merge(chmura_df)
    demo_df = generic_select_query('socio_demographics',
                                   ['id', 'hse_units', 'vacant', 'renter_occ', 'med_age', 'white', 'black', 'ameri_es',
                                    'asian', 'hawn_pi', 'hispanic', 'other', 'mult_race', 'males', 'females',
                                    'population', 'age_under5', 'age_5_9', 'age_10_14', 'age_15_19', 'age_65_74',
                                    'age_75_84', 'age_85_up'])
    demo_df['Non-White Population'] = (demo_df['black'] + demo_df['ameri_es'] + demo_df['asian'] + demo_df[
        'hawn_pi'] + demo_df['hispanic'] + demo_df['other'] + demo_df['mult_race'])
    demo_df['Age 19 or Under'] = (demo_df['age_under5']+demo_df['age_5_9']+demo_df['age_10_14']+demo_df['age_15_19'])
    demo_df['Age 65 or Over'] = (demo_df['age_65_74']+demo_df['age_75_84']+demo_df['age_85_up'])
    demo_df['Non-White Population (%)'] = demo_df['Non-White Population'] / demo_df['population'] * 100
    demo_df.rename({
        'id': 'county_id',
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
        'females': 'Female Population'
    }, axis=1, inplace=True)

    demo_df.drop(['population', 'age_under5', 'age_5_9', 'age_10_14', 'age_15_19',
    'age_65_74','age_75_84','age_85_up'], axis=1, inplace=True)
    counties_df = counties_df.merge(demo_df)
    return counties_df


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
    counties_df = counties_query()
    df = counties_df.merge(df)
    return df


def generic_select_query(table_name: str, columns: list) -> pd.DataFrame:
    conn = init_connection()
    cur = conn.cursor()
    str_columns = ', '.join('"{}"'.format(c) for c in columns)
    query = 'SELECT {} FROM {} '.format(str_columns, table_name)
    cur.execute(query)
    results = cur.fetchall()
    conn.commit()

    colnames = [desc[0] for desc in cur.description]
    df = pd.DataFrame(results, columns=colnames)
    return df


@st.cache(ttl=1200, allow_output_mutation=True, hash_funcs={"_thread.RLock": lambda _: None})
def get_county_geoms(counties_list: list, state: str) -> pd.DataFrame:
    conn = init_connection()
    counties_list = [_.replace("'", "''") for _ in counties_list]
    counties = "(" + ",".join(["'" + str(_) + "'" for _ in counties_list]) + ")"
    cur = conn.cursor()
    query = f"SELECT * FROM counties_geom WHERE LOWER(state)='{state}' AND cnty_name in {counties};"
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
    geom_df['county_id'] = df['id']
    geom_df['County Name'] = df['cnty_name']
    geom_df['State'] = df['state']
    geom_df['geom'] = pd.Series(parcels)
    return geom_df


@st.cache(ttl=1200, allow_output_mutation=True, hash_funcs={"_thread.RLock": lambda _: None})
def get_county_geoms_by_id(counties_list: list) -> pd.DataFrame:
    conn = init_connection()
    counties = "(" + ",".join(["'" + str(_) + "'" for _ in counties_list]) + ")"
    cur = conn.cursor()
    query = f"SELECT * FROM counties_geom WHERE id in {counties};"
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
    geom_df['county_id'] = df['id']
    geom_df['County Name'] = df['cnty_name']
    geom_df['State'] = df['state']
    geom_df['geom'] = pd.Series(parcels)
    return geom_df


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


def static_data_all_table() -> pd.DataFrame:
    counties_df = counties_query()
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


def load_all_data() -> pd.DataFrame:
    if os.path.exists("Output/all_tables.xlsx"):
        try:
            res = input('Previous data found. Use data from local `all_tables.xlsx`? [y/N]')
            if res.lower() == 'y' or res.lower() == 'yes':
                df = pd.read_excel('Output/all_tables.xlsx')
            else:
                df = latest_data_all_tables()
        except:
            print('Something went wrong with the Excel file. Falling back to database query.')
            df = latest_data_all_tables()
    else:
        df = latest_data_all_tables()

    return df


def clean_data(data: pd.DataFrame) -> pd.DataFrame:
    data.set_index(['State', 'County Name'], drop=True, inplace=True)

    data.drop([
        'Burdened Households Date',
        'Income Inequality Date',
        'Population Below Poverty Line Date',
        'Single Parent Households Date',
        'Unemployment Rate Date',
        'Resident Population Date',
        'SNAP Benefits Recipients Date'
    ], axis=1, inplace=True)

    data.rename({'Vulnerability Index': 'COVID Vulnerability Index'}, axis=1, inplace=True)

    data = data.loc[:, ~data.columns.str.contains('^Unnamed')]

    return data

def clean_equity_data(data: pd.DataFrame) -> pd.DataFrame:
    data['Age 19 or Under'] = (
        data['female_under_5']+ data['female_5_to_9']+ data['female_10_to_14']+ 
        data['female_15_to_17']+ data['female_18_and_19']+
        data['male_under_5']+ data['male_5_to_9']+ data['male_10_to_14']+ 
        data['male_15_to_17']+ data['male_18_and_19']
        )
    data['Age 65 or Over'] = (
        data['female_65_and_66']+ data['female_67_to_69']+ data['female_70_to_74']+
        data['female_75_to_79']+ data['female_80_to_84']+ data['female_85_and_over']+
        data['male_65_and_66']+ data['male_67_to_69']+ data['male_70_to_74']+
        data['male_75_to_79']+ data['male_80_to_84']+ data['male_85_and_over']
        )

    data.rename({'below_pov_level': 'Below Poverty Level'}, axis=1, inplace=True)

    data['total_w_a_disability'] = (data['male_under_5_w_a_disability']+data['male_5_to_17_w_a_disability']+ data['male_18_to_34_w_a_disability']+
        data['male_35_to_64_w_a_disability']+data['male_65_to_74_w_a_disability']+data['male_75_and_over_w_a_disability']+
        data['female_under_5_w_a_disability']+data['female_5_to_17_w_a_disability']+ data['female_18_to_34_w_a_disability']+
        data['female_35_to_64_w_a_disability']+data['female_65_to_74_w_a_disability']+data['female_75_and_over_w_a_disability']
        )

    data['speak_eng_not_well'] = (data['foreign_speak_spanish_speak_eng_not_well']+ data['foreign_speak_spanish_speak_eng_not_at_all']+
        data['foreign_speak_other_indo-euro_speak_eng_not_well']+ data['foreign_speak_other_indo-euro_speak_eng_not_at_all']+
        data['foreign_speak_asian_or_pac_isl_lang_speak_eng_not_well']+ data['foreign_speak_asian_or_pac_isl_lang_speak_eng_not_at_all']+
        data['foreign_speak_other_speak_eng_not_well']+ data['foreign_speak_other_speak_eng_not_at_all']
        )

    data['single_parent'] = data['other_male_householder_no_spouse_w_kids'] + data['other_female_householder_no_spouse_w_kids']

    data['non-white'] = data['total_population'] - data['not_hisp_or_latino_white']

    data['People with Disability (%)'] = data['total_w_a_disability']/(data['male']+data['female'])
    data['Below Poverty Level (%)'] = data['Below Poverty Level']/data['population_for_whom_poverty_status_is_determined']
    data['Age 19 or Under (%)'] = data['Age 19 or Under']/data['total_population']
    data['Age 65 or Over (%)'] = data['Age 65 or Over']/data['total_population']
    data['Limited English Proficiency (%)'] = data['speak_eng_not_well']/(data['native']+data['foreign_born'])
    data['Single Parent Family (%)'] = data['single_parent']/data['total_families']
    data['Zero-Vehicle Household (%)'] = data['percent_hh_0_veh']
    data['People of Color (%)'] = data['non-white']/data['total_population']

    data['criteria_A'] = 0
    data['criteria_B'] = 0

    data['Criteria A'] = False
    data['Criteria B'] = False

    return data

def clean_transport_data(data: pd.DataFrame, epc: pd.DataFrame) -> pd.DataFrame:
    averages = {}
    epc_averages = {}
    for x in TRANSPORT_CENSUS_HEADERS:
        averages[x] = data[x].mean()
        epc_averages[x] = data.loc[data['tract_id'].isin(epc['tract_id'])][x].mean()
    transport_epc = data.loc[data['tract_id'].isin(epc['tract_id'])]

    return transport_epc, averages, epc_averages, data

def get_equity_geographies(epc: pd.DataFrame, coeff: float) -> pd.DataFrame:
    concentration_thresholds = dict()
    averages = dict()
    
    for header in (EQUITY_CENSUS_POC_LOW_INCOME + EQUITY_CENSUS_REMAINING_HEADERS):
        averages[header] = epc[header+ ' (%)'].mean()
        concentration_thresholds[header] = averages[header] + coeff*epc[header+ ' (%)'].std()
        epc[header+'_check'] = epc[header+' (%)'].apply(lambda x: x>concentration_thresholds[header])
        epc[header+'_check'] = epc[header+'_check'].astype(int)

    epc['criteria_A'] = epc[[x + '_check' for x in EQUITY_CENSUS_POC_LOW_INCOME]].sum(axis=1, numeric_only=True)
    epc['Criteria A'] = epc['criteria_A'].apply(lambda x: bool(x==2))

    epc['criteria_B'] = epc[[x + '_check' for x in EQUITY_CENSUS_REMAINING_HEADERS]].sum(axis=1, numeric_only=True)
    temp = epc['Below Poverty Level (%)'].apply(lambda x: x>concentration_thresholds['Below Poverty Level'])
    epc['Criteria B'] = (epc['criteria_B'].apply(lambda x: bool(x>=3)) + temp.astype(int)) == 2

    df = epc.drop_duplicates(subset=['tract_id'])

    epc['Criteria'] = epc[['Criteria A', 'Criteria B']].apply(lambda x: 'Both' if (x['Criteria A'] & x['Criteria B']) else 
        ('Criteria A Only' if x['Criteria A'] else
        ('Criteria B Only' if x['Criteria B'] else 'Other')), 
        axis=1)
    # epc['Criteria'] = epc.apply(lambda x: 'Both' if (x['Criteria A'] | x['Criteria B']) else 'Other')
    epc = epc.loc[(epc['Criteria A'] | epc['Criteria B'])]
    df['Census Tract'] = (df['Criteria A'].apply(lambda x: bool(x))|df['Criteria B'].apply(lambda x: bool(x)))
    df['Census Tract'] = df['Census Tract'].apply(lambda x: 'Equity Geography' if x is True else 'Other')

    epc_averages = {}
    for header in (EQUITY_CENSUS_POC_LOW_INCOME + EQUITY_CENSUS_REMAINING_HEADERS):
        epc_averages[header] = epc[header + ' (%)'].mean()

    return epc, df, concentration_thresholds, averages, epc_averages

def get_county_level_data (df: pd.DataFrame) -> pd.DataFrame:
    county_df = None
    
    for header in (EQUITY_CENSUS_POC_LOW_INCOME + EQUITY_CENSUS_REMAINING_HEADERS):
        county_df['average', header] = df[header].mean()
    
    return county_df

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


@st.cache(ttl=1200, allow_output_mutation=True, hash_funcs={"_thread.RLock": lambda _: None})
def get_county_data(state: str, counties: list = None, policy: bool = False):
    df = load_all_data()
    df = filter_state(df, state)
    if counties is not None:
        df = filter_counties(df, counties)
    if policy:
        df = get_existing_policies(df)
    df = clean_data(df)
    return df


@st.cache(ttl=3600, hash_funcs={"_thread.RLock": lambda _: None})
def get_national_county_data() -> pd.DataFrame:
    frames = []
    for s in STATES:
        tmp_df = get_county_data(s)
        frames.append(tmp_df)
    df = pd.concat(frames)
    return df

@st.cache(ttl=3600, hash_funcs={"_thread.RLock": lambda _: None})
def get_national_county_geom_data(counties: list) ->pd.DataFrame:
    frames = []
    for c in counties:
        tmp_df = get_county_geoms()
        frames.append(tmp_df)
    df = pd.concat(frames)
    return df

if __name__ == '__main__':
    latest_data_census_tracts('California', ['Contra Costa County'],
                              ['household_technology_availability', 'disability_status'])
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
