import requests
import pandas as pd
from google.transit import gtfs_realtime_pb2
from datetime import datetime

GTFS_RT_URL = "https://www.mpkrzeszow.pl/gtfs/rt/gtfsrt.pb" 

def pobierz_dane_gtfs_rt():
    
    dane_pojazdow = []

    try:
        response = requests.get(GTFS_RT_URL)
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
                    'predkosc_kmh': round(position.speed * 3.6, 2),
                    'timestamp_danych': timestamp_vehicle,
                })
        
        return dane_pojazdow, timestamp_feed

    except requests.exceptions.RequestException as e:
        print(f"[BŁĄD KLIENTA] Błąd pobierania danych: {e}")
        return None, None
    except Exception as e:
        print(f"[BŁĄD KLIENTA] Błąd parsowania danych: {e}")
        return None, None