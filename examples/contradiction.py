import os, sys; sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from aixl import detect_contradiction
print(detect_contradiction("Permite eliminar el reporte.", "Prohíbe eliminar el reporte.").to_dict())
print(detect_contradiction("Analiza las ventas de Q1 2026.", "Analiza las ventas de Q2 2026.").to_dict())   # different, NOT contradictory
