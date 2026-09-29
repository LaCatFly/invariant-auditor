# Chapter 5: Address Clustering & Behavioral Profiling

## Core Idea
Individual wallet addresses often leave behavioral, temporal, and cryptographic fingerprints that allow clustering distinct addresses under a single controller.

```
┌────────────────────────────────────────────────────────────┐
│                Address Fingerprint Profiler                │
├──────────────────────────┬─────────────────────────────────┤
│ Feature                  │ Analytical Indicator            │
├──────────────────────────┼─────────────────────────────────┤
│ Active Hours (Histogram) │ Timezone / Geographic Region    │
│ Gas Price Preference     │ Fast/Aggressive vs Economical   │
│ Client / Wallet Nonce    │ Sequential nonce alignment      │
│ dApp Interaction Pattern │ Specific DEX / Aggregator preference│
│ Seed Funding Origin      │ Shared genesis transaction hash │
└──────────────────────────┴─────────────────────────────────┘
```

## Profiling Techniques

1. **Active Time Window Analysis (Timezone Mapping)**:
   - Plot transaction counts across 24 UTC hours.
   - *Example*: Consistently active from 02:00 UTC to 14:00 UTC with complete inactivity from 15:00 to 23:00 UTC indicates UTC+8 (East/Southeast Asia timezone).
2. **Gas & Client Fingerprinting**:
   - Fixed `maxPriorityFeePerGas` (e.g. exactly 2.0 gwei) and standard RPC gas limit estimations reveal specific bot frameworks or wallet scripts (Foundry cast vs. Hardhat vs. Python web3).
3. **Multi-Wallet Gas Seeding Clusters**:
   - If Wallet X transfers `0.1 ETH` to Wallets Y1, Y2, Y3 within the same 10-minute window, Wallets Y1, Y2, Y3 belong to the same operational cluster.
