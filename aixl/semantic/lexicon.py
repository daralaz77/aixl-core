"""Closed-class lexicon for the controlled domain (ES/EN/PT): function words and common instruction verbs.
Everything here is general instruction vocabulary; anything NOT here stays as an opaque content token (never dropped)."""
import re

ARTICLES = {"es": {"el", "la", "los", "las", "un", "una", "unos", "unas", "lo"},
            "pt": {"o", "a", "os", "as", "um", "uma", "uns", "umas"},
            "en": {"the", "a", "an"}}
FILLERS = {"por favor", "porfa", "porfavor", "please", "kindly", "pf", "ya", "por favor,", "favor", "pode", "aí", "ai", "de", "forma"}
FILLER_WORDS = {"porfa", "please", "kindly", "favor", "ya", "ai", "ahi", "tenga", "bien", "bem"}
COPULA = {"es": {"es", "esta", "estan", "son", "este", "estes", "sea", "ser", "estar", "estoy", "esten", "fue", "ha", "han", "he", "habia"},
          "pt": {"e", "esta", "estao", "sao", "seja", "ser", "estar", "foi", "tem", "tiver", "tiverem", "ficar", "ficou", "estiver", "estiverem"},
          "en": {"is", "are", "be", "been", "being", "was", "were", "has", "have", "had", "does", "do", "did", "will"}}

LANG_HINTS = {"es": {"el", "la", "los", "las", "de", "del", "que", "y", "en", "para", "con", "por", "al", "se", "una", "un", "si", "no", "es", "su", "le"},
              "pt": {"o", "os", "as", "do", "da", "dos", "das", "uma", "para", "com", "nao", "voce", "se", "em", "no", "na", "ao", "seu", "daqui", "feitos", "mae", "ele", "ela", "eles", "ainda", "tambem", "mais", "pelo", "pela", "aos", "ligue", "confirme", "mande", "envie", "um"},
              "en": {"the", "to", "of", "and", "is", "for", "with", "in", "on", "it", "not", "all", "if", "you", "your", "a", "an", "from", "be", "that"}}

# ---- negation / deontic ---------------------------------------------------------------------------------------------
NEG_TOKENS = {"no", "nunca", "jamas", "not", "never", "nao", "ni", "nem", "nadie", "nobody", "nothing", "nada", "neither", "nor"}
MODAL_MAY = {"puedes", "puede", "pueden", "podes", "pode", "podem", "podemos", "can", "may", "could", "permitido", "permitida", "allowed", "permitted", "permissao", "permitido."}
MODAL_MUST = {"debes", "debe", "deben", "debas", "deba", "deban", "debera", "deve", "devem", "deves", "must", "shall", "need", "needs", "necesitas", "necesita", "precisa", "precisam", "tienes", "tiene"}
MODAL_ADVISE = {"recomienda", "recomendado", "recomendable", "conviene", "should", "recommended", "aconselha", "recomenda", "deberias", "deberia", "convem"}
PROHIBITED = {"prohibido", "prohibida", "prohibe", "prohibidos", "forbidden", "prohibited", "proibido", "proibida", "vedado"}
AVOID = {"evita", "evite", "evitar", "evitas", "evitem", "avoid", "evitar", "evitem"}
NOT_TRUE = [("no", "es", "cierto", "que"), ("no", "es", "verdad", "que"), ("it", "is", "not", "true", "that"), ("nao", "e", "verdade", "que"), ("no", "es", "cierto"), ]
LITOTES = [("no", "dejes", "de"), ("no", "deje", "de"), ("nao", "deixe", "de"), ("do", "not", "fail", "to"), ("never", "fail", "to"), ("no", "dejen", "de")]
NOT_REQUIRED = [("no", "hace", "falta"), ("no", "necesitas"), ("no", "necesita"), ("nao", "precisa"), ("nao", "precisam"), ("no", "precisa"),
                ("do", "not", "need", "to"), ("need", "not"), ("no", "tienes", "que"), ("no", "tiene", "que")]

