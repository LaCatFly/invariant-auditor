# Solana Anchor Smart Contract Audit Playbook

Comprehensive security auditing manual for Solana programs built with the Anchor framework and native Solana SDK.

---

## 🎯 Target Toolchain & Environment

- **Core Frameworks**: Anchor 0.30+, Solana CLI (`solana-test-validator`), Rust 1.75+
- **Fuzzing & Formal Verification**: Trident Fuzzing Framework, Soteria, Cargo-audit
- **Unit & Integration Harness**: `anchor test`, `solana-program-test`, `solana-bankrun`

---

## 🔍 Core Solana Vulnerability Archetypes

### 1. Missing Signer & Ownership Verification

#### Vulnerable Pattern
Raw `AccountInfo<'info>` does not verify that the account signed the transaction or is owned by the expected program:
```rust
// ❌ VULNERABLE: Unchecked AccountInfo allows attacker to pass arbitrary fake accounts
pub fn withdraw(ctx: Context<Withdraw>, amount: u64) -> Result<()> {
    let vault = &ctx.accounts.vault; // AccountInfo<'info>
    let authority = &ctx.accounts.authority; // AccountInfo<'info>
    
    // Attacker can pass any authority without signing, or a fake vault owned by malicious program
    **vault.try_borrow_mut_lamports()? -= amount;
    **authority.try_borrow_mut_lamports()? += amount;
    Ok(())
}
```

#### Secure Anchor Pattern
Enforce `Signer<'info>` for authorization and typed `Account<'info, Vault>` for program ownership and discriminator validation:
```rust
// ✅ SECURE: Anchor automatically validates owner == program_id, 8-byte discriminator, and is_signer
#[derive(Accounts)]
pub struct Withdraw<'info> {
    #[account(
        mut,
        has_one = authority,
        seeds = [b"vault", authority.key().as_ref()],
        bump = vault.bump
    )]
    pub vault: Account<'info, VaultAccount>,
    
    pub authority: Signer<'info>,
    
    #[account(mut)]
    pub destination: SystemAccount<'info>,
}
```

---

### 2. PDA Canonical Bump & Seed Derivation Collisions

#### Vulnerability Mechanics
- Using `Pubkey::create_program_address` with unvalidated bumps allows non-canonical bumps, enabling multiple addresses to represent the same logical entity.
- Arbitrary variable-length seeds (e.g. `[user_input.as_bytes()]`) without fixed delimiters allow seed collisions (e.g. `"ab"` + `"c"` vs `"a"` + `"bc"`).

#### Audit Checklist
1. Always store `bump: u8` in the account state upon initialization.
2. In instruction validation macros, strictly assert `bump = vault.bump`.
3. Do **not** use `ctx.bumps.vault` in operations after initialization if the bump is already stored in state.

```rust
#[account(
    mut,
    seeds = [b"user_vault", authority.key().as_ref(), mint.key().as_ref()],
    bump = user_vault.bump // Enforce stored canonical bump
)]
pub user_vault: Account<'info, UserVault>,
```

---

### 3. Account Closing & Lamport Drain Resurrection Attacks

#### Vulnerability Mechanics
Closing an account by simply zeroing lamports without reassigning owner to `SystemProgram` and wiping memory leaves the account vulnerable. In the same transaction (or later in the slot), an attacker can transfer lamports to the account, reviving it with its stale data still intact.

#### Secure Anchor Account Closing Pattern
Anchor's `close = <target>` constraint performs the complete safe closure sequence:
1. Transfers all lamports to destination.
2. Sets account data to 8-byte closed account discriminator (`[255, 255, 255, 255, 255, 255, 255, 255]`).
3. Zeros out remaining memory.

```rust
#[derive(Accounts)]
pub struct CloseVault<'info> {
    #[account(
        mut,
        close = recipient, // Safely zeros data, sets discriminator, transfers lamports
        has_one = authority,
        seeds = [b"vault", authority.key().as_ref()],
        bump = vault.bump
    )]
    pub vault: Account<'info, VaultAccount>,
    pub authority: Signer<'info>,
    #[account(mut)]
    pub recipient: SystemAccount<'info>,
}
```

