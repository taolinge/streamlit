# Arup Social Data
[![Streamlit App](https://static.streamlit.io/badges/streamlit_badge_black_white.svg)](https://share.streamlit.io/arup-group/social-data/run.py)

This is a repository for collection and analysis of open social data. This type of data can be useful to planners, NGO's, governments, firms, and anyone trying to address social problems through data.

The bulk of the analysis is related to evictions as a result of COVID-19. This repository gathers data from the Federal Reserve Economic Data portal (FRED). There are a number of potential use cases we're aware of to apply that data to address evictions. This analysis allows us to compare counties side by side by their "Relative Risk" of evictions.

## No code, no problem
Not a developer? Just don't want to code today? No problem! You can access the data using our web app at the link below.

[https://share.streamlit.io/arup-group/social-data/run.py](https://share.streamlit.io/arup-group/social-data/run.py)

## Python Usage
We've done our previous analyses in Python, and have built data gathering, cleaning, and analysis functions.

The `credentials.py` file is configured to allow read-only access to an Arup-maintained database of the most recent relevant FRED data. In addition to using these Python scripts, you can connect to this database and run direct SQL queries to get the data you want.


### Install
This project relies on GDAL for geospatial things, which means you'll need to install GDAL on your machine (sorry, Windows people). 

Mac users (using homebrew):

`brew install gdal`

Windows users (based on [this](https://sandbox.idre.ucla.edu/sandbox/tutorials/installing-gdal-for-windows)):

1. [Get and install](https://www.gisinternals.com/release.php) appropriate binary for your machine
2. Add PATH and environment variables like in [this article](https://jingwen-z.github.io/how-to-install-python-module-fiona-on-windows-os/)
3. Install [Visual C++ Build Tools](https://visualstudio.microsoft.com/downloads/#build-tools-for-visual-studio-2019) if you haven't already
4. Install Fiona from the appropriate whl file [here](https://www.lfd.uci.edu/~gohlke/pythonlibs/#fiona)
5. In your virtual environment: `pip install <path/to/fiona.whl>`


In a virtual environment:

`pip install -r requirements.txt`

### Run
We suggest running using Streamlit for most use cases:

`streamlit run run.py`

To run as a typical Python script, run:

`python run.py --mode script`

### Docker
You can also install and run the application locally using Docker:

`docker build . -t streamlit-social-data`

`docker-compose up -d`

You can access the app on `http://localhost:8501`.

## Database Usage
The PostgreSQL database that this repository uses is open for *read-only* access. The connection details are stored in `credentials.py` if you're using the Python workflow.

If you'd like to query the database directly using the method of your choice, you can access it using the credentials below:

```
DB_HOST = ade-eviction.ccgup3bgyakw.us-east-1.rds.amazonaws.com
DB_NAME = eviction_data
DB_PORT = 5432
DB_USER = readuser
DB_PASSWORD = password
```

## Workflows
This repository currently two primary workflows:

1. Viewing and examining the data in the database and downloading raw data for your own analysis
2. Gathering data for counties in the US and comparing their Relative Risk of eviction

Currently we support census tract level data for the Data Exploration workflow

These workflows support a number of use cases, including:
- Providing direct assistance to families in one or more counties
- Driving decisions around future affordable housing projects
- Directing policy response on the city or county level

There are three ways to interact with this data.
- Web interface - You can use the interactive UI either on the web or run locally
- Python scripts - Include functions to gather, clean, and analyze data to output a relative risk ranking for multiple counties. Can be extended with your own scripts. 
- Custom SQL Queries - SQL that you write to get the most recent data from our database and use however you want. 

## About the data
We currently have almost 40 tables in the database, representing over 2 million rows of data.

This data is the most recent data we could get, but some datasets are updated more frequently than others. You can see the date that the data was updated in `all_tables.xlsx`. We refresh the data monthly on the first of the month. Some datasets are at the county level and some are at the census tract level. The following datasets are currently in the database:

| Feature Name | Resolution | Source | Updated | Notes | 
| ------------ | ---------- | ------ | ------- | ----- |
| ID Index | All | -- | 2021 | Arup-developed index of State, County, and Census tract IDs to query between tables |
| Burdened Households (%) | County | [FRED](https://fred.stlouisfed.org/) | 1/1/2018 | People who pay more than 30 percent of their income towards rent |
| Home Ownership (%) | County | [FRED](https://fred.stlouisfed.org/) | 1/1/2018 | This field has been superseded by the renter occupied housing units value from the demographic data. |
| Income Inequality (Ratio) | County | [FRED](https://fred.stlouisfed.org/) | 1/1/2018 | |
| Population Below Poverty Line (%) | County | [FRED](https://fred.stlouisfed.org/) | 1/1/2018 | |
| Single Parent Households (%) | County | [FRED](https://fred.stlouisfed.org/) | 1/1/2018 | |
| SNAP Benefits Recipients (Persons) | County | [FRED](https://fred.stlouisfed.org/) | 1/1/2017 | This field is no longer used in our analysis, but exists in the database. |
| Unemployment Rate (%) | County | [FRED](https://fred.stlouisfed.org/) | 6/1/2020 | |
| Resident Population (Thousands of Persons) | County | [FRED](https://fred.stlouisfed.org/) | 1/1/2019 | Used to convert percentages to raw population|
| Resident Population | Census Tract | [ACS](https://www.census.gov/programs-surveys/acs) | 2019 | |
| COVID Vulnerability Index | County | [CHMURA](http://www.chmuraecon.com/interactive/covid-19-economic-vulnerability-index/) | 4/15/2020 | An index from CHMURA to represent how vulnerable counties across the US are to COVID-related economic effects. |
| Fair Market Rents | County | [HUD](https://www.huduser.gov/portal/datasets/fmr.html#2021_data) | 10/1/2020 | Represents the estimated amount (base rent + essential utilities) that a property in a given area typically rents for|
| Median Rents | County | [HUD](https://www.huduser.gov/PORTAL/datasets/50per.html) | 2021 | Rent estimates at the 50th percentile (or median)  calculated for all Fair Market Rent areas|
| Housing Stock Distributions | County | [US Census](https://www.census.gov/programs-surveys/ahs/data/interactive/ahstablecreator.html?s_areas=00000&s_year=2017&s_tablename=TABLE2&s_bygroup1=1&s_bygroup2=1&s_filtergroup1=1&s_filtergroup2=1) | 2017 | Distribution of housing units in the US by number of bedrooms. Defaults to the national distribution, but includes data for the top 15 metro areas in the US. Includes percentage and estimated housing units. |
| County Geometries | County | [US Census](https://catalog.data.gov/dataset/tiger-line-shapefile-2017-nation-u-s-current-county-and-equivalent-national-shapefile) | 2017 | PostGIS compatible geometry data |
| Socio-Demographics | County | [ArcGIS](https://hub.arcgis.com/datasets/48f9af87daa241c4b267c5931ad3b226_0) | 2017 | A collection of fields including each race & ethnicity break down, the count of males and females, median age, the number of housing units, vacant units, renter occupied units, and more. |
| Census Tract Geometries | Census Tracts | -- | 2010 | |
| English Proficiency | Census Tracts | [ACS](https://www.census.gov/programs-surveys/acs) | 2019 | Used to find percent of population with Limited English Proficiency |
| Group Quarters Population | Census Tracts | [ACS](https://www.census.gov/programs-surveys/acs) | 2019 | |
| Housing Units in Structure | Census Tracts | [ACS](https://www.census.gov/programs-surveys/acs) | 2019 | Used to find percent that are Renter Occupied Units |
| Occupants per Bedroom | Census Tracts | [ACS](https://www.census.gov/programs-surveys/acs) | 2019 | |
| Median Household Income | Census Tracts | [ACS](https://www.census.gov/programs-surveys/acs) | 2019 | |
| Employment Status | Census Tracts | [ACS](https://www.census.gov/programs-surveys/acs) | 2019 | |
| Per Capita Income | Census Tracts | [ACS](https://www.census.gov/programs-surveys/acs) | 2019 | |
| Disability Status | Census Tracts | [ACS](https://www.census.gov/programs-surveys/acs) | 2019 | Used to find percent of population with People with Disability |
| Poverty Status | Census Tracts | [ACS](https://www.census.gov/programs-surveys/acs) | 2019 | Used to find percent of population 200% Below Poverty Line |
| Family Type | Census Tracts | [ACS](https://www.census.gov/programs-surveys/acs) | 2019 | Used to find percent of population with Single Parent Families |
| Educational Attainment | Census Tracts | [ACS](https://www.census.gov/programs-surveys/acs) | 2019 | |
| Hispanic or Latino Origin by Race | Census Tracts | [ACS](https://www.census.gov/programs-surveys/acs) | 2019 | Used to find percent of population that are People of Color |
| Sex by Age | Census Tracts | [ACS](https://www.census.gov/programs-surveys/acs) | 2019 | Used to find percent of population Aged 65 and Over and Aged 19 and Under |
| Sex of Workers by Vehicles Available | Census Tracts | [ACS](https://www.census.gov/programs-surveys/acs) | 2019 | |
| Commuting Characteristics by Sex | Census Tracts | [ACS](https://www.census.gov/programs-surveys/acs) | 2019 | Used to find percent that are Drive Alone Commuters |
| Household Job Availability | Census Tracts | [ACS](https://www.census.gov/programs-surveys/acs) | 2013 | |
| Household Technology Availability | Census Tracts | [ACS](https://www.census.gov/programs-surveys/acs)| 2013 | Used to find percent that are No Computer Households |
| Household Vehicle Availability | Census Tracts | [ACS](https://www.census.gov/programs-surveys/acs)| 2013 | Used to find percent of population in Zero-Vehicle Households |
| National Walkability Index | Census Tracts | [EPA](https://www.epa.gov/smartgrowth/smart-location-mapping#SLD) | 2012 | |
| Trip Miles | Census Tracts | [BTS](https://www.bts.gov/latch/latch-data) | 2013 | Used to find average Vehicle Miles Traveled |
| Level of Urbanicity | Census Tracts | [EPA](https://www.epa.gov/smartgrowth/smart-location-mapping#SLD) | 2013 | |


If you have datasets you'd like to see included, please create an Issue.
 
 
### What is Relative Risk?
Relative risk is an index used to compare counties against each other in our Python analysis. It is _not_ a measure of absolute or percentage risk and has no meaning outside of this analysis. We use this to compare counties to understand where people are more at risk of eviction. 

We calculate this using a custom formula to balance socioeconomic factors with the policy response of a city. There are three parts of this formula: a *socioeconomic index* value calculated from the combination of normalized FRED data and other data sources in the table above, a *policy index* value found using the policy Excel sheet in this repository and using methodology adapted from EvictionLab, and the *time remaining* until protections end. The equation is

`relative_risk = socioeconomic_index * (1 - policy_index) / sqrt(time_remaining)`

In this equation, we aim to minimize socioeconomic risk on the top of the fraction, maximize the policy response value and take 1 minus the index value calculated (to represent that better policy constitutes less relative risk), and maximize the time remaining on the bottom of the fraction. The square root of the time remaining is used to represent how additional time has diminishing returns. For example, the different between having 2 days and 2 weeks until protections expire is much different than whether policies expire in 3 months or 4 months when we think about how to prioritize one county over another.   

### What is cost of evictions?

To calculate the cost to avoid evictions the following calcuation was used:

`(burdened_household_proportion / 100) * county_rent * housing_stock_distribution percentage * population * (burdened_households_proportion / 100)`

Housing stock distributions (US Census) were used to evaluate the types of houses that exist in the United States (e.g. studio, one bedroom, etc.).  Burdened household proportions were decided by Arup and were used to determine what percentage of people were most at risk.  Proportions were set at 5, 25, 33, 50, and 75 to represent that not all burdened households will face eviction, and we don't know how many actually will.  With the chosen proportion values, we are representing a general range, knowing there isn't a case where nobody will be evicted, or a case where everybody will be evicted.  These numbers can be adjusted based on the user's knowledge of their own county. County rents for each housing stock were sourced from HUD, and used Fair Market Rates to determine rent prices for each stock.  Fair Market Rents (FMRs) represent the estimated amount (base rent + essential utilities) that a property in a given area typically rents for. Burdened households was a percentage calculated by FRED which gives the percentage of the population who pay more than 30% of their income on rent.  Population data was pulled from HUD and represents the population by county in the year 2017. 

Performing this calculation for each proportion and each housing stock will calculate the amount needed to prevent eviction for each proportion.  The total cost of evictions for a particular county for one month was calcuated by summing each housing stock.  To get the cost of prevention for more than one month, the sum was multiplied by the number of months of interest. 

This script uses Fair Market Rent values.  Median rent values are also available in the database.  The script can be manually adjusted by the user to reference median rent values rather than fair market rent if they choose.  

Upon script completion, an excel file will be created within the output folder displaying all values mentioned above.  If you experience problems with the script or have questions about methodologies, please reach out to a member of the development team.  

### How are Equity Geographies identified?
"Equity Geographies" are census tracts that have a significicant concentration of underserved populations, such as households with low incomes and people of color. By identifying historically underserved communities, planning and funding can be targeted to enable more equitable access to transportation. 

Equity Geographies must meet at least one of the following 2 criteria. This methodology is based on the equity priority community [methodology](https://bayareametro.github.io/Spatial-Analysis-Mapping-Projects/Project-Documentation/Equity-Priority-Communities/#summary-of-mtc-epc-demographic-factors--demographic-factor-definitions) developed by the San Francisco Bay Area Metropolitan Transportation Commission (MTC).       
    A) Census tracts have a concentration of BOTH people of color AND low-income households
    B) Census tracts have a concentration of three or more of the remaining six equity indicators AND a concentration of low-income households

All of the equity indicators considered in the analysis are here:
    1) People of Color
    2) 200% Below Poverty Level
    3) People with Disability
    4) Age 19 or Under
    5) Age 65 of Over
    6) Limited English Proficiency
    7) Single Parent Family
    8) Zero Vehicle Household

Equity geographies are compared against concentration thresholds as defined below. The coefficient value varies on user input. 
    `concentration threshold = average + (standard deviation * coefficient)`

### How is the Transportation Vulnerability Index created?
First, values for each of the indicators are normalized across the entire region. The script uses preprocessing.MinMaxScaler() to normalize values. Index values are the sume of the normalized values times the corresponding weights of each selected indicator. 

### FRED Queries
You can get the most recent Federal Reserve Economic Data (FRED) using the following commands:

`python -m queries`

#### Flags

| Flag | Purpose |
|------|---------|
| `--table`| Specifies a table that you want to query. If none is given, will return all tables.|
| `--ouput`| Specifies an output type, without a ".". Currently, only `pk` or `xlsx` are supported. `pk` returns a pickled `pandas.DataFrame`. If none is given, will default to `xlsx`.|

#### Purpose

This command will query the eviction data database, and return data in an `Output` folder. If no folder exists, will be created by the `queries.py` script.

### Policy Workbook
Included in this repository is a template Excel file for policy data. This file is referenced in the Python scripts. There are three pages to be aware of.

#### Policy Timeline
This page is used to keep track of time-dependent policies and generate a "countdown clock" for a county. You can add policies and their expirations to end up with a date where people lose protections. You can also color the cells on this page to show where different policies overlap and how their expirations line up visually.  

#### Policy Ranking
This page is used to collect and represent the specific policy nuanced not captured by the timeline. For each county, enter a `1` in each cell where a policy applies. These values are weighted according the methodology used by EvictionLab (with a couple minor modifications) to get an index score for each county.

#### Analysis Data
This page collects the results from the previous two pages in a format that can be more easily read by the Python scripts. You may need to copy the countdown and policy index values for each county you're analyzing. 


## Contributing
We would love for you to use this code, build on it, and share with others. See [our contribution guide](CONTRIBUTING.md) and [code of conduct](CODE_OF_CONDUCT.md)  for more information.

### Issues
Please post bugs, errors, and questions to the Issues tab of this repository.

### Code
Make a pull request with your feature or bug fixes and we will review it. You're free to merge once it's been approved.

### Policy Data
Policy data is some of the most useful, but also the hardest to get. We've shared policies for a number of counties we've analyzed in the Bay Area and Tulsa area. We hope that as you do policy analysis for your area, you'll contribute that back so others can use and verify it. 

For now, to submit your data, open an issue in this repository and submit your policy data (countdown and/or policy ranking) for the county or counties you're looking at. 

### Other Data Sources
If there are data sources you'd like to see included in this, please reach out through the Issues tab.

## License
This repository and the underlying data is [MIT licensed](LICENSE).
