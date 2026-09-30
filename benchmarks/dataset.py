"""200-case DEV benchmark (spec §30). Hand-authored, reproducible (no randomness), SAME AUTHOR as the code:
this is a DEMO/dev set, not independent evidence (see BENCHMARK.md)."""
import json, os
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

EQ = [  # (a, b) equivalent paraphrases, mixed ES/EN/PT
 ("Analiza las ventas del primer trimestre de 2026.", "Examina las ventas de Q1 2026."), ("Analyze sales.", "Analiza las ventas."),
 ("Estudia los datos de clientes.", "Analiza los datos de los clientes."), ("Busca los eventos de hoy.", "Localiza los eventos de hoy."),
 ("Compara las ventas de Q1 2026 con las de Q2 2026.", "Compare Q1 2026 sales with Q2 2026 sales."), ("Traduce el documento al inglés.", "Translate the document into English."),
 ("Genera un informe en JSON.", "Crea un reporte en formato JSON."), ("Calcula el total de ventas de 2025.", "Compute total sales for 2025."),
 ("Encuentra anomalías en las ventas.", "Detecta anomalías en las ventas."), ("Verifica los datos de usuarios.", "Valida los datos de los usuarios."),
 ("Send the report today.", "Envía el reporte hoy."), ("Get the customers dataset.", "Retrieve the customers dataset."),
 ("Analise as vendas do primeiro trimestre de 2026.", "Analiza las ventas de Q1 2026."), ("Actualiza el producto #5.", "Modifica el producto #5."),
 ("Executa o modelo #3.", "Ejecuta el modelo #3."), ("Analyze customers from last month.", "Analiza los clientes del mes pasado."),
 ("Resume el reporte #12.", "Summarize report #12."), ("Search the audio dataset.", "Busca en el dataset de audio."),
 ("Analyze the images.", "Examine the images."), ("Genera un CSV de los clientes.", "Generate a CSV of the customers."),
 ("Compara el dataset #77 con el dataset #81.", "Compare dataset #77 with dataset #81."), ("Traduce el reporte al francés.", "Traduza o relatório para o francês."),
 ("Analiza las ventas de marzo de 2026.", "Analyze sales for 2026-03."), ("Calcula las ventas de 2024.", "Calculate the 2024 sales."),
 ("Analiza los videos de esta semana.", "Analyze this week's videos."), ("Crea un documento sobre el producto #9.", "Write a document about product #9."),
 ("Analiza las ventas.", "Examina las ventas."), ("Encuentra los eventos del 2026-03-15.", "Find the events of 2026-03-15."),
 ("Verifica el resultado.", "Check the result."), ("Envía el resultado a la empresa Acme.", "Send the result to the company Acme."),
]
DIFF = [  # different action / target / output / language
 ("Analiza las ventas.", "Elimina las ventas."), ("Analiza las ventas.", "Analiza los clientes."), ("Genera un informe en PDF.", "Genera un informe en JSON."),
 ("Traduce el documento al inglés.", "Traduce el documento al francés."), ("Compara las ventas.", "Calcula las ventas."), ("Busca eventos.", "Elimina eventos."),
 ("Analiza los usuarios.", "Analiza las imágenes."), ("Genera un CSV.", "Genera un PDF."), ("Envía el reporte.", "Elimina el reporte."),
 ("Analiza el audio.", "Analiza el video."), ("Translate the report.", "Summarize the report."), ("Get the customers.", "Delete the customers."),
 ("Check the dataset.", "Update the dataset."), ("Analiza las ventas.", "Analiza el total de ventas."), ("Genera un reporte.", "Traduce un reporte."),
 ("Ejecuta el modelo #3.", "Actualiza el modelo #3."), ("Find anomalies.", "Find events."), ("Envía el resultado.", "Envía el reporte."),
 ("Analiza los clientes.", "Compara los clientes."), ("Genera un documento.", "Genera un dataset."), ("Analyze the sales report.", "Analyze the customers report."),
 ("Habilita la alerta.", "Deshabilita la alerta."), ("Incluye los usuarios.", "Excluye los usuarios."), ("Translate the document to Spanish.", "Translate the document to Portuguese."),
 ("Retrieve the images.", "Retrieve the audio."), ("Analiza las ventas en tabla.", "Analiza las ventas en CSV."), ("Calcula las ventas.", "Calcula los clientes."),
 ("Verifica los usuarios.", "Elimina los usuarios."), ("Busca personas.", "Busca empresas."), ("Genera un informe de ventas.", "Genera un informe de clientes."),
]
NEG_NEQ = [("Elimina el reporte.", "No elimines el reporte."), ("Delete the report.", "Do not delete the report."), ("Envía el resultado.", "No envíes el resultado."),
 ("Send the file to Ana.", "Never send the file to Ana."), ("Ejecuta el modelo.", "Nunca ejecutes el modelo."), ("Update the record.", "Do not update the record."),
 ("Traduce el documento.", "No traduzcas el documento."), ("Analyze the sales.", "Don't analyze the sales."), ("Activa la alerta.", "No actives la alerta."),
 ("Include the images.", "Do not include the images."), ("Elimina los usuarios.", "Prohíbe eliminar los usuarios."), ("Permite eliminar el reporte.", "Prohíbe eliminar el reporte."),
 ("Allow deleting the report.", "Forbid deleting the report."), ("Genera el informe.", "No generes el informe."), ("Compara los datasets.", "No compares los datasets."),
 ("Borra los archivos temporales #4.", "No borres los archivos temporales #4."), ("Run the model.", "Never run the model."), ("Translate the report.", "Do not translate the report."),
 ("Envía el reporte.", "Está prohibido enviar el reporte."), ("Delete users.", "Deleting users is forbidden.")]
