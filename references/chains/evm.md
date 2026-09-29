# EVM Smart Contract Audit Reference Manual

## 🎯 Target Toolchain
- **Framework**: Foundry (`forge`, `cast`, `anvil`)
- **Static Analysis**: Slither 0.11.x, Aderyn
- **Base Harness**: `smart-contract/lib/AuditTestBase.sol`

---

## 🔍 Uniswap v4 Hook Bitwise Permission Flags

Uniswap v4 encodes hook permissions in the lowest 14 bits of the hook address:

| Bit | Flag Name | Mask Hex | Description & Risk Vector |
| :---: | :--- | :---: | :--- |
| **13** | `BEFORE_INITIALIZE` | `0x2000` | Called when pool is created. Risk: Front-running initialization parameters. |
| **12** | `AFTER_INITIALIZE` | `0x1000` | Called after pool creation. |
| **11** | `BEFORE_ADD_LIQUIDITY` | `0x0800` | Custodial risk if hook takes fee deltas or modifies amounts. |
| **10** | `AFTER_ADD_LIQUIDITY` | `0x0400` | Reentrancy risk during liquidity callback. |
| **9** | `BEFORE_REMOVE_LIQUIDITY`| `0x0200` | Interception of withdrawal funds. |
| **8** | `AFTER_REMOVE_LIQUIDITY` | `0x0100` | State sync after withdrawal. |
| **7** | `BEFORE_SWAP` | `0x0080` | Dynamic swap fee calculation (LVR mitigation). |
| **6** | `AFTER_SWAP` | `0x0040` | Post-swap accounting. |
| **5** | `BEFORE_DONATE` | `0x0020` | Donation callback interception. |
| **4** | `AFTER_DONATE` | `0x0010` | Post-donation state update. |
| **3** | `BEFORE_SWAP_RETURNS_DELTA` | `0x0008` | 🚨 **Custodial Alert**: Allows hook to alter net token output of swaps! |
| **2** | `AFTER_SWAP_RETURNS_DELTA`  | `0x0004` | 🚨 **Custodial Alert**: Allows hook to siphon swap returns! |
| **1** | `AFTER_ADD_RETURNS_DELTA`   | `0x0002` | 🚨 Hook can intercept LP deposit tokens. |
| **0** | `AFTER_REMOVE_RETURNS_DELTA`| `0x0001` | 🚨 Hook can intercept LP withdrawal tokens. |

---

## 🏦 ERC-4626 & Vault Attack Vectors

1. **Empty Vault Donation Inflation Attack**:
   - Attacker deposits 1 wei of assets, receives 1 wei of shares.
   - Attacker directly transfers (donates) $10,000 worth of assets to the vault contract.
   - Subsequent user deposits $19,999 assets $\to$ receives $\lfloor \frac{19999 \times 1}{10001} \rfloor = 1$ share.
   - Attacker redeems 1 share $\to$ gets 50% of total pool ($15,000 assets), stealing $5,000 from victim.
   - **Remediation**: Use OpenZeppelin ERC4626 with virtual shares and virtual assets offset (Decimals offset $\ge 3$).
2. **Transient Storage Reentrancy (`tload`/`tstore`)**:
   - In Cancun EVM, ensure transient storage slots are explicitly cleared at the end of every external call execution frame.

---

## 🛠️ Canonical Direct On-Chain Execution & Simulation

### 1. ERC-20 Direct Token Approvals & Allowances
```bash
# Check current allowance
cast call <TOKEN_ADDR> "allowance(address,address)(uint256)" <OWNER> <SPENDER> --rpc-url <RPC_URL>

# Approve exact deposit amount
cast send <TOKEN_ADDR> "approve(address,uint256)" <SPENDER> <AMOUNT_WEI> --rpc-url <RPC_URL> --private-key <KEY>
```

### 2. ERC-4626 Direct Vault Operations
```bash
# Deposit assets into vault
cast send <VAULT_ADDR> "deposit(uint256,address)(uint256)" <ASSET_AMOUNT> <RECEIVER> --rpc-url <RPC_URL> --private-key <KEY>

# Redeem shares for underlying assets
cast send <VAULT_ADDR> "redeem(uint256,address,address)(uint256)" <SHARES_AMOUNT> <RECEIVER> <OWNER> --rpc-url <RPC_URL> --private-key <KEY>
```

### 3. Multisig Transaction Simulation (via Foundry Anvil Fork)
```bash
# Simulate state execution on an Anvil fork before submitting to Gnosis Safe
cast rpc anvil_setBalance <SAFE_ADDR> 10000000000000000000 --rpc-url http://127.0.0.1:8545
cast send <TARGET_ADDR> <CALLDATA> --from <SAFE_ADDR> --unlocked --rpc-url http://127.0.0.1:8545
```

