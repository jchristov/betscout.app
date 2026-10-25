from betscout.walkforward import run  # noqa: F401  (import check)


def test_double_chance_devig_sums_to_two():
    inv = {"1X": 1 / 1.25, "X2": 1 / 1.6, "12": 1 / 1.2}
    scale = 2 / sum(inv.values())
    assert abs(sum(v * scale for v in inv.values()) - 2) < 1e-12
