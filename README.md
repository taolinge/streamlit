# Arup Eviction Data
This is a repository for analysis on open data related to evictions as a result of COVID-19. This repository gathers data from the Federal Reserve Economic Data portal (FRED). There are a number of potential use cases we're aware of to apply that data to address evictions. 

The analysis we do now allows us compare counties side by side by their "Relative Risk" of evictions, based on the FRED data.
 
## Install
In a virtual environment:
`pip install -r requirements.txt`

## Run
Run the following and follow the command line prompts. 

`python run.py`

The `credentials.py` file is configured to allow read-only access to an Arup-maintained database of the most recent relevant FRED data. In addition to using these Python scripts, you can connect to this database and run direct SQL queries to get the data you want.

Connect to `ade-eviction.ccgup3bgyakw.us-east-1.rds.amazonaws.com` using the user `readonly`.

`SELECT * from {tables} WHERE county_name={county};` 

## Usage
This repository currently supports three workflows:

- 1: Gathering data for a single county in a state
- 2: Gathering and comparing data for multiple counties using a Relative Risk index
- 3: Gathering data for all counties in a state and comparing using a Relative Risk index

These workflows support a number of use cases, including:
- Providing direct assistance to families in one or more counties
- Driving decisions around future affordable housing projects
- Directing policy response on the city or county level


## Fred Queries

`python -m queries`

### Flags

| Flag | Purpose |
|------|---------|
| `--table`| Specifies a table that you want to query. If none is given, will return all tables.|
| `--ouput`| Specifies an output type, without a ".". Currently, only `pk` or `xlsx` are supported. `pk` returns a pickled `pandas.DataFrame`. If none is given, will default to `xlsx`.|

### Purpose

This command will query the eviction data database, and return data in an `Output` folder. If no folder exists, will be created by the `queries.py` script.

## Issues
Please submit bugs or errors to the Issues tab of this repository.

## Contributing
We would love for you to use this code, build on it, and share with others. See CONTRIBUTING.md for more information.

Arup is not using this repository for commercial work. 

### Code
Make a merge request with your feature or bug fixes and we will review it and merge once it's been reviewed.

### Policy Data
Policy data is some of the most useful, but also the hardest to get. We've shared policies for a number of counties we've analyzed in the Bay Area and Tulsa area, and we hope that as you do policy analysis for your county, you'll contribute that back so others can use and verify it. 

For now, to submit your data, open an issue in this repository and submit your policy data (countdown and/or policy ranking). 

### Other Data Sources
If there are data sources you'd like to see included in this, please reach out through the Issues tab. 

 