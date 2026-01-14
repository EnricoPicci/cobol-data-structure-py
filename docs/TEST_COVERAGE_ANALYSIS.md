# Test Coverage Analysis

This document analyzes options for calculating and reporting test coverage in the COBOL Anonymizer project and proposes a recommended solution.

## Current State

The project already has basic coverage infrastructure in place:

| Component | Status | Details |
|-----------|--------|---------|
| pytest-cov | Installed | Version 7.0.0 |
| coverage.py | Installed | Version 7.13.1 |
| pyproject.toml config | Configured | Basic `[tool.coverage.run]` and `[tool.coverage.report]` |
| Makefile target | Available | `make test-cov` |
| Current coverage | **85%** | 608 tests, 2606 statements, 313 missed |

### Current Configuration

```toml
[tool.coverage.run]
source = ["src"]
branch = true

[tool.coverage.report]
exclude_lines = [
    "pragma: no cover",
    "def __repr__",
    "raise AssertionError",
    "raise NotImplementedError",
    "if __name__ == .__main__.:",
    "if TYPE_CHECKING:",
    "@(abc\\.)?abstractmethod",
]
```

---

## Coverage Options Analysis

### Option 1: Terminal-Only Reports (Current)

**Command:** `pytest --cov=src/cobol_anonymizer --cov-report=term-missing`

**Pros:**
- Simple, no additional files generated
- Immediate feedback in terminal
- Shows missing line numbers
- Low disk usage

**Cons:**
- No persistent report
- Difficult to share or review later
- No visual navigation of source code

**Best for:** Quick local development checks

---

### Option 2: HTML Reports

**Command:** `pytest --cov=src/cobol_anonymizer --cov-report=html`

**Pros:**
- Visual, interactive reports
- Click-through to see exact uncovered lines highlighted in source
- Easy to navigate large codebases
- Can be served locally or published

**Cons:**
- Generates ~2.5MB of files in `htmlcov/`
- Needs to be regenerated after each run
- Not suitable for CI artifacts without hosting

**Best for:** Detailed local analysis, code review preparation

---

### Option 3: XML Reports (Cobertura Format)

**Command:** `pytest --cov=src/cobol_anonymizer --cov-report=xml`

**Pros:**
- Standard format (Cobertura) supported by most CI systems
- GitHub Actions, GitLab CI, Jenkins all support it
- Can be used with coverage badges
- Machine-readable for automated checks

**Cons:**
- Not human-readable
- Requires additional tools to visualize

**Best for:** CI/CD integration, automated coverage gates

---

### Option 4: JSON Reports

**Command:** `pytest --cov=src/cobol_anonymizer --cov-report=json`

**Pros:**
- Machine-readable
- Easy to parse programmatically
- Can be used for custom reporting

**Cons:**
- Not directly viewable
- Less tooling support than XML

**Best for:** Custom integrations, data analysis

---

### Option 5: LCOV Reports

**Command:** `pytest --cov=src/cobol_anonymizer --cov-report=lcov`

**Pros:**
- Widely supported format
- Compatible with many visualization tools
- Can be uploaded to Codecov, Coveralls

**Cons:**
- Requires external services for best visualization

**Best for:** Third-party coverage services

---

### Option 6: Coverage Thresholds (Fail Below Minimum)

**Command:** `pytest --cov=src/cobol_anonymizer --cov-fail-under=80`

**Pros:**
- Enforces minimum coverage standards
- Prevents coverage regression
- Clear pass/fail for CI

**Cons:**
- Can be frustrating during rapid development
- May encourage gaming metrics over quality

**Best for:** Mature projects, CI enforcement

---

## Comparison Matrix

| Option | Local Dev | CI/CD | Visualization | Persistence | Effort |
|--------|-----------|-------|---------------|-------------|--------|
| Terminal | Excellent | Poor | Basic | None | None |
| HTML | Excellent | Medium | Excellent | Local | Low |
| XML | Poor | Excellent | Via tools | Yes | Low |
| JSON | Poor | Good | Custom | Yes | Low |
| LCOV | Poor | Excellent | Via services | Yes | Medium |
| Thresholds | Good | Excellent | N/A | N/A | None |

---

## Recommended Solution

### Hybrid Approach: Terminal + HTML + XML with Threshold

Implement a comprehensive coverage strategy that serves multiple use cases:

#### 1. Update pyproject.toml

```toml
[tool.coverage.run]
source = ["src"]
branch = true
parallel = true
relative_files = true

[tool.coverage.report]
exclude_lines = [
    "pragma: no cover",
    "def __repr__",
    "raise AssertionError",
    "raise NotImplementedError",
    "if __name__ == .__main__.:",
    "if TYPE_CHECKING:",
    "@(abc\\.)?abstractmethod",
]
fail_under = 80
show_missing = true
skip_covered = false

[tool.coverage.html]
directory = "htmlcov"
show_contexts = true

[tool.coverage.xml]
output = "coverage.xml"
```

#### 2. Update Makefile

```makefile
# Quick coverage check (terminal only)
test-cov:
	pytest --cov=src/cobol_anonymizer --cov-report=term-missing

# Full coverage report (all formats)
test-cov-full:
	pytest --cov=src/cobol_anonymizer \
		--cov-report=term-missing \
		--cov-report=html \
		--cov-report=xml

# Coverage with enforcement (for CI)
test-cov-ci:
	pytest --cov=src/cobol_anonymizer \
		--cov-report=xml \
		--cov-fail-under=80
```

#### 3. Update .gitignore

```gitignore
# Coverage artifacts
htmlcov/
coverage.xml
.coverage
.coverage.*
```

---

## Implementation Checklist

1. **pyproject.toml**: Add enhanced coverage configuration
2. **Makefile**: Add `test-cov-full` and `test-cov-ci` targets
3. **.gitignore**: Ensure coverage artifacts are ignored
4. **README.md**: Document coverage commands
5. **(Optional)** CI workflow: Add coverage step with threshold enforcement

---

## Coverage Improvement Targets

Based on current coverage analysis, focus areas for improvement:

| Module | Current | Target | Priority |
|--------|---------|--------|----------|
| cli.py | 65% | 80% | Medium |
| output/report.py | 61% | 80% | Medium |
| logging_config.py | 67% | 80% | Low |
| output/validator.py | 74% | 85% | Medium |
| core/utils.py | 77% | 85% | Low |

---

## Document History

- **Created:** 2026-01-14
- **Author:** Code analysis
- **Current Coverage:** 85% (608 tests)
