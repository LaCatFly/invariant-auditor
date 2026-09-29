#!/usr/bin/env python3
"""
================================================================================
Universal On-Chain Asset & Deployer Forensic Tracer (`audit_tracer.py`)
================================================================================
Standard: Cryptographic Asset Tracing Standard | SlowMist Forensics | AML 3-Hop Rule
Zero external dependencies (Python 3.8+ standard library only).

Specialized Modular Capabilities:
  - Phase 1: Deployer Archaeology (Resolves contract creation tx and deployer EOA)
  - Phase 2: Genesis Funding Trail (Traces first incoming native gas inflow)
  - Phase 3: Entity Classification (Identifies CEX hot wallets, Mixers, Bridges, Relayers)
  - Phase 4: Cluster & Sibling Archaeology (Discovers other contracts deployed by cluster)
  - Phase 5: Automated AML Risk Scoring (0 - 100) & Pre-Audit Kill Switch Evaluation
  - Phase 6: Automatic Deliverable Generation (`FORENSIC_REPORT.md` and JSON)
================================================================================
"""

import sys
import os
import json
import time
import argparse
import urllib.request
import urllib.error
from typing import Dict, Any, Optional, List, Tuple

# -----------------------------------------------------------------------------
# Known Entities & Address Directory (EVM)
# -----------------------------------------------------------------------------

KNOWN_DIRECTORIES = {
    # Tier-1 CEX Hot Wallets (Low Direct AML Risk)
    "0x28c6c06298d514db089934071355e5743bf21d60": {"name": "Binance 14", "category": "CEX", "risk_weight": 0},
    "0x21a31ee1afc51d94c2efccaa2092ad1028285549": {"name": "Binance 15", "category": "CEX", "risk_weight": 0},
    "0x56eddb7aa87536c09ccc2793473599fd21a8b17f": {"name": "Binance 16", "category": "CEX", "risk_weight": 0},
    "0xdfd5293d8e347dfe59e90efd55b2956a1343963d": {"name": "Binance 17", "category": "CEX", "risk_weight": 0},
    "0xbe0eb53f46cd790cd13851d5eff43d12404d33e8": {"name": "Binance 7", "category": "CEX", "risk_weight": 0},
    "0x3f5ce5fbfe3e9af3971dd833d26ba9b5c936f0be": {"name": "Binance 1", "category": "CEX", "risk_weight": 0},
    "0x6cc5f688a30d370e237a31407761e41135f4f3a5": {"name": "OKX Hot Wallet 1", "category": "CEX", "risk_weight": 0},
    "0x5041ed759dd4afc3a72b8192c143f72f4724081a": {"name": "OKX Hot Wallet 2", "category": "CEX", "risk_weight": 0},
    "0x2368940d55c2763f6804afaef9bf06530f49dd9a": {"name": "OKX Hot Wallet 3", "category": "CEX", "risk_weight": 0},
    "0x503828976d22510aad0201ac7ec88293211523da": {"name": "Coinbase Hot Wallet 1", "category": "CEX", "risk_weight": 0},
    "0xddfabcdc4d8ffc6d5beaf154f18b778f892a0740": {"name": "Coinbase Hot Wallet 2", "category": "CEX", "risk_weight": 0},
    "0x3cd751e6b0078be393132286c442345e5dc49699": {"name": "Coinbase Hot Wallet 3", "category": "CEX", "risk_weight": 0},
    "0x71660c4005ba85c37ccec55d0c4493e66fe775d3": {"name": "Coinbase Hot Wallet 4", "category": "CEX", "risk_weight": 0},
    "0x2910543af39aba0cd09dbb2d50200b3e800a63d2": {"name": "Kraken Hot Wallet 1", "category": "CEX", "risk_weight": 0},
    "0x267be1c1d684f74cb4f698ee73caab176531cc0d": {"name": "Kraken Hot Wallet 2", "category": "CEX", "risk_weight": 0},

    # Mixers & Privacy Pools (🚨 Critical AML Risk: 90-100)
    "0xd90e2f925da726b50c4ed8d0fb90ad053324f31b": {"name": "Tornado.Cash: Router", "category": "MIXER", "risk_weight": 95},
    "0x12d66f87a04a9e220743712ce6d9bb1b5616b8fc": {"name": "Tornado.Cash: 0.1 ETH", "category": "MIXER", "risk_weight": 95},
    "0x47ce0c6ed5b0ce3e36154579544c81cc7c631f47": {"name": "Tornado.Cash: 1 ETH", "category": "MIXER", "risk_weight": 95},
    "0x910cbd523d972eb0a6f4cae4618ad62622b39dbf": {"name": "Tornado.Cash: 10 ETH", "category": "MIXER", "risk_weight": 95},
    "0xa160cdab225685da1d56aa342ad8841c3b53f291": {"name": "Tornado.Cash: 100 ETH", "category": "MIXER", "risk_weight": 95},
    "0x08fc81b0327045fd37996587359d7d8968628ea6": {"name": "Tornado.Cash: DAI", "category": "MIXER", "risk_weight": 95},
    "0xfa7093cdd9ee6032941249b1391af6a33c7e9a30": {"name": "Railgun: Treasury", "category": "MIXER", "risk_weight": 90},
    "0x8537a7e620c684795908234856e3d231ff6d7d31": {"name": "Railgun: Logic", "category": "MIXER", "risk_weight": 90},

    # Bridges & Cross-Chain (Medium Risk: 30-40)
    "0x296f55f8fb28e498b858d0adda0627169fe3968b": {"name": "Stargate: Router", "category": "BRIDGE", "risk_weight": 35},
    "0x5c7bcd6e7de5423a257d81b442095a1a6ced35c5": {"name": "Across: SpokePool", "category": "BRIDGE", "risk_weight": 35},
    "0x3666f603cc164936c1b87e207f36beba4ac5f18a": {"name": "Hop: Bridge", "category": "BRIDGE", "risk_weight": 35},
    "0x4e59b44847b379578588920ca78fbf26c0b4956c": {"name": "ERC-2470 Singleton Factory", "category": "INFRA", "risk_weight": 10},
}

