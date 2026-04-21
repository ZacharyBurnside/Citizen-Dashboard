import streamlit as st
import pandas as pd
import mysql.connector
import plotly.express as px
import ast, re

# ── Database Configuration ─────────────────────────────────────────────────────
DB_CONFIG = {
    "host":     "zburnside.mysql.pythonanywhere-services.com",
    "user":     "zburnside",
    "password": "Bearsocks24!",
    "database": "zburnside$citizens"
}

# ── Data Loading ───────────────────────────────────────────────────────────────
@st.cache_data
def load_data():
    conn = mysql.connector.connect(**DB_CONFIG)
    df = pd.read_sql("SELECT * FROM citizens_crime_data", conn)
    conn.close()
    df['date']       = pd.to_datetime(df['ts'], unit='ms')
    df['start_date'] = pd.to_datetime(df['cs'], unit='ms')
    df['date']       = df['date'].dt.date
    df['period']     = pd.to_datetime(df['date'])
    return df

# ── Category Extraction ─────────────────────────────────────────────────────────
def extract_category(cell):
    if pd.isna(cell): return None
    s = str(cell)
    try:
        outer = ast.literal_eval(s)
        if isinstance(outer, list) and outer:
            first = outer[0]
            inner = ast.literal_eval(first) if isinstance(first, str) else first
            if isinstance(inner, list) and inner:
                return inner[0]
    except Exception:
        pass
    m = re.search(r'\["([^\"]+)"\]', s)
    return m.group(1) if m else s.strip("[]'\"")

# ── Prepare Data ───────────────────────────────────────────────────────────────
df = load_data()
df['category'] = df['categories'].apply(extract_category)
severity_map = {'Murder':5, 'Shooting':5, 'Stabbing':5, 'Assault':4}
df['severity'] = df['title'].map(severity_map).fillna(2)

neighborhoods = sorted(df['neighborhood'].dropna().astype(str).unique())
categories    = sorted(df['category'].dropna().unique())

violent_set = {'Assault / Fight','Break In','Gun Related','Harassment','Pursuit / Search','Robbery / Theft','Weapon'}
ice_set     = {'ICE Related'}

# ── Sidebar Filters ────────────────────────────────────────────────────────────
st.sidebar.header("Filters")
date_range = st.sidebar.date_input(
    "Select Date Range",
    value=(df['period'].min().date(), df['period'].max().date())
)
selected_neighborhoods = st.sidebar.multiselect("Neighborhoods", neighborhoods)
selected_categories    = st.sidebar.multiselect("Categories", categories)

# ── Apply Filters ──────────────────────────────────────────────────────────────
start_date, end_date = date_range
dff = df[(df['period'] >= pd.to_datetime(start_date)) & (df['period'] <= pd.to_datetime(end_date))]
if selected_neighborhoods:
    dff = dff[dff['neighborhood'].isin(selected_neighborhoods)]
if selected_categories:
    dff = dff[dff['category'].isin(selected_categories)]

# ── Main Dashboard Layout ──────────────────────────────────────────────────────
st.title("Citizen Crime Dashboard")

col1, col2 = st.columns(2)

# ── Map ────────────────────────────────────────────────────────────────────────
with col1:
    st.subheader("Incident Map")
    map_fig = px.scatter_mapbox(
        dff,
        lat='latitude',
        lon='longitude',
        color='severity',
        color_continuous_scale='Turbo',
        hover_data=['category','neighborhood','date','title'],
        zoom=10,
        mapbox_style='carto-positron'
    )
    st.plotly_chart(map_fig, use_container_width=True)

# ── Time Series ────────────────────────────────────────────────────────────────
with col2:
    st.subheader("Crime Over Time")
    ts = dff.groupby('period').size().reset_index(name='count')
    ts_fig = px.line(
        ts,
        x='period',
        y='count',
        title='Crime Over Time',
        color_discrete_sequence=px.colors.sequential.Plasma
    )
    st.plotly_chart(ts_fig, use_container_width=True)

# ── 3 Crime Type Graphs ────────────────────────────────────────────────────────
st.subheader("Crime Type Breakdown")
col_v, col_nv, col_ice = st.columns(3)

# Violent crimes
df_v = dff[dff['category'].isin(violent_set)]
pv = df_v.groupby(['period','category']).size().reset_index(name='count')
pv = pv.pivot(index='period', columns='category', values='count').fillna(0).reset_index()
fig_v = px.bar(pv, x='period', y=pv.columns.drop('period'), barmode='stack',
               title='Violent Crimes', color_discrete_sequence=px.colors.sequential.Magma)
col_v.plotly_chart(fig_v, use_container_width=True)

# Non-violent
nonv = set(dff['category'].unique()) - violent_set - ice_set
df_nv = dff[dff['category'].isin(nonv)]
pn = df_nv.groupby(['period','category']).size().reset_index(name='count')
pn = pn.pivot(index='period', columns='category', values='count').fillna(0).reset_index()
fig_nv = px.bar(pn, x='period', y=pn.columns.drop('period'), barmode='stack',
                title='Non-Violent Incidents', color_discrete_sequence=px.colors.sequential.Viridis)
col_nv.plotly_chart(fig_nv, use_container_width=True)

# ICE related
df_ice = dff[dff['category'] == 'ICE Related']
ci = df_ice.groupby('period').size().reset_index(name='count')
fig_ice = px.bar(ci, x='period', y='count', title='ICE Related Incidents',
                 color_discrete_sequence=px.colors.sequential.Inferno)
col_ice.plotly_chart(fig_ice, use_container_width=True)

# ── Top 5 Dangerous & Safe Neighborhoods ───────────────────────────────────────
st.subheader("Neighborhood Rankings")

scores = dff.groupby('neighborhood')['severity'].sum().reset_index(name='score')
danger = scores.nlargest(5, 'score')
safe = scores.nsmallest(5, 'score')

col_danger, col_safe = st.columns(2)
col_danger.markdown("### Top 5 Dangerous")
col_danger.dataframe(danger)

col_safe.markdown("### Top 5 Safe")
col_safe.dataframe(safe)
