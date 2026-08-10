"""
GenMeme Guard - Live StudioNet Consensus Verification

Deploys the current contract to GenLayer StudioNet and exercises the real
multi-validator LLM consensus round against it, then checks the two properties
the audit is supposed to guarantee:

  1. a stored report carries analysis_source == "llm_consensus", meaning the
     verdict came from the on-chain model round and not from local code;
  2. the audit fails closed — an evidence-less request stores nothing.

Usage:  py scripts/test_live_consensus.py [existing_contract_address]
"""

import json
import os
import sys
import time

from dotenv import load_dotenv
from genlayer_py import create_client, create_account, studionet

load_dotenv()

PRIVATE_KEY = os.getenv("GENLAYER_PRIVATE_KEY")
CONTRACT_FILE = os.path.normpath(
    os.path.join(os.path.dirname(__file__), "..", "contracts", "meme_rug_auditor.py")
)
WIF_CA = "EKpQGSJtjMFqKZ9KQanSqYXRcF8fBopzLHYxdM65zcjm"

# Real WIF-scale figures. Authority flags and liquidity are present, so the
# contract has the evidence it demands and will proceed to the model round.
FULL_TELEMETRY = json.dumps({
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

# A syntactically valid mint that no indexer knows. RugCheck and DEXScreener
# both come back empty for it, so the contract has no authority evidence from
# any source and must refuse rather than assume the authorities are revoked.
UNKNOWN_MINT = "GmGuardUnknownMint1111111111111111111111111"

NO_AUTHORITY_TELEMETRY = json.dumps({
    "token_symbol": "NOEVIDENCE",
    "fdv_usd": 2450000000.0,
    "liquidity_usd": 15420000.0,
    "volume_24h_usd": 185000000.0,
    "txns_24h_buys": 14200,
    "txns_24h_sells": 11800,
    # deliberately no mint_disabled / freeze_disabled
})


def log(msg):
    print(msg, flush=True)


def read_audit(client, address, token):
    try:
        return client.read_contract(address=address, function_name="get_audit", args=[token])
    except Exception as e:
        log(f"    read_contract error: {str(e)[:160]}")
        return None


def poll_for_audit(client, address, token, attempts=20, delay=4):
    for i in range(1, attempts + 1):
        res = read_audit(client, address, token)
        if res and res.get("has_audit"):
            log(f"    report available after {i} poll(s)")
            return res
        log(f"    waiting for consensus finality... ({i}/{attempts})")
        time.sleep(delay)
    return None


def main():
    if not PRIVATE_KEY:
        log("[!] GENLAYER_PRIVATE_KEY is not set in .env")
        sys.exit(1)

    key = PRIVATE_KEY if PRIVATE_KEY.startswith("0x") else "0x" + PRIVATE_KEY
    account = create_account(key)
    client = create_client(chain=studionet, account=account)

    log("=" * 70)
    log(" GENMEME GUARD -- LIVE STUDIONET CONSENSUS VERIFICATION")
    log("=" * 70)
    log(f"Wallet: {account.address}")

    contract_address = sys.argv[1] if len(sys.argv) > 1 else None

    if contract_address:
        log(f"Using existing contract: {contract_address}")
    else:
        log("\n[1] Deploying current contract to StudioNet...")
        with open(CONTRACT_FILE, "r", encoding="utf-8") as f:
            code = f.read()
        tx_hash = client.deploy_contract(code=code, args=[])
        log(f"    deploy tx: {tx_hash}")
        receipt = client.wait_for_transaction_receipt(tx_hash)
        if isinstance(receipt, dict):
            contract_address = (receipt.get("contract_address")
                                or receipt.get("to_address") or receipt.get("to"))
        else:
            contract_address = (getattr(receipt, "contract_address", None)
                                or getattr(receipt, "to_address", None)
                                or getattr(receipt, "to", None))
        log(f"    deployed at: {contract_address}")

    if not contract_address:
        log("[!] No contract address available; aborting.")
        sys.exit(1)

    stamp = int(time.time())

    # --- Test 1: real LLM consensus round produces the verdict ---------------
    log("\n[2] Triggering a real multi-validator LLM consensus audit...")
    tx = client.write_contract(
        address=contract_address,
        function_name="audit_token",
        args=[WIF_CA, f"req_live_{stamp}", 1000, FULL_TELEMETRY],
    )
    log(f"    audit tx: {tx}")
    try:
        client.wait_for_transaction_receipt(tx)
        log("    receipt received")
    except Exception as e:
        log(f"    receipt wait note: {str(e)[:200]}")

    report = poll_for_audit(client, contract_address, WIF_CA)

    log("\n" + "=" * 70)
    log(" ON-CHAIN AUDIT REPORT")
    log("=" * 70)
    passed_llm = False
    if report:
        log(json.dumps(report, indent=2, ensure_ascii=True)[:2500])
        source = report.get("analysis_source")
        log("-" * 70)
        log(f"analysis_source : {source}")
        log(f"safety_score    : {report.get('safety_score')}/100")
        log(f"verdict         : {report.get('verdict')}")
        log(f"ai_summary      : {str(report.get('ai_summary'))[:300]}")
        passed_llm = source == "llm_consensus"
    else:
        log("[!] No report stored — the consensus round did not produce a verdict.")

    # --- Test 2: the audit fails closed without authority evidence -----------
    log("\n[3] Triggering an audit with no authority evidence (must store nothing)...")
    other_token = UNKNOWN_MINT

    # StudioNet's RPC intermittently answers with a Cloudflare page instead of
    # JSON. That is a failure to ask the question, not an answer to it, so it
    # is retried and — if it never lands — reported as inconclusive rather than
    # being counted as the contract having refused.
    tx2 = None
    for attempt in range(1, 7):
        try:
            tx2 = client.write_contract(
                address=contract_address,
                function_name="audit_token",
                args=[other_token, f"req_noauth_{stamp}_{attempt}", 1000, NO_AUTHORITY_TELEMETRY],
            )
            log(f"    audit tx: {tx2}")
            break
        except Exception as e:
            log(f"    submit attempt {attempt} failed: {str(e)[:110]}")
            time.sleep(8)

    if tx2 is None:
        passed_failclosed = None  # inconclusive
        log("    could not submit the transaction; fail-closed behaviour untested")
    else:
        try:
            client.wait_for_transaction_receipt(tx2)
        except Exception as e:
            log(f"    receipt wait note: {str(e)[:160]}")
        stored = False
        for i in range(12):
            time.sleep(5)
            res2 = read_audit(client, contract_address, other_token)
            if res2 and res2.get("has_audit"):
                stored = True
                break
            log(f"    poll {i + 1}/12: still nothing stored")
        log(f"    stored report for evidence-less request: {stored}")
        passed_failclosed = not stored

    # --- Summary ------------------------------------------------------------
    log("\n" + "=" * 70)
    log(" RESULT")
    log("=" * 70)
    failclosed_label = ("INCONCLUSIVE (RPC unavailable)" if passed_failclosed is None
                        else ("PASS" if passed_failclosed else "FAIL"))
    log(f"Contract               : {contract_address}")
    log(f"Verdict from LLM round : {'PASS' if passed_llm else 'FAIL'}")
    log(f"Fails closed w/o data  : {failclosed_label}")
    log("=" * 70)
    sys.exit(0 if (passed_llm and passed_failclosed) else 1)


if __name__ == "__main__":
    main()
