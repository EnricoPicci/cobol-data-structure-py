# Funny Naming Schemes - Implementation Plan

## 1. Overview

### 1.1 Purpose

This document describes the implementation plan for adding alternative "funny" naming schemes to the COBOL anonymizer. Instead of generating dull numeric identifiers like `D00000001` or `SC00000001`, the tool will support human-readable, amusing alternatives like `FLUFFY-LLAMA-1` or `SPICY-TACO-1`.

### 1.2 Goals

| Goal | Description |
|------|-------------|
| **Deterministic** | Same input always maps to same funny name |
| **Configurable** | Multiple schemes selectable via CLI argument |
| **Backward Compatible** | Default behavior unchanged (numeric scheme) |
| **Valid COBOL** | Generated names comply with COBOL identifier rules |
| **Traceable** | Mappings file preserves original-to-funny name mapping |

### 1.3 Example Output

**Before (current numeric scheme):**
```cobol
       SC0000000000000000036            SECTION.
       IF C000000000106
       SET C000000000000000000000486 TO TRUE
       PERFORM VARYING D03370 FROM 1 BY 1
```

**After (animals scheme):**
```cobol
       FLUFFY-LLAMA-36                  SECTION.
       IF GRUMPY-PENGUIN-106
       SET WOBBLY-WOMBAT-486 TO TRUE
       PERFORM VARYING SNEAKY-OTTER-3370 FROM 1 BY 1
```

---

## 2. Available Naming Schemes

### 2.1 Scheme Definitions

| Scheme | CLI Value | Description | Example |
|--------|-----------|-------------|---------|
| **Numeric** | `numeric` | Current default: prefix + zero-padded counter | `D00000001` |
| **Animals** | `animals` | Adjective + animal combinations | `FLUFFY-LLAMA-1` |
| **Food** | `food` | Adjective + food combinations | `SPICY-TACO-1` |
| **Fantasy** | `fantasy` | Adjective + mythical creature combinations | `SNEAKY-DRAGON-1` |
| **Corporate** | `corporate` | Satirical business buzzword combinations | `AGILE-SYNERGY-1` |

### 2.2 Word Lists

#### Animals Scheme
```python
ADJECTIVES = ["FLUFFY", "GRUMPY", "SNEAKY", "WOBBLY", "DIZZY",
              "SLEEPY", "JUMPY", "FUZZY", "CHUNKY", "SPEEDY",
              "MIGHTY", "CLEVER", "SWIFT", "BRAVE", "SILLY"]

NOUNS = ["LLAMA", "PENGUIN", "WOMBAT", "PLATYPUS", "BADGER",
         "OTTER", "SLOTH", "KOALA", "LEMUR", "PANDA",
         "FERRET", "MARMOT", "BEAVER", "FALCON", "TOUCAN"]
```

#### Food Scheme
```python
ADJECTIVES = ["SPICY", "CRISPY", "SOGGY", "CHUNKY", "TANGY",
              "ZESTY", "GOOEY", "CRUNCHY", "SAVORY", "SIZZLY",
              "SMOKY", "CHEESY", "FRESH", "TOASTY", "SAUCY"]

NOUNS = ["TACO", "WAFFLE", "NOODLE", "PICKLE", "MUFFIN",
         "PRETZEL", "BURRITO", "DUMPLING", "PANCAKE", "NACHO",
         "BAGEL", "DONUT", "BISCUIT", "CRUMPET", "CHURRO"]
```

#### Fantasy Scheme
```python
ADJECTIVES = ["SNEAKY", "ANCIENT", "MIGHTY", "SLEEPY", "GRUMPY",
              "MYSTIC", "SHADOW", "FIERCE", "CLEVER", "NOBLE",
              "ARCANE", "GOLDEN", "SILVER", "WILD", "COSMIC"]

NOUNS = ["DRAGON", "GOBLIN", "UNICORN", "TROLL", "PHOENIX",
         "WIZARD", "SPHINX", "GRIFFIN", "OGRE", "FAIRY",
         "KRAKEN", "HYDRA", "CENTAUR", "CYCLOPS", "CHIMERA"]
```

