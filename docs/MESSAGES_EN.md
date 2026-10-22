# First-contact messages — English drafts for review (NOT sent)

Sender: Darwing Pérez Aranguren · director@daralaz.com · +57 320 205 4478
Same rule as the Spanish file: nothing goes out without your approval; every figure comes from `LIMITATIONS.md` (small samples, relays written by models, no real traffic yet).
What is asked for is a **measurement pilot**, not a sale.

---

## 1. A2A project — post for GitHub Discussions (`github.com/a2aproject/A2A/discussions`)
Before posting: read the Discussions guidelines and pick the category for "show and tell"/community feedback if one exists. Do not post it as an advertisement.

**Title:** Feedback wanted: a free, offline check for critical-slot changes between agents (A2A skill + MCP tool)

Hi all,

I maintain an open-source A2A agent and MCP server (AIXL) that checks whether an instruction kept its critical slots when one agent hands it to another: negation, numbers, dates and weekdays, modality (must/may), and/or, conditions, "only", named entities, action verb, who-is-first, pronouns. It needs no model and works in any vocabulary (ES/EN/PT tested).

What we measured, with the limits up front:
- Near-verbatim relays (copy errors, tampering, a flipped word): it flags 94.7 % of 2,659 meaning-changing corruptions and 0.1 % of 1,141 benign edits (formatting, politeness, contractions).
- Relays written by real models (120 sources, preregistered, run once): 75.8 % of subtle corruptions flagged, 8.3 % of near-verbatim faithful relays flagged.
- Where it does NOT work: when an agent rewords the instruction it flags 9 of 10 faithful relays. For that regime we use a two-judge arbiter (237/240 faithful relays proven, 119/120 corruptions caught); combining the two as a veto was tested and rejected.
- No measurement on real production traffic yet. That is the gap.

I would like feedback from teams that chain agents over A2A: what kinds of handoff errors do you actually see, and would a check like this be useful at the handoff? I am also looking for one or two teams willing to run a free, confidential 4–6 week measurement on 200–300 anonymised handoffs; if the real error rate turns out low, I will say so and stop.

Repo / results: [link to the public page you choose; the repository is currently private]. Contact: director@daralaz.com

Thanks!

> **Heads-up before posting:** the `aixl-core` repository is private, so the "link" has to be a public page you create (a short README or the paper, doi:10.5281/zenodo.23227169). Do not post a link nobody can open.

---

## 2. Langfuse — contact form `langfuse.com/talk-to-us`

**Subject:** Partnership idea: handoff-integrity checks for agent traces (design-partner pilot)

Hi Langfuse team,

I'm Darwing Pérez Aranguren (Daralaz). I build AIXL, an open-source layer that checks whether an instruction kept its critical slots (negation, numbers, dates, modality, conditions, names) when it passes between agents. It runs offline, with no model, and it is exposed as an MCP tool.

I'm looking for a way to test it on real agent traces, and Langfuse is where those traces live. Would you be open to a 30-minute call to see whether a handoff-integrity score could make sense as an evaluator or integration? I would run it as a free measurement pilot, with data staying on your side.

What I have, honestly: preregistered tests on 120 model-written relays (75.8 % of subtle corruptions flagged by the free detector; a two-judge arbiter caught 119/120). What I do not have: any real production traffic. That is the point of the pilot.

director@daralaz.com · +57 320 205 4478

Best,
Darwing Pérez Aranguren

---

## 3. LangChain — contact form `langchain.com/contact-sales` or `/langchain-partner-network`

**Subject:** Handoff-integrity check for multi-agent graphs — looking for a design partner

Hi LangChain team,

I'm Darwing Pérez Aranguren (Daralaz), author of AIXL, an open-source check that flags when a critical slot (negation, number, date, modality, condition, name) changes as a message moves between agents. It is deterministic, offline and available as an MCP tool.

In multi-agent graphs, the failure I care about is silent: the handoff is grammatical and the next agent acts confidently on a changed instruction. I'd like to learn whether LangGraph users see this in practice and whether a node-level check would help. Could we talk for 30 minutes?

Measured so far (small samples, preregistered): the free check flags 75.8 % of subtle corruptions in model-written relays; for reworded relays a two-judge arbiter caught 119/120. No real production traffic yet — that is what I'm looking for.

director@daralaz.com · +57 320 205 4478

Best,
Darwing Pérez Aranguren

---

## 4. Vozy / Wolkvox — English short version (for international contacts or partners)

**Subject:** Free measurement pilot: how often does meaning change when a bot hands a case over?

Hi, I'm Darwing Pérez Aranguren (Daralaz). I build a layer that detects when an instruction loses or changes a detail — a negation, a figure, a date — as it passes from one agent to another or to a person. I'm looking for one organisation for a free, confidential 4–6 week measurement on 200–300 anonymised handoffs. The offline detector sends no data out; you get a report with the share of handoffs that changed meaning and the type of change, and if it is low I will tell you and we stop. Could we talk for 30 minutes? director@daralaz.com · +57 320 205 4478

---

## Checklist before sending anything
- [ ] Each figure is one you can explain: 94.7 % (arena mutants) and 75.8 % / 237/240 / 119/120 (120 model-written relays) are small, preregistered samples.
- [ ] The public link exists (the repository is private).
- [ ] You have an NDA template ready, and `director@daralaz.com` receives and replies.
- [ ] Post in community spaces only after reading their rules; use the feedback framing, not an ad.
- [ ] Do not send the same message to many people at once: one organisation at a time, learn, adjust.
