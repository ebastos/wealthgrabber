# wealthgrabber - Agent Guide

This document contains context, conventions, and instructions for AI agents working on the `wealthgrabber` codebase.


## Project Overview
`wealthgrabber` is a Python CLI application for wealth management operations. It appears to interface with external services using `ws-api` and `requests`, and handles authentication securely via `keyring`.

### Architecture
- **Root**: `src/wealthgrabber`
- **Entry Point**: `src/wealthgrabber/cli.py` (exposed as `wealthgrabber` script)
- **Authentication**: `src/wealthgrabber/auth.py`
- **Core Logic**: `src/wealthgrabber/accounts.py`
- **Dependencies**: Managed via `uv` (standard `pyproject.toml`).

## Development Environment
- **Package Manager**: `uv`
- **Python Version**: >=3.12

### Key Commands
- **Install/Sync**: `uv sync`
- **Run App**: `uv run wealthgrabber --help` or `uv run python -m wealthgrabber`
- **Locate Package**: `uv run python -c "import wealthgrabber; print(wealthgrabber.__file__)"`

## Testing & Quality
- **Test Runner**: `pytest`
- **Coverage**: `pytest-cov` is configured.
- **Commands**:
    - Run all tests: `uv run pytest`
    - Run specific test: `uv run pytest tests/test_auth.py`
    - Check types (recommended): `uv run mypy .`
    - Lint/Format (recommended): `uv run ruff check .`

## Conventions
- **Style**: Modern Python (3.12+). Use type hints for all function signatures.
- **CLI Framework**: `typer` is used for command-line interactions.
- **Imports**: Absolute imports from `wealthgrabber` package (e.g., `from wealthgrabber.auth import ...`).
- **Async**: Use `async`/`await` where I/O bound operations occur (implied by `ws-api`).

## File Structure
```
src/wealthgrabber/
├── __init__.py
├── __main__.py
├── auth.py              # Authentication (keyring)
├── models.py            # Data models (AccountData, ActivityData, PositionData)
├── formatters.py        # Output formatters (Table, JSON, CSV)
├── accounts.py          # Account management logic
├── activities.py        # Activity/transaction logic
├── assets.py            # Asset position logic
├── cli.py               # Typer CLI application
tests/                   # Pytest suite
pyproject.toml           # Project configuration
```

## Architecture: Three-Layer Output Pattern

The application follows a clean three-layer architecture for data retrieval and output:

### Layer 1: Data Retrieval
Functions in each module (`accounts.py`, `activities.py`, `assets.py`) fetch and transform API data:
- **`get_accounts_data()`** - Fetches accounts and returns `list[AccountData]`
- **`get_activities_data()`** - Fetches activities and returns `list[ActivityData]`
- **`get_assets_data()`** - Fetches positions and returns `list[PositionData]`

These functions handle:
- API calls and error handling
- Data transformation (dicts → dataclasses)
- Filtering and aggregation logic
- Enhancement (e.g., security name lookups)

### Layer 2: Data Models
`models.py` defines simple, serializable dataclasses:
- **`AccountData`** - `description`, `number`, `value`, `currency`
- **`ActivityData`** - `date`, `activity_type`, `description`, `amount`, `currency`, `sign`, `account_label`
- **`PositionData`** - `symbol`, `name`, `quantity`, `market_value`, `book_value`, `currency`, `pnl`, `pnl_pct`, `account_label`

### Layer 3: Formatters
`formatters.py` implements output formatters using a protocol-based design:

**`FormatterProtocol`** - Interface for all formatters with methods:
- `format_accounts(accounts: Sequence[AccountData]) -> str`
- `format_activities(activities: Sequence[ActivityData]) -> str`
- `format_positions(positions: Sequence[PositionData], show_totals: bool, group_label: Optional[str]) -> str`

**Concrete Implementations:**
- **`TableFormatter`** - ASCII tables with borders, alignment, and totals (default)
- **`JsonFormatter`** - JSON arrays with optional totals wrapper
- **`CsvFormatter`** - CSV format with headers and optional totals row

**Factory:** `get_formatter(format_type: str) -> FormatterProtocol`

### Output Flow
```
CLI Command (with --format option)
    ↓
get_*_data() retrieves and transforms data
    ↓
Data models (AccountData, ActivityData, PositionData)
    ↓
get_formatter(format_type) selects formatter
    ↓
formatter.format_*() converts to output string
    ↓
print(output) to stdout
```

## CLI Usage

All commands support `--format` option with choices: `table` (default), `json`, `csv`

```bash
# Table format (default)
wealthgrabber list
wealthgrabber activities
wealthgrabber assets

# JSON format
wealthgrabber list --format json
wealthgrabber activities --format json --dividends
wealthgrabber assets --format json --by-account

# CSV format
wealthgrabber list --format csv > accounts.csv
wealthgrabber activities --format csv > activities.csv
wealthgrabber assets --format csv > assets.csv
```

## Adding New Output Formats

To add a new output format (e.g., XML):

1. Create formatter class implementing `FormatterProtocol`:
   ```python
   class XmlFormatter:
       def format_accounts(self, accounts: Sequence[AccountData]) -> str:
           # XML formatting logic
           ...
   ```

2. Register in `get_formatter()`:
   ```python
   formatters = {
       "table": TableFormatter(),
       "json": JsonFormatter(),
       "csv": CsvFormatter(),
       "xml": XmlFormatter(),  # New!
   }
   ```

3. Add to `OutputFormat` enum in `cli.py`:
   ```python
   class OutputFormat(str, Enum):
       table = "table"
       json = "json"
       csv = "csv"
       xml = "xml"  # New!
   ```

No other changes needed - data retrieval and CLI plumbing remain the same.

## PR Instructions
- Ensure `uv run pytest` passes before finishing.
- Keep `AGENTS.md` updated if new tools or patterns are introduced.
