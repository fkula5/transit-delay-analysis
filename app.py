import streamlit as st
import pandas as pd
import pymongo
import pydeck as pdk
from datetime import datetime, timedelta
import plotly.express as px
import plotly.graph_objects as go
from gtfs_client import pobierz_dane_gtfs_rt

MONGO_CONNECTION_STRING = "mongodb://localhost:27017/"
NAZWA_BAZY = "ztm_rzeszow_data"

st.set_page_config(
    layout="wide", 
    page_title="Monitoring ZTM Rzeszów",
    page_icon="🚌"
)

MAPA_DNI = {
    'Monday': 'Poniedziałek', 'Tuesday': 'Wtorek', 'Wednesday': 'Środa',
    'Thursday': 'Czwartek', 'Friday': 'Piątek', 'Saturday': 'Sobota', 'Sunday': 'Niedziela'
}
KOLEJNOSC_DNI = ['Poniedziałek', 'Wtorek', 'Środa', 'Czwartek', 'Piątek', 'Sobota', 'Niedziela']

@st.cache_resource
def polacz_mongodb():
    try:
        client = pymongo.MongoClient(MONGO_CONNECTION_STRING, serverSelectionTimeoutMS=2000)
        client.admin.command('ping')
        return client
    except Exception as e:
        st.error(f"Błąd połączenia: {e}")
        return None

@st.cache_data(ttl=300)
def zaladuj_opoznienia(dni_wstecz=7):
    client = polacz_mongodb()
    if not client: return None
    db = client[NAZWA_BAZY]
    collection = db["opoznienia"]
    data_od = datetime.now() - timedelta(days=dni_wstecz)
    opoznienia = list(collection.find({'timestamp': {'$gte': data_od}}))
    if not opoznienia: return None
    df = pd.DataFrame(opoznienia)
    df['timestamp'] = pd.to_datetime(df['timestamp'])
    df['hour'] = df['timestamp'].dt.hour
    df['day_of_week'] = df['timestamp'].dt.day_name().map(MAPA_DNI)
    df['date'] = df['timestamp'].dt.date
    return df

@st.cache_data(ttl=60)
def pobierz_dane_z_cache():
    return pobierz_dane_gtfs_rt()

with st.sidebar:
    st.image("https://upload.wikimedia.org/wikipedia/commons/thumb/2/2d/POL_Rzesz%C3%B3w_COA.svg/960px-POL_Rzesz%C3%B3w_COA.svg.png", width=200)
    st.title("Panel Sterowania")
    if st.button("Odśwież widok", use_container_width=True, type="primary"):
        pobierz_dane_z_cache.clear()
        zaladuj_opoznienia.clear()
        st.rerun()
    st.divider()
    dni_wstecz = st.select_slider("Pokaż dane z ostatnich:", options=[1, 3, 7, 14, 30], value=7)
    st.divider()
    st.info("**Status systemu:**\n\n✅ Połączono z GTFS-RT\n✅ Baza MongoDB: Aktywna")

st.title("🚌 System Monitoringu Komunikacji Miejskiej - Rzeszów")
tab1, tab2 = st.tabs(["Mapa na żywo", "Statystyki opóźnień"])

with tab1:
    dane, timestamp_serwera = pobierz_dane_z_cache()
    if dane:
        df = pd.DataFrame(dane)
        m1, m2, m3, m4 = st.columns(4)
        m1.metric("Pojazdy w trasie", f"{len(df)} szt.")
        m2.metric("Śr. prędkość", f"{df['predkosc_kmh'].mean():.1f} km/h")
        m3.metric("Aktywne linie", df['route_id'].nunique())
        m4.metric("Aktualizacja", timestamp_serwera.strftime("%H:%M:%S") if timestamp_serwera else "--:--")

        def get_status_color(speed):
            if speed < 5: return [231, 76, 60, 200]
            if speed < 25: return [241, 196, 15, 200]
            return [46, 204, 113, 200]

        df['color'] = df['predkosc_kmh'].apply(get_status_color)
        view_state = pdk.ViewState(latitude=df['lat'].mean(), longitude=df['lon'].mean(), zoom=12, pitch=30)

        st.pydeck_chart(pdk.Deck(
            layers=[pdk.Layer(
                "ScatterplotLayer", df, get_position=["lon", "lat"],
                get_fill_color="color", get_radius=60, pickable=True, auto_highlight=True
            )],
            initial_view_state=view_state,
            tooltip={
                "html": "<b>Linia: {route_id}</b><br/>Pojazd: {id_pojazdu}<br/>Prędkość: <b>{predkosc_kmh} km/h</b>",
                "style": {"background": "#1e3a8a", "color": "white", "font-family": "Arial"}
            }
        ))
        st.markdown("""<div style="display: flex; gap: 20px; font-size: 0.8em; justify-content: center;">
            <span style="color: #e74c3c;">● Postój</span> <span style="color: #f1c40f;">● Wolno</span> <span style="color: #2ecc71;">● Płynnie</span>
        </div>""", unsafe_allow_html=True)
    else:
        st.error("Brak danych GTFS-RT.")

