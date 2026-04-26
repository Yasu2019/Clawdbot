import re
COMPLAINT_PATTERNS = [
    r'show (me )?full output', r'need full output', r'information missing',
    r'not enough context', r'cannot determine', r'再表示', r'全文', r'情報が足りない'
]

def agent_complained(text: str) -> bool:
    return any(re.search(p, text or '', re.I) for p in COMPLAINT_PATTERNS)

def command_loop_detected(commands: list[str], threshold=3) -> bool:
    if len(commands) < threshold: return False
    return len(set(commands[-threshold:])) == 1
