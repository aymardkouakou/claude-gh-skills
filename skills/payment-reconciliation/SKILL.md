---
name: payment-reconciliation
description: Diagnose a stuck or mismatched payment transaction (deposit, withdrawal, transfer, merchant payment, mobile money) and run reconciliation checks (orphans, duplicates, operator float, transit-account closing, treasury position). Use for "transaction à vérifier", "écart", "wallet pas crédité", "client réclame", "double débit", "contrôle quotidien".
---

# Transaction diagnosis and reconciliation

Read-only by default. **No balance correction without the user's approval**, and never directly in the database: a traced reversal entry. No personal data or secret in outputs. Read the project's business procedures first (flows, statuses, deadlines, known gaps).

## Inputs to ask for
Reference or reconciliation key, flow, operator (Wave, MTN, Orange, Moov), amount in XOF (integer), date, fee mode.

## Status rules (confirm against the project's procedure)
- **Deposit**: never credit before a verified notification; idempotency on the reconciliation key.
- **Withdrawal**: debit before the payment order; re-credit only if the failure is **certain** (operator status), otherwise "To verify".
- **Transfer**: debit, credit and commission are atomic.
- **Merchant**: the customer pays the price, the commission is deducted from the merchant.
- **Webhooks and callbacks**: idempotent, signature verified, logged without sensitive data; timeouts and intermediate (pending) statuses handled explicitly. Wave: skill `wave-payments`.

## Diagnosis
1. Find the transaction and its idempotency key; list every linked entry.
2. Compare with the operator status by **querying with the same key**; never resend with a new key.
3. "To verify": wait for the operator delay, query, then decide Paid or Failed; never re-credit without certainty.
4. Mismatch: classify (orphan, duplicate, amount, fee) and apply the procedure's target deadlines.
5. Complaint: acknowledge, answer within deadlines, keep the evidence.
6. Code defect: link it to the known technical gap or open an issue (`issue-lifecycle`) rather than fixing by hand.

## Check catalogue
| Check | Frequency | What to look for |
|---|---|---|
| Orphan transactions (paid at operator but not credited, or the reverse) | daily before 10:00 | mismatches by reconciliation key |
| "To verify" withdrawal queue | daily | query the operator by key |
| Duplicates and global wallet invariant | daily | sum of entries ≠ 0 |
| Operator float | daily | insufficient provision |
| Transit and suspense accounts | weekly and on every configuration change | hard-coded references, closing > 48 h |
| Tontines, pots, vaults: unpaid or failed recoveries | daily | failed recoveries first |
| Consolidated treasury position (wallets = assets) | daily | global gap |

## Report
Table: reference, amount in XOF, gap, age, proposed action, target deadline. Critical gaps (closing > 48 h, failed recovery) first. Fee calculations: skill `amounts-check`.

## Never
Edit a balance in the database, apply a rule listed as a "pending arbitration", resend an order with a new key.

## End of task
Log the run: `~/.claude/skills/skill-learning/learn.py log payment-reconciliation ok|partial|failed [--note …]`.
