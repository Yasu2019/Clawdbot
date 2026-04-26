from pathlib import Path
import sys
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from taco.controller import TacoController
sample = "\n".join([f"Iteration {i} OK" for i in range(1,80)]) + "\nERROR contact failed at element 120\nWARNING timestep collapse\n" + "\n".join([f"heartbeat {i}" for i in range(40)])
ctl=TacoController(str(Path(__file__).resolve().parents[1]/'taco/config.yaml'))
r=ctl.process(sample, domain='cae')
print(r['text'])
print('\n--- STATS ---')
print(r['stats'])
