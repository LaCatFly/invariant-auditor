#!/usr/bin/env python3
"""
================================================================================
Universal EVM Smart Contract Audit Inspector (Modular Enterprise Edition)
================================================================================
Standard: 6 Accuracy Gates | Trail of Bits Context | SlowMist On-Chain Verification
Zero external dependencies (Python 3.8+ standard library only).

Specialized Modular Subsystems:
  - Core: RPCClient, StorageSlotInspector, BytecodeAnalyzer
  - Module 1: Proxy & Implementation Archaeology (EIP-1967, UUPS, Beacon, Immutable Beacon, Diamond, Clones)
  - Module 2: Governance, Timelock & Privilege Radar (Admin keys, minDelay, two-step transfer)
  - Module 3: AMM & Liquidity Hooks (Uniswap v4 Hook bitmask, Uniswap v2/v3, Curve StableSwap)
  - Module 4: Tokenized Vaults & Yield (ERC-4626, share inflation, asset/share decimals)
  - Module 5: Token Integrity & Destructive Privileges (Rebasing uiMultiplier, adminBurn, blacklist)
  - Module 6: Lending & Money Markets (Compound/IronBank/Curvance cToken, Comptroller)
  - Module 7: Oracles & Price Feeds (Chainlink AggregatorV3 staleness, round completeness)
================================================================================
"""

import sys
import json
import time
import re
import argparse
import urllib.request
import urllib.error
from typing import Dict, Any, Optional, List, Tuple

# -----------------------------------------------------------------------------
# Standard Storage Slots & Selectors Registry
# -----------------------------------------------------------------------------

STORAGE_SLOTS = {
    "EIP_1967_IMPL": "0x360894a13ba1a3210667c828492db98dca3e2076cc3735a920a3ca505d382bbc",
    "EIP_1967_BEACON": "0xa3f0adfb68e35c6e0a6193ff75443ae9e10ce3e659f140f721a5645b30133c10",
    "EIP_1967_ADMIN": "0xb53127684a568b3173ae13b9f8a6016e243e63b6e8ee1178d6a717850b5d6103",
    "UUPS_PROXIABLE": "0xc5f1683af44ba74280299ca630f0d5f71f03fc6f1998b3718f6291ab460dc414"
}

SELECTORS = {
    # Governance & Ownership
    "owner": "0x8da5cb5b",
    "pendingOwner": "0xe30c3978",
    "admin": "0xf851a440",
    "pendingAdmin": "0x26782247",
    "getMinDelay": "0xf27a0c92",
    "paused": "0x5c975abb",
    # Tokens & Assets
    "name": "0x06fdde03",
    "symbol": "0x95d89b41",
    "decimals": "0x313ce567",
    "totalSupply": "0x18160ddd",
    "balanceOf": "0x70a08231",
    "uiMultiplier": "0xa60bf13d",
    "adminBurn": "0x06dd0419",
    "isBlocked": "0x24745215",
    # Vaults (ERC-4626)
    "asset": "0x38d52e0f",
    "totalAssets": "0x01e1d114",
    "convertToAssets": "0x07a2d13a",
    "convertToShares": "0xc6e6f592",
    # AMMs & Hooks
    "token0": "0x0dfe1681",
    "token1": "0xd21220a7",
    "fee": "0xddca3f43",
    "slot0": "0x3850c7bd",
    "getReserves": "0x0902f1ac",
    "get_virtual_price": "0xbb7b8b80",
    "beforeInitialize": "0xdc98354e",
    "beforeSwap": "0x575e24b4",
    # Lending & Money Markets
    "exchangeRateStored": "0x182df0f5",
    "comptroller": "0x5fe3b567",
    "totalBorrows": "0x47bd3718",
    "totalReserves": "0x8f840ddd",
    "reserveFactorMantissa": "0x173b9904",
    # Oracles (Chainlink AggregatorV3)
    "latestRoundData": "0xfeaf968c",
    # Diamond & Proxy Implementation
    "facets": "0x7a0ed627",
    "implementation": "0x5c60da1b"
}

UNISWAP_V4_HOOK_FLAGS = {
    "BEFORE_INITIALIZE": 1 << 13,
    "AFTER_INITIALIZE": 1 << 12,
    "BEFORE_ADD_LIQUIDITY": 1 << 11,
    "AFTER_ADD_LIQUIDITY": 1 << 10,
    "BEFORE_REMOVE_LIQUIDITY": 1 << 9,
    "AFTER_REMOVE_LIQUIDITY": 1 << 8,
    "BEFORE_SWAP": 1 << 7,
    "AFTER_SWAP": 1 << 6,
    "BEFORE_DONATE": 1 << 5,
    "AFTER_DONATE": 1 << 4,
    "BEFORE_SWAP_RETURNS_DELTA": 1 << 3,
    "AFTER_SWAP_RETURNS_DELTA": 1 << 2,
    "AFTER_ADD_LIQUIDITY_RETURNS_DELTA": 1 << 1,
    "AFTER_REMOVE_LIQUIDITY_RETURNS_DELTA": 1 << 0
}

