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
        "fdv": 2450000000.0,
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

# The same source answering completely: authorities plus every distribution
# metric. Tests that care about the model's verdict surviving intact use this,
# so nothing lands in unverified_fields and neither the LP-burn reclaim nor a
# ceiling deduction moves the score out from under the assertion.
RUGCHECK_FULL_RESPONSE = {
    "token": {"mintAuthority": None, "freezeAuthority": None},
    "risks": [{"name": "High volume volatility"}],
    "score": 92,
    "markets": [{"lp": {"lpBurnedPct": 100}}],
    "topHoldersPct": 18,
    "totalHolders": 185400,
    "topHolders": [
        {"pct": 1.5, "insider": False},
        {"pct": 2.0, "insider": False},
        {"pct": 3.2, "insider": False},
        {"pct": 1.1, "insider": False},
    ],
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


def get_pick_primary_pair(direct_deploy):
    contract = direct_deploy("contracts/meme_rug_auditor.py")
    mod = sys.modules["_contract_meme_rug_auditor"]
    return mod._pick_primary_pair


def dex_pair(symbol, pair_address, fdv, liquidity, volume=5000000.0):
    return {
        "baseToken": {"symbol": symbol, "name": symbol},
        "pairAddress": pair_address,
        "dexId": "raydium",
        "priceUsd": "2.45",
        "fdv": fdv,
        "liquidity": {"usd": liquidity},
        "volume": {"h24": volume},
        "priceChange": {"h24": 12.5},
        "txns": {"h24": {"buys": 1200, "sells": 800}},
    }


def test_primary_pair_is_the_deepest_not_the_first(direct_deploy):
    """DEXScreener lists every pool a mint trades in, in an order it does not
    promise to keep. Depth is what decides where price is really discovered."""
    _pick = get_pick_primary_pair(direct_deploy)
    junk = dex_pair("JUNK", "junk1", 2161.0, 2052.0)
    deep = dex_pair("WIF", "deep1", 2450000000.0, 1500000.0)
    mid = dex_pair("WIF", "mid1", 2450000000.0, 158793.0)

    assert _pick([junk, deep, mid])["pairAddress"] == "deep1"
    assert _pick([deep, junk, mid])["pairAddress"] == "deep1"
    assert _pick([mid, junk, deep])["pairAddress"] == "deep1"


def test_primary_pair_breaks_ties_deterministically(direct_deploy):
    """Equal depth must not leave the choice to input order, or two validators
    sorting the same data differently would audit different pools."""
    _pick = get_pick_primary_pair(direct_deploy)
    a = dex_pair("WIF", "aaa", 1000000.0, 500000.0)
    b = dex_pair("WIF", "bbb", 9000000.0, 500000.0)

    assert _pick([a, b])["pairAddress"] == _pick([b, a])["pairAddress"]


def test_primary_pair_handles_empty_and_malformed(direct_deploy):
    _pick = get_pick_primary_pair(direct_deploy)
    assert _pick(None) is None
    assert _pick([]) is None
    assert _pick(["not a dict", 42]) is None


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


def equiv_result(**overrides):
    """A complete audit result as leader_fn returns it, tweakable per test.

    Every field here is stored in AuditRecord and rendered in the dApp, which is
    the definition of material used by _check_equivalence.
    """
    result = {
        "analysis_source": "llm_consensus",
        "token_symbol": "WIF",
        "safety_score": 85,
        "verdict": "SAFE_TO_TRADE",
        "mint_disabled": True,
        "freeze_disabled": True,
        "lp_burned_pct": 100,
        "top10_holder_pct": 18,
        "holder_count": 185400,
        "smart_money_wallets": 42,
        "unverified_fields": [],
        "scale_tier": "Tier 4 Institutional Bluechip",
        "score_ceiling": 100,
        "risk_factors": ["High volume volatility"],
        "ai_summary": "Leader phrasing.",
    }
    result.update(overrides)
    return result


def test_equivalence_covers_full_result(direct_deploy):
    """Two nodes reporting the same facts agree, even though their prose differs
    — no two LLM rounds write identical sentences, and requiring that would make
    consensus unreachable rather than stricter."""
    _check_equivalence = get_check_equivalence(direct_deploy)
    leader = equiv_result()
    validator = equiv_result(
        safety_score=91,                        # within the 10-point band
        risk_factors=["Volatility, worded differently"],
        ai_summary="Validator phrasing, same findings.",
    )
    assert _check_equivalence(leader, validator) is True


def test_equivalence_tolerates_live_metric_drift(direct_deploy):
    """Nodes fetch seconds apart, so figures move a little. Small drift is not
    disagreement."""
    _check_equivalence = get_check_equivalence(direct_deploy)
    leader = equiv_result()
    validator = equiv_result(
        top10_holder_pct=19,          # 1 point, within PCT_TOLERANCE
        holder_count=189000,          # ~1.9%, within COUNT_REL_TOLERANCE
        smart_money_wallets=43,
    )
    assert _check_equivalence(leader, validator) is True


@pytest.mark.parametrize("field,value", [
    ("lp_burned_pct", 0),             # 100 vs 0: burned or not is not a rounding matter
    ("top10_holder_pct", 44),         # crosses the concentration deduction line
    ("holder_count", 400),            # nowhere near a 5% drift
    ("smart_money_wallets", 2),       # crosses the retail-trap line
    ("scale_tier", "Tier 1 Micro-Cap"),
    ("score_ceiling", 55),
    ("token_symbol", "NOTWIF"),
])
def test_equivalence_rejects_material_divergence(direct_deploy, field, value):
    """Each of these is stored and displayed, so a node disagreeing about one is
    disagreeing about what the user is shown. None of them were checked before:
    a leader could report any value here and no validator would object."""
    _check_equivalence = get_check_equivalence(direct_deploy)
    assert _check_equivalence(equiv_result(), equiv_result(**{field: value})) is False


def test_equivalence_rejects_unverified_field_mismatch(direct_deploy):
    """unverified_fields is what tells a reader whether a stored 0 was measured
    or merely unknown. Two nodes that disagree about what they could verify have
    not reached the same audit, even when every number matches."""
    _check_equivalence = get_check_equivalence(direct_deploy)
    leader = equiv_result(lp_burned_pct=0, unverified_fields=["lp_burned_pct"])
    validator = equiv_result(lp_burned_pct=0, unverified_fields=[])
    assert _check_equivalence(leader, validator) is False


def test_equivalence_ignores_unverified_field_ordering(direct_deploy):
    """Order is an artifact of iteration, not a finding."""
    _check_equivalence = get_check_equivalence(direct_deploy)
    leader = equiv_result(unverified_fields=["lp_burned_pct", "holder_count"])
    validator = equiv_result(unverified_fields=["holder_count", "lp_burned_pct"])
    assert _check_equivalence(leader, validator) is True


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

    mock_live_sources(direct_vm)
    direct_vm.mock_llm(r".*", json.dumps(mock_llm_result))

    contract = direct_deploy("contracts/meme_rug_auditor.py")
    token_ca = "EKpQGSJtjMFqKZ9KQanSqYXRcF8fBopzLHYxdM65zcjm"

    # Audit token
    contract.audit_token(token_ca)

    report = contract.get_audit(token_ca)
    assert report["has_audit"] is True
    assert report["token_address"] == token_ca
    assert report["token_symbol"] == "WIF"
    # RUGCHECK_RESPONSE carries authority flags but no markets/holders block, so
    # the distribution metrics have no evidence behind them. The model's
    # lp_burned_pct 100 and top10_holder_pct 18 are therefore discarded, and the
    # rubric's +5 "LP burned >= 95%" bonus is taken back off its 92.
    assert report["safety_score"] == 87
    assert report["verdict"] == "SAFE_TO_TRADE"
    assert report["mint_disabled"] is True
    assert report["freeze_disabled"] is True
    assert report["lp_burned_pct"] == 0
    assert report["top10_holder_pct"] == 0
    assert set(report["unverified_fields"]) == {
        "lp_burned_pct", "top10_holder_pct", "holder_count", "smart_money_wallets"
    }

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

    Fetched evidence with revoked authorities and $1.5M liquidity is about as
    strong as this rubric gets, yet the model returns 63/HIGH_VOLATILITY_WARN
    and that is exactly what lands on chain — the number and the wording both
    come from the model, not from anything the contract could have computed.
    """
    direct_vm.sender = direct_alice
    mock_live_sources(direct_vm, rugcheck=RUGCHECK_FULL_RESPONSE)
    direct_vm.mock_llm(r".*", llm_verdict(
        safety_score=63,
        verdict="HIGH_VOLATILITY_WARN",
        risk_factors=["Model-flagged momentum exhaustion after parabolic run"],
        ai_summary="Model brief: elevated volatility despite deep liquidity.",
    ))

    contract = direct_deploy(CONTRACT)
    contract.audit_token(WIF_CA, request_id="req_llm_drives_1", payment_amount=1000)

    report = contract.get_audit(WIF_CA)
    assert report["analysis_source"] == "llm_consensus"
    assert report["safety_score"] == 63
    assert report["verdict"] == "HIGH_VOLATILITY_WARN"
    assert "momentum exhaustion" in report["risk_factors"][0]
    assert report["ai_summary"] == "Model brief: elevated volatility despite deep liquidity."


def test_evidence_backed_metrics_are_kept(direct_vm, direct_deploy, direct_alice):
    """When RugCheck really reports LP burn and holder data, those figures are
    stored, nothing is marked unverified, and the LP bonus stands."""
    direct_vm.sender = direct_alice
    mock_live_sources(direct_vm, rugcheck={
        "token": {"mintAuthority": None, "freezeAuthority": None},
        "risks": [],
        "score": 92,
        "markets": [{"lp": {"lpBurnedPct": 97}}],
        "topHoldersPct": 21,
        "totalHolders": 185400,
        "topHolders": [
            {"pct": 1.5, "insider": False},   # counts as smart money
            {"pct": 2.0, "insider": False},   # counts
            {"pct": 3.2, "insider": False},   # counts — keeps the count >= 3 so
                                              # the ceiling's "retail trap" rule
                                              # does not fire and muddy this test
            {"pct": 8.0, "insider": False},   # too large
            {"pct": 0.1, "insider": False},   # too small
            {"pct": 1.0, "insider": True},    # insider
        ],
    })
    direct_vm.mock_llm(r".*", llm_verdict(
        safety_score=92, lp_burned_pct=100, top10_holder_pct=18,
        holder_count=1, smart_money_wallets=1,
    ))

    contract = direct_deploy(CONTRACT)
    contract.audit_token(WIF_CA, request_id="req_evidence_1", payment_amount=1000)

    report = contract.get_audit(WIF_CA)
    assert report["unverified_fields"] == []
    assert report["safety_score"] == 92          # bonus kept: LP burn is real
    assert report["lp_burned_pct"] == 97         # RugCheck value, not the model's 100
    assert report["top10_holder_pct"] == 21      # RugCheck value, not the model's 18
    assert report["holder_count"] == 185400      # model said 1
    assert report["smart_money_wallets"] == 3    # counted from topHolders, model said 1
    assert report["scale_tier"] == "Tier 4 Institutional Bluechip"
    assert report["score_ceiling"] == 100


def test_micro_cap_cannot_exceed_tier_ceiling(direct_vm, direct_deploy, direct_alice):
    """The advertised guarantee: a micro-cap is capped at 55 no matter how
    generously the model scores it. Nothing enforced this before."""
    direct_vm.sender = direct_alice
    mock_live_sources(direct_vm, dex={
        "pairs": [{
            "baseToken": {"symbol": "SCAM", "name": "Scam Coin"},
            "dexId": "raydium",
            "priceUsd": "0.00001",
            "fdv": 42000.0,             # well under the $100k Tier 1 line
            "liquidity": {"usd": 9000.0},
            "volume": {"h24": 5000.0},
            "priceChange": {"h24": -12.0},
            "txns": {"h24": {"buys": 10, "sells": 40}},
        }]
    })
    direct_vm.mock_llm(r".*", llm_verdict(safety_score=100, verdict="SAFE_TO_TRADE"))

    contract = direct_deploy(CONTRACT)
    contract.audit_token(WIF_CA, request_id="req_microcap_ceiling_1", payment_amount=1000)

    report = contract.get_audit(WIF_CA)
    assert report["scale_tier"] == "Tier 1 Micro-Cap"
    assert report["score_ceiling"] == 55
    assert report["safety_score"] == 55          # model's 100 does not survive
    assert report["verdict"] == "HIGH_VOLATILITY_WARN"
    assert any("Score capped at 55" in r for r in report["risk_factors"])


def test_tier_is_read_from_the_deepest_pool(direct_vm, direct_deploy, direct_alice):
    """A junk pool listed first must not decide the token's scale tier.

    Observed live: one mint returned 25 pairs whose FDV ranged from $40 to
    $4.36M. Reading pairs[0] meant whichever pool DEXScreener happened to list
    first set the ceiling, so the same token could be audited as a Tier 4
    bluechip or a Tier 1 micro-cap depending on response ordering. Here the
    leading pool would give Tier 1 / ceiling 55; the deepest gives Tier 4."""
    direct_vm.sender = direct_alice
    mock_live_sources(direct_vm, dex={"pairs": [
        dex_pair("WIF", "junk_first", 2161.0, 2052.0, volume=20304.0),
        dex_pair("WIF", "deepest", 2450000000.0, 1500000.0, volume=5000000.0),
        dex_pair("WIF", "shallow", 2450000000.0, 8750.0, volume=93476.0),
    ]}, rugcheck=RUGCHECK_FULL_RESPONSE)
    direct_vm.mock_llm(r".*", llm_verdict(safety_score=92, verdict="SAFE_TO_TRADE"))

    contract = direct_deploy(CONTRACT)
    contract.audit_token(WIF_CA, request_id="req_deepest_pool_1", payment_amount=1000)

    report = contract.get_audit(WIF_CA)
    assert report["scale_tier"] == "Tier 4 Institutional Bluechip"
    assert report["score_ceiling"] == 100
    assert report["safety_score"] == 92          # not capped to 55 by the junk pool


def test_wash_trading_turnover_lowers_the_ceiling(direct_vm, direct_deploy, direct_alice):
    """The slippage shield the dApp advertises, now enforced.

    These are the live figures from a token that scored 75/100 while turning
    over 138x its own depth in a day: $16.1M of volume against $116.7k of
    liquidity. Nothing in the contract deducted for that."""
    direct_vm.sender = direct_alice
    mock_live_sources(direct_vm, dex={"pairs": [
        dex_pair("PLUMB", "pumpswap", 1244638.0, 116699.0, volume=16155894.0),
    ]}, rugcheck=RUGCHECK_FULL_RESPONSE)
    direct_vm.mock_llm(r".*", llm_verdict(safety_score=75, verdict="HIGH_VOLATILITY_WARN"))

    contract = direct_deploy(CONTRACT)
    contract.audit_token(WIF_CA, request_id="req_turnover_1", payment_amount=1000)

    report = contract.get_audit(WIF_CA)
    assert report["scale_tier"] == "Tier 3 Mid-Cap"
    assert report["score_ceiling"] == 58         # 88 tier cap - 30 for 138x turnover
    assert report["safety_score"] == 58          # the model's 75 does not survive
    assert any("138x liquidity" in r for r in report["risk_factors"])


def test_healthy_turnover_is_not_punished(direct_vm, direct_deploy, direct_alice):
    """A book trading a few times its depth is normal activity, not a signal."""
    direct_vm.sender = direct_alice
    mock_live_sources(direct_vm, dex={"pairs": [
        dex_pair("WIF", "healthy", 2450000000.0, 1500000.0, volume=5000000.0),
    ]}, rugcheck=RUGCHECK_FULL_RESPONSE)          # 3.3x turnover
    direct_vm.mock_llm(r".*", llm_verdict(safety_score=92, verdict="SAFE_TO_TRADE"))

    contract = direct_deploy(CONTRACT)
    contract.audit_token(WIF_CA, request_id="req_healthy_turnover_1", payment_amount=1000)

    report = contract.get_audit(WIF_CA)
    assert report["score_ceiling"] == 100
    assert report["safety_score"] == 92
    assert not any("liquidity" in r and "x liquidity" in r for r in report["risk_factors"])


def test_verified_deductions_lower_the_ceiling(direct_vm, direct_deploy, direct_alice):
    """Deductions the rubric makes mandatory come off the ceiling when the
    evidence backs them — here a top-10 concentration RugCheck measured."""
    direct_vm.sender = direct_alice
    mock_live_sources(direct_vm, rugcheck={
        "token": {"mintAuthority": None, "freezeAuthority": None},
        "risks": [],
        "score": 90,
        "markets": [{"lp": {"lpBurnedPct": 100}}],
        "topHoldersPct": 44,                       # > 40% -> mandatory -25
        "totalHolders": 500000,
        "topHolders": [
            {"pct": 1.0, "insider": False},
            {"pct": 2.0, "insider": False},
            {"pct": 3.0, "insider": False},
        ],
    })
    direct_vm.mock_llm(r".*", llm_verdict(safety_score=100, verdict="SAFE_TO_TRADE"))

    contract = direct_deploy(CONTRACT)
    contract.audit_token(WIF_CA, request_id="req_ceiling_deduction_1", payment_amount=1000)

    report = contract.get_audit(WIF_CA)
    assert report["scale_tier"] == "Tier 4 Institutional Bluechip"
    assert report["score_ceiling"] == 75          # 100 tier cap - 25 concentration
    assert report["safety_score"] == 75
    assert report["verdict"] == "HIGH_VOLATILITY_WARN"


def test_unverified_metrics_never_deduct(direct_vm, direct_deploy, direct_alice):
    """A stored 0 that means "nobody measured this" must not be punished as if
    it meant 0% burned or 0 holders — that would invent a finding."""
    direct_vm.sender = direct_alice
    mock_live_sources(direct_vm, rugcheck={
        "token": {"mintAuthority": None, "freezeAuthority": None},
        "risks": [], "score": 90,
        # no markets / topHolders / totalHolders at all
    })
    direct_vm.mock_llm(r".*", llm_verdict(safety_score=90, verdict="SAFE_TO_TRADE",
                                          lp_burned_pct=0))

    contract = direct_deploy(CONTRACT)
    contract.audit_token(WIF_CA, request_id="req_unverified_no_deduct_1", payment_amount=1000)

    report = contract.get_audit(WIF_CA)
    assert set(report["unverified_fields"]) == {
        "lp_burned_pct", "top10_holder_pct", "holder_count", "smart_money_wallets"
    }
    assert report["score_ceiling"] == 100   # nothing verified, so nothing deducted
    assert report["safety_score"] == 90     # the model's judgement stands


def test_audit_reverts_without_market_cap(direct_vm, direct_deploy, direct_alice):
    """Without a market cap there is no verifiable scale tier, and guessing one
    would classify a bluechip as a micro-cap or vice versa."""
    direct_vm.sender = direct_alice
    mock_live_sources(direct_vm, dex={
        "pairs": [{
            "baseToken": {"symbol": "WIF", "name": "Dogwifhat"},
            "dexId": "raydium",
            "priceUsd": "2.45",
            "liquidity": {"usd": 1500000.0},   # liquidity but no fdv
            "volume": {"h24": 5000000.0},
            "txns": {"h24": {"buys": 1200, "sells": 800}},
        }]
    })
    direct_vm.mock_llm(r".*", llm_verdict())

    contract = direct_deploy(CONTRACT)
    with pytest.raises(Exception, match="no market capitalisation"):
        contract.audit_token(WIF_CA, request_id="req_no_fdv_1", payment_amount=1000)

    assert contract.get_audit(WIF_CA)["has_audit"] is False


def test_caller_telemetry_is_never_evidence(direct_vm, direct_deploy, direct_alice):
    """telemetry_json carries no evidentiary weight, even where it is the only
    thing offering a figure.

    A caller who could fill gaps left by an incomplete upstream response would
    be deciding the audit: authority flags force the verdict and market size
    sets the ceiling. Validator agreement would not catch it either, since every
    node reads the same payload from the same calldata and agrees on it
    perfectly. Here RugCheck reports a live mint authority and 12% LP burn while
    the payload asserts the flattering opposite, and the payload changes
    nothing."""
    direct_vm.sender = direct_alice
    mock_live_sources(direct_vm, rugcheck={
        "token": {"mintAuthority": "SomeMintAuthorityPubkey", "freezeAuthority": None},
        "risks": [],
        "score": 30,
        "markets": [{"lp": {"lpBurnedPct": 12}}],
    })
    direct_vm.mock_llm(r".*", llm_verdict(safety_score=95, verdict="SAFE_TO_TRADE"))

    lying_telemetry = json.dumps({
        "token_symbol": "WIF",
        "fdv_usd": 2450000000.0,
        "liquidity_usd": 15420000.0,
        "txns_24h_buys": 14200,
        "txns_24h_sells": 11800,
        "mint_disabled": True,     # false: RugCheck reports a live mint authority
        "freeze_disabled": True,
        "lp_burned_pct": 100,      # false: RugCheck reports 12%
    })

    contract = direct_deploy(CONTRACT)
    contract.audit_token(WIF_CA, request_id="req_lying_telemetry_1", payment_amount=1000,
                         telemetry_json=lying_telemetry)

    report = contract.get_audit(WIF_CA)
    assert report["mint_disabled"] is False          # fetched evidence, not the payload
    assert report["lp_burned_pct"] == 12             # RugCheck's 12%, not the claimed 100
    assert report["verdict"] == "CRITICAL_RUG_RISK"  # forced by the live authority
    assert report["safety_score"] <= 49


def test_telemetry_cannot_supply_missing_authority(direct_vm, direct_deploy, direct_alice):
    """The gap-filling case specifically: RugCheck answers with nothing, and a
    payload asserting revoked authorities does not rescue the audit. Before,
    this stored a clean bill of health sourced entirely from the caller."""
    direct_vm.sender = direct_alice
    mock_live_sources(direct_vm, rugcheck={})     # upstream returns no authority data
    direct_vm.mock_llm(r".*", llm_verdict())

    generous_telemetry = json.dumps({
        "token_symbol": "WIF",
        "mint_disabled": True,
        "freeze_disabled": True,
        "lp_burned_pct": 100,
        "holder_count": 185400,
        "smart_money_wallets": 42,
    })

    contract = direct_deploy(CONTRACT)
    with pytest.raises(Exception, match="authority status unavailable"):
        contract.audit_token(WIF_CA, request_id="req_tele_gapfill_1", payment_amount=1000,
                             telemetry_json=generous_telemetry)

    assert contract.get_audit(WIF_CA)["has_audit"] is False


def test_telemetry_cannot_supply_missing_market_size(direct_vm, direct_deploy, direct_alice):
    """Market cap and liquidity set the scale-tier ceiling, so a payload that
    supplies them would be buying its own ceiling. DEXScreener returning no
    pairs reverts regardless of what the caller claims the token is worth."""
    direct_vm.sender = direct_alice
    mock_live_sources(direct_vm, dex={"pairs": []})
    direct_vm.mock_llm(r".*", llm_verdict())

    bluechip_claim = json.dumps({
        "token_symbol": "WIF",
        "fdv_usd": 2450000000.0,      # would buy a Tier 4 ceiling of 100
        "liquidity_usd": 15420000.0,
        "mint_disabled": True,
        "freeze_disabled": True,
    })

    contract = direct_deploy(CONTRACT)
    with pytest.raises(Exception, match="no live market data"):
        contract.audit_token(WIF_CA, request_id="req_tele_market_1", payment_amount=1000,
                             telemetry_json=bluechip_claim)

    assert contract.get_audit(WIF_CA)["has_audit"] is False


def test_unbacked_lp_burn_claim_is_stripped(direct_vm, direct_deploy, direct_alice):
    """A model that claims a fully burned LP with nothing backing it loses both
    the number and the bonus the rubric grants for it."""
    direct_vm.sender = direct_alice
    mock_live_sources(direct_vm, rugcheck={
        "token": {"mintAuthority": None, "freezeAuthority": None},
        "risks": [],
        "score": 90,
    })
    direct_vm.mock_llm(r".*", llm_verdict(safety_score=90, lp_burned_pct=100))

    contract = direct_deploy(CONTRACT)
    contract.audit_token(WIF_CA, request_id="req_unbacked_lp_1", payment_amount=1000)

    report = contract.get_audit(WIF_CA)
    assert report["lp_burned_pct"] == 0
    assert "lp_burned_pct" in report["unverified_fields"]
    assert report["safety_score"] == 85  # 90 minus the reclaimed +5
    assert any("LP Burn Unverified" in r for r in report["risk_factors"])


def test_modest_lp_claim_keeps_score(direct_vm, direct_deploy, direct_alice):
    """Only the >= 95% bonus is reclaimed. A model reporting an unbacked but
    unremarkable LP figure loses the number, not points it never gained."""
    direct_vm.sender = direct_alice
    mock_live_sources(direct_vm, rugcheck={
        "token": {"mintAuthority": None, "freezeAuthority": None},
        "risks": [], "score": 70,
    })
    direct_vm.mock_llm(r".*", llm_verdict(
        safety_score=70, verdict="HIGH_VOLATILITY_WARN", lp_burned_pct=60,
    ))

    contract = direct_deploy(CONTRACT)
    contract.audit_token(WIF_CA, request_id="req_modest_lp_1", payment_amount=1000)

    report = contract.get_audit(WIF_CA)
    assert report["lp_burned_pct"] == 0
    assert report["safety_score"] == 70  # untouched


def test_audit_reverts_when_llm_round_unavailable(direct_vm, direct_deploy, direct_alice):
    """No model, no report. There is no local scoring path to fall back on, so
    the transaction reverts rather than storing a fabricated audit."""
    direct_vm.sender = direct_alice
    mock_live_sources(direct_vm)          # market and authority evidence are fine
    contract = direct_deploy(CONTRACT)

    with pytest.raises(Exception, match="LLM consensus round unavailable"):
        contract.audit_token(WIF_CA, request_id="req_llm_missing_1", payment_amount=1000)

    assert contract.get_audit(WIF_CA)["has_audit"] is False


def test_audit_reverts_on_malformed_llm_response(direct_vm, direct_deploy, direct_alice):
    """A reply that breaks the schema or leaves the valid range is untrusted,
    and an untrusted reply aborts the audit instead of being stored."""
    direct_vm.sender = direct_alice
    mock_live_sources(direct_vm)
    direct_vm.mock_llm(r".*", json.dumps({
        "token_symbol": "WIF",
        "safety_score": 420,               # out of the 0-100 range
        "verdict": "DEFINITELY_FINE",      # not an allowed verdict
        "ai_summary": "",
    }))

    contract = direct_deploy(CONTRACT)
    with pytest.raises(Exception, match="LLM_ERROR"):
        contract.audit_token(WIF_CA, request_id="req_llm_malformed_1", payment_amount=1000)

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
    mock_live_sources(direct_vm, rugcheck=RUGCHECK_FULL_RESPONSE)
    direct_vm.mock_llm(r".*", llm_verdict(
        token_symbol=symbol, safety_score=score, verdict=verdict,
        ai_summary=f"{symbol} brief at {score}/100.",
    ))

    contract = direct_deploy(CONTRACT)
    contract.audit_token(WIF_CA, request_id=f"req_tier_{symbol}", payment_amount=1000)

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
    with pytest.raises(Exception, match="authority status unavailable"):
        contract.audit_token(WIF_CA, request_id="req_no_authority_1", payment_amount=1000)

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
        "mint_disabled": True,      # model contradicts the fetched evidence below
        "freeze_disabled": True,
        "lp_burned_pct": 100,
        "top10_holder_pct": 18,
        "risk_factors": [],
        "ai_summary": "Model brief claiming a clean bill of health.",
    }))

    # The live mint authority is a hard on-chain fact, read from RugCheck.
    mock_live_sources(direct_vm, rugcheck={
        "token": {"mintAuthority": "SomeMintAuthorityPubkey", "freezeAuthority": None},
        "risks": [],
        "score": 30,
    })

    contract = direct_deploy("contracts/meme_rug_auditor.py")
    contract.audit_token(WIF_CA, request_id="req_authority_override_1", payment_amount=1000)

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
    mock_live_sources(direct_vm)
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
    mock_live_sources(direct_vm)
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
    mock_live_sources(direct_vm)
    direct_vm.mock_llm(r".*", json.dumps(divergent_llm_result))

    disagreed = direct_vm.run_validator()
    assert disagreed is False


def test_validator_rejects_divergent_distribution_metrics(direct_vm, direct_deploy, direct_alice):
    """The gap the widened equivalence closes, isolated.

    The divergence here is chosen so that everything the OLD check compared
    stays identical: both nodes report 92/SAFE_TO_TRADE with both authorities
    revoked, and because 185,400 and 150,000 holders are both far above the
    200-holder deduction line, the tier, the ceiling and the final score come
    out the same on each. The old check would have called this equivalent and
    stored the leader's holder count unchallenged.

    It is not equivalent. holder_count is written to AuditRecord and rendered in
    the dApp, and the two nodes disagree about it by 19%."""
    direct_vm.sender = direct_alice
    mock_live_sources(direct_vm, rugcheck=RUGCHECK_FULL_RESPONSE)
    direct_vm.mock_llm(r".*", llm_verdict(safety_score=92, verdict="SAFE_TO_TRADE"))

    contract = direct_deploy(CONTRACT)
    contract.audit_token(WIF_CA, request_id="req_metric_divergence_1", payment_amount=1000)

    stored = contract.get_audit(WIF_CA)
    assert stored["holder_count"] == 185400
    assert stored["safety_score"] == 92
    assert stored["score_ceiling"] == 100

    # The validator's independent re-run reads a different holder count, and
    # nothing else changes: same LP burn, same concentration, same authorities.
    divergent = dict(RUGCHECK_FULL_RESPONSE)
    divergent["totalHolders"] = 150000
    direct_vm.clear_mocks()
    mock_live_sources(direct_vm, rugcheck=divergent)
    direct_vm.mock_llm(r".*", llm_verdict(safety_score=92, verdict="SAFE_TO_TRADE"))

    assert direct_vm.run_validator() is False
