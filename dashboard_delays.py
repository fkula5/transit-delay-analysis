import streamlit as st
import pandas as pd
import pymongo
from datetime import datetime, timedelta
import plotly.express as px
import plotly.graph_objects as go

MONGO_CONNECTION_STRING = "mongodb://localhost:27017/"
NAZWA_BAZY = "ztm_rzeszow_data"

st.set_page_config(layout="wide", page_title="Analiza Opóźnień - Rzeszów")

@st.cache_resource
def polacz_mongodb():
    """Połączenie z MongoDB (cache)"""
    try:
        client = pymongo.MongoClient(MONGO_CONNECTION_STRING)
        client.admin.command('ping')
        return client
    except Exception as e:
        st.error(f"Błąd połączenia z MongoDB: {e}")
        return None

@st.cache_data(ttl=300)
def zaladuj_opoznienia(dni_wstecz=7):
    """Ładuje dane o opóźnieniach z ostatnich N dni"""
    client = polacz_mongodb()
    if not client:
        return None
    
    db = client[NAZWA_BAZY]
    collection = db["opoznienia"]
    
    data_od = datetime.now() - timedelta(days=dni_wstecz)
    
    opoznienia = list(collection.find({
        'timestamp': {'$gte': data_od}
    }))
    
    if not opoznienia:
        return None
    
    df = pd.DataFrame(opoznienia)
    df['timestamp'] = pd.to_datetime(df['timestamp'])
    df['hour'] = df['timestamp'].dt.hour
    df['day_of_week'] = df['timestamp'].dt.day_name()
    df['date'] = df['timestamp'].dt.date
    
    return df

st.title("🚌 Analiza Opóźnień Komunikacji Miejskiej")
st.caption("Rzeszów - System monitoringu i analizy opóźnień")

with st.sidebar:
    st.header("⚙️ Ustawienia")
    dni_wstecz = st.slider("Dane z ostatnich dni:", 1, 30, 7)
    
    if st.button("🔄 Odśwież dane", use_container_width=True):
        zaladuj_opoznienia.clear()
        st.rerun()

with st.spinner("Ładowanie danych o opóźnieniach..."):
    df = zaladuj_opoznienia(dni_wstecz)

if df is None or len(df) == 0:
    st.warning("""
    ### Brak danych o opóźnieniach
    
    **Prawdopodobne przyczyny:**
    1. Kolektor danych nie jest uruchomiony (`data_collector.py`)
    2. Kalkulator opóźnień nie przetworzył jeszcze danych (uruchom `delay_calculator.py`)
    3. MongoDB nie zawiera danych
    
    **Jak naprawić:**
    ```bash
    # Uruchom kolektor (w osobnym terminalu)
    python data_collector.py
    
    # Poczekaj kilka minut, potem uruchom kalkulator
    python delay_calculator.py
    ```
    """)
    st.stop()

col1, col2, col3, col4 = st.columns(4)

with col1:
    st.metric(
        "📊 Łączna liczba pomiarów",
        f"{len(df):,}",
        help="Liczba zarejestrowanych opóźnień"
    )

with col2:
    avg_delay = df['delay_minutes'].mean()
    st.metric(
        "⏱️ Średnie opóźnienie",
        f"{avg_delay:.1f} min",
        delta=f"{avg_delay - df['delay_minutes'].median():.1f} min vs mediana",
        help="Średnie opóźnienie wszystkich pojazdów"
    )

with col3:
    on_time = len(df[df['delay_minutes'].abs() <= 1])
    on_time_pct = (on_time / len(df)) * 100
    st.metric(
        "✅ Punktualność",
        f"{on_time_pct:.1f}%",
        help="Procent kursów z opóźnieniem ≤1 min"
    )

with col4:
    max_delay = df['delay_minutes'].max()
    st.metric(
        "🔴 Maksymalne opóźnienie",
        f"{max_delay:.0f} min",
        help="Największe zarejestrowane opóźnienie"
    )

st.subheader("📈 Rozkład opóźnień")

fig_hist = px.histogram(
    df,
    x='delay_minutes',
    nbins=50,
    title='Histogram opóźnień',
    labels={'delay_minutes': 'Opóźnienie (minuty)', 'count': 'Liczba przypadków'},
    color_discrete_sequence=['#FF6B6B']
)
fig_hist.update_layout(showlegend=False)
st.plotly_chart(fig_hist, use_container_width=True)

col1, col2 = st.columns(2)

with col1:
    st.subheader("🕐 Opóźnienia według godziny")
    hourly = df.groupby('hour')['delay_minutes'].agg(['mean', 'count']).reset_index()
    
    fig_hour = go.Figure()
    fig_hour.add_trace(go.Bar(
        x=hourly['hour'],
        y=hourly['mean'],
        name='Średnie opóźnienie',
        marker_color='#4ECDC4'
    ))
    fig_hour.update_layout(
        xaxis_title='Godzina dnia',
        yaxis_title='Średnie opóźnienie (min)',
        showlegend=False
    )
    st.plotly_chart(fig_hour, use_container_width=True)

