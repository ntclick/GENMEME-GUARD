import json
import sys
import pytest

CONTRACT = "contracts/meme_rug_auditor.py"

# The audit fails closed, so every successful-path test has to supply the live
# market and authority evidence the contract insists on before it will call the
# model at all.
DEX_RESPONSE = {
    "pairs": [{
        "baseToken": {"symbol": "WIF", "name": "Dogwifhat"},
        "dexId": "raydium",
        "priceUsd": "2.45",
        "liquidity": {"usd": 1500000.0},
        "volume": {"h24": 5000000.0},
        "priceChange": {"h24": 12.5},
        "txns": {"h24": {"buys": 1200, "sells": 800}},
    }]
}

RUGCHECK_RESPONSE = {
    "token": {"mintAuthority": None, "freezeAuthority": None},
    "risks": [{"name": "High volume volatility"}],
    "score": 92,
}


def mock_live_sources(vm, dex=None, rugcheck=None):
    """Register the DEXScreener and RugCheck responses the contract fetches."""
    vm.mock_web(r".*dexscreener\.com.*",
                {"status": 200, "body": json.dumps(dex if dex is not None else DEX_RESPONSE)})
    vm.mock_web(r".*rugcheck\.xyz.*",
                {"status": 200, "body": json.dumps(rugcheck if rugcheck is not None else RUGCHECK_RESPONSE)})


def llm_verdict(**overrides):
    """A schema-valid model report, tweakable per test."""
    report = {
        "token_address": "EKpQGSJtjMFqKZ9KQanSqYXRcF8fBopzLHYxdM65zcjm",
        "token_symbol": "WIF",
        "safety_score": 92,
        "verdict": "SAFE_TO_TRADE",
        "mint_disabled": True,
        "freeze_disabled": True,
        "lp_burned_pct": 100,
        "top10_holder_pct": 18,
        "holder_count": 185400,
        "smart_money_wallets": 42,
        "risk_factors": ["High volume volatility"],
        "ai_summary": "Model brief covering tier, liquidity, hooks and orderbook flow.",
    }
    report.update(overrides)
    return json.dumps(report)


def get_check_equivalence(direct_deploy):
    contract = direct_deploy("contracts/meme_rug_auditor.py")
    mod = sys.modules["_contract_meme_rug_auditor"]
    return mod._check_equivalence


def test_equivalence_valid(direct_deploy):
    _check_equivalence = get_check_equivalence(direct_deploy)
    res1 = {
        "safety_score": 85,
        "verdict": "SAFE_TO_TRADE",
        "mint_disabled": True,
        "freeze_disabled": True,
    }
    res2 = {
        "safety_score": 90,  # delta = 5 <= SCORE_TOLERANCE (10)
        "verdict": "SAFE_TO_TRADE",
        "mint_disabled": True,
        "freeze_disabled": True,
    }
    assert _check_equivalence(res1, res2) is True


def test_equivalence_exceeds_tolerance(direct_deploy):
    _check_equivalence = get_check_equivalence(direct_deploy)
    res1 = {
        "safety_score": 70,
        "verdict": "SAFE_TO_TRADE",
        "mint_disabled": True,
        "freeze_disabled": True,
    }
    res2 = {
        "safety_score": 85,  # delta = 15 > SCORE_TOLERANCE (10)
        "verdict": "SAFE_TO_TRADE",
        "mint_disabled": True,
        "freeze_disabled": True,
    }
    assert _check_equivalence(res1, res2) is False


def test_equivalence_verdict_mismatch(direct_deploy):
    _check_equivalence = get_check_equivalence(direct_deploy)
    res1 = {
        "safety_score": 80,
        "verdict": "SAFE_TO_TRADE",
        "mint_disabled": True,
        "freeze_disabled": True,
    }
    res2 = {
        "safety_score": 80,
        "verdict": "CRITICAL_RUG_RISK",
        "mint_disabled": True,
        "freeze_disabled": True,
    }
    assert _check_equivalence(res1, res2) is False


