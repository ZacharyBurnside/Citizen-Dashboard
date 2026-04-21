import time
import requests
import pandas as pd
import json
import math
import mysql.connector
from requests.exceptions import RequestException

# —— CONFIG —— #
DB_CONFIG = {
    "host":     "zburnside.mysql.pythonanywhere-services.com",
    "user":     "zburnside",
    "password": "Bearsocks24!",
    "database": "zburnside$citizens"
}

JSON_COLS = {"ll", "rawLocation", "categories"}
WANTED    = [
    "address","cs","key","level","location","latitude","longitude",
    "neighborhood","ll","rawLocation","title","ts","police",
    "severity","categories","confirmed","incidentScore","city"
]

cities = {
    "Atlanta":        (33.60, -84.60, 34.00, -84.10),
    "Baltimore":      (39.10, -76.80, 39.50, -76.40),
    "Boston":         (42.20, -71.20, 42.40, -70.90),
    "Charlotte":      (35.00, -80.99, 35.40, -80.65),
    "Chicago":        (41.60, -87.90, 42.00, -87.50),
    "Dallas":         (32.60, -96.98, 33.00, -96.60),
    "Detroit":        (42.20, -83.30, 42.50, -82.90),
    "Houston":        (29.50, -95.80, 29.90, -95.10),
    "Indianapolis":   (39.60, -86.40, 39.90, -86.00),
    "Los Angeles":    (33.70, -118.70, 34.30, -118.10),
    "Miami":          (25.60, -80.35, 25.90, -80.00),
    "Minneapolis":    (44.80, -93.35, 45.00, -93.10),
    "New York City":  (40.50, -74.25, 40.90, -73.70),
    "Philadelphia":   (39.85, -75.30, 40.10, -74.90),
    "Phoenix":        (33.30, -112.30, 33.70, -111.70),
    "SF Bay Area":    (37.30, -122.50, 38.20, -121.50),
    "Washington DC":  (38.80, -77.20, 39.00, -76.80),
    "Portland":       (45.30, -122.75, 45.65, -122.40),
    "Seattle":        (47.45, -122.45, 47.75, -122.10),
    "San Diego":      (32.65, -117.25, 33.05, -116.90),
    "San Antonio":    (29.30, -98.80, 29.60, -98.40),
    "Austin":         (30.10, -97.90, 30.50, -97.60),
    "Jacksonville":   (30.15, -81.80, 30.55, -81.35),
    "Columbus":       (39.85, -83.10, 40.15, -82.75),
    "Fort Worth":     (32.65, -97.45, 33.00, -97.15),
    "El Paso":        (31.65, -106.55, 32.00, -106.05),
    "Memphis":        (35.00, -90.20, 35.30, -89.85),
    "Nashville":      (36.05, -86.85, 36.30, -86.60),
    "Las Vegas":      (36.05, -115.35, 36.25, -115.05),
    "Louisville":     (38.15, -85.90, 38.30, -85.60),
    "Milwaukee":      (43.00, -88.00, 43.15, -87.85),
    "Oklahoma City":  (35.30, -97.70, 35.60, -97.30),
    "Orlando":        (28.30, -81.60, 28.70, -81.20),
    "Providence":     (41.75, -71.45, 41.85, -71.30),
    "Richmond":       (37.45, -77.60, 37.65, -77.35),
    "Raleigh":        (35.70, -78.80, 36.00, -78.40),
    "Kansas City":    (39.00, -94.60, 39.20, -94.45),
    "Cleveland":      (41.40, -81.75, 41.60, -81.65),
    "Pittsburgh":     (40.35, -80.10, 40.55, -79.90),
    "Tampa":          (27.90, -82.60, 28.10, -82.35),
}


session = requests.Session()
session.headers.update({"User-Agent": "Mozilla/5.0"})

# —— FETCH FUNCTION —— #
def fetch_incidents(llat, llon, ulat, ulon, limit=5000):
    url = "https://citizen.com/api/incident/trending"
    params = {
        "lowerLatitude":  llat,
        "lowerLongitude": llon,
        "upperLatitude":  ulat,
        "upperLongitude": ulon,
        "fullResponse":   True,
        "limit":          limit
    }
    try:
        r = session.get(url, params=params, timeout=15)
        r.raise_for_status()
        data = r.json().get("results", [])
        df = pd.DataFrame(data)
        if "id" in df.columns:
            df = df.rename(columns={"id": "key"})
        # only keep incident columns (city will be added later)
        incident_cols = [c for c in WANTED if c in df.columns and c != "city"]
        return df[incident_cols].copy()
    except RequestException as e:
        print(f"⚠️ {e.__class__.__name__} for bbox {llat, llon, ulat, ulon}: {e}")
        return pd.DataFrame(columns=[c for c in WANTED if c != "city"])

# —— DB SAVE FUNCTIONS —— #
def get_connection():
    return mysql.connector.connect(**DB_CONFIG)

def save_to_db(df):
    conn = get_connection()
    cur = conn.cursor()
    cols = df.columns.tolist()
    cols_sql = ", ".join(f"`{c}`" for c in cols)
    placeholders = ", ".join(["%s"] * len(cols))

    # Upsert query
    sql = f"""
    INSERT INTO `all_city` ({cols_sql})
    VALUES ({placeholders})
    ON DUPLICATE KEY UPDATE
    {", ".join(f"`{c}`=VALUES(`{c}`)" for c in cols if c != "key")}
    """

    rows = []
    for row in df.itertuples(index=False, name=None):
        record = []
        for c, v in zip(cols, row):
            if c in JSON_COLS:
                record.append(json.dumps(v, default=str) if isinstance(v, (dict, list)) else None)
            elif isinstance(v, float) and math.isnan(v):
                record.append(None)
            else:
                record.append(v)
        rows.append(tuple(record))

    cur.executemany(sql, rows)
    conn.commit()
    print(f"{len(rows)} rows upserted into all_city.")
    cur.close()
    conn.close()

# —— MAIN SCRIPT —— #
if __name__ == "__main__":
    all_dfs = []
    for city, bbox in cities.items():
        print(f"→ Fetching {city}…", end=" ")
        df_city = fetch_incidents(*bbox)
        print("Done" if not df_city.empty else "No data")
        df_city["city"] = city
        all_dfs.append(df_city)
        time.sleep(1)

    master_df = pd.concat(all_dfs, ignore_index=True)
    save_to_db(master_df)
    print("Finished running!")
