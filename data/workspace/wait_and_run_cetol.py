
import time
import subprocess
import os

FISCHER_SCRIPT = "ingest_fischer_figures.py"
CETOL_SCRIPT = "/home/node/clawd/ingest_cetol_documentation.py"
LOG_FILE = "/home/node/clawd/ingest_cetol.log"

print(f"Waiting for {FISCHER_SCRIPT} to finish...")

while True:
    try:
        # Check if process is running
        output = subprocess.check_output(["pgrep", "-f", FISCHER_SCRIPT])
        pids = output.decode().strip().split('\n')
        # Filter out empty strings
        pids = [p for p in pids if p]
        
        if not pids:
            print("Fischer script finished.")
            break
            
        print(f"Fischer script still running (PIDs: {pids}). Waiting 60s...")
        time.sleep(60)
    except subprocess.CalledProcessError:
        # pgrep returns non-zero if no process found
        print("Fischer script finished (no process found).")
        break
    except Exception as e:
        print(f"Error checking process: {e}")
        time.sleep(60)

with open(LOG_FILE, "w") as log:
    print("Starting CETOL Extraction...", file=log)
    subprocess.run(["python3", "/home/node/clawd/extract_cetol_figures.py"], stdout=log, stderr=subprocess.STDOUT)
    print("CETOL Extraction Finished.", file=log)

    print("Starting CETOL Ingestion...", file=log)
    subprocess.run(["python3", CETOL_SCRIPT], stdout=log, stderr=subprocess.STDOUT)
    print("CETOL Ingestion Finished.", file=log)

print("CETOL processing complete. Check log file for details.")
