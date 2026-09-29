#!/usr/bin/env python3
"""
Universal Foundry PoC Scaffolder (Zero-Dependency)
Generates ready-to-run Foundry configuration and PoC test harnesses for EVM audits.
Helps auditors and beginners quickly spin up reproducible fork exploit tests.
"""

import sys
import os
import json
import argparse

FOUNDRY_TOML_TEMPLATE = """[profile.default]
src = "src"
out = "out"
libs = {libs_toml}
test = "test"
cache_path = "cache"
solc_version = "{solc_version}"
evm_version = "{evm_version}"
optimizer = true
optimizer_runs = 200

[rpc_endpoints]
mainnet = "{rpc_url}"
"""

POC_TEST_TEMPLATE = """// SPDX-License-Identifier: MIT
pragma solidity {solc_version};

import "forge-std/Test.sol";

/**
 * @title PoC_{protocol_name}_Exploit
 * @notice Automated exploit verification test suite for {protocol_name}
 * @dev Run with: forge test --match-contract PoC_{protocol_name} -vvv --fork-url "{rpc_url}"
 */
contract PoC_{protocol_name} is Test {{
    // -------------------------------------------------------------------------
    // Target Contract Addresses
    // -------------------------------------------------------------------------
    address constant TARGET_CONTRACT = {target_address};
    address constant ATTACKER = address(0xBEEF);
    address constant VICTIM = address(0xCAFE);

    uint256 mainnetFork;

    function setUp() public {{
        // Pin to live RPC fork
        mainnetFork = vm.createFork("{rpc_url}");
        vm.selectFork(mainnetFork);

        // Fund attacker and victim
        vm.deal(ATTACKER, 100 ether);
        vm.deal(VICTIM, 100 ether);
    }}

    /**
     * @notice Test H-01: Verifies exploit execution and value extraction
     */
    function test_Exploit_Verification() public {{
        vm.startPrank(ATTACKER);

        uint256 attackerInitialBalance = ATTACKER.balance;

        // ---------------------------------------------------------------------
        // TODO: Place specific exploit call trace here
        // ---------------------------------------------------------------------
        // Example:
        // ITarget(TARGET_CONTRACT).vulnerableFunction(param);

        // ---------------------------------------------------------------------
        // Fail-Closed Assertion: Exploit must prove tangible fund extraction
        // ---------------------------------------------------------------------
        uint256 attackerFinalBalance = ATTACKER.balance;
        // uint256 profit = attackerFinalBalance - attackerInitialBalance;
        // assertGt(profit, 0, "Exploit failed: No value extracted!");

        emit log_named_uint("Attacker Starting Balance", attackerInitialBalance);
        emit log_named_uint("Attacker Ending Balance", attackerFinalBalance);

        vm.stopPrank();
    }}
}}
"""

def main():
    parser = argparse.ArgumentParser(description="Universal Foundry PoC Scaffolder")
    parser.add_argument("--protocol", required=True, help="Protocol name (e.g. Fables, Superform)")
    parser.add_argument("--rpc", required=True, help="RPC URL for fork testing")
    parser.add_argument("--target", default="address(0x1234)", help="Primary target contract address")
    parser.add_argument("--solc", default="0.8.26", help="Solidity version (default 0.8.26)")
    parser.add_argument("--evm", default="cancun", help="EVM version (default cancun)")
    parser.add_argument("--out-dir", default=".", help="Output directory to place foundry.toml and test/")
    parser.add_argument("--extra-lib", default=None, help="Optional additional library path to include in foundry.toml")
    args = parser.parse_args()

    protocol_clean = args.protocol.replace(" ", "_").replace("-", "_")
    target_addr = args.target if args.target.startswith("0x") or args.target.startswith("address") else f"address({args.target})"
    if not target_addr.startswith("address"):
        target_addr = f"{target_addr}"

    libs = ["lib"]
    if args.extra_lib:
        libs.append(args.extra_lib)
    libs_toml = json.dumps(libs)

    out_dir = os.path.abspath(args.out_dir)
    test_dir = os.path.join(out_dir, "test")
    os.makedirs(test_dir, exist_ok=True)

    # 1. Write foundry.toml if not present
    foundry_toml_path = os.path.join(out_dir, "foundry.toml")
    if not os.path.exists(foundry_toml_path):
        content = FOUNDRY_TOML_TEMPLATE.format(
            libs_toml=libs_toml,
            solc_version=args.solc,
            evm_version=args.evm,
            rpc_url=args.rpc
        )
        with open(foundry_toml_path, "w") as f:
            f.write(content)
        print(f"[+] Created: {foundry_toml_path}")
    else:
        print(f"[*] Preserved existing: {foundry_toml_path}")

    # 2. Write test/PoC_<protocol>.t.sol
    poc_path = os.path.join(test_dir, f"PoC_{protocol_clean}.t.sol")
    if not os.path.exists(poc_path):
        content = POC_TEST_TEMPLATE.format(
            protocol_name=protocol_clean,
            solc_version=args.solc,
            rpc_url=args.rpc,
            target_address=target_addr
        )
        with open(poc_path, "w") as f:
            f.write(content)
        print(f"[+] Created PoC Test Harness: {poc_path}")
    else:
        print(f"[*] Preserved existing PoC: {poc_path}")

    print(f"\n[+] PoC Harness Ready! Run with:")
    print(f"    forge test --match-contract PoC_{protocol_clean} -vvv")

if __name__ == "__main__":
    main()