# ---- quantity ------------------------------------------------------------------------------------------------------
QTY_PHRASES = [  # (token tuple, mode); longest first
    (("al", "menos"), "at_least"), (("como", "minimo"), "at_least"), (("como", "minimo", "de"), "at_least"), (("un", "minimo", "de"), "at_least"),
    (("minimo",), "at_least"), (("at", "least"), "at_least"), (("no", "menos", "de"), "at_least"), (("pelo", "menos"), "at_least"), (("no", "minimo"), "at_least"),
    (("como", "maximo"), "at_most"), (("como", "mucho"), "at_most"), (("un", "maximo", "de"), "at_most"), (("maximo",), "at_most"), (("at", "most"), "at_most"),
    (("no", "mas", "de"), "at_most"), (("no", "more", "than"), "at_most"), (("up", "to"), "at_most"), (("no", "maximo"), "at_most"), (("a", "lo", "sumo"), "at_most"),
    (("exactamente",), "exact"), (("exactly",), "exact"), (("exatamente",), "exact"), (("justo",), "exact"),
    (("aproximadamente",), "approx"), (("approximately",), "approx"), (("roughly",), "approx"), (("about",), "approx"), (("around",), "approx"),
    (("alrededor", "de"), "approx"), (("unos",), "approx"), (("unas",), "approx"), (("cerca", "de"), "approx"), (("aproximadamente",), "approx"), (("mais", "ou", "menos"), "approx"),
    (("mas", "de"), "greater_than"), (("more", "than"), "greater_than"), (("over",), "greater_than"), (("mayor", "de"), "greater_than"), (("mayor", "que"), "greater_than"),
    (("mais", "de"), "greater_than"), (("acima", "de"), "greater_than"), (("mayores", "de"), "greater_than"),
    (("menos", "de"), "less_than"), (("menor", "de"), "less_than"), (("menores", "de"), "less_than"), (("menor", "que"), "less_than"), (("less", "than"), "less_than"),
    (("fewer", "than"), "less_than"), (("under",), "less_than"), (("below",), "less_than"), (("abaixo", "de"), "less_than"), (("menos", "que"), "less_than"),
]
QUANTIFIERS = {"todos": "all", "todas": "all", "todo": "all", "toda": "all", "all": "all", "every": "all", "everyone": "all", "everybody": "all", "todo": "all",
               "tudo": "all", "cada": "each", "each": "each",
               "algunos": "some", "algunas": "some", "some": "some", "alguns": "some", "algumas": "some", "varios": "some", "several": "some",
               "ningun": "none", "ninguno": "none", "ninguna": "none", "ningunos": "none", "none": "none", "nenhum": "none", "nenhuma": "none",
               "ninguem": "none", "nadie": "none", "nobody": "none",
               "cualquier": "any", "cualquiera": "any", "any": "any", "anyone": "any", "anybody": "any", "qualquer": "any", "alguien": "some"}
NUM_WORDS = {"cero": 0, "zero": 0, "uno": 1, "one": 1, "um": 1, "dos": 2, "two": 2, "dois": 2, "duas": 2, "tres": 3, "three": 3, "cuatro": 4, "four": 4, "quatro": 4,
             "cinco": 5, "five": 5, "seis": 6, "six": 6, "siete": 7, "seven": 7, "sete": 7, "ocho": 8, "eight": 8, "oito": 8, "nueve": 9, "nine": 9, "nove": 9,
             "diez": 10, "ten": 10, "dez": 10, "doce": 12, "twelve": 12, "doze": 12, "quince": 15, "fifteen": 15, "quinze": 15, "veinte": 20, "twenty": 20, "vinte": 20,
             "treinta": 30, "thirty": 30, "trinta": 30, "cuarenta": 40, "forty": 40, "cincuenta": 50, "fifty": 50, "sesenta": 60, "sixty": 60,
             "setenta": 70, "ochenta": 80, "noventa": 90, "cien": 100, "ciento": 100, "hundred": 100, "cem": 100, "doscientos": 200, "doscientas": 200,
             "trescientos": 300, "trescientas": 300, "quinientos": 500, "quinientas": 500, "mil": 1000, "thousand": 1000}
