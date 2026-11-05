---
name: amounts-check
description: Compute and verify amounts and fees in a payment project - XOF as integers, conversion 1 EUR = 676 XOF, base, rate, explicit rounding, ledger entry split, fee schedule and fee modes. Use for "combien de frais", "vérifie ce calcul", "modifie la grille de tarification", or when writing tests on amounts.
---

# Amount and fee checks

Read the project's schedule and rules first (CLAUDE.md, `procedures/`, fee code): this skill gives the method, not the rates.

## Absolute rules
- **XOF as integers**, no decimals; never a float. Conversion **1 EUR = 676 XOF**, rounding explicit (documented direction) and tested.
- Amounts stored in the minor unit of the configured currency; the currency is never hard-coded.
- The **fee mode** (fee on the sender or taken from the amount) is frozen when the transaction is initiated.
- No hidden rounding in display: the displayed total is the sum of the displayed lines.

## Method
1. Compute with integers and show the detail: base, rate, cap/allowance, rounding, split between accounts.
2. Check the invariant: **sum of entries = 0** (debits = credits), fees and commissions included.
3. Compare with the code and existing tests; on divergence, cite the known gap (identifier from the project's gap list) instead of fixing by hand.
4. Schedule change: boundary tests (0, 1, threshold, cap, cap + 1), every fee mode, idempotency if the operation is replayed.
5. Worked examples in the answer on a reference amount (for example 1,000 XOF) for each flow (deposit, withdrawal, transfer, merchant).

## Never
Float or unquantised `Decimal` for money, editing a balance in the database (use a traced reversal entry), implicit rounding.

## End of task
Log the run: `${CLAUDE_SKILL_DIR}/../skill-learning/learn.py log amounts-check ok|partial|failed [--note …]`.
