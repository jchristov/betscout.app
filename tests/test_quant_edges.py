from sportdata_model.enrich import infer_surface
from sportdata_model.ingest import _valid_1x2, _valid_dc, _valid_totals, american_to_decimal
from sportdata_model.quant_edges import settle_asian_total


def test_settle_asian_total_pushes_and_quarter_lines():
    # Exact push on 3.0 line (both Over and Under return 0.0, NOT a win for Under!)
    assert settle_asian_total(3.0, 3.0, 1.90, "OVER") == 0.0
    assert settle_asian_total(3.0, 3.0, 1.90, "UNDER") == 0.0
    # Quarter line 2.25 when total goals == 2: Over loses half (-0.5), Under wins half (+0.5*(odds-1))
    assert settle_asian_total(2.0, 2.25, 2.00, "OVER") == -0.5
    assert settle_asian_total(2.0, 2.25, 2.00, "UNDER") == 0.5
    # Quarter line 2.75 when total goals == 3: Over wins half (+0.5*(odds-1)), Under loses half (-0.5)
    assert settle_asian_total(3.0, 2.75, 1.80, "OVER") == 0.40
    assert settle_asian_total(3.0, 2.75, 1.80, "UNDER") == -0.5
    # Half line 2.5
    assert settle_asian_total(3.0, 2.5, 1.95, "OVER") == 0.95
    assert settle_asian_total(3.0, 2.5, 1.95, "UNDER") == -1.0


def test_infer_surface():
    assert infer_surface("Roland Garros") == "clay"
    assert infer_surface("Wimbledon") == "grass"
    assert infer_surface("US Open") == "hard"


def test_validators_reject_inplay_and_bad_overround():
    # Reject 90th-minute in-play draw odds (1.063) or extreme 451.0 odds
    assert not _valid_1x2(10.0, 1.063, 41.0)
    assert not _valid_1x2(1.004, 41.0, 301.0)
    # Accept genuine pre-match 1X2
    assert _valid_1x2(1.80, 3.60, 4.50)
    # Reject corrupted double-chance overround (1.111, 1.125, 1.167 -> sum/2 = 1.32 > 1.25)
    assert not _valid_dc(1.111, 1.125, 1.167)
    assert _valid_dc(1.30, 1.65, 1.28, 2.10, 3.40, 3.50)
    # Totals validator
    assert _valid_totals(2.5, 1.90, 1.95)
    assert not _valid_totals(None, 1.90, 1.95)
    assert round(american_to_decimal(-200), 2) == 1.50
    assert round(american_to_decimal("+350"), 2) == 4.50
