import sys
import subprocess
from pathlib import Path

def sprawdz_kolor(text, color='green'):
    """Kolorowy output"""
    colors = {
        'green': '\033[92m',
        'red': '\033[91m',
        'yellow': '\033[93m',
        'blue': '\033[94m',
        'end': '\033[0m'
    }
    return f"{colors.get(color, '')}{text}{colors['end']}"

def sprawdz_python():
    """Sprawdza wersję Pythona"""
    print("\n🐍 Sprawdzanie wersji Pythona...")
    version = sys.version_info
    
    if version.major >= 3 and version.minor >= 10:
        print(sprawdz_kolor(f"   ✓ Python {version.major}.{version.minor}.{version.micro}", 'green'))
        return True
    else:
        print(sprawdz_kolor(f"   ✗ Python {version.major}.{version.minor} - wymagane 3.10+", 'red'))
        return False

def sprawdz_mongodb():
    """Sprawdza czy MongoDB jest uruchomione"""
    print("\n🍃 Sprawdzanie MongoDB...")
    try:
        import pymongo
        client = pymongo.MongoClient("mongodb://localhost:27017/", serverSelectionTimeoutMS=2000)
        client.admin.command('ping')
        print(sprawdz_kolor("   ✓ MongoDB działa", 'green'))
        return True
    except Exception as e:
        print(sprawdz_kolor(f"   ✗ MongoDB nie działa: {e}", 'red'))
        print(sprawdz_kolor("   Uruchom MongoDB przed kontynuacją!", 'yellow'))
        return False

def sprawdz_pakiety():
    """Sprawdza czy wszystkie pakiety są zainstalowane"""
    print("\n📦 Sprawdzanie zainstalowanych pakietów...")
    
    required = [
        'pymongo', 'pandas', 'requests', 'streamlit', 
        'scipy', 'plotly', 'google.transit'
    ]
    
    missing = []
    for package in required:
        try:
            if package == 'google.transit':
                __import__('google.transit.gtfs_realtime_pb2')
            else:
                __import__(package)
            print(sprawdz_kolor(f"   ✓ {package}", 'green'))
        except ImportError:
            print(sprawdz_kolor(f"   ✗ {package}", 'red'))
            missing.append(package)
    
    if missing:
        print(sprawdz_kolor(f"\n   Brakujące pakiety: {', '.join(missing)}", 'red'))
        print(sprawdz_kolor("   Uruchom: pip install -r requirements.txt", 'yellow'))
        return False
    
    return True

def sprawdz_pliki():
    """Sprawdza czy wszystkie wymagane pliki istnieją"""
    print("\n📁 Sprawdzanie plików projektu...")
    
    required_files = [
        'gtfs_client.py',
        'data_collector.py',
        'gtfs_static_loader.py',
        'delay_calculator.py',
        'dashboard_delays.py',
        'requirements.txt'
    ]
    
    missing = []
    for file in required_files:
        if Path(file).exists():
            print(sprawdz_kolor(f"   ✓ {file}", 'green'))
        else:
            print(sprawdz_kolor(f"   ✗ {file}", 'red'))
            missing.append(file)
    
    if missing:
        print(sprawdz_kolor(f"\n   Brakujące pliki: {', '.join(missing)}", 'red'))
        return False
    
    return True

def test_api():
    """Testuje API GTFS-RT"""
    print("\n🌐 Testowanie API GTFS-RT...")
    try:
        from gtfs_client import pobierz_dane_gtfs_rt
        dane, timestamp = pobierz_dane_gtfs_rt()
        
        if dane and len(dane) > 0:
            print(sprawdz_kolor(f"   ✓ API działa - znaleziono {len(dane)} pojazdów", 'green'))
            print(f"   Timestamp serwera: {timestamp}")
            return True
        else:
            print(sprawdz_kolor("   ✗ API zwróciło puste dane", 'red'))
            return False
            
    except Exception as e:
        print(sprawdz_kolor(f"   ✗ Błąd połączenia: {e}", 'red'))
        return False

def test_gtfs_static():
    """Testuje pobieranie GTFS Static"""
    print("\n📋 Testowanie GTFS Static...")
    try:
        from gtfs_static_loader import GTFSStaticLoader
        loader = GTFSStaticLoader()
        
        if loader.zaladuj_dane():
            print(sprawdz_kolor(f"   ✓ GTFS Static załadowane", 'green'))
            print(f"   Liczba kursów: {len(loader.trips)}")
            print(f"   Liczba przystanków: {len(loader.stops)}")
            return True
        else:
            print(sprawdz_kolor("   ✗ Nie udało się załadować GTFS Static", 'red'))
            return False
            
    except Exception as e:
        print(sprawdz_kolor(f"   ✗ Błąd: {e}", 'red'))
        return False

def menu_glowne():
    """Menu główne quick start"""
    print("\n" + "="*60)
    print(sprawdz_kolor("🚀 QUICK START - System Analizy Opóźnień", 'blue'))
    print("="*60)
    
    print("\n1. 🔍 Sprawdź konfigurację systemu")
    print("2. 📊 Uruchom kolektor danych (terminal 1)")
    print("3. 🧮 Uruchom kalkulator opóźnień (terminal 2)")
    print("4. 📈 Uruchom dashboard (terminal 3)")
    print("5. 🧪 Uruchom wszystkie testy")
    print("6. 📖 Pokaż instrukcje")
    print("0. ❌ Wyjście")
    
    return input("\nWybierz opcję: ")

