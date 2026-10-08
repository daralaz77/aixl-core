from aixl.refpolicy import PolicyStore, pointers_allowed

BIG = "\n".join(f"def function_number_{i}(argument): return argument * {i}" for i in range(12))


def test_measured_families():
    assert pointers_allowed("claude-sonnet-5-5") and pointers_allowed("claude-opus-5-5") and not pointers_allowed("claude-haiku-4-5-20251001")


def test_unknown_receiver_fails_closed():
    assert not pointers_allowed("claude-fable-5-1") and not pointers_allowed("some-other-model")


def test_weak_receiver_gets_plain_text_strong_gets_pointer():
    for model, want_ptr in [("claude-haiku-4-5", False), ("claude-sonnet-5-5", True)]:
        s = PolicyStore(model); s.encode(BIG); e = s.encode("x\n" + BIG)
        assert ("⟦=" in e) == want_ptr
        if want_ptr: assert s.decode(e) == "x\n" + BIG
        else: assert e == "x\n" + BIG
