from scripts.eval import composite_score, WEIGHTS


def test_composite_score_all_ones():
    scores = {d: 1.0 for d in WEIGHTS}
    assert abs(composite_score(scores) - 1.0) < 1e-9


def test_composite_score_all_zeros():
    scores = {d: 0.0 for d in WEIGHTS}
    assert composite_score(scores) == 0.0


def test_composite_score_only_factual():
    scores = {d: 0.0 for d in WEIGHTS}
    scores["factual_accuracy"] = 1.0
    assert abs(composite_score(scores) - 0.50) < 1e-9


def test_weights_sum_to_one():
    assert abs(sum(WEIGHTS.values()) - 1.0) < 1e-9
