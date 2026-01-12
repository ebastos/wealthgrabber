from ws_api import WealthsimpleAPI

from .formatters import get_formatter
from .models import AccountData


def _extract_account_value(account: dict) -> tuple[float, str]:
    """Extract account value and currency from account data.

    Args:
        account: Account data dict from API

    Returns:
        Tuple of (value, currency)
    """
    financials = account.get("financials", {})
    net_liq = financials.get("currentCombined", {}).get("netLiquidationValue", {})
    value = float(net_liq.get("amount", 0))
    currency = net_liq.get("currency", "CAD")
    return value, currency


def _is_non_liquid_account(description: str) -> bool:
    """Check if account is non-liquid based on description.

    Args:
        description: Account description

    Returns:
        True if account is non-liquid (RRSP, LIRA, Private Equity, Private Credit)
    """
    non_liquid_keywords = ["rrsp", "lira", "private equity", "private credit"]
    return any(keyword in description.lower() for keyword in non_liquid_keywords)


def _should_include_account(
    is_non_liquid: bool, liquid_only: bool, not_liquid: bool
) -> bool:
    """Determine if account should be included based on filter options.

    Args:
        is_non_liquid: Whether account is non-liquid
        liquid_only: Only include liquid accounts
        not_liquid: Only include non-liquid accounts

    Returns:
        True if account should be included
    """
    if liquid_only and is_non_liquid:
        return False
    if not_liquid and not is_non_liquid:
        return False
    return True


def get_accounts_data(
    ws: WealthsimpleAPI,
    show_zero_balances: bool = False,
    liquid_only: bool = False,
    not_liquid: bool = False,
) -> list[AccountData]:
    """Fetch and transform account data.

    Args:
        ws: Authenticated WealthsimpleAPI client
        show_zero_balances: Whether to include accounts with zero balance
        liquid_only: Whether to show only liquid accounts (excludes RRSP, LIRA, Private Equity, Private Credit)
        not_liquid: Whether to show only non-liquid accounts (RRSP, LIRA, Private Equity, Private Credit)

    Returns:
        List of AccountData objects
    """
    accounts = ws.get_accounts()

    if not accounts:
        return []

    result = []
    for account in accounts:
        description = account.get("description", "Unknown Account")
        number = account.get("number", "N/A")

        # Apply liquid/not_liquid filters
        is_non_liquid = _is_non_liquid_account(description)
        if not _should_include_account(is_non_liquid, liquid_only, not_liquid):
            continue

        # Extract value and currency
        value, currency = _extract_account_value(account)

        if value == 0 and not show_zero_balances:
            continue

        result.append(
            AccountData(
                description=description,
                number=number,
                value=value,
                currency=currency,
            )
        )

    return result


def print_accounts(
    ws: WealthsimpleAPI,
    show_zero_balances: bool = False,
    liquid_only: bool = False,
    not_liquid: bool = False,
    output_format: str = "table",
    verbose: bool = False,
) -> None:
    """Fetch and print accounts.

    Args:
        ws: Authenticated WealthsimpleAPI client
        show_zero_balances: Whether to include accounts with zero balance
        liquid_only: Whether to show only liquid accounts (excludes RRSP, LIRA, Private Equity, Private Credit)
        not_liquid: Whether to show only non-liquid accounts (RRSP, LIRA, Private Equity, Private Credit)
        output_format: Output format - 'table', 'json', or 'csv' (default 'table')
        verbose: If True, print status messages during execution
    """
    if verbose:
        print("\nFetching accounts...")

    accounts_data = get_accounts_data(ws, show_zero_balances, liquid_only, not_liquid)

    if not accounts_data:
        print("No accounts found.")
        return

    formatter = get_formatter(output_format)
    output = formatter.format_accounts(accounts_data)
    print(output)