MULTIPLIERS = {"docena": 12, "docenas": 12, "dozen": 12, "dozens": 12, "duzia": 12, "duzias": 12, "hundred": 100, "thousand": 1000}
PAIR_WORDS = {("un", "par"), ("a", "couple"), ("um", "par"), ("a", "pair")}
UNITS = {"palabra": "words", "palabras": "words", "word": "words", "words": "words", "palavra": "words", "palavras": "words",
         "caracter": "characters", "caracteres": "characters", "character": "characters", "characters": "characters", "caractere": "characters", "caracteres": "characters",
         "dia": "days", "dias": "days", "day": "days", "days": "days", "hora": "hours", "horas": "hours", "hour": "hours", "hours": "hours",
         "minuto": "minutes", "minutos": "minutes", "minute": "minutes", "minutes": "minutes", "semana": "weeks", "semanas": "weeks", "week": "weeks", "weeks": "weeks",
         "mes": "months", "meses": "months", "month": "months", "months": "months", "ano": "years", "anos": "years", "year": "years", "years": "years",
         "dolar": "usd", "dolares": "usd", "dollar": "usd", "dollars": "usd", "usd": "usd", "euro": "eur", "euros": "eur", "eur": "eur",
         "mg": "mg", "kg": "kg", "kilo": "kg", "kilos": "kg", "g": "g", "gramo": "g", "gramos": "g", "gramas": "g",
         "parrafo": "paragraphs", "parrafos": "paragraphs", "paragraph": "paragraphs", "paragraphs": "paragraphs", "paragrafo": "paragraphs",
         "km": "km", "kilometro": "km", "kilometros": "km", "kilometer": "km", "kilometers": "km", "kilometre": "km", "quilometro": "km", "quilometros": "km",
         "milla": "mi", "millas": "mi", "mile": "mi", "miles": "mi", "milha": "mi", "milhas": "mi", "metro": "m", "metros": "m", "meter": "m", "meters": "m",
         "pagina": "pages", "paginas": "pages", "page": "pages", "pages": "pages", "linea": "lines", "lineas": "lines", "line": "lines", "lines": "lines"}
BIZ = {("dias", "habiles"), ("business", "days"), ("dias", "uteis"), ("dia", "habil"), ("business", "day")}

# ---- time ----------------------------------------------------------------------------------------------------------
DAYS = {"lunes": "mon", "monday": "mon", "segunda": "mon", "martes": "tue", "tuesday": "tue", "terca": "tue", "miercoles": "wed", "wednesday": "wed", "quarta": "wed",
        "jueves": "thu", "thursday": "thu", "quinta": "thu", "viernes": "fri", "friday": "fri", "sexta": "fri", "sabado": "sat", "saturday": "sat",
        "domingo": "sun", "sunday": "sun"}
DAYS_PT_FEIRA = {"segunda-feira": "mon", "terca-feira": "tue", "quarta-feira": "wed", "quinta-feira": "thu", "sexta-feira": "fri"}
RELDAYS = {"hoy": "today", "today": "today", "hoje": "today", "manana": "tomorrow", "tomorrow": "tomorrow", "amanha": "tomorrow", "ayer": "yesterday",
           "yesterday": "yesterday", "ontem": "yesterday", "ahora": "now", "now": "now", "agora": "now", "midnight": "T0000", "medianoche": "T0000", "meia-noite": "T0000"}
