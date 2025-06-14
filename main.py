# scoreboard_monitor/main.py

import time
from datetime import datetime
import signal  # <-- Importato
import os      # <-- Importato

import api_client
import data_processor
import terminal_ui
from config import TARGET_TEAM_SHORTNAME, DEFAULT_TICK_DURATION_SECONDS, COLOR_YELLOW, COLOR_RESET, COLOR_RED

# --- Gestione del ridimensionamento del terminale ---

# Variabile globale per segnalare la necessità di un ridisegno
NEEDS_REDRAW = False

def handle_resize(signum, frame):
    """
    Questa funzione viene chiamata quando il terminale viene ridimensionato.
    Imposta semplicemente un flag.
    """
    global NEEDS_REDRAW
    NEEDS_REDRAW = True

# --- Fine gestione resize ---


def main_loop():
    """
    Loop principale che orchestra il fetching, la processazione e la visualizzazione dei dati,
    gestendo anche il ridimensionamento della finestra.
    """
    # Registra la funzione handle_resize per il segnale SIGWINCH, se disponibile
    if hasattr(signal, 'SIGWINCH'):
        signal.signal(signal.SIGWINCH, handle_resize)

    previous_scoreboard_data = None
    last_processed_round = -1
    
    # Variabili per conservare gli ultimi dati validi per il ridisegno
    last_processed_data = None
    last_status_data = None

    print("Avvio del monitor... Recupero lo stato iniziale della partita.")
    
    while True:
        try:
            # La logica di fetch rimane la stessa
            status_data = api_client.fetch_game_status()
            
            if not status_data:
                print(f"{COLOR_YELLOW}Impossibile recuperare lo stato della partita. Riprovo tra 30 secondi...{COLOR_RESET}")
                time.sleep(30)
                continue

            scoreboard_round = status_data.get('scoreboardRound')

            if scoreboard_round is not None and scoreboard_round != last_processed_round:
                # Se è il primo ciclo, tenta di recuperare il round precedente
                if last_processed_round == -1 and scoreboard_round > 0:
                    print(f"Avvio a metà partita. Tento di recuperare il round {scoreboard_round - 1} per i calcoli delta...")
                    previous_scoreboard_data = api_client.fetch_scoreboard_data(scoreboard_round - 1)
                
                # Fetch e processamento dei dati correnti
                current_scoreboard_data = api_client.fetch_scoreboard_data(scoreboard_round)
                if current_scoreboard_data:
                    processed_data = data_processor.process_data_for_display(
                        current_scoreboard_data, previous_scoreboard_data, TARGET_TEAM_SHORTNAME
                    )
                    if processed_data:
                        last_processed_data = processed_data
                        last_status_data = status_data
                        terminal_ui.display_scoreboard(processed_data, status_data)
                        
                        if processed_data.get('failing_services'):
                            terminal_ui.play_alert_sound()

                        previous_scoreboard_data = current_scoreboard_data
                        last_processed_round = scoreboard_round

            # --- NUOVO CICLO DI ATTESA INTELLIGENTE ---
            # Sostituisce il singolo time.sleep() per essere reattivo
            global NEEDS_REDRAW
            round_duration = status_data.get('roundTime', DEFAULT_TICK_DURATION_SECONDS)
            sleep_start_time = time.time()
            
            while time.time() - sleep_start_time < round_duration:
                if NEEDS_REDRAW:
                    NEEDS_REDRAW = False  # Resetta il flag
                    # Ridisegna l'interfaccia con gli ultimi dati validi
                    if last_processed_data and last_status_data:
                        terminal_ui.display_scoreboard(last_processed_data, last_status_data)
                
                # Dormi per un breve intervallo per non consumare troppa CPU
                time.sleep(0.2)

        except KeyboardInterrupt:
            print("\nMonitoraggio interrotto dall'utente. Arrivederci!")
            break
        except Exception as e:
            print(f"{COLOR_RED}Errore inaspettato nel loop principale: {e}{COLOR_RESET}")
            time.sleep(30)

if __name__ == "__main__":
    main_loop()