# CLAUDE.md — Invariant Auditor Master Guidelines

Guidance for Claude Code (`claude.ai/code`) when working in this repository or executing smart contract security audits using Invariant Auditor.

---

## 🏛️ Repository Architecture

This repository hosts **Invariant Auditor**, an institutional multi-chain smart contract security audit engine designed for EVM, Solana, Sui, and bespoke architectures.

```
invariant-auditor/
├── CLAUDE.md                    # This master directive for Claude Code
├── SKILL.md                     # Flagship master skill (self-contained, 8-session lifecycle)
├── install.sh                   # Universal multi-agent installer (Claude Code, Antigravity, Workspace)
├── scripts/                     # Bundled master executable toolsuite
│   ├── audit_inspector.py       # Live RPC slot archaeology, storage layout & hook bitmask
│   ├── audit_tracer.py          # Deployer genesis tracing, AML scoring & exploit trace decoder
│   ├── liquidity_run_sim.py     # Lens 1: Bank run cash shock & liquidity drain simulator
│   ├── symbolic_sensitivity.py  # Lens 3: SymPy Jacobian & zero-denominator sensitivity calculus
│   └── generate_poc_scaffold.py # Automated Foundry fork PoC test scaffold generator
├── test/                        # Test suite & CI validation
│   └── check_portability.py     # Portability & self-containment test harness
├── references/                  # Multi-chain & perspective reference manuals
│   ├── evm.md, solana.md, sui.md, btc.md
│   ├── allocator-perspective.md # Perspective B criteria, AML gates & kill-switches
│   └── audit-heuristics.md     # Rapid gap identification & CEI sequencing
├── recon-triage/                # Satellite sub-skill: Slot archaeology & Slither triage
├── transaction-tracer/          # Satellite sub-skill: Deployer genesis & exploit traces
├── boundary-sensitivity/        # Satellite sub-skill: 5 Boundary diagnostic math lenses
└── poc-engine/                  # Satellite sub-skill: Fail-closed fork PoCs & surgical diffs
```

### Self-Contained Master vs. Satellite Modules
- **Master Flagship (`invariant-auditor`)**: Fully self-contained. Bundles all 5 executable analysis scripts in `scripts/`. Runs the complete 8-session audit lifecycle end-to-end without requiring satellite directory structures.
- **Satellite Sub-Skills (`recon-triage`, `transaction-tracer`, etc.)**: Standalone point tools for focused modular workflows or external distribution.

---

## 🚫 Critical Scope Boundaries (STRICT RULES)

1. **Security Audit ONLY**: Never write deployment scripts (`Deploy.s.sol`), debug deployment simulations, or attempt transaction broadcasts. Auditing evaluates security, not client deployment engineering.
2. **No Speculative Bytecode Reversing**: If source code is missing or unverified, flag it immediately as a Gate 1 blocker rather than spending hours guessing raw bytecode decompilations.
3. **Fail-Closed PoC Iron Rule**: Findings without executable balance extraction receipts CANNOT be classified as Critical or High. Unproven findings are theories, not vulnerabilities.
4. **Single Living `WORKSPACE.md`**: Maintain a single living `output/<protocol-slug>/WORKSPACE.md` during analysis instead of scattering state across multiple scratch files.
5. **Deterministic Deliverables**: All audit outputs are deposited into `output/<protocol-slug>/` using standardized skill prefixes (`00_IA_`, `01_RT_`, `03_TT_`, `04_BS_`, `05_IA_`, `06_PE_`, `07_TT_`, `08_PE_`).

---

## ⚡ Quick Commands & Tool Execution

Claude Code can execute all bundled tools directly via bash:

```bash
# 1. On-Chain Recon (Slot Archaeology, EIP-1967/UUPS Proxy Resolution & Hook Bitmasks)
python3 scripts/audit_inspector.py --rpc $RPC_URL --address <TARGET_CONTRACT>

# 2. Deployer Genesis Forensics & Rug Radar (Milestone 1.5)
python3 scripts/audit_tracer.py <TARGET_CONTRACT_OR_DEPLOYER> --chain <CHAIN> --output output/<PROTOCOL>/03_TT_FORENSIC_REPORT.md

# 3. Static Analysis Scanner 100% Triage
slither . --json slither.json
cat slither.json | jq '.results.detectors[] | select(.impact == "High" or .impact == "Medium")' > triage.json

# 4. Liquidity Shock & Bank Run Simulation (Milestone 2.5 Lens 1)
python3 scripts/liquidity_run_sim.py --liabilities 50000000 --cash 5000000 --shock 0.25 --hours 48

# 5. Closed-Form Symbolic Calculus (Milestone 2.5 Lens 3)
python3 scripts/symbolic_sensitivity.py --formula "(collateral * p_o) / (debt * (1 - penalty))" --vars p_o debt

# 6. Instant Foundry Fork PoC Scaffold Generation
python3 scripts/generate_poc_scaffold.py --protocol <PROTOCOL> --rpc $RPC_URL --target <ADDRESS>

# 7. Execute Foundry Fork Exploit Test
forge test --match-contract PoC -vvv

# 8. Suite Portability & Health Check
python3 test/check_portability.py
```

