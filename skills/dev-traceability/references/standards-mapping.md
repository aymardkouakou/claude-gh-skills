# Controls ↔ standards mapping

Indicative alignment, to be validated with the quality manager or the auditor. Clause numbers refer to the cited standards; check the applicable edition before reusing them in a file.

| Applied control | ISO/IEC 27001:2022 (Annex A) | ISO 9001:2015 | ISO/IEC/IEEE 12207 | ITIL 4 / SOC 2 |
|---|---|---|---|---|
| Documented secure development lifecycle (this skill + PR template) | A.8.25 | 8.3 | development processes | SOC 2 CC8.1 |
| Requirements identified and traced to tests (RTM) | A.8.26 | 8.3.3, 8.3.4 | requirements, verification | n/a |
| Secure coding, independent code review | A.8.28 | 8.3.4 | implementation, review | CC8.1 |
| Security and acceptance testing before delivery | A.8.29 | 8.3.4, 8.6 | verification, validation | CC8.1 |
| Separate environments, no real data in tests | A.8.31, A.8.33 | n/a | n/a | CC6.1 |
| Change management (record, approval, rollback) | A.8.32 | 8.5.6 | configuration management | ITIL change enablement; CC8.1 |
| Segregation of duties (author ≠ approver) | A.5.3 | n/a | n/a | CC5.1 |
| Logging and retained evidence | A.8.15 | 7.5.3 | records | CC7.2 |
| Vulnerability and dependency management | A.8.8 | n/a | n/a | CC7.1 |
| Incident handling and emergency fix | A.5.24 to A.5.27 | 10.2 | n/a | ITIL incident; CC7.4 |
| Documented, versioned information | A.5.37 | 7.5 | documentation | n/a |

## Limits
- This table is neither a declaration of conformity nor a certification.
- Local legal obligations (data protection, sector regulator requirements) are additional and not covered here: read them in the project's procedures.
