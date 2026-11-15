from gate import check

GATE = {"accuracy": 0.85}


def test_gate_passes_good_model():
    assert check({"accuracy": 0.89, "f1": 0.89}, GATE) == []


def test_gate_blocks_bad_model():
    assert check({"accuracy": 0.10}, GATE) == ["accuracy=0.1000 < 0.85"]