---

## 🛡️ The 8 Master Sessions & 6 Accuracy Gates

| Session / Milestone | Primary Tool / Script | Deliverable | Accuracy Gate |
|---|---|---|---|
| **Session 1: Ingestion & Routing** | Input Block / `cast code` | `WORKSPACE.md` | Gate 1: Ingestion & Track Partitioning |
| **Session 2: Storage Slot Archaeology** | `scripts/audit_inspector.py` | `01_RT_CONTRACTS.md`, `01_RT_ON_CHAIN_VERIFICATION.md` | Gate 1: Live RPC Verification |
| **🏁 M1.5: Deployer Genesis Forensics** | `scripts/audit_tracer.py` | `03_TT_FORENSIC_REPORT.md` (AML 0–100) | **Pre-Audit Kill Switch (AML ≥ 80)** |
| **Session 3: 100% Scanner Triage** | Slither / Aderyn + `jq` | `02_RT_SLITHER_TRIAGE.md`, `02_RT_AUDIT_PLAN.md` | Gate 2: Scanner Triage & Assumptions Matrix |
| **🏁 M2.5: 5 Boundary Lenses** | `liquidity_run_sim.py`, `symbolic_sensitivity.py` | `04_BS_BOUNDARY_SENSITIVITY.md`, `04_BS_ALLOCATOR_CAPACITY.md` | Gate 3: Economic Boundary Stress |
| **Session 5: 5 Attacker Personas** | Threat Modeling Engine | `05_IA_THREAT_MODEL.md`, `05_IA_DIAGRAMS.md` | Gate 3: Track Decomposition & Adversary Personas |
| **Session 6: Fail-Closed Fork PoC** | `scripts/generate_poc_scaffold.py` + `forge test` | `test/06_PE_PoC_<PROTOCOL>.t.sol` | Gate 4: Executable PoC Verification (IRON RULE) |
| **🏁 M4.5: Exploit Trace Reconstruction** | `scripts/audit_tracer.py` | `07_TT_EXPLOIT_TRACE.md` | Gate 4: Adversarial Trace Mapping |
| **Session 7: Surgical Remediation Diff** | `git apply patch.diff` + `forge test` | `08_PE_patch.diff`, `08_PE_VERIFICATION_RECEIPT.md` | Gate 5: Remediation & Regression Test |
| **Session 8: Tri-Perspective Delivery** | Report & HTML Generator | `00_IA_AUDIT_REPORT.md`, `00_IA_EXECUTIVE_CONVICTION.md`, `00_IA_PRESENTATION.html` | Gate 6: Tri-Perspective Institutional Delivery |

---

## 🎯 Claude Code Audit Execution Flow

When conducting an audit in Claude Code:
1. **Initialize Workspace**: Create `output/<protocol-slug>/` and set up `WORKSPACE.md`.
2. **Execute On-Chain Recon**: Run `python3 scripts/audit_inspector.py` to verify proxy targets and read live slots.
3. **Execute Rug Radar**: Run `python3 scripts/audit_tracer.py`. Check the AML risk score.
   - If score $\ge 80$: trigger immediate pre-audit warning.
4. **Formulate Invariant Model**: Decompose target into PAI dimensions (Reservoir, Inflow, Outflow, Valuation Oracle).
5. **Stress Test Boundaries**: Run `liquidity_run_sim.py` and `symbolic_sensitivity.py` for mathematical and liquidity friction boundaries.
6. **Construct PoC Exploit**: Write and run a concrete Foundry fork test (`assertGt(extractedProfit, 0)`). Never claim High/Critical without this pass.
7. **Write Minimal Patch**: Provide a 5–15 line diff and verify the exploit fails while baseline tests pass.
8. **Deliver Final Artifacts**: Produce the Developer Audit Report, Allocator Conviction Sheet, Exploit Trace, and Interactive HTML Presentation.

---

## 📦 Installation for Claude Code

To install Invariant Auditor as a global Claude Code skill:
```bash
./install.sh --agent claude
```
This places the self-contained suite into `~/.claude/skills/invariant-auditor/` with all scripts executable and references linked.
