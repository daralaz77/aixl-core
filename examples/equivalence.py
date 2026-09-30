import os, sys; sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from aixl import compare
r = compare("Analiza las ventas de Q1 2026.", "Examina las ventas del primer trimestre de 2026.")
print(r.equivalent, round(r.similarity, 2), r.diff)      # True 1.0 []
