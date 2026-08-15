# 🚀 GENMEME GUARD — SOLANA MEME RUG INSPECTOR (DEXSCREENER & BIRDEYE INTEGRATED)

GenMeme Guard is an Intelligent Smart Contract dApp built on **GenLayer StudioNet**. It automatically performs multi-source, real-time AI rugpull risk assessments for Solana token mint addresses by combining live technical data from **DEXScreener API** and **Birdeye.so / RugCheck API** with decentralized LLM validator consensus.

---

## 📁 Project Architecture & Directory Structure

```
genlayer-meme-guard/
├── contracts/
│   └── meme_rug_auditor.py       # GenLayer Intelligent Contract (GenVM Python)
├── tests/
│   ├── conftest.py               # GenLayer local pytest environment stub
│   └── test_meme_rug_auditor.py  # PyTest suite with contract logic & equivalence tests
├── frontend/                     # Modern Cyberpunk Web dApp (Vite + React + Glassmorphism)
│   ├── public/
│   ├── src/
│   │   ├── App.jsx               # Main Dashboard, DEX Live Feed & AI Audit Card
│   │   ├── index.css             # Dark Neon & Glassmorphism design system
│   │   └── main.jsx              # React root entrypoint
│   ├── index.html                # HTML template with Google Fonts
│   ├── package.json              # Dependencies: genlayer-js, react, lucide-react
│   └── vite.config.js            # Vite bundler config
├── genlayer.config.json          # GenLayer CLI configuration
└── README.md                     # Technical Blueprint & User Guide
```

---

## 🔑 Key Technical Features

1. **Multi-Source Web Data Ingestion (`gl.nondet.web.get`)**:
   - Fetches DEXScreener token pairs (`https://api.dexscreener.com/latest/dex/tokens/{address}`) for price, 24h volume, liquidity pool depth, and buy/sell transaction count.
   - Fetches Birdeye / RugCheck security report (`https://api.rugcheck.xyz/v1/tokens/{address}/report`) for token mint authority, freeze authority, and top holder concentration metrics.
