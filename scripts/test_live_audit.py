"""
GenMeme Guard - Live On-Chain AI Audit Test Script

Sends a real `audit_token` transaction to the deployed Intelligent Contract on
GenLayer StudioNet and shows the consensus round as it happens: each validator's
vote, every leader rotation, and the record that ends up stored.

The votes are the part worth watching. Every validator re-runs the DEXScreener
fetch, the RugCheck fetch and the LLM audit itself, then compares its own result
against the leader's through `_check_equivalence`. A node whose round lands
outside that envelope votes `disagree`, the round is thrown out and a new leader
is drawn — which is why a round count above 1 is normal rather than a fault.

Usage:
    py scripts/test_live_audit.py                      # audits WIF
    py scripts/test_live_audit.py <token_mint>
    py scripts/test_live_audit.py <token_mint> <contract_address>

Exit codes:
    0  audited, record stored and printed
    1  the audit failed — UNDETERMINED consensus, or nothing readable afterwards
    2  still queued on StudioNet when the watch window ran out; nothing decided

CONTRACT_ADDRESS in .env overrides the built-in default, so a stale value there
sends the audit to an old deployment. The address in use is printed before
anything is sent.
"""

import os
import sys
import json
import time
from dotenv import load_dotenv
from genlayer_py import create_client, create_account, studionet

# The stored rationale contains em dashes; a cp1252 console would raise on them
# and lose the whole report over a punctuation mark.
try:
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
except Exception:
    pass

load_dotenv()

PRIVATE_KEY = os.getenv("GENLAYER_PRIVATE_KEY")
DEFAULT_CONTRACT = "0x0F134A29962B9729788D292ba1527d7916e80df4"
WIF_CA = "EKpQGSJtjMFqKZ9KQanSqYXRcF8fBopzLHYxdM65zcjm"

TOKEN_CA = sys.argv[1] if len(sys.argv) > 1 else WIF_CA
CONTRACT_ADDRESS = (
    sys.argv[2] if len(sys.argv) > 2
    else os.getenv("CONTRACT_ADDRESS", DEFAULT_CONTRACT)
)

SETTLED = ("ACCEPTED", "FINALIZED", "UNDETERMINED", "CANCELED")
EXPLORER = "https://explorer-studio.genlayer.com"

POLL_INTERVAL = 6
POLL_ATTEMPTS = 60          # 6 minutes: a rejected round rotates the leader and
                            # re-runs the whole web+LLM audit, which is not fast


def log(msg=""):
    print(msg, flush=True)


def watch_transaction(client, tx_hash):
    """Follow the consensus rounds, printing each change. Returns the final status."""
    last_line = None
    status = None
    for _ in range(POLL_ATTEMPTS):
        time.sleep(POLL_INTERVAL)
        try:
            tx = client.get_transaction(transaction_hash=tx_hash)
            tx = tx if isinstance(tx, dict) else dict(tx)
        except Exception as e:
            log(f"    rpc error, retrying: {str(e)[:120]}")
            continue

        status = tx.get("status_name") or tx.get("status")
        rounds = tx.get("num_of_rounds")
        votes = (tx.get("last_round") or {}).get("validator_votes_name") or []

        line = f"    {status:<12} round {rounds}  {', '.join(votes) if votes else '(voting)'}"
        if line != last_line:
            log(line)
            last_line = line

        if status in SETTLED:
            return status
    return status