# -----------------------------------------------------------------------------
# Core Engine: RPCClient
# -----------------------------------------------------------------------------

class RPCClient:
    """Robust JSON-RPC client with user-agent spoofing, timeouts, and batch support."""
    def __init__(self, rpc_url: str, timeout: int = 15):
        self.rpc_url = rpc_url
        self.timeout = timeout
        self.headers = {
            "Content-Type": "application/json",
            "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
        }

    def call(self, method: str, params: list) -> Optional[Any]:
        payload = {"jsonrpc": "2.0", "id": 1, "method": method, "params": params}
        req = urllib.request.Request(self.rpc_url, data=json.dumps(payload).encode("utf-8"), headers=self.headers)
        try:
            with urllib.request.urlopen(req, timeout=self.timeout) as resp:
                data = json.loads(resp.read().decode("utf-8"))
                if "error" in data:
                    return None
                return data.get("result")
        except Exception:
            return None

    def eth_call(self, to_address: str, data_hex: str) -> Optional[str]:
        res = self.call("eth_call", [{"to": to_address, "data": data_hex}, "latest"])
        if res and res != "0x" and len(res) > 2:
            return res
        return None

    def get_storage_at(self, address: str, slot_hex: str) -> Optional[str]:
        return self.call("eth_getStorageAt", [address, slot_hex, "latest"])

    def get_code(self, address: str) -> Optional[str]:
        return self.call("eth_getCode", [address, "latest"])

    def get_chain_id(self) -> Optional[int]:
        res = self.call("eth_chainId", [])
        if res:
            return int(res, 16)
        return None

# -----------------------------------------------------------------------------
# Core Data Decoders
# -----------------------------------------------------------------------------

def decode_address(raw_hex: Optional[str]) -> Optional[str]:
    if not raw_hex or raw_hex == "0x" or raw_hex == "0x" + "0" * 64:
        return None
    cleaned = raw_hex.replace("0x", "")
    if len(cleaned) < 40:
        return None
    addr = "0x" + cleaned[-40:].lower()
    if addr == "0x" + "0" * 40:
        return None
    return addr

def decode_uint256(raw_hex: Optional[str]) -> Optional[int]:
    if not raw_hex or raw_hex == "0x":
        return None
    try:
        return int(raw_hex, 16)
    except ValueError:
        return None

def decode_string(raw_hex: Optional[str]) -> Optional[str]:
    if not raw_hex or raw_hex == "0x" or len(raw_hex) < 130:
        return None
    try:
        data = bytes.fromhex(raw_hex[2:])
        offset = int.from_bytes(data[0:32], "big")
        length = int.from_bytes(data[offset:offset+32], "big")
        str_bytes = data[offset+32:offset+32+length]
        return str_bytes.decode("utf-8", errors="ignore").strip("\x00")
    except Exception:
        return None

def decode_bool(raw_hex: Optional[str]) -> Optional[bool]:
    val = decode_uint256(raw_hex)
    if val is not None:
        return val != 0
    return None

# -----------------------------------------------------------------------------
# Module 1: Proxy & Implementation Archaeology
# -----------------------------------------------------------------------------

