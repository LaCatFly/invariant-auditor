# Chapter 6: Deployer Forensic Investigation Playbook

## Core Idea
Before evaluating smart contract source code, an auditor must evaluate the deployer's origin. Malicious protocols, honeypots, and rug pulls almost always exhibit suspicious genesis funding trails or prior associations with drained contracts.

## 5-Step Deployer Audit Execution

```
[1. Extract Creation Tx] ──► Query explorer/RPC for block height of contract creation.
[2. Identify Deployer EOA] ──► Extract the msg.sender of the creation transaction.
[3. Trace Genesis Gas Tx] ──► Trace the FIRST inbound transaction to the deployer EOA.
[4. Profile Funding Cluster] ──► Categorize source (Tier-1 CEX vs Mixer vs Intermediary EOA).
[5. Historical Cross-Check] ──► Search deployer address across exploit databases and multi-chain explorers.
```

## Calculating the AML Risk Score (0–100 Formula)

$$\text{AML Score} = \text{Base Score} + \text{Mixer Penalty} + \text{Cluster Penalty} + \text{Velocity Penalty}$$

- **Base Score**: 0 (Clean CEX KYC origin) or 30 (Unknown fresh EOA origin).
- **Mixer Penalty**: +70 if funded via Tornado Cash / Railgun / Wasabi.
- **Cluster Penalty**: +50 if associated with previous failed/drained token contracts.
- **Velocity Penalty**: +20 if contract deployed within <5 minutes of gas seed funding.
- **Max Cap**: 100. (Scores $\ge 60$ represent high risk; $\ge 90$ represent critical threat).
