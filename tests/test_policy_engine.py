from backend.app.services.policy_engine import PolicyEngine


def test_loads_policy_from_json():
    engine = PolicyEngine()
    assert engine.policy["policy_id"] == "PLUM-OPD-2026"


def test_annual_limit():
    assert PolicyEngine().annual_limit() == 25000


def test_per_claim_limit():
    assert PolicyEngine().per_claim_limit() == 5000


def test_waiting_period():
    assert PolicyEngine().waiting_period_days() == 30


def test_exclusions():
    exclusions = PolicyEngine().exclusions()
    assert "cosmetic" in exclusions
    assert "teeth whitening" in exclusions


def test_category_limit():
    assert PolicyEngine().category_limit("consultation") == 1000
    assert PolicyEngine().category_limit("pharmacy") == 3000
    assert PolicyEngine().category_limit("nonexistent") == 0


def test_network_providers():
    providers = PolicyEngine().network_providers()
    assert "CityCare Clinic" in providers
