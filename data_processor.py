# scoreboard_monitor/data_processor.py

from typing import Dict, Any, List

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
    
    current_total_score = current_team.get('score', 0)
    previous_total_score = previous_team.get('score', 0) if previous_team else current_total_score
    score_delta = current_total_score - previous_total_score
    
    processed = {
        'name': current_team.get('name'),
        'shortname': current_team.get('shortname'),
        'position': current_team.get('position'),
        'score': current_team.get('score'),
        'score_delta': score_delta,
        'services': {},
        'failing_services': {}
    }

    prev_services = {s['shortname']: s for s in previous_team['services']} if previous_team else {}

    for service in current_team['services']:
        s_name = service['shortname']
        prev_s = prev_services.get(s_name)

        score = service.get('score', 0)
        attacker_score = service.get('attackerScore', 0)
        attack_flag = service.get('stolen', 0)
        victim_score = service.get('victimScore', 0)
        defense_flag = service.get('lost', 0)
        sla = (service['successfulChecks'] / service['totalChecks']) * 100 if service['totalChecks'] > 0 else 0.0
        sla_adjusted_score = score * (sla / 100.0)

        prev_score = prev_s.get('score', 0) if prev_s else 0
        prev_sla = 0.0
        if prev_s and prev_s.get('totalChecks', 0) > 0:
            prev_sla = (prev_s['successfulChecks'] / prev_s['totalChecks']) * 100
        prev_sla_adjusted_score = prev_score * (prev_sla / 100.0)

        score_delta = score - prev_score
        attacker_score_delta = attacker_score - (prev_s.get('attackerScore', 0) if prev_s else 0)
        victim_score_delta = victim_score - (prev_s.get('victimScore', 0) if prev_s else 0)
        sla_delta = sla - prev_sla
        sla_adjusted_score_delta = sla_adjusted_score - prev_sla_adjusted_score
        attack_flag_delta = service['stolen'] - prev_s.get('stolen', 0) if prev_s else service['stolen']
        defense_flag_delta = -(service['lost'] - prev_s.get('lost', 0) if prev_s else service['lost'])

        check_results = {}
        action_map = {'CHECK_SLA': 'S', 'PUT_FLAG': 'P', 'GET_FLAG': 'G'}
        for check in service.get('checks', []):
            action = check.get('action')
            if action in action_map:
                is_ok = check.get('exitCode') == 101
                check_results[action_map[action]] = is_ok
                if not is_ok and s_name not in processed['failing_services']:
                    error_message = check.get('stdout', 'Errore sconosciuto').strip().replace('\n', ' ')
                    processed['failing_services'][s_name] = error_message
        
        ordered_checks_details = []
        for char in ['S', 'P', 'G']:
            ordered_checks_details.append({'action': char, 'ok': check_results.get(char, False)})

        processed['services'][s_name] = {
            'score': score, 'score_delta': score_delta,
            'sla': sla, 'sla_delta': sla_delta,
            'sla_adjusted_score': sla_adjusted_score, 'sla_adjusted_score_delta': sla_adjusted_score_delta,
            'attack_score': attacker_score, 'attack_flag': attack_flag,
            'attack_score_delta': attacker_score_delta, 'attack_flag_delta': attack_flag_delta,
            'defense_score': victim_score, 'defense_flag': defense_flag,
            'defense_score_delta': victim_score_delta, 'defense_flag_delta': defense_flag_delta,
            'checks': ordered_checks_details,
            'successfulChecks': service.get('successfulChecks', 0),
            'totalChecks': service.get('totalChecks', 0)
        }
        
    ordered_services = {}
    if current_data.get('services'):
        for s_info in current_data['services']:
            s_name = s_info['shortname']
            if s_name in processed['services']:
                ordered_services[s_name] = processed['services'][s_name]
        processed['services'] = ordered_services

    return processed

def calculate_shutdown_advice(
    team_data: Dict[str, Any], 
    status_data: Dict[str, Any], 
    loss_history: Dict[str, List[float]]
) -> Dict[str, str]:
    """
    Analizza ogni servizio, usando una media mobile delle perdite, per determinare 
    se un arresto strategico potrebbe massimizzare il punteggio finale.
    """
    advice = {}
    if not team_data or not status_data or not team_data.get('services'):
        return advice

    current_round = status_data.get('scoreboardRound')
    total_rounds = status_data.get('rounds')

    if current_round is None or total_rounds is None or current_round >= total_rounds:
        return advice

    remaining_rounds = total_rounds - current_round

    for s_name, s_data in team_data['services'].items():
        history = loss_history.get(s_name, [])
        
        if not history:
            continue

        avg_loss = sum(history) / len(history)
        
        if avg_loss < 0.01:
            continue
            
        points_lost_per_round_estimate = avg_loss
        estimated_future_loss_if_up = remaining_rounds * points_lost_per_round_estimate
        current_service_score = s_data['score']
        
        final_score_if_up = (current_service_score - estimated_future_loss_if_up) * (s_data['sla'] / 100.0)

        current_up_ticks = s_data.get('successfulChecks', 0)
        final_sla_if_down = (current_up_ticks / total_rounds) * 100
        final_score_if_down = current_service_score * (final_sla_if_down / 100.0)
        
        if final_score_if_down > final_score_if_up:
            advice_msg = f"(media su {len(history)} round)"
            advice[s_name] = (
                f"Valutare shutdown {advice_msg}. "
                f"Stima punteggio finale con shutdown: {final_score_if_down:,.0f}. "
                f"Stima se online: {final_score_if_up:,.0f}."
            )
            
    return advice