class ProxyModule:
    """Deconstructs EIP-1967, UUPS, Minimal Clones, Beacon, and Diamond proxy topologies."""
    def __init__(self, rpc: RPCClient):
        self.rpc = rpc

    def inspect(self, address: str, bytecode: str) -> Dict[str, Any]:
        info: Dict[str, Any] = {
            "is_proxy": False,
            "proxy_type": "None",
            "implementation": None,
            "beacon": None,
            "admin": None,
            "diamond_facets_detected": False
        }

        # 1. EIP-1167 Minimal Clone check
        if bytecode.startswith("0x363d3d373d3d3d363d73") and len(bytecode) == 92:
            impl = "0x" + bytecode[22:62].lower()
            info["is_proxy"] = True
            info["proxy_type"] = "EIP-1167 Minimal Clone"
            info["implementation"] = impl
            return info

        # 2. Immutable BeaconProxy check (embedded beacon before 5c60da1b in bytecode)
        # Pattern: 7f000000000000000000000000<20-byte-beacon>...635c60da1b
        match = re.search(r"7f000000000000000000000000([0-9a-fA-F]{40}).*?635c60da1b", bytecode)
        if match:
            beacon_addr = "0x" + match.group(1).lower()
            info["is_proxy"] = True
            info["proxy_type"] = "Immutable BeaconProxy"
            info["beacon"] = beacon_addr
            # Resolve implementation from beacon
            beacon_impl_raw = self.rpc.eth_call(beacon_addr, SELECTORS["implementation"])
            beacon_impl = decode_address(beacon_impl_raw)
            if beacon_impl:
                info["implementation"] = beacon_impl
            return info

        # 3. EIP-1967 Implementation Slot
        impl_raw = self.rpc.get_storage_at(address, STORAGE_SLOTS["EIP_1967_IMPL"])
        impl = decode_address(impl_raw)
        if impl:
            info["is_proxy"] = True
            info["proxy_type"] = "EIP-1967 Transparent/Custom Proxy"
            info["implementation"] = impl

        # 4. UUPS Proxiable Slot
        uups_raw = self.rpc.get_storage_at(address, STORAGE_SLOTS["UUPS_PROXIABLE"])
        uups_impl = decode_address(uups_raw)
        if uups_impl:
            info["is_proxy"] = True
            info["proxy_type"] = "EIP-1822 / UUPS Proxy"
            info["implementation"] = uups_impl

        # 5. Beacon Slot
        beacon_raw = self.rpc.get_storage_at(address, STORAGE_SLOTS["EIP_1967_BEACON"])
        beacon = decode_address(beacon_raw)
        if beacon:
            info["is_proxy"] = True
            info["beacon"] = beacon
            if info["proxy_type"] == "None":
                info["proxy_type"] = "EIP-1967 BeaconProxy"
            beacon_impl_raw = self.rpc.eth_call(beacon, SELECTORS["implementation"])
            beacon_impl = decode_address(beacon_impl_raw)
            if beacon_impl:
                info["implementation"] = beacon_impl

        # 6. Admin Slot
        admin_raw = self.rpc.get_storage_at(address, STORAGE_SLOTS["EIP_1967_ADMIN"])
        admin = decode_address(admin_raw)
        if admin:
            info["admin"] = admin

        # 7. EIP-2535 Diamond Proxy Check
        facets_res = self.rpc.eth_call(address, SELECTORS["facets"])
        if facets_res and len(facets_res) > 130:
            info["is_proxy"] = True
            info["proxy_type"] = "EIP-2535 Diamond Proxy"
            info["diamond_facets_detected"] = True

        return info

# -----------------------------------------------------------------------------
# Module 2: Governance, Timelock & Privilege Radar
# -----------------------------------------------------------------------------

class GovernanceModule:
    """Maps administrative authority, timelocks, and pause powers."""
    def __init__(self, rpc: RPCClient):
        self.rpc = rpc

    def inspect(self, address: str) -> Dict[str, Any]:
        info: Dict[str, Any] = {}

        owner_raw = self.rpc.eth_call(address, SELECTORS["owner"])
        info["owner"] = decode_address(owner_raw)

        pending_owner_raw = self.rpc.eth_call(address, SELECTORS["pendingOwner"])
        info["pending_owner"] = decode_address(pending_owner_raw)

        admin_raw = self.rpc.eth_call(address, SELECTORS["admin"])
        info["admin"] = decode_address(admin_raw)

        pending_admin_raw = self.rpc.eth_call(address, SELECTORS["pendingAdmin"])
        info["pending_admin"] = decode_address(pending_admin_raw)

        min_delay_raw = self.rpc.eth_call(address, SELECTORS["getMinDelay"])
        min_delay = decode_uint256(min_delay_raw)
        if min_delay is not None:
            info["timelock_min_delay_seconds"] = min_delay
            info["timelock_min_delay_hours"] = round(min_delay / 3600, 2)
            info["is_timelock"] = True

        paused_raw = self.rpc.eth_call(address, SELECTORS["paused"])
        info["is_paused"] = decode_bool(paused_raw)

        return info

# -----------------------------------------------------------------------------
# Module 3: AMM & Liquidity Hooks
# -----------------------------------------------------------------------------

