import re, hashlib
from dataclasses import dataclass, asdict
from collections import defaultdict

@dataclass
class CompressionRule:
    name: str
    pattern: str
    replacement: str
    confidence: float = 0.5
    success_count: int = 0
    failure_count: int = 0
    domain: str = "generic"

    def id(self):
        return hashlib.sha1((self.name+self.pattern).encode()).hexdigest()[:12]

class Layer2Evolver:
    def __init__(self, config: dict, rules: list[CompressionRule] | None = None):
        self.config = config
        self.rules = rules or self.default_rules(config)

    def default_rules(self, config):
        cp = config.get('compressible_patterns', {})
        return [
            CompressionRule('iteration_range', cp.get('iteration', r'^(Iteration|Step)\s+\d+.*$'), '[TACO] iteration/progress lines compressed: {count}', 0.85, 3, 0, 'cae'),
            CompressionRule('docker_health_noise', cp.get('docker_health', r'.*(healthcheck|heartbeat|polling).*'), '[TACO] healthcheck/heartbeat noise compressed: {count}', 0.90, 3, 0, 'docker'),
            CompressionRule('progress_noise', cp.get('python_progress', r'.*(\d+%|it/s|ETA).*'), '[TACO] progress meter compressed: {count}', 0.80, 3, 0, 'generic'),
        ]

    def compress_by_rule(self, lines, rule: CompressionRule):
        rx = re.compile(rule.pattern, re.I)
        out, buf = [], []
        def flush():
            nonlocal buf
            if len(buf) >= 3:
                out.append(rule.replacement.format(count=len(buf), first=buf[0], last=buf[-1]))
            else:
                out.extend(buf)
            buf = []
        for line in lines:
            if rx.search(line):
                buf.append(line)
            else:
                flush(); out.append(line)
        flush()
        return out

    def compress(self, lines):
        out = list(lines)
        applied = []
        min_conf = self.config.get('compression', {}).get('min_confidence_to_apply', 0.8)
        for rule in self.rules:
            if rule.confidence >= min_conf and rule.failure_count == 0:
                before = len('\n'.join(out))
                out2 = self.compress_by_rule(out, rule)
                after = len('\n'.join(out2))
                if after < before:
                    out = out2
                    applied.append({'rule': rule.name, 'before_chars': before, 'after_chars': after})
        return out, applied

    def infer_candidate_rules(self, lines):
        # LLMなしでも動く安全な候補生成。頻出の似た行をprefix単位で候補化。
        buckets = defaultdict(list)
        for line in lines:
            key = re.sub(r'\d+', '<N>', line[:100])
            if len(key) > 12:
                buckets[key].append(line)
        cands=[]
        for k,v in buckets.items():
            if len(v) >= 10:
                pat = re.escape(k).replace('<N>', r'\d+') + r'.*'
                cands.append(CompressionRule('auto_'+hashlib.sha1(k.encode()).hexdigest()[:8], pat, f'[TACO] auto-pattern compressed: {{count}} lines / {k[:60]}', 0.55, 0, 0, 'auto'))
        return cands[:20]