VAGUE_TIME = {"pronto": "soon", "soon": "soon", "luego": None, "later": "later", "despues": None, "eventually": "later", "asap": "soon", "breve": "soon"}
TIME_REL = [  # (tokens, rel)  — event-vs-value decision is made by the parser
    (("prior", "to"), "before"), (("previo", "al"), "before"), (("previo", "a"), "before"), (("previa", "al"), "before"), (("previa", "a"), "before"), (("previamente", "a"), "before"),
    (("posterior", "al"), "after"), (("posterior", "a"), "after"), (("subsequent", "to"), "after"), (("following",), "after"), (("tras",), "after"),
    (("antes", "de", "que"), "before"), (("antes", "del"), "before"), (("antes", "de"), "before"), (("before",), "before"), (("antes",), "before"),
    (("despues", "de", "que"), "after"), (("despues", "del"), "after"), (("despues", "de"), "after"), (("after",), "after"), (("depois", "de"), "after"), (("depois", "do"), "after"),
    (("hasta", "que"), "until"), (("hasta", "el"), "until"), (("hasta", "las"), "until"), (("hasta",), "until"), (("until",), "until"), (("till",), "until"), (("ate",), "until"),
    (("a", "mas", "tardar"), "until"), (("no", "later", "than"), "until"), (("by",), "until"), (("ate", "o"), "until"),
    (("desde", "que"), "since"), (("desde",), "since"), (("since",), "since"), (("from",), "since"), (("a", "partir", "de"), "since"),
    (("dentro", "de"), "within"), (("within",), "within"), (("en", "un", "plazo", "de"), "within"), (("daqui", "a"), "within"), (("in",), "within"),
    (("durante",), "during"), (("during",), "during"), (("durante", "o"), "during"),
]
RECUR_WORDS = {"diariamente": (1, "days"), "daily": (1, "days"), "nightly": (1, "night"), "weekly": (1, "weeks"), "semanalmente": (1, "weeks"), "monthly": (1, "months"),
               "mensualmente": (1, "months"), "yearly": (1, "years"), "annually": (1, "years"), "anualmente": (1, "years"), "hourly": (1, "hours"), "siempre": "always",
               "always": "always", "sempre": "always"}
SPECIAL_PERIODS = {"semestre": (6, "months"), "semester": (6, "months"), "trimestre": (3, "months"), "quarter": (3, "months"), "bimestre": (2, "months"),
                   "quincena": (2, "weeks"), "fortnight": (2, "weeks"), "cuatrimestre": (4, "months")}
RECUR_ADJ = {"semanal": (1, "weeks"), "mensual": (1, "months"), "anual": (1, "years"), "diario": (1, "days"), "diaria": (1, "days"), "semestral": (6, "months"),
             "trimestral": (3, "months"), "bimestral": (2, "months"), "quincenal": (2, "weeks"), "bimensual": (2, "months"), "cuatrimestral": (4, "months")}
RECUR_ADJ_CANDS = {"bimensual": (0.5, "months")}      # 'bimensual' = every two months OR twice a month
RECUR_CUE = {"forma", "manera", "periodicidad", "frecuencia", "ritmo", "basis"}
EXEMPT_WORDS = {"exempt", "exento", "exenta", "exentos", "exentas", "isento", "isenta", "isentos", "isentas", "exempted", "exceptuado", "exceptuados"}
PHASE_PHRASES = [(("al", "final", "de"), "end"), (("a", "finales", "de"), "end"), (("ao", "final", "de"), "end"), (("no", "final", "do"), "end"), (("no", "fim", "de"), "end"),
                 (("al", "inicio", "de"), "start"), (("al", "principio", "de"), "start"), (("a", "principios", "de"), "start"), (("al", "comienzo", "de"), "start"),
                 (("at", "the", "end", "of"), "end"), (("at", "the", "start", "of"), "start"), (("at", "the", "beginning", "of"), "start"), (("by", "the", "end", "of"), "end"),
                 (("en", "la", "mitad", "de"), "middle"), (("in", "the", "middle", "of"), "middle")]
RECUR_KEY = {"noche": "night", "noite": "night", "night": "night", "nights": "night"}
DEMONSTRATIVES = {"proprio", "propria", "mismo", "misma", "mesmo", "mesma", "same", "dicho", "dicha", "referido", "this", "that", "these", "those", "este", "esta", "estos", "estas", "ese", "esa", "esos", "esas", "esse", "essa", "aquel", "aquella"}
FRACTION_WORDS = {"media", "medio", "mitad", "half", "quarter", "tercio", "metade"}
RECUR_UNITS = set(DAYS) | {"noche", "night", "dia", "day", "hora", "hour", "semana", "week", "mes", "month", "ano", "year", "mañana", "tarde", "manana", "noite", "dias", "horas"}
ORDINALS = {"primer": 1, "primero": 1, "primera": 1, "primeiro": 1, "primeira": 1, "first": 1, "segundo": 2, "segunda": 2, "second": 2, "tercer": 3, "tercero": 3,
            "tercera": 3, "terceiro": 3, "third": 3, "cuarto": 4, "fourth": 4, "quarto": 4, "quinto": 5, "fifth": 5,
            "ultimo": "last", "ultima": "last", "ultimos": "last", "last": "last", "latest": "most_recent", "newest": "most_recent", "ultimo-": "last",
            "reciente": "most_recent", "recientes": "most_recent", "recent": "most_recent", "recente": "most_recent",
            "antiguo": "oldest", "oldest": "oldest", "earliest": "oldest", "antigo": "oldest",
            "anterior": "previous", "previous": "previous", "siguiente": "next_item", "seguinte": "next_item"}
