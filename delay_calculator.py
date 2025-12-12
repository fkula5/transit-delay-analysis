import pymongo
from datetime import datetime, timedelta
import pandas as pd
import numpy as np
from scipy.spatial import cKDTree

from gtfs_static_loader import GTFSStaticLoader

MONGO_CONNECTION_STRING = "mongodb://localhost:27017/"
NAZWA_BAZY = "ztm_rzeszow_data"
NAZWA_KOLEKCJI_RT = "odczyty_gtfs_rt"
NAZWA_KOLEKCJI_OPOZNIENIA = "opoznienia"

# Parametry obliczania opóźnień
PROMIEN_PRZYSTANKU_METRY = 50  # Pojazd musi być w tym promieniu, żeby uznać że jest na przystanku
MAX_OPOZNIENIE_SEKUND = 1800   # Ignoruj opóźnienia >30 min (prawdopodobnie błąd danych)


class DelayCalculator:
    """Klasa do obliczania opóźnień na podstawie danych GTFS-RT i statycznych"""
    
    def __init__(self):
        self.gtfs_loader = GTFSStaticLoader()
        self.client = None
        self.db = None
        self.collection_rt = None
        self.collection_delays = None
        
        # Cache przystanków do szybkiego wyszukiwania
        self.stops_kdtree = None
        self.stops_coords = None
        self.stops_ids = None
        
    def polacz_z_mongodb(self):
        """Łączy się z MongoDB"""
        try:
            self.client = pymongo.MongoClient(MONGO_CONNECTION_STRING)
            self.db = self.client[NAZWA_BAZY]
            self.collection_rt = self.db[NAZWA_KOLEKCJI_RT]
            self.collection_delays = self.db[NAZWA_KOLEKCJI_OPOZNIENIA]
            
            self.client.admin.command('ping')
            print(f"✓ Połączono z MongoDB")
            return True
            
        except Exception as e:
            print(f"[BŁĄD] Nie można połączyć z MongoDB: {e}")
            return False
    
    def zaladuj_gtfs(self):
        """Ładuje dane GTFS"""
        if not self.gtfs_loader.zaladuj_dane():
            return False
        
        # Przygotuj KD-tree dla szybkiego wyszukiwania najbliższych przystanków
        stops = self.gtfs_loader.stops
        self.stops_coords = stops[['stop_lat', 'stop_lon']].values
        self.stops_ids = stops['stop_id'].values
        self.stops_kdtree = cKDTree(self.stops_coords)
        
        print(f"✓ Przygotowano indeks przystanków")
        return True
    
    def znajdz_najblizszy_przystanek(self, lat, lon, max_distance_km=0.1):
        """
        Znajduje najbliższy przystanek do podanych koordynatów
        
        Returns:
            tuple: (stop_id, distance_meters) lub (None, None)
        """
        if self.stops_kdtree is None:
            return None, None
        
        # Proste przybliżenie odległości (działa dla małych odległości)
        distance, index = self.stops_kdtree.query([lat, lon])
        
        # Konwersja różnicy stopni na metry (przybliżenie dla Polski: ~111km na stopień)
        distance_meters = distance * 111000
        
        if distance_meters < max_distance_km * 1000:
            return self.stops_ids[index], distance_meters
        
        return None, None
    
    def oblicz_opoznienie_dla_pojazdu(self, dane_pojazdu, timestamp_odczytu):
        """
        Oblicza opóźnienie dla pojedynczego pojazdu
        
        Returns:
            dict lub None: Informacje o opóźnieniu
        """
        trip_id = dane_pojazdu.get('trip_id')
        if not trip_id:
            return None
        
        # Znajdź najbliższy przystanek
        lat = dane_pojazdu.get('lat')
        lon = dane_pojazdu.get('lon')
        
        if lat is None or lon is None:
            return None
        
        stop_id, distance = self.znajdz_najblizszy_przystanek(lat, lon, max_distance_km=0.05)
        
        if stop_id is None:
            return None
        
        # Znajdź informacje o tym przystanku w rozkładzie kursu
        przystanki_kursu = self.gtfs_loader.pobierz_wszystkie_przystanki_kursu(trip_id)
        
        if not przystanki_kursu:
            return None
        
        # Znajdź który to przystanek w kolejności
        przystanek_na_kursie = None
        for p in przystanki_kursu:
            if str(p['stop_id']) == str(stop_id):
                przystanek_na_kursie = p
                break
        
        if przystanek_na_kursie is None:
            return None
        
        # Pobierz zaplanowany czas przyjazdu
        zaplanowany_czas_str = przystanek_na_kursie['arrival_time']
        zaplanowany_czas_sek = self.gtfs_loader.konwertuj_czas_na_sekundy(zaplanowany_czas_str)
        
        if zaplanowany_czas_sek is None:
            return None
        
        # Oblicz rzeczywisty czas od północy
        rzeczywisty_czas = timestamp_odczytu
        sekund_od_polnocy = (rzeczywisty_czas.hour * 3600 + 
                            rzeczywisty_czas.minute * 60 + 
                            rzeczywisty_czas.second)
        
        # Obsługa kursów po północy (GTFS może mieć godziny >24)
        if zaplanowany_czas_sek >= 86400:  # >= 24:00:00
            zaplanowany_czas_sek -= 86400
        
        # Oblicz opóźnienie
        opoznienie_sek = sekund_od_polnocy - zaplanowany_czas_sek
        
        # Ignoruj opóźnienia przekraczające maksimum (prawdopodobnie błędne dane)
        if abs(opoznienie_sek) > MAX_OPOZNIENIE_SEKUND:
            return None
        
        # Pobierz dodatkowe informacje
        info_kursu = self.gtfs_loader.pobierz_info_o_kursie(trip_id)
        info_przystanku = self.gtfs_loader.pobierz_info_o_przystanku(stop_id)
        
        return {
            'timestamp': timestamp_odczytu,
            'trip_id': trip_id,
            'route_id': dane_pojazdu.get('route_id'),
            'vehicle_id': dane_pojazdu.get('id_pojazdu'),
            'stop_id': stop_id,
            'stop_name': info_przystanku.get('stop_name') if info_przystanku else None,
            'stop_sequence': przystanek_na_kursie['stop_sequence'],
            'scheduled_arrival': zaplanowany_czas_str,
            'actual_arrival_seconds': sekund_od_polnocy,
            'delay_seconds': opoznienie_sek,
            'delay_minutes': round(opoznienie_sek / 60, 1),
            'distance_to_stop_meters': round(distance, 1),
            'route_short_name': info_kursu.get('route_short_name') if info_kursu else None,
            'trip_headsign': info_kursu.get('trip_headsign') if info_kursu else None,
            'lat': lat,
            'lon': lon,
        }
    
    def przetwórz_odczyt_historyczny(self, odczyt_id=None, limit=100):
        """
        Przetwarza historyczne odczyty i oblicza opóźnienia
        
        Args:
            odczyt_id: Konkretny ID odczytu lub None dla najnowszych
            limit: Maksymalna liczba odczytów do przetworzenia
        """
        if odczyt_id:
            odczyty = list(self.collection_rt.find({'_id': odczyt_id}))
        else:
            odczyty = list(self.collection_rt.find().sort('timestamp_zapisu_db', -1).limit(limit))
        
        print(f"\nPrzetwarzam {len(odczyty)} odczytów...")
        
        opoznienia_znalezione = 0
        
        for odczyt in odczyty:
            timestamp = odczyt.get('timestamp_serwera_gtfs') or odczyt.get('timestamp_zapisu_db')
            
            for dane_pojazdu in odczyt.get('dane_pojazdow', []):
                opoznienie = self.oblicz_opoznienie_dla_pojazdu(dane_pojazdu, timestamp)
                
                if opoznienie:
                    # Sprawdź czy już nie mamy tego opóźnienia
                    exists = self.collection_delays.find_one({
                        'trip_id': opoznienie['trip_id'],
                        'stop_id': opoznienie['stop_id'],
                        'timestamp': opoznienie['timestamp']
                    })
                    
                    if not exists:
                        self.collection_delays.insert_one(opoznienie)
                        opoznienia_znalezione += 1
        
        print(f"✓ Znaleziono {opoznienia_znalezione} nowych opóźnień")
        return opoznienia_znalezione
    
    def generuj_raport_opoznien(self, dni_wstecz=7):
        """Generuje raport opóźnień z ostatnich N dni"""
        data_od = datetime.now() - timedelta(days=dni_wstecz)
        
        opoznienia = list(self.collection_delays.find({
            'timestamp': {'$gte': data_od}
        }))
        
        if not opoznienia:
            print("Brak danych o opóźnieniach")
            return None
        
        df = pd.DataFrame(opoznienia)
        
        print(f"\n=== RAPORT OPÓŹNIEŃ ({dni_wstecz} dni) ===")
        print(f"Łączna liczba pomiarów: {len(df)}")
        print(f"\nStatystyki opóźnień (minuty):")
        print(df['delay_minutes'].describe())
        
        print(f"\n=== TOP 10 LINII Z NAJWIĘKSZYMI OPÓŹNIENIAMI ===")
        top_routes = df.groupby('route_short_name')['delay_minutes'].agg(['mean', 'count']).sort_values('mean', ascending=False).head(10)
        print(top_routes)
        
        print(f"\n=== TOP 10 PRZYSTANKÓW Z NAJWIĘKSZYMI OPÓŹNIENIAMI ===")
        top_stops = df.groupby('stop_name')['delay_minutes'].agg(['mean', 'count']).sort_values('mean', ascending=False).head(10)
        print(top_stops)
        
        return df
    
    def uruchom_ciagla_analize(self, interwal_sekund=300):
        """
        Uruchamia ciągłą analizę nowych odczytów
        
        Args:
            interwal_sekund: Jak często sprawdzać nowe dane
        """
        import time
        
        print(f"Uruchamiam ciągłą analizę (co {interwal_sekund}s)...")
        ostatni_odczyt = None
        
        while True:
            try:
                # Znajdź najnowszy odczyt
                najnowszy = self.collection_rt.find_one(sort=[('timestamp_zapisu_db', -1)])
                
                if najnowszy and (ostatni_odczyt is None or najnowszy['_id'] != ostatni_odczyt):
                    print(f"\n[{datetime.now()}] Nowy odczyt: {najnowszy['_id']}")
                    self.przetwórz_odczyt_historyczny(odczyt_id=najnowszy['_id'])
                    ostatni_odczyt = najnowszy['_id']
                
                time.sleep(interwal_sekund)
                
            except KeyboardInterrupt:
                print("\nZatrzymano analizę")
                break
            except Exception as e:
                print(f"[BŁĄD] {e}")
                time.sleep(interwal_sekund)


def main():
    """Główna funkcja - oblicza opóźnienia dla zebranych danych"""
    calculator = DelayCalculator()
    
    if not calculator.polacz_z_mongodb():
        return
    
    if not calculator.zaladuj_gtfs():
        return
    
    print("\n=== KALKULATOR OPÓŹNIEŃ ===")
    print("1. Przetwórz ostatnie 100 odczytów")
    print("2. Generuj raport z ostatnich 7 dni")
    print("3. Uruchom ciągłą analizę")
    print("4. Wyjście")
    
    wybor = input("\nWybór: ")
    
    if wybor == "1":
        calculator.przetwórz_odczyt_historyczny(limit=100)
    elif wybor == "2":
        calculator.generuj_raport_opoznien(dni_wstecz=7)
    elif wybor == "3":
        calculator.uruchom_ciagla_analize()
    

if __name__ == "__main__":
    main()