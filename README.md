# Arup Social Data
[![Streamlit App](https://static.streamlit.io/badges/streamlit_badge_black_white.svg)](https://share.streamlit.io/arup-group/eviction-data/run.py)

This is a repository for collection and analysis of open social data. This type of data can be useful to planners, NGO's, governments, firms, and anyone trying to address social problems through data.

The bulk of the analysis is related to evictions as a result of COVID-19. This repository gathers data from the Federal Reserve Economic Data portal (FRED). There are a number of potential use cases we're aware of to apply that data to address evictions. This analysis allows us to compare counties side by side by their "Relative Risk" of evictions.

## No code, no problem
Not a developer? Just don't want to code today? No problem! You can test drive our web app at the link below.

https://share.streamlit.io/arup-group/eviction-data/run.py

## Usage
This repository currently two primary workflows:

1. Gathering data for counties in the US and comparing their Relative Risk of eviction
2. Viewing and examing the data in the database and downloading raw data for your own analysis

These workflows support a number of use cases, including:
- Providing direct assistance to families in one or more counties
- Driving decisions around future affordable housing projects
- Directing policy response on the city or county level

There are three ways to interact with this data.
- Web interface - You can use the interactive UI either on the web or run locally
- Python scripts - Include functions to gather, clean, and analyze data to output a relative risk ranking for multiple counties. Can be extended with your own scripts. 
- Custom SQL Queries - SQL that you write to get the most recent data from our database and use however you want. 

### About the data
This data is the most recent data we could get, but some datasets are updated more frequently than others. You can see the date that the data was updated in `all_tables.xlsx`. We refresh the data monthly on the first of the month. All datasets are at the county level. The following datasets are currently in the database:

| Feature Name | Source | Updated | Notes | 
| ------------ | ------ | ------- | ----- |
| Burdened Households (%) | [FRED](https://fred.stlouisfed.org/) | 1/1/2018 | People who pay more than 30 percent of their income towards rent |
| Home Ownership (%) | [FRED](https://fred.stlouisfed.org/) | 1/1/2018 | This field has been superseded by the renter occupied housing units value from the demographic data. |
| Income Inequality (Ratio) | [FRED](https://fred.stlouisfed.org/) | 1/1/2018 | |
| Population Below Poverty Line (%) | [FRED](https://fred.stlouisfed.org/) | 1/1/2018 | |
| Single Parent Households (%) | [FRED](https://fred.stlouisfed.org/) | 1/1/2018 | |
| SNAP Benefits Recipients (Persons) | [FRED](https://fred.stlouisfed.org/) | 1/1/2017 | This field is no longer used in our analysis, but exists in the database. |
| Unemployment Rate (%) | [FRED](https://fred.stlouisfed.org/) | 6/1/2020 | |
| Resident Population (Thousands of Persons) | [FRED](https://fred.stlouisfed.org/) | 1/1/2019 | Used to convert percentages to raw population|
| COVID Vulnerability Index | [CHMURA](http://www.chmuraecon.com/interactive/covid-19-economic-vulnerability-index/) | 4/15/2020 | An index from CHMURA to represent how vulnerable counties across the US are to COVID-related economic effects. |
| Fair Market Rents | [HUD](https://www.huduser.gov/portal/datasets/fmr.html#2021_data) | 10/1/2020 | Represents the estimated amount (base rent + essential utilities) that a property in a given area typically rents for|
| Median Rents | [HUD](https://www.huduser.gov/PORTAL/datasets/50per.html) | 2021 | Rent estimates at the 50th percentile (or median)  calculated for all Fair Market Rent areas|
| Housing Stock Distributions | [US Census](https://www.census.gov/programs-surveys/ahs/data/interactive/ahstablecreator.html?s_areas=00000&s_year=2017&s_tablename=TABLE2&s_bygroup1=1&s_bygroup2=1&s_filtergroup1=1&s_filtergroup2=1) | 2017 | Distribution of housing units in the US by number of bedrooms. Defaults to the national distribution, but includes data for the top 15 metro areas in the US. Includes percentage and estimated housing units. |
| County Geometries | [US Census](https://catalog.data.gov/dataset/tiger-line-shapefile-2017-nation-u-s-current-county-and-equivalent-national-shapefile) | 2017 | PostGIS compatible geometry data |
| Demographics | [ArcGIS](https://hub.arcgis.com/datasets/48f9af87daa241c4b267c5931ad3b226_0) | 2017 | We currently pull in a number of fields here including each race & ethnicity break down, the count of males and females, median age, the number of housing units, vacant units, and renter occupied units. |

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

### Outputs
These are the columns that appear in our output for Eviction Analysis and in our raw data. Units can vary between raw and outputted data as we transform percentages in to raw population estimates. In our ranking, values in each column are all normalized.

- county_id: Unique ID for each county
- Income Inequality (Ratio): The income earned by the top percentage of households and dividing that by the income earned by the poorest percentage of households.
- Resident Population (Thousands of Persons): Number of persons in a county 
- VulnerabilityIndex: COVID Vulnerability Index, as defined by CHMURA
- Housing Units: Total number of housing units in a county
- Vacant Units: Number of vacant housing units in a county
- Renter Occupied Units: Number of  housing units in a county occupied by renters. This is used in eviction analysis workflows.
- Median Age: Median age of the county population
- Burdened Households: Number People who pay more than 30 percent of their income towards rent
- Population Below Poverty Line: Population living below the minimum level of income deemed adequate in a particular county 
- Single Parent Households: Number of households with a single parent
- Unemployed Population: Number of people unemployed in a county
- [Race/Ethnicity] Population: Number of people by reported race/ethnicity in a county
- Non-White Population/Percentage: The total number of people in a county who did not report as white. The percentage represents the proportion of historically minority groups in a county. 
- Males/Females: Number of reported Males and Females in a population. (Note: there is no value for non-binary reporting in the existing ACS dataset)
- rent_50_[0-4]: Median Rent value for a 0 bedroom house to a 4 bedroom house
- fmr_[0-4]: Fair Market Rent value for a 0 bedroom house to a 4 bedroom house
- [0-4]_br_cost_5: Cost of preventing evictions for a 0-4 bedroom house for 5% of burdened households
- [0-4]_br_cost_25: Cost of preventing evictions for a 0-4 bedroom house for 25% of burdened households
- [0-4]_br_cost_33: Cost of preventing evictions for a 0-4 bedroom house for 33% of burdened households
- [0-4]_br_cost_50: Cost of preventing evictions for a 0-4 bedroom house for 50% of burdened households
- [0-4]_br_cost_75: Cost of preventing evictions for a 0-4 bedroom house for 75% of burdened households

To calculate the total cost of evictions for a single month, simply add the costs for each housing type for a particular proportion.  

## Python Users
We've done our previous analyses in Python, and have built data gathering, cleaning, and analysis functions.

### Install
In a virtual environment:

`pip install -r requirements.txt`

### Run
We suggest running using Streamlit for most use cases:

`streamlit run run.py`

To run as a typical Python script, run:

`python run.py --mode script`

The `credentials.py` file is configured to allow read-only access to an Arup-maintained database of the most recent relevant FRED data. In addition to using these Python scripts, you can connect to this database and run direct SQL queries to get the data you want.

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

## Database Users
The PostgreSQL database that this repository uses is open for *read-only* access. The connection details are stored in `credentials.py` if you're using the Python workflow.

If you'd like to query the database directly using the method of your choice, you can access it using the credentials below:

```
DB_HOST = ade-eviction.ccgup3bgyakw.us-east-1.rds.amazonaws.com
DB_NAME = eviction_data
DB_PORT = 5432
DB_USER = readuser
DB_PASSWORD = password
```

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
If there are data sources you'd like to see included in this, please reach out through the Issues tab. We are aware of a few blind spots in our current data, including the existing state of homelessness in a county and the county demographics. We are also interested in getting data beyond the county level. 

## License
This repository and the underlying data is [MIT licensed](LICENSE).
