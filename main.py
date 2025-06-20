# scoreboard_monitor/main.py

import time
from datetime import datetime
import signal

import api_client
import data_processor
import terminal_ui
from config import TARGET_TEAM_SHORTNAME, DEFAULT_TICK_DURATION_SECONDS, COLOR_YELLOW, COLOR_RESET, COLOR_RED, COLOR_GREEN, COLOR_BOLD

# --- Gestione ridimensionamento e flag ---
NEEDS_REDRAW = False

def handle_resize(signum, frame):
    global NEEDS_REDRAW
    NEEDS_REDRAW = True

# --- Funzione di Sincronizzazione ---
def synchronize_and_wait_for_next_tick(initial_round: int):
    """
    Attende attivamente l'inizio del prossimo round per sincronizzare l'esecuzione.
    """
    print(f"\n{COLOR_YELLOW}Snapshot visualizzato. In attesa del round {initial_round + 1} per la sincronizzazione...{COLOR_RESET}")
    
    while True:
        time.sleep(5) # Intervallo di polling
        current_status = api_client.fetch_game_status()

        if current_status and current_status.get('scoreboardRound') is not None:
            new_round = current_status.get('scoreboardRound')
            if new_round > initial_round:
                print(f"\n{COLOR_GREEN}Sincronizzato!{COLOR_RESET} Caricamento dati per il round {COLOR_BOLD}{new_round}{COLOR_RESET}.")
                time.sleep(1)
                return current_status
    return None

# --- Loop Principale ---
def main():
    """
    Orchestra l'intero processo: snapshot iniziale, sincronizzazione e loop di monitoraggio.
    """
    if hasattr(signal, 'SIGWINCH'):
        signal.signal(signal.SIGWINCH, handle_resize)

    # --- 1. VISUALIZZAZIONE DELLO SNAPSHOT INIZIALE ---
    print(f"{COLOR_YELLOW}Recupero snapshot iniziale della scoreboard...{COLOR_RESET}")
    
    status_data = api_client.fetch_game_status()
    if not status_data or status_data.get('scoreboardRound') is None:
        print(f"{COLOR_RED}Impossibile recuperare lo stato iniziale. Uscita.{COLOR_RESET}")
        return

    current_round = status_data.get('scoreboardRound')
    
    # Se la partita non è ancora iniziata, salta lo snapshot e sincronizza direttamente
    if current_round == 0:
        print("La partita è al round 0. In attesa del primo round per iniziare...")
        status_data = synchronize_and_wait_for_next_tick(0)
        if not status_data: return
        current_round = status_data.get('scoreboardRound')

    print(f"Visualizzazione dei dati per il round attuale: {COLOR_BOLD}{current_round}{COLOR_RESET}")
    
    # Recupera i dati per lo snapshot
    snapshot_scoreboard_data = api_client.fetch_scoreboard_data(current_round)
    snapshot_previous_data = api_client.fetch_scoreboard_data(current_round - 1)

    if not snapshot_scoreboard_data:
        print(f"{COLOR_RED}Impossibile recuperare i dati della scoreboard per il round {current_round}.{COLOR_RESET}")
        # Procede comunque alla sincronizzazione
    else:
        processed_snapshot = data_processor.process_data_for_display(
            snapshot_scoreboard_data, snapshot_previous_data, TARGET_TEAM_SHORTNAME
        )
        if processed_snapshot:
            terminal_ui.display_scoreboard(processed_snapshot, status_data)
            if processed_snapshot.get('failing_services'):
                terminal_ui.play_alert_sound()
    
    # --- 2. SINCRONIZZAZIONE CON IL TICK SUCCESSIVO ---
    status_data = synchronize_and_wait_for_next_tick(current_round)
    if not status_data: return # Esce se la sincronizzazione fallisce

    # --- 3. INIZIO DEL LOOP DI MONITORAGGIO PRINCIPALE ---
    last_processed_round = current_round
    previous_scoreboard_data = snapshot_scoreboard_data
    last_processed_data = None
    last_status_data = None

    while True:
        try:
            # La prima iterazione usa i dati già ottenuti dalla sincronizzazione
            if status_data is None:
                status_data = api_client.fetch_game_status()
            
            if not status_data:
                print(f"{COLOR_YELLOW}Impossibile recuperare lo stato della partita. Riprovo...{COLOR_RESET}")
                time.sleep(30)
                continue

            scoreboard_round = status_data.get('scoreboardRound')
            
            if scoreboard_round is not None and scoreboard_round > last_processed_round:
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

            # Ciclo di attesa reattivo
            global NEEDS_REDRAW
            wait_duration = status_data.get('roundTime', DEFAULT_TICK_DURATION_SECONDS)
            sleep_start_time = time.time()
            
            while time.time() - sleep_start_time < wait_duration:
                if NEEDS_REDRAW:
                    NEEDS_REDRAW = False
                    if last_processed_data and last_status_data:
                        terminal_ui.display_scoreboard(last_processed_data, last_status_data)
                time.sleep(0.2)
            
            # Resetta per forzare il fetch alla prossima iterazione
            status_data = None

        except KeyboardInterrupt:
            print("\nMonitoraggio interrotto dall'utente. Arrivederci!")
            break
        except Exception as e:
            print(f"{COLOR_RED}Errore inaspettato nel loop principale: {e}{COLOR_RESET}")
            time.sleep(30)

if __name__ == "__main__":
    main()