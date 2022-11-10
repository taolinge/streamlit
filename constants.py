# Consider using python ENUM class
from enum import Enum, auto

STATES = [
    'Alabama',
    'Alaska',
    'Arizona',
    'Arkansas',
    'California',
    'Colorado',
    'Connecticut',
    'Delaware',
    'District of Columbia',
    'Florida',
    'Georgia',
    'Hawaii',
    'Idaho',
    'Illinois',
    'Indiana',
    'Iowa',
    'Kansas',
    'Kentucky',
    'Louisiana',
    'Maine',
    'Maryland',
    'Massachusetts',
    'Michigan',
    'Minnesota',
    'Mississippi',
    'Missouri',
    'Montana',
    'Nebraska',
    'Nevada',
    'New Hampshire',
    'New Jersey',
    'New Mexico',
    'New York',
    'North Carolina',
    'North Dakota',
    'Ohio',
    'Oklahoma',
    'Oregon',
    'Pennsylvania',
    'Puerto Rico',
    'Rhode Island',
    'South Carolina',
    'South Dakota',
    'Tennessee',
    'Texas',
    'Utah',
    'Vermont',
    'Virginia',
    'Washington',
    'West Virginia',
    'Wisconsin',
    'Wyoming'
]

HOUSING_STOCK_DISTRIBUTION = {
    # Assumed National housing distribution [https://www.census.gov/programs-surveys/ahs/data/interactive/ahstablecreator.html?s_areas=00000&s_year=2017&s_tablename=TABLE2&s_bygroup1=1&s_bygroup2=1&s_filtergroup1=1&s_filtergroup2=1]
    0: 0.0079,
    1: 0.1083,
    2: 0.2466,
    3: 0.4083,
    4: 0.2289
}

BURDENED_HOUSEHOLD_PROPORTION = [5, 25, 33, 50, 75]

COLOR_RANGE = [
    [65, 182, 196],
    [127, 205, 187],
    [199, 233, 180],
    [237, 248, 177],
    [255, 255, 204],
    [255, 237, 160],
    [254, 217, 118],
    [254, 178, 76],
    [253, 141, 60],
    [252, 78, 42],
    [227, 26, 28],
]

COLOR_VALUES=[
    [13, 59, 102],
    [238, 150, 75],
    [249, 87, 56],
    [0,0,128],
    [210,105,30],
    [220,20,60],
    [250,128,114],
    [0,100,0],
    [255,215,0],
    [50,205,50],
    [47,79,79],
    [0,255,255],
    [0,0,255],
    [75,0,130],
    [255,0,255],
    [255,192,203],
]

BREAKS = [0, .1, .2, .3, .4, .5, .6, .7, .8, .9, 1]



EQUITY_DATA_TABLE = '''
| Feature Name | Resolution | Source | Updated | Notes | 
| ------------ | ---------- | ------ | ------- | ----- |
| English Proficiency | Census Tracts | [ACS](https://www.census.gov/programs-surveys/acs) | 2019 | Used to find percent of population with Limited English Proficiency |
| Disability Status | Census Tracts | [ACS](https://www.census.gov/programs-surveys/acs) | 2019 | Used to find percent of population with People with Disability |
| Poverty Status | Census Tracts | [ACS](https://www.census.gov/programs-surveys/acs) | 2019 | Used to find percent of population 200% Below Poverty Line |
| Hispanic or Latino Origin by Race | Census Tracts | [ACS](https://www.census.gov/programs-surveys/acs) | 2019 | Used to find percent of population that are People of Color |
| Family Type | Census Tracts | [ACS](https://www.census.gov/programs-surveys/acs) | 2019 | Used to find percent of population with Single Parent Families |
| Sex by Age | Census Tracts | [ACS](https://www.census.gov/programs-surveys/acs) | 2019 | Used to find percent of population Aged 65 and Over and Aged 19 and Under |
| Household Vehicle Availability | Census Tracts | [ACS](https://www.census.gov/programs-surveys/acs)| 2013 | Used to find percent of population in Zero-Vehicle Households |
'''

TRANSPORT_DATA_TABLE = '''
| Feature Name | Resolution | Source | Updated | Notes | 
| ------------ | ---------- | ------ | ------- | ----- |
| Housing Units in Structure | Census Tracts | [ACS](https://www.census.gov/programs-surveys/acs) | 2019 | Used to find percent that are Renter Occupied Units |
| Poverty Status | Census Tracts | [ACS](https://www.census.gov/programs-surveys/acs) | 2019 | Used to find percent of population 200% Below Poverty Line |
| Commuting Characteristics by Sex | Census Tracts | [ACS](https://www.census.gov/programs-surveys/acs) | 2019 | Used to find percent that are Drive Alone Commuters |
| Household Technology Availability | Census Tracts | [ACS](https://www.census.gov/programs-surveys/acs)| 2013 | Used to find percent that are No Computer Households |
| Household Vehicle Availability | Census Tracts | [ACS](https://www.census.gov/programs-surveys/acs)| 2013 | Used to find percent of population in Zero-Vehicle Households |
| Trip Miles | Census Tracts | [BTS](https://www.bts.gov/latch/latch-data) | 2013 | Used to find average Vehicle Miles Traveled |
| National Hazard Risk Index | Census Tracts | [FEMA](https://hazards.fema.gov/nri/understanding-scores-ratings) | 2021 | Used to identify risk scores for water-related natural hazards |
'''

LINKS = {'mtc_framework': 'https://bayareametro.github.io/Spatial-Analysis-Mapping-Projects/Project-Documentation/Equity-Priority-Communities/#summary-of-mtc-epc-demographic-factors--demographic-factor-definitions'}