---
name: implement-linear
description: Use when implementing a Linear issue — fetches issue, validates labels, enters plan mode for approval, then executes implementation
---

# Implement Linear Issue

Implements a Linear issue end-to-end: fetch → validate → plan → approve → execute.

**Argument:** Linear issue identifier (e.g., `BE-2`, `FE-5`, `AI-12`)

## Phase 1 — Fetch & Validate

1. **Fetch the issue** using `mcp__linear__get_issue` with the identifier from `$ARGUMENTS`
2. **Check labels** — this is a hard gate:

| Label state | Action |
|------------|--------|
| Has `claude-ready` | Proceed to Phase 2 |
| Has `claude-blocked` | **STOP.** Print the issue title, status, and say: "Esta issue está bloqueada. Precisa de decisão humana antes de prosseguir." Do NOT continue. |
| Has neither | **STOP.** Print: "Esta issue não foi refinada. Adicione a label `claude-ready` após preencher o template PBI." Do NOT continue. |

3. **Extract from the issue description:**
   - Contexto (the why)
   - Critérios de aceite (the what — these become your acceptance tests)
   - Escopo técnico: o que está dentro / o que está fora
   - Notas para o agente (constraints, preferred libs, anti-patterns)

4. **Print a summary** to the user:
   ```
   Issue: [ID] — [Title]
   Team: [team name]
   Priority: [priority]
   Labels: [labels]
   Critérios de aceite: [count] items
   ```

## Phase 2 — Plan (MANDATORY)

**You MUST call `EnterPlanMode` here.** This is not optional.

In plan mode, do the following:

1. **Explore the codebase** — read relevant files mentioned in "Escopo técnico"
2. **Map the changes** — for each critério de aceite, identify:
   - Which files need to change
   - What the change looks like (function signatures, logic flow)
   - What tests to write
3. **Respect "O que está fora"** — if your plan touches anything listed as out of scope, remove it
4. **Write the plan** with this structure:

```markdown
# Plano: [ISSUE-ID] — [Title]

## Resumo
[1-2 sentences on what this plan does]

## Alterações

### 1. [file path]
- What changes and why

### 2. [file path]
- What changes and why

## Testes
- [ ] Test for critério de aceite 1
- [ ] Test for critério de aceite 2
- ...

## Fora do escopo (confirmado)
- [Items from "O que está fora" — confirming you won't touch these]

## Branch
`feature/[issue-id-lowercase]-[slug]`
```

5. **Call `ExitPlanMode`** — wait for user approval before proceeding.

**Do NOT write any code during this phase.** Read-only exploration.

## Phase 3 — Execute (after approval)

Only after the user approves the plan:

1. **Create the branch:**
   ```
   git checkout -b feature/[issue-id-lowercase]-[slug]
   ```
   Example: `feature/be-2-busca-por-documento`

2. **Implement** following the approved plan exactly:
   - Write tests FIRST (TDD when possible)
   - Then implementation
   - Run tests after each file change
   - Run lint (`ruff check` for Python)

3. **Final validation:**
   - All tests passing
   - Lint clean
   - Only files from the plan were touched (check with `git diff --stat`)

4. **Commit** with message format:
   ```
   feat|fix|chore: [description in english]

   Closes [ISSUE-ID]

   Co-Authored-By: Claude Opus 4.6 (1M context) <noreply@anthropic.com>
   ```

5. **Push and open PR:**
   ```
   git push -u origin feature/[issue-id-lowercase]-[slug]
   gh pr create --title "[description]" --body "..." --base main
   ```
   PR body must reference `Closes [ISSUE-ID]` for auto-close on merge.

6. **Update Linear issue** — move to `In Progress` using `mcp__linear__save_issue`:
   ```
   state: "In Progress"
   ```
   (GitHub integration should auto-move to In Review when PR opens, but set In Progress as fallback)

## Rules — No Exceptions

- **Never skip plan mode.** Even if the change looks trivial.
- **Never implement anything outside the approved plan.** If you discover something else needs to change, update the plan and ask for re-approval.
- **Never touch files listed in "O que está fora."**
- **Always run tests before committing.**
- **Branch naming:** always `feature/[issue-id]-[slug]`. No other format.

## Common Mistakes

| Mistake | Reality |
|---------|---------|
| "This is simple, I'll skip the plan" | Simple issues have hidden complexity. Plan anyway. |
| "I'll also fix this nearby code" | Out of scope. Create a new issue. |
| "Tests can come after" | Tests first. They validate your understanding. |
| "I'll use the Linear suggested branch name" | Use `feature/` prefix for consistent integration. |