#### Corporate Scheme
```python
ADJECTIVES = ["AGILE", "SYNERGY", "PIVOT", "DISRUPT", "LEVERAGE",
              "SCALABLE", "ROBUST", "DYNAMIC", "HOLISTIC", "LEAN",
              "PROACTIVE", "NIMBLE", "OPTIMAL", "ALIGNED", "ELASTIC"]

NOUNS = ["PARADIGM", "BANDWIDTH", "SILO", "ROADMAP", "STAKEHOLDER",
         "TOUCHPOINT", "PIPELINE", "MINDSHARE", "VERTICAL", "METRICS",
         "SYNERGY", "ECOSYSTEM", "PLATFORM", "FRAMEWORK", "CHANNEL"]
```

### 2.3 Deterministic Name Generation Algorithm

Names are generated deterministically by hashing the original identifier:

```python
import hashlib

def generate_funny_name(original_name: str, adjectives: List[str],
                        nouns: List[str], counter: int) -> str:
    """
    Generate a deterministic funny name from the original.

    The hash ensures the same original_name always produces
    the same adjective-noun combination.
    """
    # Hash the original name (case-insensitive)
    hash_bytes = hashlib.md5(original_name.upper().encode()).digest()
    hash_int = int.from_bytes(hash_bytes[:8], byteorder='big')

    # Select adjective and noun deterministically
    adj_idx = hash_int % len(adjectives)
    noun_idx = (hash_int // len(adjectives)) % len(nouns)

    adjective = adjectives[adj_idx]
    noun = nouns[noun_idx]

    # Format: ADJECTIVE-NOUN-COUNTER
    return f"{adjective}-{noun}-{counter}"
```

---

## 3. Architecture

### 3.1 Strategy Pattern

The implementation uses the Strategy Pattern to allow pluggable naming schemes:

```
┌─────────────────────────────────────────────────────────────────┐
│                     NAMING STRATEGY PATTERN                      │
├─────────────────────────────────────────────────────────────────┤
│                                                                  │
│  ┌──────────────────────┐                                       │
│  │  BaseNamingStrategy  │◄────── Abstract base class            │
│  │  (ABC)               │                                       │
│  └──────────┬───────────┘                                       │
│             │                                                    │
│    ┌────────┴────────┬────────────┬────────────┬──────────┐    │
│    ▼                 ▼            ▼            ▼          ▼    │
│ ┌──────┐      ┌──────────┐  ┌─────────┐  ┌─────────┐ ┌──────┐ │
│ │Numeric│     │  Animals │  │  Food   │  │ Fantasy │ │Corp. │ │
│ │Strategy│    │ Strategy │  │Strategy │  │Strategy │ │Strat.│ │
│ └──────┘      └──────────┘  └─────────┘  └─────────┘ └──────┘ │
│                                                                  │
│  ┌──────────────────────┐                                       │
│  │  get_naming_strategy │◄────── Factory function               │
│  │  (scheme) -> Strategy│                                       │
│  └──────────────────────┘                                       │
│                                                                  │
└─────────────────────────────────────────────────────────────────┘
```

### 3.2 Class Diagram

```python
class NamingScheme(str, Enum):
    """Available naming schemes."""
    NUMERIC = "numeric"
    ANIMALS = "animals"
    FOOD = "food"
    FANTASY = "fantasy"
    CORPORATE = "corporate"


class BaseNamingStrategy(ABC):
    """Abstract base class for naming strategies."""

    @abstractmethod
    def generate_name(
        self,
        original_name: str,
        id_type: IdentifierType,
        counter: int,
        target_length: int
    ) -> str:
        """Generate an anonymized name."""
        pass

    @abstractmethod
    def get_scheme(self) -> NamingScheme:
        """Return the scheme identifier."""
        pass


class NumericNamingStrategy(BaseNamingStrategy):
    """Current numeric naming: D00000001, SC00000001"""

    def generate_name(self, original_name, id_type, counter, target_length):
        prefix = NAME_PREFIXES[id_type]
        available_digits = target_length - len(prefix)
        return f"{prefix}{str(counter).zfill(available_digits)}"

    def get_scheme(self) -> NamingScheme:
        return NamingScheme.NUMERIC


class WordBasedNamingStrategy(BaseNamingStrategy):
    """Base class for adjective-noun naming schemes."""

    ADJECTIVES: List[str] = []
    NOUNS: List[str] = []

    def generate_name(self, original_name, id_type, counter, target_length):
        # Deterministic hash-based selection
        hash_val = self._hash_name(original_name)
        adj = self.ADJECTIVES[hash_val % len(self.ADJECTIVES)]
        noun = self.NOUNS[(hash_val // len(self.ADJECTIVES)) % len(self.NOUNS)]

        base_name = f"{adj}-{noun}-{counter}"

        # Truncate if exceeds target length (max 30 for COBOL)
        if len(base_name) > target_length:
            # Shorten adjective/noun but keep counter
            return self._truncate_name(adj, noun, counter, target_length)

        return base_name

    def _hash_name(self, name: str) -> int:
        """Generate deterministic hash from name."""
        hash_bytes = hashlib.md5(name.upper().encode()).digest()
        return int.from_bytes(hash_bytes[:8], byteorder='big')

    def _truncate_name(self, adj, noun, counter, max_len):
        """Truncate name to fit within max length."""
        counter_str = str(counter)
        # Reserve space for: ADJ- + NOUN- + counter
        available = max_len - len(counter_str) - 2  # 2 hyphens
        adj_len = available // 2
        noun_len = available - adj_len
        return f"{adj[:adj_len]}-{noun[:noun_len]}-{counter_str}"
```

