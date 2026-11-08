# Security audit - read-only commands

Adapt to the stack; every command below only reads. Cite `path:line`, never a value.

| Check | How to look |
| --- | --- |
| Routes and auth | Django: `grep -rn "urlpatterns\|permission_classes\|login_required"`; Express/Nest: `grep -rnE "@(Get|Post|Put|Delete)\|router\.(get\|post)\|@UseGuards"`; FastAPI: `grep -rn "APIRouter\|Depends("`. A route without an auth dependency is a candidate gap. |
| Ownership (IDOR) | For each endpoint taking an id, find where the record is loaded and confirm the owner is compared with the caller. |
| Default secrets | `python3 ${CLAUDE_SKILL_DIR}/../secrets-hygiene/scan_secrets.py .` (names and lines only); check `.env.example`, compose files for `changeme`, `admin`, empty values. |
| Exposed ports | `grep -rnE "^\s*-\s*\"?[0-9]+:[0-9]+" docker-compose*.yml`: a published port without `127.0.0.1:` is exposed. |
| HTTPS, CORS | `grep -rniE "cors|allow_origin|hsts|secure_ssl|Strict-Transport"`: wildcard origins with credentials are a gap. |
| Webhooks | Find the handler; confirm signature check before parsing, `hmac.compare_digest` or equivalent, timestamp window, idempotency key. |
| Queries | `grep -rnE "execute\(.*(\+\|%\|f\")"` and raw-SQL helpers: string-built SQL is a gap. |
| Logging | `grep -rniE "log.*(password\|token\|authorization\|card\|phone)"`. |
| Dependencies | `pip-audit`, `npm audit --omit=dev`, `composer audit`, `flutter pub outdated` when installed; otherwise report "not verified". |
| Backups | Look for a restore test in the runbook or CI; a backup never restored is "not verified". |

Severity: **critical** = exploitable now with data or funds at stake; **high** = exploitable with preconditions; **medium** = defence in depth.
