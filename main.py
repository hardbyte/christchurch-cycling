
from enum import StrEnum
from typing import Tuple

import httpx
import datetime
import duckdb
from pydantic import BaseModel


class EcoCounterDirection(StrEnum):
    both = "both"
    one = "one"


class Geometry(BaseModel):
    _type = "Point"
    coordinates: Tuple[float, float]


class EcoCounterProperty(BaseModel):
    feature: str = "ecocounter"
    total: bool | None
    name: str
    count: int
    installed_on: datetime.date | None
    oid: str
    direction: EcoCounterDirection | None


class EcoCounterSite(BaseModel):
    _type = "Feature"
    properties: EcoCounterProperty
    geometry: Geometry


class EcoCountersResponse(BaseModel):
    features: list[EcoCounterSite]


class RawEcoCounterResponse(BaseModel):
    x: list[datetime.date]
    y: list[int]


def download_cycling_sites() -> list[EcoCounterSite]:
    base_url = "https://smartview.ccc.govt.nz"
    url = f"{base_url}/app/router/map_features.php?feat=ecocounter"

    response = httpx.get(url, timeout=60)

    return EcoCountersResponse.parse_raw(response.text).features


def download_cycling_count_data(oid) -> RawEcoCounterResponse:
    base_url = "https://smartview.ccc.govt.nz"
    url = f"{base_url}/app/router/ecocounter.php?oid={oid}&type=ecocounter"

    response = httpx.get(url, timeout=60)
    return RawEcoCounterResponse.parse_raw(response.text)


def get_db_connection(db_filename=None):
    if db_filename is None:
        db_filename = ':memory:'
    # By default, duckdb is fully in-memory - we want to use persistent storage:
    conn = duckdb.connect(db_filename)
    return conn


def create_tables(conn):

    conn.execute("""
    create table sites (
        oid VARCHAR,
        installed_date Date,
        info VARCHAR
    )
    """)

    conn.execute("""
    create table cycling_counts (
        site VARCHAR,
        date Date,
        value Integer
    )
    """)


if __name__ == '__main__':
    db = get_db_connection()
    create_tables(db)
    print("Downloading list of sites")
    sites = download_cycling_sites()

    for s in sites:
        if not s.properties.total:
            print(s.properties.oid, s.properties.name, s.geometry)

            site_oid = s.properties.oid
            measurement_data = download_cycling_count_data(site_oid)

            db.executemany("insert into cycling_counts VALUES (?, ?, ?)",
               [
                   [site_oid, x, y] for (x, y) in zip(measurement_data.x, measurement_data.y)
               ]
            )

    # Output to parquet file:
    db.execute("""
    COPY (SELECT date, value from cycling_counts) TO 'cycling-counters.parquet' (FORMAT PARQUET);
    """)