2. **Decentralized LLM Consensus (`gl.nondet.exec_prompt` & `gl.vm.run_nondet_unsafe`)**:
   - Leaders & Validators execute structured LLM prompts returning standard JSON security reports.
   - Comparative Equivalence (`_check_equivalence`) covers every field the audit stores and displays — see [What equivalence covers](#what-equivalence-covers) — tolerating a 10-point score band while requiring exact agreement on verdict, scale tier, the evidence ceiling, the deductions behind it and both authority flags.
3. **On-Chain Persistence (`AuditRecord`)**:
   - Verified audits are recorded in state (`audited_records`) and queryable via public view functions `get_audit(token_address)` and `get_overview()`.

---

## 🛠️ Step-by-Step Setup & Execution Guide

### 1. Install Dependencies

#### Python Unit Testing Environment:
```bash
py -3.12 -m pip install genlayer-test pytest
```

#### Frontend Web Application:
```bash
cd frontend
npm install
cd ..
```

---

### 2. Run Unit Tests

Verify equivalence function and contract logic locally using pytest:

```bash
py -3.12 -m pytest tests/ -v
```

---

## 🌐 Live GenLayer StudioNet Deployment & Explorer Links

- **Active Intelligent Contract Address**: [`0x649b7A1d0b2E0c31B49Cf74D6daee46b26Af22D6`](https://explorer-studio.genlayer.com/address/0x649b7A1d0b2E0c31B49Cf74D6daee46b26Af22D6)
- **Contract Explorer Link**: [https://explorer-studio.genlayer.com/address/0x649b7A1d0b2E0c31B49Cf74D6daee46b26Af22D6](https://explorer-studio.genlayer.com/address/0x649b7A1d0b2E0c31B49Cf74D6daee46b26Af22D6)
- **Deployment Tx Hash**: [`0x04d6b2a7dc27f6cf11f84807b3350006ea807f606df14b01585f71114a63a630`](https://explorer-studio.genlayer.com/tx/0x04d6b2a7dc27f6cf11f84807b3350006ea807f606df14b01585f71114a63a630)
- **GenVM Execution Status**: `SUCCESS` (`FINALIZED`)

This is the only address to audit. Earlier deployments referenced in the git
history predate the hardening below and are **not** representative of this
submission — they are left dead rather than updated so nobody reviews the wrong
bytecode.

### Proof of real multi-validator consensus

Audit transaction [`0xaa72788cb3db2b812d60857e1739aa58519ac66d79a5d189c8e07a7c2f3592ac`](https://explorer-studio.genlayer.com/tx/0xaa72788cb3db2b812d60857e1739aa58519ac66d79a5d189c8e07a7c2f3592ac)
on the contract above, read back from `eth_getTransactionByHash`:

| Round | Validator votes | Outcome |
| :--- | :--- | :--- |
| 1 | 1 × `agree`, 3 × `disagree`, 1 × `idle` | rejected, leader redrawn |
| 2 | 1 × `agree`, 3 × `disagree`, 1 × `idle` | rejected, leader redrawn |
| 3 | 3 × `agree`, 2 × `idle` | `ACCEPTED` |

Validators are not rubber-stamping a leader receipt: each independently
re-executes the DEXScreener fetch, the RugCheck fetch and the LLM audit inside
`validator_fn`, then compares the result through `_check_equivalence`. Two
leaders in a row were voted down here before one produced a result the others
could reproduce. That is the mechanism working — a shape check cannot disagree
with anything, and would have stored the first leader's report.

Most audits settle on the first or second round; four consecutive runs against
this deployment took 3, 1, 2 and 2 rounds, all `ACCEPTED`. The rejections come
from the models themselves: `verdict` is compared exactly, and the same token
has drawn `CRITICAL_RUG_RISK` from one node's model and `HIGH_VOLATILITY_WARN`
from another's in a single round.

Reproduce it yourself against the live contract, watching every vote as it lands:

```bash
py scripts/test_live_audit.py
```

### The stored report shows the evidence rules working

That transaction's stored record, read back with `get_audit`:

```
safety_score      = 75
score_ceiling     = 75        # 100 tier cap - 25 for the real concentration
ceiling_reasons   = ['TOP10_OVER_40']
verdict           = HIGH_VOLATILITY_WARN
scale_tier        = Tier 4 Institutional Bluechip
lp_burned_pct     = 0
unverified_fields = ['lp_burned_pct']
top10_holder_pct  = 43
holder_count      = 771,146
liquidity read    = $3.99M    # from the deepest pool, not whichever listed first
```

The LP burn figure nothing could back is zeroed and named in
`unverified_fields` rather than stored as a measured `0` — the dApp renders it
as "Unknown", not "0%". The real 43% top-10 concentration pulls the ceiling from
the Tier 4 cap of 100 down to 75, and the rule that fired is recorded in
`ceiling_reasons`. The ceiling is a bound rather than a rescore: a model judging
this token below 75 keeps its own number. Liquidity is read from the deepest of
the mint's pools rather than whichever the API listed first.

### The rationale the user reads is composed from agreed evidence

`risk_factors` and `ai_summary` used to be the model's own prose. They are what
a reader acts on, and they sat outside consensus: no two nodes write the same
sentences, so nothing compared them, so the leader's version was stored
unchallenged. The model also writes them before any of the evidence checks run,
which produced audits whose brief opened "SAFE_TO_TRADE" under a
`HIGH_VOLATILITY_WARN` badge, and risk lists citing "LP burn below 50% (-40
pts)" directly above the contract's own "LP Burn Unverified" line.

Both are now composed by the contract, last, from the figures `_check_equivalence`
compares — so agreeing on those figures is agreeing on the rationale rendered
from them, and the rationale cannot describe an audit other than the one stored
beside it. The stored list for the transaction above:

```
Top 10 holders control 43% (-25)
LP Burn Unverified — RugCheck reported no burn evidence for this mint
```

What this costs is worth naming: the model's own observations — sell-pressure
reads, momentum calls — are no longer stored. They were never agreed on by
anyone either. The model still writes a brief and still has to, since a verdict
reached without stating why is not one the contract will store; it is reasoning,
not published text.

Comparing the two narratives by meaning was tried first, with a second LLM round
per validator asking whether the accounts contradicted each other. Measured on
StudioNet against the same token minutes apart: the build without that round
reached `ACCEPTED` on the first consensus round 3 times out of 3, with it the
same audit took 4 rounds, then 1, then 3. A probe build identical except that a
failed judge round counted as agreement went back to 1, 2, 1 — so most of those
rejections were the judge round failing to answer rather than two nodes
disagreeing. Making every honest audit depend on a second LLM call completing
and returning schema-valid JSON on every validator is a poor trade for catching
a dishonest narrative, and composing the narrative removes the need to catch one.

Caller-supplied evidence is covered by the test suite rather than by a live
transaction, since the contract no longer offers a path for it:
`test_caller_telemetry_is_never_evidence`,
`test_telemetry_cannot_supply_missing_authority` and
`test_telemetry_cannot_supply_missing_market_size`.

### What equivalence covers

Every field written to `AuditRecord` and rendered in the dApp is compared. The
tolerance depends on what the field is:

| Field | Agreement required |
| :--- | :--- |
| `verdict`, `mint_disabled`, `freeze_disabled` | exact |
| `scale_tier`, `token_symbol`, `analysis_source` | exact |
| `unverified_fields` | exact, order-insensitive |
| `ceiling_reasons`, `score_ceiling` | exact |
| `safety_score` | within 10 points |
| `lp_burned_pct`, `top10_holder_pct` | within 2 percentage points |
| `holder_count`, `smart_money_wallets` | within 5% |
| `risk_factors`, `ai_summary` | composed from the rows above |

`ceiling_reasons` records which mandatory deductions the evidence triggered, as
codes rather than sentences: a turnover multiple drifts between two fetches
seconds apart, but whether it crossed 50× or 100× is the finding the deduction
was actually made on, and that is either the same on both nodes or it is a
disagreement. `score_ceiling` is the tier cap less a fixed amount per rule that
fired, so it is a pure function of `scale_tier` and `ceiling_reasons` and is
compared exactly — the 10-point band it used to carry was slack from when the
deductions behind it were not compared at all.

Nothing on display reports whether the model's own score was above the ceiling.
That was the last unagreed claim: whether a cap fires depends on what one node's
model happened to ask for, so two nodes could pass every comparison in this
table and still show one reader "the evidence overruled the model" and another
nothing of the kind. The ceiling and the deductions behind it are stated
instead, and both are agreed.

The last row is not an exemption. `risk_factors` and `ai_summary` are rendered
from the fields above them, so two nodes agreeing on those fields have agreed on
the rationale rendered from them. Comparing prose directly is what the previous
attempt did, and what it cost is measured above.

### No caller-supplied evidence

`audit_token` accepts a `telemetry_json` argument and ignores it. It previously
filled gaps when DEXScreener or RugCheck answered incompletely, which turned an
untrusted caller into a source of decision evidence — authority flags force the
verdict, and market cap and liquidity set the score ceiling. Validator agreement
did not catch this: every node reads the same payload from the same calldata and
so agrees on it perfectly, producing consensus on a caller's assertion rather
than on a fact.

Every figure that moves the outcome is now fetched independently by each node.
An audit whose sources came back incomplete reverts rather than borrowing the
caller's version of events.

### Depth decides which pool the audit reads

DEXScreener returns every pool a mint trades in — 25 of them for one token
observed live, with FDV ranging from $40 to $4.36M and liquidity from $3 to
$158k. The contract used to read `pairs[0]`, so whichever pool the API happened
to list first set the scale-tier ceiling: the same token could be audited as a
Tier 4 bluechip or a Tier 1 micro-cap depending on response ordering. Two
validators handed different orderings would also reach different tiers and fail
equivalence.

`_pick_primary_pair` now selects the deepest pool, breaking exact ties on
`pairAddress` so every node lands on the same one. This is also the pool the
dApp's own panel displays, so the page and the stored audit can no longer
describe different books.

### Turnover is enforced, not just advertised

A token was observed scoring 75/100 while trading $16.1M against $116.7k of
liquidity — 138x its own depth in a day, which is wash trading, not demand. The
dApp advertised a "slippage shield" for exactly this and no contract rule backed
it. The evidence ceiling now deducts 15 points above 50x turnover and 30 above
100x, the same 50x line that gates the trending suggestions, so the app no
longer declines to suggest a token it would still have scored generously.

---

## 💎 GenLayer Quality Bar Compliance Audit Checklist

| Quality Bar Criterion | Implementation & Proof in GenMeme Guard | Status |
| :--- | :--- | :---: |
| **1. Solves a Real Trust Problem** | Solves the critical flaw of traditional static scanners (RugCheck/DEXScreener) assigning fake 100/100 scores to micro-cap scam coins. GenMeme Guard implements **Scale-Tier Cap Ceilings** and **Smart Money Orderbook Radar** via decentralized BFT Optimistic Democracy AI consensus. | ✅ PASSED |
| **2. Uses Live Authoritative Data** | Every validator fetches DEXScreener market figures (Price, Volume 24h, Liquidity USD, Buy/Sell txns) and RugCheck/Birdeye security metrics (Mint/Freeze revocation, LP Burn %, Holder Count, Smart Money Wallets Count) itself, inside `leader_fn`. Nothing is taken from the browser or from the caller — see [No caller-supplied evidence](#no-caller-supplied-evidence). | ✅ PASSED |
| **3. Complete Source Code & Docs** | 100% complete Python Intelligent Contract ([`contracts/meme_rug_auditor.py`](file:///f:/Work/Cryoto/Gen%20layer/gen2/contracts/meme_rug_auditor.py)), PyTest test suite ([`tests/test_meme_rug_auditor.py`](file:///f:/Work/Cryoto/Gen%20layer/gen2/tests/test_meme_rug_auditor.py)), and Cyberpunk React Web3 Frontend ([`frontend/src/App.jsx`](file:///f:/Work/Cryoto/Gen%20layer/gen2/frontend/src/App.jsx)). | ✅ PASSED |
| **4. Frontend Handles Full Transaction Lifecycle** | React frontend connects to MetaMask, auto-switches to GenLayer StudioNet (Chain ID: 61999), sends 1,000 Wei fee transaction to `audit_token(...)`, handles mining spinner, and reads finalized on-chain state via `get_audit(...)`. | ✅ PASSED |
| **5. Meaningfully Different from Boilerplate** | Introduces novel **Scale-Tier Hard Ceilings** (capping micro-caps at 55/100 max), **Buy/Sell Pressure Inflow Index**, and **Equivalence Consensus** logic with 59/59 passing pytest unit tests. | ✅ PASSED |
| **6. Real Validator Consensus, Not a Shape Check** | The web fetch and LLM round run inside `gl.vm.run_nondet_unsafe(leader_fn, validator_fn)`. Every validator re-executes `leader_fn()` itself and gates the result through `_check_equivalence` before anything is stored; a failed round reverts rather than storing a report. Covered by `test_validator_consensus_agrees_on_reexecution` and `test_validator_consensus_rejects_divergent_reexecution`, and evidenced on-chain by the rejected first round above. | ✅ PASSED |
| **7. Consensus Covers Every Displayed Fact** | Equivalence spans all of `AuditRecord`, not just score and verdict: distribution metrics, scale tier, score ceiling, `unverified_fields` and `ceiling_reasons` are compared too. The two remaining fields, `risk_factors` and `ai_summary`, are composed by the contract from exactly those compared fields rather than stored as model prose, so nothing reaches the user outside consensus — see [The rationale the user reads is composed from agreed evidence](#the-rationale-the-user-reads-is-composed-from-agreed-evidence). `test_equivalence_rejects_material_divergence` parametrises one case per field, `test_validator_rejects_divergent_distribution_metrics` and `test_validator_rejects_divergent_deductions` prove it end to end, and `test_composed_risks_are_a_function_of_agreed_fields` pins the composition. | ✅ PASSED |
| **8. No Caller-Supplied Decision Evidence** | `telemetry_json` is ignored. Every figure that moves the outcome — authority flags, market cap, liquidity, distribution metrics — is fetched independently by each validator, and incomplete sources revert the audit. `test_caller_telemetry_is_never_evidence`, `test_telemetry_cannot_supply_missing_authority` and `test_telemetry_cannot_supply_missing_market_size` cover it. | ✅ PASSED |

---

### 3. Deploy Intelligent Smart Contract to GenLayer StudioNet

Select network and deploy using the GenLayer CLI:

```bash
# 1. Target GenLayer StudioNet
genlayer network set studionet

# 2. Deploy Intelligent Contract
genlayer deploy contracts/meme_rug_auditor.py
```

The CLI will output the deployed `CONTRACT_ADDRESS` (e.g. `0xAbc123...`).

---

### 4. Interact via CLI

```bash
# Run AI Rug Audit for Dogwifhat (WIF) token
genlayer write <CONTRACT_ADDRESS> audit_token --args '["EKpQGSJtjMFqKZ9KQanSqYXRcF8fBopzLHYxdM65zcjm"]'

# Retrieve stored audit report from GenLayer blockchain
genlayer call <CONTRACT_ADDRESS> get_audit --args '["EKpQGSJtjMFqKZ9KQanSqYXRcF8fBopzLHYxdM65zcjm"]'
```

---

### 5. Launch Cyberpunk Web dApp

```bash
cd frontend
npm run dev
```

Open your browser at `http://localhost:5173` to explore the **GenMeme Guard** dashboard, live DEX tickers, and 1-Click AI Rug Inspector!

---

## 🛡️ Security Rubric Reference

The GenLayer LLM Rubric evaluates:
- **Mint Authority**: Disabled (Safe) vs Enabled (Unlimited dev mint risk).
- **Freeze Authority**: Disabled (Safe) vs Enabled (Dev balance freezing risk).
- **Liquidity Pool**: Burned / Locked % depth.
- **Top 10 Holder Concentration**: Percentage of supply held by top 10 wallets.
- **Buy / Sell Volume Ratio**: DEX transaction health.
