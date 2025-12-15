import pymongo
from datetime import datetime, timedelta

MONGO_CONNECTION_STRING = "mongodb://localhost:27017/"
NAZWA_BAZY = "ztm_rzeszow_data"

def check_mongodb_connection():
    """Sprawdza połączenie z MongoDB"""
    print("\n" + "="*60)
    print("1. SPRAWDZANIE POŁĄCZENIA Z MONGODB")
    print("="*60)
    
    try:
        client = pymongo.MongoClient(MONGO_CONNECTION_STRING, serverSelectionTimeoutMS=2000)
        client.admin.command('ping')
        print("✅ MongoDB działa poprawnie")
        return client
    except Exception as e:
        print(f"❌ Błąd połączenia z MongoDB: {e}")
        print("\nRozwiązanie:")
        print("  1. Upewnij się, że MongoDB jest uruchomione")
        print("  2. Windows: Sprawdź Usługi -> MongoDB Server")
        print("  3. Linux/Mac: sudo systemctl start mongodb")
        return None

def check_raw_data_collection(client):
    """Sprawdza czy są zebrane surowe dane z GTFS-RT"""
    print("\n" + "="*60)
    print("2. SPRAWDZANIE SUROWYCH DANYCH (odczyty_gtfs_rt)")
    print("="*60)
    
    db = client[NAZWA_BAZY]
    collection = db["odczyty_gtfs_rt"]
    
    count = collection.count_documents({})
    print(f"📊 Liczba odczytów w bazie: {count}")
    
    if count == 0:
        print("❌ BRAK DANYCH!")
        print("\nRozwiązanie:")
        print("  1. Uruchom data_collector.py w osobnym terminalu")
        print("  2. Poczekaj minimum 2-3 minuty")
        print("  3. Uruchom ponownie ten skrypt")
        return False
    
    latest = collection.find_one(sort=[('timestamp_zapisu_db', -1)])
    if latest:
        timestamp = latest.get('timestamp_zapisu_db', latest.get('timestamp_serwera_gtfs'))
        age = datetime.now() - timestamp
        
        print(f"📅 Ostatni odczyt: {timestamp}")
        print(f"⏰ Wiek: {age.seconds // 60} minut temu")
        print(f"🚌 Liczba pojazdów: {latest.get('liczba_aktywnych_pojazdow', 0)}")
        
        if age.seconds > 300:
            print("⚠️  Dane są stare (>5 min). Czy data_collector.py jest uruchomiony?")
        else:
            print("✅ Dane są świeże")
        
        if latest.get('dane_pojazdow') and len(latest['dane_pojazdow']) > 0:
            pojazd = latest['dane_pojazdow'][0]
            print(f"\n📍 Przykładowy pojazd:")
            print(f"   ID: {pojazd.get('id_pojazdu')}")
            print(f"   Trip ID: {pojazd.get('trip_id')}")
            print(f"   Route ID: {pojazd.get('route_id')}")
            print(f"   Lokalizacja: {pojazd.get('lat')}, {pojazd.get('lon')}")
            
            if not pojazd.get('trip_id'):
                print("⚠️  UWAGA: Pojazd nie ma trip_id - nie można obliczyć opóźnienia!")
    
    return True

def check_delay_data(client):
    """Sprawdza czy są obliczone opóźnienia"""
    print("\n" + "="*60)
    print("3. SPRAWDZANIE DANYCH O OPÓŹNIENIACH (opoznienia)")
    print("="*60)
    
    db = client[NAZWA_BAZY]
    collection = db["opoznienia"]
    
    count = collection.count_documents({})
    print(f"📊 Liczba obliczonych opóźnień: {count}")
    
    if count == 0:
        print("❌ BRAK DANYCH O OPÓŹNIENIACH!")
        print("\nRozwiązanie:")
        print("  1. Upewnij się, że masz surowe dane (patrz punkt 2)")
        print("  2. Uruchom: python delay_calculator.py")
        print("  3. Wybierz opcję 1 (przetwórz ostatnie 100 odczytów)")
        print("  4. Poczekaj na zakończenie")
        return False

    latest = collection.find_one(sort=[('timestamp', -1)])
    if latest:
        print(f"\n📅 Ostatnie opóźnienie:")
        print(f"   Czas: {latest.get('timestamp')}")
        print(f"   Linia: {latest.get('route_short_name')}")
        print(f"   Przystanek: {latest.get('stop_name')}")
        print(f"   Opóźnienie: {latest.get('delay_minutes')} minut")
        print("✅ Dane o opóźnieniach są dostępne")
    
    data_od = datetime.now() - timedelta(days=1)
    count_24h = collection.count_documents({'timestamp': {'$gte': data_od}})
    print(f"\n📈 Opóźnienia z ostatnich 24h: {count_24h}")
    
    return True

