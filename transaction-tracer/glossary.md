# Crypto Asset Tracing Glossary

- **AML Risk Score** — A quantitative score (0–100) calculated from entity associations, mixer hops, and blacklisted wallet interactions.
- **Address Clustering** — The analytical process of grouping multiple on-chain addresses under the control of a single individual, organization, or threat actor.
- **Beacon Proxy** — A proxy design where multiple proxy contracts reference a single Beacon contract to resolve the active implementation address.
- **Burn Address** — An unspendable address without a private key (e.g., `0x0000...0000` or `0x0000...dEaD`) used to destroy assets.
- **CoinJoin** — A trustless method of combining multiple Bitcoin payments from multiple spenders into a single transaction (e.g., Wasabi, JoinMarket).
- **Deposit Address** — An exchange-managed intermediate address assigned to a user for receiving inbound deposits before sweeping to hot wallets.
- **Genesis Funding** — The initial transaction that transfers native gas tokens (ETH, SOL, TRX) to a newly generated wallet, unlocking its ability to execute operations.
- **Many-to-One Consolidation** — Funneling funds from multiple satellite wallets into a single centralized address prior to off-ramping.
- **Mixer / Tumbler** — A privacy protocol (e.g., Tornado Cash) that pools and redistributes funds to break graph traceability between senders and recipients.
- **Multi-Hop Relay** — A rapid sequence of intermediary wallet transfers designed to artificially increase path depth.
- **One-to-Many Distribution** — Fan-out transfer pattern where a central wallet disburses funds across numerous downstream addresses.
- **Peel Chain** — A sequential money laundering technique where large sums are broken down over a chain of transactions, peeling off small amounts while forwarding the bulk balance.
- **UTXO (Unspent Transaction Output)** — The indivisible accounting unit used in Bitcoin, requiring complete consumption of inputs and creation of change outputs.
