# scoreboard_monitor/api_client.py

import requests
import json
from config import BASE_URL, SCOREBOARD_ENDPOINT, STATUS_ENDPOINT, COLOR_RED, COLOR_RESET

def _fetch_json(endpoint: str) -> dict | None:
    """Funzione helper per effettuare richieste GET e gestire errori comuni."""
    url = f"{BASE_URL}{endpoint}"
    try:
        response = requests.get(url, timeout=10)
        response.raise_for_status()
        return response.json()
    except requests.exceptions.RequestException as e:
        print(f"{COLOR_RED}Errore di connessione all'API ({url}): {e}{COLOR_RESET}")
    except json.JSONDecodeError:
        print(f"{COLOR_RED}Errore nel decodificare la risposta JSON da {url}{COLOR_RESET}")
    return None

def fetch_scoreboard_data(tick_number: int) -> dict | None:
    """
    Effettua una richiesta GET all'API del tabellone per un dato tick.
    """
    return _fetch_json(f"{SCOREBOARD_ENDPOINT}{tick_number}")

def fetch_game_status() -> dict | None:
    """
    Effettua una richiesta GET all'API di stato del gioco.
    """
    return _fetch_json(STATUS_ENDPOINT)