---

## 4. File Changes

### 4.1 New File: `src/cobol_anonymizer/generators/naming_schemes.py`

Complete new module containing:
- `NamingScheme` enum
- `BaseNamingStrategy` abstract class
- `NumericNamingStrategy` class (refactored from current logic)
- `WordBasedNamingStrategy` base class
- `AnimalNamingStrategy` class
- `FoodNamingStrategy` class
- `FantasyNamingStrategy` class
- `CorporateNamingStrategy` class
- `get_naming_strategy(scheme: NamingScheme)` factory function

### 4.2 Modify: `src/cobol_anonymizer/generators/name_generator.py`

```python
# Add import
from cobol_anonymizer.generators.naming_schemes import (
    NamingScheme,
    get_naming_strategy,
    BaseNamingStrategy
)

@dataclass
class NameGeneratorConfig:
    preserve_length: bool = True
    min_length: int = 4
    max_length: int = MAX_IDENTIFIER_LENGTH
    seed: Optional[int] = None
    naming_scheme: NamingScheme = NamingScheme.NUMERIC  # NEW FIELD


@dataclass
class NameGenerator:
    config: NameGeneratorConfig = field(default_factory=NameGeneratorConfig)
    _counters: Dict[IdentifierType, int] = field(default_factory=dict)
    _generated_names: Set[str] = field(default_factory=set)
    _strategy: BaseNamingStrategy = field(init=False)  # NEW FIELD

    def __post_init__(self):
        # Initialize the naming strategy based on config
        self._strategy = get_naming_strategy(self.config.naming_scheme)
        if self.config.seed is not None:
            self._random = random.Random(self.config.seed)

    def generate(self, original_name: str, id_type: IdentifierType,
                 target_length: Optional[int] = None) -> str:
        # ... existing length calculation ...

        counter = self._get_next_counter(id_type)

        # Delegate to strategy
        for attempt in range(max_retries):
            name = self._strategy.generate_name(
                original_name, id_type, counter, length
            )

            if self._is_valid_name(name):
                self._generated_names.add(name.upper())
                return name

            counter = self._get_next_counter(id_type)

        raise RuntimeError(f"Could not generate valid name after {max_retries} attempts")
```

### 4.3 Modify: `src/cobol_anonymizer/config.py`

```python
# Add import
from cobol_anonymizer.generators.naming_schemes import NamingScheme

@dataclass
class Config:
    # ... existing fields ...

    # Name generation
    seed: Optional[int] = None
    naming_scheme: NamingScheme = NamingScheme.NUMERIC  # NEW FIELD

    # ... rest of class ...

    def to_dict(self) -> Dict[str, Any]:
        data = {}
        for key, value in asdict(self).items():
            if isinstance(value, Path):
                data[key] = str(value)
            elif isinstance(value, NamingScheme):  # NEW
                data[key] = value.value
            # ... rest of serialization ...
        return data

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "Config":
        # ... existing path conversions ...

        # Convert naming_scheme string to enum
        if "naming_scheme" in data and isinstance(data["naming_scheme"], str):
            data["naming_scheme"] = NamingScheme(data["naming_scheme"])

        # ... rest of method ...
```

### 4.4 Modify: `src/cobol_anonymizer/cli.py`

