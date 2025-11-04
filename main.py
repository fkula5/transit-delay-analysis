# Zapisz ten kod jako app.py

import streamlit as st
import requests
import pandas as pd
from google.transit import gtfs_realtime_pb2
from datetime import datetime

# --- Konfiguracja ---
# WAŻNE: Wejdź na stronę https://www.mpkrzeszow.pl/otwartedane/
# Znajdź sekcję "GTFS Realtime", kliknij prawym na "Skopiuj link (.pb)" i wklej go poniżej:
GTFS_RT_URL = "https://www.mpkrzeszow.pl/gtfs/rt/gtfsrt.pb" 

# --- Funkcja do pobierania i parsowania danych ---
@st.cache_data(ttl=60) # Dodajemy cache Streamlit - odświeży dane max co 60 sekund
def pobierz_dane_gtfs_rt(url):
    """
    Pobiera i parsuje dane GTFS-Realtime (pozycje pojazdów) z podanego URL.
    Zwraca listę słowników z danymi pojazdów.
    """
    
    dane_pojazdow = []

    try:
        response = requests.get(url)
        response.raise_for_status() 

        feed = gtfs_realtime_pb2.FeedMessage()
        feed.ParseFromString(response.content)
        
        timestamp_feed = datetime.fromtimestamp(feed.header.timestamp)

        for entity in feed.entity:
            if entity.HasField('vehicle'):
                vehicle = entity.vehicle
                position = vehicle.position
                trip = vehicle.trip
                
                timestamp_vehicle = "Brak"
                if vehicle.HasField('timestamp'):
                     timestamp_vehicle = datetime.fromtimestamp(vehicle.timestamp)

                dane_pojazdow.append({
                    'id_pojazdu': vehicle.vehicle.id,
                    'trip_id': trip.trip_id,
                    'route_id': trip.route_id,
                    'lat': position.latitude,
                    'lon': position.longitude,
                    'predkosc_kmh': round(position.speed * 3.6, 2), # m/s na km/h
                    'timestamp_danych': timestamp_vehicle,
                })
        
        return dane_pojazdow, timestamp_feed

    except requests.exceptions.RequestException as e:
        # Zamiast st.error, zwracamy błąd, aby aplikacja mogła go obsłużyć
        print(f"Błąd pobierania danych: {e}")
        return None, None
    except Exception as e:
        print(f"Błąd parsowania danych: {e}")
        return None, None

# --- Budowanie interfejsu aplikacji Streamlit ---

st.set_page_config(layout="wide")
st.title("🚌 Analizator Komunikacji Miejskiej (Rzeszów)")
st.caption("Prototyp w ramach projektu 'Analiza danych w R i Python'")

if GTFS_RT_URL == "TUTAJ_WKLEJ_LINK_ZE_STRONY_MPK":
    st.error("BŁĄD KONFIGURACJI: Musisz edytować plik app.py i wkleić poprawny URL do danych GTFS-RT!")
    st.info(f"Link znajdziesz na stronie: https://www.mpkrzeszow.pl/otwartedane/")
else:
    # Używamy st.rerun(), aby stworzyć pętlę auto-odświeżania
    if st.button("Odśwież dane manualnie"):
        st.cache_data.clear() # Czyści cache, aby wymusić pobranie nowych danych

    dane, timestamp_serwera = pobierz_dane_gtfs_rt(GTFS_RT_URL)
    
    if dane:
        st.success(f"Pobrano dane! Czas serwera: {timestamp_serwera}. Aktywne pojazdy: {len(dane)}")
        
        df = pd.DataFrame(dane)
        
        # Mapa
        st.subheader("Mapa aktywnych pojazdów")
        st.map(df, latitude='lat', longitude='lon') 
        
        # Tabela
        st.subheader("Surowe dane (próbka)")
        st.dataframe(df.head())
        
        # Automatyczne odświeżenie (opcjonalnie, ale fajne)
        # st.experimental_rerun(ttl=60) # To jest przestarzałe, zostajemy przy cache
        
    else:
        st.error("Nie udało się pobrać ani przetworzyć danych. Sprawdź logi terminala.")