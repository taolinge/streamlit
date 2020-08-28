# Arup Eviction Data
This is a repository for analysis on open data related to evictions as a result of COVID-19. This repository gathers data from the Federal Reserve Economic Data portal (FRED). There are a number of potential use cases we're aware of to apply that data to address evictions. 

The analysis we do now allows us compare counties side by side by their "Relative Risk" of evictions.

## Usage
This repository currently supports three primary workflows:

1. Gathering data for a single county in a state
2. Gathering and comparing data for multiple counties using a Relative Risk index
3. Gathering data for all counties in a state and comparing using a Relative Risk index

These workflows support a number of use cases, including:
- Providing direct assistance to families in one or more counties
- Driving decisions around future affordable housing projects
- Directing policy response on the city or county level

There are two ways to interact with this data.
- Python scripts - Include functions to gather, clean, and analyze data to output a relative risk ranking for multiple counties. Can be extended with your own scripts. 
- Custom SQL Queries - SQL that you write to get the most recent data from our database and use however you want. 

### About the data
This data is the most recent data we could get, but some datasets are updated more frequently than others. You can see the date that the data was updated in `all_tables.xlsx`. We refresh the data monthly on the first of the month. All datasets are at the county level. The following datasets are currently in the database:

| Feature Name | Source | Updated | Notes | 
| ------------ | ------ | ------- | ----- |
| Burdened Households (%) | [FRED](https://fred.stlouisfed.org/) | 1/1/2018 | People who pay more than 30 percent of their income towards rent |
| Home Ownership (%) | [FRED](https://fred.stlouisfed.org/) | 1/1/2018 | Inverted to non-homeowners in analysis to get renters |
| Income Inequality (Ratio) | [FRED](https://fred.stlouisfed.org/) | 1/1/2018 | |
| Population Below Poverty Line (%) | [FRED](https://fred.stlouisfed.org/) | 1/1/2018 | |
| Single Parent Households (%) | [FRED](https://fred.stlouisfed.org/) | 1/1/2018 | |
| SNAP Benefits Recipients (Persons) | [FRED](https://fred.stlouisfed.org/) | 1/1/2017 | |
| Unemployment Rate (%) | [FRED](https://fred.stlouisfed.org/) | 6/1/2020 | |
| Resident Population (Thousands of Persons) | [FRED](https://fred.stlouisfed.org/) | 1/1/2019 | Used to convert percentages to raw population|
| COVID Vulnerability Index | [CHMURA](http://www.chmuraecon.com/interactive/covid-19-economic-vulnerability-index/) | 4/15/2020 | |
| Fair Market Rents | [HUD](https://www.huduser.gov/portal/datasets/fmr.html#2021_data) | 10/1/2020 | Represents the estimated amount (base rent + essential utilities) that a property in a given area typically rents for|
| Median Rents | [HUD](https://www.huduser.gov/PORTAL/datasets/50per.html) | 2021 | Rent estimates at the 50th percentile (or median)  calculated for all Fair Market Rent areas|
| Housing Stock Distributions | [US Census](https://www.census.gov/programs-surveys/ahs/data/interactive/ahstablecreator.html?s_areas=00000&s_year=2017&s_tablename=TABLE2&s_bygroup1=1&s_bygroup2=1&s_filtergroup1=1&s_filtergroup2=1) | 2017 | Distribution of housing units in the US by number of bedrooms |
If you have datasets you'd like to see included, please create an Issue.
 
 
### What is Relative Risk?
Relative risk is an index used to compare counties against each other in our Python analysis. It is _not_ a measure of absolute or percentage risk and has no meaning outside of this analysis. We use this compare counties to understand where people are more at risk of eviction. 

We calculate this using a custom formula to balance socioeconomic factors with the policy response of a city. There are three parts of this formula: a socioeconomic value from FRED and other data sources, a policy value found using the policy Excel sheet in this repository, and the time remaining until protections end. The equation is

`relative_risk = socioeconomic_index * (1 - policy_index) / sqrt(time_remaining)`

In this equation, we aim to minimize socioeconomic risk on the top of the fraction, maximize the policy response value and take 1 minus the index value calculated (to represent that better policy constitutes less relative risk), and maximize the time remaining on the bottom of the fraction. The square root of the time remaining is used to represent how additional time has diminishing returns. For example, the different between having 2 days and 2 weeks until protections expire is much different than whether policies expire in 3 months or 4 months when we think about how to prioritize one county over another.   

## What is cost of evictions?

To calculate the cost to avoid evictions the following calcuation was used:

    `(burdened household proportion/100) * county rent * housing stock distribution percentage * population * (burdened households/100)`

Housing stock distributions (US Census) were used to evaluate the types of houses that exist in the United States (e.g. studio, one bedroom, etc.).  Burdened household proportions were decided by Arup and were used to determine what percentage of people were most at risk.  Proportions were set at 5, 25, 33, 50, and 75 to represent that not all burdened households will face eviction, and we don't know how many actually will.  With the chosen proportion values, we are representing a general range, knowing there isn't a case where nobody will be evicted, or a case where everybody will be evicted.  These numbers can be adjusted based on the user's knowledge of their own county. County rents for each housing stock were sourced from HUD, and used Fair Market Rates to determine rent prices for each stock.  Fair Market Rents (FMRs) represent the estimated amount (base rent + essential utilities) that a property in a given area typically rents for. Burdened households was a percentage calculated by FRED which gives the percentage of the population who pay more than 30% of their income on rent.  Population data was pulled from HUD and represents the population by county in the year 2017. 

Performing this calculation for each proportion and each housing stock will calculate the amount needed to prevent eviction for each proportion.  The total cost of evictions for a particular county for one month was calcuated by summing each housing stock.  To get the cost of prevention for more than one month, the sum was multiplied by the number of months of interest. 

This script uses Fair Market Rent values.  Median rent values are also available in the database.  The script can be manually adjusted by the user to reference median rent values rather than fair market rent if they choose.  

Upon script completion, an excel file will be created within the output folder displaying all values mentioned above.  If you experience problems with the script or have questions about methodologies, please reach out to a member of the development team.  

Explanation of output fields:

    county_id: Unique ID for each county
    fmr_[0-4]: Fair Market Rent value for a 0 bedroom house to a 4 bedroom house
    Burdened Households (%): People who pay more than 30 percent of their income towards rent
    Income Inequality (Ratio): The income earned by the top percentage of households and dividing that by the income earned by the poorest percentage of households.
    Population Below Poverty Line (%): Population living below the minimum level of income deemed adequate in a particular county 
    Single Parent Households (%): Number of households with a single parent
    SNAP Benefits Recipients (Persons): Number of people receiving Supplemental Nutrition Assistance Progarm benefits 
    Unemployment Rate (%): Percentage of the population unemployed
    Resident Population (Thousands of Persons): Number of persons in a county 
    VulnerabilityIndex: COVID Vulnerability Index, as defined by CHMURA
    Non-Home Ownership (%): Percentage of persons who do not own a home
    [0-4]_br_cost_5: Cost of preventing evictions for a 0-4 bedroom house for proportion 5
    [0-4]_br_cost_25: Cost of preventing evictions for a 0-4 bedroom house for proportion 25
    [0-4]_br_cost_33: Cost of preventing evictions for a 0-4 bedroom house for proportion 33
    [0-4]_br_cost_50: Cost of preventing evictions for a 0-4 bedroom house for proportion 50
    [0-4]_br_cost_75: Cost of preventing evictions for a 0-4 bedroom house for proportion 75

To calculate the total cost of evictions for a single month, simply add the costs for each housing type for a particular proportion.  

## Python Users
We've done our previous analyses in Python, and have built data gathering, cleaning, and analysis functions.

### Install
In a virtual environment:

`pip install -r requirements.txt`

### Run
To run the main script, run:

`python run.py`

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
The database that this repository uses is open for *read-only* access. The connection details are stored in `credentials.py` if you're using the Python workflow.

If you'd like to query the database directly using the method of your choice, you can access it using the credentials below:

```
DB_HOST = ade-eviction.ccgup3bgyakw.us-east-1.rds.amazonaws.com
DB_NAME = eviction_data
DB_PORT = 5432
DB_USER = readonly
DB_PASSWORD = PublicReadPassword
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