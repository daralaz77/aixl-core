"""Shared metric helpers."""

def prf(tp, fp, fn, tn):
    p = tp / (tp + fp) if tp + fp else 0.0
    r = tp / (tp + fn) if tp + fn else 0.0
    f1 = 2 * p * r / (p + r) if p + r else 0.0
    n = tp + fp + fn + tn
    return {"tp": tp, "fp": fp, "fn": fn, "tn": tn, "n": n, "accuracy": round((tp + tn) / n, 4) if n else 0.0,
            "precision": round(p, 4), "recall": round(r, 4), "f1": round(f1, 4),
            "false_positive_rate": round(fp / (fp + tn), 4) if fp + tn else 0.0,
            "false_negative_rate": round(fn / (fn + tp), 4) if fn + tp else 0.0}