```python
# Add to create_parser() function:
parser.add_argument(
    "--naming-scheme",
    type=str,
    choices=["numeric", "animals", "food", "fantasy", "corporate"],
    default="numeric",
    help="Naming scheme for anonymized identifiers: "
         "numeric (default, e.g., D00000001), "
         "animals (e.g., FLUFFY-LLAMA-1), "
         "food (e.g., SPICY-TACO-1), "
         "fantasy (e.g., SNEAKY-DRAGON-1), "
         "corporate (e.g., AGILE-SYNERGY-1)",
)

# Add to args_to_config() function:
from cobol_anonymizer.generators.naming_schemes import NamingScheme

def args_to_config(args: argparse.Namespace) -> Config:
    config = create_default_config()
    # ... existing assignments ...
    config.naming_scheme = NamingScheme(args.naming_scheme)  # NEW
    # ... rest of function ...
```

### 4.5 Modify: `src/cobol_anonymizer/core/mapper.py`

```python
# Add import
from cobol_anonymizer.generators.naming_schemes import NamingScheme

@dataclass
class MappingTable:
    _mappings: Dict[str, MappingEntry] = field(default_factory=dict)
    _external_names: Set[str] = field(default_factory=set)
    _generator: NameGenerator = field(default_factory=NameGenerator)
    _preserve_length: bool = True
    _naming_scheme: NamingScheme = NamingScheme.NUMERIC  # NEW FIELD

    def __post_init__(self):
        config = NameGeneratorConfig(
            preserve_length=self._preserve_length,
            naming_scheme=self._naming_scheme,  # Pass scheme to generator
        )
        self._generator = NameGenerator(config=config)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "generated_at": datetime.now().isoformat(),
            "naming_scheme": self._naming_scheme.value,  # NEW: persist scheme
            "mappings": [e.to_dict() for e in self._mappings.values()],
            "external_names": list(self._external_names),
            "generator_state": {
                k.name: v for k, v in self._generator.get_counter_state().items()
            },
        }

    @classmethod
    def load_from_file(cls, path: Path) -> "MappingTable":
        with open(path, 'r') as f:
            data = json.load(f)

        # Restore naming scheme
        scheme_value = data.get("naming_scheme", "numeric")
        naming_scheme = NamingScheme(scheme_value)

        table = cls(_naming_scheme=naming_scheme)

        # ... rest of loading logic ...

        return table
```

### 4.6 New File: `tests/test_naming_schemes.py`

Unit tests for all naming schemes:

```python
import pytest
from cobol_anonymizer.generators.naming_schemes import (
    NamingScheme,
    get_naming_strategy,
    NumericNamingStrategy,
    AnimalNamingStrategy,
    FoodNamingStrategy,
    FantasyNamingStrategy,
    CorporateNamingStrategy,
)
from cobol_anonymizer.core.classifier import IdentifierType


class TestNamingSchemes:
    """Tests for naming scheme strategies."""

    def test_numeric_scheme_format(self):
        """Numeric scheme produces PREFIX + zero-padded counter."""
        strategy = get_naming_strategy(NamingScheme.NUMERIC)
        name = strategy.generate_name("WS-FIELD", IdentifierType.DATA_NAME, 1, 10)
        assert name.startswith("D")
        assert name[1:].isdigit()

    def test_animals_scheme_format(self):
        """Animals scheme produces ADJECTIVE-NOUN-counter format."""
        strategy = get_naming_strategy(NamingScheme.ANIMALS)
        name = strategy.generate_name("WS-FIELD", IdentifierType.DATA_NAME, 1, 30)
        parts = name.split("-")
        assert len(parts) == 3
        assert parts[2].isdigit()

    def test_deterministic_mapping(self):
        """Same input always produces same adjective-noun combination."""
        strategy = get_naming_strategy(NamingScheme.ANIMALS)
        name1 = strategy.generate_name("CUSTOMER-NAME", IdentifierType.DATA_NAME, 1, 30)
        name2 = strategy.generate_name("CUSTOMER-NAME", IdentifierType.DATA_NAME, 1, 30)
        assert name1 == name2

    def test_different_inputs_different_names(self):
        """Different inputs produce different combinations."""
        strategy = get_naming_strategy(NamingScheme.ANIMALS)
        name1 = strategy.generate_name("FIELD-A", IdentifierType.DATA_NAME, 1, 30)
        name2 = strategy.generate_name("FIELD-B", IdentifierType.DATA_NAME, 1, 30)
        # Counter is same, but adjective-noun should differ
        assert name1.rsplit("-", 1)[0] != name2.rsplit("-", 1)[0]

    def test_case_insensitive(self):
        """Hash is case-insensitive (COBOL standard)."""
        strategy = get_naming_strategy(NamingScheme.FOOD)
        name_upper = strategy.generate_name("MY-FIELD", IdentifierType.DATA_NAME, 1, 30)
        name_lower = strategy.generate_name("my-field", IdentifierType.DATA_NAME, 1, 30)
        assert name_upper == name_lower

    def test_max_length_respected(self):
        """Generated names respect COBOL 30-char limit."""
        for scheme in NamingScheme:
            strategy = get_naming_strategy(scheme)
            name = strategy.generate_name("TEST", IdentifierType.DATA_NAME, 99999, 30)
            assert len(name) <= 30

    def test_valid_cobol_identifier(self):
        """Generated names are valid COBOL identifiers."""
        for scheme in NamingScheme:
            strategy = get_naming_strategy(scheme)
            name = strategy.generate_name("TEST", IdentifierType.DATA_NAME, 1, 30)
            # Must start with letter
            assert name[0].isalpha()
            # Cannot end with hyphen
            assert not name.endswith("-")
            # Only alphanumeric and hyphens
            assert all(c.isalnum() or c == "-" for c in name)

    def test_all_schemes_available(self):
        """All defined schemes can be instantiated."""
        for scheme in NamingScheme:
            strategy = get_naming_strategy(scheme)
            assert strategy is not None
            assert strategy.get_scheme() == scheme
```

