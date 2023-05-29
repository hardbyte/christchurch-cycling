
Quick script to scrape the Christchurch City Council cycling
data from https://smartview.ccc.govt.nz/map/layers/ecocounter

The data directory contains a sample of the cycle count data.

TODO: The data may be updated nightly and made available on GCP in parquet and duckdb formats.

To run the scraper script [install poetry](https://python-poetry.org/) and Python3.11+.

From a terminal, install the dependencies, enter the virtual environment, and run the `main` 
script with:

```
poetry install
poetry shell
python main.py
```


## Ideas:

- Python script to get the data and make available as a CSV/parquet file. 
- Run nightly (GCP Build Job, Cloud Task) and upload data somewhere public.
- Metabase Dashboard (Add people who care as Admin)

Live version of this graph
- https://cyclingchristchurch.co.nz/2023/01/21/chch-cycle-counter-update-2022-lockdown-jitters/


## Examples

After you have run the `main.py` script you will have a duckdb database that you can query directly. You can also
download mine from https://storage.googleapis.com/hardbyte-ccc/duck.db

Install duckdb - https://duckdb.org/docs/installation/index and start a DB console with:

```shell
duckdb duck.db
```

Some example SQL queries: 

### Get all the raw counts for each site for the last 30 days:


```sql
select 
    sites.name, cycling_counts.date, cycling_counts.value
from 
    sites, cycling_counts
where 
    cycling_counts.site = sites.oid
    and current_date - cycling_counts.date < 30
```

### 7 day moving average for a site

Ref https://duckdb.org/docs/sql/window_functions

```sql
select "Name", "Date", AVG("value") OVER (
    partition by "site" 
    order by "Date" ASC 
    RANGE BETWEEN INTERVAL 3 DAYS PRECEDING
          AND INTERVAL 3 DAYS FOLLOWING)
AS "7-day Moving Average"
from 
    sites, cycling_counts
where 
    cycling_counts.site = sites.oid
    order by "Name", "Date"
```

### Output

Duckdb can output to csv/parquet and much much more. 
Ref https://duckdb.org/docs/sql/statements/copy

```sql
COPY (
    SELECT 
        site, date, value, sites.name, sites.x, sites.y 
    FROM sites, cycling_counts
    WHERE 
        cycling_counts.site = sites.oid
) TO 'data/cycling-counters.parquet' (FORMAT PARQUET);
```