def test_equivalence_mint_disabled_mismatch(direct_deploy):
    _check_equivalence = get_check_equivalence(direct_deploy)
    res1 = {
        "safety_score": 80,
        "verdict": "SAFE_TO_TRADE",
        "mint_disabled": True,
        "freeze_disabled": True,
    }
    res2 = {
        "safety_score": 80,
        "verdict": "SAFE_TO_TRADE",
        "mint_disabled": False,  # Mismatch
        "freeze_disabled": True,
    }
    assert _check_equivalence(res1, res2) is False


def test_meme_rug_auditor_init(direct_vm, direct_deploy, direct_alice):
    direct_vm.sender = direct_alice
    contract = direct_deploy("contracts/meme_rug_auditor.py")

    overview = contract.get_overview()
    assert overview["audited_count"] == 0
    assert overview["recent_tokens"] == []
    alice_hex = direct_alice.hex() if isinstance(direct_alice, bytes) else str(direct_alice)
    if not alice_hex.startswith("0x"):
        alice_hex = f"0x{alice_hex}"
    assert overview["owner"].lower() == alice_hex.lower()


def test_meme_rug_auditor_audit_flow(direct_vm, direct_deploy, direct_alice):
    direct_vm.sender = direct_alice

    mock_llm_result = {
        "token_address": "EKpQGSJtjMFqKZ9KQanSqYXRcF8fBopzLHYxdM65zcjm",
        "token_symbol": "WIF",
        "safety_score": 92,
        "verdict": "SAFE_TO_TRADE",
        "mint_disabled": True,
        "freeze_disabled": True,
        "lp_burned_pct": 100,
        "top10_holder_pct": 18,
        "risk_factors": ["High volume volatility"],
        "ai_summary": "Dogwifhat token exhibits 100% burned liquidity and mint/freeze authority disabled.",
    }

    dex_response = {
        "pairs": [
            {
                "baseToken": {"symbol": "WIF", "name": "Dogwifhat"},
                "dexId": "raydium",
                "priceUsd": "2.45",
                "liquidity": {"usd": 1500000.0},
                "volume": {"h24": 5000000.0},
                "priceChange": {"h24": 12.5},
                "txns": {"h24": {"buys": 1200, "sells": 800}},
            }
        ]
    }

    rugcheck_response = {
        "token": {"mintAuthority": None, "freezeAuthority": None},
        "risks": [{"name": "High volume volatility"}],
        "score": 92,
    }

    # Set up GenVM Direct Mode mocks for Web API & LLM calls
    direct_vm.mock_web(r".*dexscreener\.com.*", {"status": 200, "body": json.dumps(dex_response)})
    direct_vm.mock_web(r".*rugcheck\.xyz.*", {"status": 200, "body": json.dumps(rugcheck_response)})
    direct_vm.mock_llm(r".*", json.dumps(mock_llm_result))

    contract = direct_deploy("contracts/meme_rug_auditor.py")
    token_ca = "EKpQGSJtjMFqKZ9KQanSqYXRcF8fBopzLHYxdM65zcjm"

    # Audit token
    contract.audit_token(token_ca)

    report = contract.get_audit(token_ca)
    assert report["has_audit"] is True
    assert report["token_address"] == token_ca
    assert report["token_symbol"] == "WIF"
    assert report["safety_score"] == 92
    assert report["verdict"] == "SAFE_TO_TRADE"
    assert report["mint_disabled"] is True
    assert report["freeze_disabled"] is True
    assert report["lp_burned_pct"] == 100
    assert report["top10_holder_pct"] == 18

    overview = contract.get_overview()
    assert overview["audited_count"] == 1
    assert token_ca in overview["recent_tokens"]


def test_forged_payment_rejection(direct_vm, direct_deploy, direct_alice):
    direct_vm.sender = direct_alice
    contract = direct_deploy("contracts/meme_rug_auditor.py")
    token_ca = "EKpQGSJtjMFqKZ9KQanSqYXRcF8fBopzLHYxdM65zcjm"

    # Attempting audit with forged/insufficient payment (500 < MIN_AUDIT_FEE 1000)
    with pytest.raises(Exception, match="Insufficient audit fee / Forged payment"):
        contract.audit_token(token_ca, request_id="forged_req_001", payment_amount=500)


