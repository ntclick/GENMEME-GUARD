"""
GenMeme Guard - Local GenVM Simulator Live Audit Runner
Runs contract audit_token & get_audit under GenVM local consensus engine
"""

import json
from genlayer_test.direct import DirectContract

def main():
    print("=" * 65)
    print(" GENMEME GUARD -- LOCAL GENVM SIMULATOR LIVE AUDIT RUNNER")
    print("=" * 65)

    # 1. Initialize Contract in GenVM Simulator
    contract = DirectContract("contracts/meme_rug_auditor.py")
    print("[+] Contract Initialized in GenVM Simulator!")

    # 2. Define Sample Tokens
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

    print(f"[*] Triggering audit_token for WIF ({wif_ca})...")
    res_raw = contract.audit_token(
        token_address=wif_ca,
        request_id="req_demo_wif_1",
        payment_amount=1000,
        telemetry_json=wif_telemetry
    )
    print(f"[+] audit_token execution result: {res_raw}")

    print("\n" + "=" * 65)
    print(" READING FINAL ON-CHAIN AUDIT REPORT VIA get_audit()...")
    print("=" * 65)
    report = contract.get_audit(token_address=wif_ca)
    print(json.dumps(report, indent=2))
    print("=" * 65)
    print(f"✅ Safety Score:   {report.get('safety_score')}/100")
    print(f"✅ Threat Verdict:  {report.get('verdict')}")
    print(f"✅ Mint Revoked:   {report.get('mint_disabled')}")
    print(f"✅ Freeze Revoked: {report.get('freeze_disabled')}")
    print(f"✅ AI Summary:     {report.get('ai_summary')}")
    print("=" * 65)

if __name__ == "__main__":
    main()
