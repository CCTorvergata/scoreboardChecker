# scoreboard_monitor/terminal_ui.py

import os
import shutil
import re
from typing import Dict, Any, List
from datetime import datetime, timezone
from wcwidth import wcswidth

from config import (
    COLOR_GREEN, COLOR_RED, COLOR_YELLOW, COLOR_CYAN, COLOR_MAGENTA,
    COLOR_BOLD, COLOR_RESET
)

# --- Funzioni Helper per la UI ---

def get_terminal_width() -> int:
    return shutil.get_terminal_size().columns

def clear_screen():
    os.system('cls' if os.name == 'nt' else 'clear')

def play_alert_sound():
    print('\a', end='', flush=True)

def visible_len(text: str) -> int:
    """Calcola la larghezza visibile di una stringa, gestendo caratteri wide e codici ANSI."""
    return wcswidth(re.sub(r'\x1b\[[0-9;]*m', '', text))

def pad_str(text: str, width: int, align: str = 'left') -> str:
    """Aggiunge padding a una stringa, usando wcswidth per un corretto allineamento."""
    v_len = visible_len(text)
    padding_needed = max(0, width - v_len)
    
    if align == 'right':
        return (' ' * padding_needed) + text
    elif align == 'center':
        left_pad = ' ' * (padding_needed // 2)
        right_pad = ' ' * (padding_needed - len(left_pad))
        return left_pad + text + right_pad
    else:
        return text + (' ' * padding_needed)

def _create_aligned_cell(left: str, right: str, width: int) -> str:
    """Crea una cella con contenuto allineato a sx e dx, usando wcswidth."""
    len_left = visible_len(left)
    len_right = visible_len(right)
    padding = ' ' * max(1, width - len_left - len_right)
    return f"{left}{padding}{right}"

# --- Funzioni di Formattazione dei Dati ---

def _format_score_delta(value: float, with_arrow: bool = False) -> str:
    """Formatta la variazione di un punteggio."""
    if abs(value) < 0.001:
        return f"{0.0:.2f}"
    
    color = COLOR_GREEN if value > 0 else COLOR_RED
    arrow = '↑' if value > 0 else '↓'
    value_str = f"{value:+.2f}" if value > 0 else f"{value:.2f}"
    
    return f"{color}{value_str}{' ' + arrow if with_arrow else ''}{COLOR_RESET}"

def _format_flag_delta(value: int) -> str:
    """Formatta il delta dei flag. Positivo è buono (verde), negativo è cattivo (rosso)."""
    if value == 0: return ""
    color = COLOR_GREEN if value > 0 else COLOR_RED
    return f"({color}{value:+}{COLOR_RESET})"

def _get_check_letters(checks: List[Dict]) -> str:
    output = []
    for check in checks:
        color = COLOR_GREEN if check['ok'] else COLOR_RED
        output.append(f"{color}{check['action']}{COLOR_RESET}")
    return ' '.join(output)

# --- Funzioni di Rendering Principali ---

def _display_game_status_header(status_data: Dict[str, Any]):
    # (Invariata)
    now = datetime.now(timezone.utc)
    start_time = datetime.fromisoformat(status_data['start'].replace('Z', '+00:00'))
    end_time = datetime.fromisoformat(status_data['end'].replace('Z', '+00:00'))

    time_remaining = end_time - now
    time_rem_str = "Concluso"
    if time_remaining.total_seconds() >= 0:
        hours, rem = divmod(int(time_remaining.total_seconds()), 3600)
        minutes, _ = divmod(rem, 60)
        time_rem_str = f"{hours:02d}:{minutes:02d} rimanenti"

    total_duration = (end_time - start_time).total_seconds()
    elapsed_duration = (now - start_time).total_seconds()
    progress = min(1.0, elapsed_duration / total_duration) if total_duration > 0 else 0
    
    width = get_terminal_width()
    static_text = f"Progresso Gara: [] {progress:.1%} ({time_rem_str})"
    progress_bar_width = max(10, width - len(static_text))
    filled_width = int(progress * progress_bar_width)
    bar = '█' * filled_width + '─' * (progress_bar_width - filled_width)

    print(f"Progresso Gara: [{bar}] {progress:.1%} ({time_rem_str})")
    
    current_round, total_rounds, freeze_round = status_data.get('currentRound', 'N/A'), status_data.get('rounds', 'N/A'), status_data.get('freezeRound', 'N/A')
    print(f"Round: {COLOR_BOLD}{current_round}/{total_rounds}{COLOR_RESET} | Freeze al round: {COLOR_YELLOW}{freeze_round}{COLOR_RESET}")

    if current_round is not None and current_round >= freeze_round:
        freeze_msg = "!!! PUNTEGGIO CONGELATO !!!"
        print(f"\n{freeze_msg:^{width}}\n")

def display_scoreboard(team_data: Dict[str, Any], status_data: Dict[str, Any]):
    clear_screen()
    if not team_data or not status_data: return

    _display_game_status_header(status_data)
    
    score_str = f"{team_data['score']:,.2f}"
    name_str = f"{team_data['name']} ({team_data['shortname']})"
    print(f"{COLOR_BOLD}{COLOR_CYAN}Monitor Team: {name_str}{COLOR_RESET}")
    print(f"Posizione: {COLOR_BOLD}{team_data['position']}{COLOR_RESET} | Punteggio Totale: {COLOR_BOLD}{score_str}{COLOR_RESET}\n")

    services = team_data.get('services', {})
    if not services: return
    
    num_services, term_width = len(services), get_terminal_width()
    separator_str = " │ "
    col_width = (term_width - (num_services - 1) * len(separator_str)) // num_services if num_services > 0 else term_width
    
    if col_width < 32:
        print(f"{COLOR_YELLOW}Finestra del terminale troppo stretta.{COLOR_RESET}")
        return

    columns = [[] for _ in range(8)]
    
    for i, (s_name, s_data) in enumerate(services.items()):
        columns[i].append(pad_str(f"🏆 {s_data['sla_adjusted_score']:.2f}", col_width, 'center'))
        columns[i].append(pad_str(f"{COLOR_BOLD}{s_name}{COLOR_RESET}", col_width, 'center'))
        
        # Le parti di sinistra ora hanno un COLOR_RESET esplicito prima del numero
        # per evitare "sanguinamenti" di colore dal carattere dell'icona.
        left_score = f"⭐ {COLOR_RESET}{s_data['score']:.2f}"
        left_attack = f"⚔️ {COLOR_RESET}{s_data['attack_score']:+.2f} ({s_data['attack_flag']})"
        left_defense = f"🛡️ {COLOR_RESET}{s_data['defense_score']:+.2f} ({s_data['defense_flag']})"
        left_sla = f"🌐 {COLOR_RESET}{s_data['sla']:.2f}%"
        left_checks = f"🔧 [{_get_check_letters(s_data['checks'])}]"

        right_score = _format_score_delta(s_data['score_delta'])
        right_attack = f"{_format_score_delta(s_data['attack_score_delta'])} {_format_flag_delta(s_data['attack_flag_delta'])}"
        right_defense = f"{_format_score_delta(s_data['defense_score_delta'])} {_format_flag_delta(s_data['defense_flag_delta'])}"
        right_sla = _format_score_delta(s_data['sla_delta'], with_arrow=True)
        
        columns[i].append(_create_aligned_cell(left_score, right_score, col_width))
        columns[i].append(_create_aligned_cell(left_attack, right_attack, col_width))
        columns[i].append(_create_aligned_cell(left_defense, right_defense, col_width))
        columns[i].append(_create_aligned_cell(left_sla, right_sla, col_width))
        columns[i].append(pad_str(left_checks, col_width))
        columns[i].append(' ' * col_width)

    num_rows = len(columns[0]) if columns else 0
    for r in range(num_rows):
        if r == 2:
            print(separator_str.join(['─' * col_width] * num_services))
        print(separator_str.join([columns[c][r] for c in range(num_services)]))
    
    print("")
    if team_data['failing_services']:
        alerts = [f"{COLOR_RED}{s}{COLOR_RESET} ({r})" for s, r in team_data['failing_services'].items()]
        print(f"{COLOR_YELLOW}AVVISO: Problemi di operatività rilevati per i seguenti servizi: {', '.join(alerts)}")