---

### 4. CPI Reentrancy & Stale Account Cache Invalidation

#### Vulnerability Mechanics
Solana does not have an EVM-style call stack, but Cross-Program Invocations (CPIs) invoke external programs. If an external program calls back into the caller, or mutates an account shared with the caller, Anchor's in-memory deserialized account state becomes **stale**.

```rust
// ❌ VULNERABLE: State mutation after external CPI with stale in-memory struct
pub fn execute_flash_loan(ctx: Context<FlashLoan>, amount: u64) -> Result<()> {
    let balance_before = ctx.accounts.vault.balance;
    
    // External CPI to untrusted recipient
    invoke(
        &transfer_ix,
        &[ctx.accounts.vault.to_account_info(), ctx.accounts.recipient.to_account_info()]
    )?;
    
    // BUG: ctx.accounts.vault state here does not reflect mutations that occurred during CPI!
    // Must call ctx.accounts.vault.reload()? to sync from account memory buffer
    ctx.accounts.vault.reload()?;
    require!(ctx.accounts.vault.balance >= balance_before + fee, ErrorCode::RepaymentFailed);
    Ok(())
}
```

---

### 5. Type Cosplay & 8-Byte Discriminator Collisions

#### Vulnerability Mechanics
Anchor prepends an 8-byte discriminator to all account data: `sha256("account:<StructName>")[..8]`.
If an instruction deserializes accounts with `UncheckedAccount` or `AccountInfo` and manually parses data without checking this discriminator, an attacker can pass an account with an identical memory layout (e.g. `UserAccount` vs `AdminAccount`).

```rust
// ❌ VULNERABLE: Deserializing without discriminator check
let user_data: UserAccount = UserAccount::try_from_slice(&ctx.accounts.raw_account.data.borrow())?;

// ✅ SECURE: Use typed Anchor wrapper
pub raw_account: Account<'info, UserAccount>,
```

---

### 6. Remaining Accounts & Duplicate Account Confusion

When instructions iterate over `ctx.remaining_accounts`, they must ensure that:
1. No duplicate accounts are supplied (e.g. passing the same token account as both `source` and `destination` in a multi-token swap).
2. The account owner is strictly checked for every account in the loop.

```rust
let mut seen_keys = std::collections::BTreeSet::new();
for acc in ctx.remaining_accounts.iter() {
    require!(seen_keys.insert(acc.key()), ErrorCode::DuplicateAccount);
    require_keys_eq!(*acc.owner, token::ID, ErrorCode::InvalidOwner);
}
```

---

## 🧪 Executable PoC Verification Harness (`anchor test` / Bankrun)

Every High or Critical Solana finding requires an executable PoC using `anchor test` or `solana-bankrun`:

```typescript
import * as anchor from "@coral-xyz/anchor";
import { Program } from "@coral-xyz/anchor";
import { assert } from "chai";
import { startAnchor } from "solana-bankrun";

describe("Solana PoC: Lamport Extraction via Missing Signer", () => {
  it("Exploits unvalidated authority to drain vault", async () => {
    const context = await startAnchor(".", [], []);
    const provider = new anchor.BankrunProvider(context);
    const program = new Program(IDL, programId, provider);

    const attacker = anchor.web3.Keypair.generate();
    const victimVault = anchor.web3.Keypair.generate();

    const vaultBalanceBefore = await provider.connection.getBalance(victimVault.publicKey);

    // Attacker invokes withdraw without victim signing
    await program.methods
      .withdraw(new anchor.BN(10_000_000_000))
      .accounts({
        vault: victimVault.publicKey,
        authority: attacker.publicKey, // Rogue authority
        destination: attacker.publicKey,
      })
      .signers([attacker])
      .rpc();

    const vaultBalanceAfter = await provider.connection.getBalance(victimVault.publicKey);
    assert.isBelow(vaultBalanceAfter, vaultBalanceBefore, "Vault was drained successfully");
  });
});
```
