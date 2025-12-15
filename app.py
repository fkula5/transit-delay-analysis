import streamlit as st
import pandas as pd
import pymongo
from datetime import datetime, timedelta
import plotly.express as px
import plotly.graph_objects as go
from gtfs_client import pobierz_dane_gtfs_rt

MONGO_CONNECTION_STRING = "mongodb://localhost:27017/"
NAZWA_BAZY = "ztm_rzeszow_data"

st.set_page_config(
    layout="wide", 
    page_title="Analiza Komunikacji Miejskiej - Rzeszów",
    page_icon="🚌"
)

@st.cache_resource
def polacz_mongodb():
    try:
        client = pymongo.MongoClient(MONGO_CONNECTION_STRING)
        client.admin.command('ping')
        return client
    except Exception as e:
        st.error(f"Błąd połączenia z MongoDB: {e}")
        return None

@st.cache_data(ttl=300)
def zaladuj_opoznienia(dni_wstecz=7):
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

@st.cache_data(ttl=60)
def pobierz_dane_z_cache():
    return pobierz_dane_gtfs_rt()

st.title("🚌 System Monitoringu Komunikacji Miejskiej - Rzeszów")
st.caption("Mapa w czasie rzeczywistym i analiza opóźnień")

with st.sidebar:
    st.header("⚙️ Ustawienia")
    
    if st.button("🔄 Odśwież dane", use_container_width=True):
        pobierz_dane_z_cache.clear()
        zaladuj_opoznienia.clear()
        st.rerun()
    
    st.divider()
    
    st.subheader("Analiza opóźnień")
    dni_wstecz = st.slider("Dane z ostatnich dni:", 1, 30, 7)
    
    st.divider()
    
    st.caption("💡 **Wskazówki:**")
    st.caption("• Dane odświeżają się co 60s")
    st.caption("• Uruchom data_collector.py dla ciągłego zbierania danych")
    st.caption("• Uruchom delay_calculator.py dla analizy opóźnień")

tab1, tab2 = st.tabs(["🗺️ Mapa na żywo", "📊 Analiza opóźnień"])

with tab1:
    st.header("Aktualna pozycja autobusów")
    
    dane, timestamp_serwera = pobierz_dane_z_cache()
    
    if dane:
        df = pd.DataFrame(dane)
        
        col1, col2, col3, col4 = st.columns(4)
        
        with col1:
            st.metric(
                "🚌 Aktywne pojazdy",
                len(df),
                help="Liczba autobusów aktualnie w ruchu"
            )
        
        with col2:
            avg_speed = df['predkosc_kmh'].mean()
            st.metric(
                "⚡ Średnia prędkość",
                f"{avg_speed:.1f} km/h",
                help="Średnia prędkość wszystkich pojazdów"
            )
        
        with col3:
            unique_routes = df['route_id'].nunique()
            st.metric(
                "🛣️ Aktywne linie",
                unique_routes,
                help="Liczba różnych linii w ruchu"
            )
        
        with col4:
            st.metric(
                "🕐 Aktualizacja",
                timestamp_serwera.strftime("%H:%M:%S") if timestamp_serwera else "N/A",
                help="Czas ostatniej aktualizacji danych"
            )
        
        st.divider()
        
        st.subheader("📍 Mapa pozycji")
        
        def get_color(speed):
            if speed < 5:
                return [255, 0, 0, 160]
            elif speed < 20:
                return [255, 165, 0, 160]
            else:
                return [0, 255, 0, 160]
        
        df['color'] = df['predkosc_kmh'].apply(get_color)
        
        import pydeck as pdk
        
        layer = pdk.Layer(
            "ScatterplotLayer",
            data=df,
            get_position=["lon", "lat"],
            get_radius=50,
            get_fill_color="color",
            pickable=True,
        )
        
        view_state = pdk.ViewState(
            latitude=df['lat'].mean(),
            longitude=df['lon'].mean(),
            zoom=12,
            pitch=0,
        )
        
        r = pdk.Deck(
            layers=[layer],
            initial_view_state=view_state,
            tooltip={
                "html": "<b>🚌 Pojazd {id_pojazdu}</b><br>"
                        "Linia: {route_id}<br>"
                        "Prędkość: {predkosc_kmh} km/h<br>"
                        "Trip: {trip_id}",
                "style": {"color": "white"}
            }
        )
        
        st.pydeck_chart(r)
        
        st.caption("🔴 Stoi (<5 km/h)  🟠 Wolno (5-20 km/h)  🟢 Jedzie (>20 km/h)")
        
        st.subheader("📈 Statystyki według linii")
        
        col1, col2 = st.columns(2)
        
        with col1:
            route_counts = df.groupby('route_id').size().reset_index(name='count').sort_values('count', ascending=False).head(10)
            
            fig_routes = px.bar(
                route_counts,
                x='route_id',
                y='count',
                title='TOP 10 linii z największą liczbą pojazdów',
                labels={'route_id': 'Linia', 'count': 'Liczba pojazdów'},
                color='count',
                color_continuous_scale='Blues'
            )
            st.plotly_chart(fig_routes, use_container_width=True)
        
        with col2:
            route_speeds = df.groupby('route_id')['predkosc_kmh'].mean().reset_index().sort_values('predkosc_kmh', ascending=False).head(10)
            
            fig_speeds = px.bar(
                route_speeds,
                x='route_id',
                y='predkosc_kmh',
                title='TOP 10 linii z największą średnią prędkością',
                labels={'route_id': 'Linia', 'predkosc_kmh': 'Średnia prędkość (km/h)'},
                color='predkosc_kmh',
                color_continuous_scale='RdYlGn'
            )
            st.plotly_chart(fig_speeds, use_container_width=True)
        
        with st.expander("📋 Szczegółowe dane wszystkich pojazdów"):
            st.dataframe(
                df[['id_pojazdu', 'route_id', 'trip_id', 'lat', 'lon', 'predkosc_kmh', 'timestamp_danych']].sort_values('route_id'),
                use_container_width=True,
                height=400
            )
    
    else:
        st.error("❌ Nie udało się pobrać danych z API. Sprawdź logi terminala.")
        st.info("""
        **Możliwe przyczyny:**
        - API MPK Rzeszów nie odpowiada
        - Problem z połączeniem internetowym
        - Serwer GTFS-RT jest niedostępny
        
        Spróbuj odświeżyć za chwilę.
        """)

