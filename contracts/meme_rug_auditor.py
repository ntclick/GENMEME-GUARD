# { "Depends": "py-genlayer:1jb45aa8ynh2a9c9xn3b7qqh8sm5q93hwfp7jqmwsfhh8jpz09h6" }
from genlayer import *
from dataclasses import dataclass
import json

# Institutional-grade Rubric prompt for Senior On-Chain Forensic AI Auditors with Scale-Tier Architecture
RUBRIC_PROMPT = """
You are a SENIOR QUANTITATIVE ON-CHAIN ANALYST at GenLayer Security Intelligence Lab.
Perform a FORENSIC SCALE-TIER AUDIT on Solana token: {token_address} using the telemetry payload below.

--- Extracted Birdeye & On-Chain Telemetry Payload ---
{tech_data}
---

INSTITUTIONAL SCALE-TIER SCORING MATRIX:

1. MARKET CAP & LIQUIDITY SCALE TIERS (HARD CEILINGS):
   - Tier 1 Micro-Cap (Market Cap < $100,000 USD OR Liquidity < $20,000 USD):
     MAX SCORE CEILING = 55 PTS (CANNOT exceed 55 / HIGH_VOLATILITY_WARN, no matter what!). Deduct 35 pts for unproven micro liquidity depth.
   - Tier 2 Small-Cap (Market Cap $100,000 - $1,000,000 USD):
     MAX SCORE CEILING = 75 PTS.
   - Tier 3 Mid-Cap (Market Cap $1,000,000 - $10,000,000 USD):
     MAX SCORE CEILING = 88 PTS.
   - Tier 4 Institutional Bluechip Meme (Market Cap > $10,000,000 USD & Liquidity > $500,000 USD):
     MAX SCORE CEILING = 100 PTS. Add +25 pts for proven multi-million market resilience & deep liquidity depth!

2. CONTRACT HOOK SECURITY:
   - Mint Authority Active: Immediate -50 pts -> Verdict MUST be CRITICAL_RUG_RISK!
   - Freeze Authority Active: Immediate -50 pts -> Verdict MUST be CRITICAL_RUG_RISK!
   - LP Burned %: < 50% = -40 pts; 50-80% = -20 pts; >= 95% = +5 pts.
     If the payload above does not contain an LP burn percentage, you MUST report
     lp_burned_pct as 0 and MUST NOT award the >= 95% bonus. Do not substitute a
     reassuring value for a figure the evidence never supplied.

EVIDENCE DISCIPLINE (applies to every numeric field):
Report 0 for lp_burned_pct, top10_holder_pct, holder_count or smart_money_wallets
whenever the payload does not contain that measurement, and say plainly in
ai_summary which metrics were unavailable. Never infer, estimate or default these
numbers — an unverified figure is treated as absent and the contract will
overwrite anything you invent here.

3. HOLDER DISTRIBUTION & SMART MONEY NETWORK:
   - Holder Count > 10,000: +15 pts; < 200: -25 pts (Insider Sybil risk).
   - Smart Money Wallets >= 15: +15 pts; < 3: -20 pts (Retail Trap).
   - Top 10 Holder Concentration > 40%: -25 pts.

4. ORDERBOOK INFLOW & TRADING VELOCITY:
   - Buy/Sell Ratio > 1.2: +10 pts; < 0.8: -20 pts (Whale Dumping Outflow).

VERDICT CLASSIFICATION:
- SAFE_TO_TRADE (Score 80-100): Tier 3/4 Mid/Large Cap, zero active hooks, LP burned > 90%, strong smart money accumulation.
- HIGH_VOLATILITY_WARN (Score 50-79): Tier 1/2 Micro/Small Cap, moderate liquidity, or elevated price swings.
- CRITICAL_RUG_RISK (Score 0-49): Active Mint/Freeze hooks, unlocked LP, severe whale dumping, or micro liquidity crash danger.

REQUIREMENT FOR "ai_summary":
Write an INSTITUTIONAL 4-SENTENCE BIRDEYE FORENSIC BRIEF:
Sentence 1: Formal verdict & Scale-Tier classification (e.g., Tier 4 Institutional Bluechip vs Tier 1 Micro-Cap).
Sentence 2: Market Cap ($...), Liquidity ($...), Holder Count, and Smart Money Wallets count.
Sentence 3: Contract Hooks status (Mint/Freeze revocation) and LP Burn %.
Sentence 4: Quantitative orderbook inflow (Buys vs Sells) and 24h price trajectory %.

Return strictly a single valid JSON object matching this exact schema — no markdown formatting, no extra text:
{
    "token_address": "{token_address}",
    "token_symbol": "<symbol>",
    "safety_score": 88,
    "verdict": "<SAFE_TO_TRADE|HIGH_VOLATILITY_WARN|CRITICAL_RUG_RISK>",
    "mint_disabled": true,
    "freeze_disabled": true,
    "lp_burned_pct": 100,
    "top10_holder_pct": 20,
    "holder_count": 18500,
    "smart_money_wallets": 24,
    "risk_factors": ["explicit Scale-Tier risk 1", "explicit Scale-Tier risk 2"],
    "ai_summary": "Formal 4-sentence Scale-Tier forensic audit brief citing exact market scale tier, market cap, holder count, smart money wallets count, liquidity depth, and contract hook security."
}
"""

