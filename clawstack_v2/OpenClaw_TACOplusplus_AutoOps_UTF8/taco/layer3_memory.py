import os, json
from dataclasses import asdict

class Layer3Memory:
    def __init__(self, enabled=True, local_path='taco_rules_local.jsonl'):
        self.enabled = enabled
        self.local_path = local_path

    def save_rule_local(self, rule):
        with open(self.local_path, 'a', encoding='utf-8') as f:
            f.write(json.dumps(asdict(rule), ensure_ascii=False) + '\n')

    def load_rules_local(self):
        if not os.path.exists(self.local_path):
            return []
        from taco.layer2_evolve import CompressionRule
        rules=[]
        with open(self.local_path, encoding='utf-8') as f:
            for line in f:
                try: rules.append(CompressionRule(**json.loads(line)))
                except Exception: pass
        return rules

    def save_rule_qdrant_best_effort(self, rule):
        if not self.enabled:
            return False
        # qdrant-clientが無い/未起動でも落とさない
        try:
            from qdrant_client import QdrantClient
            from qdrant_client.models import Distance, VectorParams, PointStruct
            url=os.getenv('QDRANT_URL','http://localhost:6333')
            col=os.getenv('QDRANT_COLLECTION','taco_rules')
            cli=QdrantClient(url=url)
            try:
                cli.create_collection(col, vectors_config=VectorParams(size=4, distance=Distance.COSINE))
            except Exception:
                pass
            vec=[rule.confidence, rule.success_count, rule.failure_count, len(rule.pattern)/1000]
            cli.upsert(col, [PointStruct(id=abs(hash(rule.id())) % (2**63), vector=vec, payload=asdict(rule))])
            return True
        except Exception:
            return False
