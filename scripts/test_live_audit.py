"""
GenMeme Guard - Live On-Chain AI Audit Test Script

Queries live DEX & Birdeye metrics and triggers a real AI Consensus Audit on GenLayer StudioNet:
Contract Address: 0x89A635c008Dc1C6bec363985B5F6Df1785E1F06B
"""

import os
import sys
import json
import time
from dotenv import load_dotenv
from genlayer_py import create_client, create_account, studionet

load_dotenv()

PRIVATE_KEY = os.getenv("GENLAYER_PRIVATE_KEY")
CONTRACT_ADDRESS = os.getenv("CONTRACT_ADDRESS", "0x89A635c008Dc1C6bec363985B5F6Df1785E1F06B")

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

    # 1. No telemetry is sent. Every figure that moves the outcome is fetched
    # independently by each validator node, so a caller payload carries no
    # evidentiary weight and the contract ignores it outright.
    print("[1/3] Sending no telemetry — the contract fetches its own evidence...")
    telemetry_payload = ""

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