def test_replay_attack_prevention(direct_vm, direct_deploy, direct_alice):
    direct_vm.sender = direct_alice

    mock_live_sources(direct_vm)
    direct_vm.mock_llm(r".*", llm_verdict(safety_score=90))

    contract = direct_deploy(CONTRACT)
    token_ca = "EKpQGSJtjMFqKZ9KQanSqYXRcF8fBopzLHYxdM65zcjm"

    # First request succeeds
    contract.audit_token(token_ca, request_id="unique_req_101", payment_amount=1000)

    # Replay request with exact same request_id must be rejected
    with pytest.raises(Exception, match="Replay attack detected"):
        contract.audit_token(token_ca, request_id="unique_req_101", payment_amount=1000)


def test_request_id_mismatch_authorization(direct_vm, direct_deploy, direct_alice, direct_bob):
    direct_vm.sender = direct_alice

    mock_live_sources(direct_vm)
    direct_vm.mock_llm(r".*", llm_verdict(
        token_address="5c4HyD2rSShqnTsf5z3SaoD2H3GE452u2CUuYjviBAGS",
        token_symbol="SGL",
        safety_score=85,
        ai_summary="SGL audit completed for Alice.",
    ))

    contract = direct_deploy(CONTRACT)
    token_ca = "5c4HyD2rSShqnTsf5z3SaoD2H3GE452u2CUuYjviBAGS"

    # Alice submits audit request
    contract.audit_token(token_ca, request_id="alice_private_req_999", payment_amount=1000)

    # Alice queries her own request_id -> succeeds
    alice_hex = direct_alice.hex() if isinstance(direct_alice, bytes) else str(direct_alice)
    report = contract.get_request_audit("alice_private_req_999", caller_address=alice_hex)
    assert report["has_audit"] is True
    assert report["request_id"] == "alice_private_req_999"

    # Bob attempts to query Alice's request_id pretending to be caller -> rejected
    bob_hex = direct_bob.hex() if isinstance(direct_bob, bytes) else str(direct_bob)
    with pytest.raises(Exception, match="Caller authorization mismatch"):
        contract.get_request_audit("alice_private_req_999", caller_address=bob_hex)



WIF_CA = "EKpQGSJtjMFqKZ9KQanSqYXRcF8fBopzLHYxdM65zcjm"

BLUECHIP_TELEMETRY = json.dumps({
    "token_symbol": "WIF",
    "token_name": "dogwifhat",
    "price_usd": "2.45",
    "market_cap_usd": 2450000000.0,
    "fdv_usd": 2450000000.0,
    "liquidity_usd": 15420000.0,
    "volume_24h_usd": 185000000.0,
    "price_change_24h_pct": 5.2,
    "txns_24h_buys": 14200,
    "txns_24h_sells": 11800,
    "holder_count": 185400,
    "smart_money_wallets": 42,
    "top10_holder_pct": 18,
    "mint_disabled": True,
    "freeze_disabled": True,
    "lp_burned_pct": 100,
    "detected_risks": []
})


def test_llm_verdict_drives_stored_report(direct_vm, direct_deploy, direct_alice):
    """The on-chain LLM round decides the stored report.

    Bluechip telemetry with revoked authorities and $15M liquidity is about as
    strong as this rubric gets, yet the model returns 63/HIGH_VOLATILITY_WARN
    and that is exactly what lands on chain — the number and the wording both
    come from the model, not from anything the contract could have computed.
    """
    direct_vm.sender = direct_alice
    direct_vm.mock_llm(r".*", llm_verdict(
        safety_score=63,
        verdict="HIGH_VOLATILITY_WARN",
        risk_factors=["Model-flagged momentum exhaustion after parabolic run"],
        ai_summary="Model brief: elevated volatility despite deep liquidity.",
    ))

    contract = direct_deploy(CONTRACT)
    contract.audit_token(WIF_CA, request_id="req_llm_drives_1", payment_amount=1000,
                         telemetry_json=BLUECHIP_TELEMETRY)

    report = contract.get_audit(WIF_CA)
    assert report["analysis_source"] == "llm_consensus"
    assert report["safety_score"] == 63
    assert report["verdict"] == "HIGH_VOLATILITY_WARN"
    assert "momentum exhaustion" in report["risk_factors"][0]
    assert report["ai_summary"] == "Model brief: elevated volatility despite deep liquidity."


