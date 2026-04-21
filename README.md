# Citizen Crime Dashboard

A real-time public safety analytics platform built on data from the Citizen app. Tracks incidents across 40+ major US cities — including violent crime, non-violent incidents, and ICE-related activity — with an interactive map, time series trends, and neighborhood safety rankings.

Available as both a **Plotly Dash app** and a **Streamlit app**.

---

## What It Does

1. **Scrapes** live incident data from Citizen's trending API across 40 US cities using geographic bounding boxes
2. **Stores** incidents in MySQL with upsert logic — no duplicate entries per incident key
3. **Visualizes** the data through an interactive dashboard with map, time series, crime type breakdowns, and neighborhood rankings

---

## Data Pipeline

```
citizen_full_scrape.py (run on schedule)
        ↓
Hits Citizen API for each city bounding box → up to 5,000 incidents per city
        ↓
Upserts into MySQL all_city table (keyed on incident ID)
        ↓
main_app.py or streamlit_dash.py
        ↓
Loads from MySQL → filters → renders charts
```

---

## Scraper — `citizen_full_scrape.py`

Covers **40 US cities** including NYC, LA, Chicago, Houston, Miami, Seattle, and more.

Each city is defined by a latitude/longitude bounding box. For each city the scraper:
- Hits `citizen.com/api/incident/trending` with the bounding box
- Fetches up to 5,000 incidents per city
- Upserts into MySQL — updates existing records, inserts new ones
- Sleeps 1 second between cities to avoid rate limiting

**Fields collected:**
`title`, `address`, `neighborhood`, `city`, `latitude`, `longitude`, `categories`, `severity`, `confirmed`, `incidentScore`, `timestamp`, `police`

---

## Dashboards

### Plotly Dash — `main_app.py`

```bash
pip install dash plotly pandas mysql-connector-python
python main_app.py
# Open http://localhost:8059
```

### Streamlit — `streamlit_dash.py`

```bash
pip install streamlit plotly pandas mysql-connector-python
streamlit run streamlit_dash.py
```

Both dashboards include identical functionality — use whichever you prefer.

---

## Dashboard Features

| Feature | Description |
|---|---|
| **Incident map** | Scatter map colored by severity (Turbo scale) with hover details |
| **Crime over time** | Line chart of daily incident volume |
| **Violent crimes** | Stacked bar chart — Assault, Break In, Gun Related, Robbery, etc. |
| **Non-violent incidents** | Stacked bar chart of all other categories |
| **ICE related incidents** | Separate bar chart tracking immigration enforcement activity |
| **Neighborhood rankings** | Top 5 most and least dangerous neighborhoods by severity score |

**Filters:** Date range, neighborhood, incident category

---

## Cities Covered

Atlanta, Baltimore, Boston, Charlotte, Chicago, Dallas, Detroit, Houston, Indianapolis, Los Angeles, Miami, Minneapolis, New York City, Philadelphia, Phoenix, SF Bay Area, Washington DC, Portland, Seattle, San Diego, San Antonio, Austin, Jacksonville, Columbus, Fort Worth, El Paso, Memphis, Nashville, Las Vegas, Louisville, Milwaukee, Oklahoma City, Orlando, Providence, Richmond, Raleigh, Kansas City, Cleveland, Pittsburgh, Tampa

---

## Tech Stack

- **Python** — scraper and dashboard logic
- **Requests** — Citizen API calls
- **MySQL** — incident storage with upsert
- **Plotly Dash / Streamlit** — dashboard frameworks
- **Pandas** — data processing
- **Plotly Express** — all charts and maps
