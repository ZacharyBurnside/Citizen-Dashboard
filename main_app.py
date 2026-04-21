import dash
from dash import dcc, html, Input, Output
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

# ── Dropdown Options ────────────────────────────────────────────────────────────
neighborhoods = sorted(df['neighborhood'].dropna().astype(str).unique())
categories    = sorted(df['category'].dropna().unique())
violent_set    = {'Assault / Fight','Break In','Gun Related','Harassment','Pursuit / Search','Robbery / Theft','Weapon'}
ice_set       = {'ICE Related'}

# ── Initialize Dash App ─────────────────────────────────────────────────────────
app = dash.Dash(__name__)
app.title = "Citizen Dashboard"

# ── Layout ─────────────────────────────────────────────────────────────────────
app.layout = html.Div([
    html.Div([
        dcc.DatePickerRange(id='date-range',start_date=df['period'].min().date(),end_date=df['period'].max().date(),display_format='YYYY-MM-DD'),
        dcc.Dropdown(id='neighborhood-filter',options=[{'label':n,'value':n} for n in neighborhoods],multi=True,placeholder='Neighborhood'),
        dcc.Dropdown(id='category-filter',options=[{'label':c,'value':c} for c in categories],multi=True,placeholder='Category')
    ], style={'display':'flex','gap':'10px','marginBottom':'20px'}),

    html.Div([
        dcc.Graph(id='map-graph', style={'width':'49%','display':'inline-block'}),
        dcc.Graph(id='time-series', style={'width':'49%','display':'inline-block'})
    ]),

    html.Div([
        dcc.Graph(id='violent-graph', style={'width':'32%','display':'inline-block'}),
        dcc.Graph(id='nonviolent-graph', style={'width':'32%','display':'inline-block'}),
        dcc.Graph(id='ice-graph', style={'width':'32%','display':'inline-block'})
    ], style={'marginTop':'20px'}),

    html.Div([
        html.Div([html.H3('Top 5 Dangerous'),dcc.Markdown(id='danger-table')],style={'width':'49%','display':'inline-block'}),
        html.Div([html.H3('Top 5 Safe'),dcc.Markdown(id='safe-table')],style={'width':'49%','display':'inline-block'})
    ], style={'marginTop':'20px'})
])

# ── Callbacks ───────────────────────────────────────────────────────────────────
@app.callback(
    Output('map-graph','figure'),Output('time-series','figure'),Output('violent-graph','figure'),
    Output('nonviolent-graph','figure'),Output('ice-graph','figure'),Output('danger-table','children'),
    Output('safe-table','children'),Input('date-range','start_date'),Input('date-range','end_date'),
    Input('neighborhood-filter','value'),Input('category-filter','value')
)
def update(start_date,end_date,nb_filter,cat_filter):
    dff = df[(df['period']>=pd.to_datetime(start_date))&(df['period']<=pd.to_datetime(end_date))]
    if nb_filter: dff=dff[dff['neighborhood'].isin(nb_filter)]
    if cat_filter: dff=dff[dff['category'].isin(cat_filter)]

    # Map with vibrant turbo scale
    map_fig=px.scatter_mapbox(dff,lat='latitude',lon='longitude',color='severity',
        color_continuous_scale='Turbo',hover_data=['category','neighborhood','date','title'],
        zoom=10,mapbox_style='carto-positron')

    # Time series with Plasma palette
    ts=dff.groupby('period').size().reset_index(name='count')
    ts_fig=px.line(ts,x='period',y='count',title='Crime Over Time',
        color_discrete_sequence=px.colors.sequential.Plasma)

    # Violent crimes with Magma
    df_v=dff[dff['category'].isin(violent_set)]
    pv=df_v.groupby(['period','category']).size().reset_index(name='count')
    pv=pv.pivot(index='period',columns='category',values='count').fillna(0).reset_index()
    fig_v=px.bar(pv,x='period',y=pv.columns.drop('period'),barmode='stack',
        title='Violent Crimes',color_discrete_sequence=px.colors.sequential.Magma)

    # Non-violent with Viridis
    nonv=set(dff['category'].unique())-violent_set-ice_set
    df_nv=dff[dff['category'].isin(nonv)]
    pn=df_nv.groupby(['period','category']).size().reset_index(name='count')
    pn=pn.pivot(index='period',columns='category',values='count').fillna(0).reset_index()
    fig_nv=px.bar(pn,x='period',y=pn.columns.drop('period'),barmode='stack',
        title='Non-Violent Incidents',color_discrete_sequence=px.colors.sequential.Viridis)

    # ICE related with Inferno
    df_ice=dff[dff['category']=='ICE Related']
    ci=df_ice.groupby('period').size().reset_index(name='count')
    fig_ice=px.bar(ci,x='period',y='count',title='ICE Related Incidents',
        color_discrete_sequence=px.colors.sequential.Inferno)

    # Tables
    scores=dff.groupby('neighborhood')['severity'].sum().reset_index(name='score')
    danger=scores.nlargest(5,'score')
    safe=scores.nsmallest(5,'score')
    def df_to_md(df_):
        md='| Neighborhood | Score |\n|---|---|\n'
        for _,r in df_.iterrows():md+=f"| {r['neighborhood']} | {r['score']} |\n"
        return md

    return map_fig,ts_fig,fig_v,fig_nv,fig_ice,df_to_md(danger),df_to_md(safe)

# ── Run Server ─────────────────────────────────────────────────────────────────
if __name__=='__main__':
    app.run_server(debug=True,port=8059)