with col2:
    st.subheader("📅 Opóźnienia według dnia tygodnia")
    
    day_order = ['Monday', 'Tuesday', 'Wednesday', 'Thursday', 'Friday', 'Saturday', 'Sunday']
    df['day_of_week'] = pd.Categorical(df['day_of_week'], categories=day_order, ordered=True)
    
    daily = df.groupby('day_of_week')['delay_minutes'].mean().reset_index()
    
    fig_day = px.bar(
        daily,
        x='day_of_week',
        y='delay_minutes',
        labels={'day_of_week': 'Dzień tygodnia', 'delay_minutes': 'Średnie opóźnienie (min)'},
        color='delay_minutes',
        color_continuous_scale='RdYlGn_r'
    )
    st.plotly_chart(fig_day, use_container_width=True)

st.subheader("🚍 TOP 10 linii z największymi opóźnieniami")

top_routes = df.groupby('route_short_name').agg({
    'delay_minutes': ['mean', 'count'],
    'trip_id': 'count'
}).round(2)
top_routes.columns = ['Średnie opóźnienie (min)', 'Liczba pomiarów', 'Liczba kursów']
top_routes = top_routes.sort_values('Średnie opóźnienie (min)', ascending=False).head(10)

fig_routes = px.bar(
    top_routes.reset_index(),
    x='route_short_name',
    y='Średnie opóźnienie (min)',
    labels={'route_short_name': 'Linia'},
    color='Średnie opóźnienie (min)',
    color_continuous_scale='RdYlGn_r',
    text='Średnie opóźnienie (min)'
)
fig_routes.update_traces(texttemplate='%{text:.1f}', textposition='outside')
st.plotly_chart(fig_routes, use_container_width=True)

st.subheader("📍 TOP 10 przystanków z największymi opóźnieniami")

top_stops = df.groupby('stop_name').agg({
    'delay_minutes': ['mean', 'count']
}).round(2)
top_stops.columns = ['Średnie opóźnienie (min)', 'Liczba pomiarów']
top_stops = top_stops.sort_values('Średnie opóźnienie (min)', ascending=False).head(10)

col1, col2 = st.columns([2, 1])

with col1:
    fig_stops = px.bar(
        top_stops.reset_index(),
        x='stop_name',
        y='Średnie opóźnienie (min)',
        labels={'stop_name': 'Przystanek'},
        color='Średnie opóźnienie (min)',
        color_continuous_scale='RdYlGn_r'
    )
    st.plotly_chart(fig_stops, use_container_width=True)

with col2:
    st.dataframe(
        top_stops,
        use_container_width=True,
        height=400
    )

st.subheader("🗺️ Mapa średnich opóźnień na przystankach")

map_data = df.groupby(['stop_name', 'lat', 'lon']).agg({
    'delay_minutes': 'mean'
}).reset_index()

map_data['color'] = map_data['delay_minutes'].apply(
    lambda x: [0, 255, 0, 160] if x < 0 else ([255, 255, 0, 160] if x < 2 else [255, 0, 0, 160])
)

st.pydeck_chart(
    {
        "map_style": "mapbox://styles/mapbox/light-v9",
        "initial_view_state": {
            "latitude": map_data['lat'].mean(),
            "longitude": map_data['lon'].mean(),
            "zoom": 12,
            "pitch": 0,
        },
        "layers": [
            {
                "type": "ScatterplotLayer",
                "data": map_data,
                "get_position": ["lon", "lat"],
                "get_radius": 100,
                "get_fill_color": "color",
                "pickable": True,
            }
        ],
        "tooltip": {
            "html": "<b>{stop_name}</b><br>Średnie opóźnienie: {delay_minutes:.1f} min",
            "style": {"color": "white"}
        }
    }
)

st.subheader("📊 Trend opóźnień w czasie")

daily_trend = df.groupby('date')['delay_minutes'].mean().reset_index()
daily_trend['date'] = pd.to_datetime(daily_trend['date'])

fig_trend = px.line(
    daily_trend,
    x='date',
    y='delay_minutes',
    labels={'date': 'Data', 'delay_minutes': 'Średnie opóźnienie (min)'},
    markers=True
)
fig_trend.update_traces(line_color='#FF6B6B', line_width=3)
st.plotly_chart(fig_trend, use_container_width=True)

with st.expander("📋 Szczegółowe dane (ostatnie 100 wpisów)"):
    st.dataframe(
        df[['timestamp', 'route_short_name', 'trip_headsign', 'stop_name', 
            'delay_minutes', 'vehicle_id']].tail(100).sort_values('timestamp', ascending=False),
        use_container_width=True,
        height=400
    )

st.divider()
st.caption(f"Ostatnia aktualizacja: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')} | Dane z ostatnich {dni_wstecz} dni")