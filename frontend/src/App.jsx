import React, { useState, useEffect } from 'react';
import { createClient, chains } from 'genlayer-js';
import {
  ShieldCheck,
  ShieldAlert,
  Lock,
  Unlock,
  Wallet,
  Sliders,
  ExternalLink,
  FileCode,
  Search,
  Cpu,
  RefreshCw,
  Activity,
  Zap,
  Coins,
  DollarSign,
  Percent,
  TrendingUp,
  Clock,
  Database,
  Sparkles,
  CheckCircle2,
  AlertTriangle,
  Award
} from 'lucide-react';

const DEFAULT_CONTRACT = '0x2e06779f31E6E29041e9E2402472427a6e1882Fc';
const STUDIONET_RPC_URL = 'https://studio.genlayer.com/api';
const EXPLORER_BASE_URL = 'https://explorer-studio.genlayer.com';

const genClient = createClient({
  chain: chains.studionet,
  endpoint: STUDIONET_RPC_URL
});

const GENLAYER_STUDIONET_CHAIN = {
  chainId: '0xf22f', // 61999 in hex
  chainName: 'GenLayer StudioNet',
  nativeCurrency: { name: 'GEN', symbol: 'GEN', decimals: 18 },
  rpcUrls: [STUDIONET_RPC_URL],
  blockExplorerUrls: [EXPLORER_BASE_URL]
};

const PRESET_TOKENS = [
  { symbol: 'SGL', name: 'Singularity Layer', address: '5c4HyD2rSShqnTsf5z3SaoD2H3GE452u2CUuYjviBAGS' },
  { symbol: 'WIF', name: 'Dogwifhat', address: 'EKpQGSJtjMFqKZ9KQanSqYXRcF8fBopzLHYxdM65zcjm' },
  { symbol: 'BONK', name: 'Bonk', address: 'DezXAZ8z7PnrnRJjz3wXBoRgixCa6xjnB7YaB1pPB263' },
  { symbol: 'POPCAT', name: 'Popcat', address: '7GCihgDB8fe6KNjn2MYtkzZcRjQy3t9GHdC8uHYmW2hr' },
  { symbol: 'TRUMP', name: 'Official Trump', address: '6p6xgHyF7AeE6TZkSmFsko444wqoP15icUSqi2jfPump' },
];

// Helper to switch or add GenLayer StudioNet chain (Chain ID: 61999 -> 0xf22f)
const ensureGenLayerNetwork = async () => {
  if (typeof window.ethereum === 'undefined') return false;

  try {
    const currentChainId = await window.ethereum.request({ method: 'eth_chainId' });
    if (currentChainId === '0xf22f' || currentChainId === '0xF22F' || parseInt(currentChainId, 16) === 61999) {
      return true;
    }

    try {
      await window.ethereum.request({
        method: 'wallet_switchEthereumChain',
        params: [{ chainId: '0xf22f' }],
      });
      return true;
    } catch (switchError) {
      if (switchError.code === 4902 || (switchError.message && switchError.message.includes('Unrecognized chain ID'))) {
        await window.ethereum.request({
          method: 'wallet_addEthereumChain',
          params: [GENLAYER_STUDIONET_CHAIN],
        });
        return true;
      }
    }
  } catch (e) {
    console.error('Network switch/add error:', e);
  }
  return false;
};

// Directly read real audit report from contract via genClient.readContract (100% FINALIZED ON-CHAIN BLOCK STATE & REQUEST-ID ISOLATION)
async function fetchStudioNetAuditReport(contractAddr, tokenAddr, requestId = '', callerAddr = '') {
  if (!tokenAddr || !tokenAddr.trim()) return null;
  try {
    if (requestId && requestId.trim()) {
      const reqRes = await genClient.readContract({
        address: contractAddr,
        functionName: 'get_request_audit',
        args: [requestId, callerAddr || ''],
        transactionHashVariant: 'latest_finalized'
      });
      if (reqRes && reqRes.has_audit) {
        return reqRes;
      }
    }

    const res = await genClient.readContract({
      address: contractAddr,
      functionName: 'get_audit',
      args: [tokenAddr],
      transactionHashVariant: 'latest_finalized'
    });
    if (res && res.has_audit) {
      return res;
    }
  } catch (e) {
    console.warn('genClient.readContract get_audit error:', e);
  }
  return null;
}

// Query StudioNet contract overview via genClient.readContract (100% FINALIZED ON-CHAIN BLOCK STATE)
async function fetchStudioNetOverview(contractAddr) {
  try {
    const res = await genClient.readContract({
      address: contractAddr,
      functionName: 'get_overview',
      args: [],
      transactionHashVariant: 'latest_finalized'
    });
    if (res && res.audited_count > 0) {
      return {
        audited_count: res.audited_count,
        recent_tokens: res.recent_tokens || []
      };
    }
  } catch (e) {
    console.warn('genClient.readContract get_overview error:', e);
  }
  return null;
}

// Consensus rounds that ended without a stored verdict. The audit fails closed,
// so these are real outcomes the user has to see, not states worth polling on.
const TERMINAL_FAILURE_STATUSES = {
  CANCELED: 'Consensus round was canceled before a verdict was reached.',
  UNDETERMINED: 'Validators could not agree on a verdict for this token.',
  LEADER_TIMEOUT: 'The leader node timed out before producing a verdict.',
  VALIDATORS_TIMEOUT: 'Validator nodes timed out during the consensus round.'
};

