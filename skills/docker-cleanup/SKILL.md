---
name: docker-cleanup
description: Clean Docker at the end of a task (unused images and build cache) without ever touching volumes. Use after a finished Docker or compose task, or for "nettoie docker", "libère de l'espace".
---

# Safe Docker cleanup

User convention: at the end of a Docker task, remove unused images and the build cache. Local machine only; never run on a shared or production server without approval.

```bash
docker system df             # before
docker image prune -a -f     # images not used by a container
docker builder prune -f      # build cache
docker system df             # after, to report the gain
docker volume ls | wc -l     # same before and after: volumes intact
```

## Do NOT
`docker volume prune`, `docker compose down -v`, any project `uninstall` or `clean --volumes`, unless the user explicitly asks **and** a backup exists (`backup-restore`).

## Report
Space reclaimed (before/after) and confirmation that the number of volumes is unchanged. The next start must re-pull removed images: say so if a stack is to be restarted.

## End of task
Log the run: `${CLAUDE_SKILL_DIR}/../skill-learning/learn.py log docker-cleanup ok|partial|failed [--note …]`.
