import streamlit as st
import boto3
import pandas as pd
import io
import os
import pydeck as pdk
import plotly.graph_objects as go

st.set_page_config(page_title="MigrationPulse", page_icon="🦅", layout="wide")

# ── Indigo + White + Neon theme ──────────────────────────────────────────────
st.markdown("""
<style>
@import url('https://fonts.googleapis.com/css2?family=Outfit:wght@300;400;600;800;900&family=DM+Mono:wght@400;500&display=swap');

/* ── Base ── */
html, body,
[data-testid="stAppViewContainer"],
[data-testid="stMain"],
[data-testid="block-container"] {
    background-color: #1a1a2e !important;
    color: #ffffff !important;
}

[data-testid="stHeader"] { background: transparent !important; }

/* ── All text white ── */
*, p, div, span, label, li {
    font-family: 'Outfit', sans-serif !important;
    color: #ffffff !important;
}

/* ── Title block ── */
.title-wrap {
    padding: 2.8rem 0 2rem 0;
    border-bottom: 1px solid rgba(255,255,255,0.1);
    margin-bottom: 2.5rem;
}
.main-title {
    font-family: 'Outfit', sans-serif !important;
    font-size: 6rem !important;
    font-weight: 900 !important;
    line-height: 1.0 !important;
    margin: 0 !important;
    letter-spacing: -0.02em;
    color: #ffffff !important;
    -webkit-text-fill-color: #ffffff !important;
}
.main-title span.pink  { color: #ff4dbe !important; -webkit-text-fill-color: #ff4dbe !important; }
.subtitle-line {
    font-family: 'DM Mono', monospace !important;
    color: rgba(255,255,255,0.55) !important;
    font-size: 0.85rem !important;
    letter-spacing: 0.18em;
    text-transform: uppercase;
    margin-top: 0.7rem;
}

/* ── Section label ── */
.sec-label {
    font-family: 'DM Mono', monospace !important;
    font-size: 0.7rem !important;
    font-weight: 500 !important;
    letter-spacing: 0.25em;
    text-transform: uppercase;
    color: rgba(255,255,255,0.45) !important;
    margin: 2.2rem 0 1rem 0;
    display: flex;
    align-items: center;
    gap: 0.6rem;
}
.sec-label::after {
    content: '';
    flex: 1;
    height: 1px;
    background: rgba(255,255,255,0.1);
}

/* ── Metric cards ── */
[data-testid="stMetric"] {
    background: rgba(255,255,255,0.05) !important;
    border: 1px solid rgba(255,255,255,0.1) !important;
    border-radius: 12px !important;
    padding: 1.4rem 1.6rem !important;
}
[data-testid="stMetricLabel"] p {
    font-family: 'DM Mono', monospace !important;
    font-size: 0.68rem !important;
    color: rgba(255,255,255,0.5) !important;
    -webkit-text-fill-color: rgba(255,255,255,0.5) !important;
    text-transform: uppercase !important;
    letter-spacing: 0.18em !important;
}
[data-testid="stMetricValue"] {
    font-family: 'Outfit', sans-serif !important;
    font-size: 2rem !important;
    font-weight: 800 !important;
    color: #ffffff !important;
    -webkit-text-fill-color: #ffffff !important;
}

/* ── Multiselect input ── */
[data-testid="stMultiSelect"] > div > div {
    background: rgba(255,255,255,0.07) !important;
    border: 1px solid rgba(255,255,255,0.15) !important;
    border-radius: 8px !important;
}
[data-testid="stMultiSelect"] input { color: #ffffff !important; }
span[data-baseweb="tag"] {
    background: rgba(255, 77, 190, 0.2) !important;
    border: 1px solid #ff4dbe !important;
    border-radius: 6px !important;
    color: #ff4dbe !important;
    -webkit-text-fill-color: #ff4dbe !important;
    font-family: 'DM Mono', monospace !important;
    font-size: 0.75rem !important;
}
span[data-baseweb="tag"] span { color: #ff4dbe !important; -webkit-text-fill-color: #ff4dbe !important; }

/* ── Label above multiselect ── */
[data-testid="stMultiSelect"] label p {
    color: rgba(255,255,255,0.6) !important;
    -webkit-text-fill-color: rgba(255,255,255,0.6) !important;
    font-size: 0.82rem !important;
}

/* ── Divider ── */
hr {
    border: none !important;
    border-top: 1px solid rgba(255,255,255,0.08) !important;
    margin: 2rem 0 !important;
}

/* ── Scrollbar ── */
::-webkit-scrollbar { width: 4px; height: 4px; }
::-webkit-scrollbar-track { background: #1a1a2e; }
::-webkit-scrollbar-thumb { background: rgba(255,255,255,0.15); border-radius: 4px; }
::-webkit-scrollbar-thumb:hover { background: #ff4dbe; }

/* ── Spinner ── */
[data-testid="stSpinner"] p { color: #ff4dbe !important; }
</style>
""", unsafe_allow_html=True)

# ── Header ────────────────────────────────────────────────────────────────────
st.markdown("""
<div class="title-wrap">
    <div class="main-title">Migration<span class="pink">Pulse</span></div>
    <div class="subtitle-line">// Live Bald Eagle Migration Analytics — Pacific Northwest</div>
</div>
""", unsafe_allow_html=True)

