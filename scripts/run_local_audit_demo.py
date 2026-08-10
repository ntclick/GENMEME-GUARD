"""
GenMeme Guard - Local GenVM Live Audit Runner

Runs audit_token / get_audit under the GenVM direct-execution engine and
prints the provenance of each verdict, so it is visible whether a report came
from the on-chain LLM consensus round or from the deterministic fallback.
"""

import json
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO_ROOT / "tests"))

from conftest import _patch_windows_fd0_injection  # noqa: E402  (Windows temp-file workaround)

_patch_windows_fd0_injection()

from gltest.direct import VMContext, deploy_contract, create_address  # noqa: E402

CONTRACT = REPO_ROOT / "contracts" / "meme_rug_auditor.py"
WIF_CA = "EKpQGSJtjMFqKZ9KQanSqYXRcF8fBopzLHYxdM65zcjm"

WIF_TELEMETRY = json.dumps({
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

# What a validator node's LLM returns for this token during the consensus round.
LLM_VERDICT = json.dumps({
    "token_address": WIF_CA,
    "token_symbol": "WIF",
    "safety_score": 63,
    "verdict": "HIGH_VOLATILITY_WARN",
    "mint_disabled": True,
    "freeze_disabled": True,
    "lp_burned_pct": 100,
    "top10_holder_pct": 18,
    "holder_count": 185400,
    "smart_money_wallets": 42,
    "risk_factors": ["Momentum exhaustion after parabolic run"],
    "ai_summary": (
        "Tier 4 Institutional Bluechip with deep liquidity but stretched momentum. "
        "Market Cap $2,450,000,000, Liquidity $15,420,000, 185,400 holders, 42 smart money wallets. "
        "Mint and freeze authorities are revoked and LP is 100% burned. "
        "Orderbook shows 14,200 buys against 11,800 sells with a +5.2% 24h trajectory."
    ),
})


def _print_report(title, report):
    print("\n" + "=" * 68)
    print(f" {title}")
    print("=" * 68)
    print(json.dumps(report, indent=2))
    print("-" * 68)
    print(f"Analysis Source: {report.get('analysis_source')}")
    print(f"LLM Error:       {report.get('llm_error') or '(none)'}")
    print(f"Safety Score:    {report.get('safety_score')}/100")
    print(f"Threat Verdict:  {report.get('verdict')}")
    print(f"Mint Revoked:    {report.get('mint_disabled')}")
    print(f"Freeze Revoked:  {report.get('freeze_disabled')}")
    print("=" * 68)


def run_audit(label, request_id, llm_response=None):
    vm = VMContext()
    vm.sender = create_address("demo_caller")
    with vm.activate():
        if llm_response is not None:
            vm.mock_llm(r".*", llm_response)
        contract = deploy_contract(CONTRACT, vm)
        contract.audit_token(
            WIF_CA,
            request_id=request_id,
            payment_amount=1000,
            telemetry_json=WIF_TELEMETRY,
        )
        _print_report(label, contract.get_audit(WIF_CA))


def main():
    print("=" * 68)
    print(" GENMEME GUARD -- LOCAL GENVM LIVE AUDIT RUNNER")
    print("=" * 68)

    # The consensus round reaches the LLM: its verdict is what gets stored.
    run_audit(
        "AUDIT WITH LLM CONSENSUS ROUND AVAILABLE",
        "req_demo_wif_llm",
        llm_response=LLM_VERDICT,
    )

    # No LLM reachable: the report falls back to local scoring and says so,
    # rather than passing local arithmetic off as a consensus verdict.
    run_audit(
        "AUDIT WITH LLM ROUND UNAVAILABLE (FALLBACK, TAGGED)",
        "req_demo_wif_fallback",
    )


if __name__ == "__main__":
    main()
