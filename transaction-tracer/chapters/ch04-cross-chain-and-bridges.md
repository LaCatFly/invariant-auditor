# Chapter 4: Cross-Chain & Bridge Tracking

## Core Idea
Attackers leverage cross-chain bridges to transition between EVM chains, Layer 2 rollups, UTXO chains (Bitcoin), and high-throughput networks (Tron, Solana). Tracing requires correlating source bridge deposits with destination bridge releases via bridge explorers, transaction calldata parameters, and event logs.

```mermaid
graph LR
    Origin["Origin Chain (e.g. Ethereum)"] -->|"Deposit Tx"| BridgeRouter["Bridge Contract (Stargate / Across / THORChain)"]
    BridgeRouter -->|"Relayer / Oracle"| DestPool["Destination Pool (e.g. Arbitrum / Tron / BTC)"]
    DestPool -->|"Mint / Release"| DestAddr["Destination Recipient Address"]
```

## The 3 Bridge Tracing Methods

### Method 1: Dedicated Bridge Explorers
When the bridge provides a public indexing explorer:
- **THORChain**: `https://thorchain.net/tx/<TX_HASH>` (reveals native BTC output address and amount).
- **Wormhole**: `https://wormholescan.io` (reveals Solana / EVM target).
- **LayerZero / Stargate**: `https://layerzeroscan.com`.
- **Socket / Bungee**: `https://socketscan.io`.

### Method 2: Blockchain Explorer Calldata & Log Decoding
When a bridge lacks a dedicated explorer:
1. **Decode Input Data on Origin Tx**:
   - Locate parameters: `receiver`, `recipient`, `dstChainId`, `toAddress`.
   - *Example*: `dstChainId: 195` (TRON network) with receiver `0x05ae12A468e0eDD6C2bF05753dE3aCcF33267C6F`.
2. **EVM-to-Tron Address Format Conversion**:
   - EVM 20-byte hex: `0x05ae12A468e0eDD6C2bF05753dE3aCcF33267C6F`
   - Prefix with `0x41` and compute double SHA-256 base58check.
   - Resulting Tron address: `TAVEuovS7uVd6V9M95CqCKpdxDZQE5qSaG`.
3. **Inspect Bridge Relayer Logs**:
   - Query destination chain explorer for contract event `Mint` or `Unlock` matching the exact token amount within `timestamp ± 5 minutes`.

---

## High-Risk Cross-Chain Corridors

| Origin Ecosystem | Bridge Used | Destination Ecosystem | Primary Attacker Objective |
| :--- | :--- | :--- | :--- |
| **Ethereum L1** | THORChain | **Bitcoin (BTC)** | Convert stolen ERC-20 into non-freezable native BTC. |
| **Ethereum / Base** | Stargate / Across | **Arbitrum / Optimism** | Lower gas costs for high-frequency DEX swaps and peel chaining. |
| **BSC / Polygon** | Multichain / Bitget | **TRON (USDT-TRC20)** | Funnel into OTC networks / Telegram cash-out brokers. |
| **EVM Chains** | Allbridge / Wormhole | **Solana** | Transfer into meme coin ecosystems or unmonitored SOL wallets. |
