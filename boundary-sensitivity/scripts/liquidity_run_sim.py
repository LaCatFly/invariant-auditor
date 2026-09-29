#!/usr/bin/env python3
"""
================================================================================
Dynamic Liquidity Outflow & Settlement Latency Simulator (Lens 1 Engine)
================================================================================
Standard: Physical vs Accounting Liquidity Slicing & Run Dynamics (LlamaRisk Lens 1)
Simulates:
  - Capital run shock curve: Outflow(t) = TotalLiabilities * (1 - e^(-kappa * t))
  - Multi-tier latency pipeline:
      Tier 0: Instant in-contract cash (C_instant, Block t)
      Tier 1: On-chain AMM/flash unswapping (T+0, minutes)
      Tier 2: Off-chain MMF / RWA redemption (T+1 / T+2, 24-48 hours)
      Tier 3: Weekend/holiday bank freeze (T_weekend, 60+ hours)
  - Computes:
      - Physical Liquidity Ratio (mu)
      - Time-to-Illiquidity (T_exhaust in hours/blocks)
      - Synthetic Liquidity Trap (Accounting Utilization vs Physical Cashout)
================================================================================
"""

import sys
import argparse
import json
import math
from typing import Dict, Any, List, Optional

class LiquidityRunSimulator:
    def __init__(self):
        pass

    def simulate_shock(
        self,
        total_liabilities: float,
        instant_cash: float,
        delayed_t1: float = 0.0,
        delayed_t2: float = 0.0,
        shock_percentage_24h: float = 0.25,
        is_weekend: bool = False,
        hours: int = 72
    ) -> Dict[str, Any]:
        """
        Simulates capital outflow velocity across a given time horizon.
        """
        # Historical DeFi run parameter: 98.6% of run depletion happens in first 24h
        # 1 - exp(-kappa * 24) = shock_percentage_24h
        # exp(-kappa * 24) = 1 - shock_percentage_24h
        # kappa = -ln(1 - shock_percentage_24h) / 24
        if shock_percentage_24h >= 1.0:
            shock_percentage_24h = 0.99
        kappa = -math.log(1.0 - shock_percentage_24h) / 24.0

        mu = instant_cash / total_liabilities if total_liabilities > 0 else 1.0

        timeline = []
        exhaustion_hour = None
        insolvent = False

        for h in range(hours + 1):
            # Cumulative withdrawal demand by hour h
            outflow_fraction = 1.0 - math.exp(-kappa * h)
            cumulative_demand = total_liabilities * outflow_fraction

            # Available liquidity by hour h
            avail_liquid = instant_cash

            # T+1 clears at h >= 24 (unless weekend)
            if h >= 24 and not (is_weekend and h < 60):
                avail_liquid += delayed_t1

            # T+2 clears at h >= 48 (unless weekend)
            if h >= 48 and not (is_weekend and h < 84):
                avail_liquid += delayed_t2

            cash_remaining = avail_liquid - cumulative_demand
            if cash_remaining < 0 and not insolvent:
                insolvent = True
                exhaustion_hour = h

            if h in [0, 6, 12, 18, 24, 36, 48, 72]:
                timeline.append({
                    "hour": h,
                    "cumulative_demand": round(cumulative_demand, 2),
                    "outflow_percent": round(outflow_fraction * 100, 2),
                    "available_cleared": round(avail_liquid, 2),
                    "cash_balance": round(cash_remaining, 2),
                    "is_solvent": cash_remaining >= 0
                })

        # Calculate exact run percentage where instant cash depletes
        cash_depletion_shock_pct = (instant_cash / total_liabilities) * 100 if total_liabilities > 0 else 100.0

        results = {
            "total_liabilities": total_liabilities,
            "instant_cash": instant_cash,
            "delayed_t1": delayed_t1,
            "delayed_t2": delayed_t2,
            "physical_liquidity_ratio_pct": round(mu * 100, 2),
            "is_weekend_gap_mode": is_weekend,
            "24h_shock_target_pct": round(shock_percentage_24h * 100, 2),
            "cash_exhaustion_at_shock_pct": round(cash_depletion_shock_pct, 2),
            "will_exhaust": insolvent,
            "time_to_exhaustion_hours": exhaustion_hour,
            "synthetic_liquidity_trap": mu < 0.30 and (delayed_t1 + delayed_t2) > instant_cash,
            "timeline": timeline
        }

        return results

    def print_terminal_report(self, res: Dict[str, Any]):
        print(f"\n{'='*75}")
        print(f"[*] DYNAMIC LIQUIDITY RUN & SETTLEMENT LATENCY SIMULATOR (Lens 1)")
        print(f"{'='*75}")
        print(f"Total Liabilities: ${res['total_liabilities']:,.2f}")
        print(f"Instant Cash in Vault (T0): ${res['instant_cash']:,.2f} ({res['physical_liquidity_ratio_pct']}% of liabilities)")
        print(f"Latent T+1 Claims: ${res['delayed_t1']:,.2f} | Latent T+2 Claims: ${res['delayed_t2']:,.2f}")
        print(f"Weekend Settlement Gap: {'ACTIVE (Bank rails closed)' if res['is_weekend_gap_mode'] else 'INACTIVE'}")

        if res["synthetic_liquidity_trap"]:
            print(f"\n[CRIT] SYNTHETIC LIQUIDITY TRAP DETECTED!")
            print(f"       Physical cash is only {res['physical_liquidity_ratio_pct']}% of liabilities, while ${(res['delayed_t1'] + res['delayed_t2']):,.2f} is swept into delayed claims.")
            print(f"       A withdrawal shock will drain physical cash before accounting utilization spikes borrow rates!")

        if res["will_exhaust"]:
            print(f"\n[!] TIME TO ILLIQUIDITY (T_exhaust): {res['time_to_exhaustion_hours']} HOURS!")
            print(f"    Vault runs dry at {res['cash_exhaustion_at_shock_pct']:.2f}% cumulative withdrawal run.")
        else:
            print(f"\n[+] PROTOCOL REMAINS SOLVENT through 72h shock curve (Cash buffer absorbs outflow).")

        print(f"\n[+] Shock Depletion Timeline:")
        print(f"    {'Hour':<6} {'Outflow %':<12} {'Demand ($)':<16} {'Cleared ($)':<16} {'Vault Cash ($)':<16} {'Status'}")
        print(f"    {'-'*70}")
        for t in res["timeline"]:
            status = "SOLVENT" if t["is_solvent"] else "FROZEN (DRY)"
            print(f"    {t['hour']:<6} {t['outflow_percent']:<12.1f} {t['cumulative_demand']:<16,.0f} {t['available_cleared']:<16,.0f} {t['cash_balance']:<16,.0f} {status}")

def main():
    parser = argparse.ArgumentParser(description="Dynamic Liquidity Outflow & Latency Simulator")
    parser.add_argument("--liabilities", type=float, required=True, help="Total liabilities / deposits ($)")
    parser.add_argument("--cash", type=float, required=True, help="Immediately withdrawable cash in vault ($)")
    parser.add_argument("--t1", type=float, default=0.0, help="T+1 settlement assets ($)")
    parser.add_argument("--t2", type=float, default=0.0, help="T+2 settlement assets ($)")
    parser.add_argument("--shock", type=float, default=0.25, help="24-hour shock fraction (e.g. 0.25 = 25%%)")
    parser.add_argument("--weekend", action="store_true", help="Model weekend banking gap (60h freeze on T+1/T+2)")
    parser.add_argument("--json", action="store_true", help="Output raw JSON")
    args = parser.parse_args()

    sim = LiquidityRunSimulator()
    res = sim.simulate_shock(args.liabilities, args.cash, args.t1, args.t2, args.shock, args.weekend)

    if args.json:
        print(json.dumps(res, indent=2))
    else:
        sim.print_terminal_report(res)

if __name__ == "__main__":
    main()
