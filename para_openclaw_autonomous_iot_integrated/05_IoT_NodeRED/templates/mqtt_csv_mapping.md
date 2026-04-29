# MQTT/CSV Mapping Template

Expected fields:
- timestamp
- machine_id
- shot
- spm
- chokotei
- jyotai

Recommended destination:
`02_PARA_Vault/90_Inbox/iot_logs/YYYYMMDD_machine.csv`

Routing rule:
- normal logs -> 40_Archives/YYYYMM
- active investigation logs -> 10_Projects/ESP32_Press_IoT/YYYYMM
- anomaly summaries -> 40_Archives/Past_Troubles/YYYYMM
