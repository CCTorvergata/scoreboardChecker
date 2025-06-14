# scoreboard_monitor/main.py

import time
from datetime import datetime

import api_client
import data_processor
import terminal_ui
from config import TARGET_TEAM_SHORTNAME, DEFAULT_TICK_DURATION_SECONDS, COLOR_YELLOW, COLOR_RESET, COLOR_RED

def main_loop():
    """
    Loop principale che orchestra il fetching, la processazione e la visualizzazione dei dati,
    usando l'API di stato e gestendo l'avvio a partita in corso.
    """
    previous_scoreboard_data = None
    last_processed_round = -1

    print("Avvio del monitor... Recupero lo stato iniziale della partita.")
    
    while True:
        try:
            status_data = api_client.fetch_game_status()
            
            if not status_data:
                print(f"{COLOR_YELLOW}Impossibile recuperare lo stato della partita. Riprovo tra 30 secondi...{COLOR_RESET}")
                time.sleep(30)
                continue

            scoreboard_round = status_data.get('scoreboardRound')

            # Se non c'è un nuovo round del tabellone, attendi e riprova
            if scoreboard_round is None or scoreboard_round == last_processed_round:
                time.sleep(15)
                continue

            scoreboard_round = 140

            # --- LOGICA DI AVVIO A PARTITA IN CORSO ---
            # Se è il primo ciclo in assoluto (last_processed_round == -1) e non siamo
            # al round 0, prova a recuperare il round precedente per calcolare i delta.
            if last_processed_round == -1 and scoreboard_round > 0:
                print(f"Avvio a metà partita. Tento di recuperare il round {scoreboard_round - 1} per i calcoli delta...")
                previous_scoreboard_data = api_client.fetch_scoreboard_data(scoreboard_round - 1)
                if not previous_scoreboard_data:
                    print(f"{COLOR_YELLOW}Dati del round precedente non disponibili. I primi delta non saranno calcolati.{COLOR_RESET}")
                else:
                    print(f"Dati del round {scoreboard_round - 1} recuperati con successo.")
            # --- FINE LOGICA DI AVVIO ---

            timestamp = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
            print(f"[{timestamp}] Nuovo round disponibile ({scoreboard_round}). Fetching dati...")

            current_scoreboard_data = api_client.fetch_scoreboard_data(scoreboard_round)

            if current_scoreboard_data:
                processed_data = data_processor.process_data_for_display(
                    current_scoreboard_data, 
                    previous_scoreboard_data, # Ora questo può avere valore fin dal primo ciclo
                    TARGET_TEAM_SHORTNAME
                )

                if processed_data:
                    terminal_ui.display_scoreboard(processed_data, status_data)
                    
                    if processed_data.get('failing_services'):
                        terminal_ui.play_alert_sound()

                    # Aggiorna lo stato per il prossimo ciclo
                    previous_scoreboard_data = current_scoreboard_data
                    last_processed_round = scoreboard_round
                else:
                    print(f"{COLOR_YELLOW}Team '{TARGET_TEAM_SHORTNAME}' non trovato nel tick {scoreboard_round}.{COLOR_RESET}")
            else:
                 print(f"{COLOR_YELLOW}Dati del tabellone non ricevuti per il tick {scoreboard_round}.{COLOR_RESET}")

            # Attendi per una durata pari a quella del round prima del prossimo check
            round_duration = status_data.get('roundTime', DEFAULT_TICK_DURATION_SECONDS)
            time.sleep(round_duration)

        except KeyboardInterrupt:
            print("\nMonitoraggio interrotto dall'utente. Arrivederci!")
            break
        except Exception as e:
            print(f"{COLOR_RED}Errore inaspettato nel loop principale: {e}{COLOR_RESET}")
            time.sleep(30)

if __name__ == "__main__":
    main_loop()