class AMMHookModule:
    """Decodes Uniswap v4 Hook bitmasks, evaluates non-custodial safety, and AMM pools."""
    def __init__(self, rpc: RPCClient):
        self.rpc = rpc

    def is_likely_v4_hook(self, address: str, bytecode: str, name: str) -> bool:
        """Determines if a contract is genuinely a Uniswap v4 Hook to avoid false positives on arbitrary addresses."""
        if "hook" in name.lower():
            return True
        # Check if bytecode has Uniswap v4 hook signatures
        if "575e24b4" in bytecode or "dc98354e" in bytecode:
            return True
        return False

    def decode_hook_bitmask(self, address: str) -> Dict[str, Any]:
        try:
            addr_int = int(address, 16)
        except ValueError:
            return {}
        flags_val = addr_int & 0x3FFF  # Lowest 14 bits
        permissions = {}
        for name, mask in UNISWAP_V4_HOOK_FLAGS.items():
            permissions[name] = (flags_val & mask) != 0

        can_intercept_liquidity = any(permissions[f] for f in [
            "BEFORE_ADD_LIQUIDITY", "AFTER_ADD_LIQUIDITY",
            "BEFORE_REMOVE_LIQUIDITY", "AFTER_REMOVE_LIQUIDITY"
        ])
        can_return_deltas = any(permissions[f] for f in [
            "BEFORE_SWAP_RETURNS_DELTA", "AFTER_SWAP_RETURNS_DELTA",
            "AFTER_ADD_LIQUIDITY_RETURNS_DELTA", "AFTER_REMOVE_LIQUIDITY_RETURNS_DELTA"
        ])
        is_non_custodial = not (can_intercept_liquidity or can_return_deltas)

        return {
            "flags_hex": hex(flags_val),
            "flags_bin": bin(flags_val),
            "permissions": permissions,
            "can_intercept_liquidity": can_intercept_liquidity,
            "can_return_deltas": can_return_deltas,
            "is_non_custodial": is_non_custodial
        }

    def inspect_amm(self, address: str) -> Dict[str, Any]:
        info: Dict[str, Any] = {}
        t0 = decode_address(self.rpc.eth_call(address, SELECTORS["token0"]))
        t1 = decode_address(self.rpc.eth_call(address, SELECTORS["token1"]))
        if t0 and t1:
            info["token0"] = t0
            info["token1"] = t1
            fee_raw = self.rpc.eth_call(address, SELECTORS["fee"])
            info["fee_bps"] = decode_uint256(fee_raw)
            info["is_amm_pool"] = True

        vp_raw = self.rpc.eth_call(address, SELECTORS["get_virtual_price"])
        vp = decode_uint256(vp_raw)
        if vp is not None:
            info["curve_virtual_price"] = vp / 1e18
            info["is_curve_pool"] = True

        return info

# -----------------------------------------------------------------------------
# Module 4: Tokenized Vaults & Yield (ERC-4626)
# -----------------------------------------------------------------------------

class VaultModule:
    """Verifies ERC-4626 vaults, inflation vulnerability, and share pricing."""
    def __init__(self, rpc: RPCClient):
        self.rpc = rpc

    def inspect(self, address: str) -> Dict[str, Any]:
        info: Dict[str, Any] = {}
        asset_raw = self.rpc.eth_call(address, SELECTORS["asset"])
        asset = decode_address(asset_raw)
        if not asset:
            return {"is_erc4626": False}

        info["is_erc4626"] = True
        info["asset"] = asset

        tot_assets = decode_uint256(self.rpc.eth_call(address, SELECTORS["totalAssets"]))
        tot_supply = decode_uint256(self.rpc.eth_call(address, SELECTORS["totalSupply"]))

        info["total_assets"] = tot_assets
        info["total_supply"] = tot_supply

        if tot_supply == 0:
            info["inflation_risk"] = "HIGH: Vault is completely empty (totalSupply == 0). Susceptible to first-deposit inflation attack if virtual shares are missing."
        else:
            info["inflation_risk"] = "LOW: Vault is actively funded (totalSupply > 0)."

        one_share_hex = SELECTORS["convertToAssets"] + ("00" * 31 + "01")
        rate_raw = self.rpc.eth_call(address, one_share_hex)
        rate = decode_uint256(rate_raw)
        if rate is not None:
            info["rate_1_share_to_assets"] = rate

        return info

# -----------------------------------------------------------------------------
# Module 5: Token Integrity & Destructive Privileges
# -----------------------------------------------------------------------------

class TokenModule:
    """Audits ERC-20 fundamentals, rebasing uiMultipliers, and adminBurn rights."""
    def __init__(self, rpc: RPCClient):
        self.rpc = rpc

    def inspect(self, address: str, bytecode: str, impl_bytecode: Optional[str] = None) -> Dict[str, Any]:
        info: Dict[str, Any] = {}
        name = decode_string(self.rpc.eth_call(address, SELECTORS["name"]))
        sym = decode_string(self.rpc.eth_call(address, SELECTORS["symbol"]))
        dec = decode_uint256(self.rpc.eth_call(address, SELECTORS["decimals"]))
        supply = decode_uint256(self.rpc.eth_call(address, SELECTORS["totalSupply"]))

        if sym or dec is not None:
            info["name"] = name
            info["symbol"] = sym
            info["decimals"] = dec
            info["total_supply"] = supply
            info["is_erc20"] = True

        # Fables / RWA Multiplier check
        mult_raw = self.rpc.eth_call(address, SELECTORS["uiMultiplier"])
        mult = decode_uint256(mult_raw)
        if mult is not None:
            info["uiMultiplier"] = mult
            info["uiMultiplier_float"] = mult / 1e18 if mult > 1e15 else mult
            info["is_rebasing_equity"] = True

        # Check for Destructive Admin Functions (adminBurn, isBlocked)
        combined_code = (bytecode + (impl_bytecode or "")).lower()
        if "06dd0419" in combined_code:
            info["has_admin_burn"] = True
        if "24745215" in combined_code:
            info["has_blacklist_or_block"] = True

        return info