NEXT_WORDS = {"proximo", "proxima", "next", "proximos", "seguinte", "coming", "upcoming"}

# ---- conditions / exceptions / only / sequence -----------------------------------------------------------------------
COND_NEC = [("solo", "si"), ("solo", "cuando"), ("unicamente", "si"), ("only", "if"), ("only", "when"), ("apenas", "se"), ("somente", "se"), ("so", "se"), ("solamente", "si")]
COND_UNLESS = [("a", "menos", "que"), ("unless",), ("salvo", "que"), ("a", "no", "ser", "que"), ("a", "menos", "de", "que"), ("exceto", "se"), ("a", "menos", "que")]
COND_SUFF = [("provided", "that"), ("provided",), ("providing",), ("contanto", "que"), ("caso",), ("en", "caso", "de", "que"), ("en", "caso", "de"), ("siempre", "que"), ("cada", "vez", "que"), ("as", "long", "as"), ("in", "case"), ("em", "caso", "de"),
             ("si",), ("if",), ("when",), ("cuando",), ("whenever",), ("se",), ("quando",), ("once",), ("una", "vez", "que")]
EXCEPT_WORDS = [("exceptuando",), ("a", "excepcion", "de"), ("con", "excepcion", "de"), ("excepto",), ("salvo",), ("menos",), ("except", "for"), ("except",), ("other", "than"),
                ("exceto",), ("a", "excecao", "de"), ("excluding",), ("excluyendo",), ("sin", "contar"), ("apart", "from"), ("aside", "from")]
WITHOUT_WORDS = {"sin": "without", "without": "without", "sem": "without"}
ONLY_WORDS = {"solo", "solamente", "unicamente", "only", "just", "apenas", "somente", "soh"}
SEQ_ADVERBS = {"luego", "despues", "entonces", "then", "depois", "entao", "afterwards", "afterward", "later"}
FIRST_ADVERBS = {"primero", "first", "primeiro", "firstly"}
CONJ = {"y", "e", "and", "ou", "o", "u", "or", "ni", "nem"}
CONJ_AND = {"y", "e", "and"}
CONJ_OR = {"o", "u", "or", "ou"}
PRONOUN_PERSON = {"el", "ella", "ellos", "ellas", "he", "she", "they", "ele", "ela", "eles", "elas", "su", "sus", "his", "her", "their", "seu", "sua", "seus", "suas", "its"}
PRONOUN_OBJECT = {"lo", "la", "los", "las", "it", "them", "him", "her", "o", "a", "os", "as"}
ROLES = {"tecnico", "gerente", "jefe", "director", "cliente", "usuario", "empleado", "manager", "client", "user", "employee", "technician", "boss", "supplier", "proveedor",
         "aluno", "mae", "madre", "mother", "student", "alumno", "responsavel", "equipo", "team", "equipe", "administrador", "admin", "propietario", "dueno", "owner"}

