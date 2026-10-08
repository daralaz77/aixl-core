"""Encoding layer: AIXL -> SemanticFrame -> natural-language reconstruction (spec §30-31)."""
import re

from aixl.legacy02.core.parser import parse
from aixl.legacy02.core.semantic_frame import SemanticFrame

ACT = {
 "es": dict(ANALYZE="analizar", FIND="encontrar", COMPARE="comparar", SEARCH="buscar", SUMMARIZE="resumir",
   GENERATE="generar", CREATE="crear", CALCULATE="calcular", CHECK="verificar", VALIDATE="validar",
   TRANSLATE="traducir", GET="obtener", RETRIEVE="recuperar", DELETE="eliminar", EXECUTE="ejecutar",
   TRANSFORM="transformar", CLASSIFY="clasificar", EXTRACT="extraer", PREDICT="predecir"),
 "en": dict(ANALYZE="analyze", FIND="find", COMPARE="compare", SEARCH="search", SUMMARIZE="summarize",
   GENERATE="generate", CREATE="create", CALCULATE="calculate", CHECK="check", VALIDATE="validate",
   TRANSLATE="translate", GET="get", RETRIEVE="retrieve", DELETE="delete", EXECUTE="execute",
   TRANSFORM="transform", CLASSIFY="classify", EXTRACT="extract", PREDICT="predict"),
}
NOUN = {
 "es": dict(SALES="las ventas", CUSTOMERS="los clientes", USERS="los usuarios", DATA="los datos",
   DATASET="el dataset", REPORT="el reporte", DOCUMENT="el documento", IMAGE="la imagen", AUDIO="el audio",
   VIDEO="el video", ANOMALY="anomalías", PERSON="personas", COMPANY="empresas", PRODUCT="productos",
   MODEL="modelos", RESULT="el resultado", EVENT="eventos"),
 "en": dict(SALES="the sales", CUSTOMERS="the customers", USERS="the users", DATA="the data",
   DATASET="the dataset", REPORT="the report", DOCUMENT="the document", IMAGE="the image", AUDIO="the audio",
   VIDEO="the video", ANOMALY="anomalies", PERSON="people", COMPANY="companies", PRODUCT="products",
   MODEL="models", RESULT="the result", EVENT="events"),
}
GOAL = {"es": dict(ANOMALY_DETECTION="detección de anomalías", COMPARISON="comparación", SUMMARY="resumen",
          TRANSLATION="traducción", VALIDATION="validación", DATA_RETRIEVAL="recuperación de datos",
          CONTENT_GENERATION="generación de contenido"),
        "en": dict(ANOMALY_DETECTION="anomaly detection", COMPARISON="comparison", SUMMARY="summary",
          TRANSLATION="translation", VALIDATION="validation", DATA_RETRIEVAL="data retrieval",
          CONTENT_GENERATION="content generation")}
ORD_ES = {1: "primer", 2: "segundo", 3: "tercer", 4: "cuarto"}
ORD_EN = {1: "first", 2: "second", 3: "third", 4: "fourth"}
MONTH_ES = "enero febrero marzo abril mayo junio julio agosto septiembre octubre noviembre diciembre".split()
MONTH_EN = "January February March April May June July August September October November December".split()
MON3 = "JAN FEB MAR APR MAY JUN JUL AUG SEP OCT NOV DEC".split()
REL = {"es": dict(TODAY="hoy", YESTERDAY="ayer", TOMORROW="mañana", THIS_WEEK="esta semana",
        THIS_MONTH="este mes", THIS_YEAR="este año", LAST_YEAR="el año pasado", LAST_MONTH="el mes pasado",
        LAST_WEEK="la semana pasada", NEXT_YEAR="el próximo año", NEXT_MONTH="el próximo mes",
        NEXT_WEEK="la próxima semana"),
       "en": dict(TODAY="today", YESTERDAY="yesterday", TOMORROW="tomorrow", THIS_WEEK="this week",
        THIS_MONTH="this month", THIS_YEAR="this year", LAST_YEAR="last year", LAST_MONTH="last month",
        LAST_WEEK="last week", NEXT_YEAR="next year", NEXT_MONTH="next month", NEXT_WEEK="next week")}
OP = {"es": {">=": "igual o superior a", "<=": "igual o inferior a", ">": "mayor que", "<": "menor que",
             "=": "igual a", "!=": "distinto de"},
      "en": {">=": "at least", "<=": "at most", ">": "greater than", "<": "less than",
             "=": "equal to", "!=": "not equal to"}}
CMP = re.compile(r"^(.*?)(>=|<=|!=|>|<|=)(.*)$")


def _num(s):
    return re.sub(r"(?<![\d])\.(\d)", r"0.\1", s)


def _time(t, lg):
    t = t.strip('"')
    if "," in t:
        return (" y " if lg == "es" else " and ").join(_time(x, lg) for x in t.split(","))
    m = re.match(r"^Q(\d)(?:-(\d{4}))?$", t)
    if m:
        n, y = int(m.group(1)), m.group(2)
        if lg == "es":
            return f"{ORD_ES[n]} trimestre" + (f" de {y}" if y else " (año no especificado)")
        return f"{ORD_EN[n]} quarter" + (f" of {y}" if y else " (year not specified)")
    m = re.match(r"^(\d{4})-(\d{2})$", t)
    if m:
        mo = int(m.group(2)) - 1
        return f"{(MONTH_ES if lg=='es' else MONTH_EN)[mo]} {'de ' if lg=='es' else ''}{m.group(1)}"
    if t in REL[lg]:
        return REL[lg][t]
    if t in MON3:
        i = MON3.index(t)
        return (MONTH_ES if lg == "es" else MONTH_EN)[i] + (" (año no especificado)" if lg == "es" else " (year not specified)")
    return t


