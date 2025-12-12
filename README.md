# 🚌 System Analizy Opóźnień Komunikacji Miejskiej w Rzeszowie

Projekt do zbierania, analizy i predykcji opóźnień autobusów miejskich MPK Rzeszów z wykorzystaniem danych GTFS-RT (real-time) i GTFS Static (rozkłady jazdy).

## 📋 Spis treści

- [Funkcjonalności](#funkcjonalności)
- [Architektura systemu](#architektura-systemu)
- [Instalacja](#instalacja)
- [Użycie](#użycie)
- [Struktura danych](#struktura-danych)
- [Dalszy rozwój](#dalszy-rozwój)

## ✨ Funkcjonalności

### ✅ Zaimplementowane

- **Zbieranie danych w czasie rzeczywistym** - automatyczne pobieranie pozycji autobusów co 60 sekund
- **Kalkulacja opóźnień** - porównywanie rzeczywistych przyjazdów z rozkładem jazdy
- **Baza danych MongoDB** - przechowywanie historycznych danych i opóźnień
- **Dashboard interaktywny** - wizualizacja opóźnień, map, wykresów i statystyk
- **Analiza temporalna** - trendy według godzin, dni tygodnia, dat

### 🔄 W planach

- Predykcja opóźnień za pomocą ML (Random Forest, XGBoost)
- Analiza przyczyn opóźnień (pogoda, ruch, godziny szczytu)
- API REST dla dostępu do danych
- Alerty i powiadomienia o opóźnieniach

## 🏗️ Architektura systemu

```
┌─────────────────┐
│  GTFS-RT API    │  ← Dane w czasie rzeczywistym (co minutę)
│  mpkrzeszow.pl  │
└────────┬────────┘
         │
         ↓
┌─────────────────┐
│ data_collector  │  ← Zbiera dane co 60 sekund
│     .py         │
└────────┬────────┘
         │
         ↓
┌─────────────────┐
│    MongoDB      │  ← Baza danych (odczyty + opóźnienia)
│  ztm_rzeszow    │
└────────┬────────┘
         │
         ↓
┌─────────────────┐      ┌─────────────────┐
│ delay_calculator│  ←→  │ GTFS Static     │
│     .py         │      │ (rozkłady)      │
└────────┬────────┘      └─────────────────┘
         │
         ↓
┌─────────────────┐
│   Dashboard     │  ← Streamlit (wizualizacje)
│ dashboard_delays│
└─────────────────┘
```

## 🔧 Instalacja

### Wymagania

- Python 3.10+
- MongoDB 5.0+
- Git

### Krok 1: Klonowanie repozytorium

```bash
git clone https://github.com/twoj-username/transit-delay-analysis.git
cd transit-delay-analysis
```

### Krok 2: Utworzenie środowiska wirtualnego

```bash
python -m venv venv

# Windows
venv\Scripts\activate

# Linux/Mac
source venv/bin/activate
```

### Krok 3: Instalacja zależności

```bash
pip install -r requirements.txt
```

### Krok 4: Instalacja i uruchomienie MongoDB

**Windows:**

```bash
# Pobierz MongoDB Community Server z mongodb.com
# Zainstaluj i uruchom jako usługę
```

**Linux (Ubuntu/Debian):**

```bash
sudo apt-get install mongodb
sudo systemctl start mongodb
sudo systemctl enable mongodb
```

**Mac:**

```bash
brew tap mongodb/brew
brew install mongodb-community
brew services start mongodb-community
```

Sprawdź połączenie:

```bash
mongosh  # powinno się połączyć z localhost:27017
```

## 🚀 Użycie

### 1. Zbieranie danych (uruchom w osobnym terminalu)

```bash
python data_collector.py
```

To uruchomi ciągły proces zbierający dane co 60 sekund. **Pozostaw włączony!**

Oczekiwany output:

```
Uruchamianie kolektora danych...
Połączono z MongoDB. Baza: ztm_rzeszow_data
Rozpoczynam zbieranie danych co 60 sekund...
[2025-12-12 10:30:15] Zapisano odczyt. ID: 675a... Pojazdów: 42
```

### 2. Pobranie rozkładów jazdy i obliczenie opóźnień

**Poczekaj minimum 5-10 minut** po uruchomieniu kolektora, aby zebrać dane.

```bash
python delay_calculator.py
```

Wybierz opcję:

- **1** - Przetwórz ostatnie 100 odczytów (pierwsza analiza)
- **2** - Generuj raport z ostatnich 7 dni
- **3** - Uruchom ciągłą analizę (analizuje nowe dane automatycznie)

Oczekiwany output:

```
✓ Połączono z MongoDB
Pobieranie statycznego GTFS...
✓ Załadowano:
  - 15234 kursów
  - 142567 przystanków na kursach
  - 458 przystanków
  - 48 linii
✓ Przygotowano indeks przystanków

Przetwarzam 100 odczytów...
✓ Znaleziono 1247 nowych opóźnień
```

### 3. Uruchomienie dashboardu

```bash
streamlit run dashboard_delays.py
```

Dashboard otworzy się w przeglądarce (domyślnie http://localhost:8501)

### Testowanie systemu (dla pierwszego uruchomienia)

```bash
# Terminal 1: Zbieranie danych
python data_collector.py

# Poczekaj 5-10 minut...

# Terminal 2: Oblicz opóźnienia
python delay_calculator.py
# Wybierz opcję: 1

# Terminal 3: Dashboard
streamlit run dashboard_delays.py
```

## 📊 Struktura danych

### Kolekcja MongoDB: `odczyty_gtfs_rt`

```json
{
  "_id": ObjectId("..."),
  "timestamp_serwera_gtfs": ISODate("2025-12-12T10:30:00Z"),
  "timestamp_zapisu_db": ISODate("2025-12-12T10:30:15Z"),
  "liczba_aktywnych_pojazdow": 42,
  "dane_pojazdow": [
    {
      "id_pojazdu": "1234",
      "trip_id": "t_123_456",
      "route_id": "12",
      "lat": 50.0412,
      "lon": 21.9991,
      "predkosc_kmh": 28.5,
      "timestamp_danych": ISODate("2025-12-12T10:29:55Z")
    }
  ]
}
```

### Kolekcja MongoDB: `opoznienia`

```json
{
  "_id": ObjectId("..."),
  "timestamp": ISODate("2025-12-12T10:30:00Z"),
  "trip_id": "t_123_456",
  "route_id": "12",
  "route_short_name": "12",
  "vehicle_id": "1234",
  "stop_id": "s_1001",
  "stop_name": "Rynek",
  "stop_sequence": 5,
  "scheduled_arrival": "10:28:00",
  "actual_arrival_seconds": 36600,
  "delay_seconds": 120,
  "delay_minutes": 2.0,
  "distance_to_stop_meters": 25.3,
  "trip_headsign": "Os. Baranówka",
  "lat": 50.0412,
  "lon": 21.9991
}
```

## 📈 Dalszy rozwój

### Faza 1: Wzbogacenie danych (1-2 tygodnie)

- [ ] Zbieranie danych pogodowych (OpenWeatherMap API)
- [ ] Analiza ruchu drogowego (Google Traffic API)
- [ ] Identyfikacja dni świątecznych i wydarzeń

### Faza 2: Feature Engineering (2-3 tygodnie)

- [ ] Agregacja historycznych opóźnień (średnia/mediana na trasie)
- [ ] Propagacja opóźnień między przystankami
- [ ] Ekstrakcja cech czasowych (godziny szczytu, weekend, etc.)
- [ ] Segmentacja tras (śródmieście vs peryferie)

### Faza 3: Modelowanie (3-4 tygodnie)

- [ ] Baseline model (średnia historyczna)
- [ ] Linear Regression
- [ ] Random Forest / XGBoost
- [ ] Time Series (ARIMA / Prophet) dla tras
- [ ] LSTM dla sekwencji opóźnień
- [ ] Ewaluacja modeli (MAE, RMSE, R²)

### Faza 4: Deployment

- [ ] REST API (FastAPI)
- [ ] Predykcje w czasie rzeczywistym
- [ ] Integracja z dashboardem
- [ ] Monitoring i alerty

## 🎯 Metryki sukcesu projektu

| Metryka                    | Cel         | Status                       |
| -------------------------- | ----------- | ---------------------------- |
| Dokładność predykcji (MAE) | <3 minuty   | 🔄 W trakcie                 |
| Pokrycie danych            | >80% kursów | ✅ Zależne od API            |
| Latencja predykcji         | <1 sekunda  | 🔄 W planach                 |
| Dostępność systemu         | >95%        | ✅ Zależne od infrastruktury |

## 📝 Uwagi techniczne

### Limitacje GTFS-RT API

- API MPK Rzeszów aktualizuje dane co ~1 minutę
- Nie wszystkie pojazdy mają aktywny GPS
- `trip_id` może być brakujący dla niektórych pojazdów

### Kalkulacja opóźnień

- Pojazd jest "na przystanku" gdy znajduje się w promieniu 50m
- Opóźnienia >30 minut są ignorowane (prawdopodobnie błąd)
- Używamy KD-tree do szybkiego wyszukiwania najbliższych przystanków

### Wydajność

- MongoDB indeksy: `trip_id`, `timestamp`, `stop_id`
- Cache GTFS static (24h)
- Przetwarzanie batch (100 odczytów na raz)

## 🤝 Wkład w projekt

Jeśli chcesz pomóc:

1. Fork repozytorium
2. Stwórz branch (`git checkout -b feature/nowa-funkcja`)
3. Commit zmian (`git commit -m 'Dodano nową funkcję'`)
4. Push do brancha (`git push origin feature/nowa-funkcja`)
5. Otwórz Pull Request

## 📄 Licencja

MIT License - używaj jak chcesz!

## 🙏 Podziękowania

- **MPK Rzeszów** za udostępnienie danych GTFS/GTFS-RT
- **Miasto Rzeszów** za portal Otwarte Dane
- **MKuranowski** za poprawki i wzbogacenie plików GTFS

## 📧 Kontakt

Masz pytania? Otwórz Issue na GitHubie!

---

**Projekt rozwijany w ramach kursu "Analiza danych w R i Python"**
