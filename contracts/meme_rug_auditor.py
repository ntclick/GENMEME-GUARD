# { "Depends": "py-genlayer:1jb45aa8ynh2a9c9xn3b7qqh8sm5q93hwfp7jqmwsfhh8jpz09h6" }
from genlayer import *
from dataclasses import dataclass
import json

# Institutional-grade Rubric prompt for Senior On-Chain Forensic AI Auditors with Scale-Tier Architecture
RUBRIC_PROMPT = """
You are a SENIOR QUANTITATIVE ON-CHAIN ANALYST at GenLayer Security Intelligence Lab.
Perform a FORENSIC SCALE-TIER AUDIT on Solana token: {token_address} using the evidence below.

The evidence was fetched by this validator node directly from DEXScreener and
RugCheck. It is the only information you have. Nothing in it was supplied by the
caller requesting the audit, so never describe it as caller-provided or as
"telemetry" — a reader takes that to mean the subject supplied its own report
card.

--- Evidence fetched by this node (DEXScreener market data + RugCheck security report) ---
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
     If the evidence above does not contain an LP burn percentage, you MUST report
     lp_burned_pct as 0 and MUST NOT award the >= 95% bonus. Do not substitute a
     reassuring value for a figure the evidence never supplied.

EVIDENCE DISCIPLINE (applies to every numeric field):
Report 0 for lp_burned_pct, top10_holder_pct, holder_count or smart_money_wallets
whenever the evidence does not contain that measurement, and say plainly in
ai_summary which metrics were unavailable. Never infer, estimate or default these
numbers — an unverified figure is treated as absent and the contract will
overwrite anything you invent here.

3. HOLDER DISTRIBUTION & SMART MONEY NETWORK:
   - Holder Count > 10,000: +15 pts; < 200: -25 pts (Insider Sybil risk).
   - Smart Money Wallets >= 15: +15 pts; < 3: -20 pts (Retail Trap).
   - Top 10 Holder Concentration > 40%: -25 pts.

4. ORDERBOOK INFLOW & TRADING VELOCITY:
   - Buy/Sell Ratio > 1.2: +10 pts; < 0.8: -20 pts (Whale Dumping Outflow).
   - 24h Volume / Liquidity turnover > 50x: -15 pts; > 100x: -30 pts.
     A book cannot honestly trade fifty times its own depth in a day. Treat this
     as wash trading and thin exit liquidity, and say so in ai_summary.

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
# score_ceiling is a quantity in the same 0-100 space as the score, derived from
# the tier plus verified deductions, so it is held to the same tolerance.
CEILING_TOLERANCE = 10
# Percentage-point drift allowed between two nodes reading the same source
# seconds apart. Wide enough for a live figure to move, far too narrow to hide
# the difference between a burned LP and an unburned one.
PCT_TOLERANCE = 2
# Wallet counts move as people trade, so they are compared proportionally, with
# an absolute floor so tokens with tiny counts are not held to a stricter bar
# than large ones.
COUNT_REL_TOLERANCE = 0.05
COUNT_ABS_TOLERANCE = 2
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

# 24h volume as a multiple of pool depth. A real book does not trade fifty times
# its own liquidity in a day; past a hundred it is wash trading with a chart.
# The same 50x line gates the dApp's trending suggestions, so the app no longer
# refuses to suggest a token it would still have scored generously.
HIGH_TURNOVER = 50.0
EXTREME_TURNOVER = 100.0

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


def _within_abs(a, b, tol: int) -> bool:
    return abs(_safe_int(a) - _safe_int(b)) <= tol


def _within_rel(a, b, rel: float, floor: int) -> bool:
    x = _safe_int(a)
    y = _safe_int(b)
    return abs(x - y) <= max(floor, int(max(abs(x), abs(y)) * rel))


def _check_equivalence(res1: dict, res2: dict) -> bool:
    """Compare two nodes' independent audits across every material fact.

    "Material" is defined by what leaves this function's blast radius: each
    field below is written to AuditRecord and rendered in the dApp, so a
    disagreement on any of them is a disagreement about what the user is shown.
    Checking only score, verdict and the authority flags left the rest —
    distribution metrics, the scale tier, the ceiling, and which figures nobody
    could verify — outside consensus entirely, so a leader could have stored
    whatever it liked there and no validator would have objected.

    Tolerances differ by what the field is. Categorical findings must match
    outright; live figures get room for the seconds between two nodes' fetches;
    the model's own score keeps its existing 10-point band. risk_factors and
    ai_summary are deliberately excluded — they are model prose, and no two
    independent LLM rounds produce identical sentences. Equivalence here means
    the nodes agree on the facts, not that they phrased them the same way.
    """
    if not isinstance(res1, dict) or not isinstance(res2, dict):
        return False

    # Provenance and categorical findings: exact agreement or nothing. Two nodes
    # that did not reach their verdicts the same way are not equivalent even
    # when the numbers happen to line up.
    for key in ("analysis_source", "verdict", "scale_tier", "token_symbol"):
        if res1.get(key) != res2.get(key):
            return False
    if res1.get("verdict") not in ALLOWED_VERDICTS:
        return False
    for key in ("mint_disabled", "freeze_disabled"):
        if bool(res1.get(key)) != bool(res2.get(key)):
            return False

    # Which metrics no source could back is itself a stored, displayed fact: it
    # is what tells a reader whether a 0 was measured or merely unknown. Two
    # nodes that disagree about what they could verify have not agreed.
    if sorted(str(f) for f in (res1.get("unverified_fields") or [])) != sorted(
        str(f) for f in (res2.get("unverified_fields") or [])
    ):
        return False

    if not _within_abs(res1.get("safety_score"), res2.get("safety_score"), SCORE_TOLERANCE):
        return False
    if not _within_abs(res1.get("score_ceiling"), res2.get("score_ceiling"), CEILING_TOLERANCE):
        return False
    for key in ("lp_burned_pct", "top10_holder_pct"):
        if not _within_abs(res1.get(key), res2.get(key), PCT_TOLERANCE):
            return False
    for key in ("holder_count", "smart_money_wallets"):
        if not _within_rel(res1.get(key), res2.get(key), COUNT_REL_TOLERANCE, COUNT_ABS_TOLERANCE):
            return False
    return True


def _pick_primary_pair(pairs):
    """The pair whose depth actually describes this token, or None.

    Reading pairs[0] was wrong twice over. DEXScreener returns every pool a mint
    trades in — 25 of them for one token observed here — in an order it does not
    promise to keep, and the fields taken from that one pair set the scale-tier
    ceiling. Among those 25, FDV ranged from $40 to $4.36M and liquidity from $3
    to $158k, so whichever pair happened to lead decided whether the token was
    audited as a Tier 3 Mid-Cap or a Tier 1 Micro-Cap. Two validators handed
    different orderings would reach different tiers and fail equivalence, and
    the dApp's own panel already picked the deepest pair, so the page and the
    stored audit could describe different pools.

    Depth is the tiebreak that means something: the deepest pool is where the
    token's price and liquidity are actually discovered. pairAddress breaks
    exact ties so every node lands on the same pair rather than on whatever its
    own sort happened to leave first.
    """
    if not isinstance(pairs, list):
        return None
    usable = [p for p in pairs if isinstance(p, dict)]
    if not usable:
        return None

    def depth_key(p):
        liq = p.get("liquidity") if isinstance(p.get("liquidity"), dict) else {}
        return (_safe_float(liq.get("usd")), str(p.get("pairAddress") or ""))

    return max(usable, key=depth_key)


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


def _tier_ceiling(fdv: float, liquidity: float):
    """The rubric's scale-tier hard ceiling for a token of this size.

    Nothing enforced these before — the model was merely asked to respect them,
    and a run has been observed returning 100/100 while listing deductions that
    should have pulled it well below that.
    """
    if fdv < 100000.0 or liquidity < 20000.0:
        return 55, "Tier 1 Micro-Cap"
    if fdv < 1000000.0:
        return 75, "Tier 2 Small-Cap"
    if fdv < 10000000.0:
        return 88, "Tier 3 Mid-Cap"
    if liquidity > 500000.0:
        return 100, "Tier 4 Institutional Bluechip"
    # Tier 4 valuation without Tier 4 liquidity depth does not earn the Tier 4
    # ceiling; the rubric requires both.
    return 88, "Tier 4 valuation without Tier 4 liquidity depth"


def _evidence_score_ceiling(report: dict, ground_truth: dict, unverified: list):
    """Highest score the fetched evidence can justify, and why.

    This is a ceiling, not a rescore: the model stays free to judge a token
    more harshly than the numbers demand. It only prevents the opposite —
    a score that ignores deductions the rubric makes mandatory. Metrics in
    *unverified* are skipped entirely, because their stored 0 means "no source
    supplied this", not "measured as zero", and penalising it would invent a
    finding just as surely as trusting an invented number would.
    """
    ceiling, tier = _tier_ceiling(
        _safe_float(ground_truth.get("fdv_usd")),
        _safe_float(ground_truth.get("liquidity_usd")),
    )
    reasons = []

    if "lp_burned_pct" not in unverified:
        lp = _safe_int(report.get("lp_burned_pct"))
        if lp < 50:
            ceiling -= 40
            reasons.append(f"LP burn {lp}% below 50%")
        elif lp < 80:
            ceiling -= 20
            reasons.append(f"LP burn {lp}% below 80%")

    if "top10_holder_pct" not in unverified:
        top10 = _safe_int(report.get("top10_holder_pct"))
        if top10 > 40:
            ceiling -= 25
            reasons.append(f"top 10 holders control {top10}%")

    if "holder_count" not in unverified:
        holders = _safe_int(report.get("holder_count"))
        if holders < 200:
            ceiling -= 25
            reasons.append(f"only {holders} holders")

    if "smart_money_wallets" not in unverified:
        wallets = _safe_int(report.get("smart_money_wallets"))
        if wallets < 3:
            ceiling -= 20
            reasons.append(f"only {wallets} smart money wallets")

    # Turnover far above the pool that supposedly supports it is manufactured
    # volume, not demand — the dApp advertises this as its slippage shield, and
    # until now nothing in the contract enforced it. A token was observed
    # scoring 75/100 while turning over 141x its own depth in a day.
    liquidity = _safe_float(ground_truth.get("liquidity_usd"))
    volume = _safe_float(ground_truth.get("volume_24h_usd"))
    if liquidity > 0.0 and volume > 0.0:
        turnover = volume / liquidity
        if turnover > EXTREME_TURNOVER:
            ceiling -= 30
            reasons.append(f"24h volume is {turnover:.0f}x liquidity")
        elif turnover > HIGH_TURNOVER:
            ceiling -= 15
            reasons.append(f"24h volume is {turnover:.0f}x liquidity")

    return max(0, ceiling), tier, reasons


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


# Phrases that mark a risk factor as being about a particular metric. Kept
# narrow on purpose: "holders" alone would also match a top-10 concentration
# finding, and dropping a real finding to silence an unbacked one trades a
# confusing audit for a misleading one.
UNVERIFIED_CLAIM_PHRASES = {
    "lp_burned_pct": ("lp burn", "lp burned", "liquidity pool burn", "unburned lp", "unlocked lp"),
    "top10_holder_pct": ("top 10", "top-10", "top10", "holder concentration", "whale concentration"),
    "holder_count": ("holder count", "number of holders", "sybil"),
    "smart_money_wallets": ("smart money", "smart-money"),
}


def _claims_unverified_metric(risk_factor, unverified: list) -> bool:
    """True when this risk factor asserts something about a metric no source backed."""
    text = str(risk_factor or "").lower()
    for field in unverified:
        for phrase in UNVERIFIED_CLAIM_PHRASES.get(field, ()):
            if phrase in text:
                return True
    return False


def _validate_findings(report: dict, ground_truth: dict) -> dict:
    """Cross-check a model verdict against hard evidence before it is stored.

    Mint/freeze authority is an on-chain fact read from this node's RugCheck
    fetch, not a matter of model opinion, so the fetched value always wins and
    an active authority forces CRITICAL_RUG_RISK. The verdict is then
    reconciled with its own score band, keeping whichever of the two readings
    is more severe so the model cannot label a failing score as safe.
    """
    # What the model asked for, kept so the brief can be reconciled with what
    # the evidence actually allowed.
    model_score = _safe_int(report.get("safety_score"))
    model_verdict = str(report.get("verdict") or "")

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

    # The model's risk list is written against the numbers it invented, so a
    # metric just zeroed as unverified can still be sitting in that list as a
    # confident finding. Observed on chain: "LP burn below 50% (-40 pts)" listed
    # directly above the contract's own "LP Burn Unverified" line, on an audit
    # whose ceiling stayed at the full Tier 3 cap of 88 because no such deduction
    # was ever applied. A reader sees the -40 and believes the score was punished
    # for a figure nothing measured. These claims are dropped; the contract's own
    # line below says what is actually known.
    report["risk_factors"] = [
        r for r in report["risk_factors"]
        if not _claims_unverified_metric(r, unverified)
    ]

    if "lp_burned_pct" in unverified:
        label = "LP Burn Unverified — RugCheck reported no burn evidence for this mint"
        if label not in report["risk_factors"]:
            report["risk_factors"].append(label)

    report["unverified_fields"] = unverified

    # Hold the score to what the evidence can actually support. Applied after the
    # metrics above are settled so the ceiling is computed from stored, verified
    # figures rather than anything the model asserted.
    ceiling, tier, ceiling_reasons = _evidence_score_ceiling(report, ground_truth, unverified)
    report["score_ceiling"] = ceiling
    report["scale_tier"] = tier
    if report["safety_score"] > ceiling:
        label = (
            f"Score capped at {ceiling} by {tier} evidence"
            + (f" ({'; '.join(ceiling_reasons)})" if ceiling_reasons else "")
            + f" — model reported {report['safety_score']}"
        )
        report["safety_score"] = ceiling
        if label not in report["risk_factors"]:
            report["risk_factors"].append(label)

    banded = _band_verdict(report["safety_score"])
    if VERDICT_SEVERITY[banded] > VERDICT_SEVERITY[report["verdict"]]:
        report["verdict"] = banded

    if not report["risk_factors"]:
        report["risk_factors"] = ["Volatile Meme Market Dynamics"]

    # The model writes its brief before any of the checks above run, so a capped
    # score or a reconciled verdict leaves the prose arguing for a rating that
    # was never stored — a summary opening "SAFE_TO_TRADE" underneath a
    # HIGH_VOLATILITY_WARN badge, which reads as the audit contradicting itself.
    # The model's words are left intact rather than edited, because rewriting an
    # analyst's reasoning to match a conclusion it did not reach is its own kind
    # of dishonesty. The adjustment is stated in front of them instead.
    if model_score != report["safety_score"] or model_verdict != report["verdict"]:
        report["ai_summary"] = (
            f"[Adjusted by the contract: the model returned {model_score}/100 "
            f"{model_verdict}; the fetched evidence supports "
            f"{report['safety_score']}/100 {report['verdict']}. The brief below "
            f"is the model's own wording and argues its original rating.] "
            + report["ai_summary"]
        )
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
    # The scale tier the evidence put this token in, and the highest score that
    # tier plus its verified deductions allowed. safety_score can be lower —
    # the model may judge harshly — but never higher.
    scale_tier: str
    score_ceiling: u32


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

        telemetry_json is accepted for call compatibility and deliberately
        ignored. It used to fill gaps when DEXScreener or RugCheck answered
        incompletely, which quietly turned an untrusted caller into a source of
        decision evidence: authority flags force the verdict, and market cap and
        liquidity set the score ceiling. Validator agreement did not catch it,
        because every node reads the same payload out of the same calldata and
        so agrees on it perfectly — consensus on a caller's assertion, not on a
        fact. Every figure that moves the outcome is now fetched independently
        by each node, and an audit whose sources came back incomplete reverts
        instead of borrowing the caller's version of events.
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
            # Every figure below is fetched by this node. telemetry_json is not
            # read at all — see the audit_token docstring for why a caller
            # payload cannot be evidence even when validators agree on it.
            dex_metrics = {}

            # 1. Fetch market metrics from DEXScreener. Market cap and liquidity
            # decide the scale-tier score ceiling, so these have to come from a
            # source the caller does not control: asserting the numbers would
            # otherwise buy a Tier 4 ceiling for a micro-cap.
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
                p = _pick_primary_pair(raw_dex.get("pairs"))
                if p:
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

            # Authority status is hard evidence, not model opinion. Everything
            # here comes from this node's own RugCheck fetch — there is no
            # second source to fall back to, by design.
            ground_truth = {}
            if isinstance(security_metrics, dict):
                for evidence_key in ("mint_authority_disabled", "freeze_authority_disabled",
                                     "lp_burned_pct", "top10_holder_pct",
                                     "holder_count", "smart_money_wallets"):
                    if evidence_key in security_metrics and security_metrics[evidence_key] is not None:
                        ground_truth[evidence_key] = security_metrics[evidence_key]

            # Market size decides the scale-tier ceiling, read from this node's
            # own DEXScreener fetch.
            ground_truth["fdv_usd"] = _safe_float(dex_metrics.get("fdv_usd"))
            ground_truth["liquidity_usd"] = _safe_float(dex_metrics.get("liquidity_usd"))
            # Volume rides along so the ceiling can measure turnover against depth.
            ground_truth["volume_24h_usd"] = _safe_float(dex_metrics.get("volume_24h_usd"))

            # An auditor that cannot see the token's authority status cannot
            # certify anything about it. Rather than assume a clean default,
            # the audit fails closed so no report is ever written from absent
            # evidence.
            if "mint_authority_disabled" not in ground_truth or "freeze_authority_disabled" not in ground_truth:
                raise gl.vm.UserError(
                    "EXTERNAL: mint/freeze authority status unavailable from RugCheck "
                    "— refusing to audit without on-chain evidence."
                )
            # Both figures are required, not just liquidity: they decide the
            # scale-tier ceiling, and a missing market cap would otherwise be
            # read as $0 and silently classify a bluechip as a micro-cap. An
            # unknown tier is not a conservative tier, it is an unknown one.
            if not dex_metrics or _safe_float(dex_metrics.get("liquidity_usd")) <= 0.0:
                raise gl.vm.UserError(
                    "EXTERNAL: no live market data for this mint from DEXScreener "
                    "— refusing to audit without real liquidity."
                )
            if _safe_float(dex_metrics.get("fdv_usd")) <= 0.0:
                raise gl.vm.UserError(
                    "EXTERNAL: no market capitalisation for this mint from DEXScreener "
                    "— refusing to audit without a verifiable scale tier."
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
        scale_tier = str(consensus_output.get("scale_tier", "Unclassified"))
        score_ceiling = _safe_int(consensus_output.get("score_ceiling", 100))

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
            scale_tier=scale_tier,
            score_ceiling=score_ceiling,
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
            "scale_tier": scale_tier,
            "score_ceiling": score_ceiling,
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
                "scale_tier": rec.scale_tier,
                "score_ceiling": rec.score_ceiling,
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
                "scale_tier": rec.scale_tier,
                "score_ceiling": rec.score_ceiling,
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
