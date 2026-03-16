# Code Principles

Single source of truth for code quality standards. Referenced by CLAUDE.md, CodeRabbit, OpenSpec, and implementation subagents.

## Hard Rules (always enforce)

### 1. Single Responsibility
Every function and class does one thing. If you need "and" in the description, split it.

### 2. No Magic Values
All literals that aren't self-evident (0, 1, True, False, "") must be named constants.
```python
# Bad
if response.status_code == 429:
    await asyncio.sleep(60)

# Good
RATE_LIMIT_STATUS = 429
RATE_LIMIT_BACKOFF_SECONDS = 60
if response.status_code == RATE_LIMIT_STATUS:
    await asyncio.sleep(RATE_LIMIT_BACKOFF_SECONDS)
```

### 3. Descriptive Names
Names reveal intent. No abbreviations, no generic names (data, info, item, temp, result) in scopes longer than 3 lines. Use snake_case for functions/variables, PascalCase for classes.

### 4. Error Handling at Boundaries
All async operations and external API calls must handle errors explicitly. Use specific exception types, not bare `except`.
```python
# Bad
try:
    response = await client.post(url, json=payload)
except Exception:
    pass

# Good
try:
    response = await client.post(url, json=payload)
except httpx.TimeoutException as exc:
    raise ApifyTimeoutError(f"Actor run timed out: {exc}") from exc
except httpx.HTTPStatusError as exc:
    raise ApifyAPIError(f"API returned {exc.response.status_code}") from exc
```

### 5. Maximum 40 Lines Per Function
If a function exceeds 40 lines, decompose it. Extract helpers with clear names.

### 6. Maximum 3 Parameters
Functions with more than 3 parameters should accept a parameter object (dataclass or Pydantic model).

### 7. Maximum 3 Levels of Nesting
Use early returns, guard clauses, or extraction to reduce nesting depth.

### 8. No Duplicated Logic
If the same logic appears in more than one place (>5 similar lines), extract it.

### 9. YAGNI
Only build what the current task requires. No speculative abstractions, no "just in case" code.

### 10. Law of Demeter
Talk to direct collaborators only. No method chains reaching through 2+ objects.

### 11. Composition Over Inheritance
Combine objects via composition. Avoid class hierarchies.

## Soft Guidelines (prefer, but use judgment)

### 1. KISS
Pick the simplest solution that works. Three similar lines of code is better than a premature abstraction.

### 2. Deep Modules
Prefer simple interfaces that hide complex implementations. A function with 1-2 parameters that does substantial work internally is better than a thin wrapper.

### 3. Strategic Programming
Think about design before coding. Invest a bit more time now to produce cleaner code rather than working tactically and accumulating tech debt.

### 4. Comments Explain Why, Not What
Code should be self-documenting for the "what". Comments explain non-obvious reasoning, constraints, or trade-offs.

### 5. Fail Fast
Validate inputs at system boundaries. Return errors early rather than propagating bad state.

### 6. Immutability by Default
Prefer immutable data structures. Use `frozen=True` on Pydantic models where mutation isn't needed.

### 7. Type Everything
Use type annotations on all function signatures and class attributes. Let pyright catch errors at analysis time.

### 8. AAA Tests
Tests follow Arrange-Act-Assert. Each test covers one behavior. Test names describe expected behavior, not implementation details.