def _cond(c, lg):
    if c == "AMBIGUOUS_MODALITY":
        return "modalidad ambigua (¿permiso o solicitud?)" if lg == "es" else "ambiguous modality (permission or request?)"
    if c == "AMBIGUOUS_YEAR":
        return "año ambiguo (no especificado)" if lg == "es" else "ambiguous year (not specified)"
    m = re.match(r"^(.+)_EXISTS$", c)
    if m:
        n = NOUN[lg].get(m.group(1), m.group(1).lower())
        return f"si existen {n}" if lg == "es" else f"if there are {n}"
    m = CMP.match(c)
    if m:
        l, op, r = m.groups()
        left = {"H": "la confianza" if lg == "es" else "confidence"}.get(l, l.lower())
        return (f"si {left} es {OP[lg][op]} {_num(r)}" if lg == "es"
                else f"if {left} is {OP[lg][op]} {_num(r)}")
    return (f"si: «{c}»" if lg == "es" else f"if: “{c}”")


def _constraint(c, lg):
    m = re.match(r"^FORBID_(\w+)$", c)
    if m:
        a = ACT[lg].get(m.group(1), m.group(1).lower())
        return f"prohibido {a}" if lg == "es" else f"forbidden to {a}"
    m = re.match(r"^OPTIONAL_(\w+)$", c)
    if m:
        a = ACT[lg].get(m.group(1), m.group(1).lower())
        return f"{a} solo es opcional, no obligatorio" if lg == "es" else f"{a} is only optional, not required"
    m = CMP.match(c)
    if m:
        l, op, r = m.groups()
        if l == "LIMIT" and op == "=":
            return f"límite de {r}" if lg == "es" else f"limit of {r}"
        if l == "APPROX":
            return f"aproximadamente {r}" if lg == "es" else f"approximately {r}"
        if l == "LANG":
            return f"idioma {r}" if lg == "es" else f"language {r}"
        return f"{l.lower()} {OP[lg][op]} {_num(r)}"
    return c


def to_natural(f: SemanticFrame, lang="es") -> str:
    lg = "en" if lang == "en" else "es"
    L = {"es": ["Solicitar", "datos", "entidades", "tiempo", "ubicación", "confianza", "referencias",
                "negaciones (operación mencionada, NO permitida)", "restricciones", "condiciones",
                "prioridad", "objetivo", "formato de salida"],
         "en": ["Request", "data", "entities", "time", "location", "confidence", "references",
                "negations (operation mentioned, NOT allowed)", "constraints", "conditions",
                "priority", "goal", "output format"]}[lg]
    parts = []
    if f.intent in ("CAPABILITY_QUERY", "CAPABILITY_RESPONSE"):
        return ("Consulta de capacidades" if f.intent == "CAPABILITY_QUERY" else "Capacidades: " + ", ".join(
            ACT[lg].get(a, a) for a in f.actions)) if lg == "es" else (
            "Capability query" if f.intent == "CAPABILITY_QUERY" else "Capabilities: " + ", ".join(
            ACT[lg].get(a, a) for a in f.actions))
    if f.actions:
        acts = [ACT[lg].get(a, a.lower()) for a in f.actions]
        joiner = " y " if lg == "es" else " and "
        parts.append(f"{L[0]}: " + (", ".join(acts[:-1]) + joiner + acts[-1] if len(acts) > 1 else acts[0]))
    if f.data: parts.append(f"{L[1]}: " + ", ".join(NOUN[lg].get(d, d.lower()) for d in f.data))
    if f.entities: parts.append(f"{L[2]}: " + ", ".join(NOUN[lg].get(d, d.lower()) for d in f.entities))
    if f.time: parts.append(f"{L[3]}: {_time(f.time, lg)}")
    if f.location: parts.append(f"{L[4]}: " + ", ".join(x.title() if len(x) > 2 else x for x in f.location))
    if f.confidence:
        m = re.match(r"^(>=|<=|>|<|=)(.*)$", f.confidence)
        parts.append(f"{L[5]}: {OP[lg][m.group(1)]} {_num(m.group(2))}" if m else f"{L[5]}: {f.confidence}")
    if f.references: parts.append(f"{L[6]}: " + ", ".join(f.references))
    if f.negations:
        parts.append(f"{L[7]}: " + ", ".join(
            (ACT[lg].get(n[3:], n[3:].lower()) if n.startswith("NO_") else n) for n in f.negations))
    if f.constraints: parts.append(f"{L[8]}: " + "; ".join(_constraint(c, lg) for c in f.constraints))
    if f.conditions: parts.append(f"{L[9]}: " + "; ".join(_cond(c, lg) for c in f.conditions))
    if f.priority: parts.append(f"{L[10]}: {f.priority}")
    if f.goal: parts.append(f"{L[11]}: {GOAL[lg].get(f.goal, f.goal.lower())}")
    if f.output: parts.append(f"{L[12]}: " + ", ".join(f.output))
    if not parts:
        return "Mensaje sin contenido semántico" if lg == "es" else "Message with no semantic content"
    return ". ".join(p[0].upper() + p[1:] for p in parts) + "."


def decode(aixl: str, lang="es") -> dict:
    f = parse(aixl)
    return {"frame": f, "natural": to_natural(f, lang)}