NEG_EQ = [("No elimines el reporte.", "Nunca elimines el reporte."), ("Do not delete the report.", "Never delete the report."), ("No envíes el resultado.", "Prohíbe enviar el resultado."),
 ("Don't send the file.", "Sending the file is forbidden."), ("No ejecutes el modelo.", "No corras el modelo."), ("Do not run the model.", "Never execute the model."),
 ("No traduzcas el documento.", "Está prohibido traducir el documento."), ("Do not include the images.", "Exclude the images."), ("Excluye los usuarios.", "No incluyas los usuarios."),
 ("Não exclua os registros.", "Nunca remova os registros.")]
QTY_NEQ = [("Analiza 100 registros.", "Analiza 1000 registros."), ("Analyze 10 records.", "Analyze 100 records."), ("Procesa 50 usuarios.", "Procesa 500 usuarios."),
 ("Analiza 100 registros.", "Analiza 200 registros."), ("Genera 5 informes.", "Genera 6 informes."), ("Analyze 1,000 users.", "Analyze 10,000 users."),
 ("Retrieve 20 customers.", "Retrieve 25 customers."), ("Analiza 100 clientes.", "Analiza 100 usuarios."), ("Get 3 documents.", "Get 30 documents."),
 ("Procesa 1.000 registros.", "Procesa 100 registros."), ("Analyze 100 records.", "Analyze 100 users."), ("Traduce 2 documentos.", "Traduce 3 documentos.")]
QTY_EQ = [("Analiza 1.000 registros.", "Analiza 1000 registros."), ("Analyze 1,000 records.", "Analyze 1000 records."), ("Analiza 100 registros.", "Analyze 100 records."),
 ("Procesa 500 usuarios.", "Process 500 users."), ("Analiza 100 registros.", "Analiza cien registros."), ("Analyze 20 customers.", "Analiza 20 clientes."),
 ("Get five documents.", "Get 5 documents."), ("Analiza 1.000 usuarios.", "Analyze 1,000 users.")]
DATE_EQ = [("Analiza las ventas de Q1 2026.", "Analiza las ventas del primer trimestre de 2026."), ("Analyze Q1 2026 sales.", "Analyze first quarter of 2026 sales."),
 ("Ventas del segundo trimestre de 2026.", "Ventas de Q2-2026."), ("Analiza 2026 Q3.", "Analiza Q3 2026."), ("Analiza marzo de 2026.", "Analiza 2026-03."),
 ("Analyze sales for January 2026.", "Analiza las ventas de enero de 2026."), ("Analiza las ventas de ayer.", "Analyze yesterday's sales."),
 ("Analiza el 2026-03-15.", "Analyze 2026-03-15."), ("Analyze the year 2025.", "Analiza el año 2025."), ("Analiza el cuarto trimestre de 2025.", "Analyze Q4 2025.")]
DATE_NEQ = [("Analiza las ventas de Q1 2026.", "Analiza las ventas de Q2 2026."), ("Analyze sales for 2025.", "Analyze sales for 2026."), ("Analiza marzo de 2026.", "Analiza abril de 2026."),
 ("Analiza las ventas de hoy.", "Analiza las ventas de ayer."), ("Analyze Q3 2026.", "Analyze Q3 2025."), ("Analiza el 2026-03-15.", "Analiza el 2026-03-16."),
 ("Ventas de esta semana.", "Ventas de la semana pasada."), ("Analyze January 2026.", "Analyze January 2025."), ("Analiza Q4 2025.", "Analiza Q1 2026."), ("Analyze last month.", "Analyze this month.")]
