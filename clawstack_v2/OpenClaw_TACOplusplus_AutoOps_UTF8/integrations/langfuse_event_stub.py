def emit_taco_event(langfuse_client, trace_id, stats):
    try:
        langfuse_client.event(
            trace_id=trace_id,
            name='taco_compression',
            metadata=stats,
        )
    except Exception:
        pass
