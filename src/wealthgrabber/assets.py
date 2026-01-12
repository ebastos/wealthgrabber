from itertools import groupby
from typing import Optional

from ws_api import WealthsimpleAPI

from .formatters import get_formatter
from .models import PositionData


def _position_has_account(position: dict, account_id: str) -> bool:
    """Check if a position belongs to a specific account."""
    accounts = position.get("accounts", [])
    return any(acc.get("id") == account_id for acc in accounts)


def _get_position_account_ids(position: dict) -> list[str]:
    """Get all account IDs associated with a position."""
    accounts = position.get("accounts", [])
    return [acc.get("id") for acc in accounts if acc.get("id")]


def _get_security_info(
    ws: WealthsimpleAPI, security_id: str, cache: dict
) -> tuple[str, str]:
    """Get symbol and name for a security, using cache to avoid redundant API calls."""
    if security_id in cache:
        return cache[security_id]

    symbol = "N/A"
    name = "Unknown"

    if security_id:
        try:
            market_data = ws.get_security_market_data(security_id, use_cache=False)
            if market_data and market_data.get("stock"):
                stock = market_data["stock"]
                symbol = stock.get("symbol", "N/A")
                name = stock.get("name", symbol)
        except Exception:
            # Fallback for securities that can't be looked up
            symbol = security_id
            name = security_id

    cache[security_id] = (symbol, name)
    return symbol, name


def _get_position_data(
    ws: WealthsimpleAPI,
    position: dict,
    security_cache: dict[str, tuple[str, str]],
    currency: str,
) -> PositionData:
    """Extract and format position data including P&L calculation."""
    # Get security info
    security = position.get("security", {})
    security_id = security.get("id", "")
    symbol, name = _get_security_info(ws, security_id, security_cache)
    name = name[:30]

    # Extract quantity and market value
    quantity = float(position.get("quantity", 0))
    total_val = position.get("totalValue", {})
    market_value = float(total_val.get("amount", 0))
    val_currency = total_val.get("currency", currency)

    # Extract book value for P&L calculation
    book_val = position.get("bookValue", {})
    book_value = float(book_val.get("amount", 0))

    # Calculate P&L
    pnl = market_value - book_value
    pnl_pct = (pnl / book_value * 100) if book_value != 0 else 0.0

    return PositionData(
        symbol=symbol,
        name=name,
        quantity=quantity,
        market_value=market_value,
        book_value=book_value,
        currency=val_currency,
        pnl=pnl,
        pnl_pct=pnl_pct,
    )


def _build_account_label(account: dict) -> str:
    """Build account label string from account data.

    Args:
        account: Account data dict

    Returns:
        Formatted account label (e.g., "TFSA (ACC-001)")
    """
    description = account.get("description", "Unknown")
    number = account.get("number", "N/A")
    return f"{description} ({number})"


def _get_positions_by_account_grouped(
    ws: WealthsimpleAPI,
    positions: list,
    accounts: list,
    security_cache: dict,
    currency: str,
) -> list[PositionData]:
    """Get positions organized by account with labels.

    Args:
        ws: Authenticated WealthsimpleAPI client
        positions: List of all positions
        accounts: List of accounts to organize by
        security_cache: Cache for security lookups
        currency: Currency code

    Returns:
        List of PositionData objects with account labels
    """
    # Build position mapping by account
    positions_by_account: dict[str, list] = {}
    for pos in positions:
        for acc_id in _get_position_account_ids(pos):
            positions_by_account.setdefault(acc_id, []).append(pos)

    result = []
    for account in accounts:
        acc_id = account.get("id")
        acc_positions = positions_by_account.get(acc_id, [])

        if not acc_positions:
            continue

        acc_label = _build_account_label(account)
        for pos in acc_positions:
            pos_data = _get_position_data(ws, pos, security_cache, currency)
            pos_data.account_label = acc_label
            result.append(pos_data)

    return result


def _filter_positions_by_account(positions: list, account_id: str) -> list:
    """Filter positions to those in a specific account.

    Args:
        positions: List of all positions
        account_id: Account ID to filter by

    Returns:
        Filtered list of positions
    """
    return [p for p in positions if _position_has_account(p, account_id)]


def _get_accounts_for_assets(
    ws: WealthsimpleAPI, account_id: Optional[str] = None
) -> list:
    """Get accounts, optionally filtered by account_id.

    Args:
        ws: Authenticated WealthsimpleAPI client
        account_id: Optional account ID to filter by

    Returns:
        List of accounts
    """
    accounts = ws.get_accounts()
    if account_id:
        accounts = [a for a in accounts if a.get("id") == account_id]
    return accounts


