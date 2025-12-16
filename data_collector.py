import pymongo
import time
from datetime import datetime

from gtfs_client import pobierz_dane_gtfs_rt

MONGO_CONNECTION_STRING = "mongodb://localhost:27017/" 


NAZWA_BAZY = "ztm_rzeszow_data"
NAZWA_KOLEKCJI = "odczyty_gtfs_rt"
INTERWAL_SEKUNDY = 30


def uruchom_kolektor():
    print("Uruchamianie kolektora danych...")
    
    try:
        client = pymongo.MongoClient(MONGO_CONNECTION_STRING)
        db = client[NAZWA_BAZY]
        collection = db[NAZWA_KOLEKCJI]

        client.admin.command('ping')
        print(f"Połączono z MongoDB. Baza: {NAZWA_BAZY}, Kolekcja: {NAZWA_KOLEKCJI}")
        
    except Exception as e:
        print(f"[BŁĄD KRYTYCZNY] Nie można połączyć z MongoDB: {e}")
        print("Upewnij się, że serwer MongoDB jest uruchomiony, a CONNECTION_STRING jest poprawny.")
        return

    print(f"Rozpoczynam zbieranie danych co {INTERWAL_SEKUNDY} sekund...")
    
    while True:
        try:
            dane_pojazdow, timestamp_serwera = pobierz_dane_gtfs_rt()
            
            if dane_pojazdow is not None:
                dokument = {
                    "timestamp_serwera_gtfs": timestamp_serwera,
                    "timestamp_zapisu_db": datetime.now(),
                    "liczba_aktywnych_pojazdow": len(dane_pojazdow),
                    "dane_pojazdow": dane_pojazdow
                }
                
                result = collection.insert_one(dokument)
                print(f"[{datetime.now()}] Zapisano odczyt. ID: {result.inserted_id}. Pojazdów: {len(dane_pojazdow)}")
                
            else:
                print(f"[{datetime.now()}] Nie udało się pobrać danych (zwrócono None).")

        except Exception as e:
            print(f"[{datetime.now()}] Wystąpił błąd w pętli głównej: {e}")

        time.sleep(INTERWAL_SEKUNDY)

if __name__ == "__main__":
    uruchom_kolektor()