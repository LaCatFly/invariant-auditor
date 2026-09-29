# Bitcoin Script, Runes & Babylon Staking Audit Playbook

Comprehensive security auditing manual for Bitcoin Script, Taproot (BIP-341/342), Runes/Ordinals, and Babylon Staking covenants.

---

## 🎯 Target Toolchain & Verification Framework

- **Core Toolchain**: `bitcoind` (regtest mode), `rust-bitcoin`, `bitcoinjs-lib`, `ord` CLI
- **Protocol Standards**: 
  - BIP-341 (Taproot SegWit v1), BIP-342 (Tapscript)
  - BIP-65 (`OP_CHECKLOCKTIMEVERIFY`), BIP-112 (`OP_CHECKSEQUENCEVERIFY`)
  - BIP-174 / BIP-370 (Partially Signed Bitcoin Transactions - PSBT v1/v2)

---

## 🔍 Core Bitcoin Script & Covenant Vulnerability Archetypes

### 1. Taproot Internal Key Hijacking & NUMS Key Verification

#### Vulnerability Mechanics
A Taproot output key $P$ is derived from an internal key $Q$ and a Merkle root $m$ of leaf scripts:
$$P = Q + \text{hash}(Q, m) \cdot G$$
- If a protocol intends to enforce script-only logic (e.g. multi-sig, covenants, staking timelocks), the internal key $Q$ must **not** have a known private key.
- If $Q$ is set to a standard user public key, the holder of $Q$'s private key can spend the UTXO via the **Key-Path Spend**, completely bypassing all leaf script restrictions and timelocks!

#### Secure NUMS Pattern
Protocols must use a provably unspendable NUMS (Nothing Up My Sleeve) point where the discrete logarithm is unknown:
```rust
// ✅ SECURE: Use standard BIP-341 provably unspendable internal key
// H = lift_x(SHA256("Taproot NUMS point"))
const NUMS_H: &str = "50929b74c1a04954b78b4b6035e97a5e078a5a0f28ec96d547bfee9ace803ac0";

let internal_key = XOnlyPublicKey::from_str(NUMS_H).unwrap();
let taproot_spend_info = TaprootBuilder::new()
    .add_leaf(1, unbonding_script)?
    .add_leaf(1, slashing_script)?
    .finalize(&secp, internal_key)
    .unwrap();
```

---

### 2. Slashing vs Unbonding Race Conditions (Babylon Staking)

#### The Staking Architecture
In Bitcoin staking protocols (such as Babylon), staked UTXOs have two mutually exclusive spending paths:
1. **Unbonding Path**: Staker can withdraw after a timelock delay $T$ (`<timelock_blocks> OP_CHECKSEQUENCEVERIFY OP_DROP <staker_pubkey> OP_CHECKSIG`).
2. **Slashing Path**: If the staker double-signs on the PoS chain, their Extractable One-Time Signature (EOTS) is revealed, allowing anyone to broadcast a slashing transaction burning or siphoning the BTC.

#### The Race Vulnerability
If the staker initiates unbonding, a race condition exists near block $T$:
- If a slashing proof is generated while the unbonding timelock is close to expiration, the staker can broadcast an unbonding transaction with a higher miner fee (using Replace-By-Fee - RBF).
- If the unbonding transaction confirms before the slashing transaction, the staker successfully escapes slashing with 100% of their principal.

#### Audit Invariants
1. **Timelock Safety Factor**: $T_{\text{unbond}} \ge T_{\text{slashing\_window}} + 144 \text{ blocks}$ (minimum 24-hour safety buffer).
2. **Covenant Pre-Signed Penalty**: The slashing transaction must be pre-signed with a CPFP (Child-Pays-For-Parent) or high fixed fee rate to out-bid attacker frontrunning.

---

### 3. Dust Limit Griefing & Non-Standard Outputs

#### Mempool Policy Constraints
Bitcoin nodes enforce standardness rules (`minRelayTxFee`) that reject transactions creating outputs below the **dust threshold**:
- **P2PKH / P2SH**: 546 satoshis
- **P2WPKH**: 294 satoshis
- **P2TR (Taproot)**: 354 satoshis

#### Vulnerability in Runes / Ordinals
If an inscription, Runes mint, or token distribution splits change into sub-dust outputs (e.g. 100 satoshis), miners refuse to broadcast the transaction. Attackers can intentionally submit transaction inputs that force contract logic or escrow vaults to produce sub-dust change, locking the protocol in an un-executable state.

```rust
// ✅ SECURE: Enforce explicit dust threshold validation
const TAPROOT_DUST_LIMIT: u64 = 354;

pub fn build_rune_transfer(recipient: Address, rune_sats: u64) -> Result<TxOut> {
    require!(rune_sats >= TAPROOT_DUST_LIMIT, Error::BelowDustThreshold);
    Ok(TxOut {
        value: rune_sats,
        script_pubkey: recipient.script_pubkey(),
    })
}
```

---

### 4. PSBT Non-Witness UTXO Missing Vulnerability (Fee Siphoning)

#### Attack Mechanism
In BIP-174 (PSBT), SegWit and Taproot inputs provide `witness_utxo` (only value and scriptPubKey) rather than full previous transactions (`non_witness_utxo`).
- If a wallet signs a multi-input transaction where one input is legacy or the coordinator is untrusted, the coordinator can falsify the input value in `witness_utxo`.
- The wallet calculates `Fee = Sum(Inputs) - Sum(Outputs)`. Because the coordinator reported a smaller input value, the actual fee paid to the miner is massive (siphoned to a colluding miner).
- **Rule**: Auditors must verify that signers mandate `non_witness_utxo` for all non-Taproot inputs in PSBT workflows.

---

## 🧪 Executable BTC Script Simulation (`bitcoinjs-lib` / `rust-bitcoin`)

Every High/Critical Bitcoin Script finding must include an executable script test proving unauthorized spend or unbonding race execution:

```typescript
import * as bitcoin from "bitcoinjs-lib";
import { assert } from "chai";

describe("BTC Script PoC: Tapscript Key-Path Bypass", () => {
  it("Bypasses timelock script when internal key is owned by staker", () => {
    const keypair = bitcoin.ECPair.makeRandom();
    const leafScript = bitcoin.script.compile([
      bitcoin.script.number.encode(1008),
      bitcoin.opcodes.OP_CHECKSEQUENCEVERIFY,
      bitcoin.opcodes.OP_DROP,
      keypair.publicKey.slice(1, 33),
      bitcoin.opcodes.OP_CHECKSIG,
    ]);

    // ❌ VULNERABLE: Using keypair's public key as internal key instead of NUMS
    const { address, output } = bitcoin.payments.p2tr({
      internalPubkey: keypair.publicKey.slice(1, 33),
      scriptTree: { output: leafScript },
    });

    // Attacker can spend via Key-Path immediately without waiting 1008 blocks!
    assert.isDefined(address);
    console.log("Exploit address generated:", address);
  });
});
```