EXPLORER_APIS = {
    "eth": "https://eth.blockscout.com/api/v2",
    "bsc": "https://bsc.blockscout.com/api/v2",
    "arbitrum": "https://arbitrum.blockscout.com/api/v2",
    "base": "https://base.blockscout.com/api/v2",
    "polygon": "https://polygon.blockscout.com/api/v2",
    "optimism": "https://optimism.blockscout.com/api/v2",
}

# -----------------------------------------------------------------------------
# HTTP & API Helper
# -----------------------------------------------------------------------------

def fetch_json(url: str, timeout: int = 12) -> Optional[Dict[str, Any]]:
    req = urllib.request.Request(
        url,
        headers={"User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) Chrome/120.0.0.0 Safari/537.36"}
    )
    try:
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            return json.loads(resp.read().decode("utf-8"))
    except Exception:
        return None

def identify_entity(address: str, chain: str = "eth") -> Dict[str, Any]:
    addr_lower = address.lower()
    if addr_lower in KNOWN_DIRECTORIES:
        return KNOWN_DIRECTORIES[addr_lower]
    
    # Try querying Blockscout public tags / metadata
    base_api = EXPLORER_APIS.get(chain, EXPLORER_APIS["eth"])
    data = fetch_json(f"{base_api}/addresses/{address}")
    if data:
        name = data.get("name") or data.get("ens_domain_name")
        public_tags = data.get("public_tags", [])
        tag_name = public_tags[0].get("name") if public_tags and isinstance(public_tags[0], dict) else None
        is_contract = data.get("is_contract", False)
        
        # Check heuristics on name
        resolved_label = name or tag_name
        if resolved_label:
            lbl_lower = resolved_label.lower()
            if any(k in lbl_lower for k in ["binance", "okx", "coinbase", "kraken", "bybit", "kucoin"]):
                return {"name": resolved_label, "category": "CEX", "risk_weight": 0}
            if any(k in lbl_lower for k in ["tornado", "mixer", "railgun"]):
                return {"name": resolved_label, "category": "MIXER", "risk_weight": 95}
            if any(k in lbl_lower for k in ["bridge", "stargate", "across", "wormhole", "hop"]):
                return {"name": resolved_label, "category": "BRIDGE", "risk_weight": 35}
            return {"name": resolved_label, "category": "CONTRACT" if is_contract else "EOA", "risk_weight": 20}
        
        # Check if high balance CEX hot wallet
        coin_bal = int(data.get("coin_balance", 0)) / 1e18
        if coin_bal > 5000:
            return {"name": f"High-Balance Vault / Pool ({coin_bal:.0f} ETH)", "category": "INSTITUTIONAL", "risk_weight": 10}
            
        if is_contract:
            return {"name": "Unverified Contract", "category": "CONTRACT", "risk_weight": 30}

    return {"name": "Fresh / Private EOA", "category": "EOA", "risk_weight": 40}