# ---- verbs (stem -> canonical action). Matching: stem + inflection suffix (+ clitics). GENERIC actions never prove inequality.
ACTIONS = {
    "DELETE": ["borr", "elimin", "delet", "remov", "remuev", "apag", "exclu", "exclui", "descart", "purg", "quit"],
    "SEND": ["envi", "mand", "send", "remit", "despach", "pas", "entreg", "enve"],
    "SUMMARIZE": ["resum", "summar", "sintetiz", "condens"],
    "USE": ["us", "utiliz", "use", "emple"],
    "SELECT": ["seleccion", "select", "escolh", "elij", "eleg", "choos", "pick"],
    "REQUEST": ["solicit", "request", "pid", "pedi", "peca", "ask"],
    "PUBLISH": ["public", "publiqu", "publish", "post"],
    "REVIEW": ["revis", "review", "examin", "check", "verific", "audit", "inspec"],
    "APPROVE": ["aprueb", "aprob", "apruebe", "approv", "aprov", "autoriz", "authoriz"],
    "REJECT": ["rechaz", "reject", "deneg", "deny", "reprov"],
    "CREATE": ["cre", "gener", "generat", "creat", "produc", "elabor", "redact", "escrib", "write", "draft", "compon", "redig"],
    "COPY": ["copi", "copy", "duplic"],
    "OPEN": ["abr", "open", "abra"],
    "CLOSE": ["cierr", "cerr", "close", "feche", "fech", "cance"],
    "COMPARE": ["compar"],
    "TRANSLATE": ["traduc", "traduz", "translat"],
    "LIST": ["list", "enumer", "lista"],
    "CALL": ["llam", "call", "ligu", "telefon", "phon"],
    "NOTIFY": ["notific", "notif", "avis", "inform", "advert", "alert", "dile", "dig", "tell", "diga", "dime"],
    "BUY": ["compr", "buy", "purchas", "adquir", "adquier"],
    "PAY": ["pag", "pay", "abon", "cancel", "liquid"],
    "TRANSFER": ["transfier", "transfer", "transfir"],
    "RESTART": ["reinici", "restart", "reboot", "reinic", "reiniciar"],
    "DEPLOY": ["despleg", "deploy", "implement", "lanz", "desplieg", "desplegu", "implant"],
    "BACKUP": ["respald", "backup", "back", "salvag", "copi"],
    "UPDATE": ["actualiz", "updat", "atualiz", "upgrad", "modific"],
    "CLEAR": ["limpi", "clear", "clean", "vaci", "vazi", "purg", "borrar"],
    "SCHEDULE": ["program", "schedul", "agend", "calend"],
    "RUN": ["ejecut", "run", "corr", "execut", "lanc", "launch"],
    "SHARE": ["compart", "share", "comparti"],
    "GRANT": ["conced", "grant", "otorg", "dale", "dar", "give", "da", "de", "brind", "dei", "conceda"],
    "REVOKE": ["revoc", "revok", "retir", "withdraw", "cancel"],
    "BLOCK": ["bloque", "block", "bloqu", "suspend", "suspende"],
    "ARCHIVE": ["archiv", "archive", "arquiv", "guard"],
    "EXPORT": ["export", "exporta"],
    "REGISTER": ["regist", "record", "anot", "log"],
    "CORRECT": ["corrig", "correct", "fix", "arregl", "repar"],
    "RESTORE": ["restaur", "restor", "recuper", "revert", "revier", "reverta", "volv"],
    "ESCALATE": ["escal", "escalate", "eleva"],
    "ADD": ["agreg", "add", "anad", "adicion", "incluy", "inclu", "includ", "insert"],
    "MOVE": ["mov", "mueve", "move", "traslad", "mude"],
    "RENAME": ["renombr", "rename", "renome"],
    "CONVERT": ["convier", "convert", "convirt", "conver"],
    "COMPUTE": ["calcul", "comput", "compute"],
    "READ": ["lee", "leer", "lea", "leas", "leen", "read", "leia", "leia"],
    "WRITE": ["escrib"],
    "ANSWER": ["respond", "repl", "answer", "reply", "conest", "responda"],
    "POSTPONE": ["pospon", "posp", "retras", "delay", "postpone", "aplaz", "adi"],
    "CONFIRM": ["confirm"],
    "CANCEL": ["cancel", "anul"],
    "STAY": ["quedat", "quede", "queda", "stay", "fique"],
    "ACCESS": ["acced", "access"],
    "SIGN": ["firm", "sign", "assin"],
    "DISCOVER": ["busc", "search", "find", "encuentr", "localiz", "procur"],
    "APPLY": ["aplic", "apply", "aplique"],
    "EDIT": ["edit", "editar"],
    "GET": ["traer", "trae", "tr", "bring", "get", "grab", "obt", "consig", "obtén"],
    "TAKE": ["tom", "take", "saca", "remueve"],
    "MAKE": ["hac", "haz", "hag", "hace", "make", "fa", "faca", "fazer", "faz", "do", "realiz", "efectu"],
    "ENSURE": ["asegur", "ensur", "garant", "certif"],
    "VALIDATE": ["valid"],
    "STORE": ["grab", "grave", "store", "almacen", "salv", "sav", "guard"],
    "PRINT": ["imprim", "print"],
    "CHARGE": ["cobr", "charg", "factur", "invoic"],
    "KEEP": ["mant", "keep", "conserv", "retien", "retain", "preserv"],
    "SHOW": ["muestr", "most", "show", "display", "exhib", "ensen", "mostr"],
    "HIDE": ["ocult", "hide", "esconde", "esconder"],
    "SORT": ["orden", "sort", "classific", "clasific", "ordene"],
    "FILTER": ["filtr", "filter"],
    "COUNT": ["cont", "count"],
    "INSTALL": ["instal", "install"],
    "DOWNLOAD": ["descarg", "download", "baix"],
    "UPLOAD": ["sub", "upload", "carg", "load", "envi"],
    "IMPORT": ["import"],
    "ENABLE": ["activ", "enable", "habilit", "ative"],
    "DISABLE": ["desactiv", "disable", "deshabilit", "desabilit"],
    "CHANGE": ["cambi", "chang", "mud", "alter"],
    "REPLACE": ["reemplaz", "replac", "substitu", "sustitu"],
    "MERGE": ["fusion", "merg", "uni", "junt", "combin", "combine"],
    "SPLIT": ["divid", "split", "separ"],
    "ASSIGN": ["asign", "assign", "atribu"],
    "RESERVE": ["reserv", "book"],
    "RETURN": ["devuelv", "devolv", "return", "reembols", "refund", "reembolse"],
    "PAUSE": ["paus", "pause", "detien", "deten", "stop", "paralis", "interromp"],
    "START": ["inici", "empie", "empez", "start", "comienz", "comenz", "comec", "begin"],
    "FINISH": ["termin", "finish", "conclu", "finaliz", "complet"],
    "PASTE": ["peg", "paste", "cole"],
    "CUT": ["cort", "cut"],
    "TAG": ["etiquet", "tag", "marc", "mark"],
    "TEST": ["prueb", "test", "probar"],
}
GENERIC_ACTIONS = {"MAKE", "GET", "TAKE", "GRANT", "USE", "DO", "CLEAR"}
# stems that are ambiguous with very common non-verb words: require an exact imperative-looking form instead of stem+suffix
EXACT_ONLY = {"da", "de", "le", "us", "pas", "fa", "tr", "quit", "cre", "dar", "don", "dig", "back", "pid", "log", "cance", "ask", "mov", "pick", "do", "adi", "sav", "post"}

