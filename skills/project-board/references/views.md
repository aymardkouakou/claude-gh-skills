# Standard views

Created by `board.py views --apply` (name, layout and filter only: the API cannot set grouping or sorting). Existing names are never recreated; the default "View 1" is renamed "All items".

| View | Layout | Filter | Needs field | Manual setting (one click) |
|---|---|---|---|---|
| Board | board | `is:open` | | sort by Priority |
| Backlog | table | `is:open status:Todo` | | sort by Priority, then Created |
| Current iteration | board | `iteration:@current` | Iteration | |
| Roadmap | roadmap | `is:open` | Target date | dates: Target date; group by Parent issue |
| Epics | table | `label:epic` | | show Sub-issues progress |
| By epic | table | `is:open -label:epic` | | group by Parent issue |
| Without epic | table | `is:issue is:open no:parent-issue -label:epic` | | none |
| My work | table | `assignee:@me is:open` | | group by Status |
| Needs triage | table | `is:open no:priority` | Priority | sort by Created |
| In review | table | `is:pr is:open` | | show Reviewers, Linked pull requests |
| Blocked | table | `label:blocked is:open` | | sort by Updated |
| Bugs | table | `label:bug is:open` | | sort by Priority |
| Security | table | `label:security is:open` | | sort by Priority |
| Stale | table | `is:open updated:<@today-30d` | | sort by Updated (oldest first) |
| Done | table | `status:Done` | | sort by Closed (newest first) |

A view whose field is missing is skipped with a message: run `setup --apply` first.

## Built-in workflows (manual, Project → Workflows)
Item added to project → Status Todo; Item closed and Pull request merged → Status Done; Auto-add to project for this repository; Auto-archive items.

## Limits
- `Status` keeps GitHub's options (Todo, In Progress, Done): changing them resets item values.
- Field names `Type` and a few others are reserved by GitHub: the kind field is called `Kind`.
- Staleness in `report` uses the last update of the issue or pull request.
