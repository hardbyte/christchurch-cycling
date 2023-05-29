
Quick script to scrape the Christchurch City Council cycling
data from https://smartview.ccc.govt.nz/map/layers/ecocounter

The data directory contains a sample of the cycle count data.

The live data is also available on GCP:
https://storage.googleapis.com/hardbyte-ccc/cycling-counters.parquet

To run the scraper script [install poetry](https://python-poetry.org/) and Python3.11+.

From a terminal, install the dependencies, enter the virtual environment, and run the `main` 
script with:

```
poetry install
poetry shell
python main.py
```



Ideas:

- Python script to get the data and make available as a CSV/parquet file. 
- Run nightly (GCP Build Job, Cloud Task) and upload data somewhere public.
- Metabase Dashboard (Add people who care as Admin)



## Examples

WIP some examples of querying the DuckDB database: 

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