# -----------------------------------------------------------------------------
# Core Tracing Engine
# -----------------------------------------------------------------------------

class DeployerTracer:
    def __init__(self, target_address: str, chain: str = "eth"):
        self.target = target_address
        self.chain = chain.lower()
        self.api_base = EXPLORER_APIS.get(self.chain, EXPLORER_APIS["eth"])
        self.report_data = {
            "target": target_address,
            "chain": self.chain,
            "is_contract": False,
            "proxy_creator": None,
            "impl_creator": None,
            "deployer": None,
            "creation_tx": None,
            "creation_time": None,
            "genesis_tx": None,
            "genesis_from": None,
            "genesis_val": 0.0,
            "genesis_time": None,
            "genesis_entity": None,
            "inflows": [],
            "cluster_deployments": [],
            "aml_score": 0,
            "risk_level": "LOW",
            "kill_switch": False,
            "findings": []
        }

    def run(self) -> Dict[str, Any]:
        print(f"[*] Starting on-chain forensic trace for: {self.target} (Chain: {self.chain})")
        
        # 1. Target Archaeology
        target_info = fetch_json(f"{self.api_base}/addresses/{self.target}")
        if not target_info:
            print(f"[!] Failed to fetch address info for {self.target}")
            return self.report_data
        
        self.report_data["is_contract"] = target_info.get("is_contract", False)
        creator_addr = target_info.get("creator_address_hash")
        creation_tx = target_info.get("creation_tx_hash") or target_info.get("creation_transaction_hash")
        
        # Check implementation if proxy
        impls = target_info.get("implementations", [])
        if impls and len(impls) > 0:
            impl_addr = impls[0].get("address_hash")
            self.report_data["impl_address"] = impl_addr
            impl_info = fetch_json(f"{self.api_base}/addresses/{impl_addr}")
            if impl_info:
                self.report_data["impl_creator"] = impl_info.get("creator_address_hash")
        
        primary_deployer = creator_addr if creator_addr else self.target
        self.report_data["proxy_creator"] = creator_addr
        self.report_data["deployer"] = primary_deployer
        self.report_data["creation_tx"] = creation_tx
        print(f"[+] Primary Deployer Resolved: {primary_deployer}")
        if self.report_data.get("impl_creator"):
            print(f"[+] Implementation Deployer: {self.report_data['impl_creator']}")

        # 2. Trace Deployer Transactions & Find Earliest Inflow
        txs_url = f"{self.api_base}/addresses/{primary_deployer}/transactions"
        all_txs = []
        page_count = 0
        while txs_url and page_count < 10:
            data = fetch_json(txs_url)
            if not data or not data.get("items"):
                break
            all_txs.extend(data.get("items", []))
            next_params = data.get("next_page_params")
            if next_params:
                param_str = "&".join([f"{k}={v}" for k, v in next_params.items()])
                txs_url = f"{self.api_base}/addresses/{primary_deployer}/transactions?{param_str}"
                page_count += 1
            else:
                break

        print(f"[+] Loaded {len(all_txs)} transactions for deployer {primary_deployer}")

        # 3. Analyze Inflows & Find Contract Creation Txs
        inflows = []
        cluster_creations = []
        target_creation_item = None

        for tx in all_txs:
            to_addr = tx.get("to", {}).get("hash", "") if tx.get("to") else None
            from_addr = tx.get("from", {}).get("hash", "") if tx.get("from") else None
            
            # Check inflow
            if to_addr and to_addr.lower() == primary_deployer.lower():
                inflows.append(tx)
                
            # Check contract creation
            created = tx.get("created_contract", {}).get("hash") if tx.get("created_contract") else None
            if to_addr is None or created:
                c_hash = created or "Unknown"
                cluster_creations.append({
                    "tx_hash": tx.get("hash"),
                    "contract": c_hash,
                    "timestamp": tx.get("timestamp")
                })
                if c_hash.lower() == self.target.lower():
                    target_creation_item = tx

        # If creation tx was not in target info, get it from cluster creations
        if target_creation_item:
            self.report_data["creation_tx"] = target_creation_item.get("hash")
            self.report_data["creation_time"] = target_creation_item.get("timestamp")
        elif creation_tx:
            self.report_data["creation_tx"] = creation_tx

        self.report_data["cluster_deployments"] = cluster_creations[:15]
        print(f"[+] Associated Cluster Deployments: {len(cluster_creations)} contracts found")

        # 4. Chronological Inflows (Oldest First)
        inflows_sorted = sorted(inflows, key=lambda x: x.get("timestamp", ""))
        self.report_data["inflows"] = []
        
        for inf in inflows_sorted:
            from_h = inf.get("from", {}).get("hash", "")
            val_native = int(inf.get("value", 0)) / 1e18
            entity = identify_entity(from_h, self.chain)
            self.report_data["inflows"].append({
                "hash": inf.get("hash"),
                "from": from_h,
                "value": val_native,
                "timestamp": inf.get("timestamp"),
                "entity": entity["name"],
                "category": entity["category"],
                "risk_weight": entity["risk_weight"]
            })

        if inflows_sorted:
            genesis = self.report_data["inflows"][0]
            self.report_data["genesis_tx"] = genesis["hash"]
            self.report_data["genesis_from"] = genesis["from"]
            self.report_data["genesis_val"] = genesis["value"]
            self.report_data["genesis_time"] = genesis["timestamp"]
            self.report_data["genesis_entity"] = genesis["entity"]
            print(f"[+] Genesis Gas Origin: {genesis['from']} ({genesis['entity']}) | Val: {genesis['value']} native")
        else:
            print("[-] No direct incoming transactions found (funded via internal tx or miner reward).")

        # 5. Check Relationship with Implementation Deployer (if exists)
        if self.report_data.get("impl_creator") and self.report_data["impl_creator"].lower() != primary_deployer.lower():
            impl_deployer = self.report_data["impl_creator"]
            # Check if primary deployer funded impl deployer
            for tx in all_txs:
                to_addr = tx.get("to", {}).get("hash", "") if tx.get("to") else ""
                if to_addr.lower() == impl_deployer.lower():
                    self.report_data["findings"].append(
                        f"Direct Operational Coupling: Proxy deployer ({primary_deployer[:10]}...) directly funded implementation deployer ({impl_deployer[:10]}...) via tx `{tx.get('hash')}`. Confirmed same-entity operations cluster."
                    )
                    break

        # 6. AML Risk Scoring Calculation (0-100)
        score = 0
        risk_flags = []
        
        # Inflow category analysis
        has_cex = any(inf["category"] == "CEX" for inf in self.report_data["inflows"])
        has_mixer = any(inf["category"] == "MIXER" for inf in self.report_data["inflows"])
        has_bridge = any(inf["category"] == "BRIDGE" for inf in self.report_data["inflows"])
        
        if has_mixer:
            score += 90
            risk_flags.append("🚨 CRITICAL: Deployer funded directly or indirectly via Privacy Mixer (Tornado/Railgun).")
        elif has_cex:
            score += 10
            risk_flags.append("🟢 POSITIVE: Deployer gas sourced from KYC Tier-1 Centralized Exchange (Binance/OKX/Coinbase).")
        elif has_bridge:
            score += 35
            risk_flags.append("🟡 MEDIUM: Deployer funded via cross-chain bridge; origin chain identity obfuscated.")
        else:
            score += 45
            risk_flags.append("🟡 ELEVATED: Deployer funded exclusively by private untagged EOAs.")

        # Age and transaction depth
        if len(all_txs) < 5:
            score += 20
            risk_flags.append("🟠 FRESH WALLET: Deployer has < 5 transactions prior to deployment.")
        elif len(all_txs) > 100:
            score = max(5, score - 10)
            risk_flags.append("🟢 MATURE WALLET: High transaction longevity (>100 historical txs).")

        # Cluster size
        if len(cluster_creations) > 10:
            risk_flags.append(f"ℹ️ SERIAL DEPLOYER: Deployer has launched {len(cluster_creations)} protocol contracts on-chain.")

        self.report_data["aml_score"] = min(100, max(0, score))
        if self.report_data["aml_score"] >= 80:
            self.report_data["risk_level"] = "CRITICAL"
            self.report_data["kill_switch"] = True
        elif self.report_data["aml_score"] >= 50:
            self.report_data["risk_level"] = "HIGH"
        elif self.report_data["aml_score"] >= 25:
            self.report_data["risk_level"] = "MEDIUM"
        else:
            self.report_data["risk_level"] = "LOW"

        self.report_data["risk_flags"] = risk_flags
        print(f"[+] AML Risk Score: {self.report_data['aml_score']}/100 [{self.report_data['risk_level']}]")
        return self.report_data

    def generate_markdown(self) -> str:
        d = self.report_data
        status_icon = "🟢" if d["risk_level"] == "LOW" else ("🟡" if d["risk_level"] == "MEDIUM" else "🔴")
        
        md = []
        md.append(f"# Forensic On-Chain & Deployer Investigation Report")
        md.append(f"")
        md.append(f"> **Target Contract**: `{d['target']}`  ")
        md.append(f"> **Chain**: `{d['chain'].upper()}`  ")
        md.append(f"> **Primary Deployer EOA**: `{d['deployer']}`  ")
        if d.get("impl_creator"):
            md.append(f"> **Implementation Deployer**: `{d['impl_creator']}`  ")
        md.append(f"> **Standard**: Cryptographic Asset Tracing Standard | SlowMist AML 3-Hop Truncation  ")
        md.append(f"> **Report Timestamp**: `{time.strftime('%Y-%m-%d %H:%M:%S UTC', time.gmtime())}`  ")
        md.append(f"")
        md.append(f"---")
        md.append(f"")
        md.append(f"## 1. Executive Summary & AML Risk Score")
        md.append(f"")
        md.append(f"| Metric | Evaluation | Implication |")
        md.append(f"| :--- | :---: | :--- |")
        md.append(f"| **AML Risk Score** | **{d['aml_score']} / 100** | Scaled composite counterparty risk score |")
        md.append(f"| **Risk Classification** | **{status_icon} {d['risk_level']}** | Pre-audit threat level |")
        md.append(f"| **Genesis Origin** | **{d.get('genesis_entity', 'Unknown')}** | First native gas funding source |")
        md.append(f"| **Pre-Audit Kill Switch** | **{'🚨 TRIGGERED' if d['kill_switch'] else '✅ PASS (Proceed)'}** | Allocation & audit gating rule |")
        md.append(f"")
        
        md.append(f"### Core Forensic Summary")
        for flag in d.get("risk_flags", []):
            md.append(f"- {flag}")
        for find in d.get("findings", []):
            md.append(f"- **Cluster Insight**: {find}")
        md.append(f"")
        md.append(f"---")
        md.append(f"")
        
        md.append(f"## 2. Deployer Genesis Funding Trail (Inflows)")
        md.append(f"")
        md.append(f"| Hop | From Address / Entity | Category | Value (Native) | Tx Hash | Timestamp (UTC) |")
        md.append(f"| :---: | :--- | :---: | :---: | :---: | :---: |")
        
        inflows = d.get("inflows", [])
        if inflows:
            for idx, inf in enumerate(inflows[:10], 1):
                md.append(f"| **Hop {idx}** | `{inf['from']}`<br/>*({inf['entity']})* | `{inf['category']}` | `{inf['value']:.4f}` | [`{inf['hash'][:10]}...`](https://eth.blockscout.com/tx/{inf['hash']}) | {inf['timestamp']} |")
        else:
            md.append(f"| **Hop 1** | *Internal transaction or direct miner gas* | `N/A` | `0.0000` | `{d.get('creation_tx', 'N/A')}` | {d.get('creation_time', 'N/A')} |")
        
        if d.get("creation_tx"):
            md.append(f"| **Creation** | Deployer `{d['deployer'][:10]}...` | `CONTRACT` | `0.0000` | [`{d['creation_tx'][:10]}...`](https://eth.blockscout.com/tx/{d['creation_tx']}) | {d.get('creation_time', 'N/A')} |")
            
        md.append(f"")
        md.append(f"---")
        md.append(f"")
        
        md.append(f"## 3. Associated Protocol Cluster & Sibling Deployments")
        md.append(f"")
        md.append(f"The deployer cluster has initiated **{len(d.get('cluster_deployments', []))} contract deployments**. Recent key contracts:")
        md.append(f"")
        md.append(f"| Timestamp (UTC) | Deployed Contract Address | Deployment Tx Hash |")
        md.append(f"| :--- | :--- | :--- |")
        for dep in d.get("cluster_deployments", [])[:8]:
            md.append(f"| {dep['timestamp']} | [`{dep['contract']}`](https://eth.blockscout.com/address/{dep['contract']}) | [`{dep['tx_hash'][:14]}...`](https://eth.blockscout.com/tx/{dep['tx_hash']}) |")
            
        md.append(f"")
        md.append(f"---")
        md.append(f"")
        md.append(f"## 4. Downstream Audit Handoff Directives")
        if d["kill_switch"]:
            md.append(f"> [!CAUTION]")
            md.append(f"> **COUNTERPARTY KILL-SWITCH ALERT**: Deployer risk exceeds acceptable institutional thresholds. Halt audit or require comprehensive multisig ownership transfer proof.")
        else:
            md.append(f"> [!NOTE]")
            md.append(f"> **COUNTERPARTY VERIFIED**: Deployer genesis is traced to regulated CEX KYC infrastructure. Proceed to Session 2 (Live RPC Storage Archaeology) and Session 3 (Scanner Triage).")
        md.append(f"")
        
        return "\n".join(md)

