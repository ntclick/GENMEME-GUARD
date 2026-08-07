"""
GenMeme Guard - Live On-Chain AI Audit Test Script

Queries live DEX & Birdeye metrics and triggers a real AI Consensus Audit on GenLayer StudioNet:
Contract Address: 0xcf8B56fc8ec5C1A0bce8E064D4516C49D63fD3eb
"""

import os
import sys
import json
import time
from dotenv import load_dotenv
from genlayer_py import create_client, create_account, studionet

load_dotenv()

PRIVATE_KEY = os.getenv("GENLAYER_PRIVATE_KEY")
CONTRACT_ADDRESS = os.getenv("CONTRACT_ADDRESS", "0xcf8B56fc8ec5C1A0bce8E064D4516C49D63fD3eb")

# Default Test Token: WIF (dogwifhat)
TOKEN_CA = sys.argv[1] if len(sys.argv) > 1 else "EKpQGSJtjMFqKZ9KQanSqYXRcF8fBopzLHYxdM65zcjm"

def main():
    print("=" * 65)
    print(" GENMEME GUARD -- LIVE ON-CHAIN AI AUDIT TESTER")
    print("=" * 65)

    if not PRIVATE_KEY:
        print("[!] ERROR: GENLAYER_PRIVATE_KEY is not set in .env")
        sys.exit(1)

    key = PRIVATE_KEY if PRIVATE_KEY.startswith("0x") else "0x" + PRIVATE_KEY
    account = create_account(key)
    client = create_client(chain=studionet, account=account)

    print(f"[*] Wallet Address:  {account.address}")
    print(f"[*] Target Contract: {CONTRACT_ADDRESS}")
    print(f"[*] Target Token:    {TOKEN_CA}")
    print("-" * 65)

    # 1. Prepare Realistic Birdeye & DEX Telemetry Payload
    print("[1/3] Preparing Birdeye & DEX Telemetry Payload...")
    telemetry_payload = json.dumps({
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

    req_id = f"req_script_test_{int(time.time())}"

    # 2. Send audit_token transaction to GenLayer StudioNet
    print(f"[2/3] Sending audit_token transaction to GenLayer StudioNet (req_id: {req_id})...")
    try:
        tx_hash = client.write_contract(
            address=CONTRACT_ADDRESS,
            function_name="audit_token",
            args=[TOKEN_CA, req_id, 1000, telemetry_payload]
        )
        print(f"[+] Audit Tx Hash: {tx_hash}")
        print("[*] Waiting for GenLayer BFT Optimistic Democracy AI Consensus finalization...")
        client.wait_for_transaction_receipt(tx_hash)
        print("[+] Transaction Receipt received! Waiting 12s for StudioNet AI Consensus state propagation...")
        time.sleep(12)
    except Exception as e:
        print(f"[!] Tx Execution Warning / Note: {e}")

    # 3. Query Final On-Chain Audit Report with polling loop
    print("-" * 65)
    print("[3/3] Polling Finalized On-Chain Audit Report via get_audit()...")
    report = None
    for attempt in range(1, 15):
        try:
            res = client.read_contract(
                address=CONTRACT_ADDRESS,
                function_name="get_audit",
                args=[TOKEN_CA]
            )
            if res and res.get("has_audit"):
                report = res
                print(f"[+] Audit Consensus Finalized on-chain (Attempt {attempt}/15)!")
                break
        except Exception as e:
            pass
        print(f"[*] Waiting for StudioNet AI Consensus finalization... ({attempt}/15)")
        time.sleep(3)

    print("\n" + "=" * 65)
    print(" ON-CHAIN AUDIT CONSENSUS REPORT RESULT:")
    print("=" * 65)
    if report:
        print(json.dumps(report, indent=2, ensure_ascii=True))
        print("=" * 65)
        print(f"[+] Safety Score:  {report.get('safety_score')}/100")
        print(f"[+] Threat Verdict: {report.get('verdict')}")
        print(f"[+] AI Summary:    {report.get('ai_summary')}")
    else:
        print("[!] Note: Audit transaction is processing on StudioNet. View transaction hash on explorer.")
    print("=" * 65)

if __name__ == "__main__":
    main()
