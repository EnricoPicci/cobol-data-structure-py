# CLAUDE.md Update Recommendations

This document evaluates the current `.claude/CLAUDE.md` file and identifies updates needed to reflect the current state of the project.

## Summary

| Section | Change Type | Priority |
|---------|-------------|----------|
| Quick Commands | Update commands | HIGH |
| Project Structure | Fix counts, add files | MEDIUM |
| Testing Conventions | Add coverage note | MEDIUM |
| Code Style | Add ruff rules | LOW |
| Adding a New Naming Scheme | Fix steps | MEDIUM |

**Total: 5 changes recommended**

---

## Detailed Recommendations

### 1. Quick Commands Section

**Priority:** HIGH

**Current:**
```bash
# Run tests with coverage
pytest --cov=src/cobol_anonymizer
```

**Issue:** Coverage is now automatic when running `pytest` (configured in `pyproject.toml` addopts). The Makefile commands are also missing.

**Recommended change:**
```bash
# Run all tests (coverage included automatically)
pytest

# Run all checks (format, lint, typecheck, test)
make all

# Generate HTML coverage report
make test-cov
```

**Reason:** The project now has a Makefile that standardizes development commands. Coverage reporting is automatic via pytest's `addopts` configuration, so the old explicit command is misleading and redundant.

---

### 2. Project Structure Section

**Priority:** MEDIUM

**Current:**
```
tests/              # Comprehensive pytest suite (16 test files)
docs/               # Design docs: DESIGN.md, IMPLEMENTATION_PLAN.md
```

**Issues:**
- Test file count is incorrect (15 files, not 16)
- docs/ now contains 8 markdown files, not 2
- Missing mention of new project organization files (Makefile, README.md, etc.)

**Recommended change:**
```
tests/              # Comprehensive pytest suite
docs/               # Documentation (design, plans, analysis)
Makefile            # Development commands (make help for list)
README.md           # User documentation
CONTRIBUTING.md     # Contributor guidelines
```

**Reason:** Accuracy matters for AI assistants. The new project organization files are important for developers to know about.

---

### 3. Testing Conventions Section

**Priority:** MEDIUM

**Current:**
```bash
# All tests
pytest

# With verbose output
pytest -v
```

**Issue:** Doesn't mention that coverage reporting is now automatic, or the Makefile targets available.

**Recommended change:**
```bash
# All tests (coverage report included automatically)
pytest

# All tests with HTML coverage report
make test-cov

# Run all checks (format, lint, typecheck, test)
make all
```

**Reason:** Developers should know that coverage is always reported without needing extra flags. The Makefile provides a standardized interface.

---

### 4. Code Style Section

**Priority:** LOW

**Current:**
```
- **Linter**: Ruff (line-length: 100)
```

**Issue:** Doesn't mention the specific ruff rules that are enabled.

**Recommended change:**
```
- **Linter**: Ruff (line-length: 100, rules: E, W, F, I, B, C4, UP)
```

**Reason:** Helps developers understand what linting rules are enforced, particularly:
- `I` = isort (import sorting)
- `B` = flake8-bugbear (common bugs)
- `UP` = pyupgrade (Python upgrade suggestions)

---

### 5. Common Tasks > Adding a New Naming Scheme

**Priority:** MEDIUM

**Current:**
```
1. Add scheme to `NamingScheme` enum in `generators/naming_schemes.py`
2. Add word lists (adjectives + nouns) if word-based
3. Implement generation logic in `NameGenerator`
4. Add tests in `tests/test_naming_schemes.py`
```

**Issue:** Step 3 is inaccurate. The actual implementation pattern uses Strategy classes registered in a registry, not direct implementation in `NameGenerator`.

**Recommended change:**
```
1. Add scheme to `NamingScheme` enum in `generators/naming_schemes.py`
2. Create a new strategy class extending `WordBasedNamingStrategy` or `BaseNamingStrategy`
3. Add word lists (adjectives + nouns) if word-based
4. Register in `_STRATEGY_REGISTRY`
5. Add tests in `tests/test_naming_schemes.py`
```

**Reason:** Matches the actual Strategy Pattern implementation in the codebase. Incorrect instructions would lead to confusion.

---

## Document History

- **Created:** 2026-01-14
- **Author:** Code analysis
- **Source:** Comparison of `.claude/CLAUDE.md` with current project state
