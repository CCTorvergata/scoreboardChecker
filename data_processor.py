# scoreboard_monitor/data_processor.py

from typing import Dict, Any

def find_team_in_scoreboard(data: dict, team_shortname: str) -> dict | None:
    """Trova i dati di un team specifico all'interno del JSON del tabellone."""
    if not data or 'scoreboard' not in data:
        return None
    for team in data['scoreboard']:
        if team.get('shortname') == team_shortname:
            return team
    return None

def process_data_for_display(current_data: dict, previous_data: dict | None, team_shortname: str) -> dict | None:
    """
    Estrae e calcola i dati necessari per la visualizzazione, garantendo l'ordine dei check [S P G].
    """
    current_team = find_team_in_scoreboard(current_data, team_shortname)
    previous_team = find_team_in_scoreboard(previous_data, team_shortname) if previous_data else None

    if not current_team:
        return None

    processed = {
        'name': current_team.get('name'),
        'shortname': current_team.get('shortname'),
        'position': current_team.get('position'),
        'score': current_team.get('score'),
        'services': {},
        'failing_services': {}
    }

    prev_services = {s['shortname']: s for s in previous_team['services']} if previous_team else {}

    for service in current_team['services']:
        s_name = service['shortname']
        prev_s = prev_services.get(s_name)

        # Calcolo Punteggi Correnti
        score = service.get('score', 0)
        attacker_score = service.get('attackerScore', 0)
        attack_flag = service.get('stolen', 0)
        victim_score = service.get('victimScore', 0)
        defense_flag = service.get('lost', 0)
        sla = (service['successfulChecks'] / service['totalChecks']) * 100 if service['totalChecks'] > 0 else 0.0
        sla_adjusted_score = score * (sla / 100.0)

        # Calcolo Punteggi Precedenti (se esistono)
        prev_score = prev_s.get('score', 0) if prev_s else 0
        prev_sla = 0.0
        if prev_s and prev_s.get('totalChecks', 0) > 0:
            prev_sla = (prev_s['successfulChecks'] / prev_s['totalChecks']) * 100
        prev_sla_adjusted_score = prev_score * (prev_sla / 100.0)

        # Calcolo Delta
        score_delta = score - prev_score
        attacker_score_delta = attacker_score - (prev_s.get('attackerScore', 0) if prev_s else 0)
        victim_score_delta = victim_score - (prev_s.get('victimScore', 0) if prev_s else 0)
        sla_delta = sla - prev_sla
        sla_adjusted_score_delta = sla_adjusted_score - prev_sla_adjusted_score
        
        attack_flag_delta = service['stolen'] - prev_s.get('stolen', 0) if prev_s else service['stolen']
        defense_flag_delta = -(service['lost'] - prev_s.get('lost', 0) if prev_s else service['lost'])

        # --- Logica per ordinare i check ---
        # 1. Mappa i risultati dei check in un dizionario per un facile accesso.
        check_results = {}
        action_map = {'CHECK_SLA': 'S', 'PUT_FLAG': 'P', 'GET_FLAG': 'G'}
        
        for check in service.get('checks', []):
            action = check.get('action')
            if action in action_map:
                is_ok = check.get('exitCode') == 101
                check_results[action_map[action]] = is_ok
                
                # Se un check fallisce, registra il messaggio di errore
                if not is_ok and s_name not in processed['failing_services']:
                    error_message = check.get('stdout', 'Errore sconosciuto').strip().replace('\n', ' ')
                    processed['failing_services'][s_name] = error_message
        
        # 2. Costruisci la lista finale nell'ordine desiderato [S, P, G].
        # Se un check non è presente nel JSON, viene considerato fallito (ok=False).
        ordered_checks_details = []
        for char in ['S', 'P', 'G']:
            ordered_checks_details.append({
                'action': char,
                'ok': check_results.get(char, False)
            })
        # --- Fine logica ordinamento ---

        processed['services'][s_name] = {
            'score': score,
            'score_delta': score_delta,
            'sla': sla,
            'sla_delta': sla_delta,
            'sla_adjusted_score': sla_adjusted_score,
            'sla_adjusted_score_delta': sla_adjusted_score_delta,
            'attack_score': attacker_score,
            'attack_flag': attack_flag,
            'attack_score_delta': attacker_score_delta,
            'attack_flag_delta': attack_flag_delta,
            'defense_score': victim_score,
            'defense_flag': defense_flag,
            'defense_score_delta': victim_score_delta,
            'defense_flag_delta': defense_flag_delta,
            'checks': ordered_checks_details # Usa la lista ordinata
        }
        
    ordered_services = {}
    if current_data.get('services'):
        for s_info in current_data['services']:
            s_name = s_info['shortname']
            if s_name in processed['services']:
                ordered_services[s_name] = processed['services'][s_name]
        processed['services'] = ordered_services

    return processed