def check_gtfs_static():
    """Sprawdza czy GTFS Static został pobrany"""
    print("\n" + "="*60)
    print("4. SPRAWDZANIE GTFS STATIC (rozkłady)")
    print("="*60)
    
    from pathlib import Path
    
    cache_dir = Path("gtfs_cache")
    cache_file = cache_dir / "gtfs_static.zip"
    
    if not cache_file.exists():
        print("❌ GTFS Static nie został pobrany")
        print("\nRozwiązanie:")
        print("  1. Uruchom: python gtfs_static_loader.py")
        print("  2. Lub uruchom: python delay_calculator.py (pobierze automatycznie)")
        return False
    
    age = datetime.now() - datetime.fromtimestamp(cache_file.stat().st_mtime)
    print(f"✅ GTFS Static pobrany")
    print(f"📅 Wiek: {age.days} dni")
    
    if age.days > 7:
        print("⚠️  Rozkład jest stary (>7 dni). Rozważ pobranie nowego.")
    
    return True

def diagnose_trip_id_issue(client):
    """Diagnozuje problemy z trip_id"""
    print("\n" + "="*60)
    print("5. DIAGNOZA TRIP_ID")
    print("="*60)
    
    db = client[NAZWA_BAZY]
    collection = db["odczyty_gtfs_rt"]
    
    latest = collection.find_one(sort=[('timestamp_zapisu_db', -1)])
    
    if not latest:
        print("❌ Brak danych do analizy")
        return
    
    pojazdy = latest.get('dane_pojazdow', [])
    total = len(pojazdy)
    with_trip_id = sum(1 for p in pojazdy if p.get('trip_id'))
    
    print(f"📊 Pojazdy z trip_id: {with_trip_id}/{total} ({with_trip_id/total*100:.1f}%)")
    
    if with_trip_id < total * 0.5:
        print("⚠️  PROBLEM: Więcej niż 50% pojazdów nie ma trip_id!")
        print("   To może oznaczać:")
        print("   - Pojazdy są w zajezdni (nie wykonują kursów)")
        print("   - Problemy z API MPK Rzeszów")
        print("   - Pora dnia z małą ilością kursów")
    else:
        print("✅ Większość pojazdów ma trip_id")
    
    bez_trip = [p for p in pojazdy if not p.get('trip_id')]
    if bez_trip and len(bez_trip) <= 5:
        print(f"\n🚌 Pojazdy bez trip_id:")
        for p in bez_trip[:5]:
            print(f"   ID: {p.get('id_pojazdu')}, Route: {p.get('route_id')}")

def show_summary_and_next_steps(has_raw, has_delays):
    """Podsumowanie i następne kroki"""
    print("\n" + "="*60)
    print("📋 PODSUMOWANIE I NASTĘPNE KROKI")
    print("="*60)
    
    if not has_raw:
        print("\n❌ PROBLEM: Brak surowych danych")
        print("\n🔧 CO ZROBIĆ:")
        print("   1. Uruchom w OSOBNYM TERMINALU:")
        print("      python data_collector.py")
        print("   2. Poczekaj 5-10 minut")
        print("   3. Uruchom ponownie: python debug_checker.py")
        
    elif not has_delays:
        print("\n⚠️  PROBLEM: Masz surowe dane, ale brak opóźnień")
        print("\n🔧 CO ZROBIĆ:")
        print("   1. Uruchom:")
        print("      python delay_calculator.py")
        print("   2. Wybierz opcję: 1")
        print("   3. Poczekaj na zakończenie (może potrwać 1-2 minuty)")
        print("   4. Uruchom dashboard:")
        print("      streamlit run dashboard_delays.py")
        
    else:
        print("\n✅ WSZYSTKO DZIAŁA!")
        print("\n🎉 Możesz teraz:")
        print("   1. Uruchomić dashboard:")
        print("      streamlit run dashboard_delays.py")
        print("   2. Lub uruchomić ciągłą analizę:")
        print("      python delay_calculator.py → opcja 3")
        print("   3. Lub wygenerować raport:")
        print("      python delay_calculator.py → opcja 2")

def main():
    """Główna funkcja diagnostyczna"""
    print("\n" + "🔍 DIAGNOSTYKA SYSTEMU ANALIZY OPÓŹNIEŃ 🔍")

    client = check_mongodb_connection()
    if not client:
        return
    
    has_raw = check_raw_data_collection(client)
    
    has_delays = check_delay_data(client)
    
    check_gtfs_static()
    
    if has_raw:
        diagnose_trip_id_issue(client)
    
    show_summary_and_next_steps(has_raw, has_delays)
    
    print("\n" + "="*60)
    print("Diagnostyka zakończona!")
    print("="*60 + "\n")

if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print("\n\nDiagnostyka przerwana")
    except Exception as e:
        print(f"\n❌ Nieoczekiwany błąd: {e}")
        import traceback
        traceback.print_exc()