# Internal response to a reported vulnerability or incident

AIXL has one maintainer, so this is a checklist for that person, not a team process. It follows the recommendations of the OSTIF *Security Best Practices Guide* (chapter 3). Targets are the ones promised in [SECURITY.md](../SECURITY.md).

## A. A vulnerability report arrives (private advisory or director@daralaz.com)
1. **Acknowledge** within 5 working days: say it was received, who handles it, and the next date you will write.
2. **Record it** privately (GitHub draft security advisory, not a public issue): date received, reporter, affected version or commit, claimed impact.
3. **Reproduce and confirm.** Write the smallest failing case as a test first. For this project a **silent failure** (the comparator, `compare_verified` or `relay_check` reporting EQUIVALENT / `ok: true` for a meaning change they claim to detect) is a security-relevant bug, not only a quality bug.
4. **Triage** within 15 working days: severity (critical = authentication bypass, remote code execution, or a silent failure on the destructive-action path DELETE / SEND; high = other silent failures, denial of service; medium / low = the rest), who is affected, whether a workaround exists. Tell the reporter the plan.
5. **Fix** on a private branch or advisory fork; add the regression test; run the full suite and, for comparator fixes, the blind-set regression (`benchmarks/blind*_eval.py` numbers recorded in the PREREG files must not get worse).
6. **Verify with the reporter** that the fix closes their case.
7. **Release and disclose**: publish the fix, request a CVE through the GitHub advisory if it qualifies, credit the reporter if they wish, and disclose no later than 90 days after the report (earlier by agreement).
8. **Look for siblings.** Add the pattern to `tests/test_mutation_properties.py` (a new mutator) so the same class cannot return unnoticed.

## B. A security incident without a report (compromised token, malicious dependency, tampered image, leaked secret)
1. **Contain**: revoke the token or key (GitHub, ghcr.io, Resend, any `AIXL_A2A_TOKEN` in use), pull or retag the affected image, pin the dependency to the last good version.
2. **Assess**: what was exposed, since when (git history, Actions logs, registry audit log), who could have used it.
3. **Eradicate and recover**: rotate every secret that could have been read, rebuild the image from a clean commit, re-run the tests, republish.
4. **Notify**: users of the public image (release note and, if warranted, a GitHub security advisory), and the maintainers of the affected third-party project. Report to the authorities where the law of the country of operation (Colombia) requires it.
5. **Write a short post-mortem** in `docs/HISTORY.md` or the advisory: cause, impact, fix, what changes so it cannot repeat.

## C. Things that are NOT handled by this document
Handling of personal data of third parties, legal advice and any commitment to a response time beyond best effort. See `SECURITY.md` ("Supported versions" and "Known limits").
