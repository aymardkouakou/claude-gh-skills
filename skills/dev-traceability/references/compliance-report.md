# Compliance report

On request or before an audit. One row per control: control, target standard (`standards-mapping.md`), result (**compliant / gap / not verified**), evidence (link or `path:line`), action. Distinguish "verified now" from "declared"; line numbers drift, so re-read the code before asserting.

State the limit: the report prepares evidence and certifies nothing.

Steering indicators (DORA): lead time, deployment frequency, change failure rate, time to restore. Compute them from merged PRs, releases and the change register; never estimate silently.
