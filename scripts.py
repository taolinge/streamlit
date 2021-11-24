import queries
import pandas as pd
import geopandas as gpd
from sqlalchemy import create_engine
import psycopg2
import credentials


# engine = create_engine(f'postgresql+psycopg2://postgres:Password@localhost:5432/test_counties')

def init_engine():
    engine = create_engine(
        f'postgresql://{credentials.DB_USER}:{credentials.DB_PASSWORD}@{credentials.DB_HOST}:{credentials.DB_PORT}/{credentials.DB_NAME}')
    return engine


def fix_chmura_counties():
    counties = queries.all_counties_query()
    counties.set_index(['State', 'County Name'], inplace=True)
    ch_df = queries.generic_select_query('chmura_economic_vulnerability_index',
                                         ['fips', 'name', 'VulnerabilityIndex', 'Rank', 'state', 'county_id'])
    for i, row in ch_df.iterrows():
        if pd.isnull(row['county_id']):
            try:
                ch_df.at[i, 'county_id'] = counties.loc[row['state'], row['name']]['county_id']
            except KeyError:
                print(row['state'], row['name'])

    queries.write_table(ch_df, 'chmura_economic_vulnerability_index')


def populate_table(path: str, name: str):
    engine = init_engine()
    df = pd.read_csv(path)
    df.drop(['tract'], inplace=True, axis=1)
    df.replace('N', None, inplace=True)
    # print(df.columns)
    # print(df.tail())

    df.to_sql(name, engine, if_exists='replace', method='multi', index=False)


def import_geojson():
    gdf = gpd.read_file('temp/USA_Counties.geojson', rows=2)
    gdf['geometry'].apply(lambda x: print(type(x)))


FRED_TABLES = [
    # 'burdened_households',
    # 'homeownership_rate',
    # 'income_inequality',
    # 'population_below_poverty',
    # 'resident_population',
    # 'single_parent_households',
    # 'snap_benefits_recipients',
    # 'unemployment_rate',
    'fair_market_rents',
    'median_rents'
]


def update_FRED():
    engine = init_engine()
    ch_df = queries.read_table('chmura_economic_vulnerability_index')
    keep_cols = {'date', 'value', 'fips', 'state_name', 'county_name','rent50_0', 'rent50_1',
       'rent50_2', 'rent50_3', 'rent50_4', 'pop2017', 'hu2017','fmr_0', 'fmr_1', 'fmr_2',
       'fmr_3', 'fmr_4', 'pop2017', 'fmr_pct_chg', 'fmr_dollar_chg'}
    big_df=pd.DataFrame()
    frames=[]
    for table in FRED_TABLES:
        df = queries.read_table(table)
        df = df.merge(ch_df, on='county_id')
        print(df.columns)
        drop_cols = list(set(df.columns) - keep_cols)
        df.drop(drop_cols, axis=1, inplace=True)
        df.replace('.',None, inplace=True)
        df.rename({"value": table, 'fips': 'county_id'}, axis=1, inplace=True)
        # df.to_csv('temp/temp.csv')
        df.to_sql(f"{table}_new", engine, if_exists='replace', method='multi', index=False)
        print(df.head())


if __name__ == '__main__':
    # fix_chmura_counties()
    # populate_table('temp/commuting_characteristics.csv', 'commuting_characteristics')
    # import_geojson()
    update_FRED()
    pass