def show_report(report):
    log("=" * 72)
    log(" STORED ON-CHAIN RECORD")
    log("=" * 72)
    log(f"  token          : {report.get('token_symbol')}  ({report.get('token_address')})")
    log(f"  verdict        : {report.get('verdict')}")
    log(f"  safety score   : {report.get('safety_score')}/100")
    log(f"  scale tier     : {report.get('scale_tier')}  (evidence ceiling {report.get('score_ceiling')})")
    log(f"  analysis source: {report.get('analysis_source')}")
    log("")
    log("  measured:")
    for field, label in (
        ("mint_disabled", "mint authority revoked"),
        ("freeze_disabled", "freeze authority revoked"),
        ("lp_burned_pct", "LP burned %"),
        ("top10_holder_pct", "top 10 holders %"),
        ("holder_count", "holder count"),
        ("smart_money_wallets", "smart-money wallets"),
    ):
        unknown = field in (report.get("unverified_fields") or [])
        value = "unverified" if unknown else report.get(field)
        log(f"    {label:<24} {value}")
    log("")
    log("  risk factors:")
    for risk in report.get("risk_factors") or []:
        log(f"    - {risk}")
    log("")
    log("  consensus rationale:")
    log(f"    {report.get('ai_summary')}")
    log("=" * 72)


def main():
    log("=" * 72)
    log(" GENMEME GUARD -- LIVE ON-CHAIN AI AUDIT")
    log("=" * 72)

    if not PRIVATE_KEY:
        log("[!] GENLAYER_PRIVATE_KEY is not set in .env (see .env.example)")
        sys.exit(1)

    key = PRIVATE_KEY if PRIVATE_KEY.startswith("0x") else "0x" + PRIVATE_KEY
    account = create_account(key)
    client = create_client(chain=studionet, account=account)

    req_id = f"req_script_{int(time.time())}"

    log(f"  wallet   : {account.address}")
    log(f"  contract : {CONTRACT_ADDRESS}")
    log(f"  token    : {TOKEN_CA}")
    log(f"  request  : {req_id}")
    log("-" * 72)

    # No telemetry. Every figure that moves the outcome is fetched independently
    # by each validator, so a caller payload carries no evidentiary weight and
    # the contract ignores the argument outright. Sending one anyway would read
    # as though it counted for something.
    log("[1/3] Sending audit_token (no caller payload — each node fetches its own evidence)")
    try:
        tx_hash = client.write_contract(
            address=CONTRACT_ADDRESS,
            function_name="audit_token",
            args=[TOKEN_CA, req_id, 1000, ""],
        )
    except Exception as e:
        log(f"[!] Transaction was rejected on submission: {e}")
        sys.exit(1)

    log(f"      tx {tx_hash}")
    log(f"      {EXPLORER}/tx/{tx_hash}")
    log("")
    log("[2/3] Watching the consensus round (a rejected round redraws the leader)")

    status = watch_transaction(client, tx_hash)
    log("")
    if status not in ("ACCEPTED", "FINALIZED"):
        log(f"[!] Transaction did not settle within {POLL_ATTEMPTS * POLL_INTERVAL // 60} minutes: {status}")
        if status == "UNDETERMINED":
            # A real consensus failure: the validators never agreed within the
            # rotations available, so nothing is stored. That is the design.
            log("    The validators never reached agreement across the rotations")
            log("    available, so nothing was stored. That is the audit failing closed.")
            sys.exit(1)
        # PENDING means StudioNet has not started the transaction yet — it is
        # queued behind others. Nothing has been judged, so calling this a
        # consensus failure would blame the contract for the network's backlog.
        log("    It is still queued on StudioNet and has not been executed yet, so")
        log("    nothing about the audit has been decided. Re-check it with:")
        log(f"      {EXPLORER}/tx/{tx_hash}")
        sys.exit(2)

    log(f"[3/3] {status} — reading the record back with get_audit()")
    log("")

    report = None
    for _ in range(10):
        try:
            res = client.read_contract(
                address=CONTRACT_ADDRESS, function_name="get_audit", args=[TOKEN_CA]
            )
            if res and res.get("has_audit"):
                report = res
                break
        except Exception:
            pass
        time.sleep(4)

    if not report:
        log("[!] The transaction settled but no record is readable yet.")
        sys.exit(1)

    show_report(report)
    log("")
    log(f"Raw JSON:\n{json.dumps(report, indent=2, ensure_ascii=False)}")


if __name__ == "__main__":
    main()