---

## 5. Mappings File Format

### 5.1 Updated JSON Structure

The `mappings.json` file includes the naming scheme used:

```json
{
  "generated_at": "2025-01-13T14:30:00.123456",
  "naming_scheme": "animals",
  "mappings": [
    {
      "original_name": "WS-CUSTOMER-NAME",
      "anonymized_name": "GRUMPY-PENGUIN-1",
      "id_type": "DATA_NAME",
      "is_external": false,
      "first_seen_file": "CUSTMGMT.cob",
      "first_seen_line": 127,
      "occurrence_count": 8
    },
    {
      "original_name": "CALCULATE-INTEREST",
      "anonymized_name": "FLUFFY-WOMBAT-1",
      "id_type": "PARAGRAPH_NAME",
      "is_external": false,
      "first_seen_file": "INTEREST.cob",
      "first_seen_line": 342,
      "occurrence_count": 3
    },
    {
      "original_name": "MAIN-PROCESS",
      "anonymized_name": "WOBBLY-LLAMA-1",
      "id_type": "SECTION_NAME",
      "is_external": false,
      "first_seen_file": "MAINPROG.cob",
      "first_seen_line": 200,
      "occurrence_count": 1
    }
  ],
  "external_names": [
    "MSMFS-GRP",
    "MSMFS-MODNAME"
  ],
  "generator_state": {
    "DATA_NAME": 45,
    "PARAGRAPH_NAME": 12,
    "SECTION_NAME": 4,
    "CONDITION_NAME": 23
  }
}
```

### 5.2 Backward Compatibility

- Files generated without `naming_scheme` field default to `"numeric"`
- Loading old mappings files works without changes
- The scheme is only informational; actual mappings are authoritative

---

## 6. CLI Usage Examples

### 6.1 Basic Usage

```bash
# Default numeric scheme (backward compatible)
cobol-anonymize -i input/ -o output/

# Use animal names
cobol-anonymize -i input/ -o output/ --naming-scheme animals

# Use food names
cobol-anonymize -i input/ -o output/ --naming-scheme food

# Use fantasy creature names
cobol-anonymize -i input/ -o output/ --naming-scheme fantasy

# Use corporate buzzwords (for ironic effect)
cobol-anonymize -i input/ -o output/ --naming-scheme corporate
```

### 6.2 With Mapping File

```bash
# Generate with animals scheme and save mappings
cobol-anonymize -i input/ -o output/ \
    --naming-scheme animals \
    --mapping-file mappings.json

# Later: load existing mappings (scheme is preserved)
cobol-anonymize -i input/ -o output/ \
    --load-mappings mappings.json
```

### 6.3 Help Output

```
$ cobol-anonymize --help
...
  --naming-scheme {numeric,animals,food,fantasy,corporate}
                        Naming scheme for anonymized identifiers:
                        numeric (default, e.g., D00000001),
                        animals (e.g., FLUFFY-LLAMA-1),
                        food (e.g., SPICY-TACO-1),
                        fantasy (e.g., SNEAKY-DRAGON-1),
                        corporate (e.g., AGILE-SYNERGY-1)
...
```

---

## 7. Sample Transformations