CON_PAIRS = [
 (("Analiza las ventas con confianza >= 0.90.", "Analiza las ventas con confianza >= 0.70."), False), (("Analyze sales with confidence at least 0.9.", "Analyze sales with confidence at least 0.7."), False),
 (("Genera un informe en PDF.", "Genera un informe en JSON."), False), (("Get the top 10 customers.", "Get the top 100 customers."), False),
 (("Traduce al inglés.", "Traduce al francés."), False), (("Analiza las ventas, máximo 20.", "Analiza las ventas, máximo 200."), False),
 (("Analiza las ventas con prioridad alta.", "Analiza las ventas con prioridad urgente."), False), (("Analiza las ventas con confianza > 0.90.", "Analiza las ventas con confianza >= 0.90."), False),
 (("Get customers as CSV.", "Get customers as table."), False), (("Analiza los últimos 100 registros.", "Analiza los primeros 100 registros."), False),
 (("Analiza las ventas con confianza >= 0.90.", "Analiza las ventas con confianza mayor o igual a 0.90."), True), (("Analyze sales with confidence >= 0.9.", "Analyze sales with at least 0.90 confidence."), True),
 (("Genera un informe en JSON.", "Crea un reporte en formato JSON."), True), (("Get the top 10 customers.", "Fetch the 10 best customers."), True),
 (("Traduce al inglés.", "Translate into English."), True), (("Analiza las ventas, máximo 20.", "Analyze sales, at most 20."), True),
 (("Genera un reporte en tabla.", "Generate a report as a table."), True), (("Analiza las ventas con prioridad alta.", "Analyze sales with high priority."), True),
 (("Get customers, no more than 5.", "Get customers, max 5."), True), (("Analiza con confianza >= 0.90.", "Analiza con confianza >= 0.9."), True)]
COND_PAIRS = [
 (("Analiza las ventas si existen más de 100 registros.", "Analiza las ventas."), False), (("Analyze sales if there are more than 100 records.", "Analyze sales if there are more than 1000 records."), False),
 (("Analiza las ventas si hay anomalías.", "Analiza las ventas."), False), (("Si la confianza es menor a 0.80, verifica el resultado.", "Si la confianza es menor a 0.50, verifica el resultado."), False),
 (("Check the result if confidence is below 0.80.", "Check the result."), False), (("Elimina el reporte si hay más de 10 anomalías.", "Elimina el reporte si hay más de 100 anomalías."), False),
 (("Send the alert if there are anomalies.", "Send the alert."), False), (("Analiza si existen más de 100 registros.", "Analiza si existen menos de 100 registros."), False),
 (("Verifica que el documento no contenga anomalías.", "Verifica que el documento contenga anomalías."), False), (("Send the report if there are more than 5 events.", "Send the report if there are at least 5 events."), False),
 (("Analiza las ventas si existen más de 100 registros.", "Analyze sales if there are more than 100 records."), True), (("Analiza las ventas si hay anomalías.", "Analyze sales if there are anomalies."), True),
 (("Si la confianza es menor a 0.80, verifica el resultado.", "Verifica el resultado si la confianza es menor a 0.80."), True), (("Check the result if confidence is below 0.80.", "If confidence is under 0.80, check the result."), True),
 (("Envía la alerta si existen anomalías.", "Envía la alerta cuando haya anomalías."), True), (("Send the report if there are more than 5 events.", "Send the report whenever there are more than 5 events."), True),
 (("Si hay más de 100 registros, no ejecutes el proceso.", "No ejecutes el proceso cuando haya más de 100 registros."), True), (("Analiza si existe una anomalía.", "Analiza si se detecta una anomalía."), True),
 (("Verify if the report contains anomalies.", "Check whether the report has anomalies."), True), (("Elimina el reporte si hay más de 10 anomalías.", "Delete the report if there are more than 10 anomalies."), True)]
REF_PAIRS = [
 (("Compara el dataset #77 con el dataset #81.", "Compara el dataset #77 con el dataset #82."), False), (("Actualiza el producto #5.", "Actualiza el producto #6."), False),
 (("Delete report #4.", "Delete report #5."), False), (("Analiza el documento #12.", "Analiza el documento #21."), False), (("Send report #7 to Ana.", "Send report #7 to Beto."), False),
 (("Compare dataset #1 with #2.", "Compare dataset #1 with #3."), False), (("Traduce el documento #8.", "Traduce el documento."), False), (("Analiza el reporte #3 y el #4.", "Analiza el reporte #3."), False),
 (("Ejecuta el modelo #10.", "Ejecuta el modelo #100."), False), (("Get user #45.", "Get user #46."), False), (("Envía el informe a la empresa Acme.", "Envía el informe a la empresa Beta."), False),
 (("Check result #9.", "Check result #90."), False),
 (("Compara el dataset #77 con el dataset #81.", "Compare dataset #77 with dataset #81."), True), (("Actualiza el producto #5.", "Update product #5."), True),
 (("Delete report #4.", "Elimina el reporte #4."), True), (("Analiza el documento #12.", "Analyze document #12."), True), (("Send report #7 to Ana.", "Envía el reporte #7 a Ana."), True),
 (("Get user #45.", "Obtén el usuario #45."), True), (("Ejecuta el modelo #10.", "Run model #10."), True), (("Check result #9.", "Verifica el resultado #9."), True)]
