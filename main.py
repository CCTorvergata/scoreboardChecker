# scoreboard_monitor/main.py

import time
from datetime import datetime
import signal

import api_client
import data_processor
import terminal_ui
from config import TARGET_TEAM_SHORTNAME, DEFAULT_TICK_DURATION_SECONDS, COLOR_YELLOW, COLOR_RESET, COLOR_RED, COLOR_GREEN, COLOR_BOLD

NEEDS_REDRAW = False
def handle_resize(signum, frame):
    global NEEDS_REDRAW
    NEEDS_REDRAW = True

def synchronize_and_wait_for_next_tick(initial_round: int):
    print(f"\n{COLOR_YELLOW}Snapshot visualizzato. In attesa del round {initial_round + 1} per la sincronizzazione...{COLOR_RESET}")
    while True:
        time.sleep(5)
        current_status = api_client.fetch_game_status()
        if current_status and current_status.get('scoreboardRound') is not None:
            new_round = current_status.get('scoreboardRound')
            if new_round > initial_round:
                print(f"\n{COLOR_GREEN}Sincronizzato!{COLOR_RESET} Caricamento dati per il round {COLOR_BOLD}{new_round}{COLOR_RESET}.")
                time.sleep(1)
                return current_status
    return None

def main():
    if hasattr(signal, 'SIGWINCH'):
        signal.signal(signal.SIGWINCH, handle_resize)

    print(f"{COLOR_YELLOW}Recupero snapshot iniziale della scoreboard...{COLOR_RESET}")
    status_data = api_client.fetch_game_status()
    if not status_data or status_data.get('scoreboardRound') is None:
        print(f"{COLOR_RED}Impossibile recuperare lo stato iniziale. Uscita.{COLOR_RESET}")
        return

    current_round = status_data.get('scoreboardRound')
    
    if current_round == 0:
        print("La partita è al round 0. In attesa del primo round per iniziare...")
        status_data = synchronize_and_wait_for_next_tick(0)
        if not status_data: return
        current_round = status_data.get('scoreboardRound')

    print(f"Visualizzazione dei dati per il round attuale: {COLOR_BOLD}{current_round}{COLOR_RESET}")
    
    # Inizializza lo storico delle perdite
    service_loss_history = {}

    snapshot_scoreboard_data = api_client.fetch_scoreboard_data(current_round)
    snapshot_previous_data = api_client.fetch_scoreboard_data(current_round - 1)

    if not snapshot_scoreboard_data:
        print(f"{COLOR_RED}Impossibile recuperare i dati della scoreboard per il round {current_round}.{COLOR_RESET}")
    else:
        processed_snapshot = data_processor.process_data_for_display(
            snapshot_scoreboard_data, snapshot_previous_data, TARGET_TEAM_SHORTNAME
        )
        if processed_snapshot:
            # Aggiorna lo storico con i dati dello snapshot
            if processed_snapshot.get('services'):
                for s_name, s_data in processed_snapshot['services'].items():
                    if s_name not in service_loss_history: service_loss_history[s_name] = []
                    loss = abs(s_data['defense_score_delta'])
                    if loss > 0: service_loss_history[s_name].insert(0, loss)
                    service_loss_history[s_name] = service_loss_history[s_name][:5]

            shutdown_advice = data_processor.calculate_shutdown_advice(processed_snapshot, status_data, service_loss_history)
            terminal_ui.display_scoreboard(processed_snapshot, status_data, shutdown_advice)
            if processed_snapshot.get('failing_services'):
                terminal_ui.play_alert_sound()
    
    status_data = synchronize_and_wait_for_next_tick(current_round)
    if not status_data: return

    last_processed_round = current_round
    previous_scoreboard_data = snapshot_scoreboard_data
    last_processed_data = None
    last_status_data = None

    while True:
        try:
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
                        # Aggiorna lo storico con i nuovi dati
                        if processed_data.get('services'):
                            for s_name, s_data in processed_data['services'].items():
                                if s_name not in service_loss_history: service_loss_history[s_name] = []
                                loss = abs(s_data['defense_score_delta'])
                                service_loss_history[s_name].insert(0, loss)
                                service_loss_history[s_name] = service_loss_history[s_name][:5]

                        shutdown_advice = data_processor.calculate_shutdown_advice(processed_data, status_data, service_loss_history)
                        last_processed_data = processed_data
                        last_status_data = status_data
                        terminal_ui.display_scoreboard(processed_data, status_data, shutdown_advice)
                        if processed_data.get('failing_services'):
                            terminal_ui.play_alert_sound()
                        
                        previous_scoreboard_data = current_scoreboard_data
                        last_processed_round = scoreboard_round

            global NEEDS_REDRAW
            wait_duration = status_data.get('roundTime', DEFAULT_TICK_DURATION_SECONDS)
            sleep_start_time = time.time()
            
            while time.time() - sleep_start_time < wait_duration:
                if NEEDS_REDRAW:
                    NEEDS_REDRAW = False
                    if last_processed_data and last_status_data:
                        shutdown_advice = data_processor.calculate_shutdown_advice(last_processed_data, last_status_data, service_loss_history)
                        terminal_ui.display_scoreboard(last_processed_data, last_status_data, shutdown_advice)
                time.sleep(0.2)
            
            status_data = None

        except KeyboardInterrupt:
            print("\nMonitoraggio interrotto dall'utente. Arrivederci!")
            break
        except Exception as e:
            print(f"{COLOR_RED}Errore inaspettato nel loop principale: {e}{COLOR_RESET}")
            time.sleep(30)

if __name__ == "__main__":
    main()