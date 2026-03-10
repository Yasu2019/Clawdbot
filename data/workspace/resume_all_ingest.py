
import subprocess
import time
import sys
import os

SCRIPTS = [
    # "ingest_tolerance_book.py", # Completed
    "ingest_tolerance_book_images.py",
    # "ingest_moldflow.py", # Completed
    "ingest_cetol_documentation.py"
]

def main():
    print("=== Launching Knowledge Ingestion Swarm ===")
    
    procs = []
    for script in SCRIPTS:
        print(f"Starting {script}...")
        # Use Popen to run in background (independent process)
        # On Windows, using creationflags=subprocess.CREATE_NEW_CONSOLE might pop up windows, 
        # but here we want them hidden usually?
        # User wants to monitor them via dashboard.
        # We run them as detached subprocesses.
        
        try:
            # shell=True required for some windows path handling, but let's try direct
            p = subprocess.Popen([sys.executable, script], 
                                 cwd=os.path.dirname(os.path.abspath(__file__)),
                                 stdout=subprocess.DEVNULL, 
                                 stderr=subprocess.DEVNULL) # Hide output, rely on status_reporter
            procs.append(p)
            print(f"  -> PID: {p.pid}")
        except Exception as e:
            print(f"  -> Failed: {e}")
            
    print("\nAll scripts launched.")
    
    if len(sys.argv) > 1 and sys.argv[1] == "--no-dashboard":
        print("Skipping dashboard (Background mode).")
        return

    print("Starting Dashboard in 3 seconds...")
    time.sleep(3)
    
    # Run dashboard in THIS process (blocking)
    import monitor_dashboard
    monitor_dashboard.main()

if __name__ == "__main__":
    main()
