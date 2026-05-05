from core.query_router import QueryRouter
from core.evidence_verifier import EvidenceVerifier
from core.cache_manager import CacheManager
from learning.failure_logger import FailureLogger
from learning.self_improver import SelfImprover

from engines.corpus2skill_engine import Corpus2SkillEngine
from engines.lightrag_engine import LightRAGEngine
from engines.graphrag_engine import GraphRAGEngine
from engines.rag_engine import RAGEngine

class Orchestrator:
    def __init__(self):
        self.router = QueryRouter()
        self.verifier = EvidenceVerifier()
        self.cache = CacheManager()
        self.logger = FailureLogger()
        self.improver = SelfImprover()
        self.engines = {
            "corpus": Corpus2SkillEngine(),
            "light": LightRAGEngine(),
            "graph": GraphRAGEngine(),
            "rag": RAGEngine(),
        }

    def run(self, query: str) -> str:
        cached = self.cache.get(query)
        if cached:
            return "[CACHE HIT]\n" + cached
        route = self.router.route(query)
        result = self.engines[route].run(query)
        verified = self.verifier.verify(result)
        self.logger.log(query, verified, route)
        self.improver.learn()
        self.cache.set(query, verified)
        return verified