def test_audit_reverts_when_llm_round_unavailable(direct_vm, direct_deploy, direct_alice):
    """No model, no report. There is no local scoring path to fall back on, so
    the transaction reverts rather than storing a fabricated audit."""
    direct_vm.sender = direct_alice
    contract = direct_deploy(CONTRACT)

    with pytest.raises(Exception, match="LLM consensus round unavailable"):
        contract.audit_token(WIF_CA, request_id="req_llm_missing_1", payment_amount=1000,
                             telemetry_json=BLUECHIP_TELEMETRY)

    assert contract.get_audit(WIF_CA)["has_audit"] is False


def test_audit_reverts_on_malformed_llm_response(direct_vm, direct_deploy, direct_alice):
    """A reply that breaks the schema or leaves the valid range is untrusted,
    and an untrusted reply aborts the audit instead of being stored."""
    direct_vm.sender = direct_alice
    direct_vm.mock_llm(r".*", json.dumps({
        "token_symbol": "WIF",
        "safety_score": 420,               # out of the 0-100 range
        "verdict": "DEFINITELY_FINE",      # not an allowed verdict
        "ai_summary": "",
    }))

    contract = direct_deploy(CONTRACT)
    with pytest.raises(Exception, match="LLM_ERROR"):
        contract.audit_token(WIF_CA, request_id="req_llm_malformed_1", payment_amount=1000,
                             telemetry_json=BLUECHIP_TELEMETRY)

    assert contract.get_audit(WIF_CA)["has_audit"] is False


@pytest.mark.parametrize("symbol,score,verdict", [
    ("BLUE", 91, "SAFE_TO_TRADE"),
    ("MIDC", 64, "HIGH_VOLATILITY_WARN"),
    ("MICR", 22, "CRITICAL_RUG_RISK"),
])
def test_distinct_tokens_store_distinct_verdicts(direct_vm, direct_deploy, direct_alice,
                                                 symbol, score, verdict):
    """Each token carries through its own model verdict rather than collapsing
    onto one canned result."""
    direct_vm.sender = direct_alice
    direct_vm.mock_llm(r".*", llm_verdict(
        token_symbol=symbol, safety_score=score, verdict=verdict,
        ai_summary=f"{symbol} brief at {score}/100.",
    ))

    contract = direct_deploy(CONTRACT)
    contract.audit_token(WIF_CA, request_id=f"req_tier_{symbol}", payment_amount=1000,
                         telemetry_json=BLUECHIP_TELEMETRY)

    report = contract.get_audit(WIF_CA)
    assert report["token_symbol"] == symbol
    assert report["safety_score"] == score
    assert report["verdict"] == verdict
    assert report["analysis_source"] == "llm_consensus"


def test_audit_reverts_without_authority_evidence(direct_vm, direct_deploy, direct_alice):
    """Authority status unknown means nothing can be certified. RugCheck
    returning an empty payload must not be read as 'authorities revoked'."""
    direct_vm.sender = direct_alice
    mock_live_sources(direct_vm, rugcheck={})
    direct_vm.mock_llm(r".*", llm_verdict())

    contract = direct_deploy(CONTRACT)
    market_only_telemetry = json.dumps({
        "token_symbol": "WIF",
        "fdv_usd": 2450000000.0,
        "liquidity_usd": 15420000.0,
        "volume_24h_usd": 185000000.0,
        "txns_24h_buys": 14200,
        "txns_24h_sells": 11800,
        # deliberately no mint_disabled / freeze_disabled
    })

    with pytest.raises(Exception, match="authority status unavailable"):
        contract.audit_token(WIF_CA, request_id="req_no_authority_1", payment_amount=1000,
                             telemetry_json=market_only_telemetry)

    assert contract.get_audit(WIF_CA)["has_audit"] is False


