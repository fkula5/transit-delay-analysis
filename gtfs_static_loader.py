import requests
import zipfile
import io
import pandas as pd
from pathlib import Path
import json
from datetime import datetime, timedelta

GTFS_STATIC_URL = "https://otwartedane.erzeszow.pl/media/resources/gtfs-27-10-2025-31-12-2025-21-10-2025-08-58-31.zip"
GTFS_CACHE_DIR = Path("gtfs_cache")
GTFS_CACHE_FILE = GTFS_CACHE_DIR / "gtfs_static.zip"
GTFS_EXTRACTED_DIR = GTFS_CACHE_DIR / "extracted"
GTFS_CACHE_VALIDITY_HOURS = 24

class GTFSStaticLoader:
    """Klasa do pobierania i ładowania statycznych danych GTFS (rozkłady jazdy)"""
    
    def __init__(self):
        self.trips = None
        self.stop_times = None
        self.stops = None
        self.routes = None
        self.calendar = None
        self.calendar_dates = None
        
    def pobierz_i_zapisz_gtfs(self):
        """Pobiera plik GTFS i zapisuje lokalnie"""
        print("Pobieranie statycznego GTFS...")
        
        GTFS_CACHE_DIR.mkdir(exist_ok=True)
        
        if GTFS_CACHE_FILE.exists():
            file_age = datetime.now() - datetime.fromtimestamp(GTFS_CACHE_FILE.stat().st_mtime)
            if file_age < timedelta(hours=GTFS_CACHE_VALIDITY_HOURS):
                print(f"Używam cache (wiek: {file_age.seconds // 3600}h)")
                return GTFS_CACHE_FILE
        
        try:
            response = requests.get(GTFS_STATIC_URL, timeout=30)
            response.raise_for_status()
            
            with open(GTFS_CACHE_FILE, 'wb') as f:
                f.write(response.content)
            
            print(f"Pobrano GTFS ({len(response.content) // 1024} KB)")
            return GTFS_CACHE_FILE
            
        except Exception as e:
            print(f"[BŁĄD] Nie można pobrać GTFS: {e}")
            if GTFS_CACHE_FILE.exists():
                print("Używam starego cache")
                return GTFS_CACHE_FILE
            return None
    
    def zaladuj_dane(self):
        """Ładuje wszystkie wymagane pliki GTFS do pamięci"""
        gtfs_file = self.pobierz_i_zapisz_gtfs()
        if not gtfs_file:
            return False
        
        print("Ładowanie danych GTFS...")
        
        try:
            with zipfile.ZipFile(gtfs_file, 'r') as zip_ref:
                GTFS_EXTRACTED_DIR.mkdir(exist_ok=True, parents=True)
                zip_ref.extractall(GTFS_EXTRACTED_DIR)

                self.trips = pd.read_csv(GTFS_EXTRACTED_DIR / "trips.txt")
                self.stop_times = pd.read_csv(GTFS_EXTRACTED_DIR / "stop_times.txt")
                self.stops = pd.read_csv(GTFS_EXTRACTED_DIR / "stops.txt")
                self.routes = pd.read_csv(GTFS_EXTRACTED_DIR / "routes.txt")

                if (GTFS_EXTRACTED_DIR / "calendar.txt").exists():
                    self.calendar = pd.read_csv(GTFS_EXTRACTED_DIR / "calendar.txt")
                if (GTFS_EXTRACTED_DIR / "calendar_dates.txt").exists():
                    self.calendar_dates = pd.read_csv(GTFS_EXTRACTED_DIR / "calendar_dates.txt")
                
                print(f"✓ Załadowano:")
                print(f"  - {len(self.trips)} kursów")
                print(f"  - {len(self.stop_times)} przystanków na kursach")
                print(f"  - {len(self.stops)} przystanków")
                print(f"  - {len(self.routes)} linii")
                
                return True
                
        except Exception as e:
            print(f"[BŁĄD] Nie można załadować GTFS: {e}")
            return False
    
    def pobierz_zaplanowany_czas_przyjazdu(self, trip_id, stop_sequence):
        """
        Zwraca zaplanowany czas przyjazdu dla danego kursu i przystanku
        
        Args:
            trip_id: ID kursu z GTFS-RT
            stop_sequence: Numer kolejności przystanku
            
        Returns:
            str: Czas w formacie HH:MM:SS lub None
        """
        if self.stop_times is None:
            return None
        
        mask = (self.stop_times['trip_id'] == trip_id) & \
               (self.stop_times['stop_sequence'] == stop_sequence)
        
        result = self.stop_times[mask]
        
        if len(result) > 0:
            return result.iloc[0]['arrival_time']
        return None
    
    def pobierz_info_o_kursie(self, trip_id):
        """Zwraca informacje o kursie (linia, kierunek, etc.)"""
        if self.trips is None:
            return None
        
        trip = self.trips[self.trips['trip_id'] == trip_id]
        
        if len(trip) == 0:
            return None
        
        trip_data = trip.iloc[0].to_dict()
        
        if self.routes is not None:
            route = self.routes[self.routes['route_id'] == trip_data['route_id']]
            if len(route) > 0:
                trip_data['route_short_name'] = route.iloc[0]['route_short_name']
                trip_data['route_long_name'] = route.iloc[0].get('route_long_name', '')
        
        return trip_data
    
    def pobierz_info_o_przystanku(self, stop_id):
        """Zwraca informacje o przystanku"""
        if self.stops is None:
            return None
        
        stop = self.stops[self.stops['stop_id'] == stop_id]
        
        if len(stop) == 0:
            return None
        
        return stop.iloc[0].to_dict()
    
    def pobierz_wszystkie_przystanki_kursu(self, trip_id):
        """Zwraca wszystkie przystanki dla danego kursu w kolejności"""
        if self.stop_times is None:
            return []
        
        stops = self.stop_times[self.stop_times['trip_id'] == trip_id].sort_values('stop_sequence')
        return stops.to_dict('records')
    
    def konwertuj_czas_na_sekundy(self, time_str):
        """
        Konwertuje czas GTFS (HH:MM:SS) na sekundy od północy
        Uwaga: GTFS może mieć godziny >24 dla kursów po północy
        """
        if pd.isna(time_str) or time_str is None:
            return None
        
        parts = time_str.split(':')
        if len(parts) != 3:
            return None
        
        try:
            hours = int(parts[0])
            minutes = int(parts[1])
            seconds = int(parts[2])
            return hours * 3600 + minutes * 60 + seconds
        except ValueError:
            return None


if __name__ == "__main__":
    loader = GTFSStaticLoader()
    
    if loader.zaladuj_dane():
        print("\n=== TEST FUNKCJI ===")
        
        if len(loader.trips) > 0:
            przykladowy_trip_id = loader.trips.iloc[0]['trip_id']
            print(f"\nPrzykładowy trip_id: {przykladowy_trip_id}")
            
            info = loader.pobierz_info_o_kursie(przykladowy_trip_id)
            if info:
                print(f"  Linia: {info.get('route_short_name', 'N/A')}")
                print(f"  Kierunek: {info.get('trip_headsign', 'N/A')}")
            
            przystanki = loader.pobierz_wszystkie_przystanki_kursu(przykladowy_trip_id)
            print(f"  Liczba przystanków: {len(przystanki)}")
            
            if przystanki:
                pierwszy = przystanki[0]
                print(f"  Pierwszy przystanek: {pierwszy['stop_id']} o {pierwszy['arrival_time']}")