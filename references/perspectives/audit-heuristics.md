# Smart Contract Audit Heuristics & Verification Gaps

Operational manual for identifying subtle codebase gaps, handling tooling limitations, and enforcing formal verification hygiene.

---

## 🏛️ Core Verification Principles

1. **Context Window Hygiene (File-Based Persistence)**: LLM agents suffer cognitive degradation when flooded with raw source code across large repositories. Persist intermediate function analysis into external disk files (`audit-context/functions/`, `results/`) and only pass compact summaries back into working context.
2. **Deterministic Tool Grounding**: Pair LLM heuristic reasoning with hardened static and dynamic tools (Slither, Aderyn, Foundry, Cast, Echidna, Medusa).
3. **Fail-Closed Verification Gates**: Suspected vulnerabilities must pass strict multi-phase gates (taint tracking, mathematical bounds proof, executable PoC) before being classified as True Positives. Unverified theories must never be labeled High or Critical.

---

## ⚠️ Known Gaps in Standard Workflows

Auditors and automated engines must actively compensate for 3 structural limitations:

### 1. The "View-Function Discard" Blindspot (Read-Only Reentrancy & Oracle Poisoning)
* **The Blindspot**: Automated scanners frequently filter out `view` and `pure` functions under the assumption that read-only calls cannot directly mutate contract state.
* **Compensating Action**: In DeFi lending and vault architectures, auditors must explicitly trace all public `view` pricing functions (e.g. `get_virtual_price()`, `calculateSharePrice()`, `balanceOf()`). These represent primary targets for **Read-Only Reentrancy** and oracle pricing corruption during transient reentrancy windows.

### 2. Isolated-Function vs. Cross-Protocol MEV Trajectory
* **The Blindspot**: Static tools analyze functions in isolation and fail to model multi-contract atomic transactions.
* **Compensating Action**: Multi-step economic exploits span multiple protocols (flashloan $\to$ preconditioning $\to$ trigger $\to$ extraction). Auditors must synthesize a cross-contract **State-Mutation Graph** rather than evaluating individual function assumptions in isolation.

### 3. Tooling Compilation Fragility
* **The Blindspot**: Heavy reliance on static analyzers halts if compiler versions, `via-ir` configurations, or Cancun transient storage opcodes cause AST parser failures.
* **Compensating Action**: Maintain AST-less regex, raw opcode scanning, and manual state-variable diffing fallbacks when automated static analysis fails to compile.

---

## ⚡ 5 Ways to Rapidly Identify Codebase Gaps

1. **Read-Write Storage Asymmetry (Mutation Differential)**:
   - Map state variables to functions that Read ($R$) vs Write ($W$). Identify variables updated in multiple execution paths where only some paths enforce boundary checks or access controls.
2. **Unvalidated Parameter Surface (Zero & Bounds Check Sweep)**:
   - Check all public/external entry points for missing zero-amount, zero-address, dynamic array length equality, and unconstrained slippage (`minAmountOut == 0`) parameters.
3. **Internal Accounting vs. Raw Balance Discrepancy**:
   - Compare `token.balanceOf(address(this))` against internal ledger tracking (`trackedReserve`). Pinpoint donation inflation vulnerabilities (ERC-4626 vault inflation) and locked yield/airdrop vectors.
4. **CEI & External Call Sequencing Graph**:
   - Grep for low-level calls (`.call{value:}`) and token transfers. Verify whether state updates occur after external invocations or if un-guarded callbacks invoke user-controlled addresses.
5. **Privileged Invariant & Emergency Asymmetry**:
   - Audit `pause()` and `emergencyWithdraw()`. Verify that pause controls do not indefinitely freeze user principal, and that emergency withdrawals cannot bypass debt repayment or exit penalties.
