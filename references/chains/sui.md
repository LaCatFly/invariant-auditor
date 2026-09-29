# Sui Move Smart Contract Audit Playbook

Comprehensive security auditing manual for Move smart contracts on the Sui network.

---

## 🎯 Target Toolchain & Verification Framework

- **Core CLI**: `sui client`, `sui move test`, `sui move build`
- **Formal Verification & Provers**: Move Prover for Sui, Sui Object Security Linter
- **Testing Framework**: `sui::test_scenario`, `sui::test_utils`

---

## 🔍 Core Sui Move Vulnerability Archetypes

### 1. Hot Potato Invariant Enforcement & Evasion

#### The Pattern
In Move, a "Hot Potato" is a struct with **no abilities** (`has key`, `has store`, `has copy`, `has drop`). Because it cannot be dropped, stored in an object, or copied, it **must** be unpacked and consumed within the exact same Programmable Transaction Block (PTB).

#### Vulnerable Implementation
A protocol issues a flash-loan receipt without properly validating repayment or fees:
```move
// ❌ VULNERABLE: Receipt can be consumed with inadequate repayment or by wrong vault
module protocol::vault {
    use sui::coin::{Self, Coin};
    use sui::balance::{Self, Balance};
    use sui::tx_context::{TxContext};

    struct FlashReceipt {
        borrowed_amount: u64,
        vault_id: ID,
    }

    public fun flash_borrow<T>(vault: &mut Vault<T>, amount: u64, ctx: &mut TxContext): (Coin<T>, FlashReceipt) {
        let coin = coin::take(&mut vault.balance, amount, ctx);
        let receipt = FlashReceipt { borrowed_amount: amount, vault_id: object::id(vault) };
        (coin, receipt)
    }

    // BUG: Missing fee check! Or allows any vault to consume the receipt!
    public fun repay<T>(vault: &mut Vault<T>, payment: Coin<T>, receipt: FlashReceipt) {
        let FlashReceipt { borrowed_amount: _, vault_id } = receipt;
        assert!(object::id(vault) == vault_id, 0);
        // BUG: Does not verify coin::value(&payment) >= borrowed_amount + fee!
        coin::put(&mut vault.balance, payment);
    }
}
```

#### Secure Implementation
Strictly assert exact repayment amount plus protocol fees, and bind the receipt to the immutable vault ID:
```move
// ✅ SECURE: Strict balance assertion before destroying the hot potato
public fun repay<T>(
    vault: &mut Vault<T>,
    payment: Coin<T>,
    receipt: FlashReceipt
) {
    let FlashReceipt { borrowed_amount, vault_id } = receipt;
    assert!(object::id(vault) == vault_id, EWrongVault);
    
    let required_repayment = borrowed_amount + calculate_fee(borrowed_amount);
    assert!(coin::value(&payment) >= required_repayment, EInsufficientRepayment);
    
    coin::put(&mut vault.balance, payment);
}
```

---

### 2. Administrative Capability Leaking & Unsafe Object Wrapping

#### Vulnerability Mechanics
Move uses explicit "Capability Objects" (e.g. `AdminCap`, `TreasuryCap`) to gate privileged actions.
- **Leak Vector 1**: Calling `transfer::public_share_object(AdminCap)` makes administrative controls publicly callable by any transaction in the network.
- **Leak Vector 2**: Storing an `AdminCap` inside a dynamic field of a shared object where public getter functions return `&mut AdminCap`.

#### Secure Capability Distribution in `init`
```move
module protocol::governance {
    use sui::object::{Self, UID};
    use sui::tx_context::{Self, TxContext};
    use sui::transfer;

    struct AdminCap has key, store { id: UID }

    // ✅ SECURE: Capability transferred strictly to deployer EOA, NEVER shared
    fun init(ctx: &mut TxContext) {
        let admin_cap = AdminCap { id: object::new(ctx) };
        transfer::transfer(admin_cap, tx_context::sender(ctx));
    }
}
```

---

### 3. Dynamic Field Hijacking & Arbitrary Object Borrowing

#### Vulnerability Mechanics
Sui allows dynamic fields to be attached to any object with `key` via `sui::dynamic_field` or `sui::dynamic_object_field`.
If an endpoint exposes `borrow_mut` or `add` on child fields without enforcing caller ownership of the parent object, an attacker can overwrite internal accounting states or withdraw child tokens.

```move
// ❌ VULNERABLE: Any caller can remove or mutate dynamic child assets
public fun withdraw_child_asset<T: key + store>(
    parent: &mut ProtocolVault,
    field_name: vector<u8>,
    ctx: &mut TxContext
): T {
    // Missing permission/capability check on parent vault!
    dynamic_object_field::remove(&mut parent.id, field_name)
}

// ✅ SECURE: Gated by explicit AdminCap or owner proof
public fun withdraw_child_asset<T: key + store>(
    _admin: &AdminCap,
    parent: &mut ProtocolVault,
    field_name: vector<u8>,
    ctx: &mut TxContext
): T {
    dynamic_object_field::remove(&mut parent.id, field_name)
}
```

---

### 4. Coin vs Balance Semantics & Zero-Coin Splitting Griefing

- `Coin<T>` has `key, store` and represents an address-owned digital asset.
- `Balance<T>` has `store` and represents internal fungible accounting inside a contract struct.
- **Dust & Zero-Coin Spanning**: In Sui, `coin::zero<T>(ctx)` creates a brand new object with 0 value. Protocols that create `Coin` objects for dust payouts waste gas and create un-indexable object clutter.
- **Precision Truncation**: Enforce that multiplication precedes division when calculating fees:
  `let fee = (amount * fee_basis_points) / 10000;`

---

### 5. Package Upgrades & Immutable Shared Object Integrity

Sui allows package upgrades governed by `UpgradeCap`.
- **Policy Levels**:
  - `additive`: Can only add new structs and functions (cannot alter existing function bodies or struct memory layouts).
  - `dep_only`: Only dependencies can be updated.
  - `immutable`: `UpgradeCap` is destroyed; code is permanently frozen.
- **Audit Rule**: Ensure existing shared object schemas are never broken or rendered un-deserializable by upgraded packages.

---

## 🧪 Executable PoC Verification Harness (`test_scenario`)

Every High/Critical finding in Sui Move must be validated via an executable `sui move test`:

```move
#[test_only]
module protocol::exploit_poc {
    use sui::test_scenario::{Self as ts, Scenario};
    use sui::coin::{Self};
    use sui::sui::SUI;
    use protocol::vault::{Self, Vault};

    #[test]
    fun test_drain_vault_via_missing_fee_check() {
        let admin = @0xAD;
        let attacker = @0xBAD;

        let scenario_val = ts::begin(admin);
        let scenario = &mut scenario_val;

        // 1. Setup vault with 1,000,000 SUI
        ts::next_tx(scenario, admin);
        {
            vault::initialize_vault<SUI>(ts::ctx(scenario));
        };

        // 2. Attacker executes flash-loan without repaying fee
        ts::next_tx(scenario, attacker);
        {
            let mut vault_obj = ts::take_shared<Vault<SUI>>(scenario);
            let (borrowed_coin, receipt) = vault::flash_borrow(&mut vault_obj, 1000000, ts::ctx(scenario));
            
            // Attacker repays ONLY principal, evading 5% protocol fee
            vault::repay(&mut vault_obj, borrowed_coin, receipt);
            
            ts::return_shared(vault_obj);
        };

        ts::end(scenario_val);
    }
}
```
