# Security milestones: when to harden further or get an audit

Planning aid following the OSTIF *Security Best Practices Guide* (chapter 7). It says what would change the risk, not when anything is planned: dates belong to the maintainer.

## Current profile (2026-11-05)
| Question | Answer |
|---|---|
| Major changes planned? | Comparator work is continuous (blind sets, mutation properties). No new network-facing component is planned. |
| New third-party libraries? | Only optional extras (see [THIRD_PARTY.md](THIRD_PARTY.md)); the core stays dependency-free. |
| Cryptography? | One module: `aixl/signed_envelope.py` (Ed25519 through the `cryptography` library, **not self-rolled**). No external review of our use of it. |
| Internet exposure? | The A2A agent and MCP server can be exposed by a deployer; both are off by default. No hosted instance is run by the project. |
| Stores user PII? | No. Texts are processed in memory; the arbiter sends them to the model providers the deployer configures. |

## Triggers: re-assess and consider an external review when any of these happens
1. **A hosted AIXL service** is offered to third parties (attack surface changes from "library you run" to "service we run").
2. **Someone relies on `EQUIVALENT` for a destructive or irreversible action** in production (DELETE, SEND, payments): the comparator's documented limit is that it is fail-closed, not a proof; an independent review of the claim becomes worth paying for.
3. **The signed envelope is used to authenticate senders** outside a closed group: add key distribution, rotation, revocation and a cryptography review first.
4. **A second maintainer or outside contributors** get write access: turn on required reviews for `main` and required status checks.
5. **A new network-facing endpoint, or a change to authentication, rate limiting or the container**: threat-model it in [SECURITY_MODEL.md](SECURITY_MODEL.md) before release.
6. **Two vulnerability reports confirmed within 12 months**: schedule an audit.

## Before any audit
- Run the checklist of Least Authority's *Audit Preparation* guide (linked from the OSTIF chapter).
- Freeze a commit, regenerate the SBOM (`python scripts/make_sbom.py`), and hand over `SECURITY.md`, `LIMITATIONS.md`, `docs/SECURITY_MODEL.md` and the PREREG files of the blind sets (they list the known failures honestly).
- State the scope the way `SECURITY.md` does: the A2A agent, the MCP server, the envelope, `compare_verified` / `relay_check`, and the container.
