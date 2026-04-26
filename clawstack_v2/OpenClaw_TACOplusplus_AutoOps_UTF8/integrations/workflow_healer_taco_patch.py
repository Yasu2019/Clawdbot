from taco.brake import command_loop_detected, agent_complained

def taco_should_relax_compression(command_history, agent_message):
    return command_loop_detected(command_history, threshold=3) or agent_complained(agent_message)

def healer_event_payload(stats, reason):
    return {
        'source': 'taco++',
        'reason': reason,
        'stats': stats,
        'action': 'relax_compression_and_request_guarded_full_context'
    }
