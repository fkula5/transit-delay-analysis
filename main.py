import streamlit as st
import pandas as pd

from gtfs_client import pobierz_dane_gtfs_rt


st.set_page_config(layout="wide")
st.title("🚌 Analizator Komunikacji Miejskiej (Rzeszów)")
st.caption("Prototyp w ramach projektu 'Analiza danych w R i Python'")

if st.button("Odśwież dane manualnie", key="refresh_button_sidebar"):
    pobierz_dane_z_cache.clear() 

@st.cache_data(ttl=60)
def pobierz_dane_z_cache():
    return pobierz_dane_gtfs_rt()

dane, timestamp_serwera = pobierz_dane_z_cache()

if dane:
    st.success(f"Pobrano dane! Czas serwera: {timestamp_serwera}. Aktywne pojazdy: {len(dane)}")
    
    df = pd.DataFrame(dane)
    
    st.subheader("Mapa aktywnych pojazdów")
    st.map(df, latitude='lat', longitude='lon') 
    

    st.subheader("Surowe dane (próbka)")
    st.dataframe(df.head())
    
else:
    st.error("Nie udało się pobrać ani przetworzyć danych. Sprawdź logi terminala.")

import streamlit as st
import pandas as pd

from gtfs_client import pobierz_dane_gtfs_rt

st.set_page_config(layout="wide")
st.title("🚌 Analizator Komunikacji Miejskiej (Rzeszów)")
st.caption("Prototyp w ramach projektu 'Analiza danych w R i Python'")

if st.button("Odśwież dane manualnie", key="refresh_button"):
    pobierz_dane_z_cache.clear() 

@st.cache_data(ttl=60)
def pobierz_dane_z_cache():
    return pobierz_dane_gtfs_rt()

dane, timestamp_serwera = pobierz_dane_z_cache()

if dane:
    st.success(f"Pobrano dane! Czas serwera: {timestamp_serwera}. Aktywne pojazdy: {len(dane)}")
    
    df = pd.DataFrame(dane)
    
    st.subheader("Mapa aktywnych pojazdów")
    st.map(df, latitude='lat', longitude='lon') 
    
    st.subheader("Surowe dane (próbka)")
    st.dataframe(df.head())
    
else:
    st.error("Nie udało się pobrać ani przetworzyć danych. Sprawdź logi terminala.")