### 7.1 Numeric Scheme (Default)

| Original | Anonymized |
|----------|------------|
| `WS-CUSTOMER-NAME` | `D0000000000000001` |
| `CALCULATE-INTEREST` | `PA00000000000001` |
| `MAIN-PROCESS` | `SC00000000000001` |
| `DATA-VALID` | `C0000000000000001` |

### 7.2 Animals Scheme

| Original | Anonymized |
|----------|------------|
| `WS-CUSTOMER-NAME` | `GRUMPY-PENGUIN-1` |
| `CALCULATE-INTEREST` | `FLUFFY-WOMBAT-1` |
| `MAIN-PROCESS` | `WOBBLY-LLAMA-1` |
| `DATA-VALID` | `SNEAKY-OTTER-1` |

### 7.3 Food Scheme

| Original | Anonymized |
|----------|------------|
| `WS-CUSTOMER-NAME` | `SPICY-TACO-1` |
| `CALCULATE-INTEREST` | `CRISPY-WAFFLE-1` |
| `MAIN-PROCESS` | `ZESTY-NOODLE-1` |
| `DATA-VALID` | `CHUNKY-MUFFIN-1` |

### 7.4 Fantasy Scheme

| Original | Anonymized |
|----------|------------|
| `WS-CUSTOMER-NAME` | `ANCIENT-DRAGON-1` |
| `CALCULATE-INTEREST` | `MYSTIC-UNICORN-1` |
| `MAIN-PROCESS` | `SHADOW-PHOENIX-1` |
| `DATA-VALID` | `FIERCE-GOBLIN-1` |

### 7.5 Corporate Scheme

| Original | Anonymized |
|----------|------------|
| `WS-CUSTOMER-NAME` | `AGILE-PARADIGM-1` |
| `CALCULATE-INTEREST` | `SYNERGY-PIPELINE-1` |
| `MAIN-PROCESS` | `LEVERAGE-ROADMAP-1` |
| `DATA-VALID` | `DISRUPT-METRICS-1` |

---

## 8. Implementation Checklist

### 8.1 Files to Create

- [ ] `src/cobol_anonymizer/generators/naming_schemes.py`
- [ ] `tests/test_naming_schemes.py`

### 8.2 Files to Modify

- [ ] `src/cobol_anonymizer/generators/name_generator.py`
  - Add `naming_scheme` to `NameGeneratorConfig`
  - Initialize strategy in `NameGenerator.__post_init__`
  - Delegate name generation to strategy
- [ ] `src/cobol_anonymizer/config.py`
  - Add `naming_scheme` field to `Config`
  - Update `to_dict()` and `from_dict()` for serialization
- [ ] `src/cobol_anonymizer/cli.py`
  - Add `--naming-scheme` argument
  - Update `args_to_config()` to handle scheme
- [ ] `src/cobol_anonymizer/core/mapper.py`
  - Add `_naming_scheme` field to `MappingTable`
  - Pass scheme to `NameGenerator`
  - Include scheme in `to_dict()` output
  - Restore scheme in `load_from_file()`

### 8.3 Testing

- [ ] Unit tests for each naming strategy
- [ ] Determinism tests (same input → same output)
- [ ] Case-insensitivity tests
- [ ] Length constraint tests (max 30 chars)
- [ ] COBOL identifier validity tests
- [ ] Integration test with full anonymization pipeline
- [ ] Mapping file round-trip test

---

## 9. Future Enhancements

### 9.1 Potential Additional Schemes

- **Colors**: `BRIGHT-PURPLE-1`, `DARK-ORANGE-1`
- **Space**: `COSMIC-NEBULA-1`, `STELLAR-QUASAR-1`
- **Music**: `JAZZY-PIANO-1`, `FUNKY-GUITAR-1`
- **Weather**: `STORMY-CLOUD-1`, `SUNNY-BREEZE-1`

### 9.2 Custom Word Lists

Allow users to provide custom adjective/noun lists via configuration file:

```json
{
  "naming_scheme": "custom",
  "custom_adjectives": ["HAPPY", "SAD", "FAST", "SLOW"],
  "custom_nouns": ["CAT", "DOG", "BIRD", "FISH"]
}
```

### 9.3 Themed Schemes per Identifier Type

Different schemes for different identifier types:
- Data names: Animals
- Paragraphs: Actions (`RUNNING`, `JUMPING`)
- Sections: Locations (`KITCHEN`, `GARDEN`)