# -----------------------------------------------------------------------------
# Module 6: Lending, Money Markets & CDP
# -----------------------------------------------------------------------------

class LendingModule:
    """Inspects Compound/IronBank/Curvance cTokens and Comptrollers."""
    def __init__(self, rpc: RPCClient):
        self.rpc = rpc

    def inspect(self, address: str) -> Dict[str, Any]:
        info: Dict[str, Any] = {}
        ex_raw = self.rpc.eth_call(address, SELECTORS["exchangeRateStored"])
        ex_rate = decode_uint256(ex_raw)
        if ex_rate is not None:
            info["is_lending_ctoken"] = True
            info["exchange_rate_stored"] = ex_rate
            comp_raw = self.rpc.eth_call(address, SELECTORS["comptroller"])
            info["comptroller"] = decode_address(comp_raw)
            borrows_raw = self.rpc.eth_call(address, SELECTORS["totalBorrows"])
            info["total_borrows"] = decode_uint256(borrows_raw)
            reserves_raw = self.rpc.eth_call(address, SELECTORS["totalReserves"])
            info["total_reserves"] = decode_uint256(reserves_raw)
            rf_raw = self.rpc.eth_call(address, SELECTORS["reserveFactorMantissa"])
            info["reserve_factor_bps"] = decode_uint256(rf_raw)

        return info

# -----------------------------------------------------------------------------
# Module 7: Oracles & Price Feeds
# -----------------------------------------------------------------------------

class OracleModule:
    """Audits Chainlink AggregatorV3 staleness, round completeness, and pricing health."""
    def __init__(self, rpc: RPCClient):
        self.rpc = rpc

    def inspect(self, address: str) -> Dict[str, Any]:
        info: Dict[str, Any] = {}
        lrd_raw = self.rpc.eth_call(address, SELECTORS["latestRoundData"])
        if not lrd_raw or len(lrd_raw) < 322:
            return {"is_chainlink_oracle": False}

        try:
            data = bytes.fromhex(lrd_raw[2:])
            round_id = int.from_bytes(data[0:32], "big")
            answer = int.from_bytes(data[32:64], "big", signed=True)
            started_at = int.from_bytes(data[64:96], "big")
            updated_at = int.from_bytes(data[96:128], "big")
            answered_in_round = int.from_bytes(data[128:160], "big")

            now = int(time.time())
            staleness_sec = now - updated_at if updated_at > 0 else 0

            info["is_chainlink_oracle"] = True
            info["round_id"] = round_id
            info["answer"] = answer
            info["updated_at"] = updated_at
            info["answered_in_round"] = answered_in_round
            info["staleness_seconds"] = staleness_sec
            info["is_stale"] = staleness_sec > 86400
            info["is_round_complete"] = answered_in_round >= round_id
            info["is_negative_or_zero"] = answer <= 0
        except Exception:
            info["is_chainlink_oracle"] = False

        return info

# -----------------------------------------------------------------------------
# Module 8: Boundary & Sensitivity Diagnostic Radar (LlamaRisk Lenses)
# -----------------------------------------------------------------------------

class BoundaryDiagnosticModule:
    """Forensic radar for boundary failures: deprecated roles, physical vs accounting liquidity, and oracle asymmetry."""
    def __init__(self, rpc: RPCClient):
        self.rpc = rpc

    def inspect(self, address: str, code: str, impl_code: Optional[str], vault_info: Dict[str, Any]) -> Dict[str, Any]:
        info: Dict[str, Any] = {
            "deprecated_roles_detected": [],
            "has_deprecated_roles": False,
            "physical_cash_balance": None,
            "accounting_assets": None,
            "physical_liquidity_ratio": None,
            "synthetic_liquidity_risk": False,
            "oracle_asymmetry_risk": False
        }

        # 1. Bytecode & Role Deprecation Archaeology (Lens 5)
        combined_code = (code + (impl_code or "")).lower()
        deprecated_patterns = [
            ("DEPRECATED_WHITELISTED_ROLE", "01a111c"),
            ("DEPRECATED_BLACKLIST_MANAGER_ROLE", "5cb65d05"),
            ("DEPRECATED_WHITELIST_MANAGER_ROLE", "5d0d4c5b"),
            ("DEPRECATED_MINTER_CONTRACT", "660318"),
        ]
        # Check ASCII hex for "deprecated" (64657072656361746564)
        if "64657072656361746564" in combined_code:
            info["deprecated_roles_detected"].append("ASCII_STRING_'deprecated'_IN_BYTECODE")

        for role_name, role_hex in deprecated_patterns:
            if role_hex in combined_code:
                info["deprecated_roles_detected"].append(role_name)

        if info["deprecated_roles_detected"]:
            info["has_deprecated_roles"] = True

        # 2. Physical Cash vs Accounting Liquidity Check (Lens 1)
        if vault_info.get("is_erc4626") and vault_info.get("asset") and vault_info.get("total_assets") is not None:
            asset_addr = vault_info["asset"]
            total_assets = vault_info["total_assets"]
            info["accounting_assets"] = total_assets

            padded_addr = address[2:].lower().zfill(64)
            bal_calldata = SELECTORS["balanceOf"] + padded_addr
            raw_bal = self.rpc.eth_call(asset_addr, bal_calldata)
            if raw_bal and raw_bal != "0x":
                try:
                    phys_bal = int(raw_bal, 16)
                    info["physical_cash_balance"] = phys_bal
                    if total_assets > 0:
                        ratio = phys_bal / total_assets
                        info["physical_liquidity_ratio"] = round(ratio, 4)
                        if ratio < 0.30:
                            info["synthetic_liquidity_risk"] = True
                except Exception:
                    pass

        # 3. Oracle Asymmetry Check (Lens 3)
        has_convert = SELECTORS["convertToAssets"][2:] in combined_code
        has_chainlink = SELECTORS["latestRoundData"][2:] in combined_code
        if has_convert and has_chainlink:
            info["oracle_asymmetry_risk"] = True

        return info

