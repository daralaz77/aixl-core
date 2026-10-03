# Semantic diff
`format_diff(a, b)` / `api.semantic_diff(text_a, text_b)` renders per-dimension status for the dimensions present in either side: unchanged, or changed with source -> target, kind (`changed|added|removed|order`), and severity. Machine form: `ComparisonResult.diff` (list of `Difference{field, source, target, kind, severity, detail}`).
Example: "Envía el informe." vs "Envía el informe en PDF." gives OUTPUT added; ACTION and ENTITY unchanged. Whether an added format is acceptable is policy, left to the caller via severity.
