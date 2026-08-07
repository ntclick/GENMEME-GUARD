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


def test_run_live_demo_audit(direct_deploy):
    print("\n" + "=" * 65)
    print(" GENMEME GUARD -- RUNNING LOCAL GENVM SIMULATOR AUDIT DEMO")
    print("=" * 65)
    contract = direct_deploy("contracts/meme_rug_auditor.py")
    wif_ca = "EKpQGSJtjMFqKZ9KQanSqYXRcF8fBopzLHYxdM65zcjm"

    wif_telemetry = json.dumps({
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

    print(f"[*] Executing audit_token for WIF ({wif_ca})...")
    contract.audit_token(wif_ca, request_id="req_pytest_wif_demo_1", payment_amount=1000, telemetry_json=wif_telemetry)

    report = contract.get_audit(wif_ca)
    print("\n" + "=" * 65)
    print(" ON-CHAIN AUDIT CONSENSUS RESULT:")
    print("=" * 65)
    print(json.dumps(report, indent=2))
    print("=" * 65)
    print(f"Safety Score:   {report.get('safety_score')}/100")
    print(f"Threat Verdict:  {report.get('verdict')}")
    print(f"Mint Revoked:   {report.get('mint_disabled')}")
    print(f"Freeze Revoked: {report.get('freeze_disabled')}")
    print(f"AI Summary:     {report.get('ai_summary')}")
    print("=" * 65 + "\n")
    assert report["has_audit"] is True
    assert report["safety_score"] == 100
    assert report["verdict"] == "SAFE_TO_TRADE"


def test_run_sgl_token_audit(direct_deploy):
    print("\n" + "=" * 65)
    print(" GENMEME GUARD -- RUNNING AUDIT FOR SGL TOKEN (5c4HyD...)")
    print("=" * 65)
    contract = direct_deploy("contracts/meme_rug_auditor.py")
    sgl_ca = "5c4HyD2rSShqnTsf5z3SaoD2H3GE452u2CUuYjviBAGS"

    sgl_telemetry = json.dumps({
        "token_symbol": "SGL",
        "token_name": "Solana GenLayer",
        "price_usd": "0.15",
        "market_cap_usd": 15000000.0,
        "fdv_usd": 15000000.0,
        "liquidity_usd": 1250000.0,
        "volume_24h_usd": 3400000.0,
        "price_change_24h_pct": 12.4,
        "txns_24h_buys": 3200,
        "txns_24h_sells": 2100,
        "holder_count": 24500,
        "smart_money_wallets": 28,
        "top10_holder_pct": 22,
        "mint_disabled": True,
        "freeze_disabled": True,
        "lp_burned_pct": 100,
        "detected_risks": []
    })

    print(f"[*] Executing audit_token for SGL ({sgl_ca})...")
    contract.audit_token(sgl_ca, request_id="req_pytest_sgl_demo_1", payment_amount=1000, telemetry_json=sgl_telemetry)

    report = contract.get_audit(sgl_ca)
    print("\n" + "=" * 65)
    print(" SGL TOKEN ON-CHAIN AUDIT CONSENSUS RESULT:")
    print("=" * 65)
    print(json.dumps(report, indent=2))
    print("=" * 65)
    print(f"Safety Score:   {report.get('safety_score')}/100")
    print(f"Threat Verdict:  {report.get('verdict')}")
    print(f"Mint Revoked:   {report.get('mint_disabled')}")
    print(f"Freeze Revoked: {report.get('freeze_disabled')}")
    print(f"AI Summary:     {report.get('ai_summary')}")
    print("=" * 65 + "\n")
    assert report["has_audit"] is True
    assert report["token_address"] == sgl_ca
    assert report["token_symbol"] == "SGL"
    assert report["verdict"] == "SAFE_TO_TRADE"


def test_run_micro_cap_scam_audit(direct_deploy):
    print("\n" + "=" * 65)
    print(" GENMEME GUARD -- AUDIT TEST FOR MICRO-CAP RUG SCAM COIN")
    print("=" * 65)
    contract = direct_deploy("contracts/meme_rug_auditor.py")
    scam_ca = "ScamPUMP11111111111111111111111111111111111111"

    scam_telemetry = json.dumps({
        "token_symbol": "PUMP_SCAM",
        "token_name": "Pump Dump Rug Coin",
        "price_usd": "0.000012",
        "market_cap_usd": 12000.0,
        "fdv_usd": 12000.0,
        "liquidity_usd": 2500.0,
        "volume_24h_usd": 85000.0,
        "price_change_24h_pct": -45.2,
        "txns_24h_buys": 120,
        "txns_24h_sells": 890,
        "holder_count": 85,
        "smart_money_wallets": 1,
        "top10_holder_pct": 78,
        "mint_disabled": False,  # Active Mint Authority!
        "freeze_disabled": False, # Active Freeze Authority!
        "lp_burned_pct": 15,     # Unlocked LP!
        "detected_risks": ["Active Mint Authority", "Active Freeze Authority", "Unlocked Liquidity"]
    })

    contract.audit_token(scam_ca, request_id="req_pytest_scam_1", payment_amount=1000, telemetry_json=scam_telemetry)
    report = contract.get_audit(scam_ca)
    print(json.dumps(report, indent=2))
    print("=" * 65)
    print(f"Safety Score:   {report.get('safety_score')}/100")
    print(f"Threat Verdict:  {report.get('verdict')}")
    print("=" * 65 + "\n")
    assert report["has_audit"] is True
    assert report["safety_score"] == 0  # DYNAMICALLY SCORED AT 0/100!
    assert report["verdict"] == "CRITICAL_RUG_RISK"
    assert report["mint_disabled"] is False
    assert report["freeze_disabled"] is False


def test_run_small_cap_speculative_audit(direct_deploy):
    print("\n" + "=" * 65)
    print(" GENMEME GUARD -- AUDIT TEST FOR SMALL-CAP SPECULATIVE COIN")
    print("=" * 65)
    contract = direct_deploy("contracts/meme_rug_auditor.py")
    small_ca = "SmallCap444444444444444444444444444444444444"

    small_telemetry = json.dumps({
        "token_symbol": "MID_CAP",
        "token_name": "Speculative Meme Coin",
        "price_usd": "0.045",
        "market_cap_usd": 450000.0,
        "fdv_usd": 450000.0,
        "liquidity_usd": 45000.0,
        "volume_24h_usd": 120000.0,
        "price_change_24h_pct": -8.5,
        "txns_24h_buys": 450,
        "txns_24h_sells": 520,
        "holder_count": 850,
        "smart_money_wallets": 4,
        "top10_holder_pct": 28,
        "mint_disabled": True,
        "freeze_disabled": True,
        "lp_burned_pct": 100,
        "detected_risks": []
    })

    contract.audit_token(small_ca, request_id="req_pytest_small_1", payment_amount=1000, telemetry_json=small_telemetry)
    report = contract.get_audit(small_ca)
    print(json.dumps(report, indent=2))
    print("=" * 65)
    print(f"Safety Score:   {report.get('safety_score')}/100")
    print(f"Threat Verdict:  {report.get('verdict')}")
    print("=" * 65 + "\n")
    assert report["has_audit"] is True
    assert report["safety_score"] == 30  # DYNAMICALLY SCORED AT 30/100 (CAPPED AT TIER 2 & PENALIZED FOR DUMP PRESSURE)!
    assert report["verdict"] == "CRITICAL_RUG_RISK"
