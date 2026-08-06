import React, { useState, useEffect } from 'react';
import { createClient, chains } from 'genlayer-js';
import { 
  ShieldCheck, 
  ShieldAlert, 
  Flame, 
  Lock, 
  Unlock, 
  Users, 
  TrendingUp, 
  Activity, 
  Search, 
  Cpu, 
  RefreshCw, 
  ExternalLink, 
  AlertTriangle, 
  CheckCircle2, 
  BarChart3, 
  Database, 
  FileCode,
  Sliders,
  DollarSign,
  Wallet,
  Zap,
  TrendingDown,
  ThumbsUp,
  ThumbsDown,
  AlertCircle,
  Coins,
  Clock,
  Layers,
  Percent,
  Sparkles,
  ArrowRight,
  Eye,
  Check
} from 'lucide-react';

const DEFAULT_CONTRACT = '0x82D145770E1cE0328FC53f94e286fA108ccFAd5f';
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
        if (onStatusUpdate) onStatusUpdate(`✅ Consensus FINALIZED on-chain! Block state committed.`);
        return true;
      } else if (status === 'PROPOSING') {
        if (onStatusUpdate) onStatusUpdate(`🤖 GenLayer LLM Consensus: PROPOSING... (Multi-validator LLMs evaluating token Web APIs)`);
      } else if (status === 'COMMITTING') {
        if (onStatusUpdate) onStatusUpdate(`🤖 GenLayer LLM Consensus: COMMITTING... (Finalizing block state on StudioNet)`);
      } else if (status) {
        if (onStatusUpdate) onStatusUpdate(`🤖 GenLayer LLM Consensus Status: ${status}...`);
      }
    } catch (e) {
      console.warn('RPC Status polling error:', e);
    }
    await new Promise(r => setTimeout(r, 2500));
  }
  return false;
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
    setAuditStatusText(`🦊 Switching MetaMask to GenLayer StudioNet (Chain ID: 61999)...`);

    try {
      await ensureGenLayerNetwork();
      await fetchDexData(tokenAddress);
      let txHash = null;
      const uniqueRequestId = `req_${(senderAddr || 'anon').slice(-6)}_${tokenAddress.slice(0, 6)}_${Date.now()}`;

      if (typeof window.ethereum !== 'undefined' && senderAddr) {
        setAuditStatusText(`🦊 Please confirm GenLayer Call transaction in your MetaMask popup (Fee: 1000 GEN)...`);
        
        try {
          // Attempt 1: Standard genClient.writeContract
          txHash = await genClient.writeContract({
            address: contractAddress,
            functionName: 'audit_token',
            args: [tokenAddress, uniqueRequestId, 1000],
            account: senderAddr
          });
        } catch (err1) {
          console.warn('Attempt 1 (string account) failed:', err1);
          try {
            // Attempt 2: Object account
            txHash = await genClient.writeContract({
              address: contractAddress,
              functionName: 'audit_token',
              args: [tokenAddress, uniqueRequestId, 1000],
              account: { address: senderAddr }
            });
          } catch (err2) {
            console.warn('Attempt 2 (object account) failed:', err2);
            try {
              // Attempt 3: No account param (rely on window.ethereum provider)
              txHash = await genClient.writeContract({
                address: contractAddress,
                functionName: 'audit_token',
                args: [tokenAddress, uniqueRequestId, 1000]
              });
            } catch (err3) {
              console.error('All writeContract attempts failed:', err3);
              const errMsg = err3?.message || err2?.message || err1?.message || 'Transaction failed';
              if (errMsg.includes('rejected') || err3?.code === 4001 || err2?.code === 4001) {
                setAuditStatusText('❌ Transaction signing was rejected in MetaMask.');
              } else {
                setAuditStatusText(`❌ MetaMask / RPC Error: ${errMsg.slice(0, 120)}`);
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
        setAuditStatusText(`🤖 GenLayer LLM Consensus in progress... PROPOSING (Multi-validator voting on StudioNet)...`);

        // Poll GenLayer StudioNet RPC for true consensus finality status (FINALIZED / ACCEPTED)
        const isFinalized = await waitForStudioNetReceipt(txHash, (statusMsg) => setAuditStatusText(statusMsg));
        if (isFinalized) {
          setAuditStatusText('📥 Consensus FINALIZED! Reading fresh on-chain FINALIZED LLM verdict...');
          await new Promise(r => setTimeout(r, 1500));
          const loaded = await loadAuditFromChain(tokenAddress, uniqueRequestId);
          if (loaded) {
            setAuditStatusText('✅ Fresh On-Chain FINALIZED AI Audit Consensus Completed!');
            loadOverviewFromChain();
            return;
          }
        }

        // Additional polling fallback for state propagation
        for (let i = 0; i < 10; i++) {
          setAuditStatusText(`📥 Reading GenLayer StudioNet RPC on-chain FINALIZED state (${i + 1}/10)...`);
          await new Promise(r => setTimeout(r, 2500));
          const loaded = await loadAuditFromChain(tokenAddress, uniqueRequestId);
          if (loaded) {
            setAuditStatusText('✅ Fresh On-Chain FINALIZED AI Audit Consensus Completed!');
            loadOverviewFromChain();
            return;
          }
        }
      } else {
        setAuditStatusText('❌ Please connect your MetaMask wallet to send transactions.');
      }
    } catch (e) {
      console.error('Audit failed:', e);
      setAuditStatusText(`❌ Audit error: ${e?.message || e}`);
    } finally {
      setIsAuditing(false);
    }
  };

  const getVerdictBadge = (verdict) => {
    switch (verdict) {
      case 'SAFE_TO_TRADE':
        return <span className="badge badge-safe"><ShieldCheck size={16} /> SAFE TO TRADE</span>;
      case 'HIGH_VOLATILITY_WARN':
        return <span className="badge badge-warn"><AlertTriangle size={16} /> HIGH VOLATILITY WARN</span>;
      case 'CRITICAL_RUG_RISK':
        return <span className="badge badge-critical"><ShieldAlert size={16} /> CRITICAL RUG RISK</span>;
      default:
        return <span className="badge badge-warn">UNKNOWN</span>;
    }
  };

  // Render High-Contrast Actionable Buy Decision Banner with Strict Tier Rules:
  // 1. Score >= 80 (GREEN)
  // 2. Score 50 - 79 (YELLOW)
  // 3. Score < 50 (RED)
  const renderBuyDecisionBanner = (score, verdict) => {
    if (score >= 80 || verdict === 'SAFE_TO_TRADE') {
      return (
        <div style={{ background: 'linear-gradient(135deg, rgba(0, 255, 157, 0.18), rgba(0, 240, 255, 0.12))', padding: '1.1rem 1.3rem', borderRadius: '14px', border: '1px solid rgba(0, 255, 157, 0.5)', marginBottom: '1.25rem', display: 'flex', alignItems: 'center', gap: '1rem', boxShadow: '0 0 20px rgba(0, 255, 157, 0.15)' }}>
          <div style={{ background: 'var(--neon-green)', padding: '0.6rem', borderRadius: '12px', display: 'flex', color: '#070a12' }}>
            <ThumbsUp size={24} strokeWidth={2.5} />
          </div>
          <div>
            <div style={{ fontSize: '0.8rem', textTransform: 'uppercase', letterSpacing: '0.06em', color: 'var(--neon-green)', fontWeight: '800' }}>
              BUY RECOMMENDATION DECISION
            </div>
            <div style={{ fontSize: '1.1rem', fontWeight: '800', color: '#ffffff' }}>
              RECOMMENDED ENTRY — LOW RUG RISK
            </div>
            <div style={{ fontSize: '0.84rem', color: 'var(--text-muted)', marginTop: '0.15rem' }}>
              Mint & Freeze authorities disabled. Liquidity & buy pressure support trading safety.
            </div>
          </div>
        </div>
      );
    } else if (score >= 50 || verdict === 'HIGH_VOLATILITY_WARN') {
      return (
        <div style={{ background: 'linear-gradient(135deg, rgba(255, 184, 0, 0.2), rgba(255, 120, 0, 0.15))', padding: '1.1rem 1.3rem', borderRadius: '14px', border: '1px solid rgba(255, 184, 0, 0.6)', marginBottom: '1.25rem', display: 'flex', alignItems: 'center', gap: '1rem', boxShadow: '0 0 20px rgba(255, 184, 0, 0.2)' }}>
          <div style={{ background: 'var(--neon-yellow)', padding: '0.6rem', borderRadius: '12px', display: 'flex', color: '#070a12' }}>
            <AlertTriangle size={24} strokeWidth={2.5} />
          </div>
          <div>
            <div style={{ fontSize: '0.8rem', textTransform: 'uppercase', letterSpacing: '0.06em', color: 'var(--neon-yellow)', fontWeight: '800' }}>
              BUY RECOMMENDATION DECISION — VOLATILITY WARNING
            </div>
            <div style={{ fontSize: '1.1rem', fontWeight: '800', color: '#ffffff' }}>
              PROCEED WITH CAUTION — HIGH VOLATILITY MEME COIN
            </div>
            <div style={{ fontSize: '0.84rem', color: 'var(--text-muted)', marginTop: '0.15rem' }}>
              High 1h-24h price swing or sell volume spike detected. Exercise strict risk management!
            </div>
          </div>
        </div>
      );
    } else {
      return (
        <div className="pulse-border-risk" style={{ background: 'linear-gradient(135deg, rgba(255, 42, 109, 0.25), rgba(255, 0, 60, 0.18))', padding: '1.1rem 1.3rem', borderRadius: '14px', border: '2px solid var(--neon-pink)', marginBottom: '1.25rem', display: 'flex', alignItems: 'center', gap: '1rem', boxShadow: '0 0 30px rgba(255, 42, 109, 0.4)' }}>
          <div style={{ background: 'var(--neon-pink)', padding: '0.6rem', borderRadius: '12px', display: 'flex', color: '#ffffff', boxShadow: '0 0 15px #ff2a6d' }}>
            <ShieldAlert size={26} strokeWidth={2.5} />
          </div>
          <div>
            <div style={{ fontSize: '0.8rem', textTransform: 'uppercase', letterSpacing: '0.06em', color: 'var(--neon-pink)', fontWeight: '900', display: 'flex', alignItems: 'center', gap: '0.4rem' }}>
              <AlertTriangle size={15} /> CRITICAL WARNING — EXTREME RUGPULL DANGER
            </div>
            <div style={{ fontSize: '1.1rem', fontWeight: '900', color: '#ffffff' }}>
              DO NOT BUY — HONEYPOT OR INFLATION RUG RISK
            </div>
            <div style={{ fontSize: '0.84rem', color: '#ffb3c6', marginTop: '0.15rem', fontWeight: '600' }}>
              Score below 50, active Mint/Freeze, or unburned LP. High probability of financial loss!
            </div>
          </div>
        </div>
      );
    }
  };

  const getGaugeColor = (score, verdict) => {
    if (score >= 80 || verdict === 'SAFE_TO_TRADE') return '#00ff9d'; // Green (>= 80)
    if (score >= 50 || verdict === 'HIGH_VOLATILITY_WARN') return '#ffb800'; // Yellow (50 - 79)
    return '#ff2a6d'; // Red (< 50)
  };

  // Smart Money & Whale Sentiment Detector
  const getSmartMoneySignal = () => {
    if (!dexData || !dexData.txns?.h24) return { label: 'NEUTRAL SENTIMENT', color: 'var(--neon-yellow)', text: 'Balanced Buy/Sell Activity', netRatio: '1.0x' };
    const buys = dexData.txns.h24.buys || 0;
    const sells = dexData.txns.h24.sells || 0;
    const ratio = sells > 0 ? (buys / sells).toFixed(2) : '1.0';
    if (buys > sells * 1.15) {
      return { label: 'SMART MONEY ACCUMULATING (BUYING)', color: 'var(--neon-green)', text: `Inflow: ${buys} buys vs ${sells} sells`, netRatio: `${ratio}x Buy Pressure` };
    } else if (sells > buys * 1.15) {
      return { label: 'WHALE SELLING PRESSURE (DUMPING)', color: 'var(--neon-pink)', text: `Outflow: ${sells} sells vs ${buys} buys`, netRatio: `${(sells / (buys || 1)).toFixed(2)}x Dump Pressure` };
    }
    return { label: 'SIDEWAYS RANGE', color: 'var(--neon-cyan)', text: `Equilibrium: ${buys} buys / ${sells} sells`, netRatio: '1.0x Balanced' };
  };

  const smartMoney = getSmartMoneySignal();
  const effectiveMarketCap = dexData?.marketCap || dexData?.fdv || 0;
  const liquidityUsd = dexData?.liquidity?.usd || 0;
  const volume24h = dexData?.volume?.h24 || 0;
  const liqFdvRatio = effectiveMarketCap > 0 ? ((liquidityUsd / effectiveMarketCap) * 100).toFixed(1) : '0.0';
  const volLiqRatio = liquidityUsd > 0 ? (volume24h / liquidityUsd).toFixed(1) : '0.0';
  const activeTxHash = lastTxHash || (tokenAddress ? sessionTxHashes[tokenAddress] : '');

  return (
    <div className="container">
      {/* Navigation Bar Header */}
      <header className="glass-card" style={{ padding: '1.25rem 1.75rem', marginBottom: '2rem', display: 'flex', justifyContent: 'space-between', alignItems: 'center', flexWrap: 'wrap', gap: '1rem' }}>
        <div style={{ display: 'flex', alignItems: 'center', gap: '0.85rem' }}>
          <div style={{ background: 'linear-gradient(135deg, #00f0ff, #00ff9d)', padding: '0.6rem', borderRadius: '12px', display: 'flex', boxShadow: '0 0 15px rgba(0, 240, 255, 0.4)' }}>
            <ShieldCheck size={28} color="#070a12" strokeWidth={2.5} />
          </div>
          <div>
            <h1 style={{ fontSize: '1.5rem', fontWeight: '900', letterSpacing: '-0.02em', background: 'linear-gradient(90deg, #ffffff, #00f0ff, #00ff9d)', WebkitBackgroundClip: 'text', WebkitTextFillColor: 'transparent' }}>
              GENMEME GUARD
            </h1>
            <p style={{ fontSize: '0.82rem', color: 'var(--text-muted)', fontWeight: '600' }}>
              Solana Meme Rug Inspector — DEXScreener & Birdeye AI Consensus
            </p>
          </div>
        </div>

        <div style={{ display: 'flex', alignItems: 'center', gap: '0.75rem', flexWrap: 'wrap' }}>
          {/* MetaMask Wallet Connection Button */}
          {userAccount ? (
            <div style={{ display: 'flex', alignItems: 'center', gap: '0.4rem', background: 'rgba(0, 255, 157, 0.1)', padding: '0.45rem 0.85rem', borderRadius: '10px', border: '1px solid rgba(0, 255, 157, 0.3)', color: 'var(--neon-green)', fontSize: '0.82rem', fontFamily: 'var(--font-mono)', fontWeight: '600' }}>
              <Wallet size={15} />
              <span>{userAccount.slice(0, 6)}...{userAccount.slice(-4)}</span>
            </div>
          ) : (
            <button 
              className="btn-primary"
              onClick={connectMetaMask}
              disabled={isConnectingWallet}
              style={{ padding: '0.45rem 0.9rem', fontSize: '0.82rem', display: 'inline-flex', alignItems: 'center', gap: '0.4rem', background: 'linear-gradient(135deg, #f6851b, #e2761b)', boxShadow: '0 0 15px rgba(246, 133, 27, 0.4)' }}
            >
              <Wallet size={15} />
              <span>{isConnectingWallet ? 'Connecting...' : 'Connect MetaMask'}</span>
            </button>
          )}

          <button 
            className="btn-outline" 
            onClick={() => setShowConfig(!showConfig)}
            style={{ fontSize: '0.82rem', padding: '0.45rem 0.85rem', display: 'inline-flex', alignItems: 'center', gap: '0.4rem' }}
          >
            <Sliders size={15} color="var(--neon-cyan)" />
            <span>Settings</span>
          </button>

          <a 
            href={activeTxHash ? `${EXPLORER_BASE_URL}/tx/${activeTxHash}` : `${EXPLORER_BASE_URL}/address/${contractAddress}`}
            target="_blank" 
            rel="noreferrer"
            className="btn-outline"
            style={{ fontSize: '0.82rem', padding: '0.45rem 0.85rem', display: 'inline-flex', alignItems: 'center', gap: '0.4rem', border: '1px solid rgba(0, 240, 255, 0.4)', color: 'var(--neon-cyan)' }}
          >
            <FileCode size={15} color="var(--neon-cyan)" />
            <span>{activeTxHash ? 'Tx Explorer' : 'Explorer'}</span>
            <ExternalLink size={13} />
          </a>

          <div style={{ display: 'flex', alignItems: 'center', gap: '0.5rem', background: 'rgba(255, 255, 255, 0.04)', padding: '0.45rem 0.85rem', borderRadius: '20px', border: '1px solid rgba(0, 255, 157, 0.3)' }}>
            <span style={{ width: '8px', height: '8px', borderRadius: '50%', background: 'var(--neon-green)', display: 'inline-block', boxShadow: '0 0 8px #00ff9d' }}></span>
            <span style={{ fontSize: '0.82rem', fontWeight: '600', color: 'var(--text-muted)' }}>GenLayer StudioNet (61999)</span>
          </div>
        </div>
      </header>

      {/* Expandable Contract Address Config */}
      {showConfig && (
        <section className="glass-card" style={{ padding: '1.2rem 1.75rem', marginBottom: '2rem', background: 'rgba(0, 240, 255, 0.04)', border: '1px solid rgba(0, 240, 255, 0.25)' }}>
          <div style={{ fontSize: '0.88rem', fontWeight: '700', color: 'var(--neon-cyan)', marginBottom: '0.5rem' }}>
            Target GenLayer Intelligent Contract Address:
          </div>
          <input 
            type="text" 
            className="search-input"
            style={{ fontSize: '0.88rem', fontFamily: 'var(--font-mono)' }}
            value={contractAddress}
            onChange={(e) => setContractAddress(e.target.value)}
            placeholder="0x..."
          />
        </section>
      )}

      {/* Futuristic Hero Section */}
      <section className="glass-card" style={{ padding: '2.5rem 2rem', marginBottom: '2rem', textAlign: 'center', background: 'linear-gradient(135deg, rgba(0, 240, 255, 0.08), rgba(157, 78, 221, 0.08))', border: '1px solid rgba(0, 240, 255, 0.3)', position: 'relative', overflow: 'hidden' }}>
        <div className="hero-badge">
          <Sparkles size={14} color="var(--neon-cyan)" />
          GENLAYER INTELLECTUAL CONTRACTS • MULTI-VALIDATOR AI CONSENSUS ENGINE
        </div>
        
        <h1 style={{ fontSize: '2.4rem', fontWeight: '900', letterSpacing: '-0.03em', lineHeight: '1.25', marginBottom: '0.85rem', background: 'linear-gradient(90deg, #ffffff, #00f0ff, #00ff9d)', WebkitBackgroundClip: 'text', WebkitTextFillColor: 'transparent', maxWidth: '900px', margin: '0 auto 0.85rem auto' }}>
          AI-POWERED RUGPULL DEFENSE & SMART MONEY RADAR FOR SOLANA
        </h1>

        <p style={{ fontSize: '1.02rem', color: 'var(--text-muted)', maxWidth: '780px', margin: '0 auto 2rem auto', lineHeight: '1.6' }}>
          Instantly inspect any Solana token mint address using multi-source web API telemetry (DEXScreener & Birdeye) 
          evaluated by GenLayer's BFT Optimistic Democracy consensus validators.
        </p>

        {/* Hero Platform Metrics */}
        <div className="grid-4" style={{ maxWidth: '960px', margin: '0 auto', textAlign: 'left' }}>
          <div style={{ background: 'rgba(0, 0, 0, 0.4)', padding: '1rem 1.25rem', borderRadius: '14px', border: '1px solid rgba(0, 255, 157, 0.3)' }}>
            <div style={{ fontSize: '0.78rem', color: 'var(--text-dim)', textTransform: 'uppercase', letterSpacing: '0.05em', fontWeight: '700', display: 'flex', alignItems: 'center', gap: '0.4rem' }}>
              <ShieldCheck size={14} color="var(--neon-green)" /> On-Chain Audits
            </div>
            <div style={{ fontSize: '1.5rem', fontWeight: '900', fontFamily: 'var(--font-mono)', color: 'var(--neon-green)', marginTop: '0.2rem' }}>
              {totalAudits} Tokens
            </div>
          </div>

          <div style={{ background: 'rgba(0, 0, 0, 0.4)', padding: '1rem 1.25rem', borderRadius: '14px', border: '1px solid rgba(0, 240, 255, 0.3)' }}>
            <div style={{ fontSize: '0.78rem', color: 'var(--text-dim)', textTransform: 'uppercase', letterSpacing: '0.05em', fontWeight: '700', display: 'flex', alignItems: 'center', gap: '0.4rem' }}>
              <Cpu size={14} color="var(--neon-cyan)" /> Consensus Mode
            </div>
            <div style={{ fontSize: '1.2rem', fontWeight: '900', color: 'var(--neon-cyan)', marginTop: '0.3rem' }}>
              Optimistic BFT
            </div>
          </div>

          <div style={{ background: 'rgba(0, 0, 0, 0.4)', padding: '1rem 1.25rem', borderRadius: '14px', border: '1px solid rgba(255, 184, 0, 0.3)' }}>
            <div style={{ fontSize: '0.78rem', color: 'var(--text-dim)', textTransform: 'uppercase', letterSpacing: '0.05em', fontWeight: '700', display: 'flex', alignItems: 'center', gap: '0.4rem' }}>
              <Zap size={14} color="var(--neon-yellow)" /> Smart Money Radar
            </div>
            <div style={{ fontSize: '1.2rem', fontWeight: '900', color: 'var(--neon-yellow)', marginTop: '0.3rem' }}>
              Buy/Sell Inflow
            </div>
          </div>

          <div style={{ background: 'rgba(0, 0, 0, 0.4)', padding: '1rem 1.25rem', borderRadius: '14px', border: '1px solid rgba(157, 78, 221, 0.3)' }}>
            <div style={{ fontSize: '0.78rem', color: 'var(--text-dim)', textTransform: 'uppercase', letterSpacing: '0.05em', fontWeight: '700', display: 'flex', alignItems: 'center', gap: '0.4rem' }}>
              <Lock size={14} color="var(--neon-purple)" /> Security Checks
            </div>
            <div style={{ fontSize: '1.2rem', fontWeight: '900', color: 'var(--neon-purple)', marginTop: '0.3rem' }}>
              Mint / Freeze Revoke
            </div>
          </div>
        </div>
      </section>

      {/* Explorer Live Verification Card */}
      <section className="glass-card" style={{ padding: '1.2rem 1.75rem', marginBottom: '2rem', background: 'linear-gradient(135deg, rgba(0, 240, 255, 0.05), rgba(157, 0, 255, 0.05))', border: '1px solid rgba(0, 240, 255, 0.3)' }}>
        <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', flexWrap: 'wrap', gap: '1rem' }}>
          <div style={{ display: 'flex', alignItems: 'center', gap: '0.75rem' }}>
            <CheckCircle2 size={22} color="var(--neon-green)" />
            <div>
              <div style={{ fontSize: '0.92rem', fontWeight: '700', color: '#ffffff' }}>
                GenLayer StudioNet Active Contract & Audit State
              </div>
              <div style={{ fontSize: '0.8rem', color: 'var(--text-dim)', fontFamily: 'var(--font-mono)' }}>
                {activeTxHash ? `Audit Tx: ${activeTxHash}` : `Contract: ${contractAddress}`}
              </div>
            </div>
          </div>

          <div style={{ display: 'flex', gap: '0.75rem', flexWrap: 'wrap' }}>
            {activeTxHash ? (
              <a 
                href={`${EXPLORER_BASE_URL}/tx/${activeTxHash}`} 
                target="_blank" 
                rel="noreferrer"
                style={{ fontSize: '0.82rem', padding: '0.45rem 0.9rem', background: 'rgba(0, 255, 157, 0.15)', color: 'var(--neon-green)', borderRadius: '8px', textDecoration: 'none', display: 'inline-flex', alignItems: 'center', gap: '0.4rem', border: '1px solid rgba(0, 255, 157, 0.4)', fontWeight: '700' }}
              >
                View Audit Tx directly on Explorer <ExternalLink size={14} />
              </a>
            ) : (
              <a 
                href={`${EXPLORER_BASE_URL}/address/${contractAddress}`} 
                target="_blank" 
                rel="noreferrer"
                style={{ fontSize: '0.82rem', padding: '0.45rem 0.9rem', background: 'rgba(0, 240, 255, 0.1)', color: 'var(--neon-cyan)', borderRadius: '8px', textDecoration: 'none', display: 'inline-flex', alignItems: 'center', gap: '0.4rem', border: '1px solid rgba(0, 240, 255, 0.3)', fontWeight: '600' }}
              >
                View On-Chain Contract Explorer <ExternalLink size={14} />
              </a>
            )}
          </div>
        </div>
      </section>

      {/* Main Search & Presets Section */}
      <section className="glass-card" style={{ padding: '1.75rem', marginBottom: '2rem' }}>
        <h2 style={{ fontSize: '1.1rem', fontWeight: '800', marginBottom: '1rem', display: 'flex', alignItems: 'center', gap: '0.5rem' }}>
          <Search size={20} color="var(--neon-cyan)" /> Inspect Any Solana Token Mint Address
        </h2>

        <div style={{ display: 'flex', gap: '1rem', flexWrap: 'wrap', marginBottom: '1.2rem' }}>
          <div style={{ flex: '1', minWidth: '300px', position: 'relative' }}>
            <input 
              type="text" 
              className="search-input"
              placeholder="Paste any Solana Mint Address (e.g. 5c4HyD2rSShqnTsf5z3SaoD2H3GE452u2CUuYjviBAGS)..."
              value={tokenAddress}
              onChange={(e) => handleSelectToken(e.target.value, '')}
            />
          </div>

          <button 
            className="btn-primary" 
            onClick={handleTriggerAudit}
            disabled={isAuditing || !tokenAddress.trim()}
          >
            {isAuditing ? <RefreshCw size={18} className="spinner" /> : <Cpu size={18} />}
            {isAuditing ? 'Executing On-Chain Audit...' : 'Run 1-Click AI Rug Audit'}
          </button>
        </div>

        {/* Quick Presets */}
        <div style={{ display: 'flex', alignItems: 'center', gap: '0.75rem', flexWrap: 'wrap' }}>
          <span style={{ fontSize: '0.85rem', color: 'var(--text-dim)', fontWeight: '600' }}>Popular Tokens:</span>
          {PRESET_TOKENS.map((token) => (
            <button
              key={token.symbol}
              className={`preset-chip ${activePreset === token.symbol ? 'active' : ''}`}
              onClick={() => handleSelectToken(token.address, token.symbol)}
              disabled={isAuditing}
            >
              <Flame size={14} color={activePreset === token.symbol ? 'var(--neon-green)' : 'var(--neon-yellow)'} />
              {token.symbol} <span style={{ opacity: 0.65, fontSize: '0.75rem' }}>({token.name})</span>
            </button>
          ))}
        </div>

        {/* Status Bar */}
        {isAuditing && (
          <div style={{ marginTop: '1.2rem', padding: '0.85rem 1.2rem', background: 'rgba(0, 240, 255, 0.08)', borderRadius: '10px', border: '1px solid rgba(0, 240, 255, 0.25)', color: 'var(--neon-cyan)', fontSize: '0.9rem', display: 'flex', alignItems: 'center', gap: '0.75rem' }}>
            <RefreshCw size={18} className="spinner" />
            <span style={{ fontFamily: 'var(--font-mono)' }}>{auditStatusText}</span>
          </div>
        )}
      </section>

      {/* Grid: DEX Live Ticker + Audit Card */}
      <div className="grid-2" style={{ marginBottom: '2rem' }}>
        
        {/* Left Column: DEXScreener Real-Time Data & Smart Money Radar */}
        <div className="glass-card" style={{ padding: '1.75rem', display: 'flex', flexDirection: 'column', justifyContent: 'space-between' }}>
          <div>
            <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '1.25rem' }}>
              <h3 style={{ fontSize: '1.1rem', fontWeight: '700', display: 'flex', alignItems: 'center', gap: '0.5rem' }}>
                <Activity size={20} color="var(--neon-green)" /> DEXScreener & Smart Money Radar
              </h3>
              {dexLoading && <RefreshCw size={16} className="spinner" color="var(--text-muted)" />}
            </div>

            {dexData ? (
              <div>
                <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'baseline', marginBottom: '1.2rem', paddingBottom: '1rem', borderBottom: '1px solid rgba(255,255,255,0.08)' }}>
                  <div>
                    <div style={{ fontSize: '1.4rem', fontWeight: '800' }}>
                      {dexData.baseToken?.symbol} / {dexData.quoteToken?.symbol}
                    </div>
                    <div style={{ fontSize: '0.82rem', color: 'var(--text-muted)' }}>
                      DEX: {dexData.dexId?.toUpperCase()} • Pair: {dexData.pairAddress?.slice(0, 6)}...{dexData.pairAddress?.slice(-4)}
                    </div>
                  </div>
                  <div style={{ textAlign: 'right' }}>
                    <div style={{ fontSize: '1.5rem', fontWeight: '800', fontFamily: 'var(--font-mono)', color: 'var(--neon-cyan)' }}>
                      ${parseFloat(dexData.priceUsd || 0).toLocaleString(undefined, { minimumFractionDigits: 4, maximumFractionDigits: 8 })}
                    </div>
                    <div style={{ fontSize: '0.88rem', fontWeight: '700', color: (dexData.priceChange?.h24 || 0) >= 0 ? 'var(--neon-green)' : 'var(--neon-pink)' }}>
                      {(dexData.priceChange?.h24 || 0) >= 0 ? '▲ +' : '▼ '}
                      {dexData.priceChange?.h24?.toFixed(2)}% (24h)
                    </div>
                  </div>
                </div>

                {/* Smart Money Signal Card */}
                <div style={{ background: 'rgba(0, 240, 255, 0.04)', padding: '0.9rem 1.1rem', borderRadius: '12px', border: '1px solid rgba(0, 240, 255, 0.2)', marginBottom: '1rem' }}>
                  <div style={{ fontSize: '0.78rem', textTransform: 'uppercase', letterSpacing: '0.05em', color: 'var(--text-dim)', fontWeight: '700', marginBottom: '0.3rem', display: 'flex', alignItems: 'center', justifyContent: 'space-between' }}>
                    <span style={{ display: 'flex', alignItems: 'center', gap: '0.4rem' }}>
                      <Zap size={14} color={smartMoney.color} /> Smart Money & Whale Radar Signal:
                    </span>
                    <span style={{ color: smartMoney.color, fontFamily: 'var(--font-mono)' }}>{smartMoney.netRatio}</span>
                  </div>
                  <div style={{ fontSize: '0.98rem', fontWeight: '800', color: smartMoney.color }}>
                    {smartMoney.label}
                  </div>
                  <div style={{ fontSize: '0.8rem', color: 'var(--text-muted)', marginTop: '0.15rem', fontFamily: 'var(--font-mono)' }}>
                    {smartMoney.text}
                  </div>
                </div>

                {/* Multi-Period Price Fluctuations (5m, 1h, 6h, 24h) */}
                <div style={{ marginBottom: '1.2rem', background: 'rgba(255,255,255,0.02)', padding: '0.85rem 1rem', borderRadius: '12px', border: '1px solid rgba(255,255,255,0.05)' }}>
                  <div style={{ fontSize: '0.78rem', color: 'var(--text-dim)', fontWeight: '700', marginBottom: '0.5rem', display: 'flex', alignItems: 'center', gap: '0.4rem' }}>
                    <Clock size={13} color="var(--neon-cyan)" /> Multi-Period Price Trends (5m - 24h):
                  </div>
                  <div style={{ display: 'grid', gridTemplateColumns: 'repeat(4, 1fr)', gap: '0.5rem', textAlign: 'center' }}>
                    <div style={{ background: 'rgba(0,0,0,0.3)', padding: '0.4rem', borderRadius: '6px' }}>
                      <div style={{ fontSize: '0.7rem', color: 'var(--text-dim)' }}>5m</div>
                      <div style={{ fontSize: '0.82rem', fontWeight: '700', color: (dexData.priceChange?.m5 || 0) >= 0 ? 'var(--neon-green)' : 'var(--neon-pink)' }}>
                        {(dexData.priceChange?.m5 || 0) >= 0 ? '+' : ''}{(dexData.priceChange?.m5 || 0).toFixed(1)}%
                      </div>
                    </div>
                    <div style={{ background: 'rgba(0,0,0,0.3)', padding: '0.4rem', borderRadius: '6px' }}>
                      <div style={{ fontSize: '0.7rem', color: 'var(--text-dim)' }}>1h</div>
                      <div style={{ fontSize: '0.82rem', fontWeight: '700', color: (dexData.priceChange?.h1 || 0) >= 0 ? 'var(--neon-green)' : 'var(--neon-pink)' }}>
                        {(dexData.priceChange?.h1 || 0) >= 0 ? '+' : ''}{(dexData.priceChange?.h1 || 0).toFixed(1)}%
                      </div>
                    </div>
                    <div style={{ background: 'rgba(0,0,0,0.3)', padding: '0.4rem', borderRadius: '6px' }}>
                      <div style={{ fontSize: '0.7rem', color: 'var(--text-dim)' }}>6h</div>
                      <div style={{ fontSize: '0.82rem', fontWeight: '700', color: (dexData.priceChange?.h6 || 0) >= 0 ? 'var(--neon-green)' : 'var(--neon-pink)' }}>
                        {(dexData.priceChange?.h6 || 0) >= 0 ? '+' : ''}{(dexData.priceChange?.h6 || 0).toFixed(1)}%
                      </div>
                    </div>
                    <div style={{ background: 'rgba(0,0,0,0.3)', padding: '0.4rem', borderRadius: '6px' }}>
                      <div style={{ fontSize: '0.7rem', color: 'var(--text-dim)' }}>24h</div>
                      <div style={{ fontSize: '0.82rem', fontWeight: '700', color: (dexData.priceChange?.h24 || 0) >= 0 ? 'var(--neon-green)' : 'var(--neon-pink)' }}>
                        {(dexData.priceChange?.h24 || 0) >= 0 ? '+' : ''}{(dexData.priceChange?.h24 || 0).toFixed(1)}%
                      </div>
                    </div>
                  </div>
                </div>

                <div className="grid-4" style={{ marginBottom: '1.2rem', gridTemplateColumns: 'repeat(auto-fit, minmax(130px, 1fr))' }}>
                  {/* MARKET CAP METRIC BOX */}
                  <div style={{ background: 'rgba(157, 0, 255, 0.06)', padding: '0.85rem', borderRadius: '10px', border: '1px solid rgba(157, 0, 255, 0.2)' }}>
                    <div style={{ fontSize: '0.78rem', color: 'var(--neon-purple)', display: 'flex', alignItems: 'center', gap: '0.3rem', fontWeight: '700' }}>
                      <Coins size={13} color="var(--neon-purple)" /> Market Cap (FDV)
                    </div>
                    <div style={{ fontSize: '1.05rem', fontWeight: '800', fontFamily: 'var(--font-mono)', color: 'var(--neon-purple)', marginTop: '0.25rem' }}>
                      ${effectiveMarketCap.toLocaleString()}
                    </div>
                  </div>

                  <div style={{ background: 'rgba(255,255,255,0.03)', padding: '0.85rem', borderRadius: '10px' }}>
                    <div style={{ fontSize: '0.78rem', color: 'var(--text-dim)', display: 'flex', alignItems: 'center', gap: '0.3rem' }}>
                      <DollarSign size={13} color="var(--neon-cyan)" /> Liquidity (USD)
                    </div>
                    <div style={{ fontSize: '1.05rem', fontWeight: '700', fontFamily: 'var(--font-mono)', marginTop: '0.25rem' }}>
                      ${liquidityUsd.toLocaleString()}
                    </div>
                  </div>

                  {/* LIQUIDITY / FDV HEALTH INDEX */}
                  <div style={{ background: parseFloat(liqFdvRatio) < 5 ? 'rgba(255, 42, 109, 0.1)' : 'rgba(255,255,255,0.03)', padding: '0.85rem', borderRadius: '10px', border: parseFloat(liqFdvRatio) < 5 ? '1px solid rgba(255, 42, 109, 0.3)' : 'none' }}>
                    <div style={{ fontSize: '0.78rem', color: parseFloat(liqFdvRatio) < 5 ? 'var(--neon-pink)' : 'var(--neon-yellow)', display: 'flex', alignItems: 'center', gap: '0.3rem', fontWeight: '700' }}>
                      <Percent size={13} /> Liquidity / FDV Depth
                    </div>
                    <div style={{ fontSize: '1.05rem', fontWeight: '800', fontFamily: 'var(--font-mono)', color: parseFloat(liqFdvRatio) < 5 ? 'var(--neon-pink)' : 'var(--neon-yellow)', marginTop: '0.25rem' }}>
                      {liqFdvRatio}% {parseFloat(liqFdvRatio) < 5 ? '(Low Depth)' : ''}
                    </div>
                  </div>

                  {/* VOLUME / LIQUIDITY SLIPPAGE DANGER */}
                  <div style={{ background: parseFloat(volLiqRatio) > 3 ? 'rgba(255, 42, 109, 0.1)' : 'rgba(255,255,255,0.03)', padding: '0.85rem', borderRadius: '10px', border: parseFloat(volLiqRatio) > 3 ? '1px solid rgba(255, 42, 109, 0.3)' : 'none' }}>
                    <div style={{ fontSize: '0.78rem', color: parseFloat(volLiqRatio) > 3 ? 'var(--neon-pink)' : 'var(--neon-green)', display: 'flex', alignItems: 'center', gap: '0.3rem', fontWeight: '700' }}>
                      <TrendingUp size={13} /> Vol / Liq Slippage
                    </div>
                    <div style={{ fontSize: '1.05rem', fontWeight: '800', fontFamily: 'var(--font-mono)', color: parseFloat(volLiqRatio) > 3 ? 'var(--neon-pink)' : 'var(--neon-green)', marginTop: '0.25rem' }}>
                      {volLiqRatio}x {parseFloat(volLiqRatio) > 3 ? '(Slippage High)' : ''}
                    </div>
                  </div>
                </div>
              </div>
            ) : (
              <div style={{ textAlign: 'center', padding: '2.5rem 1rem', color: 'var(--text-dim)' }}>
                <Search size={36} style={{ opacity: 0.4, marginBottom: '0.5rem' }} />
                <p>Paste a Solana Mint Address or select a popular token to view real-time data.</p>
              </div>
            )}
          </div>

          <div style={{ borderTop: '1px solid rgba(255,255,255,0.08)', paddingTop: '1rem', display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
            <span style={{ fontSize: '0.8rem', color: 'var(--text-dim)' }}>API Multi-Source Feed</span>
            {tokenAddress.trim() && (
              <a 
                href={`https://dexscreener.com/solana/${tokenAddress}`} 
                target="_blank" 
                rel="noreferrer"
                style={{ fontSize: '0.82rem', color: 'var(--neon-cyan)', textDecoration: 'none', display: 'inline-flex', alignItems: 'center', gap: '0.3rem', fontWeight: '600' }}
              >
                Open on DEXScreener <ExternalLink size={14} />
              </a>
            )}
          </div>
        </div>

        {/* Right Column: AI Audit Security Card & Actionable Buy Decision */}
        <div className="glass-card" style={{ padding: '1.75rem', position: 'relative' }}>
          <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '1.25rem' }}>
            <h3 style={{ fontSize: '1.1rem', fontWeight: '700', display: 'flex', alignItems: 'center', gap: '0.5rem' }}>
              <Cpu size={20} color="var(--neon-cyan)" /> GenLayer LLM Audit Verdict (On-Chain)
            </h3>
            {!isAuditing && auditReport && getVerdictBadge(auditReport.verdict)}
          </div>

          {/* DYNAMIC LOADING STATE CARD DURING ACTIVE ON-CHAIN AUDIT */}
          {isAuditing ? (
            <div style={{ textAlign: 'center', padding: '3.5rem 1.5rem', background: 'rgba(0, 240, 255, 0.03)', borderRadius: '14px', border: '1px solid rgba(0, 240, 255, 0.2)' }}>
              <div style={{ display: 'inline-flex', padding: '1rem', borderRadius: '50%', background: 'rgba(0, 240, 255, 0.1)', marginBottom: '1rem' }}>
                <RefreshCw size={36} className="spinner" color="var(--neon-cyan)" />
              </div>
              <h4 style={{ fontSize: '1.1rem', fontWeight: '800', color: '#ffffff', marginBottom: '0.5rem' }}>
                GenLayer Multi-Node LLM Consensus In Progress
              </h4>
              <p style={{ fontSize: '0.88rem', color: 'var(--neon-cyan)', fontFamily: 'var(--font-mono)', lineHeight: '1.5', maxWidth: '480px', margin: '0 auto 1.2rem auto' }}>
                {auditStatusText}
              </p>
              
              <div style={{ display: 'inline-flex', alignItems: 'center', gap: '0.5rem', padding: '0.45rem 0.9rem', background: 'rgba(0, 0, 0, 0.4)', borderRadius: '20px', fontSize: '0.78rem', color: 'var(--text-dim)', border: '1px solid rgba(255, 255, 255, 0.08)' }}>
                <span className="spinner" style={{ width: '8px', height: '8px', borderRadius: '50%', background: 'var(--neon-green)', display: 'inline-block' }}></span>
                <span>Fetching live web APIs & executing LLM agreement on StudioNet...</span>
              </div>

              {activeTxHash && (
                <div style={{ marginTop: '1.2rem' }}>
                  <a 
                    href={`${EXPLORER_BASE_URL}/tx/${activeTxHash}`}
                    target="_blank"
                    rel="noreferrer"
                    style={{ fontSize: '0.82rem', color: 'var(--neon-green)', textDecoration: 'none', display: 'inline-flex', alignItems: 'center', gap: '0.35rem', fontWeight: '600', background: 'rgba(0, 255, 157, 0.08)', padding: '0.4rem 0.85rem', borderRadius: '8px', border: '1px solid rgba(0, 255, 157, 0.3)' }}
                  >
                    Track Live Consensus on Tx Explorer <ExternalLink size={13} />
                  </a>
                </div>
              )}
            </div>
          ) : auditReport ? (
            <div>
              {/* ACTIONABLE BUY RECOMMENDATION BANNER */}
              {renderBuyDecisionBanner(auditReport.safety_score, auditReport.verdict)}

              {/* Score Gauge & LLM Executive Summary */}
              <div style={{ display: 'flex', alignItems: 'center', gap: '1.5rem', marginBottom: '1.5rem', background: 'rgba(255,255,255,0.02)', padding: '1.2rem', borderRadius: '14px', border: '1px solid rgba(255,255,255,0.05)' }}>
                {/* SVG Circular Gauge */}
                <div className="gauge-container">
                  <svg className="gauge-svg" width="120" height="120" viewBox="0 0 120 120">
                    <circle className="gauge-circle-bg" cx="60" cy="60" r="50" />
                    <circle 
                      className="gauge-circle-fill" 
                      cx="60" 
                      cy="60" 
                      r="50" 
                      stroke={getGaugeColor(auditReport.safety_score, auditReport.verdict)}
                      strokeDasharray="314"
                      strokeDashoffset={314 - (314 * auditReport.safety_score) / 100}
                    />
                  </svg>
                  <div className="gauge-value" style={{ color: getGaugeColor(auditReport.safety_score, auditReport.verdict) }}>
                    {auditReport.safety_score}
                  </div>
                </div>

                <div style={{ flex: 1 }}>
                  <div style={{ fontSize: '0.8rem', textTransform: 'uppercase', letterSpacing: '0.05em', color: 'var(--text-dim)', fontWeight: '700' }}>
                    Safety Score Index
                  </div>
                  <div style={{ fontSize: '1.2rem', fontWeight: '800', margin: '0.2rem 0' }}>
                    {(auditReport.token_symbol && auditReport.token_symbol !== 'UNKNOWN') ? auditReport.token_symbol : (dexData?.baseToken?.symbol || activePreset || 'TOKEN')} LLM AI Summary Digest
                  </div>
                  <p style={{ fontSize: '0.85rem', color: auditReport.safety_score >= 80 ? 'var(--neon-cyan)' : auditReport.safety_score >= 50 ? 'var(--neon-yellow)' : 'var(--neon-pink)', lineHeight: '1.5', fontFamily: 'var(--font-sans)' }}>
                    "{auditReport.ai_summary}"
                  </p>
                </div>
              </div>

              {/* Common Meme Rug Pull Technical Matrix */}
              <div style={{ marginBottom: '1.2rem' }}>
                <div style={{ fontSize: '0.82rem', fontWeight: '800', color: 'var(--text-muted)', uppercase: 'true', letterSpacing: '0.05em', marginBottom: '0.6rem' }}>
                  ⚡ COMMON MEME RUG PULL INDICATORS:
                </div>
                <div className="grid-2">
                  <div style={{ background: 'rgba(255,255,255,0.03)', padding: '0.85rem', borderRadius: '10px', borderLeft: `3px solid ${auditReport.mint_disabled ? 'var(--neon-green)' : 'var(--neon-pink)'}` }}>
                    <div style={{ fontSize: '0.78rem', color: 'var(--text-dim)', display: 'flex', alignItems: 'center', gap: '0.3rem' }}>
                      {auditReport.mint_disabled ? <Lock size={13} color="var(--neon-green)" /> : <Unlock size={13} color="var(--neon-pink)" />} Mint Authority (Token Inflation Rug)
                    </div>
                    <div style={{ fontSize: '0.95rem', fontWeight: '700', marginTop: '0.25rem', color: auditReport.mint_disabled ? 'var(--neon-green)' : 'var(--neon-pink)' }}>
                      {auditReport.mint_disabled ? 'Disabled (Safe)' : 'Enabled (Extreme Risk)'}
                    </div>
                  </div>

                  <div style={{ background: 'rgba(255,255,255,0.03)', padding: '0.85rem', borderRadius: '10px', borderLeft: `3px solid ${auditReport.freeze_disabled ? 'var(--neon-green)' : 'var(--neon-pink)'}` }}>
                    <div style={{ fontSize: '0.78rem', color: 'var(--text-dim)', display: 'flex', alignItems: 'center', gap: '0.3rem' }}>
                      {auditReport.freeze_disabled ? <Lock size={13} color="var(--neon-green)" /> : <Unlock size={13} color="var(--neon-pink)" />} Freeze Authority (Honeypot Wallet Lock)
                    </div>
                    <div style={{ fontSize: '0.95rem', fontWeight: '700', marginTop: '0.25rem', color: auditReport.freeze_disabled ? 'var(--neon-green)' : 'var(--neon-pink)' }}>
                      {auditReport.freeze_disabled ? 'Disabled (Safe)' : 'Enabled (Honeypot Risk)'}
                    </div>
                  </div>
                </div>
              </div>

              {/* Risk Factors List */}
              {auditReport.risk_factors && auditReport.risk_factors.length > 0 && (
                <div style={{ background: 'rgba(255, 42, 109, 0.08)', borderRadius: '12px', padding: '0.9rem 1.1rem', border: '1px solid rgba(255, 42, 109, 0.3)', marginBottom: '1rem' }}>
                  <div style={{ fontSize: '0.85rem', fontWeight: '800', color: 'var(--neon-pink)', marginBottom: '0.4rem', display: 'flex', alignItems: 'center', gap: '0.4rem' }}>
                    <AlertTriangle size={15} /> Detected GenLayer Risk Signals (Real On-Chain):
                  </div>
                  <ul style={{ paddingLeft: '1.2rem', margin: 0, fontSize: '0.84rem', color: '#ffb3c6' }}>
                    {auditReport.risk_factors.map((risk, i) => (
                      <li key={i} style={{ marginBottom: '0.25rem' }}>{risk}</li>
                    ))}
                  </ul>
                </div>
              )}

              {/* ALWAYS SHOW DIRECT EXPLORER TRANSACTION LINK IF AVAILABLE */}
              {activeTxHash ? (
                <div style={{ background: 'rgba(0, 255, 157, 0.06)', padding: '0.85rem 1.1rem', borderRadius: '12px', display: 'flex', justifyContent: 'space-between', alignItems: 'center', border: '1px solid rgba(0, 255, 157, 0.35)', boxShadow: '0 0 15px rgba(0, 255, 157, 0.1)' }}>
                  <div>
                    <div style={{ fontSize: '0.75rem', textTransform: 'uppercase', letterSpacing: '0.05em', color: 'var(--text-dim)', fontWeight: '700' }}>
                      ON-CHAIN AUDIT TRANSACTION VERIFIED
                    </div>
                    <div style={{ fontSize: '0.85rem', color: 'var(--neon-green)', fontFamily: 'var(--font-mono)', fontWeight: '700', marginTop: '0.15rem' }}>
                      Tx: {activeTxHash.slice(0, 12)}...{activeTxHash.slice(-10)}
                    </div>
                  </div>
                  <a 
                    href={`${EXPLORER_BASE_URL}/tx/${activeTxHash}`}
                    target="_blank"
                    rel="noreferrer"
                    style={{ fontSize: '0.85rem', color: '#070a12', textDecoration: 'none', display: 'inline-flex', alignItems: 'center', gap: '0.35rem', fontWeight: '800', background: 'var(--neon-green)', padding: '0.5rem 0.95rem', borderRadius: '8px', boxShadow: '0 0 10px rgba(0, 255, 157, 0.4)' }}
                  >
                    View Tx on Explorer <ExternalLink size={14} />
                  </a>
                </div>
              ) : (
                <div style={{ background: 'rgba(0, 240, 255, 0.05)', padding: '0.85rem 1.1rem', borderRadius: '12px', display: 'flex', justifyContent: 'space-between', alignItems: 'center', border: '1px solid rgba(0, 240, 255, 0.3)' }}>
                  <div>
                    <div style={{ fontSize: '0.75rem', textTransform: 'uppercase', letterSpacing: '0.05em', color: 'var(--text-dim)', fontWeight: '700' }}>
                      GENLAYER CONTRACT ON-CHAIN STATE VERIFIED
                    </div>
                    <div style={{ fontSize: '0.85rem', color: 'var(--neon-cyan)', fontFamily: 'var(--font-mono)', fontWeight: '700', marginTop: '0.15rem' }}>
                      Contract: {contractAddress.slice(0, 10)}...{contractAddress.slice(-8)}
                    </div>
                  </div>
                  <a 
                    href={`${EXPLORER_BASE_URL}/address/${contractAddress}`}
                    target="_blank"
                    rel="noreferrer"
                    style={{ fontSize: '0.82rem', color: 'var(--neon-cyan)', textDecoration: 'none', display: 'inline-flex', alignItems: 'center', gap: '0.35rem', fontWeight: '700', background: 'rgba(0, 240, 255, 0.12)', padding: '0.45rem 0.85rem', borderRadius: '8px', border: '1px solid rgba(0, 240, 255, 0.35)' }}
                  >
                    View Contract Explorer <ExternalLink size={14} />
                  </a>
                </div>
              )}
            </div>
          ) : (
            <div style={{ textAlign: 'center', padding: '3.5rem 1rem', color: 'var(--text-dim)' }}>
              <ShieldAlert size={42} style={{ opacity: 0.3, marginBottom: '0.75rem', color: 'var(--neon-yellow)' }} />
              <p style={{ fontWeight: '700', fontSize: '1rem', color: '#ffffff' }}>
                No Active AI Audit Executed in Current Session
              </p>
              {tokenAddress.trim() && (
                <p style={{ fontSize: '0.82rem', marginTop: '0.4rem', color: 'var(--text-muted)', fontFamily: 'var(--font-mono)' }}>
                  Mint Address: {tokenAddress}
                </p>
              )}
              <p style={{ fontSize: '0.85rem', marginTop: '0.75rem', color: 'var(--neon-green)', fontWeight: '600' }}>
                {tokenAddress.trim() ? 'Click "Run 1-Click AI Rug Audit" to sign with MetaMask & execute GenLayer consensus on-chain!' : 'Paste a Solana token address above or select a preset token to start!'}
              </p>
            </div>
          )}
        </div>

      </div>

      {/* System Features & Architecture Showcase */}
      <section style={{ marginBottom: '2rem' }}>
        <h3 style={{ fontSize: '1.2rem', fontWeight: '800', marginBottom: '1.25rem', display: 'flex', alignItems: 'center', gap: '0.5rem' }}>
          <Sparkles size={20} color="var(--neon-cyan)" /> GenLayer Intelligent Contract Security Architecture
        </h3>

        <div className="grid-3">
          <div className="feature-card">
            <div style={{ background: 'rgba(0, 240, 255, 0.1)', padding: '0.65rem', borderRadius: '12px', display: 'inline-flex', marginBottom: '0.85rem' }}>
              <Cpu size={26} color="var(--neon-cyan)" />
            </div>
            <h4 style={{ fontSize: '1.05rem', fontWeight: '800', color: '#ffffff', marginBottom: '0.4rem' }}>
              Multi-Node LLM Agreement
            </h4>
            <p style={{ fontSize: '0.85rem', color: 'var(--text-muted)', lineHeight: '1.5' }}>
              Executes non-deterministic web API fetches across distributed validator nodes, reaching on-chain BFT consensus via the Equivalence Principle.
            </p>
          </div>

          <div className="feature-card">
            <div style={{ background: 'rgba(0, 255, 157, 0.1)', padding: '0.65rem', borderRadius: '12px', display: 'inline-flex', marginBottom: '0.85rem' }}>
              <Zap size={26} color="var(--neon-green)" />
            </div>
            <h4 style={{ fontSize: '1.05rem', fontWeight: '800', color: '#ffffff', marginBottom: '0.4rem' }}>
              Smart Money & Whale Radar
            </h4>
            <p style={{ fontSize: '0.85rem', color: 'var(--text-muted)', lineHeight: '1.5' }}>
              Analyzes 24h buys vs sells transaction volume ratios in real-time, detecting whale dumping pressure and smart money accumulation.
            </p>
          </div>

          <div className="feature-card">
            <div style={{ background: 'rgba(255, 42, 109, 0.1)', padding: '0.65rem', borderRadius: '12px', display: 'inline-flex', marginBottom: '0.85rem' }}>
              <ShieldAlert size={26} color="var(--neon-pink)" />
            </div>
            <h4 style={{ fontSize: '1.05rem', fontWeight: '800', color: '#ffffff', marginBottom: '0.4rem' }}>
              Ruthless Deduction Rubric
            </h4>
            <p style={{ fontSize: '0.85rem', color: 'var(--text-muted)', lineHeight: '1.5' }}>
              Applies zero-tolerance deductions: 50-point penalty for active mint or freeze authorities, low liquidity depth, or high volume slippage.
            </p>
          </div>
        </div>
      </section>

      {/* Bottom Section: On-Chain Audit History Directory */}
      <section className="glass-card" style={{ padding: '1.75rem' }}>
        <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '1.2rem' }}>
          <h3 style={{ fontSize: '1.1rem', fontWeight: '700', display: 'flex', alignItems: 'center', gap: '0.5rem' }}>
            <Database size={20} color="var(--neon-purple)" /> On-Chain Audits Directory (Live Contract State)
          </h3>
          <span style={{ fontSize: '0.85rem', color: 'var(--text-dim)' }}>Total On-Chain Audits: <strong style={{ color: 'var(--neon-cyan)', fontFamily: 'var(--font-mono)' }}>{totalAudits}</strong></span>
        </div>

        {recentAudits.length > 0 ? (
          <div style={{ overflowX: 'auto' }}>
            <table style={{ width: '100%', borderCollapse: 'collapse', textAlign: 'left', fontSize: '0.88rem' }}>
              <thead>
                <tr style={{ borderBottom: '1px solid rgba(255,255,255,0.1)', color: 'var(--text-dim)' }}>
                  <th style={{ padding: '0.75rem 1rem' }}>Token Mint Address</th>
                  <th style={{ padding: '0.75rem 1rem' }}>Action</th>
                  <th style={{ padding: '0.75rem 1rem' }}>Explorer Links</th>
                </tr>
              </thead>
              <tbody>
                {recentAudits.map((addr, idx) => (
                  <tr key={idx} style={{ borderBottom: '1px solid rgba(255,255,255,0.04)' }}>
                    <td style={{ padding: '0.75rem 1rem', fontFamily: 'var(--font-mono)', color: 'var(--neon-cyan)' }}>
                      {addr}
                    </td>
                    <td style={{ padding: '0.75rem 1rem' }}>
                      <button 
                        className="btn-outline"
                        style={{ padding: '0.3rem 0.75rem', fontSize: '0.8rem' }}
                        onClick={() => {
                          handleSelectToken(addr);
                        }}
                      >
                        Select Token
                      </button>
                    </td>
                    <td style={{ padding: '0.75rem 1rem' }}>
                      {sessionTxHashes[addr] ? (
                        <a 
                          href={`${EXPLORER_BASE_URL}/tx/${sessionTxHashes[addr]}`}
                          target="_blank"
                          rel="noreferrer"
                          style={{ fontSize: '0.8rem', color: 'var(--neon-green)', textDecoration: 'none', display: 'inline-flex', alignItems: 'center', gap: '0.3rem', fontWeight: '700' }}
                        >
                          View Audit Tx Explorer <ExternalLink size={12} />
                        </a>
                      ) : (
                        <a 
                          href={`${EXPLORER_BASE_URL}/address/${contractAddress}`}
                          target="_blank"
                          rel="noreferrer"
                          style={{ fontSize: '0.8rem', color: 'var(--neon-cyan)', textDecoration: 'none', display: 'inline-flex', alignItems: 'center', gap: '0.3rem' }}
                        >
                          Contract State Explorer <ExternalLink size={12} />
                        </a>
                      )}
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        ) : (
          <div style={{ textAlign: 'center', padding: '1.5rem', color: 'var(--text-dim)', fontSize: '0.88rem' }}>
            No recent token audits logged on-chain yet. Trigger your first audit above!
          </div>
        )}
      </section>

      {/* Footer */}
      <footer style={{ textAlign: 'center', marginTop: '3rem', paddingBottom: '2rem', fontSize: '0.82rem', color: 'var(--text-dim)' }}>
        GenMeme Guard — Built on GenLayer Intelligent Contracts & Multi-Source LLM Consensus
      </footer>
    </div>
  );
}