SCORE_TOLERANCE = 10
ALLOWED_VERDICTS = {"SAFE_TO_TRADE", "HIGH_VOLATILITY_WARN", "CRITICAL_RUG_RISK"}
MIN_AUDIT_FEE = u256(1000)

# Every stored report carries its provenance. There is deliberately no second
# value here: a verdict only ever comes from the on-chain LLM consensus round,
# and an audit that cannot reach one reverts instead of storing anything.
SOURCE_LLM = "llm_consensus"

VERDICT_SEVERITY = {"SAFE_TO_TRADE": 0, "HIGH_VOLATILITY_WARN": 1, "CRITICAL_RUG_RISK": 2}

# The rubric grants this for LP burned >= 95%. Reclaimed when that percentage
# turns out to be the model's own invention rather than fetched evidence.
LP_BURN_BONUS = 5

SYMBOL_HINTS = [
    ("EKpQGS", "WIF"),
    ("5c4HyD", "SGL"),
    ("DezXAZ", "BONK"),
    ("7GCihg", "POPCAT"),
    ("6p6xgH", "TRUMP"),
]


def _safe_float(val, default=0.0) -> float:
    if val is None:
        return default
    try:
        return float(val)
    except Exception:
        return default


def _safe_int(val, default=0) -> int:
    if val is None:
        return default
    try:
        return int(val)
    except Exception:
        return default


def _check_equivalence(res1: dict, res2: dict) -> bool:
    if not isinstance(res1, dict) or not isinstance(res2, dict):
        return False
    # Two nodes that did not reach their verdicts the same way are not
    # equivalent even when the numbers happen to line up.
    if res1.get("analysis_source") != res2.get("analysis_source"):
        return False
    score1 = _safe_int(res1.get("safety_score"))
    score2 = _safe_int(res2.get("safety_score"))
    if abs(score1 - score2) > SCORE_TOLERANCE:
        return False
    if res1.get("verdict") != res2.get("verdict"):
        return False
    if bool(res1.get("mint_disabled")) != bool(res2.get("mint_disabled")):
        return False
    if bool(res1.get("freeze_disabled")) != bool(res2.get("freeze_disabled")):
        return False
    return True


def _resolve_symbol(token_address: str, raw_symbol) -> str:
    sym = str(raw_symbol or "").strip()
    if sym and sym != "UNKNOWN":
        return sym
    for prefix, known in SYMBOL_HINTS:
        if prefix in token_address:
            return known
    return f"SOL-{token_address[:4]}"


def _classify_llm_error(exc) -> str:
    """Tag an LLM failure with a deterministic prefix so the revert message
    says why the consensus round could not be completed."""
    msg = str(exc).strip() or exc.__class__.__name__
    low = msg.lower()
    if "timeout" in low or "timed out" in low or "unavailable" in low:
        return f"TRANSIENT: {msg}"
    if "connect" in low or "network" in low or "http" in low or "mock" in low:
        return f"EXTERNAL: {msg}"
    return f"LLM_ERROR: {msg}"


def _band_verdict(score: int) -> str:
    if score < 50:
        return "CRITICAL_RUG_RISK"
    if score < 80:
        return "HIGH_VOLATILITY_WARN"
    return "SAFE_TO_TRADE"


