# wealthgrabber

Wealthsimple Account Viewer CLI. Secure and simple tool to view your Wealthsimple account balances, transactions, and holdings from the command line.

## Features
- **Secure Authentication**: Uses system keyring to safely store credentials.
- **Account Listing**: Clear overview of all your accounts and their current values.
- **Transaction History**: View activities and transactions across your accounts.
- **Asset Positions**: Monitor your investment holdings with P&L tracking.
- **Multiple Output Formats**: Table (default), JSON, and CSV output for easy integration.
- **Privacy Focused**: No data is stored externally; everything runs locally.

## Installation

This project is managed with `uv`.

### Quick Install

Install the application globally so you can run `wealthgrabber` directly:

```bash
# Clone the repository
git clone <your-repo-url>
cd wealthgrabber

# Install the application
make install
```

After installation, you can use `wealthgrabber` directly without the `uv run` prefix:

```bash
wealthgrabber --help
wealthgrabber login
wealthgrabber list
```

### Development Setup

For development, you can use `uv sync` to set up the environment:

```bash
# Install dependencies and sync environment
uv sync

# Run with uv (if not globally installed)
uv run wealthgrabber --help
```

## Usage

The CLI provides five main commands: `login`, `logout`, `list`, `activities`, and `assets`.

All commands support the `--verbose/-v` flag for detailed status messages during execution.

### Authentication

#### Login
Authenticate with your Wealthsimple credentials. This supports 2FA and will cache your session securely.

```bash
wealthgrabber login
```

**Options:**
- `--force/-f`: Force a new login even if a valid session exists.
- `--username/-u EMAIL`: Email address to login with. If not provided, uses cached email or prompts.

#### Logout
Clear stored session and optionally cached email.

```bash
wealthgrabber logout
```

**Options:**
- `--username/-u EMAIL`: Email address to clear session for. If not provided, uses cached email.
- `--clear-email/-c`: Also clear the cached email address.

### Accounts

#### List Accounts
View a summary of your accounts with their current values.

```bash
wealthgrabber list
```

**Options:**
- `--show-zero/-z`: Show accounts with zero balance (default: true).
- `--liquid-only/-l`: Show only liquid accounts (excludes RRSP, LIRA, Private Equity, Private Credit).
- `--not-liquid/-n`: Show only non-liquid accounts (RRSP, LIRA, Private Equity, Private Credit).
- `--format/-f {table,json,csv}`: Output format (default: table).

**Examples:**
```bash
# View all accounts as table (default)
wealthgrabber list

# Show only liquid accounts in JSON format
wealthgrabber list --liquid-only --format json

# Show non-liquid accounts and hide zero balances
wealthgrabber list --not-liquid --no-show-zero
```

### Transactions

#### List Activities
View activities and transactions for your accounts.

```bash
wealthgrabber activities
```

**Options:**
- `--account/-a ACCOUNT_NUMBER`: Filter by account number (e.g., 'TFSA-001').
- `--dividends/-d`: Show only dividend transactions.
- `--limit/-n N`: Maximum number of activities per account (default: 50).
- `--format/-f {table,json,csv}`: Output format (default: table).

**Examples:**
```bash
# View recent activities as table (default)
wealthgrabber activities

# View only dividend transactions in JSON format
wealthgrabber activities --dividends --format json

# View last 100 activities from a specific account
wealthgrabber activities --account TFSA-001 --limit 100

# Export activities to CSV
wealthgrabber activities --format csv > activities.csv
```

### Investments

#### List Asset Positions
View all asset positions across your accounts with profit/loss tracking.

```bash
wealthgrabber assets
```

**Options:**
- `--account/-a ACCOUNT_NUMBER`: Filter by account number (e.g., 'TFSA-001').
- `--by-account/-b`: Show positions grouped by account instead of aggregated.
- `--format/-f {table,json,csv}`: Output format (default: table).

**Examples:**
```bash
# View all positions aggregated (default)
wealthgrabber assets

# View positions grouped by account
wealthgrabber assets --by-account

# View positions for a specific account in JSON format
wealthgrabber assets --account TFSA-001 --format json

# Export all positions to CSV
wealthgrabber assets --format csv > positions.csv
```

## Output Formats

### Table Format (Default)
Human-readable ASCII tables with formatting, alignment, and totals where applicable.

### JSON Format
Structured JSON output suitable for programmatic processing.

### CSV Format
Comma-separated values for import into spreadsheets or other tools.

## Development

If you are an AI assistant or a developer looking to contribute, please refer to [CLAUDE.md](CLAUDE.md) for detailed guidelines.
