# Crypto Asset Tracing & Deployer Forensics — Patterns & Heuristics

## 🛠️ Tracing Heuristics by Ecosystem

### 1. EVM (Ethereum, Arbitrum, Base, BSC, Robinhood Chain)

#### Genesis Funding Extraction via RPC / Cast
```bash
# 1. Get first transaction hash of the deployer
cast tx-count <DEPLOYER_ADDRESS> --rpc-url <RPC_URL>

# 2. Inspect incoming balance transfer
cast balance <DEPLOYER_ADDRESS> --rpc-url <RPC_URL>

# 3. Decode contract creation transaction
cast tx <CREATION_TX_HASH> --rpc-url <RPC_URL>
```

#### Etherscan / Blockscout API Query Patterns
```bash
# Fetch normal transactions list (sorted ascending to get Genesis tx at index 0)
curl -s "https://api.etherscan.io/v2/api?chainid=1&module=account&action=txlist&address=<DEPLOYER_ADDRESS>&startblock=0&endblock=99999999&page=1&offset=10&sort=asc&apikey=<API_KEY>"
```

#### Internal Transactions & Token Transfers
- Contract creation often funds the newly created contract via constructor `msg.value`.
- Always inspect `txlistinternal` on Etherscan to detect hidden fund routes via proxy deployers (`CREATE2` factories).

---

### 2. Tron Network (TRX / TRC-20 USDT)

- **USDT Dominance**: >90% of laundering volume on Tron is USDT-TRC20.
- **Energy & Bandwidth Staking**: High-volume laundering wallets will rent energy from platforms like Feee.io or JustLend rather than burning raw TRX.
- **Tronscan API Query**:
  ```bash
  curl -s "https://apilist.tronscanapi.com/api/transaction?sort=-timestamp&count=true&limit=20&start=0&address=<TRON_ADDRESS>"
  ```

---

### 3. Solana (SOL / SPL Tokens)

- **Account Model Nuance**: Solana accounts have dedicated token accounts (ATAs) owned by the System Program or Token Program.
- **Genesis SOL Transfer**: Look for `transfer` instruction from System Program (`11111111111111111111111111111111`).
- **Solscan / Helius RPC Query**:
  ```bash
  curl -X POST https://api.mainnet-beta.solana.com -H "Content-Type: application/json" -d '{
    "jsonrpc": "2.0",
    "id": 1,
    "method": "getSignaturesForAddress",
    "params": ["<SOLANA_DEPLOYER_ADDRESS>", {"limit": 100}]
  }'
  ```

---

### 4. Bitcoin (UTXO / Change Detection)

- **One-Input Multi-Output**: In Bitcoin transactions, identify the change address by checking:
  1. Address format match (e.g. SegWit `bc1q` input paying to `bc1q` change vs Legacy `1...` recipient).
  2. Round-number amounts (e.g. `0.50000000 BTC` sent to recipient; `0.49981200 BTC` returned as change).
  3. Address history: Fresh address with zero prior history is almost always the change address.