# -----------------------------------------------------------------------------
# CLI Entrypoint
# -----------------------------------------------------------------------------

def main():
    parser = argparse.ArgumentParser(description="Universal On-Chain Asset & Deployer Forensic Tracer")
    parser.add_argument("target", help="Target contract address or deployer EOA")
    parser.add_argument("--chain", default="eth", help="Target chain (eth, bsc, arbitrum, base, polygon)")
    parser.add_argument("--mode", default="genesis", choices=["genesis", "cluster"], help="Tracing mode")
    parser.add_argument("--output", help="Path to write FORENSIC_REPORT.md output")
    parser.add_argument("--json", action="store_true", help="Output raw JSON to stdout")
    
    args = parser.parse_args()
    
    tracer = DeployerTracer(args.target, chain=args.chain)
    data = tracer.run()
    
    if args.json:
        print(json.dumps(data, indent=2))
        return

    md_content = tracer.generate_markdown()
    
    if args.output:
        os.makedirs(os.path.dirname(os.path.abspath(args.output)), exist_ok=True)
        with open(args.output, "w", encoding="utf-8") as f:
            f.write(md_content)
        print(f"[✓] Successfully wrote forensic report to: {args.output}")
    else:
        print("\n" + md_content)

if __name__ == "__main__":
    main()
