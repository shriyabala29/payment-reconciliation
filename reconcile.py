#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Created on Sat Oct  3 21:15:37 2026

@author: Shriya Balabathuri
"""

"""
Daily payment pre-release reconciliation control.

Compares what we intended to pay partners (disbursals.csv) against evidence the
money actually arrived (bank_evidence.csv). Holds anything that does not fully
reconcile and writes an exceptions report for the team to action.

Run: python reconcile.py
"""

import pandas as pd

# Control settings
AMOUNT_TOLERANCE = 0.01      # ignore amount differences of 1p or less (rounding)
LARGE_PAYMENT = 20000.00     # payments above this get a second-look note

def reconcile():
    disbursals = pd.read_csv("data/disbursals.csv", parse_dates=["disbursal_date"])
    evidence   = pd.read_csv("data/bank_evidence.csv", parse_dates=["value_date"])

    merged = disbursals.merge(
        evidence, on="payment_ref", how="outer",
        suffixes=("_disbursed", "_evidence"), indicator=True,
    )

    results = []
    for _, row in merged.iterrows():
        reasons = []

        if row["_merge"] == "left_only":
            reasons.append("No bank evidence for a payment we disbursed")
        elif row["_merge"] == "right_only":
            reasons.append("Bank evidence for a payment we never disbursed")
        else:
            if abs(row["amount_gbp_disbursed"] - row["amount_gbp_evidence"]) > AMOUNT_TOLERANCE:
                reasons.append(
                    f"Amount mismatch: sent {row['amount_gbp_disbursed']:.2f}, "
                    f"received {row['amount_gbp_evidence']:.2f}"
                )
            if row["payee_account_disbursed"] != row["payee_account_evidence"]:
                reasons.append("Payee account mismatch")
            days_late = (row["value_date"] - row["disbursal_date"]).days
            if days_late > 0:
                reasons.append(f"Settled {days_late} day(s) late")

            # --- Second-look note for large payments (a flag, not a hold) ---
            current_amount = row["amount_gbp_disbursed"]
            if pd.isna(current_amount):
                current_amount = row["amount_gbp_evidence"]
            if pd.notna(current_amount) and current_amount > LARGE_PAYMENT:
                reasons.append(f"Large payment (over GBP {LARGE_PAYMENT:,.0f}) - recommend second review")

      
        amount = row["amount_gbp_disbursed"]
        if pd.isna(amount):
            amount = row["amount_gbp_evidence"]

        results.append({
            "payment_ref": row["payment_ref"],
            "partner": row["partner"] if pd.notna(row["partner"]) else "UNKNOWN",
            "amount_gbp": amount,
            "status": "HOLD" if reasons else "RELEASE",
            "reason": "; ".join(reasons) if reasons else "Matched in full",
        })

    return pd.DataFrame(results)


def main():
    results = reconcile()
    held     = results[results["status"] == "HOLD"]
    released = results[results["status"] == "RELEASE"]

    print("=" * 60)
    print("DAILY PAYMENT PRE-RELEASE RECONCILIATION")
    print("=" * 60)
    print(f"Payments checked:       {len(results)}")
    print(f"Cleared to release:     {len(released)}  (GBP {released['amount_gbp'].sum():,.2f})")
    print(f"Held for investigation: {len(held)}  (GBP {held['amount_gbp'].sum():,.2f})")
    print("-" * 60)

    if held.empty:
        print("No exceptions. All payments reconcile.")
    else:
        print("ITEMS HELD:")
        for _, r in held.iterrows():
            print(f"  [{r['payment_ref']}] {r['partner']}  GBP {r['amount_gbp']:,.2f}")
            print(f"       -> {r['reason']}")
    print("=" * 60)

    # --- Save ONLY the exceptions: that's the team's worklist ---
    held.to_csv("output/exceptions_report.csv", index=False)
    print("\nExceptions written to output/exceptions_report.csv")


if __name__ == "__main__":
    main()