import queries
import pandas as pd
import geopandas as gpd
from sqlalchemy import create_engine
import psycopg2

# engine = create_engine(f'postgresql+psycopg2://postgres:iHCDlGesnQZ99QZiERiY@ade-eviction.ccgup3bgyakw.us-east-1.rds.amazonaws.com:5432/eviction_data')
engine = create_engine(f'postgresql+psycopg2://postgres:Password@localhost:5432/test_counties')


def fix_chmura_counties():
    counties = queries.counties_query()
    counties.set_index(['State', 'County Name'], inplace=True)
    ch_df = queries.generic_select_query('chmura_economic_vulnerability_index',
                                         ['fips', 'name', 'VulnerabilityIndex', 'Rank', 'state', 'county_id'])
    print(ch_df.shape)
    for i, row in ch_df.iterrows():
        if pd.isnull(row['county_id']):
            try:
                ch_df.at[i, 'county_id'] = counties.loc[row['state'], row['name']]['county_id']
            except KeyError:
                print(row['state'], row['name'])
        # print(ch_df.loc[row['state'],row['name']])
    print(ch_df.shape)
    print(ch_df.head())
    queries.write_table(ch_df, 'chmura_economic_vulnerability_index')
    return


def populate_table(path: str, name: str):
    df = pd.read_csv(path)
    df.drop(['index'], inplace=True, axis=1)
    df.to_sql(name, engine, if_exists='replace', method='multi', index=False)
    print(df.head())


def import_geojson():
    gdf=gpd.read_file('temp/USA_Counties.geojson', rows=2)
    gdf['geometry'].apply(lambda x: print(type(x)))
    # print(gdf.head())




if __name__ == '__main__':
    # fix_chmura_counties()
    # populate_table('temp/household_job_availability.csv', 'household_job_availability_new')
    import_geojson()