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
    return wcswidth(re.sub(r'\x1b\[[0-9;]*m', '', text))

def pad_str(text: str, width: int, align: str = 'left') -> str:
    v_len = visible_len(text)
    padding_needed = max(0, width - v_len)
    if align == 'right': return (' ' * padding_needed) + text
    elif align == 'center':
        left_pad = ' ' * (padding_needed // 2)
        right_pad = ' ' * (padding_needed - len(left_pad))
        return left_pad + text + right_pad
    else: return text + (' ' * padding_needed)

def _create_aligned_cell(left: str, right: str, width: int) -> str:
    len_left, len_right = visible_len(left), visible_len(right)
    padding = ' ' * max(1, width - len_left - len_right)
    return f"{left}{padding}{right}"

# --- Funzioni di Formattazione dei Dati ---

def _format_score_delta(value: float, with_arrow: bool = False) -> str:
    if abs(value) < 0.001: return "-"
    color = COLOR_GREEN if value > 0 else COLOR_RED
    arrow = '↑' if value > 0 else '↓'
    value_str = f"{value:+.2f}"
    return f"{color}{value_str}{' ' + arrow if with_arrow else ''}{COLOR_RESET}"

def _format_flag_delta(value: int) -> str:
    if value == 0: return ""
    color = COLOR_GREEN if value > 0 else COLOR_RED
    return f" ({color}{value:+}{COLOR_RESET})"

def _get_check_letters(checks: List[Dict]) -> str:
    output = []
    for check in checks:
        color = COLOR_GREEN if check['ok'] else COLOR_RED
        output.append(f"{color}{check['action']}{COLOR_RESET}")
    return ' '.join(output)

def _display_alerts_box(failing_services: Dict[str, str], width: int):
    title = " AVVISI DI STATO "
    padding = (width - len(title) - 2) // 2
    top_border = f"╭{'─' * padding}{COLOR_BOLD}{title}{COLOR_RESET}{COLOR_YELLOW}{'─' * (width - len(title) - padding - 2)}╮"
    bottom_border = '╰' + '─' * (width - 2) + '╯'
    print(f"\n{COLOR_YELLOW}{top_border}{COLOR_RESET}")
    for service, reason in failing_services.items():
        content = f"  • {COLOR_RED}{service}{COLOR_RESET}: {reason}"
        line = f"│{pad_str(content, width - 2)}{COLOR_YELLOW}│"
        print(f"{COLOR_YELLOW}{line}{COLOR_RESET}")
    print(f"{COLOR_YELLOW}{bottom_border}{COLOR_RESET}")

def _display_strategic_advice_box(advice: Dict[str, str], width: int):
    """Disegna un riquadro per i consigli strategici."""
    if not advice: return
    title = " CONSIGLI STRATEGICI "
    padding = (width - len(title) - 2) // 2
    top_border = f"╭{'─' * padding}{COLOR_BOLD}{title}{COLOR_RESET}{COLOR_MAGENTA}{'─' * (width - len(title) - padding - 2)}╮"
    bottom_border = '╰' + '─' * (width - 2) + '╯'
    print(f"\n{COLOR_MAGENTA}{top_border}{COLOR_RESET}")
    for service, message in advice.items():
        content = f"  • {COLOR_YELLOW}{service}{COLOR_RESET}: {message}"
        line = f"│{pad_str(content, width - 2)}{COLOR_MAGENTA}│"
        print(f"{COLOR_MAGENTA}{line}{COLOR_RESET}")
    print(f"{COLOR_MAGENTA}{bottom_border}{COLOR_RESET}")

# --- Funzioni di Rendering Principali ---

def _display_game_status_header(status_data: Dict[str, Any]):
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
        freeze_msg = f"{COLOR_YELLOW}!!! PUNTEGGIO CONGELATO !!!{COLOR_RESET}"
        print(f"\n{freeze_msg:^{width}}\n")

def display_scoreboard(team_data: Dict[str, Any], status_data: Dict[str, Any], shutdown_advice: Dict[str, str] = None):
    clear_screen()
    if not team_data or not status_data: return
    _display_game_status_header(status_data)
    score_str = f"{team_data['score']:,.2f}"
    name_str = f"{team_data['name']} ({team_data['shortname']})"
    print(f"{COLOR_BOLD}{COLOR_CYAN}Monitor Team: {name_str}{COLOR_RESET}")
    print(f"Posizione: {COLOR_BOLD}{team_data['position']}{COLOR_RESET} | Punteggio Totale: {COLOR_BOLD}{score_str}{COLOR_RESET} ({_format_score_delta(team_data['score_delta'], with_arrow=True)})\n\n")
    services = team_data.get('services', {})
    if not services: return
    
    term_width, num_services = get_terminal_width(), len(services)
    separator_str, MIN_COL_WIDTH = " │ ", 32
    if term_width < MIN_COL_WIDTH:
        print(f"{COLOR_YELLOW}Finestra del terminale troppo stretta per visualizzare i servizi.{COLOR_RESET}")
        return
    cols_per_row = max(1, min((term_width + len(separator_str)) // (MIN_COL_WIDTH + len(separator_str)), num_services))
    col_width = (term_width - (cols_per_row - 1) * len(separator_str)) // cols_per_row
    service_items = list(services.items())
    
    for i in range(0, num_services, cols_per_row):
        chunk_items = service_items[i:i + cols_per_row]
        num_cols_in_chunk = len(chunk_items)
        columns = [[] for _ in range(num_cols_in_chunk)]

        for j, (s_name, s_data) in enumerate(chunk_items):
            sla_adjusted_score = f"🏆 {COLOR_RESET}{s_data['sla_adjusted_score']:.2f} ({_format_score_delta(s_data['sla_adjusted_score_delta'])})"
            columns[j].append(pad_str(sla_adjusted_score, col_width, 'center'))
            columns[j].append(pad_str(f"{COLOR_BOLD}{s_name}{COLOR_RESET}", col_width, 'center'))
            
            left_score = f"⭐ {COLOR_RESET}{s_data['score']:.2f}"; right_score = _format_score_delta(s_data['score_delta'])
            left_attack = f"⚔️ {COLOR_RESET}{s_data['attack_score']:+.2f} ({s_data['attack_flag']})"; right_attack = f"{_format_score_delta(s_data['attack_score_delta'])}{_format_flag_delta(s_data['attack_flag_delta'])}"
            left_defense = f"🛡️ {COLOR_RESET}{s_data['defense_score']:+.2f} ({s_data['defense_flag']})"; right_defense = f"{_format_score_delta(s_data['defense_score_delta'])}{_format_flag_delta(s_data['defense_flag_delta'])}"
            left_sla = f"🌐 {COLOR_RESET}{s_data['sla']:.2f}%"; right_sla = _format_score_delta(s_data['sla_delta'], with_arrow=True)
            
            columns[j].append(_create_aligned_cell(left_score, right_score, col_width))
            columns[j].append(_create_aligned_cell(left_attack, right_attack, col_width))
            columns[j].append(_create_aligned_cell(left_defense, right_defense, col_width))
            columns[j].append(_create_aligned_cell(left_sla, right_sla, col_width))

            checks = f"🔧 [{_get_check_letters(s_data['checks'])}]"
            columns[j].append(pad_str(checks, col_width, 'center'))
            columns[j].append(' ' * col_width)

        num_rows = len(columns[0]) if columns else 0
        for r in range(num_rows):
            if r == 2: print(separator_str.join(['─' * col_width] * num_cols_in_chunk))
            print(separator_str.join([columns[c][r] for c in range(num_cols_in_chunk)]))

        if i + cols_per_row < num_services:
            print(f"\n{COLOR_MAGENTA}{'═' * term_width}{COLOR_RESET}\n")

    # Footer
    if shutdown_advice:
        _display_strategic_advice_box(shutdown_advice, term_width)
    if team_data['failing_services']:
        _display_alerts_box(team_data['failing_services'], term_width)