// Poll GenLayer StudioNet RPC for true consensus finality status (FINALIZED / ACCEPTED)
async function waitForStudioNetReceipt(txHash, onStatusUpdate) {
  for (let i = 0; i < 40; i++) {
    try {
      const res = await fetch(`${STUDIONET_RPC_URL}?_nocache=${Date.now()}_${i}`, {
        method: 'POST',
        cache: 'no-store',
        headers: {
          'Content-Type': 'application/json',
          'Cache-Control': 'no-cache, no-store, must-revalidate',
          'Pragma': 'no-cache'
        },
        body: JSON.stringify({
          jsonrpc: '2.0',
          id: Date.now(),
          method: 'gen_getTransactionStatus',
          params: [txHash]
        })
      });
      const json = await res.json();
      const status = (json && json.result) ? String(json.result).toUpperCase() : '';

      if (status === 'FINALIZED' || status === 'ACCEPTED' || status === 'SUCCESS') {
        if (onStatusUpdate) onStatusUpdate(`Consensus FINALIZED on-chain — block state committed.`);
        return { ok: true, status };
      } else if (TERMINAL_FAILURE_STATUSES[status]) {
        if (onStatusUpdate) onStatusUpdate(TERMINAL_FAILURE_STATUSES[status]);
        return { ok: false, status };
      } else if (status === 'PROPOSING') {
        if (onStatusUpdate) onStatusUpdate(`GenLayer consensus: PROPOSING — multi-validator LLMs evaluating token data...`);
      } else if (status === 'COMMITTING') {
        if (onStatusUpdate) onStatusUpdate(`GenLayer consensus: COMMITTING — finalizing block state on StudioNet...`);
      } else if (status) {
        if (onStatusUpdate) onStatusUpdate(`GenLayer consensus status: ${status}...`);
      }
    } catch (e) {
      console.warn('RPC Status polling error:', e);
    }
    await new Promise(r => setTimeout(r, 2500));
  }
  return { ok: false, status: 'TIMEOUT' };
}

