# Ontology
Source of truth: `aixl/core/ontology.py` (do not duplicate the lists here; this file explains them).

- **ACTIONS** (25): ANALYZE COMPARE FIND CREATE DELETE CHECK TRANSLATE GENERATE CALCULATE SEARCH RETRIEVE EXECUTE UPDATE SUMMARIZE VALIDATE GET TRANSFORM CLASSIFY EXTRACT PREDICT ENABLE DISABLE SEND INCLUDE EXCLUDE. Closed list; unknown verbs are ignored, not guessed (see LIMITATIONS.md #2).
- **ENTITIES**: PERSON COMPANY PRODUCT REPORT DOCUMENT RESULT ANOMALY EVENT LOCATION MODEL. **DATA**: SALES CUSTOMERS USERS DATA DATASET IMAGE AUDIO VIDEO. The ontology decides node type, so REPORT is an ENTITY even if a frame listed it as data.
- **Output formats**: JSON CSV TABLE TEXT REPORT AIXL MARKDOWN PDF XLSX HTML XML DOCX. **Modifiers**: CONFIDENCE PRIORITY LIMIT FORMAT LANGUAGE.
- **Antonyms** (used by the contradiction detector): ENABLE/DISABLE, INCLUDE/EXCLUDE. `action_groups` in `data/config.json` map synonyms to one canonical action; EXCLUDE is canonicalised to a prohibited INCLUDE.
- **Intent vs action** are kept separate: `intent` is *derived* from canonical actions/negation (e.g. REQUEST_SEARCH), never an independent field.
- **Relative time** tokens (TODAY, TOMORROW, LAST_MONTH, NEXT_YEAR...) resolve against an explicit `today` only at canonicalisation. Week-level tokens stay unresolved on purpose.
- Extension: add terms in the ontology/config, add a test, bump VERSIONING_POLICY.md. Domain extensions: EXTENSION_GUIDE.md. Only the general domain exists.

- **Residue** has no ontology entry on purpose: `RESIDUE` nodes hold free literals (words of the original text) that no closed list can name; they are compared as order-free stemmed content words.
