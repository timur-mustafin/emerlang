from emerlang.structure import make_markers, select_template, probabilistic_sequence

def test_markers_determinism():
    m1 = make_markers(123)
    m2 = make_markers(123)
    assert m1 == m2

def test_weighted_templates():
    templates = ["A","B","C"]
    weights = [0.1, 0.2, 0.7]
    s1 = select_template(templates, weights, 42)
    s2 = select_template(templates, weights, 42)
    assert s1 == s2

def test_probabilistic_sequence_repro():
    choices = [("x",1.0),("y",2.0)]
    seq1 = probabilistic_sequence(choices, 5, seed=99)
    seq2 = probabilistic_sequence(choices, 5, seed=99)
    assert seq1 == seq2