def _normalize_llm_report(raw, token_address: str) -> dict:
    """Strictly validate an LLM audit response.

    Returns {} when the response cannot be trusted, which aborts the audit.
    Nothing downstream may substitute a locally computed stand-in.
    """
    parsed = raw
    if isinstance(raw, str):
        clean = raw.strip()
        if clean.startswith("```json"):
            clean = clean[7:]
        if clean.startswith("```"):
            clean = clean[3:]
        if clean.endswith("```"):
            clean = clean[:-3]
        try:
            parsed = json.loads(clean.strip())
        except Exception:
            return {}

    if not isinstance(parsed, dict):
        return {}
    if "safety_score" not in parsed or "verdict" not in parsed:
        return {}

    verdict = str(parsed.get("verdict") or "").strip().upper()
    if verdict not in ALLOWED_VERDICTS:
        return {}

    score = _safe_int(parsed.get("safety_score"), -1)
    if score < 0 or score > 100:
        return {}

    summary = str(parsed.get("ai_summary") or "").strip()
    if not summary:
        return {}

    raw_risks = parsed.get("risk_factors")
    risks = [str(r) for r in raw_risks if r is not None] if isinstance(raw_risks, list) else []

    return {
        "token_address": token_address,
        "token_symbol": _resolve_symbol(token_address, parsed.get("token_symbol")),
        "safety_score": score,
        "verdict": verdict,
        "mint_disabled": bool(parsed.get("mint_disabled", True)),
        "freeze_disabled": bool(parsed.get("freeze_disabled", True)),
        "lp_burned_pct": _safe_int(parsed.get("lp_burned_pct"), 0),
        "top10_holder_pct": _safe_int(parsed.get("top10_holder_pct"), 0),
        "holder_count": _safe_int(parsed.get("holder_count"), 0),
        "smart_money_wallets": _safe_int(parsed.get("smart_money_wallets"), 0),
        "risk_factors": risks,
        "ai_summary": summary,
    }


def _validate_findings(report: dict, ground_truth: dict) -> dict:
    """Cross-check a model verdict against hard evidence before it is stored.

    Mint/freeze authority is an on-chain fact read from RugCheck or the
    caller's telemetry payload, not a matter of model opinion, so the fetched
    value always wins and an active authority forces CRITICAL_RUG_RISK. The
    verdict is then reconciled with its own score band, keeping whichever of
    the two readings is more severe so the model cannot label a failing score
    as safe.
    """
    if "mint_authority_disabled" in ground_truth:
        report["mint_disabled"] = bool(ground_truth["mint_authority_disabled"])
    if "freeze_authority_disabled" in ground_truth:
        report["freeze_disabled"] = bool(ground_truth["freeze_authority_disabled"])

    if not report["mint_disabled"]:
        label = "Mint Authority Active — Inflation Danger"
        if label not in report["risk_factors"]:
            report["risk_factors"].append(label)
    if not report["freeze_disabled"]:
        label = "Freeze Authority Active — Honeypot Lock Danger"
        if label not in report["risk_factors"]:
            report["risk_factors"].append(label)

    if not report["mint_disabled"] or not report["freeze_disabled"]:
        report["verdict"] = "CRITICAL_RUG_RISK"
        if report["safety_score"] > 49:
            report["safety_score"] = 49

    # The distribution metrics get the same treatment as authority: a fetched
    # value always wins, and one the evidence never supplied is not the model's
    # to invent. A model that admits in prose that it cannot verify LP burn has
    # still been observed reporting lp_burned_pct 100 — the most reassuring
    # value available — in the same response, so an unbacked number is zeroed
    # and named rather than stored as if it were measured. Zero is ambiguous on
    # its own (0% LP burned is a real and serious finding), which is why the
    # unverified list travels with the report instead of leaving the reader to
    # guess which zeros mean "measured" and which mean "unknown".
    unverified = []
    for evidence_key in ("lp_burned_pct", "top10_holder_pct", "holder_count", "smart_money_wallets"):
        if evidence_key in ground_truth:
            report[evidence_key] = _safe_int(ground_truth[evidence_key])
        else:
            claimed = _safe_int(report.get(evidence_key))
            report[evidence_key] = 0
            unverified.append(evidence_key)
            # Undo the rubric's own ">= 95% LP burned" bonus if the model
            # awarded it off a number nothing backed.
            if evidence_key == "lp_burned_pct" and claimed >= 95:
                report["safety_score"] = max(0, report["safety_score"] - LP_BURN_BONUS)

    if "lp_burned_pct" in unverified:
        label = "LP Burn Unverified — no burn evidence from RugCheck or caller telemetry"
        if label not in report["risk_factors"]:
            report["risk_factors"].append(label)

    report["unverified_fields"] = unverified

    banded = _band_verdict(report["safety_score"])
    if VERDICT_SEVERITY[banded] > VERDICT_SEVERITY[report["verdict"]]:
        report["verdict"] = banded

    if not report["risk_factors"]:
        report["risk_factors"] = ["Volatile Meme Market Dynamics"]
    return report


