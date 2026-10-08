"""Phase 5: the ASCII fast path of strip_accents must be identical to the original per-character implementation."""
import random

from aixl.core.normalizer import _strip_accents_slow, strip_accents


def test_every_ascii_character_is_identical():
    for i in range(128):
        c = chr(i)
        assert strip_accents(c) == _strip_accents_slow(c)


def test_whole_unicode_range_and_random_strings_are_identical():
    for i in range(0x250):                       # Latin ranges where accents live
        c = chr(i)
        assert strip_accents(c) == _strip_accents_slow(c)
    rnd = random.Random(1)
    alphabet = [chr(i) for i in range(32, 127)] + list("áéíóúñüÁÉÍÓÚÑÜçãõâêôà İıß")
    for _ in range(2000):
        s = "".join(rnd.choice(alphabet) for _ in range(rnd.randint(0, 40)))
        assert strip_accents(s) == _strip_accents_slow(s)