def test_audit_reverts_without_market_data(direct_vm, direct_deploy, direct_alice):
    """A mint with no reachable liquidity cannot be scored on real numbers."""
    direct_vm.sender = direct_alice
    mock_live_sources(direct_vm, dex={"pairs": []})
    direct_vm.mock_llm(r".*", llm_verdict())

    contract = direct_deploy(CONTRACT)
    with pytest.raises(Exception, match="no live market data"):
        contract.audit_token(WIF_CA, request_id="req_no_market_1", payment_amount=1000)

    assert contract.get_audit(WIF_CA)["has_audit"] is False


def test_llm_cannot_override_authority_findings(direct_vm, direct_deploy, direct_alice):
    """Authority status is on-chain evidence, so a model claiming a token with
    a live mint authority is safe gets corrected before the report is stored."""
    direct_vm.sender = direct_alice
    direct_vm.mock_llm(r".*", json.dumps({
        "token_address": WIF_CA,
        "token_symbol": "WIF",
        "safety_score": 95,
        "verdict": "SAFE_TO_TRADE",
        "mint_disabled": True,      # model contradicts the telemetry below
        "freeze_disabled": True,
        "lp_burned_pct": 100,
        "top10_holder_pct": 18,
        "risk_factors": [],
        "ai_summary": "Model brief claiming a clean bill of health.",
    }))

    hostile_telemetry = json.dumps({
        "token_symbol": "WIF",
        "fdv_usd": 2450000000.0,
        "liquidity_usd": 15420000.0,
        "volume_24h_usd": 185000000.0,
        "txns_24h_buys": 14200,
        "txns_24h_sells": 11800,
        "holder_count": 185400,
        "smart_money_wallets": 42,
        "top10_holder_pct": 18,
        "mint_disabled": False,     # live mint authority — hard on-chain fact
        "freeze_disabled": True,
        "lp_burned_pct": 100,
        "detected_risks": []
    })

    contract = direct_deploy("contracts/meme_rug_auditor.py")
    contract.audit_token(WIF_CA, request_id="req_authority_override_1", payment_amount=1000,
                         telemetry_json=hostile_telemetry)

    report = contract.get_audit(WIF_CA)
    assert report["analysis_source"] == "llm_consensus"
    assert report["mint_disabled"] is False          # evidence overrode the model
    assert report["verdict"] == "CRITICAL_RUG_RISK"  # forced, despite the model's SAFE
    assert report["safety_score"] <= 49
    assert any("Mint Authority Active" in r for r in report["risk_factors"])


def test_validator_consensus_agrees_on_reexecution(direct_vm, direct_deploy, direct_alice):
    """Proves real validator consensus: a validator independently re-runs the
    web+LLM audit via validator_fn and reaches equivalence with the leader
    when it observes the same external data (gl.vm.run_nondet_unsafe path)."""
    direct_vm.sender = direct_alice

    mock_llm_result = {
        "token_address": "EKpQGSJtjMFqKZ9KQanSqYXRcF8fBopzLHYxdM65zcjm",
        "token_symbol": "WIF",
        "safety_score": 92,
        "verdict": "SAFE_TO_TRADE",
        "mint_disabled": True,
        "freeze_disabled": True,
        "lp_burned_pct": 100,
        "top10_holder_pct": 18,
        "risk_factors": ["High volume volatility"],
        "ai_summary": "Dogwifhat token exhibits 100% burned liquidity and mint/freeze authority disabled.",
    }
    dex_response = {
        "pairs": [{
            "baseToken": {"symbol": "WIF", "name": "Dogwifhat"},
            "dexId": "raydium",
            "priceUsd": "2.45",
            "liquidity": {"usd": 1500000.0},
            "volume": {"h24": 5000000.0},
            "priceChange": {"h24": 12.5},
            "txns": {"h24": {"buys": 1200, "sells": 800}},
        }]
    }
    rugcheck_response = {
        "token": {"mintAuthority": None, "freezeAuthority": None},
        "risks": [{"name": "High volume volatility"}],
        "score": 92,
    }

    direct_vm.mock_web(r".*dexscreener\.com.*", {"status": 200, "body": json.dumps(dex_response)})
    direct_vm.mock_web(r".*rugcheck\.xyz.*", {"status": 200, "body": json.dumps(rugcheck_response)})
    direct_vm.mock_llm(r".*", json.dumps(mock_llm_result))

    contract = direct_deploy("contracts/meme_rug_auditor.py")
    token_ca = "EKpQGSJtjMFqKZ9KQanSqYXRcF8fBopzLHYxdM65zcjm"
    contract.audit_token(token_ca, request_id="req_consensus_agree_1", payment_amount=1000)

    # Same mocks are still active, so the validator's independent re-run of
    # leader_fn() inside validator_fn observes the same web+LLM data and
    # must reach equivalence with the stored leader result.
    agreed = direct_vm.run_validator()
    assert agreed is True


