# Payment Pre-Release Reconciliation

A small Python control that checks partner payments settled correctly before the
next batch is released. It compares what we intended to pay against evidence that
the money actually arrived, and holds anything that does not fully reconcile.

This is a simplified version of a real daily payments control: funds flow to
partners before the next day's payments go out, so you need to confirm yesterday's
money reached the right account, for the right amount, on time, before releasing
anything new.

# What it checks

For every payment, it confirms the bank evidence matches our record on:

- **Presence** — every payment we sent has evidence, and every piece of evidence maps to a real payment
- **Amount** — the amount received matches the amount sent (within a 1p rounding tolerance)
- **Account** — the money reached the account we intended to pay
- **Timing** — the payment settled on time, not late

It also flags any payment over GBP 20,000 for a second review. Anything that fails
is marked **HOLD** with a plain-English reason; everything else is **RELEASE**.

## Running it

```bash
pip install pandas
python reconcile.py
```

It prints a summary and writes the items to action to `output/exceptions_report.csv`.

## Example output

```
============================================================
DAILY PAYMENT PRE-RELEASE RECONCILIATION
============================================================
Payments checked:       6
Cleared to release:     2  (GBP 20,800.50)
Held for investigation: 4  (GBP 45,050.00)
------------------------------------------------------------
ITEMS HELD:
  [TXN003] PartnerB  GBP 15,750.00
       -> Settled 1 day(s) late
  [TXN004] PartnerB  GBP 4,200.00
       -> No bank evidence for a payment we disbursed
  [TXN005] PartnerC  GBP 22,100.00
       -> Amount mismatch: sent 22100.00, received 21100.00; Large payment (over GBP 20,000) - recommend second review
  [TXN099] UNKNOWN  GBP 3,000.00
       -> Bank evidence for a payment we never disbursed
============================================================
```

## Files

| File | Purpose |
|------|---------|
| `reconcile.py` | The control: loads both files, reconciles, reports exceptions |
| `data/disbursals.csv` | What we intended to pay (sample data) |
| `data/bank_evidence.csv` | What the bank evidenced as received (sample, with deliberate discrepancies) |
| `output/exceptions_report.csv` | Generated — the items held for investigation |

## Design notes

- The amount tolerance and large-payment threshold are set as parameters at the
  top of the script, so the control can be tightened or loosened without changing
  the logic.
- An outer join is used deliberately, so payments missing from *either* side are
  surfaced rather than silently dropped.
- Only exceptions are written to file — the point of the control is to surface the
  few items that need a human, not re-list everything that is fine.

## Possible extensions

- Re-verify partner bank details against a stored reference and flag any change
- Group exceptions by partner to spot patterns in who settles late or short
- Replace the CSV inputs with a direct database query
