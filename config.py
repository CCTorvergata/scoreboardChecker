# scoreboard_monitor/config.py

# --- Impostazioni API ---
BASE_URL = "http://10.10.0.1/api/"
STATUS_ENDPOINT = "status"
SCOREBOARD_ENDPOINT = "scoreboard/table/"
# Durata del tick di default, verrà sovrascritta da quella dell'API se disponibile
DEFAULT_TICK_DURATION_SECONDS = 120

# --- Impostazioni Team ---
# Modifica questo valore con il team che vuoi monitorare
TARGET_TEAM_SHORTNAME = "unirm2"

# --- Codici Colore per il Terminale (ANSI) ---
COLOR_GREEN = "\033[92m"
COLOR_RED = "\033[91m"
COLOR_YELLOW = "\033[93m"
COLOR_BLUE = "\033[94m"
COLOR_CYAN = "\033[96m"
COLOR_MAGENTA = "\033[95m"
COLOR_BOLD = "\033[1m"
COLOR_RESET = "\033[0m"

# --- Soglie per colorazione ---
SLA_DEGRADED_THRESHOLD = 90.0
SLA_CRITICAL_THRESHOLD = 75.0