# ── Load Data ─────────────────────────────────────────────────────────────────
@st.cache_data
def load_silver_data():
    s3 = boto3.client(
        's3',
        aws_access_key_id=os.environ.get('AWS_ACCESS_KEY_ID'),
        aws_secret_access_key=os.environ.get('AWS_SECRET_ACCESS_KEY'),
        region_name='us-east-2'
    )
    objs = sorted([
        o['Key'] for o in s3.list_objects_v2(
            Bucket='migrationpulse-silver',
            Prefix='bald_eagle/'
        )['Contents']
    ], reverse=True)
    obj = s3.get_object(Bucket='migrationpulse-silver', Key=objs[0])
    df = pd.read_parquet(io.BytesIO(obj['Body'].read()))
    df['timestamp'] = pd.to_datetime(df['timestamp'], utc=True)
    return df

with st.spinner("Loading eagle GPS data from S3..."):
    df = load_silver_data()

# ── Summary Cards ─────────────────────────────────────────────────────────────
st.markdown('<div class="sec-label">Weekly Summary</div>', unsafe_allow_html=True)
c1, c2, c3, c4 = st.columns(4)
c1.metric("Total GPS Fixes", f"{len(df):,}")
c2.metric("Individuals Tracked", df['individual_id'].nunique())
c3.metric("Date Range", f"{df['timestamp'].min().date()} → {df['timestamp'].max().date()}")
c4.metric("Species", df['species'].nunique())

st.divider()

# ── Individual Selector ───────────────────────────────────────────────────────
st.markdown('<div class="sec-label">Migration Map</div>', unsafe_allow_html=True)
individuals = sorted(df['individual_id'].unique())
selected = st.multiselect("Select individuals to display:", individuals, default=individuals[:3])
filtered = df[df['individual_id'].isin(selected)].sort_values('timestamp')

# ── Color palette: pink, green, yellow, white, cyan, orange ──────────────────
MAP_COLORS    = [[255, 77, 190], [57, 255, 143], [255, 230, 0], [255, 255, 255], [0, 220, 255], [255, 120, 50]]
PLOTLY_COLORS = ["#ff4dbe",     "#39ff8f",       "#ffe600",     "#ffffff",       "#00dcff",      "#ff7832"]

# ── Map ───────────────────────────────────────────────────────────────────────
layers = []
for i, ind in enumerate(selected):
    ind_df = filtered[filtered['individual_id'] == ind].sort_values('timestamp')
    col = MAP_COLORS[i % len(MAP_COLORS)]

    layers.append(pdk.Layer(
        "PathLayer",
        data=[{"path": list(zip(ind_df['location_long'].tolist(), ind_df['location_lat'].tolist())), "individual_id": ind}],
        get_path="path",
        get_color=col,
        width_min_pixels=2,
        pickable=True,
    ))
    layers.append(pdk.Layer(
        "ScatterplotLayer",
        data=ind_df[['location_lat', 'location_long', 'individual_id']].rename(columns={'location_long': 'lon', 'location_lat': 'lat'}),
        get_position='[lon, lat]',
        get_color=col,
        get_radius=5000,
        pickable=True,
    ))

view = pdk.ViewState(
    latitude=filtered['location_lat'].mean(),
    longitude=filtered['location_long'].mean(),
    zoom=5, pitch=0,
)

st.pydeck_chart(pdk.Deck(
    layers=layers,
    initial_view_state=view,
    map_style="https://basemaps.cartocdn.com/gl/positron-gl-style/style.json",
    tooltip={"text": "{individual_id}"},
))

st.divider()

# ── Latitude Over Time ────────────────────────────────────────────────────────
st.markdown('<div class="sec-label">Latitude Over Time — Migration Progress</div>', unsafe_allow_html=True)

fig = go.Figure()
for i, ind in enumerate(selected):
    ind_df = filtered[filtered['individual_id'] == ind].sort_values('timestamp')
    fig.add_trace(go.Scatter(
        x=ind_df['timestamp'],
        y=ind_df['location_lat'],
        mode='lines',
        name=ind,
        line=dict(color=PLOTLY_COLORS[i % len(PLOTLY_COLORS)], width=2),
    ))

fig.update_layout(
    paper_bgcolor='rgba(0,0,0,0)',
    plot_bgcolor='rgba(255,255,255,0.04)',
    font=dict(family='DM Mono, monospace', color='rgba(255,255,255,0.6)', size=11),
    xaxis=dict(
        gridcolor='rgba(255,255,255,0.07)',
        linecolor='rgba(255,255,255,0.1)',
        tickfont=dict(color='rgba(255,255,255,0.5)'),
        showgrid=True,
    ),
    yaxis=dict(
        gridcolor='rgba(255,255,255,0.07)',
        linecolor='rgba(255,255,255,0.1)',
        tickfont=dict(color='rgba(255,255,255,0.5)'),
        title=dict(text='Latitude', font=dict(color='rgba(255,255,255,0.4)')),
        showgrid=True,
    ),
    legend=dict(
        bgcolor='rgba(255,255,255,0.05)',
        bordercolor='rgba(255,255,255,0.1)',
        borderwidth=1,
        font=dict(color='#ffffff', size=11),
    ),
    margin=dict(l=50, r=20, t=20, b=40),
    height=380,
)

st.plotly_chart(fig, use_container_width=True)

st.divider()

# ── Raw Data Explorer ─────────────────────────────────────────────────────────
st.markdown('<div class="sec-label">Raw Data Explorer</div>', unsafe_allow_html=True)
st.dataframe(
    filtered[['individual_id', 'timestamp', 'location_lat', 'location_long', 'species']]
    .sort_values('timestamp', ascending=False),
    use_container_width=True,
)