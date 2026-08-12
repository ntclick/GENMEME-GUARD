"""
GenMeme Guard - StudioNet Explorer Verification Script

Deploys/Interacts with the Intelligent Contract and prints direct clickable links
for https://explorer-studio.genlayer.com/
"""

import os
import sys
import json
from dotenv import load_dotenv
from genlayer_py import create_client, create_account, studionet

load_dotenv()

EXPLORER_BASE_URL = "https://explorer-studio.genlayer.com"
CONTRACT_ADDRESS = os.getenv("CONTRACT_ADDRESS", "0x89A635c008Dc1C6bec363985B5F6Df1785E1F06B")
DEPLOY_TX_HASH = "0x9598b45427a06c35b65530891883d11774d5a4ad5f053a3c83ef69f4cc4e6a58"

TEST_TOKENS = [
    {"name": "Dogwifhat (WIF)", "ca": "EKpQGSJtjMFqKZ9KQanSqYXRcF8fBopzLHYxdM65zcjm"},
    {"name": "x402 Singularity Layer (SGL)", "ca": "5c4HyD2rSShqnTsf5z3SaoD2H3GE452u2CUuYjviBAGS"},
]

def main():
    print("\n=======================================================")
    print(" GENMEME GUARD - STUDIONET EXPLORER VERIFICATION ")
    print("=======================================================\n")

    print(f"[*] Deployed Contract Address: {CONTRACT_ADDRESS}")
    print(f"[*] Contract Explorer URL: {EXPLORER_BASE_URL}/address/{CONTRACT_ADDRESS}\n")

    print(f"[*] Deployment Transaction Hash: {DEPLOY_TX_HASH}")
    print(f"[*] Deployment Tx Explorer URL: {EXPLORER_BASE_URL}/tx/{DEPLOY_TX_HASH}\n")

    private_key = os.getenv("GENLAYER_PRIVATE_KEY")
    if not private_key:
        print("[i] GENLAYER_PRIVATE_KEY not set in .env. Showing static explorer links above.")
        sys.exit(0)

    key = private_key if private_key.startswith("0x") else "0x" + private_key
    account = create_account(key)
    client = create_client(chain=studionet, account=account)

    print(f"[*] Interacting with contract via account: {account.address}")
    for item in TEST_TOKENS:
        token_name = item["name"]
        ca = item["ca"]
        print(f"\n--- Triggering Audit for {token_name} ({ca}) ---")
        try:
            tx_hash = client.write_contract(
                address=CONTRACT_ADDRESS,
                function_name="audit_token",
                args=[ca]
            )
            print(f"[+] Write Tx Hash: {tx_hash}")
            print(f"[*] Tx Explorer Link: {EXPLORER_BASE_URL}/tx/{tx_hash}")
            
            print("[*] Waiting for consensus finality...")
            client.wait_for_transaction_receipt(tx_hash)

            report = client.read_contract(
                address=CONTRACT_ADDRESS,
                function_name="get_audit",
                args=[ca]
            )
            print(f"[SUCCESS] On-Chain Report: {json.dumps(report, indent=2)}")
        except Exception as e:
            print(f"[!] Tx error: {e}")

if __name__ == "__main__":
    main()
