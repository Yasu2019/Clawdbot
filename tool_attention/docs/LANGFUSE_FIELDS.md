# Langfuse観測フィールド

- trace.name: tool_attention_route
- input.user_text
- metadata.selected_tools
- metadata.blocked_tools
- metadata.state
- metadata.token_before_estimate
- metadata.token_after_estimate
- metadata.token_reduction_rate
- metadata.used_tool
- metadata.tool_success
- metadata.latency_ms
- metadata.learning_multiplier
- metadata.anomaly_reason

目標KPI:
- tool token 80%以上削減
- tool success rate 90%以上
- dangerous tool without approval 0件
