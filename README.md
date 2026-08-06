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

1. **Multi-Source Web Data Ingestion (`gl.nondet.get_webpage`)**:
   - Fetches DEXScreener token pairs (`https://api.dexscreener.com/latest/dex/tokens/{address}`) for price, 24h volume, liquidity pool depth, and buy/sell transaction count.
   - Fetches Birdeye / RugCheck security report (`https://api.rugcheck.xyz/v1/tokens/{address}/report`) for token mint authority, freeze authority, and top holder concentration metrics.
2. **Decentralized LLM Consensus (`gl.nondet.exec_prompt` & `gl.vm.run_nondet_unsafe`)**:
   - Leaders & Validators execute structured LLM prompts returning standard JSON security reports.
   - Comparative Equivalence (`_check_equivalence`) tolerates up to 10 points score variance while strictly requiring consensus on security verdicts (`SAFE_TO_TRADE`, `HIGH_VOLATILITY_WARN`, `CRITICAL_RUG_RISK`), `mint_disabled`, and `freeze_disabled` states.
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

### 🌐 Live GenLayer StudioNet Deployment & Explorer Links

- **Deployed Intelligent Contract Address**: [`0x6b944E229f32d822cE84292CB713fA8De4553a37`](file:///f:/Work/Cryoto/Gen%20layer/gen2/contracts/meme_rug_auditor.py)
- **Contract Explorer Link**: [https://explorer-studio.genlayer.com/address/0x6b944E229f32d822cE84292CB713fA8De4553a37](https://explorer-studio.genlayer.com/address/0x6b944E229f32d822cE84292CB713fA8De4553a37)
- **Deployment Tx Hash**: `0xbc38a6340c29dd3e374d149c0cb72d5b8aa6420f4c425656f91245f041e737e4`
- **Deployment Tx Explorer Link**: [https://explorer-studio.genlayer.com/tx/0xbc38a6340c29dd3e374d149c0cb72d5b8aa6420f4c425656f91245f041e737e4](https://explorer-studio.genlayer.com/tx/0xbc38a6340c29dd3e374d149c0cb72d5b8aa6420f4c425656f91245f041e737e4)
- **Audit SGL Token Tx Hash**: `0x63937a1484b288e077a8768e13bb7ea14a7e60487ce5e60d665baa4cda4a8878`
- **Audit SGL Tx Explorer Link**: [https://explorer-studio.genlayer.com/tx/0x63937a1484b288e077a8768e13bb7ea14a7e60487ce5e60d665baa4cda4a8878](https://explorer-studio.genlayer.com/tx/0x63937a1484b288e077a8768e13bb7ea14a7e60487ce5e60d665baa4cda4a8878)
- **GenVM Execution Result**: `SUCCESS`
- **Consensus Result**: `MAJORITY_AGREE` (ACCEPTED with 5/5 Validator Votes)

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
