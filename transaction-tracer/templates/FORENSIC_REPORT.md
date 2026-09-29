# Forensic On-Chain & Deployer Investigation Report

**Target Protocol**: `<Protocol Name>`  
**Primary Contract Address**: `<0x...>`  
**Deployer EOA Address**: `<0x...>`  
**Investigated By**: `transaction-tracer` (Cryptographic Asset Tracing Standard)  
**Investigation Timestamp**: `<YYYY-MM-DD HH:MM:SS UTC>`  

---

## 1. Executive Summary & AML Risk Score

- **AML Risk Score**: `[ 0 – 100 ]` / 100
- **Risk Classification**: `[ 🟢 LOW | 🟡 MEDIUM | 🟠 HIGH | 🔴 CRITICAL ]`
- **Genesis Funding Source**: `[ Tier-1 CEX | Unknown EOA | Mixer | Cross-Chain Bridge ]`
- **Key Finding**: `<1-2 sentence core conclusion regarding deployer trustworthiness and anonymity>`

---

## 2. Deployer Genesis Funding Trail

| Hop | From Address / Entity | To Address | Value (Native) | Tx Hash | Timestamp (UTC) | Category / Notes |
| :---: | :---: | :---: | :---: | :---: | :---: | :---: |
| **Genesis (Hop 1)** | `0x...` (e.g. Binance Hot 14) | `0x...` | `0.5 ETH` | `0x...` | `YYYY-MM-DD` | Initial Gas Funding |
| **Creation** | `0x...` (Deployer) | Contract Creation | `0.0 ETH` | `0x...` | `YYYY-MM-DD` | Contract Deployment |

---

## 3. Fund Movement & Entity Analysis

- **Mixer Interactions**: `[ None Detected | Tornado Cash | Railgun ]`
- **Cross-Chain Inflow/Outflow**: `[ None | Stargate | Across | THORChain ]`
- **Associated Address Clusters**:
  - `0x...`: Deployed `<Contract_A>` on `<Chain_A>` (Status: `<Active / Drained>`)
- **Temporal Profile**: Active between `HH:MM` and `HH:MM` UTC (Estimated Timezone: `UTC±X`).

---

## 4. Operational Recommendations for Downstream Audit
- [ ] If AML Risk Score $\ge 60$, flag deployer anonymity in `AUDIT_REPORT.md` Section 1.
- [ ] Verify if admin/owner keys have been transferred to a decentralized multi-sig with timelock delay.