AMB = [("Analiza los datos recientes.", True), ("Elimínalo.", True), ("Fix it.", True), ("Borra todo.", True), ("Compara ambos.", True), ("Elimina el archivo.", True),
       ("Analiza el informe de marzo.", True), ("Delete the old ones.", True), ("Send her the file.", True), ("Analiza aquello.", True),
       ("Analiza las ventas del primer trimestre de 2026 en JSON.", False), ("Elimina el reporte #81.", False), ("Compara el dataset #77 con el dataset #81.", False),
       ("Analyze the sales of Q1 2026.", False), ("No elimines el reporte #4.", False)]
CONTRA = [("Elimina el reporte #4.", "No elimines el reporte #4.", True), ("Activa la alerta.", "Desactiva la alerta.", True), ("Permite eliminar el reporte.", "Prohíbe eliminar el reporte.", True),
          ("Incluye los usuarios en el reporte.", "Excluye los usuarios del reporte.", True), ("Haz público el reporte #3.", "Haz privado el reporte #3.", True),
          ("Analiza los reportes antes de 2026-03-15.", "Analiza los reportes después de 2026-03-15.", True), ("Send the report.", "Do not send the report.", True),
          ("Enable the alert.", "Disable the alert.", True), ("Allow deleting the report.", "Forbid deleting the report.", True),
          ("Analiza las ventas de Q1 2026.", "Analiza las ventas de Q2 2026.", False), ("Elimina el reporte #4.", "No elimines el reporte #5.", False),
          ("Genera un informe en PDF.", "Genera un informe en JSON.", False), ("Analiza las ventas.", "Analiza las ventas de Q1 2026.", False),
          ("Include customers in the report.", "Exclude users from the report.", False), ("No elimines el reporte.", "Prohíbe eliminar el reporte.", False)]


def build():
    cases = []
    def add(cat, prefix, a, b, eq, **kw):
        cases.append({"id": f"{prefix}{sum(1 for c in cases if c['id'].startswith(prefix)) + 1:03d}", "input_a": a, "input_b": b, "expected_equivalent": eq,
                      "expected_category": cat, **kw})
    for a, b in EQ: add("EQUIVALENCE", "EQ", a, b, True)
    for a, b in DIFF: add("DIFFERENCE", "DF", a, b, False)
    for a, b in NEG_NEQ: add("NEGATION", "NG", a, b, False, expected_critical=True)
    for a, b in NEG_EQ: add("NEGATION", "NG", a, b, True)
    for a, b in QTY_NEQ: add("QUANTITY", "QT", a, b, False, expected_critical=True)
    for a, b in QTY_EQ: add("QUANTITY", "QT", a, b, True)
    for a, b in DATE_EQ: add("DATE", "DT", a, b, True)
    for a, b in DATE_NEQ: add("DATE", "DT", a, b, False, expected_critical=True)
    for (a, b), eq in CON_PAIRS: add("CONSTRAINT", "CS", a, b, eq, **({} if eq else {"expected_critical": True}))
    for (a, b), eq in COND_PAIRS: add("CONDITION", "CD", a, b, eq, **({} if eq else {"expected_critical": True}))
    for (a, b), eq in REF_PAIRS: add("REFERENCE", "RF", a, b, eq, **({} if eq else {"expected_critical": True}))
    for t, amb in AMB: cases.append({"id": f"AM{sum(1 for c in cases if c['id'].startswith('AM')) + 1:03d}", "input_a": t, "input_b": None, "expected_ambiguous": amb, "expected_category": "AMBIGUITY"})
    for a, b, con in CONTRA: cases.append({"id": f"CT{sum(1 for c in cases if c['id'].startswith('CT')) + 1:03d}", "input_a": a, "input_b": b, "expected_contradiction": con, "expected_category": "CONTRADICTION"})
    return cases


def load():
    with open(os.path.join(ROOT, "data", "dev200.jsonl"), encoding="utf-8") as fh:
        return [json.loads(l) for l in fh if l.strip()]


if __name__ == "__main__":
    cs = build()
    with open(os.path.join(ROOT, "data", "dev200.jsonl"), "w", encoding="utf-8") as fh:
        for c in cs:
            fh.write(json.dumps(c, ensure_ascii=False) + "\n")
    import collections
    print(len(cs), dict(collections.Counter(c["expected_category"] for c in cs)))