export default function App() {
  const [contractAddress, setContractAddress] = useState(DEFAULT_CONTRACT);
  const [tokenAddress, setTokenAddress] = useState(''); // DEFAULT EMPTY SEARCH BAR
  const [activePreset, setActivePreset] = useState('');
  const [showConfig, setShowConfig] = useState(false);

  // MetaMask Wallet state
  const [userAccount, setUserAccount] = useState('');
  const [isConnectingWallet, setIsConnectingWallet] = useState(false);

  // Dynamic Session Transaction & Request ID Mappings
  const [sessionTxHashes, setSessionTxHashes] = useState({});
  const [sessionRequestIds, setSessionRequestIds] = useState({});
  const [lastTxHash, setLastTxHash] = useState('');
  const [lastRequestId, setLastRequestId] = useState('');

  // State for DEXScreener Data
  const [dexData, setDexData] = useState(null);
  const [dexLoading, setDexLoading] = useState(false);

  // State for Audit Report (NEVER AUTO-LOAD PAST AUDITS ON SELECT/PAGE LOAD)
  const [auditReport, setAuditReport] = useState(null);
  const [isAuditing, setIsAuditing] = useState(false);
  const [auditStatusText, setAuditStatusText] = useState('');

  // Recent audits history directly from contract
  const [recentAudits, setRecentAudits] = useState([]);
  const [totalAudits, setTotalAudits] = useState(0);

  // Connect user's MetaMask Wallet & Switch to GenLayer StudioNet (Chain ID: 61999 / 0xf22f)
  const connectMetaMask = async () => {
    if (typeof window.ethereum === 'undefined') {
      alert('MetaMask extension is not detected. Please install MetaMask to sign transactions with your wallet.');
      return null;
    }

    setIsConnectingWallet(true);
    try {
      const accounts = await window.ethereum.request({ method: 'eth_requestAccounts' });
      if (accounts && accounts.length > 0) {
        setUserAccount(accounts[0]);
        await ensureGenLayerNetwork();
        return accounts[0];
      }
    } catch (e) {
      console.error('MetaMask connection failed:', e);
    } finally {
      setIsConnectingWallet(false);
    }
    return null;
  };

  // Fetch real-time DEXScreener data (Strict No Cache)
  const fetchDexData = async (address) => {
    if (!address || !address.trim()) {
      setDexData(null);
      return null;
    }
    setDexLoading(true);
    try {
      const res = await fetch(`https://api.dexscreener.com/latest/dex/tokens/${address}?_t=${Date.now()}`, {
        cache: 'no-store',
        headers: {
          'Cache-Control': 'no-cache, no-store, must-revalidate',
          'Pragma': 'no-cache'
        }
      });
      const data = await res.json();
      if (data && data.pairs && data.pairs.length > 0) {
        const primaryPair = data.pairs.sort((a, b) => (b.liquidity?.usd || 0) - (a.liquidity?.usd || 0))[0];
        setDexData(primaryPair);
        return primaryPair;
      } else {
        setDexData(null);
        return null;
      }
    } catch (err) {
      console.error('Failed to fetch DEXScreener data:', err);
      setDexData(null);
      return null;
    } finally {
      setDexLoading(false);
    }
  };

  // Fetch real-time Birdeye & RugCheck security data
  const fetchSecurityData = async (address) => {
    if (!address || !address.trim()) return null;
    try {
      const res = await fetch(`https://api.rugcheck.xyz/v1/tokens/${address}/report?_t=${Date.now()}`, {
        cache: 'no-store'
      });
      const data = await res.json();
      if (data && data.token) {
        // Only report figures RugCheck actually returned. Substituting a
        // plausible-looking default here would hand the auditor invented
        // evidence, and a missing authority flag would read as "revoked".
        const security = {
          detected_risks: Array.isArray(data.risks) ? data.risks.map(r => r.name || r) : []
        };

        if ('mintAuthority' in data.token) {
          security.mint_disabled = !data.token.mintAuthority;
        }
        if ('freezeAuthority' in data.token) {
          security.freeze_disabled = !data.token.freezeAuthority;
        }

        const market = Array.isArray(data.markets) && data.markets.length > 0 ? data.markets[0] : null;
        if (market && market.lp && typeof market.lp.lpBurnedPct === 'number') {
          security.lp_burned_pct = Math.round(market.lp.lpBurnedPct);
        }

        const topHolders = Array.isArray(data.topHolders) ? data.topHolders : [];
        if (typeof data.topHoldersPct === 'number') {
          security.top10_holder_pct = Math.round(data.topHoldersPct);
        } else if (topHolders.length > 0) {
          security.top10_holder_pct = Math.round(
            topHolders.slice(0, 10).reduce((acc, h) => acc + (h.pct || 0), 0)
          );
        }

        const totalHolders = data.totalHolders || data.holderCount;
        if (typeof totalHolders === 'number') {
          security.holder_count = totalHolders;
        }

        if (topHolders.length > 0) {
          security.smart_money_wallets = topHolders.filter(
            h => !h.insider && (h.pct || 0) < 5 && (h.pct || 0) > 0.2
          ).length;
        }

        return security;
      }
    } catch (e) {
      console.warn('RugCheck security fetch error:', e);
    }
    return null;
  };

  // Strictly load Real Audit Output for token directly from StudioNet RPC ONLY WHEN EXPLICITLY CALLED
  const loadAuditFromChain = async (address, reqId = '') => {
    if (!address || !address.trim()) return false;
    const currentSessionTx = sessionTxHashes[address] || '';
    const currentReqId = reqId || sessionRequestIds[address] || '';
    setLastTxHash(currentSessionTx);
    setLastRequestId(currentReqId);

    const onchainReport = await fetchStudioNetAuditReport(contractAddress, address, currentReqId, userAccount);
    if (onchainReport && onchainReport.has_audit) {
      setAuditReport(onchainReport);
      return true;
    }

    setAuditReport(null);
    return false;
  };

  // Load Overview directly from Contract via GenLayer RPC
  const loadOverviewFromChain = async () => {
    const overview = await fetchStudioNetOverview(contractAddress);
    if (overview && overview.audited_count > 0) {
      setTotalAudits(overview.audited_count);
      setRecentAudits(overview.recent_tokens);
    }
  };

  // Auto-detect MetaMask account on load
  useEffect(() => {
    if (typeof window.ethereum !== 'undefined') {
      window.ethereum.request({ method: 'eth_accounts' }).then(accounts => {
        if (accounts && accounts.length > 0) {
          setUserAccount(accounts[0]);
        }
      }).catch(e => console.warn('Account check error:', e));

      window.ethereum.on('accountsChanged', (accounts) => {
        if (accounts && accounts.length > 0) {
          setUserAccount(accounts[0]);
        } else {
          setUserAccount('');
        }
      });

      window.ethereum.on('chainChanged', () => {
        window.location.reload();
      });
    }
  }, []);

  // Handle Token Selection / Input Change (ZERO AUTO-LOAD OF PAST AUDITS)
  const handleSelectToken = async (ca, symbol = '') => {
    setTokenAddress(ca);
    setActivePreset(symbol);
    setAuditReport(null); // ALWAYS CLEAR AUDIT REPORT TO EMPTY STATE ON TOKEN CHANGE
    setLastTxHash(sessionTxHashes[ca] || '');
    setLastRequestId(sessionRequestIds[ca] || '');
    if (ca.trim()) {
      await fetchDexData(ca);
    } else {
      setDexData(null);
    }
  };

  useEffect(() => {
    (async () => {
      setAuditReport(null); // ALWAYS INITIALIZE TO EMPTY STATE ON PAGE LOAD
      loadOverviewFromChain();
    })();
  }, []);

  // Trigger GenLayer AI Audit Transaction (HOLDS LOADING STATE UNTIL FRESH ON-CHAIN RESULT ARRIVES)
  const handleTriggerAudit = async () => {
    if (!tokenAddress || !tokenAddress.trim()) {
      alert('Please enter or select a valid Solana Token Mint Address.');
      return;
    }

    let senderAddr = userAccount;
    if (!senderAddr && typeof window.ethereum !== 'undefined') {
      senderAddr = await connectMetaMask();
    }

    if (!senderAddr && typeof window.ethereum === 'undefined') {
      alert('MetaMask extension is not detected. Please install MetaMask to trigger audits on GenLayer.');
      return;
    }

    // IMMEDIATELY CLEAR STALE AUDIT & ENTER LOADING STATE
    setAuditReport(null);
    setIsAuditing(true);
    setAuditStatusText(`Switching MetaMask to GenLayer StudioNet (Chain ID: 61999)...`);

    try {
      await ensureGenLayerNetwork();
      const currentPair = await fetchDexData(tokenAddress);
      const currentSecurity = await fetchSecurityData(tokenAddress);
      let txHash = null;
      const uniqueRequestId = `req_${(senderAddr || 'anon').slice(-6)}_${tokenAddress.slice(0, 6)}_${Date.now()}`;

      // Forward only what the live sources actually returned. The contract
      // fails closed on missing evidence, so inventing defaults here would
      // just smuggle guesses past that check.
      const telemetry = {
        token_symbol: currentPair?.baseToken?.symbol || activePreset || 'TOKEN',
        token_name: currentPair?.baseToken?.name || '',
        price_usd: currentPair?.priceUsd || '0',
        market_cap_usd: currentPair?.fdv || currentPair?.marketCap || 0,
        liquidity_usd: currentPair?.liquidity?.usd || 0,
        volume_24h_usd: currentPair?.volume?.h24 || 0,
        fdv_usd: currentPair?.fdv || currentPair?.marketCap || 0,
        price_change_24h_pct: currentPair?.priceChange?.h24 || 0,
        txns_24h_buys: currentPair?.txns?.h24?.buys || 0,
        txns_24h_sells: currentPair?.txns?.h24?.sells || 0,
        detected_risks: currentSecurity?.detected_risks || []
      };

      for (const field of ['mint_disabled', 'freeze_disabled', 'lp_burned_pct',
                           'top10_holder_pct', 'holder_count', 'smart_money_wallets']) {
        if (currentSecurity && currentSecurity[field] !== undefined) {
          telemetry[field] = currentSecurity[field];
        }
      }

      const telemetryPayload = JSON.stringify(telemetry);

      if (typeof window.ethereum !== 'undefined' && senderAddr) {
        setAuditStatusText(`Confirm the GenLayer call in your MetaMask popup (fee: 1000 GEN)...`);

        try {
          // Attempt 1: Standard genClient.writeContract
          txHash = await genClient.writeContract({
            address: contractAddress,
            functionName: 'audit_token',
            args: [tokenAddress, uniqueRequestId, 1000, telemetryPayload],
            account: senderAddr
          });
        } catch (err1) {
          console.warn('Attempt 1 (string account) failed:', err1);
          try {
            // Attempt 2: Object account
            txHash = await genClient.writeContract({
              address: contractAddress,
              functionName: 'audit_token',
              args: [tokenAddress, uniqueRequestId, 1000, telemetryPayload],
              account: { address: senderAddr }
            });
          } catch (err2) {
            console.warn('Attempt 2 (object account) failed:', err2);
            try {
              // Attempt 3: No account param (rely on window.ethereum provider)
              txHash = await genClient.writeContract({
                address: contractAddress,
                functionName: 'audit_token',
                args: [tokenAddress, uniqueRequestId, 1000, telemetryPayload]
              });
            } catch (err3) {
              console.error('All writeContract attempts failed:', err3);
              const errMsg = err3?.message || err2?.message || err1?.message || 'Transaction failed';
              if (errMsg.includes('rejected') || err3?.code === 4001 || err2?.code === 4001) {
                setAuditStatusText('Transaction signing was rejected in MetaMask.');
              } else {
                setAuditStatusText(`MetaMask / RPC error: ${errMsg.slice(0, 120)}`);
              }
              setIsAuditing(false);
              return;
            }
          }
        }
      }

      if (txHash) {
        setLastTxHash(txHash);
        setLastRequestId(uniqueRequestId);
        setSessionTxHashes(prev => ({ ...prev, [tokenAddress]: txHash }));
        setSessionRequestIds(prev => ({ ...prev, [tokenAddress]: uniqueRequestId }));
        setAuditStatusText(`GenLayer LLM consensus in progress — PROPOSING (multi-validator voting on StudioNet)...`);

        // Poll GenLayer StudioNet RPC for true consensus finality status (FINALIZED / ACCEPTED)
        const receipt = await waitForStudioNetReceipt(txHash, (statusMsg) => setAuditStatusText(statusMsg));
        if (receipt.ok) {
          setAuditStatusText('Consensus finalized — reading fresh on-chain LLM verdict...');
          await new Promise(r => setTimeout(r, 1500));
          const loaded = await loadAuditFromChain(tokenAddress, uniqueRequestId);
          if (loaded) {
            setAuditStatusText('Fresh on-chain AI audit consensus completed.');
            loadOverviewFromChain();
            return;
          }
        } else if (TERMINAL_FAILURE_STATUSES[receipt.status]) {
          setAuditStatusText(`No audit stored — ${TERMINAL_FAILURE_STATUSES[receipt.status]}`);
          return;
        }

        // Additional polling fallback for state propagation
        for (let i = 0; i < 10; i++) {
          setAuditStatusText(`Reading GenLayer StudioNet finalized state (${i + 1}/10)...`);
          await new Promise(r => setTimeout(r, 2500));
          const loaded = await loadAuditFromChain(tokenAddress, uniqueRequestId);
          if (loaded) {
            setAuditStatusText('Fresh on-chain AI audit consensus completed.');
            loadOverviewFromChain();
            return;
          }
        }

        // The audit fails closed: a reverted round stores nothing, so an empty
        // read after finality is a rejected audit, not a propagation delay.
        setAuditStatusText(
          'No audit was stored on-chain. The contract refuses to write a report when live ' +
          'market or mint/freeze authority data is unavailable, or when the LLM consensus round ' +
          'fails validation. Check the transaction on the explorer for the exact reason.'
        );
      } else {
        setAuditStatusText('Please connect your MetaMask wallet to send transactions.');
      }
    } catch (e) {
      console.error('Audit failed:', e);
      setAuditStatusText(`Audit error: ${e?.message || e}`);
    } finally {
      setIsAuditing(false);
    }
  };

  const getVerdictBadge = (verdict) => {
    switch (verdict) {
      case 'SAFE_TO_TRADE':
        return <span className="badge badge-safe"><ShieldCheck size={13} /> SAFE TO TRADE</span>;
      case 'HIGH_VOLATILITY_WARN':
        return <span className="badge badge-warn"><AlertTriangle size={13} /> HIGH VOLATILITY</span>;
      case 'CRITICAL_RUG_RISK':
        return <span className="badge badge-critical"><ShieldAlert size={13} /> CRITICAL RISK</span>;
      default:
        return <span className="badge badge-warn">UNKNOWN</span>;
    }
  };

  // Render an actionable verdict banner with strict tier rules:
  // 1. Score >= 80 -> safe
  // 2. Score 50-79 -> warning
  // 3. Score < 50 -> critical
  const renderBuyDecisionBanner = (score, verdict) => {
    if (score >= 80 || verdict === 'SAFE_TO_TRADE') {
      return (
        <div className="verdict-banner verdict-safe">
          <div className="icon"><ShieldCheck size={18} strokeWidth={2.5} /></div>
          <div>
            <div className="eyebrow">Buy recommendation</div>
            <div className="headline">Recommended entry — low rug risk</div>
            <div className="detail">Mint &amp; freeze authorities disabled. Liquidity and buy pressure support trading safety.</div>
          </div>
        </div>
      );
    } else if (score >= 50 || verdict === 'HIGH_VOLATILITY_WARN') {
      return (
        <div className="verdict-banner verdict-warn">
          <div className="icon"><AlertTriangle size={18} strokeWidth={2.5} /></div>
          <div>
            <div className="eyebrow">Buy recommendation — volatility warning</div>
            <div className="headline">Proceed with caution</div>
            <div className="detail">Elevated price swings or sell volume spikes detected. Use strict risk management.</div>
          </div>
        </div>
      );
    } else {
      return (
        <div className="verdict-banner verdict-critical">
          <div className="icon"><ShieldAlert size={18} strokeWidth={2.5} /></div>
          <div>
            <div className="eyebrow">Critical warning</div>
            <div className="headline">Do not buy — honeypot or inflation risk</div>
            <div className="detail">Score below 50, an active mint/freeze authority, or unburned LP. High probability of loss.</div>
          </div>
        </div>
      );
    }
  };

  const getGaugeColor = (score, verdict) => {
    if (score >= 80 || verdict === 'SAFE_TO_TRADE') return '#22c55e';
    if (score >= 50 || verdict === 'HIGH_VOLATILITY_WARN') return '#f5a623';
    return '#ef4444';
  };

  // Smart Money & Whale Sentiment Detector
  const getSmartMoneySignal = () => {
    if (!dexData || !dexData.txns?.h24) return { label: 'Neutral sentiment', color: '#6366f1', text: 'Balanced buy/sell activity', netRatio: '1.0x' };
    const buys = dexData.txns.h24.buys || 0;
    const sells = dexData.txns.h24.sells || 0;
    const ratio = sells > 0 ? (buys / sells).toFixed(2) : '1.0';
    if (buys > sells * 1.15) {
      return { label: 'Smart money accumulating', color: '#22c55e', text: `Inflow: ${buys} buys vs ${sells} sells`, netRatio: `${ratio}x buy pressure` };
    } else if (sells > buys * 1.15) {
      return { label: 'Whale selling pressure', color: '#ef4444', text: `Outflow: ${sells} sells vs ${buys} buys`, netRatio: `${(sells / (buys || 1)).toFixed(2)}x dump pressure` };
    }
    return { label: 'Sideways range', color: '#6366f1', text: `Equilibrium: ${buys} buys / ${sells} sells`, netRatio: '1.0x balanced' };
  };

  const smartMoney = getSmartMoneySignal();
  const effectiveMarketCap = dexData?.marketCap || dexData?.fdv || 0;
  const liquidityUsd = dexData?.liquidity?.usd || 0;
  const volume24h = dexData?.volume?.h24 || 0;
  const liqFdvRatio = effectiveMarketCap > 0 ? ((liquidityUsd / effectiveMarketCap) * 100).toFixed(1) : '0.0';
  const volLiqRatio = liquidityUsd > 0 ? (volume24h / liquidityUsd).toFixed(1) : '0.0';
  const activeTxHash = lastTxHash || (tokenAddress ? sessionTxHashes[tokenAddress] : '');

  return (
    <div className="page">
      {/* ---------- Topbar ---------- */}
      <header className="topbar">
        <div className="brand">
          <div className="brand-mark"><ShieldCheck size={20} strokeWidth={2.5} /></div>
          <div>
            <div className="brand-name">GenMeme Guard</div>
            <div className="brand-sub">Solana rug inspector — GenLayer LLM consensus</div>
          </div>
        </div>

        <div className="topbar-actions">
          {userAccount ? (
            <div className="tag">
              <Wallet size={13} />
              {userAccount.slice(0, 6)}...{userAccount.slice(-4)}
            </div>
          ) : (
            <button className="btn btn-primary" onClick={connectMetaMask} disabled={isConnectingWallet}>
              <Wallet size={14} />
              {isConnectingWallet ? 'Connecting...' : 'Connect wallet'}
            </button>
          )}

          <button className="btn btn-ghost" onClick={() => setShowConfig(!showConfig)}>
            <Sliders size={14} />
            Settings
          </button>

          <a
            href={activeTxHash ? `${EXPLORER_BASE_URL}/tx/${activeTxHash}` : `${EXPLORER_BASE_URL}/address/${contractAddress}`}
            target="_blank"
            rel="noreferrer"
            className="btn btn-ghost"
          >
            <FileCode size={14} />
            {activeTxHash ? 'Tx explorer' : 'Explorer'}
            <ExternalLink size={12} />
          </a>

          <div className="network-pill">
            <span className="status-dot" />
            StudioNet · 61999
          </div>
        </div>
      </header>

      {/* ---------- Contract config ---------- */}
      {showConfig && (
        <section className="card" style={{ marginBottom: '1.5rem' }}>
          <div className="section-title" style={{ marginBottom: '0.6rem' }}>Target contract address</div>
          <input
            type="text"
            className="input"
            value={contractAddress}
            onChange={(e) => setContractAddress(e.target.value)}
            placeholder="0x..."
          />
        </section>
      )}

      {/* ---------- Hero ---------- */}
      <section className="hero">
        <div className="hero-eyebrow">GenLayer intelligent contracts · multi-validator AI consensus</div>
        <h1 className="hero-title">AI-powered rugpull defense for Solana tokens</h1>
        <p className="hero-sub">
          Paste any Solana mint address and get a forensic safety audit, evaluated by a real
          multi-validator LLM consensus round on GenLayer StudioNet — not a static rule engine.
        </p>

        <div className="grid-4" style={{ marginTop: '1.75rem' }}>
          <div className="metric-tile">
            <div className="metric-label"><ShieldCheck size={12} /> On-chain audits</div>
            <div className="metric-value">{totalAudits} tokens</div>
          </div>
          <div className="metric-tile">
            <div className="metric-label"><Cpu size={12} /> Consensus mode</div>
            <div className="metric-value">Optimistic BFT</div>
          </div>
          <div className="metric-tile">
            <div className="metric-label"><Zap size={12} /> Smart money radar</div>
            <div className="metric-value">Buy / sell inflow</div>
          </div>
          <div className="metric-tile">
            <div className="metric-label"><Lock size={12} /> Security checks</div>
            <div className="metric-value">Mint / freeze</div>
          </div>
        </div>
      </section>

      {/* ---------- Live contract state strip ---------- */}
      <section className="section">
        <div className="card-flat" style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', flexWrap: 'wrap', gap: '0.75rem' }}>
          <div style={{ display: 'flex', alignItems: 'center', gap: '0.65rem' }}>
            <CheckCircle2 size={17} color="var(--success)" />
            <div>
              <div style={{ fontSize: '0.85rem', fontWeight: 600, color: 'var(--text-primary)' }}>
                StudioNet contract active
              </div>
              <div style={{ fontSize: '0.78rem', color: 'var(--text-tertiary)', fontFamily: 'var(--font-mono)' }}>
                {activeTxHash ? `Audit tx: ${activeTxHash}` : `Contract: ${contractAddress}`}
              </div>
            </div>
          </div>
          <a
            href={activeTxHash ? `${EXPLORER_BASE_URL}/tx/${activeTxHash}` : `${EXPLORER_BASE_URL}/address/${contractAddress}`}
            target="_blank"
            rel="noreferrer"
            className="link"
          >
            {activeTxHash ? 'View audit tx' : 'View contract'} <ExternalLink size={13} />
          </a>
        </div>
      </section>

      {/* ---------- Why GenMeme Guard ---------- */}
      <section className="section">
        <div className="card">
          <div style={{ textAlign: 'center', marginBottom: '1.75rem' }}>
            <div className="hero-eyebrow" style={{ justifyContent: 'center', display: 'flex', alignItems: 'center', gap: '0.4rem' }}>
              <Award size={13} /> Why traders choose GenMeme Guard
            </div>
            <h2 style={{ fontFamily: 'var(--font-display)', fontSize: '1.35rem', fontWeight: 700, color: 'var(--text-primary)' }}>
              Real AI consensus, not static rules
            </h2>
            <p style={{ fontSize: '0.86rem', color: 'var(--text-secondary)', maxWidth: '620px', margin: '0.5rem auto 0' }}>
              Static scanners hand out 100/100 scores to worthless micro-cap coins. GenMeme Guard applies
              scale-tier ceilings and a decentralized LLM consensus round before any verdict is stored.
            </p>
          </div>

          <div className="grid-4">
            <div>
              <div className="feature-icon"><ShieldCheck size={20} /></div>
              <div className="feature-title">Scale-tier ceilings</div>
              <p className="feature-text">Micro-cap coins under $100k market cap are hard-capped at 55/100 — no fake perfect scores.</p>
            </div>
            <div>
              <div className="feature-icon"><TrendingUp size={20} /></div>
              <div className="feature-title">Smart money radar</div>
              <p className="feature-text">Tracks buy/sell ratios, holder concentration, and accumulation signals in real time.</p>
            </div>
            <div>
              <div className="feature-icon"><Zap size={20} /></div>
              <div className="feature-title">Slippage shield</div>
              <p className="feature-text">Flags abnormal volume-to-liquidity turnover that signals wash trading or thin depth.</p>
            </div>
            <div>
              <div className="feature-icon"><Cpu size={20} /></div>
              <div className="feature-title">Decentralized AI</div>
              <p className="feature-text">Verdicts are independently reproduced by validator nodes and finalized on-chain.</p>
            </div>
          </div>
        </div>
      </section>

      {/* ---------- Search & presets ---------- */}
      <section className="section">
        <div className="card">
          <div className="section-title" style={{ marginBottom: '1rem' }}>
            <Search size={17} /> Inspect a Solana token
          </div>

          <div style={{ display: 'flex', gap: '0.85rem', flexWrap: 'wrap', marginBottom: '1.1rem' }}>
            <div style={{ flex: 1, minWidth: '280px' }}>
              <input
                type="text"
                className="input"
                placeholder="Paste a Solana mint address..."
                value={tokenAddress}
                onChange={(e) => handleSelectToken(e.target.value, '')}
              />
            </div>
            <button className="btn btn-primary btn-lg" onClick={handleTriggerAudit} disabled={isAuditing || !tokenAddress.trim()}>
              {isAuditing ? <RefreshCw size={16} className="spinner" /> : <Cpu size={16} />}
              {isAuditing ? 'Running audit...' : 'Run AI audit'}
            </button>
          </div>

          <div style={{ display: 'flex', alignItems: 'center', gap: '0.6rem', flexWrap: 'wrap' }}>
            <span style={{ fontSize: '0.82rem', color: 'var(--text-tertiary)' }}>Popular:</span>
            {PRESET_TOKENS.map((token) => (
              <button
                key={token.symbol}
                className={`chip ${activePreset === token.symbol ? 'active' : ''}`}
                onClick={() => handleSelectToken(token.address, token.symbol)}
                disabled={isAuditing}
              >
                {token.symbol}
              </button>
            ))}
          </div>

          {isAuditing && (
            <div className="card-flat" style={{ marginTop: '1.1rem', display: 'flex', alignItems: 'center', gap: '0.65rem' }}>
              <RefreshCw size={15} className="spinner" color="var(--accent)" />
              <span style={{ fontSize: '0.85rem', color: 'var(--text-secondary)', fontFamily: 'var(--font-mono)' }}>{auditStatusText}</span>
            </div>
          )}
        </div>
      </section>

      {/* ---------- DEX data + audit result ---------- */}
      <section className="section grid-2">

        {/* DEX & smart money card */}
        <div className="card" style={{ display: 'flex', flexDirection: 'column' }}>
          <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '1.1rem' }}>
            <div className="section-title"><Activity size={17} /> DEX & smart money radar</div>
            {dexLoading && <RefreshCw size={14} className="spinner" color="var(--text-tertiary)" />}
          </div>

          {dexData ? (
            <div>
              <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'baseline', marginBottom: '1.1rem', paddingBottom: '0.9rem', borderBottom: '1px solid var(--border)' }}>
                <div>
                  <div style={{ fontSize: '1.2rem', fontWeight: 700, color: 'var(--text-primary)' }}>
                    {dexData.baseToken?.symbol} / {dexData.quoteToken?.symbol}
                  </div>
                  <div style={{ fontSize: '0.78rem', color: 'var(--text-tertiary)' }}>
                    {dexData.dexId?.toUpperCase()} · {dexData.pairAddress?.slice(0, 6)}...{dexData.pairAddress?.slice(-4)}
                  </div>
                </div>
                <div style={{ textAlign: 'right' }}>
                  <div style={{ fontSize: '1.15rem', fontWeight: 700, fontFamily: 'var(--font-mono)', color: 'var(--text-primary)' }}>
                    ${parseFloat(dexData.priceUsd || 0).toLocaleString(undefined, { minimumFractionDigits: 4, maximumFractionDigits: 8 })}
                  </div>
                  <div className={`metric-value ${(dexData.priceChange?.h24 || 0) >= 0 ? 'up' : 'down'}`} style={{ fontSize: '0.85rem' }}>
                    {(dexData.priceChange?.h24 || 0) >= 0 ? '+' : ''}{dexData.priceChange?.h24?.toFixed(2)}% (24h)
                  </div>
                </div>
              </div>

              <div className="card-flat" style={{ marginBottom: '0.9rem' }}>
                <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
                  <span className="metric-label"><Zap size={12} color={smartMoney.color} /> Sentiment</span>
                  <span style={{ fontSize: '0.78rem', fontFamily: 'var(--font-mono)', color: smartMoney.color }}>{smartMoney.netRatio}</span>
                </div>
                <div style={{ fontSize: '0.92rem', fontWeight: 700, color: smartMoney.color, marginTop: '0.3rem' }}>{smartMoney.label}</div>
                <div style={{ fontSize: '0.78rem', color: 'var(--text-tertiary)', marginTop: '0.15rem', fontFamily: 'var(--font-mono)' }}>{smartMoney.text}</div>
              </div>

              <div className="card-flat" style={{ marginBottom: '0.9rem' }}>
                <div className="metric-label" style={{ marginBottom: '0.5rem' }}><Clock size={12} /> Price trend</div>
                <div style={{ display: 'grid', gridTemplateColumns: 'repeat(4, 1fr)', gap: '0.5rem', textAlign: 'center' }}>
                  {['m5', 'h1', 'h6', 'h24'].map((k) => (
                    <div key={k}>
                      <div style={{ fontSize: '0.68rem', color: 'var(--text-tertiary)' }}>{k === 'm5' ? '5m' : k}</div>
                      <div className={`metric-value ${(dexData.priceChange?.[k] || 0) >= 0 ? 'up' : 'down'}`} style={{ fontSize: '0.82rem', marginTop: '0.1rem' }}>
                        {(dexData.priceChange?.[k] || 0) >= 0 ? '+' : ''}{(dexData.priceChange?.[k] || 0).toFixed(1)}%
                      </div>
                    </div>
                  ))}
                </div>
              </div>

              <div className="grid-4" style={{ gridTemplateColumns: 'repeat(auto-fit, minmax(120px, 1fr))' }}>
                <div className="metric-tile">
                  <div className="metric-label"><Coins size={12} /> Market cap</div>
                  <div className="metric-value">${effectiveMarketCap.toLocaleString()}</div>
                </div>
                <div className="metric-tile">
                  <div className="metric-label"><DollarSign size={12} /> Liquidity</div>
                  <div className="metric-value">${liquidityUsd.toLocaleString()}</div>
                </div>
                <div className="metric-tile">
                  <div className="metric-label"><Percent size={12} /> Liq / FDV</div>
                  <div className={`metric-value ${parseFloat(liqFdvRatio) < 5 ? 'down' : ''}`}>{liqFdvRatio}%</div>
                </div>
                <div className="metric-tile">
                  <div className="metric-label"><TrendingUp size={12} /> Vol / Liq</div>
                  <div className={`metric-value ${parseFloat(volLiqRatio) > 3 ? 'down' : ''}`}>{volLiqRatio}x</div>
                </div>
              </div>
            </div>
          ) : (
            <div className="empty">
              <Search size={30} />
              <p className="hint">Paste a Solana mint address or select a popular token to view live data.</p>
            </div>
          )}

          <div style={{ borderTop: '1px solid var(--border)', marginTop: '1.1rem', paddingTop: '0.9rem', display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
            <span style={{ fontSize: '0.78rem', color: 'var(--text-tertiary)' }}>DEXScreener live feed</span>
            {tokenAddress.trim() && (
              <a href={`https://dexscreener.com/solana/${tokenAddress}`} target="_blank" rel="noreferrer" className="link">
                Open on DEXScreener <ExternalLink size={12} />
              </a>
            )}
          </div>
        </div>

        {/* Audit verdict card */}
        <div className="card">
          <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '1.1rem' }}>
            <div className="section-title"><Cpu size={17} /> On-chain audit verdict</div>
            {!isAuditing && auditReport && getVerdictBadge(auditReport.verdict)}
          </div>

          {isAuditing ? (
            <div className="loading-state">
              <div className="loading-icon"><RefreshCw size={28} className="spinner" /></div>
              <div className="loading-title">Multi-node LLM consensus in progress</div>
              <p className="loading-status">{auditStatusText}</p>
              {activeTxHash && (
                <a href={`${EXPLORER_BASE_URL}/tx/${activeTxHash}`} target="_blank" rel="noreferrer" className="link">
                  Track live consensus on explorer <ExternalLink size={12} />
                </a>
              )}
            </div>
          ) : auditReport ? (
            <div>
              {renderBuyDecisionBanner(auditReport.safety_score, auditReport.verdict)}

              <div className="card-flat" style={{ display: 'flex', alignItems: 'center', gap: '1.2rem', marginBottom: '1.1rem' }}>
                <div className="gauge">
                  <svg width="104" height="104" viewBox="0 0 120 120">
                    <circle className="gauge-bg" cx="60" cy="60" r="50" />
                    <circle
                      className="gauge-fill"
                      cx="60" cy="60" r="50"
                      stroke={getGaugeColor(auditReport.safety_score, auditReport.verdict)}
                      strokeDasharray="314"
                      strokeDashoffset={314 - (314 * auditReport.safety_score) / 100}
                    />
                  </svg>
                  <div className="gauge-value">{auditReport.safety_score}</div>
                </div>

                <div style={{ flex: 1 }}>
                  <div className="metric-label">
                    {(auditReport.token_symbol && auditReport.token_symbol !== 'UNKNOWN') ? auditReport.token_symbol : (dexData?.baseToken?.symbol || activePreset || 'TOKEN')} summary
                  </div>
                  <p style={{ fontSize: '0.84rem', color: 'var(--text-secondary)', lineHeight: 1.55, marginTop: '0.35rem' }}>
                    "{auditReport.ai_summary}"
                  </p>
                  {auditReport.analysis_source && (
                    <div className="tag" style={{ marginTop: '0.6rem', color: 'var(--accent)', borderColor: 'var(--accent-border)', background: 'var(--accent-soft)' }}>
                      <Cpu size={11} />
                      LLM multi-validator consensus
                    </div>
                  )}
                </div>
              </div>

              <div style={{ marginBottom: '1rem' }}>
                <div className="metric-label" style={{ marginBottom: '0.55rem' }}>Rug pull indicators</div>
                <div className="grid-2">
                  <div className={`indicator-tile ${auditReport.mint_disabled ? 'ok' : 'risk'}`}>
                    <div className="indicator-label">
                      {auditReport.mint_disabled ? <Lock size={12} /> : <Unlock size={12} />} Mint authority
                    </div>
                    <div className={`indicator-value ${auditReport.mint_disabled ? 'ok' : 'risk'}`}>
                      {auditReport.mint_disabled ? 'Disabled (safe)' : 'Enabled (risk)'}
                    </div>
                  </div>
                  <div className={`indicator-tile ${auditReport.freeze_disabled ? 'ok' : 'risk'}`}>
                    <div className="indicator-label">
                      {auditReport.freeze_disabled ? <Lock size={12} /> : <Unlock size={12} />} Freeze authority
                    </div>
                    <div className={`indicator-value ${auditReport.freeze_disabled ? 'ok' : 'risk'}`}>
                      {auditReport.freeze_disabled ? 'Disabled (safe)' : 'Enabled (risk)'}
                    </div>
                  </div>
                </div>
              </div>

              {auditReport.risk_factors && auditReport.risk_factors.length > 0 && (
                <div className="risk-box" style={{ marginBottom: '1rem' }}>
                  <div className="heading"><AlertTriangle size={14} /> Detected risk signals</div>
                  <ul>
                    {auditReport.risk_factors.map((risk, i) => <li key={i}>{risk}</li>)}
                  </ul>
                </div>
              )}

              <div className="card-flat" style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', gap: '0.75rem', flexWrap: 'wrap' }}>
                <div>
                  <div style={{ fontSize: '0.7rem', textTransform: 'uppercase', letterSpacing: '0.04em', color: 'var(--text-tertiary)', fontWeight: 600 }}>
                    {activeTxHash ? 'Audit transaction verified' : 'Contract state verified'}
                  </div>
                  <div style={{ fontSize: '0.82rem', color: 'var(--text-primary)', fontFamily: 'var(--font-mono)', marginTop: '0.15rem' }}>
                    {activeTxHash ? `${activeTxHash.slice(0, 12)}...${activeTxHash.slice(-10)}` : `${contractAddress.slice(0, 10)}...${contractAddress.slice(-8)}`}
                  </div>
                </div>
                <a
                  href={activeTxHash ? `${EXPLORER_BASE_URL}/tx/${activeTxHash}` : `${EXPLORER_BASE_URL}/address/${contractAddress}`}
                  target="_blank" rel="noreferrer"
                  className="btn btn-secondary"
                >
                  View on explorer <ExternalLink size={13} />
                </a>
              </div>
            </div>
          ) : (
            <div className="empty">
              <ShieldAlert size={30} />
              <p className="title">No audit run this session</p>
              {tokenAddress.trim() && (
                <p style={{ fontSize: '0.78rem', color: 'var(--text-tertiary)', fontFamily: 'var(--font-mono)', marginTop: '0.3rem' }}>{tokenAddress}</p>
              )}
              <p className="hint">
                {tokenAddress.trim() ? 'Click "Run AI audit" to sign with MetaMask and execute GenLayer consensus.' : 'Paste a token address above or pick a preset to start.'}
              </p>
            </div>
          )}
        </div>
      </section>

      {/* ---------- Architecture ---------- */}
      <section className="section">
        <div className="section-title" style={{ marginBottom: '1.1rem' }}>
          <Sparkles size={17} /> How the consensus audit works
        </div>
        <div className="grid-3">
          <div className="feature-tile">
            <div className="feature-icon"><Cpu size={20} /></div>
            <div className="feature-title">Multi-node LLM agreement</div>
            <p className="feature-text">Validators independently re-run the web fetch and LLM audit, reaching on-chain consensus via the equivalence principle.</p>
          </div>
          <div className="feature-tile">
            <div className="feature-icon"><Zap size={20} /></div>
            <div className="feature-title">Smart money & whale radar</div>
            <p className="feature-text">Analyzes 24h buy/sell ratios in real time to surface whale dumping pressure or accumulation.</p>
          </div>
          <div className="feature-tile">
            <div className="feature-icon"><ShieldAlert size={20} /></div>
            <div className="feature-title">Zero-tolerance rubric</div>
            <p className="feature-text">A live mint or freeze authority, or missing evidence, forces the audit to a critical verdict or refuses to store one.</p>
          </div>
        </div>
      </section>

      {/* ---------- Audit history ---------- */}
      <section className="section">
        <div className="card">
          <div className="section-head" style={{ marginBottom: '0.9rem' }}>
            <div className="section-title"><Database size={17} /> On-chain audit history</div>
            <span className="section-meta">Total: <strong style={{ color: 'var(--text-primary)', fontFamily: 'var(--font-mono)' }}>{totalAudits}</strong></span>
          </div>

          {recentAudits.length > 0 ? (
            <div className="table-wrap">
              <table className="table">
                <thead>
                  <tr>
                    <th>Token mint address</th>
                    <th>Action</th>
                    <th>Explorer</th>
                  </tr>
                </thead>
                <tbody>
                  {recentAudits.map((addr, idx) => (
                    <tr key={idx}>
                      <td className="mono">{addr}</td>
                      <td>
                        <button className="btn btn-ghost" style={{ padding: '0.3rem 0.7rem', fontSize: '0.78rem' }} onClick={() => handleSelectToken(addr)}>
                          Select
                        </button>
                      </td>
                      <td>
                        {sessionTxHashes[addr] ? (
                          <a href={`${EXPLORER_BASE_URL}/tx/${sessionTxHashes[addr]}`} target="_blank" rel="noreferrer" className="link">
                            View tx <ExternalLink size={11} />
                          </a>
                        ) : (
                          <a href={`${EXPLORER_BASE_URL}/address/${contractAddress}`} target="_blank" rel="noreferrer" className="link">
                            Contract state <ExternalLink size={11} />
                          </a>
                        )}
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          ) : (
            <div className="empty" style={{ padding: '1.5rem' }}>
              <p className="hint">No token audits logged on-chain yet. Trigger your first audit above.</p>
            </div>
          )}
        </div>
      </section>

      <footer className="footer">
        GenMeme Guard — built on GenLayer intelligent contracts &amp; multi-validator LLM consensus
      </footer>
    </div>
  );
}