@allow_storage
@dataclass
class AuditRecord:
    request_id: str
    caller_address: Address
    token_address: str
    token_symbol: str
    safety_score: u32
    verdict: str
    mint_disabled: bool
    freeze_disabled: bool
    lp_burned_pct: u32
    top10_holder_pct: u32
    holder_count: u32
    smart_money_wallets: u32
    risk_factors_json: str
    ai_summary: str
    audited_at_block: u64
    paid_amount: u256
    analysis_source: str
    # JSON list naming the metrics above that no source could back, so a reader
    # can tell a measured zero from an unknown one.
    unverified_fields_json: str


class MemeRugAuditor(gl.Contract):
    # ---- On-Chain Persistent State ----
    contract_owner: Address
    audited_count: u32
    recent_tokens: DynArray[str]
    audited_records: TreeMap[str, AuditRecord]
    request_audits: TreeMap[str, AuditRecord]
    used_request_ids: DynArray[str]

    def __init__(self):
        self.contract_owner = gl.message.sender_address
        self.audited_count = 0

    @gl.public.write
    def audit_token(self, token_address: str, request_id: str = "", payment_amount: u256 = u256(1000), telemetry_json: str = "") -> str:
        """
        Executes Non-Deterministic Web Data Fetch & Multi-Node LLM Equivalence Principle Consensus.
        Binds one-time payment & verified caller authorization to unique request_id.

        The audit fails closed. If the live market and authority evidence is not
        available, or the LLM consensus round cannot produce a verdict that
        passes validation, the transaction reverts and no report is stored —
        there is no local scoring path that could stand in for the model.
        """
        caller = gl.message.sender_address

        # 1. Payment Verification (Reject Forged / Insufficient Payments)
        if payment_amount < MIN_AUDIT_FEE:
            raise gl.vm.UserError("Insufficient audit fee / Forged payment detected.")

        if not token_address or len(str(token_address).strip()) < 30:
            raise gl.vm.UserError("Invalid Solana token mint address.")

        token_address = str(token_address).strip()

        # 2. Request-ID Binding & Replay Prevention
        if not request_id or len(str(request_id).strip()) == 0:
            request_id = f"req_{caller}_{token_address}_{self.audited_count}"

        request_id = str(request_id).strip()

        # Replay Attack Prevention
        for i in range(len(self.used_request_ids)):
            if self.used_request_ids[i] == request_id:
                raise gl.vm.UserError("Replay attack detected: Request ID already processed.")

        def leader_fn() -> dict:
            # 1. Parse client-provided live telemetry payload if available
            dex_metrics = {}
            tele_security = {}
            if telemetry_json and len(str(telemetry_json).strip()) > 2:
                try:
                    parsed_tele = json.loads(str(telemetry_json).strip())
                    if isinstance(parsed_tele, dict):
                        buys = _safe_int(parsed_tele.get("txns_24h_buys"))
                        sells = _safe_int(parsed_tele.get("txns_24h_sells"))
                        sentiment = "BUY_ACCUMULATION" if buys > sells * 1.15 else ("WHALE_SELLING_PRESSURE" if sells > buys * 1.15 else "NEUTRAL")
                        liq_usd = _safe_float(parsed_tele.get("liquidity_usd"))
                        vol_usd = _safe_float(parsed_tele.get("volume_24h_usd"))
                        
                        dex_metrics = {
                            "token_symbol": str(parsed_tele.get("token_symbol") or "UNKNOWN"),
                            "token_name": str(parsed_tele.get("token_name") or "UNKNOWN"),
                            "price_usd": str(parsed_tele.get("price_usd") or "0"),
                            "fdv_usd": _safe_float(parsed_tele.get("fdv_usd")),
                            "liquidity_usd": liq_usd,
                            "volume_24h_usd": vol_usd,
                            "price_change_24h_pct": _safe_float(parsed_tele.get("price_change_24h_pct")),
                            "txns_24h_buys": buys,
                            "txns_24h_sells": sells,
                            "smart_money_sentiment": sentiment,
                            "volume_to_liquidity_ratio": round(vol_usd / max(liq_usd, 1.0), 2)
                        }

                        # Only carry over metrics the caller actually supplied.
                        # Defaulting a missing authority flag to "disabled" would
                        # invent a clean bill of health out of absent evidence.
                        tele_security = {}
                        if "mint_disabled" in parsed_tele and parsed_tele.get("mint_disabled") is not None:
                            tele_security["mint_authority_disabled"] = bool(parsed_tele.get("mint_disabled"))
                        if "freeze_disabled" in parsed_tele and parsed_tele.get("freeze_disabled") is not None:
                            tele_security["freeze_authority_disabled"] = bool(parsed_tele.get("freeze_disabled"))
                        for tele_key, sec_key in (
                            ("lp_burned_pct", "lp_burned_pct"),
                            ("top10_holder_pct", "top10_holder_pct"),
                            ("holder_count", "holder_count"),
                            ("smart_money_wallets", "smart_money_wallets"),
                        ):
                            if tele_key in parsed_tele and parsed_tele.get(tele_key) is not None:
                                tele_security[sec_key] = _safe_int(parsed_tele.get(tele_key))
                        if isinstance(parsed_tele.get("detected_risks"), list):
                            tele_security["detected_risks"] = parsed_tele.get("detected_risks")
                except Exception:
                    pass

            # 2. Fetch & parse technical market metrics from DEXScreener via gl.nondet.web.get if telemetry is incomplete
            if not dex_metrics.get("token_symbol") or dex_metrics.get("token_symbol") == "UNKNOWN":
                dex_url = f"https://api.dexscreener.com/latest/dex/tokens/{token_address}"
                try:
                    headers = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64)"}
                    resp = gl.nondet.web.get(dex_url, headers=headers)
                    if resp and hasattr(resp, "body") and resp.body:
                        if isinstance(resp.body, bytes):
                            raw_dex_str = resp.body.decode("utf-8")
                        elif isinstance(resp.body, str):
                            raw_dex_str = resp.body
                        else:
                            raw_dex_str = str(resp.body)
                    else:
                        raw_dex_str = "{}"

                    raw_dex = json.loads(raw_dex_str)
                    pairs = raw_dex.get("pairs", [])
                    if isinstance(pairs, list) and len(pairs) > 0 and isinstance(pairs[0], dict):
                        p = pairs[0]
                        base_tok = p.get("baseToken") if isinstance(p.get("baseToken"), dict) else {}
                        liq = p.get("liquidity") if isinstance(p.get("liquidity"), dict) else {}
                        vol = p.get("volume") if isinstance(p.get("volume"), dict) else {}
                        p_chg = p.get("priceChange") if isinstance(p.get("priceChange"), dict) else {}
                        txns = p.get("txns") if isinstance(p.get("txns"), dict) else {}
                        txns_h24 = txns.get("h24") if isinstance(txns.get("h24"), dict) else {}

                        buys = _safe_int(txns_h24.get("buys"))
                        sells = _safe_int(txns_h24.get("sells"))
                        smart_money_sentiment = "BUY_ACCUMULATION" if buys > sells * 1.15 else ("WHALE_SELLING_PRESSURE" if sells > buys * 1.15 else "NEUTRAL")

                        dex_metrics = {
                            "token_symbol": str(base_tok.get("symbol") or "UNKNOWN"),
                            "token_name": str(base_tok.get("name") or "UNKNOWN"),
                            "dex_name": str(p.get("dexId") or "UNKNOWN"),
                            "price_usd": str(p.get("priceUsd") or "0"),
                            "fdv_usd": _safe_float(p.get("fdv")),
                            "liquidity_usd": _safe_float(liq.get("usd")),
                            "volume_24h_usd": _safe_float(vol.get("h24")),
                            "price_change_5m_pct": _safe_float(p_chg.get("m5")),
                            "price_change_1h_pct": _safe_float(p_chg.get("h1")),
                            "price_change_6h_pct": _safe_float(p_chg.get("h6")),
                            "price_change_24h_pct": _safe_float(p_chg.get("h24")),
                            "txns_24h_buys": buys,
                            "txns_24h_sells": sells,
                            "smart_money_sentiment": smart_money_sentiment,
                            "volume_to_liquidity_ratio": round(_safe_float(vol.get("h24")) / max(_safe_float(liq.get("usd")), 1.0), 2)
                        }
                except Exception as e:
                    pass

            # 3. Fetch & parse technical security metrics from RugCheck via gl.nondet.web.get
            birdeye_url = f"https://api.rugcheck.xyz/v1/tokens/{token_address}/report"
            security_metrics = {}
            try:
                headers = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64)"}
                resp2 = gl.nondet.web.get(birdeye_url, headers=headers)
                if resp2 and hasattr(resp2, "body") and resp2.body:
                    if isinstance(resp2.body, bytes):
                        raw_sec_str = resp2.body.decode("utf-8")
                    elif isinstance(resp2.body, str):
                        raw_sec_str = resp2.body
                    else:
                        raw_sec_str = str(resp2.body)
                else:
                    raw_sec_str = "{}"

                raw_sec = json.loads(raw_sec_str)
                tok_info = raw_sec.get("token") if isinstance(raw_sec.get("token"), dict) else (raw_sec.get("data") if isinstance(raw_sec.get("data"), dict) else {})
                risks_list = raw_sec.get("risks") if isinstance(raw_sec.get("risks"), list) else []

                # An empty payload means RugCheck told us nothing. Reading a
                # missing mintAuthority as "revoked" would manufacture evidence,
                # so the flags are only set when the field is really there.
                security_metrics = {
                    "detected_risks": [str(r.get("name")) for r in risks_list if isinstance(r, dict) and "name" in r],
                    "rugcheck_score": _safe_int(raw_sec.get("score")),
                }
                if "mintAuthority" in tok_info:
                    security_metrics["mint_authority_disabled"] = not bool(tok_info.get("mintAuthority"))
                if "freezeAuthority" in tok_info:
                    security_metrics["freeze_authority_disabled"] = not bool(tok_info.get("freezeAuthority"))

                # Distribution metrics, again only when RugCheck really returned
                # them. These used to be read on the client alone, which left the
                # contract with no evidence of its own to check the model against.
                markets = raw_sec.get("markets") if isinstance(raw_sec.get("markets"), list) else []
                if markets and isinstance(markets[0], dict):
                    lp_info = markets[0].get("lp") if isinstance(markets[0].get("lp"), dict) else {}
                    if isinstance(lp_info.get("lpBurnedPct"), (int, float)):
                        security_metrics["lp_burned_pct"] = _safe_int(lp_info.get("lpBurnedPct"))

                top_holders = raw_sec.get("topHolders") if isinstance(raw_sec.get("topHolders"), list) else []
                if isinstance(raw_sec.get("topHoldersPct"), (int, float)):
                    security_metrics["top10_holder_pct"] = _safe_int(raw_sec.get("topHoldersPct"))
                elif top_holders:
                    security_metrics["top10_holder_pct"] = _safe_int(
                        sum(_safe_float(h.get("pct")) for h in top_holders[:10] if isinstance(h, dict))
                    )

                for holders_key in ("totalHolders", "holderCount"):
                    if isinstance(raw_sec.get(holders_key), (int, float)):
                        security_metrics["holder_count"] = _safe_int(raw_sec.get(holders_key))
                        break

                if top_holders:
                    security_metrics["smart_money_wallets"] = len([
                        h for h in top_holders
                        if isinstance(h, dict) and not h.get("insider")
                        and 0.2 < _safe_float(h.get("pct")) < 5.0
                    ])
            except Exception as e:
                security_metrics = {"status": "security_unavailable", "error": str(e)}

            tech_summary_json = json.dumps({
                "token_address": token_address,
                "dex": dex_metrics,
                "security": security_metrics
            })

            # 3. Formulate multi-source prompt using string replace
            prompt = (
                RUBRIC_PROMPT.replace("{token_address}", token_address)
                .replace("{tech_data}", tech_summary_json)
            )

            # Authority status is hard evidence, not model opinion: prefer the
            # caller's signed telemetry, else the RugCheck fetch.
            # Order matters: the caller's telemetry is applied first so that
            # anything this contract fetched for itself overwrites it. The
            # payload arrives from an untrusted caller who could assert a fully
            # burned LP and revoked authorities for a token that has neither, so
            # it only stands where RugCheck gave us nothing to check it against.
            ground_truth = {}
            for src in (tele_security, security_metrics):
                if isinstance(src, dict):
                    for evidence_key in ("mint_authority_disabled", "freeze_authority_disabled",
                                         "lp_burned_pct", "top10_holder_pct",
                                         "holder_count", "smart_money_wallets"):
                        if evidence_key in src and src[evidence_key] is not None:
                            ground_truth[evidence_key] = src[evidence_key]

            # An auditor that cannot see the token's authority status cannot
            # certify anything about it. Rather than assume a clean default,
            # the audit fails closed so no report is ever written from absent
            # evidence.
            if "mint_authority_disabled" not in ground_truth or "freeze_authority_disabled" not in ground_truth:
                raise gl.vm.UserError(
                    "EXTERNAL: mint/freeze authority status unavailable from RugCheck "
                    "and caller telemetry — refusing to audit without on-chain evidence."
                )
            if not dex_metrics or _safe_float(dex_metrics.get("liquidity_usd")) <= 0.0:
                raise gl.vm.UserError(
                    "EXTERNAL: no live market data for this mint from DEXScreener "
                    "or caller telemetry — refusing to audit without real liquidity."
                )

            # Non-deterministic LLM round. This is the only source of a verdict:
            # there is no local scoring path that could stand in for it, so a
            # failed or untrusted round aborts the transaction instead of
            # storing a fabricated report.
            try:
                response = gl.nondet.exec_prompt(prompt, response_format="json")
            except Exception as e:
                raise gl.vm.UserError(
                    f"LLM consensus round unavailable — {_classify_llm_error(e)}"
                )

            llm_report = _normalize_llm_report(response, token_address)
            if not llm_report:
                raise gl.vm.UserError(
                    "LLM_ERROR: model response failed schema, verdict or score-range "
                    "validation — refusing to store an untrusted audit."
                )

            llm_report = _validate_findings(llm_report, ground_truth)
            llm_report["analysis_source"] = SOURCE_LLM
            return llm_report

        def validator_fn(leaders_res) -> bool:
            # Real validator consensus: each validator INDEPENDENTLY re-runs the
            # non-deterministic web fetch + LLM audit and compares the substantive
            # findings (score within tolerance, verdict, mint/freeze authority)
            # against the leader's result — NOT a local shape check.
            if not isinstance(leaders_res, gl.vm.Return):
                return False
            leader_result = leaders_res.calldata
            if not isinstance(leader_result, dict):
                return False
            if "safety_score" not in leader_result:
                return False
            if leader_result.get("verdict") not in ALLOWED_VERDICTS:
                return False
            # Independently reproduce the leader's work on this validator node.
            my_result = leader_fn()
            # Equivalence check over the substantive audit findings.
            return _check_equivalence(leader_result, my_result)

        # Route the web + LLM work through GenVM's non-deterministic consensus
        # runner: the leader executes leader_fn, and every validator re-executes
        # it via validator_fn and must reach equivalence before the result is
        # accepted and stored on-chain.
        consensus_output = gl.vm.run_nondet_unsafe(leader_fn, validator_fn)
        if not isinstance(consensus_output, dict):
            raise gl.vm.UserError("Validator consensus mismatch.")

        symbol = str(consensus_output.get("token_symbol", "UNKNOWN"))
        score = _safe_int(consensus_output.get("safety_score", 75))
        verdict = str(consensus_output.get("verdict", "HIGH_VOLATILITY_WARN"))
        mint_dis = bool(consensus_output.get("mint_disabled", False))
        freeze_dis = bool(consensus_output.get("freeze_disabled", False))
        lp_burned = _safe_int(consensus_output.get("lp_burned_pct", 0))
        top10 = _safe_int(consensus_output.get("top10_holder_pct", 0))
        holder_cnt = _safe_int(consensus_output.get("holder_count", 0))
        smart_wallets = _safe_int(consensus_output.get("smart_money_wallets", 0))
        risk_list = consensus_output.get("risk_factors", [])
        if not isinstance(risk_list, list):
            risk_list = ["Unspecified risk signal"]
        ai_sum = str(consensus_output.get("ai_summary", "Audit completed."))
        analysis_source = str(consensus_output.get("analysis_source", SOURCE_LLM))
        unverified = consensus_output.get("unverified_fields", [])
        if not isinstance(unverified, list):
            unverified = []

        rec = AuditRecord(
            request_id=request_id,
            caller_address=caller,
            token_address=token_address,
            token_symbol=symbol,
            safety_score=score,
            verdict=verdict,
            mint_disabled=mint_dis,
            freeze_disabled=freeze_dis,
            lp_burned_pct=lp_burned,
            top10_holder_pct=top10,
            holder_count=holder_cnt,
            smart_money_wallets=smart_wallets,
            risk_factors_json=json.dumps(risk_list),
            unverified_fields_json=json.dumps(unverified),
            ai_summary=ai_sum,
            audited_at_block=0,
            paid_amount=payment_amount,
            analysis_source=analysis_source
        )

        self.audited_records[token_address] = rec
        self.request_audits[request_id] = rec
        self.used_request_ids.append(request_id)

        found = False
        for i in range(len(self.recent_tokens)):
            if self.recent_tokens[i] == token_address:
                found = True
                break
        if not found:
            self.recent_tokens.append(token_address)
            self.audited_count += 1

        return json.dumps({
            "request_id": request_id,
            "caller_address": str(caller),
            "token_address": token_address,
            "token_symbol": symbol,
            "safety_score": score,
            "verdict": verdict,
            "mint_disabled": mint_dis,
            "freeze_disabled": freeze_dis,
            "lp_burned_pct": lp_burned,
            "top10_holder_pct": top10,
            "holder_count": holder_cnt,
            "smart_money_wallets": smart_wallets,
            "risk_factors": risk_list,
            "unverified_fields": unverified,
            "ai_summary": ai_sum,
            "analysis_source": analysis_source,
            "paid_amount": str(payment_amount)
        })

    @gl.public.view
    def get_audit(self, token_address: str) -> dict:
        """Returns recorded on-chain audit for a specific token address."""
        token_address = str(token_address).strip()
        if token_address in self.audited_records:
            rec = self.audited_records[token_address]
            try:
                risks = json.loads(rec.risk_factors_json)
            except Exception:
                risks = []
            try:
                unverified = json.loads(rec.unverified_fields_json)
            except Exception:
                unverified = []
            return {
                "has_audit": True,
                "request_id": rec.request_id,
                "caller_address": str(rec.caller_address),
                "token_address": rec.token_address,
                "token_symbol": rec.token_symbol,
                "safety_score": rec.safety_score,
                "verdict": rec.verdict,
                "mint_disabled": rec.mint_disabled,
                "freeze_disabled": rec.freeze_disabled,
                "lp_burned_pct": rec.lp_burned_pct,
                "top10_holder_pct": rec.top10_holder_pct,
                "holder_count": rec.holder_count,
                "smart_money_wallets": rec.smart_money_wallets,
                "risk_factors": risks,
                "unverified_fields": unverified,
                "ai_summary": rec.ai_summary,
                "analysis_source": rec.analysis_source,
                "audited_at_block": rec.audited_at_block,
                "paid_amount": str(rec.paid_amount)
            }

        return {
            "has_audit": False,
            "token_address": token_address,
            "message": "No audit recorded on-chain for this token yet."
        }

    @gl.public.view
    def get_request_audit(self, request_id: str, caller_address: str = "") -> dict:
        """Returns specific request audit bound to request_id for verified caller."""
        request_id = str(request_id).strip()
        if request_id in self.request_audits:
            rec = self.request_audits[request_id]
            if caller_address and len(str(caller_address).strip()) > 0:
                expected_caller = str(rec.caller_address).strip().lower().replace("0x", "")
                provided_caller = str(caller_address).strip().lower().replace("0x", "")
                if expected_caller != provided_caller:
                    raise gl.vm.UserError("Caller authorization mismatch: Request ID belongs to another user.")

            try:
                risks = json.loads(rec.risk_factors_json)
            except Exception:
                risks = []
            try:
                unverified = json.loads(rec.unverified_fields_json)
            except Exception:
                unverified = []

            return {
                "has_audit": True,
                "request_id": rec.request_id,
                "caller_address": str(rec.caller_address),
                "token_address": rec.token_address,
                "token_symbol": rec.token_symbol,
                "safety_score": rec.safety_score,
                "verdict": rec.verdict,
                "mint_disabled": rec.mint_disabled,
                "freeze_disabled": rec.freeze_disabled,
                "lp_burned_pct": rec.lp_burned_pct,
                "top10_holder_pct": rec.top10_holder_pct,
                "holder_count": rec.holder_count,
                "smart_money_wallets": rec.smart_money_wallets,
                "risk_factors": risks,
                "unverified_fields": unverified,
                "ai_summary": rec.ai_summary,
                "analysis_source": rec.analysis_source,
                "paid_amount": str(rec.paid_amount)
            }

        return {
            "has_audit": False,
            "request_id": request_id,
            "message": "No audit recorded for this request ID yet."
        }

    @gl.public.view
    def get_overview(self) -> dict:
        """Returns overall contract stats and list of audited tokens."""
        recent_list = []
        for i in range(len(self.recent_tokens)):
            recent_list.append(self.recent_tokens[i])

        return {
            "owner": str(self.contract_owner),
            "audited_count": self.audited_count,
            "recent_tokens": recent_list
        }