def get_assets_data(
    ws: WealthsimpleAPI,
    account_id: Optional[str] = None,
    by_account: bool = False,
    currency: str = "CAD",
    pnl_filter: Optional[str] = None,
) -> list[PositionData]:
    """Fetch and transform asset position data.

    Args:
        ws: Authenticated WealthsimpleAPI client
        account_id: Optional account ID to filter positions
        by_account: Whether to organize positions by account
        currency: Currency code (default "CAD")
        pnl_filter: Optional filter by P&L - "profit" (pnl > 0), "loss" (pnl < 0), or None (all)

    Returns:
        List of PositionData objects with account labels if by_account=True
    """
    positions = ws.get_identity_positions(None, currency)
    if not positions:
        return []

    if account_id:
        positions = _filter_positions_by_account(positions, account_id)
    if not positions:
        return []

    security_cache: dict[str, tuple[str, str]] = {}

    if not by_account:
        # Aggregated view (all positions without account labels)
        position_data = [
            _get_position_data(ws, pos, security_cache, currency) for pos in positions
        ]
    else:
        # By-account view: get accounts and group positions
        accounts = _get_accounts_for_assets(ws, account_id)
        if not accounts:
            return []
        position_data = _get_positions_by_account_grouped(
            ws, positions, accounts, security_cache, currency
        )

    # Apply P&L filter if specified
    if pnl_filter == "profit":
        position_data = [pos for pos in position_data if pos.pnl > 0]
    elif pnl_filter == "loss":
        position_data = [pos for pos in position_data if pos.pnl < 0]
    # If pnl_filter is None, return all positions (default behavior)

    return position_data


def _calculate_position_totals(
    positions: list[PositionData],
) -> tuple[float, float, float]:
    """Calculate total position values and P&L.

    Args:
        positions: List of positions

    Returns:
        Tuple of (total_value, total_pnl, total_pnl_pct)
    """
    total_value = sum(p.market_value for p in positions)
    total_book = sum(p.book_value for p in positions)
    total_pnl = total_value - total_book
    total_pnl_pct = (total_pnl / total_book * 100) if total_book != 0 else 0.0
    return total_value, total_pnl, total_pnl_pct


def _format_pnl_display(pnl: float, pnl_pct: float) -> tuple[str, str]:
    """Format P&L values for display.

    Args:
        pnl: P&L amount
        pnl_pct: P&L percentage

    Returns:
        Tuple of (pnl_str, pnl_pct_str)
    """
    pnl_str = f"{'+' if pnl >= 0 else ''}{pnl:,.2f}"
    pnl_pct_str = f"{'+' if pnl_pct >= 0 else ''}{pnl_pct:.1f}%"
    return pnl_str, pnl_pct_str


def _print_positions_by_account(
    formatter,
    positions_data: list[PositionData],
) -> None:
    """Print positions grouped by account with grand totals.

    Args:
        formatter: Output formatter instance
        positions_data: List of position data
    """
    positions_sorted = sorted(positions_data, key=lambda p: p.account_label or "")

    for account_label, group_iter in groupby(
        positions_sorted, key=lambda p: p.account_label
    ):
        group = list(group_iter)
        output = formatter.format_positions(
            group, show_totals=True, group_label=account_label
        )
        print(output)

    # Print grand total
    total_value, total_pnl, total_pnl_pct = _calculate_position_totals(positions_data)
    pnl_str, pnl_pct_str = _format_pnl_display(total_pnl, total_pnl_pct)
    currency_str = positions_data[0].currency if positions_data else "CAD"

    print("\n" + "=" * 94)
    print(
        f"{'Grand Total':<51} {total_value:>13,.2f} {currency_str} {pnl_str:>13} {pnl_pct_str:>8}"
    )
    print("=" * 94)


def print_assets(
    ws: WealthsimpleAPI,
    account_id: Optional[str] = None,
    by_account: bool = False,
    currency: str = "CAD",
    output_format: str = "table",
    verbose: bool = False,
    pnl_filter: Optional[str] = None,
) -> None:
    """Fetch and print asset positions.

    Args:
        ws: Authenticated WealthsimpleAPI client
        account_id: Optional account ID to filter positions
        by_account: Whether to show positions grouped by account
        currency: Currency code (default "CAD")
        output_format: Output format - 'table', 'json', or 'csv' (default 'table')
        verbose: If True, print status messages during execution
        pnl_filter: Optional filter by P&L - "profit" (pnl > 0), "loss" (pnl < 0), or None (all)
    """
    if verbose:
        print("\nFetching positions...")

    positions_data = get_assets_data(ws, account_id, by_account, currency, pnl_filter)

    if not positions_data:
        print("No positions found.")
        return

    formatter = get_formatter(output_format)

    if by_account and output_format == "table":
        _print_positions_by_account(formatter, positions_data)
    else:
        # For non-table formats or aggregated mode, use formatter directly
        output = formatter.format_positions(positions_data, show_totals=True)
        print(output)
