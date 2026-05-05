from core.orchestrator import Orchestrator

TESTS = [
    "IATF 8.5.1の条項に関係する手順を教えて",
    "この不具合の原因をなぜなぜ分析してください",
    "検査要領書を検索してください",
]

def run_tests():
    o = Orchestrator()
    for t in TESTS:
        print("---")
        print("Q:", t)
        print(o.run(t))

if __name__ == "__main__":
    run_tests()
