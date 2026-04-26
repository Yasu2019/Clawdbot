import subprocess
import json

def get_processes():
    try:
        # Use tasklist /v to get window titles, or wmic for command lines
        # wmic process where "name like 'python%'" get processid,commandline /format:list
        proc = subprocess.run(['wmic', 'process', 'where', "name like 'python%'", 'get', 'processid,commandline', '/format:list'], 
                            capture_output=True, text=True, errors='ignore')
        return proc.stdout
    except Exception as e:
        return str(e)

print(get_processes())