# -----------------------------------------------------------------------------
# Master Orchestrator: ProtocolAuditInspector
# -----------------------------------------------------------------------------

class ProtocolAuditInspector:
    """Master orchestrator combining all modules into a unified evaluation pipeline."""
    def __init__(self, rpc_url: str):
        self.rpc = RPCClient(rpc_url)
        self.proxy_mod = ProxyModule(self.rpc)
        self.gov_mod = GovernanceModule(self.rpc)
        self.amm_mod = AMMHookModule(self.rpc)
        self.vault_mod = VaultModule(self.rpc)
        self.token_mod = TokenModule(self.rpc)
        self.lending_mod = LendingModule(self.rpc)
        self.oracle_mod = OracleModule(self.rpc)
        self.boundary_mod = BoundaryDiagnosticModule(self.rpc)

    def inspect_contract(self, address: str, name: str = "Target Contract") -> Dict[str, Any]:
        report: Dict[str, Any] = {
            "name": name,
            "address": address,
            "deployed": False,
            "bytecode_size": 0
        }

        # 1. Bytecode check
        code = self.rpc.get_code(address)
        if not code or code == "0x":
            return report

        report["deployed"] = True
        report["bytecode_size"] = (len(code) - 2) // 2

        # 2. Proxy Archaeology
        proxy_info = self.proxy_mod.inspect(address, code)
        report["proxy"] = proxy_info

        # If proxy has implementation, fetch implementation bytecode for deeper analysis
        impl_code = None
        if proxy_info.get("implementation"):
            impl_code = self.rpc.get_code(proxy_info["implementation"])
            if impl_code and impl_code != "0x":
                report["proxy"]["implementation_size"] = (len(impl_code) - 2) // 2

        # 3. Governance & Privilege
        report["governance"] = self.gov_mod.inspect(address)

        # 4. Token & Destructive Rights
        report["token"] = self.token_mod.inspect(address, code, impl_code)

        # 5. Vaults (ERC-4626)
        report["vault"] = self.vault_mod.inspect(address)

        # 6. AMMs
        report["amm"] = self.amm_mod.inspect_amm(address)

        # 7. Uniswap v4 Hook (Only if contract is genuinely a hook)
        if self.amm_mod.is_likely_v4_hook(address, code, name):
            report["hook_bitmask"] = self.amm_mod.decode_hook_bitmask(address)
        else:
            report["hook_bitmask"] = None

        # 8. Lending & Oracles
        report["lending"] = self.lending_mod.inspect(address)
        report["oracle"] = self.oracle_mod.inspect(address)

        # 9. Boundary & Sensitivity Diagnostics (LlamaRisk Lenses)
        report["boundary"] = self.boundary_mod.inspect(address, code, impl_code, report["vault"])

        # 10. Derive Protocol Archetypes & Targeted Review Checklists
        report["archetypes"] = self.derive_archetypes(report)

        return report

    def derive_archetypes(self, report: Dict[str, Any]) -> List[str]:
        archetypes = []
        if report.get("token", {}).get("is_rebasing_equity") or report.get("token", {}).get("has_admin_burn"):
            archetypes.append("TOKENIZED_EQUITY_RWA")
        if report.get("hook_bitmask") is not None:
            archetypes.append("UNISWAP_V4_HOOK")
        if report.get("amm", {}).get("is_amm_pool") or report.get("amm", {}).get("is_curve_pool"):
            archetypes.append("AMM_LIQUIDITY_POOL")
        if report.get("vault", {}).get("is_erc4626"):
            archetypes.append("ERC4626_TOKENIZED_VAULT")
        if report.get("lending", {}).get("is_lending_ctoken"):
            archetypes.append("LENDING_MONEY_MARKET")
        if report.get("oracle", {}).get("is_chainlink_oracle"):
            archetypes.append("ORACLE_DEPENDENCY")
        if report.get("proxy", {}).get("is_proxy"):
            archetypes.append("UPGRADEABLE_PROXY")
        if report.get("boundary", {}).get("synthetic_liquidity_risk"):
            archetypes.append("SYNTHETIC_LIQUIDITY_TRAP_RISK")
        if report.get("boundary", {}).get("has_deprecated_roles"):
            archetypes.append("DEPRECATED_ROLES_DETECTED")
        if report.get("boundary", {}).get("oracle_asymmetry_risk"):
            archetypes.append("ASYMMETRIC_ORACLE_RISK")
        return archetypes

    def print_terminal_report(self, report: Dict[str, Any]):
        print(f"\n{'='*70}")
        print(f"[*] PROTOCOL AUDIT INSPECTION: {report['name']} ({report['address']})")
        print(f"{'='*70}")

        if not report["deployed"]:
            print(f"[!] STATUS: NOT DEPLOYED / EMPTY (Zero Bytecode)")
            return

        print(f"[+] Deployed Bytecode: {report['bytecode_size']:,} bytes")

        # Proxy Findings
        p = report["proxy"]
        if p["is_proxy"]:
            print(f"[+] Proxy Architecture: {p['proxy_type']}")
            if p.get("implementation"):
                impl_size_str = f" ({p.get('implementation_size', 0):,} bytes)" if p.get("implementation_size") else ""
                print(f"    └── Implementation: {p['implementation']}{impl_size_str}")
            if p.get("beacon"):
                print(f"    └── UpgradeableBeacon: {p['beacon']}")
            if p.get("admin"):
                print(f"    └── Proxy Admin: {p['admin']}")

        # Governance Findings
        g = report["governance"]
        if g.get("owner"):
            print(f"[+] Access Control: Owner = {g['owner']}")
            if g.get("pending_owner"):
                print(f"    └── Two-Step Transfer Active: Pending = {g['pending_owner']}")
        if g.get("timelock_min_delay_seconds") is not None:
            print(f"[+] Timelock Delay: {g['timelock_min_delay_seconds']}s ({g['timelock_min_delay_hours']} hours)")
        if g.get("is_paused"):
            print(f"[!] STATUS: Protocol is currently PAUSED")

        # Token Findings
        t = report["token"]
        if t.get("is_erc20"):
            print(f"[+] Token Details: {t.get('name')} ({t.get('symbol')}) - Decimals: {t.get('decimals')}")
            if t.get("is_rebasing_equity"):
                print(f"[!] REBASING EQUITIES: uiMultiplier = {t.get('uiMultiplier_float')}x (Elastic Multiplier)")
            if t.get("has_admin_burn"):
                print(f"[CRIT] DESTRUCTIVE PRIVILEGE: adminBurn() detected! Issuer can unilaterally burn tokens.")
            if t.get("has_blacklist_or_block"):
                print(f"[WARN] CUSTODIAL PRIVILEGE: Blacklist / isBlocked mechanism detected.")

        # Vault Findings
        v = report["vault"]
        if v.get("is_erc4626"):
            print(f"[+] ERC-4626 Vault Detected: Underlying Asset = {v['asset']}")
            print(f"    └── Total Assets: {v.get('total_assets'):,} | Total Supply: {v.get('total_supply'):,}")
            print(f"    └── Inflation Attack Risk: {v.get('inflation_risk')}")

        # Hook Findings
        h = report.get("hook_bitmask")
        if h:
            active_hooks = [k for k, val in h.get("permissions", {}).items() if val]
            print(f"[+] Uniswap v4 Hook Flags: {h['flags_hex']}")
            print(f"    └── Active Hooks: {', '.join(active_hooks)}")
            status_text = "[PASS] Safe in PoolManager" if h["is_non_custodial"] else "[WARN] Custom liquidity/deltas active"
            print(f"    └── Non-Custodial Safety: {status_text}")

        # Lending Findings
        l = report["lending"]
        if l.get("is_lending_ctoken"):
            print(f"[+] Lending Market cToken: Comptroller = {l.get('comptroller')}")
            print(f"    └── Exchange Rate Stored: {l.get('exchange_rate_stored')}")

        # Oracle Findings
        o = report["oracle"]
        if o.get("is_chainlink_oracle"):
            print(f"[+] Chainlink Price Feed: Answer = {o['answer']} (Round {o['round_id']})")
            if o["is_stale"]:
                print(f"[!] WARNING: Oracle data is STALE ({o['staleness_seconds']} seconds old)")

        # Boundary & Sensitivity Diagnostics (LlamaRisk Lenses)
        b = report.get("boundary", {})
        if b.get("has_deprecated_roles"):
            print(f"[!] BOUNDARY WARNING: Deprecated roles detected in bytecode: {', '.join(b['deprecated_roles_detected'])}")
        if b.get("physical_liquidity_ratio") is not None:
            ratio_pct = b["physical_liquidity_ratio"] * 100
            print(f"[+] Physical Liquidity Ratio (μ): {ratio_pct:.2f}% (Cash: {b['physical_cash_balance']:,} / Accounting: {b['accounting_assets']:,})")
            if b.get("synthetic_liquidity_risk"):
                print(f"[CRIT] SYNTHETIC LIQUIDITY TRAP: Physical cash is < 30% of total reported assets! Front-loaded run risk.")
        if b.get("oracle_asymmetry_risk"):
            print(f"[WARN] ASYMMETRIC ORACLE RISK: Contract combines spot convertToAssets with Chainlink feed without uniform smoothing!")

        # Archetypes & Targeted Attack Surface Checklist
        archs = report.get("archetypes", [])
        if archs:
            print(f"\n[+] Detected Archetypes: {', '.join(archs)}")
            print("    └── Tailored Audit Checklist Items:")
            if "TOKENIZED_EQUITY_RWA" in archs:
                print("        • [RWA] Does weekend/overnight stock market gap expose pool to Monday morning MEV leakage?")
                print("        • [RWA] Does dynamic rebase / multiplier expansion cause tick liquidity desync?")
                print("        • [RWA] Can issuer trigger adminBurn on PoolManager or user accounts?")
            if "UNISWAP_V4_HOOK" in archs:
                print("        • [HOOK] Can hook modify swap output deltas or siphon fees without LP consent?")
                print("        • [HOOK] Is hook pool initialization permissionless, allowing front-run fee hijacking?")
            if "ERC4626_TOKENIZED_VAULT" in archs:
                print("        • [VAULT] Is vault vulnerable to first-deposit inflation attacks (donation + share burning)?")
                print("        • [VAULT] Are asset and share decimals aligned with no precision truncation?")
            if "LENDING_MONEY_MARKET" in archs:
                print("        • [LENDING] Can zero-liquidity positions cause division-by-zero during bad debt liquidation?")
                print("        • [LENDING] Are borrow caps and collateral factors strictly validated against oracle staleness?")
            if "UPGRADEABLE_PROXY" in archs:
                print("        • [GOV] Is the implementation contract constructor protected via _disableInitializers()?")
                print("        • [GOV] Does the proxy admin have a multi-sig and minimum timelock delay (>= 24h)?")
            if "SYNTHETIC_LIQUIDITY_TRAP_RISK" in archs:
                print("        • [LIQUIDITY] Does the interest rate model count swept/illiquid assets as available cash?")
                print("        • [LIQUIDITY] Can a 24h withdrawal shock of 20-25% deplete 100% of liquid physical reserves?")
            if "ASYMMETRIC_ORACLE_RISK" in archs:
                print("        • [ORACLE] Are all terms in composite price formula symmetrically smoothed with identical TWAP/EMA?")
                print("        • [ORACLE] Can an adversary drain vault supply in block N to amplify convertToAssets manipulation?")
            if "DEPRECATED_ROLES_DETECTED" in archs:
                print("        • [PRIVILEGE] Are advertised on-chain whitelists or access roles silently deprecated in storage?")