SYNONYMS = {  # content-noun classes (folded, singular). Deliberately small: a missing synonym costs INCONCLUSIVE, never a false EQUIVALENT.
    "informe": "report", "reporte": "report", "report": "report", "relatorio": "report",
    "archivo": "file", "file": "file", "arquivo": "file", "fichero": "file",
    "correo": "email", "email": "email", "mail": "email", "e-mail": "email", "emailes": "email",
    "factura": "invoice", "invoice": "invoice", "fatura": "invoice",
    "contrato": "contract", "contract": "contract", "documento": "document", "document": "document",
    "cliente": "client", "client": "client", "customer": "client", "cliente": "client",
    "equipo": "team", "team": "team", "equipe": "team",
    "contrasena": "password", "password": "password", "senha": "password", "clave": "password",
    "servidor": "server", "server": "server", "cache": "cache", "pedido": "order", "order": "order", "pedidos": "order",
    "viernes": "fri", "lunes": "mon",
    "ventas": "sales", "sales": "sales", "vendas": "sales", "venta": "sales",
    "base": "base", "datos": "data", "data": "data", "dados": "data",
    "permiso": "permission", "permission": "permission", "permissao": "permission", "permisos": "permission",
    "carpeta": "folder", "folder": "folder", "pasta": "folder",
    "registro": "record", "record": "record", "registros": "record", "log": "log", "logs": "log",
    "empleado": "employee", "employee": "employee", "funcionario": "employee",
    "reembolso": "refund", "refund": "refund", "pago": "payment", "payment": "payment", "pagamento": "payment",
    "errores": "error", "error": "error", "erro": "error", "erros": "error",
    "informes": "report", "reportes": "report",
}
PREP_MAP = {"es": {"a": "TO", "al": "TO", "para": "FOR", "en": "IN", "de": "OF", "del": "OF", "con": "WITH", "por": "BY", "sobre": "ON", "desde": "FROM"},
            "pt": {"para": "TO", "a": "TO", "ao": "TO", "em": "IN", "no": "IN", "na": "IN", "de": "OF", "do": "OF", "da": "OF", "dos": "OF", "das": "OF", "com": "WITH", "por": "BY", "sobre": "ON"},
            "en": {"to": "TO", "for": "FOR", "in": "IN", "on": "ON", "of": "OF", "with": "WITH", "by": "BY", "from": "FROM", "at": "AT"}}
