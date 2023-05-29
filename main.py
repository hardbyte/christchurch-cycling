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
    create table if not exists sites (
        oid VARCHAR,
        name VARCHAR,
        info VARCHAR,
        x DOUBLE,
        y DOUBLE
    )
    """)

    conn.execute("""
    create table if not exists cycling_counts (
        site VARCHAR,
        date Date,
        value Integer
    )
    """)


def add_site_counts_to_db(db, measurement_data):

    db.executemany(
        "insert into cycling_counts VALUES (?, ?, ?)",
        [
           [site_oid, x, y] for (x, y) in zip(measurement_data.x, measurement_data.y)
        ]
    )



if __name__ == '__main__':
    db = get_db_connection('duck.db')
    REFRESH_DATA = True

    if REFRESH_DATA:
        create_tables(db)
        print("Downloading cycle counts")
        sites = download_cycling_sites()

        for s in sites:
            if not s.properties.total:
                site_oid = s.properties.oid
                print(site_oid, s.properties.name, s.geometry.coordinates)
                db.execute("""
                    insert into sites VALUES (?, ?, ?, ?, ?)
                """, [
                    site_oid,
                    s.properties.name,
                    s.properties.json(),
                    *s.geometry.coordinates
                ])

                measurement_data = download_cycling_count_data(site_oid)
                add_site_counts_to_db(db, measurement_data)
        db.commit()

    # Example 3 - Output
    # We will just output cycle counts to parquet file:
    db.execute("""
    COPY (
        SELECT 
            site, date, value, sites.name, sites.x, sites.y 
        FROM sites, cycling_counts
        WHERE 
            cycling_counts.site = sites.oid
    ) TO 'data/cycling-counters.parquet' (FORMAT PARQUET);
    """)
