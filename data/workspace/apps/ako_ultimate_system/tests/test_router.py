from core.query_router import QueryRouter

def test_router():
    r = QueryRouter()
    assert r.route("IATF条項") == "corpus"
    assert r.route("不具合の原因") == "graph"
