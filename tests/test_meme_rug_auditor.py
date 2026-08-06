import json
import sys
import pytest


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

    mock_llm_result = {
        "token_address": "EKpQGSJtjMFqKZ9KQanSqYXRcF8fBopzLHYxdM65zcjm",
        "token_symbol": "WIF",
        "safety_score": 90,
        "verdict": "SAFE_TO_TRADE",
        "mint_disabled": True,
        "freeze_disabled": True,
        "lp_burned_pct": 100,
        "top10_holder_pct": 20,
        "risk_factors": [],
        "ai_summary": "Clean token audit.",
    }
    direct_vm.mock_web(r".*", {"status": 200, "body": "{}"})
    direct_vm.mock_llm(r".*", json.dumps(mock_llm_result))

    contract = direct_deploy("contracts/meme_rug_auditor.py")
    token_ca = "EKpQGSJtjMFqKZ9KQanSqYXRcF8fBopzLHYxdM65zcjm"

    # First request succeeds
    contract.audit_token(token_ca, request_id="unique_req_101", payment_amount=1000)

    # Replay request with exact same request_id must be rejected
    with pytest.raises(Exception, match="Replay attack detected"):
        contract.audit_token(token_ca, request_id="unique_req_101", payment_amount=1000)


def test_request_id_mismatch_authorization(direct_vm, direct_deploy, direct_alice, direct_bob):
    direct_vm.sender = direct_alice

    mock_llm_result = {
        "token_address": "5c4HyD2rSShqnTsf5z3SaoD2H3GE452u2CUuYjviBAGS",
        "token_symbol": "SGL",
        "safety_score": 85,
        "verdict": "SAFE_TO_TRADE",
        "mint_disabled": True,
        "freeze_disabled": True,
        "lp_burned_pct": 100,
        "top10_holder_pct": 15,
        "risk_factors": [],
        "ai_summary": "SGL audit completed for Alice.",
    }
    direct_vm.mock_web(r".*", {"status": 200, "body": "{}"})
    direct_vm.mock_llm(r".*", json.dumps(mock_llm_result))

    contract = direct_deploy("contracts/meme_rug_auditor.py")
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
