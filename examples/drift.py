import os, sys; sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from aixl import detect_drift

r = detect_drift("Elimina el reporte.", "No elimines el reporte.")
print(r.level, r.critical)
for d in r.differences: print(d.field, d.source, "->", d.target, d.severity)
