from core.orchestrator import Orchestrator

if __name__ == "__main__":
    orchestrator = Orchestrator()
    print("AKO Ultimate System started. Type 'exit' to quit.")
    while True:
        query = input(">> ").strip()
        if query.lower() in {"exit", "quit"}:
            break
        result = orchestrator.run(query)
        print(result)