with tab2:
    st.header(f"Analiza punktualności ({dni_wstecz} dni)")
    df_delays = zaladuj_opoznienia(dni_wstecz)
    if df_delays is not None:
        col1, col2, col3, col4 = st.columns(4)
        col1.metric("Pomiary", f"{len(df_delays):,}")
        avg_d = df_delays['delay_minutes'].mean()
        col2.metric("Śr. opóźnienie", f"{avg_d:.2f} min", delta_color="inverse")
        on_time = (len(df_delays[df_delays['delay_minutes'].abs() <= 2]) / len(df_delays)) * 100
        col3.metric("Punktualność (±2 min)", f"{on_time:.1f}%")
        col4.metric("Max opóźnienie", f"{df_delays['delay_minutes'].max():.0f} min")

        st.divider()
        fig_hist = px.histogram(df_delays, x='delay_minutes', nbins=40, title='<b>Rozkład opóźnień</b>',
                               labels={'delay_minutes': 'Minuty', 'count': 'Liczba'}, color_discrete_sequence=['#3498db'])
        fig_hist.add_vline(x=0, line_dash="dash", line_color="#2ecc71", annotation_text="O czasie")
        st.plotly_chart(fig_hist, use_container_width=True)

        c1, c2 = st.columns(2)
        
        with c1:
            st.subheader("Opóźnienia a pora dnia")
            hourly = df_delays.groupby('hour')['delay_minutes'].mean().reset_index()
            fig_h = px.line(hourly, x='hour', y='delay_minutes', 
                           labels={'hour': 'Godzina', 'delay_minutes': 'Śr. opóźnienie (min)'},
                           markers=True)
            fig_h.update_traces(line_color='#e67e22')
            st.plotly_chart(fig_h, use_container_width=True)

        with c2:
            st.subheader("Opóźnienia a dzień tygodnia")
            daily = df_delays.groupby('day_of_week')['delay_minutes'].mean().reindex(KOLEJNOSC_DNI).reset_index()
            fig_d = px.bar(daily, x='day_of_week', y='delay_minutes',
                          labels={'day_of_week': 'Dzień tygodnia', 'delay_minutes': 'Śr. opóźnienie (min)'},
                          color='delay_minutes', color_continuous_scale='Reds')
            st.plotly_chart(fig_d, use_container_width=True)

        st.subheader("Mapa opóźnień na przystankach")
        map_stops = df_delays.groupby(['stop_name', 'lat', 'lon'])['delay_minutes'].mean().reset_index()
        map_stops['color'] = map_stops['delay_minutes'].apply(
            lambda x: [231, 76, 60, 200] if x > 3 else ([241, 196, 15, 200] if x > 1 else [46, 204, 113, 200])
        )

        st.pydeck_chart(pdk.Deck(
            layers=[pdk.Layer(
                "ScatterplotLayer", map_stops, get_position=["lon", "lat"],
                get_radius="delay_minutes * 30 + 50", get_fill_color="color", pickable=True
            )],
            initial_view_state=pdk.ViewState(latitude=map_stops['lat'].mean(), longitude=map_stops['lon'].mean(), zoom=12),
            tooltip={
                "html": "<b>Przystanek: {stop_name}</b><br/>Średnie opóźnienie: <b>{delay_minutes} min</b>",
                "style": {"background": "#1e3a8a", "color": "white", "font-family": "Arial"}
            }
        ))
    else:
        st.warning("Brak danych historycznych.")

st.divider()
st.caption(f"Ostatnia sesja: {datetime.now().strftime('%d.%m.%Y %H:%M')}")