# -----------------------------------------------------------------------------
# CLI Entrypoint
# -----------------------------------------------------------------------------

def main():
    parser = argparse.ArgumentParser(description="Universal EVM Contract Audit Inspector (Modular Enterprise Edition)")
    parser.add_argument("--rpc", required=True, help="RPC URL")
    parser.add_argument("--address", help="Single contract address to inspect")
    parser.add_argument("--name", default="Target Contract", help="Optional name label")
    parser.add_argument("--config", help="JSON file with contract dictionary: {'name': '0x...'}")
    parser.add_argument("--json", action="store_true", help="Output raw JSON format")
    args = parser.parse_args()

    inspector = ProtocolAuditInspector(args.rpc)

    if args.address:
        res = inspector.inspect_contract(args.address, args.name)
        if args.json:
            print(json.dumps(res, indent=2))
        else:
            inspector.print_terminal_report(res)
    elif args.config:
        with open(args.config, "r") as f:
            data = json.load(f)
        contracts = data.get("contracts", data)
        all_results = {}
        for name, entry in contracts.items():
            addr = entry if isinstance(entry, str) else entry.get("address")
            if addr:
                res = inspector.inspect_contract(addr, name)
                all_results[name] = res
                if not args.json:
                    inspector.print_terminal_report(res)
        if args.json:
            print(json.dumps(all_results, indent=2))
    else:
        print("Please provide --address or --config. Run with --help for details.")
        sys.exit(1)

if __name__ == "__main__":
    main()
