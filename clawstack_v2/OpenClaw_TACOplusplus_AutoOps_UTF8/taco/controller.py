import yaml, json
from pathlib import Path
from taco.layer1_guard import Layer1Guard
from taco.layer2_evolve import Layer2Evolver
from taco.layer3_memory import Layer3Memory

class TacoController:
    def __init__(self, config_path='taco/config.yaml'):
        self.config = yaml.safe_load(Path(config_path).read_text(encoding='utf-8'))
        self.guard = Layer1Guard(
            self.config.get('critical_patterns', []),
            self.config.get('critical_keep_context_before', 8),
            self.config.get('critical_keep_context_after', 16),
        )
        self.memory = Layer3Memory(self.config.get('qdrant', {}).get('enabled', True))
        rules = self.memory.load_rules_local()
        self.evolver = Layer2Evolver(self.config, rules or None)

    def process(self, text: str, domain='generic') -> dict:
        max_input = self.config.get('max_input_chars', 400000)
        if len(text) > max_input:
            text = text[:max_input//2] + '\n[TACO] middle truncated before guarded compression\n' + text[-max_input//2:]
        guard_result = self.guard.split(text)
        compressed, applied = self.evolver.compress(guard_result.normal_lines)
        first_n = self.config.get('compression', {}).get('preserve_first_n_lines', 80)
        last_n = self.config.get('compression', {}).get('preserve_last_n_lines', 160)
        protected = guard_result.protected_lines
        merged = []
        merged.extend(['[TACO] === PROTECTED CRITICAL CONTEXT ==='])
        merged.extend(protected)
        merged.extend(['[TACO] === COMPRESSED NORMAL CONTEXT ==='])
        merged.extend(compressed)
        out = '\n'.join(merged)
        max_out = self.config.get('max_output_chars', 80000)
        if len(out) > max_out:
            out = out[:max_out//2] + '\n[TACO] output length capped, tail preserved\n' + out[-max_out//2:]
        candidates = self.evolver.infer_candidate_rules(guard_result.normal_lines)
        for rule in candidates:
            self.memory.save_rule_local(rule)
            self.memory.save_rule_qdrant_best_effort(rule)
        return {
            'text': out,
            'stats': {
                'input_chars': len(text), 'output_chars': len(out),
                'protected_lines': guard_result.protected_count,
                'applied_rules': applied,
                'candidate_rules': len(candidates),
            }
        }