def uruchom_kolektor():
    """Uruchamia data_collector.py"""
    print("\n" + sprawdz_kolor("Uruchamiam kolektor danych...", 'blue'))
    print(sprawdz_kolor("UWAGA: To będzie działać w nieskończoność. Użyj Ctrl+C aby zatrzymać.", 'yellow'))
    input("Naciśnij Enter aby kontynuować...")
    
    try:
        subprocess.run([sys.executable, 'data_collector.py'])
    except KeyboardInterrupt:
        print(sprawdz_kolor("\n\nKolektor zatrzymany", 'yellow'))

def uruchom_kalkulator():
    """Uruchamia delay_calculator.py"""
    print("\n" + sprawdz_kolor("Uruchamiam kalkulator opóźnień...", 'blue'))
    
    try:
        subprocess.run([sys.executable, 'delay_calculator.py'])
    except KeyboardInterrupt:
        print(sprawdz_kolor("\n\nKalkulator zatrzymany", 'yellow'))

def uruchom_dashboard():
    """Uruchamia dashboard Streamlit"""
    print("\n" + sprawdz_kolor("Uruchamiam dashboard...", 'blue'))
    print("Dashboard otworzy się w przeglądarce na http://localhost:8501")
    
    try:
        subprocess.run(['streamlit', 'run', 'dashboard_delays.py'])
    except KeyboardInterrupt:
        print(sprawdz_kolor("\n\nDashboard zatrzymany", 'yellow'))
    except FileNotFoundError:
        print(sprawdz_kolor("Streamlit nie znaleziony. Zainstaluj: pip install streamlit", 'red'))

def pokaz_instrukcje():
    """Wyświetla szczegółowe instrukcje"""
    print("\n" + "="*60)
    print(sprawdz_kolor("📖 INSTRUKCJE URUCHOMIENIA", 'blue'))
    print("="*60)
    
    print("""
    KROK 1: Sprawdź konfigurację
    ├─ Wybierz opcję 1 w menu
    └─ Upewnij się, że wszystkie testy przechodzą ✓
    
    KROK 2: Uruchom komponenty w 3 terminalach
    
    TERMINAL 1 - Kolektor danych:
    ├─ python data_collector.py
    ├─ Zbiera dane z API co 60 sekund
    └─ ZOSTAW WŁĄCZONY przez minimum 10 minut
    
    TERMINAL 2 - Kalkulator opóźnień:
    ├─ Poczekaj 10 minut po uruchomieniu kolektora
    ├─ python delay_calculator.py
    ├─ Wybierz opcję 1 (przetwórz ostatnie 100 odczytów)
    └─ Możesz uruchomić opcję 3 (ciągła analiza)
    
    TERMINAL 3 - Dashboard:
    ├─ streamlit run dashboard_delays.py
    └─ Otwiera się w przeglądarce (localhost:8501)
    
    KROK 3: Monitoruj dane
    ├─ Sprawdź dashboard - powinieneś zobaczyć wykresy
    ├─ Jeśli "Brak danych", wróć do TERMINAL 2
    └─ Daj systemowi zbierać dane przez kilka godzin/dni
    
    KROK 4: Analiza i predykcja
    ├─ Po zebraniu danych przez 1-2 tygodnie
    ├─ Możesz zacząć budować modele ML
    └─ Zobacz README.md sekcja "Dalszy rozwój"
    """)
    
    input("\nNaciśnij Enter aby wrócić do menu...")

def main():
    """Główna funkcja"""
    while True:
        wybor = menu_glowne()
        
        if wybor == "1":
            wyniki = []
            wyniki.append(sprawdz_python())
            wyniki.append(sprawdz_mongodb())
            wyniki.append(sprawdz_pakiety())
            wyniki.append(sprawdz_pliki())
            
            if all(wyniki):
                print("\n" + sprawdz_kolor("="*60, 'green'))
                print(sprawdz_kolor("✓ Wszystkie testy podstawowe przeszły!", 'green'))
                print(sprawdz_kolor("="*60, 'green'))
                
                if input("\nChcesz uruchomić testy API? (t/n): ").lower() == 't':
                    test_api()
                    test_gtfs_static()
            else:
                print("\n" + sprawdz_kolor("="*60, 'red'))
                print(sprawdz_kolor("✗ Niektóre testy nie przeszły. Napraw błędy przed kontynuacją.", 'red'))
                print(sprawdz_kolor("="*60, 'red'))
            
            input("\nNaciśnij Enter aby wrócić do menu...")
            
        elif wybor == "2":
            uruchom_kolektor()
            
        elif wybor == "3":
            uruchom_kalkulator()
            
        elif wybor == "4":
            uruchom_dashboard()
            
        elif wybor == "5":
            sprawdz_python()
            sprawdz_mongodb()
            sprawdz_pakiety()
            sprawdz_pliki()
            test_api()
            test_gtfs_static()
            input("\nNaciśnij Enter aby wrócić do menu...")
            
        elif wybor == "6":
            pokaz_instrukcje()
            
        elif wybor == "0":
            print(sprawdz_kolor("\nDo zobaczenia! 👋", 'blue'))
            break
            
        else:
            print(sprawdz_kolor("\nNieprawidłowa opcja!", 'red'))

if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print(sprawdz_kolor("\n\nProgram przerwany przez użytkownika", 'yellow'))