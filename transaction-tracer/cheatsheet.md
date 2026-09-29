# Crypto Asset Tracing & Deployer Forensics — Cheatsheet

## ⚖️ Deployer Genesis Funding Risk Scoring Matrix

| Initial Funding Source | Risk Level | AML Risk Score | Action Required |
| :--- | :--- | :--- | :--- |
| **Tier-1 CEX (Coinbase, Kraken, Binance, OKX)** | 🟢 Low | **0 – 15** | Direct KYC trail exists with Tier-1 compliance. Note CEX hot wallet source and timestamp. |
| **Tier-2 / Regional CEX (No-KYC or Gray Market)** | 🟡 Medium | **30 – 50** | Search entity tags; check if CEX has known association with money laundering corridors. |
| **Canonical Bridge from Verified EOA** | 🟡 Medium | **25 – 45** | Trace source transaction on origin chain back to root funding EOA. |
| **Multi-Hop EOA (>3 hops, fresh intermediary wallets)** | 🟠 High | **60 – 80** | Peel chain or smurfing pattern detected. Execute address clustering on intermediary hops. |
| **Privacy Mixer (Tornado Cash, Railgun, Cyclone)** | 🔴 Critical | **90 – 100** | 🚨 **Severe Red Flag**. Deployer deliberately anonymized origin. Assume adversarial intent. |
| **Direct Transfer from Known Exploit / Phishing EOA** | 🚨 Critical | **100** | 🚨 **Immediate Block**. Connected directly to malicious threat actor cluster. |

---

## 🧭 Fast Decision Trees

### 1. Identifying Peel Chains
```
Does Tx Input >> Tx Output to Recipient A AND
Remainder sent to fresh EOA (Recipient B) AND
Recipient B immediately repeats the split?
  ├─► YES: Classify as Peel Chain -> Follow high-value remainder to next hop.
  └─► NO: Standard transfer or multi-send contract.
```

### 2. Identifying CEX Deposit vs Personal Wallet
```
Does the address have thousands of incoming transfers from different EOAs AND
Periodic sweeping to a known Exchange Hot Wallet (e.g. Binance 14)?
  ├─► YES: Deposit Address (DO NOT cluster senders together).
  └─► NO: Personal EOA / Smart Contract Vault.
```

### 3. Cross-Chain Bridge Correlation
```
Tx Out on Chain A (e.g. Ethereum) via Stargate/Across Router
  └─► Note: [Exact Timestamp, Amount in USD, Destination Chain ID, Asset Symbol]
  └─► Query Bridge Explorer / Destination Chain RPC for matching inbound mint/unlock within (t ± 5 min).
```

---

## 🚩 Tells & Smells for Malicious Deployers

1. **Gas-only Seed Transfer**: Deployer wallet received exact gas amount (e.g., `0.05 ETH`) minutes before contract deployment from a one-time-use EOA.
2. **Burner Deployer Pattern**: Deployer deploys contract, transfers ownership to a multisig/timelock or renounces, and wallet never conducts any further transactions.
3. **Synchronized Multi-Deployment**: Same funding source seeded 5+ distinct deployer wallets in the same block or within 1 hour.
4. **Deployer Re-use across Rugs**: Same bytecode hash or salt found on other chains linked to historical drained liquidity pools.
