from aixl.refstore import RefStore

BIG = "\n".join(f"def function_number_{i}(argument): return argument * {i}" for i in range(12))


def test_second_send_is_a_pointer_and_lossless():
    s = RefStore(); s.encode("first message\n" + BIG)
    e = s.encode("second message\n" + BIG + "\nnew trailing line that is also long enough")
    assert "⟦=0:" in e and len(e) < len(BIG) // 2
    assert s.decode(e) == "second message\n" + BIG + "\nnew trailing line that is also long enough"


def test_short_repeats_not_referenced():
    s = RefStore(); s.encode("hola que tal"); assert s.encode("hola que tal") == "hola que tal"


def test_text_containing_marker_sent_raw():
    s = RefStore(); s.encode(BIG); t = BIG + "\n⟦=0:0-1⟧ literal"; assert s.encode(t) == t
