"""Option C (V1 audit): content references instead of resending. Within ONE conversation, a run of lines already sent earlier is replaced by
a pointer ⟦=<msg>:<first>-<last>⟧ to an earlier message. Lossless by construction; every encode is verified by decode()==original (else sent raw).
Scope is deliberately one conversation: the receiver already holds those messages, so the pointer is resolvable without a shared store."""
import re
from collections import defaultdict

MIN_CHARS = 200      # a run must be at least this long (~50 tokens) to be worth a pointer
MIN_LINE = 12        # shorter lines ('}', 'end', blanks) are neutral: they never start a run
MARK = "⟦="
_REF = re.compile(r"⟦=(\d+):(\d+)-(\d+)⟧")


class RefStore:
    def __init__(self):
        self.msgs: list[list[str]] = []          # original lines of every message sent so far
        self.idx = defaultdict(list)             # line -> [(msg, lineno)] (most recent last, capped)

    def _add(self, lines):
        mid = len(self.msgs)
        self.msgs.append(lines)
        for n, ln in enumerate(lines):
            if len(ln) >= MIN_LINE:
                c = self.idx[ln]
                c.append((mid, n))
                if len(c) > 6: del c[0]
        return mid

    def encode(self, text: str) -> str:
        lines = text.split("\n")
        out, i, used = [], 0, False
        if MARK not in text:
            while i < len(lines):
                best = None
                if len(lines[i]) >= MIN_LINE:
                    for (m, n) in self.idx.get(lines[i], ()):
                        src, k = self.msgs[m], 0
                        while i + k < len(lines) and n + k < len(src) and lines[i + k] == src[n + k]:
                            k += 1
                        # trim trailing neutral lines so a pointer ends on content
                        while k and len(lines[i + k - 1]) < MIN_LINE: k -= 1
                        span = sum(len(x) + 1 for x in lines[i:i + k])
                        if span >= MIN_CHARS and (best is None or span > best[0]):
                            best = (span, m, n, k)
                if best:
                    _, m, n, k = best
                    out.append(f"{MARK}{m}:{n}-{n + k - 1}⟧"); i += k; used = True
                else:
                    out.append(lines[i]); i += 1
        enc = "\n".join(out) if used else text
        if used and self.decode(enc) != text:       # never ship an encoding we cannot reverse
            enc = text
        self._add(lines)
        return enc

    def decode(self, enc: str) -> str:
        def sub(mo):
            m, a, b = map(int, mo.groups())
            return "\n".join(self.msgs[m][a:b + 1])
        return _REF.sub(sub, enc)
