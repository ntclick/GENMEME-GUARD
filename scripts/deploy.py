"""
GenMeme Guard - Solana Meme Rug Inspector - Deployment Script

Deploys and tests the Intelligent Contract using genlayer_py SDK.
Environment variables are loaded dynamically from .env file.
"""

import os
import sys
import json
from dotenv import load_dotenv
from genlayer_py import create_client, create_account, studionet, testnet_bradbury

# Load environment variables from .env file
load_dotenv()

PRIVATE_KEY = os.getenv("GENLAYER_PRIVATE_KEY")
DEFAULT_NETWORK = os.getenv("GENLAYER_NETWORK", "studionet")

CONTRACT_FILE = os.path.normpath(
    os.path.join(os.path.dirname(__file__), "..", "contracts", "meme_rug_auditor.py")
)

SAMPLE_TOKEN_CA = "EKpQGSJtjMFqKZ9KQanSqYXRcF8fBopzLHYxdM65zcjm"  # WIF token

def main():
    print("=== GenMeme Guard Deployment & On-Chain Audit Test ===")

    if not PRIVATE_KEY:
        print("[!] ERROR: GENLAYER_PRIVATE_KEY is not set in .env file.")
        print("[!] Please set your private key in .env (see .env.example).")
        sys.exit(1)

    key = PRIVATE_KEY if PRIVATE_KEY.startswith("0x") else "0x" + PRIVATE_KEY

    # 1. Derive Account
    account = create_account(key)
    print(f"[*] Wallet Address loaded: {account.address}")

    # 2. Select Network
    network_arg = sys.argv[1] if len(sys.argv) > 1 else DEFAULT_NETWORK
    if network_arg.lower() == "bradbury":
        chain_config = testnet_bradbury
        print("[*] Target Network: Bradbury Testnet (Chain ID: 4221)")
    else:
        chain_config = studionet
        print("[*] Target Network: StudioNet (Chain ID: 4220 - Gasless)")

    # 3. Create GenLayer Client
    client = create_client(chain=chain_config, account=account)
    print(f"[*] Connected to RPC: {getattr(chain_config, 'rpc_url', chain_config)}")

    # 4. Read Contract Source Code
    with open(CONTRACT_FILE, "r", encoding="utf-8") as f:
        contract_code = f.read()

    print("[*] Deploying Intelligent Contract (MemeRugAuditor)...")
    try:
        tx_hash = client.deploy_contract(
            code=contract_code,
            args=[]
        )
        print(f"[+] Deployment Tx Hash: {tx_hash}")

        receipt = client.wait_for_transaction_receipt(tx_hash)
        contract_address = (
            (receipt.get("contract_address") or receipt.get("to_address") or receipt.get("to"))
            if isinstance(receipt, dict)
            else (getattr(receipt, "contract_address", None) or getattr(receipt, "to_address", None) or getattr(receipt, "to", None))
        )
        print(f"[SUCCESS] Contract Deployed At Address: {contract_address}")

        if contract_address:
            print(f"[*] Triggering AI Consensus Rug Audit for {SAMPLE_TOKEN_CA} (audit_token)...")
            # No telemetry. The contract fetches its own evidence on every
            # validator node and ignores this argument; sending a payload would
            # only suggest it counted for something. Pass "" so the smoke test
            # exercises the same path a real caller does.
            review_tx = client.write_contract(
                address=contract_address,
                function_name="audit_token",
                args=[SAMPLE_TOKEN_CA, "req_deploy_test_wif_1", 1000, ""]
            )
            print(f"[+] Audit Tx Hash: {review_tx}")
            client.wait_for_transaction_receipt(review_tx)

            print(f"[*] Reading On-Chain Audit Report for {SAMPLE_TOKEN_CA} (get_audit)...")
            report = client.read_contract(
                address=contract_address,
                function_name="get_audit",
                args=[SAMPLE_TOKEN_CA]
            )
            print(f"[SUCCESS] On-Chain Report: {report}")

    except Exception as e:
        print(f"[!] Deployment error: {e}")

if __name__ == "__main__":
    main()
