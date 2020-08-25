# Arup Eviction Data
This is a repository for analysis on open data related to evictions as a result of COVID-19. This repository gathers data from the Federal Reserve Economic Data portal (FRED). There are a number of potential use cases we're aware of to apply that data to address evictions. 

The analysis we do now allows us compare counties side by side by their "Relative Risk" of evictions, based on the FRED data.

## Usage
This repository currently supports three workflows:

1. Gathering data for a single county in a state
2. Gathering and comparing data for multiple counties using a Relative Risk index
3. Gathering data for all counties in a state and comparing using a Relative Risk index

These workflows support a number of use cases, including:
- Providing direct assistance to families in one or more counties
- Driving decisions around future affordable housing projects
- Directing policy response on the city or county level

There are two ways to interact with this data.
- Python scripts
- Custom SQL Queries

### What is Relative Risk?
Relative risk is an index used to compare counties against each other. It is _not_ a measure of absolute or percentage risk and has no meaning outside of this analysis. We use this compare counties to understand where people are more at risk of eviction. 

We calculate this using a custom formula to balance socioeconomic factors with the policy response of a city. There are three parts of this formula: a socioeconomic value from FRED and other data sources, a policy value found using the policy Excel sheet in this repository, and the time remaining until protections end. The equation is

`relative_risk = socioeconomic_index * (1 - policy_index) / sqrt(time_remaining)`

In this equation, we aim to minimize socioeconomic risk on the top of the fraction, maximize the policy response value and take 1 minus the index value calculated (to represent that better policy constitutes less relative risk), and maximize the time remaining on the bottom of the fraction. The square root of the time remaining is used to represent how additional time has diminishing returns. For example, the different between having 2 days and 2 weeks until protections expire is much different than whether policies expire in 3 months or 4 months when we think about how to prioritize one county over another.   

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
We would love for you to use this code, build on it, and share with others. See [our contribution guide](CONTRIBUTING.md) for more information.

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