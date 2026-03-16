# Project Guidelines

## Code Quality
Mandatory: SRP, no magic values, descriptive names, error handling on boundaries,
max 40 lines / 3 params / 3 nesting, no duplication, YAGNI, Law of Demeter, AAA tests.
Prefer: KISS (simplest solution wins), deep modules, composition over inheritance,
strategic programming. See CODE_PRINCIPLES.md for full details.

## Behavioral Rules
- Never guess versions, APIs, or config syntax from training knowledge — always research first (see Tool Workflow below).
- When a task feels too complex or requires touching many files, stop and ask before proceeding.
- When encountering an unfamiliar pattern in the codebase, use LSP (`goToDefinition`, `findReferences`) to understand it before modifying.
- Before creating any abstraction (interface, base class, wrapper), ask: does the current task require this? If not, don't build it.
- When stuck for more than 2 attempts at the same problem, say so explicitly rather than trying more variations.
- Prefer modifying existing patterns over introducing new ones.
- Always request local code review (`superpowers:code-reviewer`) before committing. Fix Critical and Important issues before proceeding.
- API token comes from `APIFY_API_TOKEN` env var only — never hardcode, never accept as constructor/function parameter.
- The Apify actor ID is `apify/google-trends-scraper` (URL path form: `apify~google-trends-scraper` with tilde).
- Apify REST API base URL: `https://api.apify.com/v2` — use as a named constant, not inline.
- Sync endpoint may return dataset items (JSON array) OR a run object (JSON object with `status: RUNNING`) on timeout — handle both.
- For sync actor runs use `/acts/{actorId}/run-sync-get-dataset-items` (up to 5min timeout). For longer runs, use async polling: POST `/acts/{actorId}/runs` then poll GET `/actor-runs/{runId}?waitForFinish=60`.
- All httpx calls must set explicit timeouts — never rely on defaults for external API calls.
- Pydantic models use `model_validate()` not the deprecated `parse_obj()`.

## Tool Workflow
- **Research**: Tavily (`tavily_search`, `tavily_extract`, `tavily_research`, `tavily_crawl`, `tavily_map`) + OpenMemory (`openmemory query`). Never use built-in WebSearch or WebFetch.
- **Spec**: `/opsx:new` -> `/opsx:ff` -> review -> implement -> `/opsx:verify` -> `/opsx:archive`
- **Plan & Execute**: `/superpowers:brainstorm` -> `/superpowers:write-plan` -> `/superpowers:execute-plan`
- **Review**: `superpowers:code-reviewer` before every commit. `coderabbit:code-review` for PR-level review.
- **Navigate**: LSP (`goToDefinition`, `findReferences`, `documentSymbol`, `workspaceSymbol`) — prefer over grep. Requires `ENABLE_LSP_TOOL=1`.
- **Test**: pytest + respx for unit/integration tests.

## OpenMemory Checkpoints
**Mandatory** — do not skip. Query before starting, store after completing.

| When | Action |
|------|--------|
| Before `/opsx:new`, `/opsx:ff`, `/fix` | `openmemory query "<topic> patterns" --limit 5` |
| After `/opsx:ff`, `/opsx:continue` | Store design summary and key decisions |
| During `/opsx:apply` (every 3-4 tasks) | Store progress, surprises, deviations |
| After `/opsx:verify` | Store findings (pass/fail, issues, fixes) |
| After `/opsx:archive` | Store completion record, patterns learned |
| After code review | Store non-obvious issues that apply beyond current PR |
| After `/fix` confirmed | Store error pattern, root cause, resolution |
| On `/resume` or session start | `openmemory query "recent context $REPO" --limit 5` |

## Workflows
- `/work-local "<description>"` — full pipeline from spec to PR
- `/resume` — pick up where you left off
- `/fix "<bug>"` — debug and fix workflow

## Documentation Updates
After every implementation, check and update: README.md, CHANGELOG.md, API docs, CLAUDE.md, OpenSpec specs.

## Git
Branch: `feature/short-desc` | Commit: `type(scope): desc` | PR against `main`