with tab2:
    st.header("Analiza historycznych opóźnień")
    
    with st.spinner("Ładowanie danych o opóźnieniach..."):
        df_delays = zaladuj_opoznienia(dni_wstecz)
    
    if df_delays is None or len(df_delays) == 0:
        st.warning(f"""
        ### 📭 Brak danych o opóźnieniach z ostatnich {dni_wstecz} dni
        
        **Co należy zrobić:**
        
        1. ✅ **Zbierz dane** (jeśli nie działa):
           ```bash
           python data_collector.py
           ```
           Pozostaw uruchomione na kilka godzin
        
        2. 🧮 **Oblicz opóźnienia**:
           ```bash
           python delay_calculator.py
           ```
           Wybierz opcję **1** (przetwórz ostatnie 100 odczytów)
        
        3. 🔄 **Odśwież tę stronę**
        
        **💡 Wskazówka:** Więcej danych będzie dostępnych w godzinach szczytu (7-9, 15-18)
        
        ---
        
        **🔍 Diagnostyka:**
        Uruchom `python debug_checker.py` aby sprawdzić status systemu.
        """)
    else:
        col1, col2, col3, col4 = st.columns(4)
        
        with col1:
            st.metric(
                "📊 Pomiary",
                f"{len(df_delays):,}",
                help="Liczba zarejestrowanych opóźnień"
            )
        
        with col2:
            avg_delay = df_delays['delay_minutes'].mean()
            st.metric(
                "⏱️ Średnie opóźnienie",
                f"{avg_delay:.1f} min",
                delta=f"{avg_delay - df_delays['delay_minutes'].median():.1f} vs mediana",
                help="Średnie opóźnienie wszystkich kursów"
            )
        
        with col3:
            on_time = len(df_delays[df_delays['delay_minutes'].abs() <= 1])
            on_time_pct = (on_time / len(df_delays)) * 100
            st.metric(
                "✅ Punktualność",
                f"{on_time_pct:.1f}%",
                help="Procent kursów z opóźnieniem ≤1 min"
            )
        
        with col4:
            max_delay = df_delays['delay_minutes'].max()
            st.metric(
                "🔴 Max opóźnienie",
                f"{max_delay:.0f} min",
                help="Największe zarejestrowane opóźnienie"
            )
        
        st.divider()
        
        st.subheader("📈 Rozkład opóźnień")
        
        fig_hist = px.histogram(
            df_delays,
            x='delay_minutes',
            nbins=50,
            title='Histogram opóźnień',
            labels={'delay_minutes': 'Opóźnienie (minuty)', 'count': 'Liczba przypadków'},
            color_discrete_sequence=['#FF6B6B']
        )
        fig_hist.add_vline(x=0, line_dash="dash", line_color="green", annotation_text="Na czas")
        fig_hist.update_layout(showlegend=False)
        st.plotly_chart(fig_hist, use_container_width=True)
        
        col1, col2 = st.columns(2)
        
        with col1:
            st.subheader("🕐 Według godziny")
            hourly = df_delays.groupby('hour')['delay_minutes'].agg(['mean', 'count']).reset_index()
            
            fig_hour = go.Figure()
            fig_hour.add_trace(go.Bar(
                x=hourly['hour'],
                y=hourly['mean'],
                name='Średnie opóźnienie',
                marker_color='#4ECDC4',
                hovertemplate='Godzina: %{x}:00<br>Opóźnienie: %{y:.1f} min<extra></extra>'
            ))
            fig_hour.update_layout(
                xaxis_title='Godzina dnia',
                yaxis_title='Średnie opóźnienie (min)',
                showlegend=False
            )
            st.plotly_chart(fig_hour, use_container_width=True)
        
        with col2:
            st.subheader("📅 Według dnia tygodnia")
            
            day_order = ['Monday', 'Tuesday', 'Wednesday', 'Thursday', 'Friday', 'Saturday', 'Sunday']
            day_names_pl = {'Monday': 'Pn', 'Tuesday': 'Wt', 'Wednesday': 'Śr', 
                           'Thursday': 'Cz', 'Friday': 'Pt', 'Saturday': 'So', 'Sunday': 'Nd'}
            
            df_delays['day_of_week'] = pd.Categorical(df_delays['day_of_week'], categories=day_order, ordered=True)
            daily = df_delays.groupby('day_of_week')['delay_minutes'].mean().reset_index()
            daily['day_pl'] = daily['day_of_week'].map(day_names_pl)
            
            fig_day = px.bar(
                daily,
                x='day_pl',
                y='delay_minutes',
                labels={'day_pl': 'Dzień tygodnia', 'delay_minutes': 'Średnie opóźnienie (min)'},
                color='delay_minutes',
                color_continuous_scale='RdYlGn_r'
            )
            st.plotly_chart(fig_day, use_container_width=True)
        
        st.divider()
        
        col1, col2 = st.columns(2)
        
        with col1:
            st.subheader("🚍 TOP 10 linii z opóźnieniami")
            
            top_routes = df_delays.groupby('route_short_name').agg({
                'delay_minutes': 'mean',
                'trip_id': 'count'
            }).round(2)
            top_routes.columns = ['Średnie opóźnienie (min)', 'Liczba pomiarów']
            top_routes = top_routes.sort_values('Średnie opóźnienie (min)', ascending=False).head(10)
            
            st.dataframe(
                top_routes,
                use_container_width=True
            )
        
        with col2:
            st.subheader("📍 TOP 10 przystanków z opóźnieniami")
            
            top_stops = df_delays.groupby('stop_name').agg({
                'delay_minutes': 'mean',
                'trip_id': 'count'
            }).round(2)
            top_stops.columns = ['Średnie opóźnienie (min)', 'Liczba pomiarów']
            top_stops = top_stops.sort_values('Średnie opóźnienie (min)', ascending=False).head(10)
            
            st.dataframe(
                top_stops,
                use_container_width=True
            )
        
        st.subheader("🗺️ Mapa średnich opóźnień na przystankach")
        
        map_data = df_delays.groupby(['stop_name', 'lat', 'lon']).agg({
            'delay_minutes': 'mean'
        }).reset_index()
        
        map_data['color'] = map_data['delay_minutes'].apply(
            lambda x: [0, 255, 0, 160] if x < 0 else ([255, 255, 0, 160] if x < 2 else [255, 0, 0, 160])
        )
        
        import pydeck as pdk
        
        layer = pdk.Layer(
            "ScatterplotLayer",
            data=map_data,
            get_position=["lon", "lat"],
            get_radius=100,
            get_fill_color="color",
            pickable=True,
        )
        
        view_state = pdk.ViewState(
            latitude=map_data['lat'].mean(),
            longitude=map_data['lon'].mean(),
            zoom=12,
            pitch=0,
        )
        
        r = pdk.Deck(
            layers=[layer],
            initial_view_state=view_state,
            tooltip={
                "html": "<b>{stop_name}</b><br>Średnie opóźnienie: {delay_minutes:.1f} min",
                "style": {"color": "white"}
            }
        )
        
        st.pydeck_chart(r)
        
        st.caption("🟢 Bez opóźnień (<0 min)  🟡 Małe (0-2 min)  🔴 Duże (>2 min)")
        
        st.subheader("📊 Trend opóźnień w czasie")
        
        daily_trend = df_delays.groupby('date')['delay_minutes'].mean().reset_index()
        daily_trend['date'] = pd.to_datetime(daily_trend['date'])
        
        fig_trend = px.line(
            daily_trend,
            x='date',
            y='delay_minutes',
            labels={'date': 'Data', 'delay_minutes': 'Średnie opóźnienie (min)'},
            markers=True
        )
        fig_trend.update_traces(line_color='#FF6B6B', line_width=3)
        fig_trend.add_hline(y=0, line_dash="dash", line_color="green", annotation_text="Brak opóźnienia")
        st.plotly_chart(fig_trend, use_container_width=True)
        
        # Szczegółowe dane
        with st.expander("📋 Szczegółowe dane (ostatnie 100 wpisów)"):
            st.dataframe(
                df_delays[['timestamp', 'route_short_name', 'trip_headsign', 'stop_name', 
                          'delay_minutes', 'vehicle_id']].tail(100).sort_values('timestamp', ascending=False),
                use_container_width=True,
                height=400
            )

# Footer
st.divider()
col1, col2, col3 = st.columns(3)
with col1:
    st.caption(f"🕐 Ostatnia aktualizacja: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
with col2:
    st.caption(f"📊 Analiza: {dni_wstecz} dni wstecz")
with col3:
    st.caption("💾 Dane: MongoDB + GTFS-RT")