def test_validator_consensus_rejects_divergent_reexecution(direct_vm, direct_deploy, direct_alice):
    """Proves the equivalence check actually rejects disagreement: when the
    validator's independent re-run observes materially different LLM output
    (e.g. a manipulated/hallucinating node), validator_fn must return False
    instead of blindly trusting the leader's local shape."""
    direct_vm.sender = direct_alice

    leader_llm_result = {
        "token_address": "EKpQGSJtjMFqKZ9KQanSqYXRcF8fBopzLHYxdM65zcjm",
        "token_symbol": "WIF",
        "safety_score": 92,
        "verdict": "SAFE_TO_TRADE",
        "mint_disabled": True,
        "freeze_disabled": True,
        "lp_burned_pct": 100,
        "top10_holder_pct": 18,
        "risk_factors": [],
        "ai_summary": "Clean audit.",
    }
    dex_response = {
        "pairs": [{
            "baseToken": {"symbol": "WIF", "name": "Dogwifhat"},
            "dexId": "raydium",
            "priceUsd": "2.45",
            "liquidity": {"usd": 1500000.0},
            "volume": {"h24": 5000000.0},
            "priceChange": {"h24": 12.5},
            "txns": {"h24": {"buys": 1200, "sells": 800}},
        }]
    }
    rugcheck_response = {
        "token": {"mintAuthority": None, "freezeAuthority": None},
        "risks": [],
        "score": 92,
    }

    direct_vm.mock_web(r".*dexscreener\.com.*", {"status": 200, "body": json.dumps(dex_response)})
    direct_vm.mock_web(r".*rugcheck\.xyz.*", {"status": 200, "body": json.dumps(rugcheck_response)})
    direct_vm.mock_llm(r".*", json.dumps(leader_llm_result))

    contract = direct_deploy("contracts/meme_rug_auditor.py")
    token_ca = "EKpQGSJtjMFqKZ9KQanSqYXRcF8fBopzLHYxdM65zcjm"
    contract.audit_token(token_ca, request_id="req_consensus_reject_1", payment_amount=1000)

    # Swap the LLM mock to simulate a validator node whose independent
    # re-run diverges sharply on score, verdict AND authority findings.
    divergent_llm_result = dict(leader_llm_result)
    divergent_llm_result.update({
        "safety_score": 15,
        "verdict": "CRITICAL_RUG_RISK",
        "mint_disabled": False,
        "freeze_disabled": False,
    })
    direct_vm.clear_mocks()
    direct_vm.mock_web(r".*dexscreener\.com.*", {"status": 200, "body": json.dumps(dex_response)})
    direct_vm.mock_web(r".*rugcheck\.xyz.*", {"status": 200, "body": json.dumps(rugcheck_response)})
    direct_vm.mock_llm(r".*", json.dumps(divergent_llm_result))

    disagreed = direct_vm.run_validator()
    assert disagreed is False
