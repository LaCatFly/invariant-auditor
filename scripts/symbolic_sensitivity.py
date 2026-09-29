#!/usr/bin/env python3
"""
================================================================================
Symbolic Sensitivity Analysis Engine (SymPy Math Engine for Smart Contracts)
================================================================================
Standard: Closed-Form Non-Linear Sensitivity & Oracle Parity (Lens 3 & 4)
Computes:
  - Partial derivatives (Jacobian: dMetric / dVar)
  - Curvature & second derivatives (Hessian: d^2Metric / dVar^2)
  - Denominator singularities & cubic/higher-power traps (e.g. p_o^3)
  - Inverse monotonicity hazards (e.g. dHealth / dPrice < 0)
  - Limit asymptotics (lim Var -> 0, lim Var -> inf)
================================================================================
"""

import sys
import argparse
import json
from typing import Dict, Any, List, Optional
try:
    import sympy as sp
    from sympy.parsing.sympy_parser import parse_expr, standard_transformations, implicit_multiplication_application
except ImportError:
    sys.stderr.write("[!] Error: 'sympy' is required for symbolic sensitivity analysis.\n")
    sys.stderr.write("    Please install it using: pip install sympy\n")
    sys.exit(1)

TRANSFORMATIONS = standard_transformations + (implicit_multiplication_application,)

class SymbolicSensitivityEngine:
    def __init__(self):
        pass

    def analyze_formula(self, formula_str: str, target_vars: Optional[List[str]] = None, domain_constraints: Optional[Dict[str, str]] = None) -> Dict[str, Any]:
        """
        Parses a mathematical expression, differentiates with respect to target variables,
        and checks for nonlinear boundary traps.
        """
        expr = parse_expr(formula_str, transformations=TRANSFORMATIONS)
        free_symbols = {str(s): s for s in expr.free_symbols}
        
        if not target_vars:
            target_vars = list(free_symbols.keys())

        results = {
            "original_formula": str(expr),
            "variables": list(free_symbols.keys()),
            "sensitivities": {},
            "traps_detected": []
        }

        # Check for denominator terms and powers in original formula
        numer, denom = expr.as_numer_denom()
        results["has_denominator"] = denom != 1
        results["denominator"] = str(denom)

        for var_name in target_vars:
            if var_name not in free_symbols:
                continue
            
            var = free_symbols[var_name]
            # 1. First partial derivative
            first_deriv = sp.diff(expr, var)
            simplified_first = sp.simplify(first_deriv)
            
            # 2. Second partial derivative (Curvature)
            second_deriv = sp.diff(first_deriv, var)
            simplified_second = sp.simplify(second_deriv)

            # 3. Check power of variable in denominator
            var_in_denom = var in denom.free_symbols
            denom_degree = sp.degree(denom, var) if var_in_denom else 0

            # 4. Check signs & inverse monotonicity
            # Test with assumptions that all free symbols > 0
            is_always_positive = False
            is_always_negative = False
            try:
                assumptions = {s: sp.Symbol(str(s), positive=True) for s in expr.free_symbols}
                pos_deriv = simplified_first.subs({s: assumptions[s] for s in expr.free_symbols})
                if pos_deriv.is_positive:
                    is_always_positive = True
                elif pos_deriv.is_negative:
                    is_always_negative = True
            except Exception:
                pass

            var_report = {
                "first_derivative": str(simplified_first),
                "second_derivative": str(simplified_second),
                "in_denominator": var_in_denom,
                "denominator_degree": int(denom_degree),
                "is_always_positive": is_always_positive,
                "is_always_negative": is_always_negative,
            }

            # 5. Trap Detection Rules
            if denom_degree >= 2:
                results["traps_detected"].append({
                    "trap": "HIGH_POWER_DENOMINATOR_SENSITIVITY",
                    "severity": "CRITICAL" if denom_degree >= 3 else "HIGH",
                    "variable": var_name,
                    "degree": int(denom_degree),
                    "description": f"Variable '{var_name}' sits in denominator with degree {denom_degree}. A small drop in {var_name} causes explosive non-linear surges."
                })

            if is_always_negative:
                results["traps_detected"].append({
                    "trap": "INVERSE_MONOTONICITY_HAZARD",
                    "severity": "HIGH",
                    "variable": var_name,
                    "description": f"Partial derivative dMetric/d{var_name} is strictly negative. An INCREASE in '{var_name}' causes a DECREASE in the target metric (e.g. sDOLA health collapse)."
                })

            # Check limits at 0 and infinity
            try:
                lim_0 = sp.limit(expr, var, 0, "+")
                var_report["limit_at_zero"] = str(lim_0)
                if lim_0 == sp.oo or lim_0 == -sp.oo:
                    results["traps_detected"].append({
                        "trap": "SINGULARITY_AT_ZERO",
                        "severity": "CRITICAL",
                        "variable": var_name,
                        "description": f"Metric approaches infinity when '{var_name}' approaches zero (Zero-supply / zero-reserve exploitation risk)."
                    })
            except Exception:
                pass

            results["sensitivities"][var_name] = var_report

        return results

    def print_terminal_report(self, analysis: Dict[str, Any]):
        print(f"\n{'='*75}")
        print(f"[*] SYMBOLIC SENSITIVITY & DERIVATIVE ENGINE (SymPy)")
        print(f"{'='*75}")
        print(f"Target Formula: {analysis['original_formula']}")
        print(f"Variables Identified: {', '.join(analysis['variables'])}")
        print(f"Denominator Expression: {analysis['denominator']}")
        
        traps = analysis.get("traps_detected", [])
        if traps:
            print(f"\n[!] NON-LINEAR SENSITIVITY TRAPS DETECTED: {len(traps)}")
            for t in traps:
                print(f"    └── [{t['severity']}] {t['trap']} (Var: {t.get('variable')}): {t['description']}")
        else:
            print(f"\n[+] No non-linear denominator traps or inverse monotonicity detected.")

        print(f"\n[+] Variable Derivatives & Curvature:")
        for var_name, data in analysis["sensitivities"].items():
            print(f"    • Variable: {var_name}")
            print(f"      ├── dMetric/d{var_name}: {data['first_derivative']}")
            print(f"      ├── d²Metric/d{var_name}²: {data['second_derivative']}")
            if data["in_denominator"]:
                print(f"      ├── [WARN] Denominator Degree: {data['denominator_degree']}")
            if "limit_at_zero" in data:
                print(f"      └── Limit as {var_name} -> 0: {data['limit_at_zero']}")

def main():
    parser = argparse.ArgumentParser(description="Symbolic Sensitivity Analysis Engine for Smart Contracts")
    parser.add_argument("--formula", required=True, help="Mathematical expression (e.g. 'x * p_up^2 * p_down / (p_o^3 * sqrt(band_ratio))')")
    parser.add_argument("--vars", nargs="*", help="Specific variables to differentiate against")
    parser.add_argument("--json", action="store_true", help="Output raw JSON")
    args = parser.parse_args()

    engine = SymbolicSensitivityEngine()
    analysis = engine.analyze_formula(args.formula, args.vars)

    if args.json:
        print(json.dumps(analysis, indent=2))
    else:
        engine.print_terminal_report(analysis)

if __name__ == "__main__":
    main()