PREPS_ALL = set().union(*[set(v) for v in PREP_MAP.values()]) | {"como", "as", "like", "que", "que"}

_SUFFIX = r"(?:a|e|o|as|es|an|en|ar|er|ir|ad|ed|id|ado|ido|ando|iendo|ing|ed|s|ando|ed|em|ou|ei|ava|aba|emos|amos|ais|eis|ando|ei|ia|ie|ue|ua|ue|eu|ei)?"
_CLITIC = r"(?:(?:me|te|le|les|se|lo|la|los|las|nos)){0,2}"


def verb_action(token: str) -> str | None:
    """Canonical action for a folded token (imperative / infinitive / participle, with clitics) or None."""
    for act, stems in ACTIONS.items():
        for st in stems:
            if st in EXACT_ONLY:
                if re.fullmatch(re.escape(st) + r"(?:a|e|as|es|an|en|ar|er|ir)(?:me|te|le|les|se|lo|la|los|las){0,2}", token) and token != st and len(token) > len(st):
                    return act
                continue
            if re.fullmatch(re.escape(st) + _SUFFIX + _CLITIC, token):
                if len(token) >= 3:
                    return act
    return None


def clitics_of(token: str) -> list:
    m = re.fullmatch(r"(.+?)((?:me|te|le|les|se|lo|la|los|las|nos){1,2})", token)
    if m and verb_action(m.group(1)) and verb_action(token):
        cl = re.findall(r"me|te|les|le|se|los|las|lo|la|nos", m.group(2))
        return cl
    return []

NOUN_ONLY = {"informe", "informes", "pago", "pagos", "cierre", "respaldo", "resumen", "resumenes", "registro", "registros", "cambio", "cambios", "pedido", "pedidos",
             "entrega", "envio", "aviso", "avisos", "compra", "compras", "venta", "ventas", "permiso", "permisos", "acuerdo", "error", "errores", "borrador", "firma",
             "cuenta", "cuentas", "copia", "copias", "lista", "listas", "reporte", "reportes", "pasta", "banco", "pruebas", "prueba", "test", "tests", "pass", "report",
             "reports", "post", "posts", "log", "logs", "record", "records", "order", "orders", "check", "backup", "backups", "update", "updates", "access", "answer",
             "mail", "reply", "copy", "list", "lists", "sign", "block", "call", "calls", "run", "runs", "fix", "write", "read", "make", "pick", "do", "back", "store",
             "contas", "conta", "relatorio", "relatorios", "dados", "traduccion", "trabajo", "rechazo", "revision", "aprobacion", "respuesta", "documento", "documentos"}
SE_TOKENS = {"se"}
EN_IMPERATIVE_NOUNS = {"call", "check", "run", "block", "fix", "write", "read", "make", "pick", "back", "store", "sign", "list", "copy", "reply", "answer", "update", "access", "post", "order", "mail", "log", "record"}   # English words that are nouns AND imperative verbs: a verb right after 'and'/','
